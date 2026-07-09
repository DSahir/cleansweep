"""
CleanSweep — macOS System Optimizer
Configuration and constants for all scanner/cleaner modules.
"""
import os
import sys
from pathlib import Path

# ─── Base Paths ───────────────────────────────────────────────────────────────

HOME = Path.home()
LIBRARY = HOME / "Library"  # Retain standard Library path reference

# ─── Cache & Temp Locations ───────────────────────────────────────────────────

CACHE_LOCATIONS = {}
BROWSER_CACHE_LOCATIONS = {}
TEMP_LOCATIONS = []
PACKAGE_MANAGER_CACHES = {}
PROTECTED_PATHS = {
    HOME / "Documents",
    HOME / "Desktop",
    HOME / "Pictures",
    HOME / "Music",
    HOME / "Movies",
    HOME / "Downloads",
}

if sys.platform == "darwin":
    CACHE_LOCATIONS = {
        "User Caches": LIBRARY / "Caches",
        "System Caches": Path("/Library/Caches"),
        "System Temp": Path("/tmp"),
        "Private Temp": Path("/private/tmp"),
        "User Logs": LIBRARY / "Logs",
        "Xcode Derived Data": LIBRARY / "Developer" / "Xcode" / "DerivedData",
        "Xcode Archives": LIBRARY / "Developer" / "Xcode" / "Archives",
        "CocoaPods Cache": LIBRARY / "Caches" / "CocoaPods",
        "Homebrew Cache": LIBRARY / "Caches" / "Homebrew",
        "Spotify Cache": LIBRARY / "Application Support" / "Spotify" / "PersistentCache",
    }
    BROWSER_CACHE_LOCATIONS = {
        "Chrome Cache": LIBRARY / "Caches" / "Google" / "Chrome",
        "Safari Cache": LIBRARY / "Caches" / "com.apple.Safari",
        "Firefox Cache": LIBRARY / "Caches" / "Firefox",
        "Edge Cache": LIBRARY / "Caches" / "Microsoft Edge",
    }
    TEMP_LOCATIONS = [
        Path("/tmp"),
        Path("/private/tmp"),
        Path("/var/folders"),
    ]
    PACKAGE_MANAGER_CACHES = {
        "npm Cache": HOME / ".npm" / "_cacache",
        "yarn Cache": LIBRARY / "Caches" / "Yarn",
        "pip Cache": LIBRARY / "Caches" / "pip",
        "pip3 Cache": HOME / ".cache" / "pip",
        "conda Cache": HOME / ".conda" / "pkgs",
        "gem Cache": LIBRARY / "Caches" / "gem",
        "cargo Cache": HOME / ".cargo" / "registry",
        "go Cache": HOME / "Library" / "Caches" / "go-build",
        "gradle Cache": HOME / ".gradle" / "caches",
        "maven Cache": HOME / ".m2" / "repository",
    }
    PROTECTED_PATHS.update({
        Path("/System"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/Applications"),
        LIBRARY / "Preferences",
        LIBRARY / "Keychains",
        LIBRARY / "Mail",
        HOME / "Applications",
    })
elif sys.platform == "win32":
    LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", str(HOME / "AppData" / "Local")))
    APPDATA = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming")))
    TEMP_DIR = Path(os.environ.get("TEMP", str(HOME / "AppData" / "Local" / "Temp")))
    SYSTEMROOT = Path(os.environ.get("SystemRoot", "C:\\Windows"))
    PROGRAMFILES = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
    PROGRAMFILES_X86 = Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))

    CACHE_LOCATIONS = {
        "User Temp": TEMP_DIR,
        "System Temp": SYSTEMROOT / "Temp",
    }
    BROWSER_CACHE_LOCATIONS = {
        "Chrome Cache": LOCALAPPDATA / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        "Edge Cache": LOCALAPPDATA / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
        "Firefox Cache": LOCALAPPDATA / "Mozilla" / "Firefox" / "Profiles",
    }
    TEMP_LOCATIONS = [
        TEMP_DIR,
        SYSTEMROOT / "Temp",
    ]
    PACKAGE_MANAGER_CACHES = {
        "npm Cache": LOCALAPPDATA / "npm-cache" / "_cacache",
        "yarn Cache": LOCALAPPDATA / "Yarn" / "Cache",
        "pip Cache": LOCALAPPDATA / "pip" / "cache",
        "conda Cache": HOME / ".conda" / "pkgs",
        "gem Cache": HOME / ".gem",
        "cargo Cache": HOME / ".cargo" / "registry",
        "gradle Cache": HOME / ".gradle" / "caches",
        "maven Cache": HOME / ".m2" / "repository",
    }
    PROTECTED_PATHS.update({
        SYSTEMROOT,
        PROGRAMFILES,
        PROGRAMFILES_X86,
        Path("C:\\Users"),
    })
