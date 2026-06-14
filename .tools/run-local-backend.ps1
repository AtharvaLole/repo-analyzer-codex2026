$ErrorActionPreference = "Stop"
Set-Location "D:\Coding\Personal_Projects\repo-analyzer-codex2026\backend"
$env:DEBUG = "true"
$env:SENTRY_DSN = ""
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
