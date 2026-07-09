# 🧹 CleanSweep

A lightweight, offline-first system optimizer and developer dashboard that audits storage, uncovers hidden caches, and helps you reclaim disk space.

CleanSweep runs **100% locally** on your machine. No system metrics, paths, or data ever leave your computer.

---

## ✨ Features

- **Real-Time Telemetry**: Monitor CPU load, memory allocation, and disk space usage from a sleek, Vercel-inspired dark interface.
- **Storage Breakdown Audit**: Scan and group files in your home directory into logical categories (Code, Archives, Media, Documents, etc.) and list the largest directories.
- **System Cache Sweeper**: Scan and clear logs, browser cache directories, and package manager cache stores (npm, Cargo, Pip, Conda).
- **Airtight Safety Gates**: Path-allowlist constraints prevent directory traversal attacks (such as cleaning system roots `/` or entire home paths). Safe paths are explicitly audited.
- **Dynamic Cross-Platform Support**: Automatically adapts paths and system caches depending on whether it is run on macOS, Windows, or Linux.

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
*Your browser will automatically open the local dashboard at [http://localhost:5051](http://localhost:5051).*

---

### Option 2: Download Standalone Executable (Windows)
Download the standalone executable directly from the [Releases](https://github.com/DSahir/cleansweep/releases) section:
- **Windows**: Run `CleanSweep.exe` directly.

---

### Option 3: Run via Git & Python Terminal
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
   *Your browser will automatically open the dashboard at [http://localhost:5051](http://localhost:5051).*

---

## 🔒 Security & Safety
CleanSweep implements strict directory boundary validation in `cleaner/cache_cleaner.py`. Target cache files are checked against an allowlist root system:
- It checks if path targets are within permitted cache directories (`CACHE_LOCATIONS`, `BROWSER_CACHE_LOCATIONS`, `TEMP_LOCATIONS`, `PACKAGE_MANAGER_CACHES`).
- System-critical or private user documents are skipped by default.
