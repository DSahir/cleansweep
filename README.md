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

---

## 📦 Platform Support Matrix

- **macOS (Primary / Fully Supported):** Full optimization suite, including Apple cache sweepers (Safari caches, Xcode log folders, and DerivedData) and one-click Homebrew cleanups.
- **Windows (Supported / Core Features):** Sweeps package manager registry caches (npm, Cargo, Pip), local browser caches (Chrome), and system temp directories.
- **Linux (Experimental / CLI-Only):** Command-line scanning directly from Python source (no automated dashboard shortcuts).

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

### Option 3: Run via Git & Python Terminal (All Platforms)
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
- **Protected Files:** User documents (Desktop, Documents, Downloads, pictures) and system-critical system bins are explicitly ignored.
