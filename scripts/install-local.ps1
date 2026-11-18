param([string]$PythonVersion = '3.12')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $root '.env'))) { Copy-Item (Join-Path $root '.env.example') (Join-Path $root '.env') }
foreach ($line in Get-Content -LiteralPath (Join-Path $root '.env')) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
Push-Location $root
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Zainstaluj uv: https://docs.astral.sh/uv/getting-started/installation/' }
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        uv --cache-dir .cache/uv venv --python $PythonVersion .venv
        if ($LASTEXITCODE -ne 0) { throw 'Nie udało się utworzyć środowiska Python.' }
    }
    uv --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe -r application/requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować zależności backendu.' }
    Push-Location usterka_frontend
    try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować zależności frontendu.' } } finally { Pop-Location }
    & .venv/Scripts/python.exe application/manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Migracja bazy nie powiodła się.' }
    & .venv/Scripts/python.exe application/manage.py check
    Write-Output 'Zainstalowano. Uruchom ./scripts/start-local.ps1'
} finally { Pop-Location }
