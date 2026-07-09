# 🧹 CleanSweep

<div align="center">
  <p><strong>A lightweight, cross-platform system optimizer and developer dashboard, optimized for macOS.</strong></p>
  
  <p>
    <a href="https://github.com/DSahir/cleansweep/releases">
      <img src="https://img.shields.io/github/v/release/DSahir/cleansweep?color=blue" alt="Release">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/github/license/DSahir/cleansweep?color=green" alt="License">
    </a>
    <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey" alt="Platform Support">
    <img src="https://img.shields.io/badge/offline-100%25-success" alt="Offline Status">
  </p>
</div>

---

## 🖥️ Product Preview

![CleanSweep Dashboard Mockup](assets/dashboard.png)

*The CleanSweep dashboard provides a dark, Vercel-inspired telemetry and cache scanning interface, run 100% locally and privately.*

---

## ⚙️ Architecture & Cloud Boundaries

CleanSweep operates in a hybrid, local-first configuration to ensure absolute data security:

- **Local Application (Primary):** The fully-functional, offline-first optimizer runs entirely on your host machine. The local Flask server communicates only with your browser loop at `http://localhost:5051`. **Your file paths and telemetry metrics never communicate with any external server.**
- **Hosted Cloud Preview (`cleansweep-blush.vercel.app`):** This serves as a read-only telemetry preview and documentation shell. For safety, folder scanning and cache deletion API endpoints are **disabled/mocked** in the hosted Vercel deployment.

### Capabilities Comparison

| Capability / Feature | Hosted Vercel Preview | Local Client (Homebrew / Python) |
| :--- | :--- | :--- |
| **Read/Write Filesystem Access** | ❌ Locked / Read-Only Sandbox | ✅ Local Host File Access |
| **File Scan Audits** | ❌ Disabled (Simulated Preview List) | ✅ Live Local Scanning |
| **System Caches Purge** | ❌ Blocked by Serverless Constraints | ✅ One-Click Active Deletion |
| **Host Telemetry (CPU/RAM/Disk)** | ⚠️ Simulated Mockup Stats | ✅ Real-Time Local Hooks |
| **Privacy & Offline Guarantee** | ✅ Static Shell (No local reads) | ✅ 100% Offline (No external connections) |

---

## 📦 Platform Support Matrix

| Platform OS | Support Status | Included Sweep Capabilities | Install Formats |
| :--- | :--- | :--- | :--- |
| **macOS** | 🥇 Primary / Full Support | Apple Developer Caches (Safari, Xcode DerivedData, Logs, Homebrew Cache) | Homebrew Formula (HEAD), Git Source |
| **Windows** | 🥈 Core Support | System temp directories, Chrome browser cache, Package manager cache (npm, Cargo, Pip) | Standalone .exe Package, Git Source |
| **Linux** | 🥉 Experimental Support | Command Line Interface (CLI) scan controls and Python package dependencies only | Git Source / CLI Only |

---

## 🚀 Installation & Launch

### Option 1: Install via Homebrew (Recommended for macOS)
To bypass macOS Gatekeeper security warnings completely, install CleanSweep from source using our Homebrew formula:

```bash
brew install --HEAD https://raw.githubusercontent.com/DSahir/cleansweep/main/cleansweep.rb
```

Once installed, launch the application anytime by typing:
```bash
cleansweep
```
Your browser will automatically open the local dashboard at `http://localhost:5051`.

---

### Option 2: Download Standalone Executable (Windows)
Download the standalone executable directly from the [Releases](https://github.com/DSahir/cleansweep/releases) section:
- **Windows**: Run `CleanSweep.exe` directly.

---

### Option 3: Run via Git & Python Terminal (For Developers)
1. **Clone the repository**:
   ```bash
   git clone https://github.com/DSahir/cleansweep.git
   cd cleansweep
   ```
2. **Setup virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Start the application**:
   ```bash
   python app.py
   ```
   Your browser will automatically open the dashboard at `http://localhost:5051`.

---

## 🔒 Security & Safety gates

CleanSweep implements a strict allowlist constraint system inside `cleaner/cache_cleaner.py`:
- **Path Resolution:** Every target path resolves absolute links via `Path.resolve()` to prevent parent path traversal hacks (`../../`).
- **Constrained Roots:** File scans are restricted to explicit configuration cache directories.
- **Explicit Exclusions:** Even if a path resides inside an allowlisted folder, CleanSweep explicitly skips files matching custom sensitive patterns:
  - System directories: `/System`, `/usr`, `/etc`, `/bin`, `/sbin`, `/Library/SystemProfiler`
  - Security/Access keys: `~/.ssh`, `~/.aws`, `.env` configurations
  - Hidden revision folders: `.git`, `.github` pipelines
- **What is Never Deleted:** Personal user directories (`Documents`, `Desktop`, `Downloads`, `Pictures`, `Music`, `Movies`) are fully ignored.
- **Dry-run verification:** CleanSweep compiles a safe manifest first. No files are modified until you review and confirm.
