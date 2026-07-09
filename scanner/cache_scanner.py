"""
CleanSweep — Cache & Temp Scanner
Scans all macOS cache, temp, browser, and package-manager cache directories.
Returns JSON-serializable dicts suitable for the UI or API layer.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    CACHE_LOCATIONS,
    BROWSER_CACHE_LOCATIONS,
    TEMP_LOCATIONS,
    PACKAGE_MANAGER_CACHES,
    format_size,
    get_dir_size,
)

from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _count_items(path: Path) -> int:
    """Count files (non-symlink) inside *path* recursively."""
    count = 0
    try:
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    count += 1
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return count


def _scan_location(name: str, path: Path) -> dict:
    """
    Build a cache-entry dict for a single directory.

    Returns
    -------
    dict
        name, path, size, size_formatted, item_count, exists
    """
    path = Path(path)
    exists = path.exists()
    size = 0
    item_count = 0

    if exists:
        try:
            size = get_dir_size(path)
            item_count = _count_items(path)
        except (PermissionError, OSError):
            pass

    return {
        "name": name,
        "path": str(path),
        "size": size,
        "size_formatted": format_size(size),
        "item_count": item_count,
        "exists": exists,
    }


# Developer-environment caches that don't fit the other four categories.
_DEV_CACHES = {
    "Xcode Derived Data": CACHE_LOCATIONS.get(
        "Xcode Derived Data",
        Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData",
    ),
    "Xcode Archives": CACHE_LOCATIONS.get(
        "Xcode Archives",
        Path.home() / "Library" / "Developer" / "Xcode" / "Archives",
    ),
    "CocoaPods Cache": CACHE_LOCATIONS.get(
        "CocoaPods Cache",
        Path.home() / "Library" / "Caches" / "CocoaPods",
    ),
}

# Keys in CACHE_LOCATIONS that belong to the "user_caches" bucket.
_USER_CACHE_KEYS = {"User Caches", "User Logs", "Spotify Cache", "Homebrew Cache"}


# ─── Public API ───────────────────────────────────────────────────────────────

def scan_all_caches() -> dict:
    """
    Scan every known cache / temp location on the system.

    Returns
    -------
    dict
        Keys: user_caches, browser_caches, system_temp, package_caches,
        dev_caches.  Each value is a list of cache-entry dicts.
    """
    results = {
        "user_caches": [],
        "browser_caches": [],
        "system_temp": [],
        "package_caches": [],
        "dev_caches": [],
    }

    # ── User caches ──────────────────────────────────────────────────────
    for name, path in CACHE_LOCATIONS.items():
        if name in _DEV_CACHES:
            continue  # handled separately
        if name in _USER_CACHE_KEYS:
            results["user_caches"].append(_scan_location(name, path))

    # ── Browser caches ───────────────────────────────────────────────────
    for name, path in BROWSER_CACHE_LOCATIONS.items():
        results["browser_caches"].append(_scan_location(name, path))

    # ── System temp ──────────────────────────────────────────────────────
    for path in TEMP_LOCATIONS:
        results["system_temp"].append(_scan_location(str(path), path))

    # ── Package manager caches ───────────────────────────────────────────
    for name, path in PACKAGE_MANAGER_CACHES.items():
        results["package_caches"].append(_scan_location(name, path))

    # ── Developer caches ─────────────────────────────────────────────────
    for name, path in _DEV_CACHES.items():
        results["dev_caches"].append(_scan_location(name, path))

    return results


def get_cache_summary(all_caches=None) -> dict:
    """
    High-level summary across all cache categories.

    Returns
    -------
    dict
        total_size, total_size_formatted, count_by_category, top_10_largest
    """
    if all_caches is None:
        all_caches = scan_all_caches()

    total_size = 0
    count_by_category: dict[str, dict] = {}
    flat_entries: list[dict] = []

    for category, entries in all_caches.items():
        cat_size = 0
        cat_items = 0
        for entry in entries:
            cat_size += entry["size"]
            cat_items += entry["item_count"]
            flat_entries.append(entry)
        count_by_category[category] = {
            "size": cat_size,
            "size_formatted": format_size(cat_size),
            "item_count": cat_items,
            "location_count": len(entries),
        }
        total_size += cat_size

    # Top 10 largest individual cache dirs (descending by size)
    flat_entries.sort(key=lambda e: e["size"], reverse=True)
    top_10 = flat_entries[:10]

    return {
        "total_size": total_size,
        "total_size_formatted": format_size(total_size),
        "count_by_category": count_by_category,
        "top_10_largest": top_10,
    }


# ─── CLI convenience ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    summary = get_cache_summary()
    print(json.dumps(summary, indent=2))
