"""
CleanSweep — Environment Cleaner
Cleanup operations for language runtimes, Docker, Homebrew, and Xcode
build artifacts.  All destructive actions require ``dry_run=False``.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from config import (
    PROTECTED_PATHS,
    LOG_DIR,
    format_size,
    get_dir_size,
    HOME,
    LIBRARY,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _ensure_log_dir() -> Path:
    """Create the log directory if it doesn't already exist."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return LOG_DIR


def _write_log(log_data: dict) -> str:
    """Persist *log_data* as a JSON log file. Returns the path."""
    try:
        log_dir = _ensure_log_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"env_{timestamp}.json"

        counter = 1
        while log_path.exists():
            log_path = log_dir / f"env_{timestamp}_{counter}.json"
            counter += 1

        with open(log_path, "w", encoding="utf-8") as fh:
            json.dump(log_data, fh, indent=2, default=str)

        return str(log_path)
    except OSError:
        return ""


def _is_protected(path: Path) -> bool:
    """Return True if *path* resides inside a protected directory."""
    resolved = path.resolve()
    for protected in PROTECTED_PATHS:
        try:
            protected_resolved = protected.resolve()
            if resolved == protected_resolved or protected_resolved in resolved.parents:
                return True
        except (OSError, ValueError):
            continue
    return False


def _needs_sudo(path: Path) -> bool:
    """Heuristic: paths outside HOME typically require elevated
    privileges to modify."""
    try:
        resolved = path.resolve()
        return not str(resolved).startswith(str(HOME.resolve()))
    except (OSError, ValueError):
        return True


def _run_command(
    cmd: list[str],
    dry_run: bool = True,
) -> dict:
    """Run a shell command, or simulate it in dry-run mode.

    Returns
    -------
    dict
        {command, stdout, stderr, returncode, dry_run}
    """
    result = {
        "command": " ".join(cmd),
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "dry_run": dry_run,
    }

    if dry_run:
        result["stdout"] = "[dry-run] Command would be executed."
        result["returncode"] = 0
        return result

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["returncode"] = proc.returncode
    except FileNotFoundError:
        result["stderr"] = f"Command not found: {cmd[0]}"
        result["returncode"] = 127
    except subprocess.TimeoutExpired:
        result["stderr"] = "Command timed out after 300 seconds."
        result["returncode"] = -1
    except OSError as exc:
        result["stderr"] = f"OS error running command: {exc}"
        result["returncode"] = -1

    return result


def _remove_directory(
    path: Path,
    label: str,
    dry_run: bool = True,
) -> dict:
    """Generic helper to remove a directory (e.g. a runtime version).

    Parameters
    ----------
    path : Path
        Directory to remove.
    label : str
        Human-readable label for the operation.
    dry_run : bool
        When True, report only.

    Returns
    -------
    dict
        {path, label, size, size_formatted, removed, requires_sudo,
         dry_run, errors}
    """
    path = Path(path)
    result = {
        "path": str(path),
        "label": label,
        "size": 0,
        "size_formatted": "0 B",
        "removed": False,
        "requires_sudo": False,
        "dry_run": dry_run,
        "errors": [],
    }

    if not path.exists():
        result["errors"].append(f"Path does not exist: {path}")
        return result

    if _is_protected(path):
        result["errors"].append(f"Path is protected and cannot be removed: {path}")
        return result

    # Size calculation
    try:
        dir_size = get_dir_size(path)
        result["size"] = dir_size
        result["size_formatted"] = format_size(dir_size)
    except (PermissionError, OSError):
        result["errors"].append(f"Could not calculate size of {path}")

    # Sudo check
    if _needs_sudo(path):
        result["requires_sudo"] = True
        if not dry_run:
            result["errors"].append(
                f"Removal of {path} may require sudo. "
                "Run with elevated privileges or remove manually: "
                f"sudo rm -rf '{path}'"
            )
            # Still attempt removal — it will fail gracefully if
            # permissions are insufficient.

    if dry_run:
        return result

    # Actual removal
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        result["removed"] = True
    except PermissionError as exc:
        result["errors"].append(
            f"Permission denied removing {path}: {exc}. "
            f"Try: sudo rm -rf '{path}'"
        )
    except OSError as exc:
        result["errors"].append(f"OS error removing {path}: {exc}")

    _write_log({
        "operation": label,
        "timestamp": datetime.now().isoformat(),
        **result,
    })

    return result


