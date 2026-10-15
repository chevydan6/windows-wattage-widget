$ErrorActionPreference = 'Stop'
$folder = Join-Path $env:LOCALAPPDATA 'WindowsWattageWidget'
$target = Join-Path $folder 'WindowsWattageWidget.exe'
Get-Process WindowsWattageWidget -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $target } | Stop-Process
Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name WindowsWattageWidget -ErrorAction SilentlyContinue
if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
Write-Host 'Uninstalled Windows Wattage Widget.'
