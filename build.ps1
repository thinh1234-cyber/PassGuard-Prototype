param (
    [switch]$Windows
)

$flet_path = "C:\Users\DELL\AppData\Roaming\Python\Python312\Scripts\flet.exe"

if ($Windows) {
    Write-Host "Building Windows Executable..."
    & $flet_path pack main.py --name LuuPass --hidden-import pydantic --hidden-import cryptography
} else {
    Write-Host "Please specify -Windows flag to build the Windows Executable."
}
