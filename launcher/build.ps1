<#
Simple build helper for Windows (PowerShell).

Usage:
  # Console build (shows console window)
  .\launcher\build.ps1

  # Windowed build (no console window)
  .\launcher\build.ps1 -Windowed

This script runs PyInstaller with the recommended `--add-data` entries so
the frozen bundle includes the `ui` folder, `assets`, and `main.py`.
#>

param(
    [switch]$Windowed
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $scriptDir "..")

Write-Host "Building OBDPlusLauncher from" (Get-Location)

$name = "OBDPlusLauncher"
$mode = if ($Windowed) { "--windowed" } else { "--console" }

# PyInstaller command components
$entry = "launcher\run_app.py"
$add1 = "ui;ui"
$add2 = "assets;assets"
$add3 = "main.py;."
$add4 = "obd_manager.py;."
$add5 = "obd_functions.py;."
$add6 = "cloud_client.py;."
$hidden1 = "uvicorn"
$hidden2 = "uvicorn.subprocess"

# Build the argument array to call pyinstaller safely
$args = @(
    "--name", $name,
    "--onedir",
    $mode,
    $entry,
    "--paths", ".",
    "--add-data", $add1,
    "--add-data", $add2,
    "--add-data", $add3,
    "--add-data", $add4,
    "--add-data", $add5,
    "--add-data", $add6,
    "--hidden-import", $hidden1,
    "--hidden-import", $hidden2,
    "--clean"
)

# Some packages used by the backend (FastAPI and friends) include dynamic imports
# that PyInstaller can miss. Add `--collect-all` for common packages so data and
# submodules are bundled. This reduces runtime "ModuleNotFoundError" inside the EXE.
$collects = @("fastapi", "starlette", "pydantic", "jinja2", "markupsafe", "anyio")
foreach ($c in $collects) {
    $args += "--collect-all"
    $args += $c
}

# Ensure PyInstaller also knows about internal project modules that may not be
# discoverable via import-time analysis (these are modules in the project root).
$internalHidden = @("obd_manager", "obd_functions", "cloud_client", "main")
foreach ($h in $internalHidden) {
    $args += "--hidden-import"
    $args += $h
}

Write-Host "Running: pyinstaller $($args -join ' ')"

# Prefer the venv-installed PyInstaller when available to ensure the same
# environment used during development is used for bundling.
$projectRoot = (Get-Location).Path
$venvPyInstaller = Join-Path $projectRoot 'venv\Scripts\pyinstaller.exe'

# Prepare a timestamped log for the pyinstaller run so we can diagnose failures
$logDir = Join-Path $projectRoot 'launcher\build_logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile = Join-Path $logDir ("pyinstaller_build_$timestamp.log")

$ErrorActionPreference = 'Stop'
# Use Start-Process with redirected output for reliable logging in PowerShell 5.1
try {
    if (Test-Path $venvPyInstaller) {
        Write-Host "Using venv PyInstaller: $venvPyInstaller"
        $proc = Start-Process -FilePath $venvPyInstaller -ArgumentList $args -NoNewWindow -PassThru -Wait -RedirectStandardOutput $logFile -RedirectStandardError $logFile
    } else {
        Write-Host "Using system PyInstaller (venv not found)."
        $proc = Start-Process -FilePath "pyinstaller" -ArgumentList $args -NoNewWindow -PassThru -Wait -RedirectStandardOutput $logFile -RedirectStandardError $logFile
    }
    if ($proc.ExitCode -ne 0) {
        Write-Error "PyInstaller returned exit code $($proc.ExitCode). See log: $logFile"
        Write-Host "--- Last 300 lines of log ---"
        Get-Content -Path $logFile -Tail 300 | ForEach-Object { Write-Host $_ }
        exit $proc.ExitCode
    }
} catch {
    Write-Error "Build failed while invoking PyInstaller. See log: $logFile"
    if (Test-Path $logFile) {
        Write-Host "--- Last 300 lines of log ---"
        Get-Content -Path $logFile -Tail 300 | ForEach-Object { Write-Host $_ }
    }
    exit 1
}

Write-Host "Build finished. See dist\$name for the output folder."
Write-Host "Full pyinstaller log: $logFile"
