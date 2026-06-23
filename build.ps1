param (
    [switch]$Windows,
    [switch]$Android
)

if ($Windows) {
    Write-Host "Building Windows Executable..."
    # 'flet pack' packages the python script into an exe
    flet pack main.py --name LuuPass
}

if ($Android) {
    Write-Host "Building Android APK..."
    Write-Host "Make sure Flutter SDK and Android SDK are installed locally!"
    flet build apk --project LuuPass --module-name main
}

if (-Not $Windows -and -Not $Android) {
    Write-Host "Please specify -Windows or -Android flag"
}
