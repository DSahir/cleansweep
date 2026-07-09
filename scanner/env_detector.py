"""
CleanSweep — Environment & Runtime Detector
Discovers all installed language runtimes (Python, Java, Node, Ruby),
Docker resources, and Homebrew stats.  Uses subprocess calls with
graceful fallbacks when tools are not installed.
"""

import os
import sys
import glob
import re
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    PYTHON_LOCATIONS,
    JAVA_LOCATIONS,
    NODE_LOCATIONS,
    RUBY_LOCATIONS,
    DOCKER_PATHS,
    format_size,
    get_dir_size,
)


# ─── Subprocess Helpers ──────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess | None:
    """Run a command and return the result, or *None* on any failure."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _which_all(binary: str) -> list[str]:
    """Return all paths for *binary* using ``which -a``."""
    result = _run(["which", "-a", binary])
    if result is None or result.returncode != 0:
        return []
    return [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]


def _version_from_cmd(cmd: list[str]) -> str:
    """Extract a version string from a command's output."""
    result = _run(cmd)
    if result is None or result.returncode != 0:
        return "unknown"
    text = result.stdout.strip() or result.stderr.strip()
    # Try to pull out a semver-ish pattern
    match = re.search(r"(\d+\.\d+[\.\d]*)", text)
    return match.group(1) if match else text.split("\n")[0][:60]


def _classify_python_source(path: str) -> str:
    """Guess how a Python binary was installed."""
    p = path.lower()
    if ".pyenv" in p:
        return "pyenv"
    if "anaconda" in p or "miniconda" in p or "conda" in p:
        return "anaconda"
    if "/opt/homebrew" in p or "/usr/local/Cellar" in p:
        return "homebrew"
    if p.startswith("/usr/bin"):
        return "system"
    return "other"


def _dir_size_safe(path: Path) -> int:
    """Return directory size or 0 if inaccessible."""
    try:
        return get_dir_size(path)
    except (PermissionError, OSError):
        return 0


# ─── Python ───────────────────────────────────────────────────────────────────

def detect_python() -> list[dict]:
    """
    Detect all Python 3 installations.

    Returns
    -------
    list[dict]
        version, path, size, size_formatted, source, is_active
    """
    seen_real: set[str] = set()
    installs: list[dict] = []

    # Current active python
    active_path = shutil.which("python3") or ""
    try:
        active_real = os.path.realpath(active_path) if active_path else ""
    except OSError:
        active_real = ""

    # 1. which -a
    for p in _which_all("python3"):
        try:
            real = os.path.realpath(p)
        except OSError:
            real = p
        if real in seen_real:
            continue
        seen_real.add(real)
        version = _version_from_cmd([p, "--version"])
        prefix = os.path.dirname(os.path.dirname(real))
        size = _dir_size_safe(Path(prefix))
        installs.append({
            "version": version,
            "path": real,
            "size": size,
            "size_formatted": format_size(size),
            "source": _classify_python_source(real),
            "is_active": (real == active_real),
        })

    # 2. Well-known directories (pyenv versions, conda)
    for loc in PYTHON_LOCATIONS:
        loc = Path(str(loc))  # handle glob-style entries
        if "*" in str(loc):
            for expanded in glob.glob(str(loc)):
                _add_python_from_dir(Path(expanded), installs, seen_real, active_real)
        elif loc.is_dir():
            _add_python_from_dir(loc, installs, seen_real, active_real)

    return installs


def _add_python_from_dir(
    base: Path,
    installs: list[dict],
    seen_real: set[str],
    active_real: str,
) -> None:
    """Add any Python installs found under *base*."""
    # pyenv / anaconda keep versions in sub-directories
    if not base.is_dir():
        return
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        python_bin = child / "bin" / "python3"
        if not python_bin.exists():
            python_bin = child / "bin" / "python"
        if not python_bin.exists():
            continue
        try:
            real = os.path.realpath(str(python_bin))
        except OSError:
            real = str(python_bin)
        if real in seen_real:
            continue
        seen_real.add(real)
        version = _version_from_cmd([str(python_bin), "--version"])
        size = _dir_size_safe(child)
        installs.append({
            "version": version,
            "path": real,
            "size": size,
            "size_formatted": format_size(size),
            "source": _classify_python_source(real),
            "is_active": (real == active_real),
        })


# ─── Java ─────────────────────────────────────────────────────────────────────

