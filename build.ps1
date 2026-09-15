param(
    [switch]$Clean,
    [switch]$DebugConsole
)

$ErrorActionPreference = "Stop"

$AppName = "PassGuardPrototype"
$ProductName = "PassGuard Prototype"
$ReleaseDirectory = Join-Path $PSScriptRoot "release"

function Get-FletPath {
    $command = Get-Command flet -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $scriptsPath = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
    $userScriptsPath = python -c "import os, site; print(os.path.join(site.USER_BASE, 'Scripts'))"
    $versionedUserScriptsPath = python -c "import os, site, sys; print(os.path.join(site.USER_BASE, f'Python{sys.version_info.major}{sys.version_info.minor}', 'Scripts'))"

    foreach ($directory in @($scriptsPath, $userScriptsPath, $versionedUserScriptsPath)) {
        foreach ($name in @("flet.exe", "flet")) {
            $candidate = Join-Path $directory $name
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    throw "Flet CLI not found. Run: python -m pip install -r requirements.txt"
}

if ($Clean) {
    foreach ($directory in @(
        (Join-Path $PSScriptRoot "build"),
        (Join-Path $PSScriptRoot "dist"),
        $ReleaseDirectory
    )) {
        if (Test-Path $directory) {
            Remove-Item -LiteralPath $directory -Recurse -Force
        }
    }
}

$fletPath = Get-FletPath
$appVersion = (python -c "from src.version import APP_VERSION; print(APP_VERSION)").Trim()
$fileVersion = "$appVersion.0"

New-Item -ItemType Directory -Path $ReleaseDirectory -Force | Out-Null

$arguments = @(
    "pack",
    "main.py",
    "--name", $AppName,
    "--distpath", $ReleaseDirectory,
    "--product-name", $ProductName,
    "--product-version", $appVersion,
    "--file-version", $fileVersion,
    "--company-name", "Nguyen Thinh - Kyle",
    "--file-description", "Offline encrypted password vault",
    "--hidden-import", "pydantic",
    "--hidden-import", "cryptography",
    "--hidden-import", "argon2",
    "--hidden-import", "argon2.low_level",
    "-y"
)

if ($DebugConsole) {
    $arguments += @("--debug-console", "true")
}

Write-Host "Building single-file Windows executable..."
& $fletPath @arguments

if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE."
}

$executable = Join-Path $ReleaseDirectory "$AppName.exe"
if (-not (Test-Path $executable)) {
    throw "Build completed but $executable was not created."
}

$sizeMb = [math]::Round((Get-Item $executable).Length / 1MB, 1)
Write-Host "Build complete: $executable ($sizeMb MB)"
