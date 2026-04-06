"""
Dependency validation tools.
Checks if packages actually exist on their registries (crates.io, PyPI, npm)
without needing to install anything or run a sandbox.
"""

import re
import json
import urllib.request
import urllib.error
from utils.display import console


def check_crate(name: str, version: str = None) -> dict:
    """Check if a Rust crate exists on crates.io and if the version is valid."""
    try:
        url = f"https://crates.io/api/v1/crates/{name}"
        req = urllib.request.Request(url, headers={"User-Agent": "ai-solution-architect/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        available_versions = [v["num"] for v in data.get("versions", [])]
        latest = available_versions[0] if available_versions else None

        if version:
            # Check if the requested version matches any available version
            clean_ver = version.lstrip("^~>=<")
            version_exists = any(v.startswith(clean_ver) for v in available_versions)
            return {
                "exists": True,
                "name": name,
                "version_valid": version_exists,
                "requested_version": version,
                "latest_version": latest,
                "suggestion": latest if not version_exists else None,
            }
        return {"exists": True, "name": name, "latest_version": latest}

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"exists": False, "name": name, "error": "Crate not found on crates.io"}
        return {"exists": False, "name": name, "error": str(e)}
    except Exception as e:
        return {"exists": False, "name": name, "error": f"Check failed: {e}"}


def check_pypi_package(name: str) -> dict:
    """Check if a Python package exists on PyPI."""
    try:
        url = f"https://pypi.org/pypi/{name}/json"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("info", {}).get("version", "unknown")
        return {"exists": True, "name": name, "latest_version": latest}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"exists": False, "name": name, "error": "Package not found on PyPI"}
        return {"exists": False, "name": name, "error": str(e)}
    except Exception as e:
        return {"exists": False, "name": name, "error": f"Check failed: {e}"}


def check_npm_package(name: str) -> dict:
    """Check if an npm package exists on the npm registry."""
    try:
        url = f"https://registry.npmjs.org/{name}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("dist-tags", {}).get("latest", "unknown")
        return {"exists": True, "name": name, "latest_version": latest}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"exists": False, "name": name, "error": "Package not found on npm"}
        return {"exists": False, "name": name, "error": str(e)}
    except Exception as e:
        return {"exists": False, "name": name, "error": f"Check failed: {e}"}


def extract_cargo_deps(files: list[dict]) -> list[tuple[str, str]]:
    """Extract dependency names and versions from Cargo.toml content."""
    deps = []
    for f in files:
        if f.get("path", "").endswith("Cargo.toml"):
            content = f.get("content", "")
            # Match lines like: package_name = "version" or package_name = { version = "..." }
            for match in re.finditer(r'^(\w[\w-]*)\s*=\s*"([^"]+)"', content, re.MULTILINE):
                name, version = match.groups()
                # Skip metadata keys
                if name not in ("name", "version", "edition", "description", "license", "authors"):
                    deps.append((name, version))
            # Match lines like: package_name = { version = "..." }
            for match in re.finditer(r'^(\w[\w-]*)\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"', content, re.MULTILINE):
                name, version = match.groups()
                deps.append((name, version))
    return deps


def extract_pypi_deps(files: list[dict]) -> list[str]:
    """Extract package names from requirements.txt or pyproject.toml."""
    deps = []
    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        if path.endswith("requirements.txt"):
            for line in content.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    name = re.split(r'[>=<!\[]', line)[0].strip()
                    if name:
                        deps.append(name)
    return deps


def extract_npm_deps(files: list[dict]) -> list[str]:
    """Extract package names from package.json."""
    deps = []
    for f in files:
        if f.get("path", "").endswith("package.json"):
            try:
                pkg = json.loads(f.get("content", "{}"))
                for key in ("dependencies", "devDependencies"):
                    deps.extend(pkg.get(key, {}).keys())
            except json.JSONDecodeError:
                pass
    return deps


def validate_dependencies(files: list[dict]) -> dict:
    """
    Validate all dependencies found in the project files.
    Returns a report of valid/invalid packages.
    """
    report = {"valid": [], "invalid": [], "warnings": []}

    # Check Cargo (Rust) dependencies
    cargo_deps = extract_cargo_deps(files)
    if cargo_deps:
        console.print("  [dim]Checking Rust crates...[/]")
        for name, version in cargo_deps:
            result = check_crate(name, version)
            if not result.get("exists"):
                report["invalid"].append({
                    "ecosystem": "crates.io",
                    "package": name,
                    "requested": version,
                    "error": result.get("error", "Not found"),
                })
            elif not result.get("version_valid", True):
                report["invalid"].append({
                    "ecosystem": "crates.io",
                    "package": name,
                    "requested": version,
                    "error": f"Version not found. Latest: {result.get('latest_version')}",
                    "suggestion": result.get("suggestion"),
                })
            else:
                report["valid"].append({
                    "ecosystem": "crates.io",
                    "package": name,
                    "version": version,
                })

    # Check PyPI (Python) dependencies
    pypi_deps = extract_pypi_deps(files)
    if pypi_deps:
        console.print("  [dim]Checking Python packages...[/]")
        for name in pypi_deps:
            result = check_pypi_package(name)
            if result.get("exists"):
                report["valid"].append({
                    "ecosystem": "PyPI",
                    "package": name,
                    "latest": result.get("latest_version"),
                })
            else:
                report["invalid"].append({
                    "ecosystem": "PyPI",
                    "package": name,
                    "error": result.get("error", "Not found"),
                })

    # Check npm (JavaScript) dependencies
    npm_deps = extract_npm_deps(files)
    if npm_deps:
        console.print("  [dim]Checking npm packages...[/]")
        for name in npm_deps:
            result = check_npm_package(name)
            if result.get("exists"):
                report["valid"].append({
                    "ecosystem": "npm",
                    "package": name,
                    "latest": result.get("latest_version"),
                })
            else:
                report["invalid"].append({
                    "ecosystem": "npm",
                    "package": name,
                    "error": result.get("error", "Not found"),
                })

    return report
