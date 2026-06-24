param (
    [switch]$Windows
)

function Get-FletPath {
    $cmd = Get-Command flet -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $scriptsPath = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
    $userScriptsPath = python -c "import os, site; print(os.path.join(site.USER_BASE, 'Scripts'))"
    $versionedUserScriptsPath = python -c "import os, site, sys; print(os.path.join(site.USER_BASE, f'Python{sys.version_info.major}{sys.version_info.minor}', 'Scripts'))"
    foreach ($path in @($scriptsPath, $userScriptsPath, $versionedUserScriptsPath)) {
        foreach ($name in @("flet.exe", "flet")) {
            $candidate = Join-Path $path $name
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    throw "flet CLI not found. Run: pip install -r requirements.txt"
}

$flet_path = Get-FletPath

if ($Windows) {
    Write-Host "Building Windows Executable..."
    & $flet_path pack main.py --name LuuPass --hidden-import pydantic --hidden-import cryptography --hidden-import argon2 --hidden-import argon2.low_level -y
} else {
    Write-Host "Please specify -Windows flag to build the Windows Executable."
}
