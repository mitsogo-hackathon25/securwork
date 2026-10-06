# SecurWork — start backend + frontend for local development (Windows)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$port = 5180

Write-Host "SecurWork dev servers" -ForegroundColor Cyan
Write-Host "  Storefront: http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "  API/Admin:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""

# Free ports 8000/5180 — stale servers cause blank pages and wrong redirects
Write-Host "Freeing ports 8000 and $port..." -ForegroundColor Yellow
function Stop-ListenersOnPort([int]$listenPort) {
  netstat -ano | Select-String "LISTENING" | Select-String ":$listenPort\s" | ForEach-Object {
    if ($_ -match '\s(\d+)\s*$') {
      Stop-Process -Id ([int]$Matches[1]) -Force -ErrorAction SilentlyContinue
    }
  }
}
Stop-ListenersOnPort 8000
Stop-ListenersOnPort $port
Start-Sleep -Seconds 1

$backendCmd = @"
Set-Location '$root\backend'
if (-not (Test-Path '.\venv\Scripts\Activate.ps1')) {
  Write-Host 'Creating Python venv...' -ForegroundColor Yellow
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
} else {
  .\venv\Scripts\Activate.ps1
}
`$env:USE_SQLITE = 'true'
`$env:SECRET_KEY = 'dev'
`$env:FRONTEND_URL = 'http://127.0.0.1:5180'
`$env:CORS_ALLOWED_ORIGINS = 'http://127.0.0.1:5180,http://localhost:5180'
`$env:CSRF_TRUSTED_ORIGINS = 'http://127.0.0.1:5180,http://localhost:5180'
python manage.py runserver 127.0.0.1:8000
"@

$frontendCmd = @"
Set-Location '$root\frontend'
if (-not (Test-Path '.\node_modules')) {
  Write-Host 'Installing npm packages...' -ForegroundColor Yellow
  npm install
}
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Started backend and frontend in separate windows." -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:$port in your browser." -ForegroundColor Green
