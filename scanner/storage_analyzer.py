"""
CleanSweep — Storage Analyzer
Analyzes disk usage, iCloud usage, top directories, and categories.
"""
import os
import sys
import psutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    HOME,
    ICLOUD_CONTAINER,
    DEFAULT_SCAN_DIRS,
    FILE_CATEGORIES,
    EXTENSION_TO_CATEGORY,
    format_size,
    get_dir_size,
)

def get_disk_usage() -> dict:
    """Get system disk usage."""
    disk = psutil.disk_usage("/")
    return {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent,
        "total_formatted": format_size(disk.total),
        "used_formatted": format_size(disk.used),
        "free_formatted": format_size(disk.free),
    }

def get_icloud_usage() -> dict:
    """Get iCloud storage usage based on the local cache directory."""
    path = ICLOUD_CONTAINER
    exists = path.exists()
    size = 0
    item_count = 0
    
    if exists:
        try:
            for p in path.rglob("*"):
                try:
                    if p.is_file() and not p.is_symlink():
                        size += p.stat().st_size
                        item_count += 1
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

    return {
        "exists": exists,
        "size": size,
        "size_formatted": format_size(size),
        "item_count": item_count,
    }

def get_top_directories(base_path: Path, limit: int = 20) -> list:
    """Find the top largest first-level subdirectories."""
    dirs = []
    if not base_path.exists():
        return dirs

    for entry in base_path.iterdir():
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith("."):
            try:
                # Calculating total size recursively
                size = get_dir_size(entry)
                dirs.append({
                    "name": entry.name,
                    "path": str(entry),
                    "size": size,
                    "size_formatted": format_size(size)
                })
            except (PermissionError, OSError):
                continue

    dirs.sort(key=lambda x: x["size"], reverse=True)
    return dirs[:limit]

def get_storage_by_category() -> dict:
    """Categorize files in DEFAULT_SCAN_DIRS by extension."""
    categories = {
        cat: {
            "size": 0, 
            "size_formatted": "0 B", 
            "count": 0, 
            "color": info["color"], 
            "icon": info["icon"]
        }
        for cat, info in FILE_CATEGORIES.items()
    }
    categories["Unknown"] = {
        "size": 0, 
        "size_formatted": "0 B", 
        "count": 0, 
        "color": "#94a3b8", 
        "icon": "❓"
    }
    
    for scan_dir in DEFAULT_SCAN_DIRS:
        if not scan_dir.exists():
            continue
        try:
            for p in scan_dir.rglob("*"):
                try:
                    if p.is_file() and not p.is_symlink() and not p.name.startswith("."):
                        ext = p.suffix.lower()
                        cat = EXTENSION_TO_CATEGORY.get(ext, "Unknown")
                        categories[cat]["size"] += p.stat().st_size
                        categories[cat]["count"] += 1
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

    for cat in categories:
        categories[cat]["size_formatted"] = format_size(categories[cat]["size"])

    return categories
