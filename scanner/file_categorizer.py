"""
CleanSweep — File Categorizer
Scans and organizes files into categorized folders based on extension mappings.
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EXTENSION_TO_CATEGORY, format_size

def scan_and_categorize(directory: str) -> list:
    """Scan files directly in the directory and categorize them."""
    path = Path(directory).expanduser().resolve()
    results = []
    
    if path.exists():
        try:
            for entry in path.iterdir():
                if entry.is_file() and not entry.is_symlink() and not entry.name.startswith("."):
                    stat = entry.stat()
                    ext = entry.suffix.lower()
                    cat = EXTENSION_TO_CATEGORY.get(ext, "Unknown")
                    results.append({
                        "name": entry.name,
                        "path": str(entry),
                        "size": stat.st_size,
                        "size_formatted": format_size(stat.st_size),
                        "category": cat,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        except (PermissionError, OSError):
            pass

    return results

def generate_organization_plan(directory: str) -> list:
    """Generate a plan to move uncategorized files into category subdirectories."""
    path = Path(directory).expanduser().resolve()
    plan = []
    
    if path.exists():
        try:
            for entry in path.iterdir():
                if entry.is_file() and not entry.is_symlink() and not entry.name.startswith("."):
                    ext = entry.suffix.lower()
                    cat = EXTENSION_TO_CATEGORY.get(ext, "Unknown")
                    if cat != "Unknown":
                        dest_dir = path / cat
                        dest_file = dest_dir / entry.name
                        plan.append({
                            "file": str(entry),
                            "filename": entry.name,
                            "size": entry.stat().st_size,
                            "size_formatted": format_size(entry.stat().st_size),
                            "category": cat,
                            "source": str(entry),
                            "destination": str(dest_file)
                        })
        except (PermissionError, OSError):
            pass

    return plan

def execute_organization(plan: list, dry_run: bool = True) -> dict:
    """Execute the generated organization plan."""
    results = []
    total_moved = 0
    total_freed = 0  # not strictly freed, just kept for response compatibility
    
    for item in plan:
        source = Path(item["source"])
        destination = Path(item["destination"])
        res = {"source": str(source), "destination": str(destination), "success": False}
        
        try:
            if source.exists():
                if not dry_run:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(destination))
                res["success"] = True
                total_moved += 1
            else:
                res["error"] = "Source file does not exist"
        except Exception as e:
            res["error"] = str(e)
        
        results.append(res)
        
    return {
        "results": results,
        "total_moved": total_moved,
        "dry_run": dry_run
    }

def assign_category(file_path: str, category: str) -> dict:
    """Manually assign a file to a specific category folder."""
    src = Path(file_path).resolve()
    if not src.exists():
        return {"success": False, "error": f"File {file_path} does not exist"}
        
    dest_dir = src.parent / category
    dest = dest_dir / src.name
    
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return {"success": True, "source": str(src), "destination": str(dest)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_unknown_files(directory: str) -> list:
    """Return a list of file paths that do not map to any known category."""
    path = Path(directory).expanduser().resolve()
    unknown = []
    
    if path.exists():
        try:
            for entry in path.iterdir():
                if entry.is_file() and not entry.is_symlink() and not entry.name.startswith("."):
                    ext = entry.suffix.lower()
                    cat = EXTENSION_TO_CATEGORY.get(ext, "Unknown")
                    if cat == "Unknown":
                        unknown.append(str(entry))
        except (PermissionError, OSError):
            pass

    return unknown
