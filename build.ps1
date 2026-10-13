$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

python -m pip install --disable-pip-version-check -r requirements-build.txt
if ($LASTEXITCODE -ne 0) {
    throw "Build dependencies could not be installed (exit code $LASTEXITCODE)."
}

python -m PyInstaller --noconfirm --clean --onefile --windowed --name CacheSade --paths $ProjectRoot "$ProjectRoot\cachesade\app.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed (exit code $LASTEXITCODE). Close a running CacheSade.exe and retry."
}

$OutputPath = Join-Path $ProjectRoot 'dist\CacheSade.exe'
if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
    throw "Build finished without producing $OutputPath."
}

Write-Host "Hazir: $OutputPath"

