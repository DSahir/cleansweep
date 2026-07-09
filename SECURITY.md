# Security Policy

We take the security of CleanSweep seriously. As a tool that interacts with your local filesystem to clean temporary files and caches, security and user safety are our highest priorities.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Deletion Safety Boundaries

CleanSweep operates inside strict bounds:
- It **only** deletes files within the approved cache configurations (`CACHE_LOCATIONS`, `BROWSER_CACHE_LOCATIONS`, `PACKAGE_MANAGER_CACHES`, etc.) in `config.py`.
- It uses directory resolution (`Path.resolve()`) to ensure no symbolic links or path traversal patterns (`../`) can escape these allowlisted cache folders.
- It will **never** target system roots, system bins, or user documents (Documents, Desktop, Downloads, Pictures).

## Reporting a Vulnerability

If you discover a security vulnerability (such as a safety-gate bypass or a directory traversal bug), please do not open a public issue. Instead, report it directly to the maintainer via email:

- **Email:** security@example.com (Please replace with your email or contact method if desired)

We will respond within 48 hours and work with you to patch the vulnerability before releasing details publicly. Thank you for helping keep CleanSweep secure!
