# Contributing to CleanSweep

Thank you for your interest in contributing to CleanSweep! We welcome help in keeping CleanSweep clean, fast, and secure.

---

## 🛠️ Development Setup

To set up a local workspace for developing CleanSweep on macOS, Windows, or Linux:

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/DSahir/cleansweep.git
   cd cleansweep
   ```
2. **Setup virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Run the development server**:
   ```bash
   python app.py
   ```
   The local application will launch, open your default browser, and serve the dashboard at `http://localhost:5051`.

---

## 🧼 Code Guidelines

- **Maintain Safety Gates**: Any modifications to cleaning logic in `cleaner/` or directory scanning in `scanner/` must conform to the safety gate allowlist restrictions defined in `config.py`.
- **Formatting**: Ensure your Python code is clean and adheres to standard PEP 8 formatting.
- **Commit Messages**: Write descriptive commit messages summarizing the bug fixed or feature added.

---

## 🤝 Submitting Contributions

1. Create a descriptive branch for your changes:
   ```bash
   git checkout -b feature/my-amazing-feature
   ```
2. Write tests or manually verify that your additions do not break local or Vercel-based runs.
3. Push your branch and open a Pull Request against the `main` branch.
