#Requires -Version 5.1
<#
.SYNOPSIS
  Flutter Release + frozen sidecar + staged dist/ArgosTranslate + Inno installer.

.EXAMPLE
  .\scripts\build-windows.ps1
#>
param(
    [string] $OutputDir = "",
    [switch] $SkipSidecar,
    [switch] $SkipInno
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'resolve-flutter.ps1')
$FlutterBin = Resolve-FlutterBin -RepoRoot $RepoRoot
if (-not $FlutterBin) {
    throw 'Flutter SDK not found. Install Flutter, add it to PATH, or set FLUTTER_ROOT.'
}
$env:Path = "$FlutterBin;" + $env:Path

function Invoke-Checked {
    param([scriptblock]$Command, [string]$Label)
    Write-Host "==> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Get-AppVersion {
    $pubspec = Join-Path $RepoRoot 'apps\translator\pubspec.yaml'
    foreach ($line in Get-Content -Path $pubspec) {
        if ($line -match '^version:\s*([0-9]+\.[0-9]+\.[0-9]+)') {
            return $Matches[1]
        }
    }
    return '1.0.0'
}

Set-Location $RepoRoot

Invoke-Checked { flutter pub get } 'flutter pub get'

$AppDir = Join-Path $RepoRoot 'apps\translator'
Push-Location $AppDir
try {
    Invoke-Checked { flutter build windows --release } 'flutter build windows --release'
} finally {
    Pop-Location
}

$FlutterRelease = Join-Path $AppDir 'build\windows\x64\runner\Release'
$TranslatorExe = Join-Path $FlutterRelease 'translator.exe'
if (-not (Test-Path $TranslatorExe)) {
    throw "Flutter Release not found: $TranslatorExe"
}

$SidecarDist = Join-Path $RepoRoot 'dist\argos_sidecar'
$SidecarExe = Join-Path $SidecarDist 'argos_sidecar.exe'
if (-not $SkipSidecar) {
    $VenvPy = Join-Path $RepoRoot 'venv\Scripts\python.exe'
    if (-not (Test-Path $VenvPy)) {
        throw @"
venv\Scripts\python.exe not found.
Create a venv on Python 3.10-3.12, install requirements.txt and pyinstaller, then retry.
"@
    }
    Invoke-Checked {
        & $VenvPy -m PyInstaller (Join-Path $RepoRoot 'ArgosSidecar.spec') --clean --noconfirm
    } 'PyInstaller ArgosSidecar.spec'
    if (-not (Test-Path $SidecarExe)) {
        throw "Sidecar onedir not found: $SidecarExe"
    }
} elseif (-not (Test-Path $SidecarExe)) {
    throw "SkipSidecar is set, but missing $SidecarExe. Build the sidecar first."
}

$StageDir = Join-Path $RepoRoot 'dist\ArgosTranslate'
if (Test-Path $StageDir) {
    Remove-Item -LiteralPath $StageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $StageDir | Out-Null

Write-Host "==> Staging $StageDir"
Copy-Item -Path (Join-Path $FlutterRelease '*') -Destination $StageDir -Recurse -Force

$StageSidecar = Join-Path $StageDir 'sidecar'
New-Item -ItemType Directory -Path $StageSidecar | Out-Null
Copy-Item -Path (Join-Path $SidecarDist '*') -Destination $StageSidecar -Recurse -Force

if (Test-Path (Join-Path $StageDir '_internal')) {
    throw "Do not mix PyInstaller _internal into Flutter Release root: $StageDir\_internal"
}

$ModelsSrc = Join-Path $RepoRoot 'argos_models'
if (Test-Path $ModelsSrc) {
    $StageModels = Join-Path $StageDir 'argos_models'
    New-Item -ItemType Directory -Path $StageModels -Force | Out-Null
    Get-ChildItem -Path $ModelsSrc -Filter '*.argosmodel' -ErrorAction SilentlyContinue |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $StageModels -Force }
}

$Smoke = Join-Path $RepoRoot 'scripts\smoke_flutter_dist.py'
$SmokePy = Join-Path $RepoRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $SmokePy)) {
    $SmokePy = 'python'
}
& $SmokePy $Smoke
if ($LASTEXITCODE -ne 0) {
    throw "smoke_flutter_dist.py failed with exit code $LASTEXITCODE"
}

$version = Get-AppVersion
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $RepoRoot 'dist'
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$outputResolved = (Resolve-Path -LiteralPath $OutputDir).Path
$stageResolved = (Resolve-Path -LiteralPath $StageDir).Path

if (-not $SkipInno) {
    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    $isccOnPath = Get-Command iscc -ErrorAction SilentlyContinue
    if ($isccOnPath) {
        $isccCandidates = @($isccOnPath.Source) + $isccCandidates
    }
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($iscc) {
        $iss = Join-Path $RepoRoot 'scripts\windows\argos-translate.iss'
        Write-Host "==> Inno Setup $version"
        & $iscc $iss `
            "/DMyAppVersion=$version" `
            "/DReleaseDir=$stageResolved" `
            "/DOutputDir=$outputResolved"
        if ($LASTEXITCODE -ne 0) {
            throw "ISCC failed with exit code $LASTEXITCODE"
        }
        $setup = Join-Path $outputResolved "argos-translate-$version-windows-x64-setup.exe"
        if (-not (Test-Path $setup)) {
            throw "Installer was not created: $setup"
        }
        Write-Host "Created $setup"
    } else {
        Write-Host 'Inno Setup (iscc) not found; installer skipped.'
    }
}

Write-Host ''
Write-Host 'Windows staging:' -ForegroundColor Green
Write-Host "  $TranslatorExe"
Write-Host "  $StageDir"
Write-Host "  sidecar: $(Join-Path $StageDir 'sidecar\argos_sidecar.exe')"
