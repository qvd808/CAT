import os
import uuid
import signal
import sys
import shutil
from typing import Optional

try:
    import docker
except ImportError:
    docker = None

from graph.state import SandboxSession
from config import OUTPUT_DIR
from utils.display import console

_ACTIVE_SESSIONS = []

def cleanup_all_sessions():
    """Forces cleanup of all active sessions to prevent zombie containers."""
    for session in _ACTIVE_SESSIONS:
        session.cleanup()

class SessionManager:
    """
    Manages the SandboxSession lifecycle via Docker.
    Provides context manager logic and handles SIGINT to prevent zombie containers.
    """
    def __init__(self, project_name: str, tech_strategy: dict):
        self.project_name = project_name
        self.tech_strategy = tech_strategy
        self.image = tech_strategy.get("sandbox_image", "ubuntu:latest")  # Fallback image
        
        # Safe project name for folder
        self.safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
        self.project_dir = os.path.join(OUTPUT_DIR, self.safe_name)
        
        self.session_id = str(uuid.uuid4())
        self.log_path = os.path.join(os.path.dirname(__file__), "..", "logs", f"{self.session_id}.jsonl")
        
        self.container_id = None
        self._docker_client = None
        
        # Ensure log dir and project dir exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Register SIGINT to prevent zombie containers
        self._original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, signum, frame):
        """Cleanup container on Ctrl+C"""
        console.print("\n[bold red]⚠️ Received SIGINT. Cleaning up Sandbox Container...[/]")
        self.cleanup()
        if self._original_sigint and callable(self._original_sigint):
            self._original_sigint(signum, frame)
        else:
            sys.exit(1)

    @property
    def client(self):
        if self._docker_client is None:
            if not docker:
                raise ImportError("docker package is not installed. Run `pip install docker`.")
            self._docker_client = docker.from_env()
        return self._docker_client

    def __enter__(self) -> SandboxSession:
        """Start the session and container"""
        _ACTIVE_SESSIONS.append(self)
        console.print(f" [dim]📦 Starting sandbox session (Image: {self.image})[/]")
        
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            console.print(f" [dim]Pulling image {self.image}...[/]")
            self.client.images.pull(self.image)
            
        # Run container in detached mode, mount volume, sleeping indefinitely
        abs_project_dir = os.path.abspath(self.project_dir)
        mount_path = f"/workspace"
        
        try:
            container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null",  # sleep forever
                detach=True,
                volumes={abs_project_dir: {'bind': mount_path, 'mode': 'rw'}},
                working_dir=mount_path,
                name=f"architect_sandbox_{self.session_id}"
            )
            self.container_id = container.id
            
            # Return primitive SandboxSession representing this session
            return SandboxSession(
                session_id=self.session_id,
                container_id=self.container_id,
                image=self.image,
                mount_path=mount_path,
                status="running",
                iteration=0,
                log_path=self.log_path
            )
        except Exception as e:
            console.print(f" [red]Failed to start container: {e}[/red]")
            return SandboxSession(
                session_id=self.session_id,
                container_id="",
                image=self.image,
                mount_path=mount_path,
                status="error",
                iteration=0,
                log_path=self.log_path
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop and remove container"""
        self.cleanup()

    def cleanup(self):
        """Force stops and removes the Docker container"""
        if self.container_id and self._docker_client:
            try:
                container = self._docker_client.containers.get(self.container_id)
                container.stop(timeout=2)
                container.remove(force=True)
                console.print(f" [dim]🧹 Removed sandbox container {self.container_id[:8]}[/]")
            except Exception:
                pass
            finally:
                self.container_id = None
        
        # Restore original SIGINT
        signal.signal(signal.SIGINT, self._original_sigint)

    def checkpoint(self):
        """Create a filesystem snapshot of the project directory."""
        checkpoint_dir = os.path.join(self.project_dir, ".architect_checkpoint")
        if os.path.exists(checkpoint_dir):
            shutil.rmtree(checkpoint_dir)
            
        console.print(f" [dim]📸 Saving state checkpoint...[/]")
        os.makedirs(checkpoint_dir)
        
        for item in os.listdir(self.project_dir):
            if item in [".architect_checkpoint", ".git"]:
                continue
            src = os.path.join(self.project_dir, item)
            dst = os.path.join(checkpoint_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    def rollback(self):
        """Restore filesystem from the last snapshot."""
        checkpoint_dir = os.path.join(self.project_dir, ".architect_checkpoint")
        if not os.path.exists(checkpoint_dir):
            console.print(" [dim yellow]⚠ No checkpoint found to rollback.[/]")
            return
            
        console.print(f" [dim]⏪ Rolling back to previous clean state...[/]")
        
        # Clear current files
        for item in os.listdir(self.project_dir):
            if item in [".architect_checkpoint", ".git"]:
                continue
            item_path = os.path.join(self.project_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
                
        # Restore from checkpoint
        for item in os.listdir(checkpoint_dir):
            src = os.path.join(checkpoint_dir, item)
            dst = os.path.join(self.project_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
