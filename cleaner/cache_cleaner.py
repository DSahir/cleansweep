"""
CleanSweep — Cache Cleaner
Safe cache cleaning operations with dry-run support, protected-path
enforcement, and structured JSON logging of every operation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
from datetime import datetime
from pathlib import Path

from config import (
    PROTECTED_PATHS,
    PROTECTED_EXTENSIONS,
    LOG_DIR,
    format_size,
    get_dir_size,
    CACHE_LOCATIONS,
    BROWSER_CACHE_LOCATIONS,
    PACKAGE_MANAGER_CACHES,
    TEMP_LOCATIONS,
)


# ─── Safety Helpers ──────────────────────────────────────────────────────────


def _is_inside_allowed_dirs(path: Path) -> bool:
    """Verify that the path is actually inside one of the permitted temp/cache root folders."""
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return False

    allowed_roots = []
    
    # Add CACHE_LOCATIONS
    for r in CACHE_LOCATIONS.values():
        if r:
            allowed_roots.append(Path(r))

    # Add BROWSER_CACHE_LOCATIONS
    for r in BROWSER_CACHE_LOCATIONS.values():
        if r:
            allowed_roots.append(Path(r))

    # Add PACKAGE_MANAGER_CACHES
    for r in PACKAGE_MANAGER_CACHES.values():
        if r:
            allowed_roots.append(Path(r))

    # Add TEMP_LOCATIONS
    for r in TEMP_LOCATIONS:
        if r:
            allowed_roots.append(Path(r))

    for root in allowed_roots:
        try:
            root_resolved = root.resolve()
            if resolved == root_resolved or root_resolved in resolved.parents:
                return True
        except (OSError, ValueError):
            continue

    return False


def _is_protected(path: Path) -> bool:
    """Return True if *path* (or any of its parents) falls inside a
    protected directory or carries a protected extension."""
    resolved = path.resolve()

    # Check against every protected path
    for protected in PROTECTED_PATHS:
        try:
            protected_resolved = protected.resolve()
            if resolved == protected_resolved or protected_resolved in resolved.parents:
                return True
        except (OSError, ValueError):
            continue

    # Check extension
    if path.suffix.lower() in PROTECTED_EXTENSIONS:
        return True

    return False


def _ensure_log_dir() -> Path:
    """Create the log directory if it doesn't already exist and return it."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return LOG_DIR


def _write_log(log_data: dict) -> str:
    """Persist *log_data* as a JSON file inside LOG_DIR.
    Returns the absolute path to the log file."""
    try:
        log_dir = _ensure_log_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"clean_{timestamp}.json"

        # Avoid overwriting a file created in the same second
        counter = 1
        while log_path.exists():
            log_path = log_dir / f"clean_{timestamp}_{counter}.json"
            counter += 1

        with open(log_path, "w", encoding="utf-8") as fh:
            json.dump(log_data, fh, indent=2, default=str)

        return str(log_path)
    except OSError:
        return ""


# ─── Core Cleaning ───────────────────────────────────────────────────────────


def clean_cache(cache_path, dry_run: bool = True) -> dict:
    """Delete the *contents* of a cache directory without removing the
    directory itself.

    Parameters
    ----------
    cache_path : str | Path
        Path to the cache directory whose contents should be removed.
    dry_run : bool, optional
        When ``True`` (default) no files are actually deleted; the
        function only reports what *would* be removed.

    Returns
    -------
    dict
        {path, items_removed, bytes_freed, bytes_freed_formatted,
         errors, dry_run}
    """
    cache_path = Path(cache_path)
    result = {
        "path": str(cache_path),
        "items_removed": 0,
        "bytes_freed": 0,
        "bytes_freed_formatted": "0 B",
        "errors": [],
        "dry_run": dry_run,
    }

    # ── Validation ────────────────────────────────────────────────────────
    if not cache_path.exists():
        result["errors"].append(f"Path does not exist: {cache_path}")
        return result

    if not cache_path.is_dir():
        result["errors"].append(f"Path is not a directory: {cache_path}")
        return result

    if not _is_inside_allowed_dirs(cache_path):
        result["errors"].append(f"Path is not within permitted cache locations: {cache_path}")
        return result

    if _is_protected(cache_path):
        result["errors"].append(f"Path is protected: {cache_path}")
        return result

    # ── Walk contents ─────────────────────────────────────────────────────
    try:
        entries = list(cache_path.iterdir())
    except PermissionError as exc:
        result["errors"].append(f"Permission denied listing {cache_path}: {exc}")
        return result

    for entry in entries:
        if _is_protected(entry):
            result["errors"].append(f"Skipped protected item: {entry}")
            continue

        try:
            entry_size = get_dir_size(entry) if entry.is_dir() else entry.stat().st_size
        except (PermissionError, OSError):
            entry_size = 0

        if dry_run:
            result["items_removed"] += 1
            result["bytes_freed"] += entry_size
        else:
            try:
                if entry.is_dir() and not entry.is_symlink():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
                result["items_removed"] += 1
                result["bytes_freed"] += entry_size
            except PermissionError as exc:
                result["errors"].append(
                    f"Permission denied deleting {entry}: {exc}"
                )
            except OSError as exc:
                result["errors"].append(f"OS error deleting {entry}: {exc}")

    result["bytes_freed_formatted"] = format_size(result["bytes_freed"])

    # ── Log ───────────────────────────────────────────────────────────────
    log_entry = {
        "operation": "clean_cache",
        "timestamp": datetime.now().isoformat(),
        **result,
    }
    _write_log(log_entry)

    return result