def detect_java() -> list[dict]:
    """
    Detect installed JDK/JRE versions.

    Returns
    -------
    list[dict]
        version, path, size, size_formatted
    """
    installs: list[dict] = []
    seen: set[str] = set()

    # /Library/Java/JavaVirtualMachines
    jvm_dir = JAVA_LOCATIONS[0] if JAVA_LOCATIONS else Path("/Library/Java/JavaVirtualMachines")
    if jvm_dir.is_dir():
        for child in sorted(jvm_dir.iterdir()):
            if not child.is_dir():
                continue
            java_bin = child / "Contents" / "Home" / "bin" / "java"
            real = str(child)
            if real in seen:
                continue
            seen.add(real)
            version = "unknown"
            if java_bin.exists():
                version = _version_from_cmd([str(java_bin), "-version"])
            size = _dir_size_safe(child)
            installs.append({
                "version": version,
                "path": real,
                "size": size,
                "size_formatted": format_size(size),
            })

    # java_home utility
    result = _run(["/usr/libexec/java_home", "-V"])
    if result and (result.stdout or result.stderr):
        text = result.stderr or result.stdout
        for line in text.strip().splitlines():
            match = re.search(r"(\d+[\d.]*\S*).*?(/.+)$", line)
            if match:
                ver, path = match.group(1), match.group(2).strip()
                if path not in seen:
                    seen.add(path)
                    size = _dir_size_safe(Path(path))
                    installs.append({
                        "version": ver,
                        "path": path,
                        "size": size,
                        "size_formatted": format_size(size),
                    })

    return installs


# ─── Node ─────────────────────────────────────────────────────────────────────

def detect_node() -> list[dict]:
    """
    Detect installed Node.js versions.

    Returns
    -------
    list[dict]
        version, path, size, size_formatted
    """
    installs: list[dict] = []
    seen: set[str] = set()

    # which -a node
    for p in _which_all("node"):
        try:
            real = os.path.realpath(p)
        except OSError:
            real = p
        if real in seen:
            continue
        seen.add(real)
        version = _version_from_cmd([p, "--version"])
        prefix = os.path.dirname(os.path.dirname(real))
        size = _dir_size_safe(Path(prefix))
        installs.append({
            "version": version,
            "path": real,
            "size": size,
            "size_formatted": format_size(size),
        })

    # Version-manager directories (nvm, fnm, volta)
    for loc in NODE_LOCATIONS:
        if not loc.is_dir():
            continue
        for child in sorted(loc.iterdir()):
            if not child.is_dir():
                continue
            node_bin = child / "bin" / "node"
            if not node_bin.exists():
                continue
            try:
                real = os.path.realpath(str(node_bin))
            except OSError:
                real = str(node_bin)
            if real in seen:
                continue
            seen.add(real)
            version = _version_from_cmd([str(node_bin), "--version"])
            size = _dir_size_safe(child)
            installs.append({
                "version": version,
                "path": real,
                "size": size,
                "size_formatted": format_size(size),
            })

    return installs


# ─── Ruby ─────────────────────────────────────────────────────────────────────

def detect_ruby() -> list[dict]:
    """
    Detect installed Ruby versions.

    Returns
    -------
    list[dict]
        version, path, size, size_formatted
    """
    installs: list[dict] = []
    seen: set[str] = set()

    for p in _which_all("ruby"):
        try:
            real = os.path.realpath(p)
        except OSError:
            real = p
        if real in seen:
            continue
        seen.add(real)
        version = _version_from_cmd([p, "--version"])
        prefix = os.path.dirname(os.path.dirname(real))
        size = _dir_size_safe(Path(prefix))
        installs.append({
            "version": version,
            "path": real,
            "size": size,
            "size_formatted": format_size(size),
        })

    # rbenv / rvm
    for loc in RUBY_LOCATIONS:
        if not loc.is_dir():
            continue
        for child in sorted(loc.iterdir()):
            if not child.is_dir():
                continue
            ruby_bin = child / "bin" / "ruby"
            if not ruby_bin.exists():
                continue
            try:
                real = os.path.realpath(str(ruby_bin))
            except OSError:
                real = str(ruby_bin)
            if real in seen:
                continue
            seen.add(real)
            version = _version_from_cmd([str(ruby_bin), "--version"])
            size = _dir_size_safe(child)
            installs.append({
                "version": version,
                "path": real,
                "size": size,
                "size_formatted": format_size(size),
            })

    return installs


# ─── Docker ───────────────────────────────────────────────────────────────────

