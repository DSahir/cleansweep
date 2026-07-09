"""
CleanSweep — File Archiver
Archive, zip, move, and undo operations with JSON manifest tracking
for full reversibility.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from config import ARCHIVE_DIR, MANIFEST_DIR, LOG_DIR, format_size


# ─── Directory Bootstrap ─────────────────────────────────────────────────────


def _ensure_dirs() -> None:
    """Create the archive, manifest, and log directories if missing."""
    for directory in (ARCHIVE_DIR, MANIFEST_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _write_log(log_data: dict) -> str:
    """Persist *log_data* as a JSON file inside LOG_DIR.
    Returns the absolute path to the written file."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"archive_{timestamp}.json"

    counter = 1
    while log_path.exists():
        log_path = LOG_DIR / f"archive_{timestamp}_{counter}.json"
        counter += 1

    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log_data, fh, indent=2, default=str)

    return str(log_path)


def _generate_archive_name(prefix: str = "archive") -> str:
    """Return a timestamped archive basename (without extension)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"


# ─── Manifest Management ────────────────────────────────────────────────────


def create_manifest(
    operation: str,
    files: list,
    result: dict,
) -> str:
    """Save a JSON manifest to MANIFEST_DIR describing an operation so
    it can later be undone.

    Parameters
    ----------
    operation : str
        One of ``"archive"``, ``"archive_and_delete"``, ``"move"``.
    files : list
        The file paths (or move descriptors) involved.
    result : dict
        The result dict returned by the originating function.

    Returns
    -------
    str
        Absolute path to the saved manifest file.
    """
    _ensure_dirs()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_name = f"manifest_{operation}_{timestamp}.json"
    manifest_path = MANIFEST_DIR / manifest_name

    counter = 1
    while manifest_path.exists():
        manifest_path = MANIFEST_DIR / f"manifest_{operation}_{timestamp}_{counter}.json"
        counter += 1

    manifest = {
        "operation": operation,
        "timestamp": datetime.now().isoformat(),
        "files": [str(f) for f in files],
        "result": result,
    }

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    return str(manifest_path)


# ─── Archive Operations ─────────────────────────────────────────────────────


def archive_files(
    file_list: list,
    archive_name: str | None = None,
) -> dict:
    """Create a zip archive containing every file in *file_list*.

    Parameters
    ----------
    file_list : list[str | Path]
        Paths to the files that should be archived.
    archive_name : str, optional
        Base name for the archive (without extension).  A timestamped
        name is generated if omitted.

    Returns
    -------
    dict
        {archive_path, files_archived, total_size, archive_size,
         archive_size_formatted, errors}
    """
    _ensure_dirs()

    if archive_name is None:
        archive_name = _generate_archive_name()

    archive_path = ARCHIVE_DIR / f"{archive_name}.zip"

    # Avoid clobbering an existing archive
    counter = 1
    while archive_path.exists():
        archive_path = ARCHIVE_DIR / f"{archive_name}_{counter}.zip"
        counter += 1

    result = {
        "archive_path": str(archive_path),
        "files_archived": 0,
        "total_size": 0,
        "total_size_formatted": "0 B",
        "archive_size": 0,
        "archive_size_formatted": "0 B",
        "errors": [],
    }

    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                file_path = Path(file_path)
                if not file_path.exists():
                    result["errors"].append(f"File not found: {file_path}")
                    continue

                try:
                    file_size = file_path.stat().st_size
                    # Use the file's name inside the zip to keep it flat
                    arcname = file_path.name
                    # Handle duplicate names inside the archive
                    existing_names = set(zf.namelist())
                    if arcname in existing_names:
                        stem = file_path.stem
                        suffix = file_path.suffix
                        dup = 1
                        while arcname in existing_names:
                            arcname = f"{stem}_{dup}{suffix}"
                            dup += 1

                    zf.write(file_path, arcname)
                    result["files_archived"] += 1
                    result["total_size"] += file_size
                except PermissionError as exc:
                    result["errors"].append(
                        f"Permission denied reading {file_path}: {exc}"
                    )
                except OSError as exc:
                    result["errors"].append(
                        f"OS error archiving {file_path}: {exc}"
                    )
    except OSError as exc:
        result["errors"].append(f"Failed to create archive: {exc}")
        return result

    # Record final archive size
    try:
        result["archive_size"] = archive_path.stat().st_size
    except OSError:
        pass

    result["total_size_formatted"] = format_size(result["total_size"])
    result["archive_size_formatted"] = format_size(result["archive_size"])

    # Manifest + log
    create_manifest("archive", file_list, result)
    _write_log({"operation": "archive_files", **result})

    return result


def archive_and_delete(
    file_list: list,
    archive_name: str | None = None,
) -> dict:
    """Archive files then delete the originals.

    Parameters
    ----------
    file_list : list[str | Path]
        Files to archive and remove.
    archive_name : str, optional
        Base name for the archive.

    Returns
    -------
    dict
        Same as :func:`archive_files` plus ``space_freed`` and
        ``space_freed_formatted``.
    """
    result = archive_files(file_list, archive_name=archive_name)

    # Bail out early if the archive step already failed badly
    if result["files_archived"] == 0:
        result["space_freed"] = 0
        result["space_freed_formatted"] = "0 B"
        return result

    space_freed = 0
    deleted_files = []

    for file_path in file_list:
        file_path = Path(file_path)
        if not file_path.exists():
            continue
        try:
            file_size = file_path.stat().st_size
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            space_freed += file_size
            deleted_files.append(str(file_path))
        except PermissionError as exc:
            result["errors"].append(
                f"Permission denied deleting {file_path}: {exc}"
            )
        except OSError as exc:
            result["errors"].append(f"OS error deleting {file_path}: {exc}")

    result["space_freed"] = space_freed
    result["space_freed_formatted"] = format_size(space_freed)
    result["deleted_files"] = deleted_files

    # Manifest for undo
    create_manifest("archive_and_delete", file_list, result)
    _write_log({"operation": "archive_and_delete", **result})

    return result


# ─── Move Operations ────────────────────────────────────────────────────────


def move_files(moves_list: list) -> dict:
    """Move files according to a list of ``{source, destination}`` dicts.

    Destination directories are created automatically when necessary.

    Parameters
    ----------
    moves_list : list[dict]
        Each element must have ``"source"`` and ``"destination"`` keys.

    Returns
    -------
    dict
        {files_moved, errors, moves}
    """
    result = {
        "files_moved": 0,
        "errors": [],
        "moves": [],
    }

    for move in moves_list:
        source = Path(move.get("source", ""))
        destination = Path(move.get("destination", ""))

        if not source.exists():
            result["errors"].append(f"Source not found: {source}")
            continue

        try:
            # Create destination directory tree
            dest_dir = destination if destination.is_dir() else destination.parent
            dest_dir.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source), str(destination))
            result["files_moved"] += 1
            result["moves"].append({
                "source": str(source),
                "destination": str(destination),
            })
        except PermissionError as exc:
            result["errors"].append(
                f"Permission denied moving {source}: {exc}"
            )
        except OSError as exc:
            result["errors"].append(f"OS error moving {source}: {exc}")

    # Manifest + log
    create_manifest("move", moves_list, result)
    _write_log({"operation": "move_files", **result})

    return result


# ─── Undo ────────────────────────────────────────────────────────────────────


def undo_last_operation() -> dict:
    """Read the most-recent manifest and attempt to reverse the
    operation it describes.

    Supported undo actions:
    * **archive / archive_and_delete** → extract the archive back to the
      original file locations and remove the archive.
    * **move** → move every file back to its original source path.

    Returns
    -------
    dict
        {operation, success, message, errors}
    """
    _ensure_dirs()

    result = {
        "operation": None,
        "success": False,
        "message": "",
        "errors": [],
    }

    # ── Find the latest manifest ──────────────────────────────────────────
    try:
        manifests = sorted(
            MANIFEST_DIR.glob("manifest_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        result["errors"].append(f"Cannot read manifest directory: {exc}")
        return result

    if not manifests:
        result["message"] = "No manifests found — nothing to undo."
        return result

    manifest_path = manifests[0]

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        result["errors"].append(f"Failed to read manifest: {exc}")
        return result

    operation = manifest.get("operation", "unknown")
    result["operation"] = operation
    op_result = manifest.get("result", {})

    # ── Undo: archive / archive_and_delete ────────────────────────────────
    if operation in ("archive", "archive_and_delete"):
        archive_path = Path(op_result.get("archive_path", ""))
        if not archive_path.exists():
            result["errors"].append(
                f"Archive no longer exists: {archive_path}"
            )
            return result

        original_files = manifest.get("files", [])

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Build a mapping from arcname → original path.
                # Fall back to extracting into ARCHIVE_DIR if no mapping.
                arc_names = zf.namelist()

                if len(arc_names) == len(original_files):
                    for arcname, orig in zip(arc_names, original_files):
                        orig = Path(orig)
                        orig.parent.mkdir(parents=True, exist_ok=True)
                        # Extract to temp, then move
                        extracted = zf.extract(arcname, path=ARCHIVE_DIR)
                        shutil.move(extracted, str(orig))
                else:
                    # Best-effort: extract into archive dir
                    zf.extractall(path=ARCHIVE_DIR)

            # Remove the archive
            archive_path.unlink(missing_ok=True)
            result["success"] = True
            result["message"] = (
                f"Reversed '{operation}': restored "
                f"{len(original_files)} file(s) and removed archive."
            )
        except (zipfile.BadZipFile, OSError) as exc:
            result["errors"].append(f"Failed to extract archive: {exc}")

    # ── Undo: move ────────────────────────────────────────────────────────
    elif operation == "move":
        moves = op_result.get("moves", [])
        restored = 0

        for move in moves:
            src = Path(move.get("destination", ""))
            dst = Path(move.get("source", ""))

            if not src.exists():
                result["errors"].append(
                    f"Moved file no longer at destination: {src}"
                )
                continue

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                restored += 1
            except OSError as exc:
                result["errors"].append(f"Failed to restore {src}: {exc}")

        result["success"] = restored == len(moves)
        result["message"] = f"Restored {restored}/{len(moves)} file(s)."

    else:
        result["errors"].append(f"Unsupported undo operation: {operation}")

    # ── Clean up manifest (rename so it won't be picked again) ────────────
    if result["success"]:
        try:
            undone_path = manifest_path.with_suffix(".undone.json")
            manifest_path.rename(undone_path)
        except OSError:
            pass  # Non-critical

    _write_log({
        "operation": "undo_last_operation",
        "timestamp": datetime.now().isoformat(),
        **result,
    })

    return result
