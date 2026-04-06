import json
import os
import datetime
from typing import Dict, Any, List

try:
    import docker
except ImportError:
    docker = None

from graph.state import SandboxSession
from utils.display import console


class SandboxExecutor:
    """
    Executes commands within an existing SandboxSession.
    Logs all executions to the session's JSONL trace file.
    """
    def __init__(self, session: SandboxSession):
        self.session = session
        if not docker:
            raise ImportError("docker package is not installed.")
        self.client = docker.from_env()

    def _append_log(self, log_entry: Dict[str, Any]):
        """Append a JSON string to the session's log file."""
        log_path = self.session.get("log_path")
        if not log_path:
            return
            
        # Ensure dir exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def run_command(self, command: str, triggered_by: str = "sandbox_executor") -> Dict[str, Any]:
        """
        Executes a command in the container via exec_run.
        Returns and logs exit code, stdout, and stderr.
        """
        if self.session.get("status") != "running":
            raise ValueError(f"Cannot execute command. Session status is {self.session.get('status')}")
            
        container_id = self.session.get("container_id")
        if not container_id:
            raise ValueError("No container_id in session.")
            
        console.print(f"  [dim]>$ {command}[/]")
        try:
            container = self.client.containers.get(container_id)
            
            # Using demux=True allows native separation of stdout and stderr
            result = container.exec_run(
                cmd=["sh", "-c", command],
                workdir=self.session.get("mount_path", "/workspace"),
                demux=True 
            )
            
            exit_code = result.exit_code
            stdout_data = result.output[0] if result.output and result.output[0] else b""
            stderr_data = result.output[1] if result.output and result.output[1] else b""
            
            stdout_str = stdout_data.decode("utf-8", errors="replace")
            stderr_str = stderr_data.decode("utf-8", errors="replace")
            
            # Keep last 4000 chars to avoid gigabyte-sized JSON states
            stdout_tail = stdout_str[-4000:] if len(stdout_str) > 4000 else stdout_str
            stderr_tail = stderr_str[-4000:] if len(stderr_str) > 4000 else stderr_str
            
            log_entry = {
                "command": command,
                "exit_code": exit_code,
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "triggered_by": triggered_by,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "iteration": self.session.get("iteration", 0)
            }
            
            self._append_log(log_entry)
            
            if exit_code == 0:
                console.print("  [dim green]Command succeeded[/]")
            else:
                console.print(f"  [dim red]Command failed (Exit code {exit_code})[/]")
                
            return log_entry
            
        except Exception as e:
            error_msg = f"Docker execution error: {str(e)}"
            console.print(f"  [red]{error_msg}[/red]")
            
            log_entry = {
                "command": command,
                "exit_code": -1,
                "stdout_tail": "",
                "stderr_tail": error_msg,
                "triggered_by": triggered_by,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "iteration": self.session.get("iteration", 0)
            }
            self._append_log(log_entry)
            return log_entry


def tail_logs(session: SandboxSession, limit: int = 5) -> List[Dict[str, Any]]:
    """Returns the last N execution records from the session trace file."""
    log_path = session.get("log_path")
    if not log_path or not os.path.exists(log_path):
        return []
        
    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
                    
    return records[-limit:] if limit > 0 else records
