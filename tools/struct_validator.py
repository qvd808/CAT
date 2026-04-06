"""
Structural validator — checks if generated project files are in correct locations
for the detected framework. Framework-agnostic validation.
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from utils.display import console


class StructuralIssue:
    """Represents a structural validation issue."""
    def __init__(self, severity: str, message: str, suggestion: str):
        self.severity = severity  # "error", "warning", "info"
        self.message = message
        self.suggestion = suggestion
    
    def to_dict(self):
        return {
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion
        }


def detect_framework(files: List[dict], tech_stack: dict = None) -> Tuple[str, float]:
    """
    Detect the framework being used based on file patterns.
    Returns (framework_name, confidence_score)
    """
    file_paths = [f.get("path", "") for f in files]
    file_names = [os.path.basename(p) for p in file_paths]
    
    # Check for Tauri
    tauri_indicators = 0
    if "tauri.conf.json" in file_names:
        tauri_indicators += 3
    if "Cargo.toml" in file_names:
        content = next((f.get("content", "") for f in files if f.get("path", "").endswith("Cargo.toml")), "")
        if "tauri" in content.lower():
            tauri_indicators += 2
    if any("src-tauri" in p for p in file_paths):
        tauri_indicators += 2
    if any(".invoke_handler" in f.get("content", "") for f in files):
        tauri_indicators += 1
    
    if tauri_indicators >= 3:
        return "tauri", min(tauri_indicators / 6, 1.0)
    
    # Check for React
    react_indicators = 0
    if "package.json" in file_names:
        content = next((f.get("content", "") for f in files if f.get("path", "").endswith("package.json")), "")
        if "react" in content.lower():
            react_indicators += 2
    if any(p.endswith(".jsx") or p.endswith(".tsx") for p in file_paths):
        react_indicators += 2
    if "src/App.jsx" in file_paths or "src/App.tsx" in file_paths:
        react_indicators += 1
    
    if react_indicators >= 2:
        return "react", min(react_indicators / 5, 1.0)
    
    # Check for FastAPI/Flask
    python_web_indicators = 0
    if any("fastapi" in f.get("content", "").lower() for f in files):
        python_web_indicators += 2
    if any("flask" in f.get("content", "").lower() for f in files):
        python_web_indicators += 2
    if "requirements.txt" in file_names:
        content = next((f.get("content", "") for f in files if f.get("path", "").endswith("requirements.txt")), "")
        if "fastapi" in content.lower():
            python_web_indicators += 2
        if "flask" in content.lower():
            python_web_indicators += 2
    if any("main.py" in p for p in file_paths):
        python_web_indicators += 1
    
    if python_web_indicators >= 2:
        return "python_web", min(python_web_indicators / 5, 1.0)
    
    # Check for generic Rust
    rust_indicators = 0
    if "Cargo.toml" in file_names:
        rust_indicators += 2
    if any(p.endswith(".rs") for p in file_paths):
        rust_indicators += 1
    
    if rust_indicators >= 2:
        return "rust", min(rust_indicators / 3, 1.0)
    
    return "unknown", 0.0


def validate_tauri_structure(files: List[dict]) -> List[StructuralIssue]:
    """Validate Tauri v1.x project structure."""
    issues = []
    file_paths = [f.get("path", "") for f in files]
    
    # Check for tauri.conf.json location
    tauri_conf_paths = [p for p in file_paths if p.endswith("tauri.conf.json")]
    if not tauri_conf_paths:
        issues.append(StructuralIssue(
            "error",
            "Missing tauri.conf.json file",
            "Add tauri.conf.json to src-tauri/ directory"
        ))
    else:
        # Check if tauri.conf.json is in src-tauri/
        for path in tauri_conf_paths:
            if not path.startswith("src-tauri/"):
                issues.append(StructuralIssue(
                    "error",
                    f"tauri.conf.json is in wrong location: {path}",
                    "Move tauri.conf.json to src-tauri/tauri.conf.json"
                ))
    
    # Check for src-tauri/Cargo.toml
    src_tauri_cargo = [p for p in file_paths if p == "src-tauri/Cargo.toml"]
    if not src_tauri_cargo:
        # Check if there's a Cargo.toml at root with tauri deps
        root_cargo = next((f for f in files if f.get("path", "") == "Cargo.toml"), None)
        if root_cargo and "tauri" in root_cargo.get("content", "").lower():
            issues.append(StructuralIssue(
                "error",
                "Tauri Cargo.toml is at project root instead of src-tauri/",
                "Move Cargo.toml to src-tauri/Cargo.toml and create a workspace root Cargo.toml if needed"
            ))
    
    # Check for src-tauri/src/main.rs
    if not any(p == "src-tauri/src/main.rs" for p in file_paths):
        # Check if main.rs is at wrong location
        if any(p == "src/main.rs" for p in file_paths):
            issues.append(StructuralIssue(
                "error",
                "main.rs is in src/ instead of src-tauri/src/",
                "Move Rust backend code to src-tauri/src/main.rs"
            ))
    
    # Check for src-tauri/build.rs
    if not any(p == "src-tauri/build.rs" for p in file_paths):
        if any(p == "build.rs" for p in file_paths):
            issues.append(StructuralIssue(
                "error",
                "build.rs is at project root instead of src-tauri/",
                "Move build.rs to src-tauri/build.rs"
            ))
    
    # Check tauri.conf.json content
    tauri_conf = next((f for f in files if f.get("path", "").endswith("tauri.conf.json")), None)
    if tauri_conf:
        try:
            config = json.loads(tauri_conf.get("content", "{}"))
            build = config.get("build", {})

            # Check distDir
            dist_dir = build.get("distDir", "")
            if dist_dir == "src" and tauri_conf.get("path", "").startswith("src-tauri/"):
                issues.append(StructuralIssue(
                    "error",
                    f"tauri.conf.json has incorrect distDir: '{dist_dir}'",
                    "Change distDir to '../src' (relative to src-tauri directory)"
                ))

            # Check devPath
            dev_path = build.get("devPath", "")
            if dev_path == "src" and tauri_conf.get("path", "").startswith("src-tauri/"):
                issues.append(StructuralIssue(
                    "warning",
                    f"tauri.conf.json may have incorrect devPath: '{dev_path}'",
                    "Consider changing devPath to '../src' (relative to src-tauri directory)"
                ))

            # Check for feature/allowlist mismatches in Cargo.toml vs tauri.conf.json
            # e.g., "shell-open" in features requires allowlist.shell.open = true
            cargo_file = next(
                (f for f in files if f.get("path", "") == "src-tauri/Cargo.toml"), None
            )
            if cargo_file:
                cargo_content = cargo_file.get("content", "")
                allowlist = config.get("tauri", {}).get("allowlist", {})
                feature_allowlist_map = {
                    "shell-open": ("shell", "open"),
                    "dialog-open": ("dialog", "open"),
                    "dialog-save": ("dialog", "save"),
                    "fs-read-file": ("fs", "readFile"),
                    "fs-write-file": ("fs", "writeFile"),
                    "http-request": ("http", "request"),
                    "notification": ("notification", "all"),
                }
                for cargo_feature, (allow_key, allow_sub) in feature_allowlist_map.items():
                    if f'"{cargo_feature}"' in cargo_content:
                        allowed = allowlist.get(allow_key, {}).get(allow_sub, False)
                        if not allowed:
                            issues.append(StructuralIssue(
                                "error",
                                f"Cargo.toml has feature '{cargo_feature}' but tauri.conf.json is missing allowlist.{allow_key}.{allow_sub}=true",
                                f"Either remove '{cargo_feature}' from Cargo.toml features, or add it to tauri.conf.json allowlist"
                            ))
        except json.JSONDecodeError:
            issues.append(StructuralIssue(
                "error",
                "tauri.conf.json contains invalid JSON",
                "Fix the JSON syntax in tauri.conf.json"
            ))
    
    # Check for frontend files in src/
    frontend_files = [p for p in file_paths if p.startswith("src/") and not p.startswith("src-tauri/")]
    if not frontend_files:
        issues.append(StructuralIssue(
            "warning",
            "No frontend files found in src/ directory",
            "Add index.html and other frontend assets to src/ directory"
        ))
    
    return issues


def validate_react_structure(files: List[dict]) -> List[StructuralIssue]:
    """Validate React project structure."""
    issues = []
    file_paths = [f.get("path", "") for f in files]
    
    # Check for package.json at root
    if not any(p == "package.json" for p in file_paths):
        issues.append(StructuralIssue(
            "error",
            "Missing package.json at project root",
            "Add package.json with React dependencies"
        ))
    
    # Check for src directory
    if not any(p.startswith("src/") for p in file_paths):
        issues.append(StructuralIssue(
            "error",
            "Missing src/ directory",
            "Create src/ directory for React components"
        ))
    
    # Check for public directory (optional but recommended)
    if not any(p.startswith("public/") for p in file_paths):
        issues.append(StructuralIssue(
            "info",
            "No public/ directory found",
            "Consider adding public/ for static assets like index.html"
        ))
    
    return issues


def validate_python_web_structure(files: List[dict]) -> List[StructuralIssue]:
    """Validate Python web framework structure (FastAPI/Flask)."""
    issues = []
    file_paths = [f.get("path", "") for f in files]
    
    # Check for requirements.txt or pyproject.toml
    has_deps = any(p in ["requirements.txt", "pyproject.toml", "setup.py"] for p in file_paths)
    if not has_deps:
        issues.append(StructuralIssue(
            "warning",
            "No dependency file found (requirements.txt, pyproject.toml)",
            "Add requirements.txt with project dependencies"
        ))
    
    # Check for main application file
    main_files = [p for p in file_paths if p in ["main.py", "app.py", "application.py"]]
    if not main_files:
        issues.append(StructuralIssue(
            "error",
            "No main application file found (main.py, app.py)",
            "Add a main.py or app.py as the application entry point"
        ))
    
    return issues


def validate_rust_structure(files: List[dict]) -> List[StructuralIssue]:
    """Validate generic Rust project structure."""
    issues = []
    file_paths = [f.get("path", "") for f in files]
    
    # Check for Cargo.toml at root
    if not any(p == "Cargo.toml" for p in file_paths):
        issues.append(StructuralIssue(
            "error",
            "Missing Cargo.toml at project root",
            "Add Cargo.toml with project configuration"
        ))
    
    # Check for src/main.rs or src/lib.rs
    has_entry = any(p in ["src/main.rs", "src/lib.rs"] for p in file_paths)
    if not has_entry:
        issues.append(StructuralIssue(
            "error",
            "Missing src/main.rs or src/lib.rs",
            "Add the main entry point file"
        ))
    
    return issues


def validate_structure(files: List[dict], tech_stack: dict = None) -> dict:
    """
    Main entry point for structural validation.
    Returns a report with detected framework and any structural issues.
    """
    framework, confidence = detect_framework(files, tech_stack)
    
    report = {
        "framework": framework,
        "confidence": confidence,
        "issues": [],
        "valid": True
    }
    
    if framework == "tauri":
        report["issues"] = [i.to_dict() for i in validate_tauri_structure(files)]
    elif framework == "react":
        report["issues"] = [i.to_dict() for i in validate_react_structure(files)]
    elif framework == "python_web":
        report["issues"] = [i.to_dict() for i in validate_python_web_structure(files)]
    elif framework == "rust":
        report["issues"] = [i.to_dict() for i in validate_rust_structure(files)]
    else:
        report["issues"].append({
            "severity": "info",
            "message": "Could not detect framework - skipping structural validation",
            "suggestion": "Ensure project has recognizable framework patterns"
        })
    
    # Check for critical errors
    errors = [i for i in report["issues"] if i.get("severity") == "error"]
    report["valid"] = len(errors) == 0
    report["error_count"] = len(errors)
    report["warning_count"] = len([i for i in report["issues"] if i.get("severity") == "warning"])
    
    return report


def format_structural_report(report: dict) -> str:
    """Format the structural validation report for display."""
    lines = []
    
    framework = report.get("framework", "unknown")
    confidence = report.get("confidence", 0)
    
    if framework != "unknown":
        lines.append(f"[bold]Detected Framework:[/] {framework.title()} ({confidence:.0%} confidence)")
    else:
        lines.append("[dim]Framework: Unknown[/]")
    
    issues = report.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    
    if errors:
        lines.append(f"\n[red]❌ {len(errors)} structural errors:[/]")
        for issue in errors:
            lines.append(f"  [red]•[/] {issue['message']}")
            lines.append(f"    [dim]→ {issue['suggestion']}[/]")
    
    if warnings:
        lines.append(f"\n[yellow]⚠️ {len(warnings)} warnings:[/]")
        for issue in warnings:
            lines.append(f"  [yellow]•[/] {issue['message']}")
    
    if not errors and not warnings:
        lines.append("\n[green]✅ Project structure looks good![/]")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with example files
    test_files = [
        {"path": "Cargo.toml", "content": "[package]\nname = \"test\""},
        {"path": "tauri.conf.json", "content": "{}"},
        {"path": "src/main.rs", "content": "fn main() {}"},
    ]
    
    report = validate_structure(test_files)
    print(format_structural_report(report))
