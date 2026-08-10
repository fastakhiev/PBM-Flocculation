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
$PythonSelector = "-3.12"

$PythonInfoJson = py $PythonSelector -c "import json, os, platform, struct, sys; print(json.dumps({'compatible': sys.version_info[:2] == (3, 12) and platform.python_implementation() == 'CPython' and struct.calcsize('P') == 8, 'version': platform.python_version(), 'executable': sys.executable, 'base_prefix': sys.base_prefix, 'is_conda': os.path.isdir(os.path.join(sys.base_prefix, 'conda-meta'))}))"
Assert-NativeSuccess "Python environment inspection"
$PythonInfo = $PythonInfoJson | ConvertFrom-Json
if (-not $PythonInfo.compatible) {
    throw "64-bit CPython 3.12 is required for a reproducible Windows release."
}
Write-Host "Source Python: $($PythonInfo.version) ($($PythonInfo.executable))"

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
if ($PythonInfo.is_conda) {
    $CondaExe = Join-Path $PythonInfo.base_prefix "Scripts\conda.exe"
    if (-not (Test-Path $CondaExe)) {
        $CondaCommand = Get-Command conda.exe -ErrorAction SilentlyContinue
        if (-not $CondaCommand) {
            throw "Anaconda Python was detected, but conda.exe could not be found."
        }
        $CondaExe = $CondaCommand.Source
    }
    & $CondaExe create --prefix $BuildVenv --yes --quiet python=3.12 pip
    Assert-NativeSuccess "Conda release environment creation"
    $BuildPython = Join-Path $BuildVenv "python.exe"
    $env:CONDA_PREFIX = $BuildVenv
    $env:PATH = @(
        $BuildVenv,
        (Join-Path $BuildVenv "Scripts"),
        (Join-Path $BuildVenv "Library\bin"),
        $env:PATH
    ) -join ";"
    Write-Host "Release environment: isolated Conda environment"
}
else {
    & $PythonInfo.executable -m venv $BuildVenv
    Assert-NativeSuccess "Python virtual environment creation"
    $BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
    Write-Host "Release environment: standard venv"
}

& $BuildPython -m pip install --requirement requirements-audit.txt
Assert-NativeSuccess "Python dependency installation"
& $BuildPython -m pip_audit --requirement requirements-build.txt
Assert-NativeSuccess "Python dependency audit"
& $BuildPython -m pip_audit --requirement requirements.txt --format cyclonedx-json --output (Join-Path $Release "sbom-python.cdx.json")
Assert-NativeSuccess "Python SBOM generation"
& $BuildPython -m unittest discover -s tests -v
Assert-NativeSuccess "Backend tests"
& $BuildPython -m PyInstaller --noconfirm --clean pbm_app.spec
Assert-NativeSuccess "PyInstaller build"
$BundleRoot = (Resolve-Path ".\dist\PBM-Flocculation").Path
& $BuildPython ".\build_support\collect_windows_ctypes_runtime.py" `
    --target $BundleRoot `
    --report (Join-Path $Release "ctypes-runtime-manifest.json")
Assert-NativeSuccess "_ctypes runtime dependency collection"

$OriginalPath = $env:PATH
$OriginalCondaPrefix = $env:CONDA_PREFIX
$OriginalCondaDefaultEnv = $env:CONDA_DEFAULT_ENV
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$env:PBM_SMOKE_TEST = "1"
try {
    Remove-Item Env:CONDA_PREFIX -ErrorAction SilentlyContinue
    Remove-Item Env:CONDA_DEFAULT_ENV -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    $env:PATH = @(
        (Join-Path $env:SystemRoot "System32"),
        $env:SystemRoot,
        (Join-Path $env:SystemRoot "System32\Wbem")
    ) -join ";"
    $SmokeProcess = Start-Process `
        -FilePath (Join-Path $BundleRoot "PBM-Flocculation.exe") `
        -PassThru `
        -Wait
    if ($SmokeProcess.ExitCode -ne 0) {
        throw "Packaged application smoke test failed with exit code $($SmokeProcess.ExitCode)."
    }
}
finally {
    $env:PATH = $OriginalPath
    $env:CONDA_PREFIX = $OriginalCondaPrefix
    $env:CONDA_DEFAULT_ENV = $OriginalCondaDefaultEnv
    $env:PYTHONHOME = $OriginalPythonHome
    $env:PYTHONPATH = $OriginalPythonPath
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
