# Desktop security audit · 19 November 2026

| Finding | Severity | Remediation and evidence |
|---|---|---|
| Legacy reader accepted credentials from `api.txt`. | High | Removed the reader. Settings writes one atomic record to the OS vault. Both fields are masked. Environment variables take precedence. |
| The previous PyInstaller spec bundled the entire local cache. | High | Replaced the directory inclusion with one public YAML file. The spec checks archive member names. The legacy prebuilt binary is outside this release. |
| Dependency scan returned 99 advisory entries across five installed packages. | High | Updated Pillow, PyArrow, Black, pytest and the environment's pip. Reinstalled the pinned project and reran the installed-environment audit including development and research tools. |
| Free-form ticker and cache handling could mix universes. | Medium | Normalized and bounded symbols, content-addressed processed caches, atomic writes and explicit file-picker checks. Object arrays are disabled when saving and loading NPY. |
| SDK defaults lacked an explicit timeout and could surface raw HTTP errors. | Medium | Fixed the HTTPS endpoint, disabled redirects in the pinned SDK, supplied connect/read timeouts, bounded GET retries and exponential backoff, and translate provider failures into a safe message. |
| Pre-existing security workflow fetched shallow history. | Medium | Security CI fetches all refs and runs Gitleaks independently of the Python audit. |

Local checks covered the native source with Bandit, the installed Python environment with pip-audit, and all reachable Git history, staged changes and Git-visible working files with Gitleaks 8.30.1 in redacted mode. The follow-up audit reported zero known vulnerabilities. Gitleaks reported zero findings. Two Bandit annotations cover fixed-argument invocation of the local FFmpeg binary. A separate scan of the first Linux bundle flagged three strings in PyArrow Cython sources and vendored hash headers. Those upstream development files were removed from the distribution. No project credential was identified for rotation. Review the response procedure in [SECURITY.md](SECURITY.md).

The third-party advisory database changes over time. Ignored user caches, archives and the separate web frontend dependency tree are outside the Git secret scan. The native executable excludes the web workstation.

The rebuilt Linux distribution passed a redacted Gitleaks directory scan. A byte search of the distributed files and inspection of 2,754 embedded Python module entries found no build-user home path. The packaged GUI launched on X11 and its CLI reproduced the measured 2022 result. Windows build and CLI checks are configured in CI.
