"""
CleanSweep — macOS System Optimizer
Flask application entry point with REST API endpoints.
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    LOG_DIR, MANIFEST_DIR, ARCHIVE_DIR, format_size
)
from scanner.cache_scanner import scan_all_caches, get_cache_summary
from scanner.access_analyzer import scan_directory, get_stale_files_summary
from scanner.env_detector import detect_all_environments
from scanner.storage_analyzer import (
    get_disk_usage, get_icloud_usage,
    get_top_directories, get_storage_by_category
)
from scanner.file_categorizer import (
    scan_and_categorize, generate_organization_plan,
    get_unknown_files, execute_organization, assign_category
)
from cleaner.cache_cleaner import clean_cache, clean_category, clean_all_caches
from cleaner.file_archiver import archive_files, archive_and_delete, move_files
from cleaner.env_cleaner import (
    remove_python_version, remove_java_version, remove_node_version,
    docker_prune, homebrew_cleanup, remove_xcode_derived_data
)

# ─── Setup ────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Ensure directories exist
for d in [LOG_DIR, MANIFEST_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("cleansweep")

# ─── Page Routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")

# ─── System Stats API ────────────────────────────────────────────────────────

@app.route("/api/system/stats")
def system_stats():
    """Get basic system stats for the header bar."""
    try:
        import psutil
        disk = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        return jsonify({
            "disk_total": format_size(disk.total),
            "disk_used": format_size(disk.used),
            "disk_free": format_size(disk.free),
            "disk_percent": disk.percent,
            "memory_total": format_size(mem.total),
            "memory_used": format_size(mem.used),
            "memory_percent": mem.percent,
            "cpu_percent": cpu,
            "platform": "macOS",
        })
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Cache Module API ────────────────────────────────────────────────────────

@app.route("/api/cache/scan")
def cache_scan():
    """Scan all cache and temp file locations."""
    try:
        results = scan_all_caches()
        summary = get_cache_summary(results)
        return jsonify({"results": results, "summary": summary})
    except Exception as e:
        logger.error(f"Cache scan error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cache/clean", methods=["POST"])
def cache_clean():
    """Clean caches. Body: {category?: string, path?: string, dry_run?: bool}"""
    try:
        data = request.get_json(force=True) if request.data else {}
        dry_run = data.get("dry_run", True)
        category = data.get("category")
        cache_path = data.get("path")

        if cache_path:
            result = clean_cache(Path(cache_path), dry_run=dry_run)
            return jsonify(result)
        elif category:
            # Re-scan to get entries for this category
            scan = scan_all_caches()
            if category in scan:
                result = clean_category(category, scan[category], dry_run=dry_run)
                return jsonify({"results": result})
            return jsonify({"error": f"Unknown category: {category}"}), 400
        else:
            scan = scan_all_caches()
            result = clean_all_caches(scan, dry_run=dry_run)
            return jsonify(result)
    except Exception as e:
        logger.error(f"Cache clean error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Access Analyzer API ─────────────────────────────────────────────────────

@app.route("/api/access/scan")
def access_scan():
    """Scan directory for file access times. Query: ?dir=PATH&min_size=0"""
    try:
        directory = request.args.get("dir", str(Path.home() / "Downloads"))
        min_size = float(request.args.get("min_size", 0))
        files = scan_directory(directory, min_size_mb=min_size)
        summary = get_stale_files_summary(directory)
        return jsonify({"files": files, "summary": summary, "directory": directory})
    except Exception as e:
        logger.error(f"Access scan error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/access/archive", methods=["POST"])
def access_archive():
    """Archive selected files. Body: {files: [path, ...], delete_originals?: bool}"""
    try:
        data = request.get_json(force=True)
        files = data.get("files", [])
        delete_originals = data.get("delete_originals", False)

        if not files:
            return jsonify({"error": "No files specified"}), 400

        if delete_originals:
            result = archive_and_delete(files)
        else:
            result = archive_files(files)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Archive error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/access/delete", methods=["POST"])
def access_delete():
    """Delete selected files. Body: {files: [path, ...]}"""
    try:
        data = request.get_json(force=True)
        files = data.get("files", [])
        if not files:
            return jsonify({"error": "No files specified"}), 400

        results = []
        total_freed = 0
        for f in files:
            p = Path(f)
            try:
                size = p.stat().st_size if p.exists() else 0
                p.unlink()
                total_freed += size
                results.append({"path": f, "deleted": True, "size": size})
            except Exception as e:
                results.append({"path": f, "deleted": False, "error": str(e)})

        return jsonify({
            "results": results,
            "total_freed": total_freed,
            "total_freed_formatted": format_size(total_freed),
        })
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Environments API ────────────────────────────────────────────────────────

@app.route("/api/envs/scan")
def envs_scan():
    """Detect all installed language environments."""
    try:
        results = detect_all_environments()
        return jsonify(results)
    except Exception as e:
        logger.error(f"Env scan error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/envs/clean", methods=["POST"])
def envs_clean():
    """Clean an environment. Body: {type: string, path?: string, prune_type?: string, dry_run?: bool}"""
    try:
        data = request.get_json(force=True)
        env_type = data.get("type")
        path = data.get("path")
        dry_run = data.get("dry_run", True)

        if env_type == "python" and path:
            result = remove_python_version(path, dry_run=dry_run)
        elif env_type == "java" and path:
            result = remove_java_version(path, dry_run=dry_run)
        elif env_type == "node" and path:
            result = remove_node_version(path, dry_run=dry_run)
        elif env_type == "docker":
            prune_type = data.get("prune_type", "all")
            result = docker_prune(prune_type=prune_type, dry_run=dry_run)
        elif env_type == "homebrew":
            result = homebrew_cleanup(dry_run=dry_run)
        elif env_type == "xcode":
            result = remove_xcode_derived_data(dry_run=dry_run)
        else:
            return jsonify({"error": f"Unknown env type: {env_type}"}), 400

        return jsonify(result)
    except Exception as e:
        logger.error(f"Env clean error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Storage API ──────────────────────────────────────────────────────────────

@app.route("/api/storage/scan")
def storage_scan():
    """Get comprehensive storage analysis."""
    try:
        disk = get_disk_usage()
        icloud = get_icloud_usage()
        top_dirs = get_top_directories(Path.home(), limit=20)
        categories = get_storage_by_category()
        return jsonify({
            "disk": disk,
            "icloud": icloud,
            "top_directories": top_dirs,
            "categories": categories,
        })
    except Exception as e:
        logger.error(f"Storage scan error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── File Organizer API ──────────────────────────────────────────────────────

@app.route("/api/organizer/scan")
def organizer_scan():
    """Scan and categorize files. Query: ?dir=PATH"""
    try:
        directory = request.args.get("dir", str(Path.home() / "Downloads"))
        results = scan_and_categorize(directory)
        return jsonify({"results": results, "directory": directory})
    except Exception as e:
        logger.error(f"Organizer scan error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/organizer/plan")
def organizer_plan():
    """Generate organization plan. Query: ?dir=PATH"""
    try:
        directory = request.args.get("dir", str(Path.home() / "Downloads"))
        plan = generate_organization_plan(directory)
        return jsonify({"plan": plan, "directory": directory})
    except Exception as e:
        logger.error(f"Organizer plan error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/organizer/execute", methods=["POST"])
def organizer_execute():
    """Execute organization plan. Body: {plan: [...], dry_run?: bool}"""
    try:
        data = request.get_json(force=True)
        plan = data.get("plan", [])
        dry_run = data.get("dry_run", True)

        if not plan:
            return jsonify({"error": "No plan provided"}), 400

        result = execute_organization(plan, dry_run=dry_run)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Organizer execute error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/organizer/categorize", methods=["POST"])
def organizer_categorize():
    """Manually categorize a file. Body: {path: string, category: string}"""
    try:
        data = request.get_json(force=True)
        file_path = data.get("path")
        category = data.get("category")

        if not file_path or not category:
            return jsonify({"error": "path and category are required"}), 400

        result = assign_category(file_path, category)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Categorize error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Main ─────────────────────────────────────────────────────────────────────

import webbrowser
from threading import Timer

def open_browser():
    """Automatically open the default web browser to the local dashboard."""
    try:
        webbrowser.open_new(f"http://127.0.0.1:{FLASK_PORT}")
    except Exception as e:
        logger.error(f"Failed to open default web browser: {e}")

if __name__ == "__main__":
    logger.info("🧹 CleanSweep — macOS System Optimizer")
    logger.info(f"   Dashboard: http://localhost:{FLASK_PORT}")
    
    # Only trigger browser auto-open if not running in Vercel serverless environment
    if not os.environ.get("VERCEL") and not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()
        
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
