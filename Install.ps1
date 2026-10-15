$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'WindowsWattageWidget.exe'
if (!(Test-Path $source)) { $source = Join-Path $PSScriptRoot 'dist\WindowsWattageWidget.exe' }
if (!(Test-Path $source)) { throw 'Download the executable beside Install.ps1, or run Build.ps1 first.' }
$folder = Join-Path $env:LOCALAPPDATA 'WindowsWattageWidget'
$target = Join-Path $folder 'WindowsWattageWidget.exe'
New-Item -ItemType Directory -Force $folder | Out-Null
# Stop only this user's installed copy when updating it.
Get-Process WindowsWattageWidget -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $target } | Stop-Process
if ([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($target)) { Copy-Item $source $target -Force }
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
New-Item -Path $runKey -Force | Out-Null
New-ItemProperty -Path $runKey -Name WindowsWattageWidget -Value ('"' + $target + '"') -PropertyType String -Force | Out-Null
Start-Process $target
Write-Host 'Installed for your account. The widget will start when you sign in.'
