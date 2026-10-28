# Install the proprietary core binary on Windows (PowerShell 7+).
$ErrorActionPreference = "Stop"
$Version = if ($env:JMGO_CORE_VERSION) { $env:JMGO_CORE_VERSION } else { "0.1.1" }
$Asset = "windows-x86_64"
$Base = "https://github.com/heihei6661/JMGo-SI/releases/download/v$Version"
$Dir = Join-Path $HOME ".jmgo\core\$Version"
$Bin = Join-Path $HOME ".jmgo\bin"
New-Item -ItemType Directory -Force -Path $Dir, $Bin | Out-Null

$File = "jmgo_core-$Version-$Asset.zip"
Invoke-WebRequest "$Base/$File" -OutFile (Join-Path $env:TEMP $File)
Expand-Archive -Force (Join-Path $env:TEMP $File) -DestinationPath $Dir
$Inner = Join-Path $Dir "jmgo_core-$Version-$Asset"
Copy-Item (Join-Path $Inner "jmgo_core.exe") (Join-Path $Bin "jmgo_core.exe") -Force
Write-Host "installed: $Bin\jmgo_core.exe"