# ─── Category / Bulk Cleaning ────────────────────────────────────────────────


def clean_category(
    category_name: str,
    cache_entries: dict,
    dry_run: bool = True,
) -> list:
    """Clean every cache path listed for a single category.

    Parameters
    ----------
    category_name : str
        Human-readable label for logging (e.g. ``"Browser Caches"``).
    cache_entries : dict
        Mapping of ``{label: path}`` for each cache in the category.
    dry_run : bool, optional
        Forwarded to :func:`clean_cache`.

    Returns
    -------
    list[dict]
        One result dict per cache entry.
    """
    results = []
    for label, path in cache_entries.items():
        result = clean_cache(path, dry_run=dry_run)
        result["category"] = category_name
        result["label"] = label
        results.append(result)
    return results


def clean_all_caches(scan_results: dict, dry_run: bool = True) -> dict:
    """Clean every category present in a scan result produced by the
    scanner modules.

    Parameters
    ----------
    scan_results : dict
        Mapping of ``{category_name: {label: path, ...}, ...}``.
    dry_run : bool, optional
        Forwarded to :func:`clean_cache`.

    Returns
    -------
    dict
        Summary with total_items_removed, total_bytes_freed,
        total_bytes_freed_formatted, categories_cleaned, all_results,
        errors, and dry_run.
    """
    summary = {
        "total_items_removed": 0,
        "total_bytes_freed": 0,
        "total_bytes_freed_formatted": "0 B",
        "categories_cleaned": 0,
        "all_results": [],
        "errors": [],
        "dry_run": dry_run,
    }

    for category_name, cache_entries in scan_results.items():
        # Accept both dict-of-paths and list-of-paths
        if isinstance(cache_entries, dict):
            cat_results = clean_category(category_name, cache_entries, dry_run=dry_run)
        elif isinstance(cache_entries, list):
            cat_results = []
            for entry in cache_entries:
                path = entry if isinstance(entry, (str, Path)) else entry.get("path", "")
                res = clean_cache(path, dry_run=dry_run)
                res["category"] = category_name
                cat_results.append(res)
        else:
            summary["errors"].append(
                f"Unexpected format for category '{category_name}'"
            )
            continue

        summary["categories_cleaned"] += 1
        for res in cat_results:
            summary["total_items_removed"] += res.get("items_removed", 0)
            summary["total_bytes_freed"] += res.get("bytes_freed", 0)
            summary["errors"].extend(res.get("errors", []))
        summary["all_results"].extend(cat_results)

    summary["total_bytes_freed_formatted"] = format_size(
        summary["total_bytes_freed"]
    )

    # ── Aggregate log ─────────────────────────────────────────────────────
    log_entry = {
        "operation": "clean_all_caches",
        "timestamp": datetime.now().isoformat(),
        "total_items_removed": summary["total_items_removed"],
        "total_bytes_freed": summary["total_bytes_freed"],
        "total_bytes_freed_formatted": summary["total_bytes_freed_formatted"],
        "categories_cleaned": summary["categories_cleaned"],
        "dry_run": dry_run,
        "errors": summary["errors"],
    }
    _write_log(log_entry)

    return summary
