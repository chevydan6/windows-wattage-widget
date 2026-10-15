$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path $compiler)) { throw 'The Windows .NET Framework C# compiler was not found.' }
$out = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Force $out | Out-Null
& $compiler /nologo /target:winexe /optimize+ /platform:anycpu `
    /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Management.dll `
    ('/out:' + (Join-Path $out 'WindowsWattageWidget.exe')) (Join-Path $PSScriptRoot 'src\PowerIndicator.cs')
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed.' }
