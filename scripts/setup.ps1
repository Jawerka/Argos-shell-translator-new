$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot

$FlutterBin = 'C:\Users\Masny\AppData\Local\flutter\bin'
$Flutter = Join-Path $FlutterBin 'flutter.bat'
$Py310 = 'C:\Program Files\Python310\python.exe'
$VenvPy = Join-Path $RepoRoot 'venv\Scripts\python.exe'

Write-Host "Repo:     $RepoRoot"
Write-Host "Flutter:  $Flutter"
if (Test-Path $Flutter) {
  & $Flutter --version
} else {
  Write-Host 'Flutter SDK not found at the expected path.'
}

Write-Host "Python310: $Py310  exists=$([bool](Test-Path $Py310))"
Write-Host "venv:      $VenvPy  exists=$([bool](Test-Path $VenvPy))"
if (Test-Path $VenvPy) {
  & $VenvPy --version
} elseif (Test-Path $Py310) {
  & $Py310 --version
}