def detect_docker() -> dict:
    """
    Gather Docker resource usage.

    Returns
    -------
    dict
        installed, disk_image_size, disk_image_size_formatted,
        images, containers, volumes, total_reclaimable, total_reclaimable_formatted
    """
    info: dict = {
        "installed": False,
        "disk_image_size": 0,
        "disk_image_size_formatted": "0 B",
        "images": [],
        "containers": [],
        "volumes": [],
        "total_reclaimable": 0,
        "total_reclaimable_formatted": "0 B",
    }

    if not shutil.which("docker"):
        return info
    info["installed"] = True

    # Disk image on host
    docker_data = DOCKER_PATHS.get("docker_data")
    if docker_data and Path(docker_data).exists():
        size = _dir_size_safe(Path(docker_data))
        info["disk_image_size"] = size
        info["disk_image_size_formatted"] = format_size(size)

    # Images
    result = _run(["docker", "images", "--format",
                    "{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}\t{{.CreatedAt}}"])
    if result and result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5:
                info["images"].append({
                    "repo": parts[0],
                    "tag": parts[1],
                    "size": parts[2],
                    "id": parts[3],
                    "created": parts[4],
                })

    # Containers
    result = _run(["docker", "ps", "-a", "--format",
                    "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Size}}\t{{.Image}}"])
    if result and result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5:
                info["containers"].append({
                    "id": parts[0],
                    "name": parts[1],
                    "status": parts[2],
                    "size": parts[3],
                    "image": parts[4],
                })

    # Volumes
    result = _run(["docker", "volume", "ls", "--format", "{{.Name}}\t{{.Driver}}"])
    if result and result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                info["volumes"].append({
                    "name": parts[0],
                    "driver": parts[1],
                })

    # Reclaimable space
    result = _run(["docker", "system", "df", "--format",
                    "{{.Type}}\t{{.Reclaimable}}"])
    if result and result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                raw = parts[1].strip()
                # Parse something like "1.234GB (100%)"
                match = re.match(r"([\d.]+)\s*(B|KB|MB|GB|TB)", raw, re.IGNORECASE)
                if match:
                    val = float(match.group(1))
                    unit = match.group(2).upper()
                    multiplier = {"B": 1, "KB": 1024, "MB": 1024**2,
                                  "GB": 1024**3, "TB": 1024**4}
                    info["total_reclaimable"] += int(val * multiplier.get(unit, 1))

    info["total_reclaimable_formatted"] = format_size(info["total_reclaimable"])
    return info


# ─── Homebrew ─────────────────────────────────────────────────────────────────

def detect_homebrew() -> dict:
    """
    Gather Homebrew stats and reclaimable space.

    Returns
    -------
    dict
        installed, formula_count, cask_count,
        cleanup_reclaimable, cleanup_reclaimable_formatted
    """
    info: dict = {
        "installed": False,
        "formula_count": 0,
        "cask_count": 0,
        "cleanup_reclaimable": 0,
        "cleanup_reclaimable_formatted": "0 B",
    }

    if not shutil.which("brew"):
        return info
    info["installed"] = True

    # Formula count
    result = _run(["brew", "list", "--formula", "-1"])
    if result and result.returncode == 0:
        info["formula_count"] = len(
            [l for l in result.stdout.strip().splitlines() if l.strip()]
        )

    # Cask count
    result = _run(["brew", "list", "--cask", "-1"])
    if result and result.returncode == 0:
        info["cask_count"] = len(
            [l for l in result.stdout.strip().splitlines() if l.strip()]
        )

    # Cleanup (dry-run)
    result = _run(["brew", "cleanup", "--dry-run"], timeout=30)
    if result and result.returncode == 0:
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        # Each line references a file; sum their sizes as an approximation
        total = 0
        for line in lines:
            path = line.strip()
            try:
                if os.path.isfile(path):
                    total += os.path.getsize(path)
                elif os.path.isdir(path):
                    total += _dir_size_safe(Path(path))
            except (OSError, PermissionError):
                continue
        info["cleanup_reclaimable"] = total
        info["cleanup_reclaimable_formatted"] = format_size(total)

    return info


# ─── Aggregate ────────────────────────────────────────────────────────────────

def detect_all_environments() -> dict:
    """
    Detect every supported runtime environment.

    Returns
    -------
    dict
        python, java, node, ruby, docker, homebrew
    """
    return {
        "python": detect_python(),
        "java": detect_java(),
        "node": detect_node(),
        "ruby": detect_ruby(),
        "docker": detect_docker(),
        "homebrew": detect_homebrew(),
    }


# ─── CLI convenience ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    envs = detect_all_environments()
    print(json.dumps(envs, indent=2, default=str))
