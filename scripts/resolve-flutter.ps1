# Resolve Flutter SDK bin directory (ASCII-only for Windows PowerShell 5.1).
# Order: FLUTTER_ROOT, flutter on PATH, repo .fvm/flutter_sdk, %LOCALAPPDATA%\flutter.

function Resolve-FlutterBin {
    param([string] $RepoRoot)

    if ($env:FLUTTER_ROOT) {
        $candidate = Join-Path $env:FLUTTER_ROOT 'bin'
        if (Test-Path (Join-Path $candidate 'flutter.bat')) {
            return $candidate
        }
    }

    $cmd = Get-Command flutter -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return (Split-Path -Parent $cmd.Source)
    }

    if ($RepoRoot) {
        $fvm = Join-Path $RepoRoot '.fvm\flutter_sdk\bin'
        if (Test-Path (Join-Path $fvm 'flutter.bat')) {
            return $fvm
        }
    }

    if ($env:LOCALAPPDATA) {
        $local = Join-Path $env:LOCALAPPDATA 'flutter\bin'
        if (Test-Path (Join-Path $local 'flutter.bat')) {
            return $local
        }
    }

    return $null
}