else:  # Linux / Unix
    CACHE_LOCATIONS = {
        "User Caches": HOME / ".cache",
        "System Temp": Path("/tmp"),
    }
    BROWSER_CACHE_LOCATIONS = {
        "Chrome Cache": HOME / ".config" / "google-chrome" / "Default" / "Cache",
        "Firefox Cache": HOME / ".mozilla" / "firefox",
    }
    TEMP_LOCATIONS = [
        Path("/tmp"),
        Path("/var/tmp"),
    ]
    PACKAGE_MANAGER_CACHES = {
        "npm Cache": HOME / ".npm" / "_cacache",
        "yarn Cache": HOME / ".cache" / "yarn",
        "pip Cache": HOME / ".cache" / "pip",
        "conda Cache": HOME / ".conda" / "pkgs",
        "cargo Cache": HOME / ".cargo" / "registry",
        "gradle Cache": HOME / ".gradle" / "caches",
        "maven Cache": HOME / ".m2" / "repository",
    }
    PROTECTED_PATHS.update({
        Path("/boot"),
        Path("/dev"),
        Path("/etc"),
        Path("/lib"),
        Path("/lib64"),
        Path("/proc"),
        Path("/sys"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
    })

PROTECTED_EXTENSIONS = {
    ".keychain", ".keychain-db", ".plist",
}

# ─── File Access Time Thresholds (days) ───────────────────────────────────────

ACCESS_TIME_TIERS = {
    "recent": 30,       # < 30 days
    "aging": 180,       # 30–180 days
    "old": 365,         # 180–365 days
    "stale": float("inf"),  # > 365 days
}

ACCESS_TIME_LABELS = {
    "recent": {"label": "Recently Used", "color": "#4ade80", "icon": "✅"},
    "aging": {"label": "Getting Old", "color": "#facc15", "icon": "⚠️"},
    "old": {"label": "Old Files", "color": "#fb923c", "icon": "🟠"},
    "stale": {"label": "Stale / Unused", "color": "#f87171", "icon": "🔴"},
}

# ─── Default Scan Directories ────────────────────────────────────────────────

DEFAULT_SCAN_DIRS = [
    HOME / "Desktop",
    HOME / "Downloads",
    HOME / "Documents",
]

# ─── Archive Settings ────────────────────────────────────────────────────────

ARCHIVE_DIR = HOME / "Archives" / "CleanSweep"

# ─── Environment Detection Paths ─────────────────────────────────────────────

PYTHON_LOCATIONS = []
JAVA_LOCATIONS = []
NODE_LOCATIONS = []
RUBY_LOCATIONS = []
DOCKER_PATHS = {}

if sys.platform == "darwin":
    PYTHON_LOCATIONS = [
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
        Path("/opt/homebrew/bin/python3"),
        HOME / ".pyenv" / "versions",
        HOME / "anaconda3",
        HOME / "miniconda3",
        Path("/opt/homebrew/Cellar/python*"),
    ]
    JAVA_LOCATIONS = [
        Path("/Library/Java/JavaVirtualMachines"),
        Path("/usr/libexec/java_home"),
    ]
    NODE_LOCATIONS = [
        Path("/usr/local/bin/node"),
        Path("/opt/homebrew/bin/node"),
        HOME / ".nvm" / "versions" / "node",
        HOME / ".volta",
        HOME / ".fnm" / "node-versions",
    ]
    RUBY_LOCATIONS = [
        Path("/usr/bin/ruby"),
        Path("/usr/local/bin/ruby"),
        Path("/opt/homebrew/bin/ruby"),
        HOME / ".rbenv" / "versions",
        HOME / ".rvm" / "rubies",
    ]
    DOCKER_PATHS = {
        "docker_data": HOME / "Library" / "Containers" / "com.docker.docker",
        "docker_desktop": Path("/Applications/Docker.app"),
    }
elif sys.platform == "win32":
    # Typical windows paths
    LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", str(HOME / "AppData" / "Local")))
    PROGRAMFILES = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
    
    PYTHON_LOCATIONS = [
        LOCALAPPDATA / "Programs" / "Python",
        Path("C:\\Python39"),
        Path("C:\\Python310"),
        Path("C:\\Python311"),
        Path("C:\\Python312"),
    ]
    JAVA_LOCATIONS = [
        PROGRAMFILES / "Java",
    ]
    NODE_LOCATIONS = [
        PROGRAMFILES / "nodejs",
        HOME / "AppData" / "Roaming" / "npm",
    ]
    RUBY_LOCATIONS = [
        Path("C:\\Ruby27-x64"),
        Path("C:\\Ruby30-x64"),
        Path("C:\\Ruby31-x64"),
        Path("C:\\Ruby32-x64"),
    ]
    DOCKER_PATHS = {
        "docker_desktop": Path("C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"),
    }
else:  # Linux
    PYTHON_LOCATIONS = [
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
        HOME / ".pyenv" / "versions",
    ]
    JAVA_LOCATIONS = [
        Path("/usr/lib/jvm"),
    ]
    NODE_LOCATIONS = [
        Path("/usr/bin/node"),
        Path("/usr/local/bin/node"),
        HOME / ".nvm" / "versions" / "node",
    ]
    RUBY_LOCATIONS = [
        Path("/usr/bin/ruby"),
        HOME / ".rbenv" / "versions",
    ]

# ─── iCloud Paths ─────────────────────────────────────────────────────────────

ICLOUD_DRIVE = HOME / "Library" / "Mobile Documents" if sys.platform == "darwin" else None
ICLOUD_CONTAINER = HOME / "Library" / "Mobile Documents" / "com~apple~CloudDocs" if sys.platform == "darwin" else None

# ─── File Categories ─────────────────────────────────────────────────────────

FILE_CATEGORIES = {
    "Documents": {
        "extensions": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages",
                       ".md", ".tex", ".epub", ".mobi"},
        "icon": "📄",
        "color": "#3B82F6",
    },
    "Spreadsheets": {
        "extensions": {".xls", ".xlsx", ".csv", ".numbers", ".ods", ".tsv"},
        "icon": "📊",
        "color": "#10B981",
    },
    "Presentations": {
        "extensions": {".ppt", ".pptx", ".key", ".odp"},
        "icon": "📽️",
        "color": "#EC4899",
    },
    "Images": {
        "extensions": {".jpg", ".jpeg", ".png", ".gif", ".svg", ".heic", ".heif",
                       ".raw", ".bmp", ".tiff", ".tif", ".webp", ".ico", ".psd",
                       ".cr2", ".nef", ".arw"},
        "icon": "🖼️",
        "color": "#F59E0B",
    },
    "Videos": {
        "extensions": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm",
                       ".m4v", ".mpg", ".mpeg", ".3gp"},
        "icon": "🎬",
        "color": "#EF4444",
    },
    "Audio": {
        "extensions": {".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".wma",
                       ".aiff", ".alac", ".opus"},
        "icon": "🎵",
        "color": "#8B5CF6",
    },
    "Code": {
        "extensions": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                       ".h", ".hpp", ".go", ".rs", ".swift", ".kt", ".rb", ".php",
                       ".cs", ".r", ".scala", ".lua", ".sh", ".bash", ".zsh",
                       ".html", ".css", ".scss", ".sass", ".less", ".sql", ".vue",
                       ".svelte"},
        "icon": "💻",
        "color": "#06B6D4",
    },
    "Archives": {
        "extensions": {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z",
                       ".dmg", ".iso", ".pkg", ".deb", ".rpm", ".tgz"},
        "icon": "📦",
        "color": "#A855F7",
    },
    "Data": {
        "extensions": {".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                       ".conf", ".env", ".db", ".sqlite", ".sqlite3", ".sql"},
        "icon": "🗄️",
        "color": "#14B8A6",
    },
    "Design": {
        "extensions": {".fig", ".sketch", ".ai", ".xd", ".indd", ".afdesign",
                       ".afphoto"},
        "icon": "🎨",
        "color": "#F43F5E",
    },
    "Fonts": {
        "extensions": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
        "icon": "🔤",
        "color": "#64748B",
    },
    "Executables": {
        "extensions": {".app", ".exe", ".msi", ".bin", ".command", ".sh"},
        "icon": "⚙️",
        "color": "#6366F1",
    },
}

# Build reverse lookup: extension → category
EXTENSION_TO_CATEGORY = {}
for category, info in FILE_CATEGORIES.items():
    for ext in info["extensions"]:
        EXTENSION_TO_CATEGORY[ext] = category

# ─── Size Formatting ─────────────────────────────────────────────────────────

def format_size(size_bytes):
    """Format bytes into human-readable string."""
    if size_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def get_dir_size(path):
    """Calculate total size of a directory recursively."""
    total = 0
    try:
        if path.is_file():
            return path.stat().st_size
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return total

# ─── Flask Config ─────────────────────────────────────────────────────────────

FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5051
FLASK_DEBUG = True

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_DIR = HOME / ".cleansweep" / "logs"
MANIFEST_DIR = HOME / ".cleansweep" / "manifests"
