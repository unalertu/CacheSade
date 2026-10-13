$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

python -m pip install --disable-pip-version-check -r requirements-build.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CacheSade --paths $ProjectRoot "$ProjectRoot\cachesade\app.py"

Write-Host "Hazir: $ProjectRoot\dist\CacheSade.exe"

