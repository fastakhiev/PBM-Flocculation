$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "pbm_model_interface"
$Backend = Join-Path $Root "backend"
$Release = Join-Path $Root "release\PBM-Flocculation"
$BuildVenv = Join-Path $Backend ".venv-release"

$VersionOk = py -3 -c "import platform, struct, sys; print(int((3, 10, 1) <= sys.version_info < (3, 15) and platform.python_implementation() == 'CPython' and struct.calcsize('P') == 8))"
Assert-NativeSuccess "Python version check"
if ($VersionOk -ne "1") {
    throw "64-bit CPython 3.10.1 through 3.14.x from python.org is required."
}
$PythonDescription = py -3 -c "import platform, sys; print(f'{platform.python_implementation()} {platform.python_version()} ({sys.executable})')"
Assert-NativeSuccess "Python environment inspection"
Write-Host "Build Python: $PythonDescription"

if (Test-Path $Release) {
    Remove-Item $Release -Recurse -Force
}
New-Item -ItemType Directory -Path $Release -Force | Out-Null

Push-Location $Frontend
npm ci
Assert-NativeSuccess "npm ci"
npm audit --omit=dev --audit-level=high
Assert-NativeSuccess "npm audit"
npm run build
Assert-NativeSuccess "Frontend build"
$NpmSbom = (npm sbom --sbom-format cyclonedx) -join [Environment]::NewLine
Assert-NativeSuccess "npm SBOM generation"
[IO.File]::WriteAllText(
    (Join-Path $Release "sbom-npm.cdx.json"),
    $NpmSbom,
    [Text.UTF8Encoding]::new($false)
)
Pop-Location

Push-Location $Backend
if (Test-Path $BuildVenv) {
    Remove-Item $BuildVenv -Recurse -Force
}
py -3 -m venv $BuildVenv
Assert-NativeSuccess "Python virtual environment creation"
& "$BuildVenv\Scripts\python.exe" -m pip install --requirement requirements-audit.txt
Assert-NativeSuccess "Python dependency installation"
& "$BuildVenv\Scripts\pip-audit.exe" --requirement requirements-build.txt
Assert-NativeSuccess "Python dependency audit"
& "$BuildVenv\Scripts\pip-audit.exe" --requirement requirements.txt --format cyclonedx-json --output (Join-Path $Release "sbom-python.cdx.json")
Assert-NativeSuccess "Python SBOM generation"
& "$BuildVenv\Scripts\python.exe" -m unittest discover -s tests -v
Assert-NativeSuccess "Backend tests"
& "$BuildVenv\Scripts\pyinstaller.exe" --noconfirm --clean pbm_app.spec
Assert-NativeSuccess "PyInstaller build"
$BundledFfi = Get-ChildItem ".\dist\PBM-Flocculation" -File -Recurse |
    Where-Object { $_.Name -match "^(lib)?ffi-.*\.dll$" }
if (-not $BundledFfi) {
    throw "PyInstaller output does not contain the libffi DLL required by _ctypes."
}

$OriginalPath = $env:PATH
$env:PBM_SMOKE_TEST = "1"
try {
    $env:PATH = @(
        (Join-Path $env:SystemRoot "System32"),
        $env:SystemRoot,
        (Join-Path $env:SystemRoot "System32\Wbem")
    ) -join ";"
    & ".\dist\PBM-Flocculation\PBM-Flocculation.exe"
    Assert-NativeSuccess "Packaged application smoke test"
}
finally {
    $env:PATH = $OriginalPath
    Remove-Item Env:PBM_SMOKE_TEST -ErrorAction SilentlyContinue
}
Pop-Location

Copy-Item (Join-Path $Backend "dist\PBM-Flocculation\*") $Release -Recurse -Force
Copy-Item (Join-Path $Root "LICENSE") $Release -Force
Copy-Item (Join-Path $Root "THIRD_PARTY_NOTICES.md") $Release -Force
Copy-Item (Join-Path $Root "CITATION.md") $Release -Force
Copy-Item (Join-Path $Root "SECURITY.md") $Release -Force
Copy-Item (Join-Path $Root "docs\SCIENTIFIC_METHOD.md") $Release -Force
Copy-Item (Join-Path $Root "docs\VALIDATION.md") $Release -Force
Copy-Item (Join-Path $Root "docs\DATA_PROVENANCE.md") $Release -Force

Get-ChildItem -File -Recurse $Release |
    Sort-Object FullName |
    Get-FileHash -Algorithm SHA256 |
    ForEach-Object {
        $RelativePath = $_.Path.Substring($Release.Length + 1).Replace("\", "/")
        "$($_.Hash.ToLower())  $RelativePath"
    } |
    Set-Content (Join-Path $Release "SHA256SUMS.txt") -Encoding ascii

Write-Host "Release created at $Release"