# ─── Runtime Removers ────────────────────────────────────────────────────────


def remove_python_version(path, dry_run: bool = True) -> dict:
    """Remove a Python installation at *path*.

    Works for pyenv versions, Homebrew-managed Python, Anaconda /
    Miniconda environments, and standalone installs.

    Parameters
    ----------
    path : str | Path
        Root directory of the Python installation to remove.
    dry_run : bool
        When True (default), no files are deleted.

    Returns
    -------
    dict
        Result dict with size, removed status, and any errors.
    """
    path = Path(path)
    result = _remove_directory(path, "remove_python_version", dry_run=dry_run)

    # If the path is inside pyenv, also clean up the shims
    if ".pyenv" in str(path) and not dry_run and result["removed"]:
        shims_cmd = _run_command(["pyenv", "rehash"], dry_run=False)
        if shims_cmd["returncode"] != 0:
            result["errors"].append(
                "Could not rehash pyenv shims: " + shims_cmd["stderr"]
            )

    return result


def remove_java_version(path, dry_run: bool = True) -> dict:
    """Remove a Java JDK installation at *path*.

    Typically located under ``/Library/Java/JavaVirtualMachines/``.

    Parameters
    ----------
    path : str | Path
        Root directory of the JDK to remove.
    dry_run : bool
        When True (default), no files are deleted.

    Returns
    -------
    dict
        Result dict with size, removed status, and any errors.
    """
    path = Path(path)
    result = _remove_directory(path, "remove_java_version", dry_run=dry_run)

    if result.get("requires_sudo") and dry_run:
        result["errors"].append(
            f"Java JDK removal typically requires sudo: "
            f"sudo rm -rf '{path}'"
        )

    return result


def remove_node_version(path, dry_run: bool = True) -> dict:
    """Remove a Node.js version at *path*.

    Supports nvm, fnm, Volta, and Homebrew-managed installs.

    Parameters
    ----------
    path : str | Path
        Root directory of the Node version to remove.
    dry_run : bool
        When True (default), no files are deleted.

    Returns
    -------
    dict
        Result dict with size, removed status, and any errors.
    """
    path = Path(path)
    return _remove_directory(path, "remove_node_version", dry_run=dry_run)


# ─── Docker ──────────────────────────────────────────────────────────────────


