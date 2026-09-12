param(
  [switch]$Test
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'resolve-flutter.ps1')
$FlutterBin = Resolve-FlutterBin -RepoRoot $RepoRoot
if (-not $FlutterBin) {
  throw 'Flutter SDK not found. Install Flutter, add it to PATH, or set FLUTTER_ROOT.'
}
$env:Path = "$FlutterBin;" + $env:Path

Set-Location $RepoRoot

function Invoke-Checked {
  param([scriptblock]$Command, [string]$Label)
  Write-Host "==> $Label"
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

Invoke-Checked { flutter pub get } 'flutter pub get'

if ($Test) {
  Invoke-Checked {
    dart analyze --fatal-infos packages/translator_core
  } 'dart analyze translator_core'
  Invoke-Checked {
    flutter analyze --fatal-infos apps/translator
  } 'flutter analyze translator'
  Push-Location (Join-Path $RepoRoot 'packages\translator_core')
  try {
    Invoke-Checked { dart test } 'dart test translator_core'
  } finally {
    Pop-Location
  }
  Push-Location (Join-Path $RepoRoot 'apps\translator')
  try {
    Invoke-Checked { flutter test } 'flutter test translator'
  } finally {
    Pop-Location
  }
  Write-Host 'All checks passed.'
  return
}

Set-Location (Join-Path $RepoRoot 'apps\translator')
flutter run -d windows
if ($LASTEXITCODE -ne 0) {
  throw "flutter run failed with exit code $LASTEXITCODE"
}
