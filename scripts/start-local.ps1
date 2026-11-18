$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Najpierw uruchom ./scripts/install-local.ps1' }
foreach ($line in Get-Content -LiteralPath (Join-Path $root '.env')) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$logs = Join-Path $root '.cache/logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$services = @(
    @{ Name='backend'; Port=8000; File=$python; Args=@('-u', (Join-Path $root 'application/manage.py'), 'runserver', '127.0.0.1:8000'); Dir=(Join-Path $root 'application') },
    @{ Name='frontend'; Port=5173; File=(Get-Command node).Source; Args=@((Join-Path $root 'usterka_frontend/node_modules/vite/bin/vite.js'), '--port', '5173'); Dir=(Join-Path $root 'usterka_frontend') }
)
foreach ($s in $services) {
    if (Get-NetTCPConnection -LocalPort $s.Port -State Listen -ErrorAction SilentlyContinue) { Write-Output "$($s.Name): port $($s.Port) zajęty - zostawiam."; continue }
    Start-Process -FilePath $s.File -ArgumentList $s.Args -WorkingDirectory $s.Dir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "$($s.Name).log") -RedirectStandardError (Join-Path $logs "$($s.Name)-error.log") | Out-Null
}
Write-Output 'Frontend: http://localhost:5173/'
Write-Output 'API:      http://127.0.0.1:8000/api/docs'
Write-Output 'Admin:    http://127.0.0.1:8000/admin/'
Write-Output "Logi:     $logs"