def docker_prune(
    prune_type: str = "all",
    dry_run: bool = True,
) -> dict:
    """Run ``docker system prune`` (or a targeted variant).

    Parameters
    ----------
    prune_type : str
        One of ``"images"``, ``"containers"``, ``"volumes"``, ``"all"``.
    dry_run : bool
        When True (default), no prune is actually performed.

    Returns
    -------
    dict
        {prune_type, command_result, space_freed, space_freed_formatted,
         dry_run, errors}
    """
    valid_types = {"images", "containers", "volumes", "all"}
    if prune_type not in valid_types:
        return {
            "prune_type": prune_type,
            "command_result": None,
            "space_freed": 0,
            "space_freed_formatted": "0 B",
            "dry_run": dry_run,
            "errors": [
                f"Invalid prune_type '{prune_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            ],
        }

    # Build the command
    if prune_type == "all":
        cmd = ["docker", "system", "prune", "-a", "-f"]
    elif prune_type == "images":
        cmd = ["docker", "image", "prune", "-a", "-f"]
    elif prune_type == "containers":
        cmd = ["docker", "container", "prune", "-f"]
    elif prune_type == "volumes":
        cmd = ["docker", "volume", "prune", "-f"]

    cmd_result = _run_command(cmd, dry_run=dry_run)

    # Try to parse reclaimed space from Docker's stdout
    space_freed = 0
    if cmd_result["stdout"] and not dry_run:
        match = re.search(
            r"Total reclaimed space:\s*([\d.]+)\s*(\w+)",
            cmd_result["stdout"],
        )
        if match:
            value, unit = float(match.group(1)), match.group(2).upper()
            multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
            space_freed = int(value * multipliers.get(unit, 1))

    result = {
        "prune_type": prune_type,
        "command_result": cmd_result,
        "space_freed": space_freed,
        "space_freed_formatted": format_size(space_freed),
        "dry_run": dry_run,
        "errors": [],
    }

    if cmd_result["returncode"] == 127:
        result["errors"].append(
            "Docker CLI not found. Is Docker installed and in PATH?"
        )
    elif cmd_result["returncode"] not in (0, None):
        result["errors"].append(
            f"Docker command failed: {cmd_result['stderr']}"
        )

    _write_log({
        "operation": "docker_prune",
        "timestamp": datetime.now().isoformat(),
        **result,
    })

    return result


# ─── Homebrew ────────────────────────────────────────────────────────────────


def homebrew_cleanup(dry_run: bool = True) -> dict:
    """Run ``brew cleanup`` to remove stale downloads and old formula
    versions.

    Parameters
    ----------
    dry_run : bool
        When True (default), passes ``--dry-run`` to brew.

    Returns
    -------
    dict
        {command_result, space_freed, space_freed_formatted, dry_run,
         errors}
    """
    cmd = ["brew", "cleanup"]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("-s")  # Scrub the cache, including downloads for latest versions

    cmd_result = _run_command(cmd, dry_run=False)  # Always run; brew handles its own dry-run

    # Attempt to parse freed space
    space_freed = 0
    if cmd_result["stdout"] and not dry_run:
        # Brew sometimes prints "==> This operation has freed approximately X of disk space."
        match = re.search(
            r"freed approximately\s+([\d.]+)\s*(\w+)",
            cmd_result["stdout"],
            re.IGNORECASE,
        )
        if match:
            value, unit = float(match.group(1)), match.group(2).upper()
            multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
            space_freed = int(value * multipliers.get(unit, 1))

    result = {
        "command_result": cmd_result,
        "space_freed": space_freed,
        "space_freed_formatted": format_size(space_freed),
        "dry_run": dry_run,
        "errors": [],
    }

    if cmd_result["returncode"] == 127:
        result["errors"].append(
            "Homebrew not found. Is brew installed and in PATH?"
        )
    elif cmd_result["returncode"] not in (0, None):
        result["errors"].append(
            f"brew cleanup failed: {cmd_result['stderr']}"
        )

    _write_log({
        "operation": "homebrew_cleanup",
        "timestamp": datetime.now().isoformat(),
        **result,
    })

    return result


# ─── Xcode DerivedData ───────────────────────────────────────────────────────


def remove_xcode_derived_data(dry_run: bool = True) -> dict:
    """Remove the Xcode DerivedData directory contents.

    The DerivedData folder (``~/Library/Developer/Xcode/DerivedData``)
    holds intermediate build products and can grow very large.

    Parameters
    ----------
    dry_run : bool
        When True (default), report the size without deleting.

    Returns
    -------
    dict
        {path, size, size_formatted, items_removed, removed, dry_run,
         errors}
    """
    derived_data = LIBRARY / "Developer" / "Xcode" / "DerivedData"

    result = {
        "path": str(derived_data),
        "size": 0,
        "size_formatted": "0 B",
        "items_removed": 0,
        "removed": False,
        "dry_run": dry_run,
        "errors": [],
    }

    if not derived_data.exists():
        result["errors"].append(
            f"DerivedData directory not found: {derived_data}"
        )
        return result

    # Calculate current size
    try:
        dir_size = get_dir_size(derived_data)
        result["size"] = dir_size
        result["size_formatted"] = format_size(dir_size)
    except (PermissionError, OSError) as exc:
        result["errors"].append(f"Could not calculate size: {exc}")

    # Count items
    try:
        items = list(derived_data.iterdir())
        result["items_removed"] = len(items)
    except PermissionError as exc:
        result["errors"].append(f"Permission denied listing DerivedData: {exc}")
        return result

    if dry_run:
        return result

    # Delete contents (keep the directory itself)
    errors_during_delete = []
    removed_count = 0

    for item in items:
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed_count += 1
        except PermissionError as exc:
            errors_during_delete.append(
                f"Permission denied deleting {item}: {exc}"
            )
        except OSError as exc:
            errors_during_delete.append(
                f"OS error deleting {item}: {exc}"
            )

    result["items_removed"] = removed_count
    result["removed"] = removed_count > 0
    result["errors"].extend(errors_during_delete)

    _write_log({
        "operation": "remove_xcode_derived_data",
        "timestamp": datetime.now().isoformat(),
        **result,
    })

    return result
