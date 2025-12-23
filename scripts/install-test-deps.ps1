# PowerShell script to install test dependencies for Pill Assistant
# Usage: Open PowerShell, navigate to repo root and run: .\scripts\install-test-deps.ps1

param(
    [switch]$CreateVenv,
    [switch]$AutoLoadVsTools,  # Attempt to locate and load Visual Studio build tool environment
    [string]$VsDevCmdPath       # Optional explicit path to vcvarsall.bat or VsDevCmd.bat
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not found in PATH. Please install Python 3.10+ and ensure 'python' is on PATH."
    exit 1
}

function Find-VsWhere {
    $paths = @(
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\Installer\vswhere.exe",
        "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Try-Load-VsDevEnv {
    param(
        [string]$ExplicitPath
    )

    # If an explicit path was provided, try that first
    if ($ExplicitPath) {
        if (Test-Path $ExplicitPath) {
            Write-Output "Sourcing Visual Studio dev environment from explicit path: $ExplicitPath"
            & $ExplicitPath
            return $true
        } else {
            Write-Warning "Explicit VS dev path provided but not found: $ExplicitPath"
        }
    }

    # Try to use environment variable if present
    if ($env:VSINSTALLDIR) {
        $instPath = $env:VSINSTALLDIR
        $vcvars = Join-Path $instPath "VC\Auxiliary\Build\vcvarsall.bat"
        $vsdev = Join-Path $instPath "Common7\Tools\VsDevCmd.bat"
        if (Test-Path $vcvars) { & $vcvars x64; return $true }
        if (Test-Path $vsdev) { & $vsdev; return $true }
    }

    # Try to locate a Visual Studio installation using vswhere
    $vswhere = Find-VsWhere
    if ($vswhere) {
        try {
            $instPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath -nologo
            if (-not $instPath) { $instPath = & $vswhere -latest -products * -property installationPath -nologo }

            if ($instPath) {
                $vcvars = Join-Path $instPath "VC\Auxiliary\Build\vcvarsall.bat"
                $vsdev = Join-Path $instPath "Common7\Tools\VsDevCmd.bat"

                        if (Test-Path $vcvars) {
                    Write-Output "Sourcing Visual Studio vcvarsall from: $vcvars"
                    # Run in cmd and capture environment changes, then import into this PowerShell session
                    $cmd = "`"$vcvars`" x64 && set"
                    $output = cmd /c $cmd 2>$null
                    if ($output) {
                        $lines = $output -split "`r?`n"
                        foreach ($line in $lines) {
                            if ($line -match "^([^=]+)=(.*)$") {
                                $name = $matches[1]
                                $value = $matches[2]
                                # Update PowerShell env
                                $env:$name = $value
                            }
                        }
                        return $true
                    } else {
                        Write-Warning "vcvarsall ran but produced no output"
                        return $false
                    }
                } elseif (Test-Path $vsdev) {
                    Write-Output "Sourcing Visual Studio VsDevCmd from: $vsdev"
                    $cmd = "`"$vsdev`" && set"
                    $output = cmd /c $cmd 2>$null
                    if ($output) {
                        $lines = $output -split "`r?`n"
                        foreach ($line in $lines) {
                            if ($line -match "^([^=]+)=(.*)$") {
                                $name = $matches[1]
                                $value = $matches[2]
                                $env:$name = $value
                            }
                        }
                        return $true
                    } else {
                        Write-Warning "VsDevCmd ran but produced no output"
                        return $false
                    }
                }
            }
        } catch {
            Write-Warning "Failed to invoke Visual Studio dev environment: $_"
        }
    }

    # Try common install locations (VS 2019/2022/2024 BuildTools)
    $possibleRoots = @(
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2022\BuildTools",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2022\Professional",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2022\Community",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2019\BuildTools",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2019\Professional",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio\2019\Community"
    )

    foreach ($root in $possibleRoots) {
        $vcvars = Join-Path $root "VC\Auxiliary\Build\vcvarsall.bat"
        $vsdev = Join-Path $root "Common7\Tools\VsDevCmd.bat"
        if (Test-Path $vcvars) { Write-Output "Sourcing $vcvars"; & $vcvars x64; return $true }
        if (Test-Path $vsdev) { Write-Output "Sourcing $vsdev"; & $vsdev; return $true }
    }

    return $false
}

if ($CreateVenv) {
    $venvDir = "venv"
    python -m venv $venvDir
    Write-Output "Created virtual environment in ./$venvDir. Activate it with: .\$venvDir\Scripts\Activate.ps1"
}

# Optionally attempt to auto-load VS build tools into this session
if ($AutoLoadVsTools -or $VsDevCmdPath) {
    $loaded = Try-Load-VsDevEnv -ExplicitPath $VsDevCmdPath
    if (-not $loaded) {
        Write-Warning "Auto-detection or explicit VS dev invocation failed. If you have Developer PowerShell, run this script from there or pass -VsDevCmdPath 'C:\\path\\to\\vcvarsall.bat' when invoking the script."
        # If user explicitly requested auto-loading we should fail early to avoid long installs that will later fail building C extensions
        if ($AutoLoadVsTools) {
            Write-Error "Visual Studio dev environment could not be loaded into this session. Aborting to avoid long download and build failures. Run the script from Developer PowerShell or provide the explicit path via -VsDevCmdPath.";
            exit 1
        }
    } else {
        Write-Output "Visual Studio build environment loaded into current session."
    }
}

# Quick sanity check for native build tool availability (cl.exe)
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    Write-Warning "C compiler (cl.exe) not found in PATH. If you expect to build packages from source, run this script from Developer PowerShell (Developer Command Prompt) or supply -VsDevCmdPath to this script to load the environment."
    # Warn but continue; some installs may still succeed using pure-Python wheels
}

Write-Output "Installing development/test dependencies from requirements-dev.txt..."
python -m pip install --upgrade pip
# Use isolated pip when possible to avoid unexpected constraints
python -m pip --isolated install -r requirements-dev.txt

Write-Output "Done. You can run tests with: pytest -q"
