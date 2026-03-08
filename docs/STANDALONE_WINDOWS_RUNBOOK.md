# Standalone Windows Runbook (No Assistant Needed)

## 1) One-time Setup

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## 2) Start GUI (Fault-tolerant)

Use the launcher (starts guardian + opens browser):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_gui.ps1
```

Open manually if needed:
- `http://127.0.0.1:8000`

## 3) Stop GUI

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop_gui.ps1
```

## 4) Auto-start on Login (optional)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_gui_startup_task.ps1
```

This creates a Windows Scheduled Task that launches GUI guardian at logon.

## 5) Crash Resilience

- `run_gui_guardian.ps1` restarts GUI automatically if it exits.
- Logs are written under:
  - `logs\gui_stdout_*.log`
  - `logs\gui_stderr_*.log`

## 6) Quick Health Check

In browser or PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

Expected: HTTP 200 with status payload.

