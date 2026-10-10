# Installation de Matt's Métré Toiture sur un PC Windows avec Docker Desktop.
# Lancement : double-clic sur INSTALLER.bat (qui exécute ce script).
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Pause-Fin { Write-Host ""; Read-Host "Appuyez sur Entrée pour fermer" | Out-Null }

try { docker info *> $null; if ($LASTEXITCODE -ne 0) { throw "docker" } }
catch {
  Write-Host "Docker Desktop n'est pas démarré ou pas installé." -ForegroundColor Red
  Write-Host "Installez-le depuis https://www.docker.com/products/docker-desktop/ , démarrez-le, puis relancez INSTALLER.bat."
  Pause-Fin; exit 1
}

$envFile = Join-Path $PSScriptRoot ".env"
$aCompte = (Test-Path $envFile) -and ((Get-Content $envFile) -match "^MMT_ADMIN_EMAIL=.+")
if (-not $aCompte) {
  Write-Host "Création du compte administrateur de l'application" -ForegroundColor Cyan
  $email = Read-Host "  E-mail"
  while ($true) {
    $s1 = Read-Host "  Mot de passe (10 caractères minimum)" -AsSecureString
    $s2 = Read-Host "  Confirmez le mot de passe" -AsSecureString
    $m1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1))
    $m2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2))
    if ($m1.Length -lt 10) { Write-Host "  Trop court."; continue }
    if ($m1 -ne $m2) { Write-Host "  Les deux saisies diffèrent."; continue }
    if ($m1.Contains("'")) { Write-Host "  L'apostrophe ' n'est pas acceptée dans ce mot de passe."; continue }
    break
  }
  $contenu = "MMT_COOKIE_SECURE=true`nMMT_ADMIN_EMAIL='$email'`nMMT_ADMIN_PASSWORD='$m1'`n"
  [IO.File]::WriteAllText($envFile, $contenu, (New-Object Text.UTF8Encoding($false)))
}

Write-Host "Construction et démarrage (la première fois : 10 à 20 minutes de téléchargement)..." -ForegroundColor Cyan
docker compose --profile internet up -d --build
if ($LASTEXITCODE -ne 0) { Write-Host "Échec du démarrage." -ForegroundColor Red; Pause-Fin; exit 1 }

Write-Host -NoNewline "Attente du démarrage de l'application"
$ok = $false
for ($i = 0; $i -lt 120; $i++) {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://localhost:8000/api/sante | Out-Null; $ok = $true; break }
  catch { Write-Host -NoNewline "."; Start-Sleep -Seconds 2 }
}
Write-Host ""
if (-not $ok) { Write-Host "L'application ne répond pas. Diagnostic : docker compose logs app" -ForegroundColor Red; Pause-Fin; exit 1 }

# le compte est créé : le mot de passe n'a plus à rester sur le disque
$lignes = (Get-Content $envFile) | ForEach-Object { if ($_ -like "MMT_ADMIN_PASSWORD=*") { "MMT_ADMIN_PASSWORD=" } else { $_ } }
[IO.File]::WriteAllText($envFile, (($lignes -join "`n") + "`n"), (New-Object Text.UTF8Encoding($false)))

Write-Host "Application démarrée. Sur ce PC : http://localhost:8000" -ForegroundColor Green
& (Join-Path $PSScriptRoot "adresse-windows.ps1")
