"""
CleanSweep — File Access-Time Analyzer
Classifies files by last-access time into freshness tiers and produces
human-readable summaries.  Uses ``os.stat`` (atime) with macOS ``mdls``
(kMDItemLastUsedDate) as a richer fallback when available.
"""

import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ACCESS_TIME_TIERS, ACCESS_TIME_LABELS, format_size


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _human_time_ago(seconds_ago: float) -> str:
    """Convert seconds-since-last-access to a human string like '3 months ago'."""
    minutes = seconds_ago / 60
    hours = minutes / 60
    days = hours / 24
    months = days / 30.44
    years = days / 365.25

    if days < 1:
        if hours < 1:
            return f"{int(minutes)} minute{'s' if int(minutes) != 1 else ''} ago"
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''} ago"
    if days < 30:
        return f"{int(days)} day{'s' if int(days) != 1 else ''} ago"
    if months < 12:
        return f"{int(months)} month{'s' if int(months) != 1 else ''} ago"
    return f"{years:.1f} year{'s' if years != 1 else ''} ago"


def _mdls_last_used(filepath: str) -> float | None:
    """
    Ask Spotlight for kMDItemLastUsedDate.  Returns a Unix timestamp or None.
    """
    try:
        result = subprocess.run(
            ["mdls", "-name", "kMDItemLastUsedDate", filepath],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip()
        # Typical output:  kMDItemLastUsedDate = 2024-12-01 08:30:00 +0000
        if "(null)" in line or "=" not in line:
            return None
        date_str = line.split("=", 1)[1].strip()
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        return dt.timestamp()
    except Exception:
        return None


def _get_last_accessed(filepath: str) -> float:
    """
    Best-effort last-access timestamp.

    Priority:
        1. macOS Spotlight kMDItemLastUsedDate (real "last opened" date)
        2. os.stat st_atime
    """
    mdls_ts = _mdls_last_used(filepath)
    if mdls_ts is not None:
        return mdls_ts
    try:
        return os.stat(filepath).st_atime
    except (OSError, PermissionError):
        return 0.0


# ─── Tier Classification ─────────────────────────────────────────────────────

def get_tier(days_since_access: float) -> str:
    """
    Classify a file into a freshness tier.

    Parameters
    ----------
    days_since_access : float
        Number of days since the file was last accessed.

    Returns
    -------
    str
        One of 'recent', 'aging', 'old', 'stale'.
    """
    # ACCESS_TIME_TIERS is ordered: recent < aging < old < stale(inf)
    for tier_name, threshold in ACCESS_TIME_TIERS.items():
        if days_since_access < threshold:
            return tier_name
    return "stale"


# ─── Directory Scanner ───────────────────────────────────────────────────────

def scan_directory(directory: str, min_size_mb: float = 0) -> list[dict]:
    """
    Recursively scan *directory* and return file-access metadata.

    Parameters
    ----------
    directory : str | Path
        Root directory to scan.
    min_size_mb : float
        Ignore files smaller than this (megabytes).

    Returns
    -------
    list[dict]
        Sorted by ``last_accessed`` ascending (oldest first).
        Each dict: path, name, size, size_formatted, extension,
        last_accessed, last_modified, last_accessed_ago, tier.
    """
    directory = Path(directory).expanduser().resolve()
    if not directory.exists():
        return []

    now = time.time()
    min_size_bytes = min_size_mb * 1024 * 1024
    results: list[dict] = []

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            filepath = os.path.join(root, fname)
            try:
                stat = os.stat(filepath)
                if stat.st_size < min_size_bytes:
                    continue
                # Skip symlinks
                if os.path.islink(filepath):
                    continue

                last_accessed = _get_last_accessed(filepath)
                last_modified = stat.st_mtime
                seconds_ago = max(now - last_accessed, 0)
                days_ago = seconds_ago / 86400

                results.append({
                    "path": filepath,
                    "name": fname,
                    "size": stat.st_size,
                    "size_formatted": format_size(stat.st_size),
                    "extension": os.path.splitext(fname)[1].lower(),
                    "last_accessed": last_accessed,
                    "last_modified": last_modified,
                    "last_accessed_ago": _human_time_ago(seconds_ago),
                    "tier": get_tier(days_ago),
                })
            except (PermissionError, OSError):
                continue

    # Oldest first
    results.sort(key=lambda f: f["last_accessed"])
    return results


# ─── Stale-Files Summary ─────────────────────────────────────────────────────

def get_stale_files_summary(directory: str) -> dict:
    """
    Per-tier summary of file counts and total sizes.

    Returns
    -------
    dict
        tiers : dict  — for each tier: count, total_size, total_size_formatted,
                         label, color, icon
        total_files : int
        total_size : int
        total_size_formatted : str
    """
    files = scan_directory(directory)

    tiers: dict[str, dict] = {}
    for tier_name, meta in ACCESS_TIME_LABELS.items():
        tiers[tier_name] = {
            "count": 0,
            "total_size": 0,
            "total_size_formatted": "0 B",
            "label": meta["label"],
            "color": meta["color"],
            "icon": meta["icon"],
        }

    total_size = 0
    for f in files:
        t = f["tier"]
        if t in tiers:
            tiers[t]["count"] += 1
            tiers[t]["total_size"] += f["size"]
        total_size += f["size"]

    # Final formatting pass
    for tier in tiers.values():
        tier["total_size_formatted"] = format_size(tier["total_size"])

    return {
        "tiers": tiers,
        "total_files": len(files),
        "total_size": total_size,
        "total_size_formatted": format_size(total_size),
    }


# ─── CLI convenience ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    target = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Downloads")
    summary = get_stale_files_summary(target)
    print(json.dumps(summary, indent=2))
