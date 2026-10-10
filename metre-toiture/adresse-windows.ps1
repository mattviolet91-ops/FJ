# Affiche l'adresse internet (https) de l'application, publiée par le tunnel Cloudflare.
Set-Location -Path $PSScriptRoot
$url = $null
for ($i = 0; $i -lt 60; $i++) {
  $journal = docker compose --profile internet logs tunnel 2>&1 | Out-String
  $m = [regex]::Matches($journal, "https://[a-z0-9-]+\.trycloudflare\.com")
  if ($m.Count -gt 0) { $url = $m[$m.Count - 1].Value; break }
  if ($journal -match "Registered tunnel connection" -and $journal -notmatch "trycloudflare") {
    Write-Host "Tunnel à adresse fixe actif : utilisez l'adresse configurée dans votre compte Cloudflare." -ForegroundColor Green
    Read-Host "Appuyez sur Entrée pour fermer" | Out-Null; exit 0
  }
  Start-Sleep -Seconds 2
}
if ($url) {
  Write-Host ""
  Write-Host "Adresse de l'application : $url" -ForegroundColor Green
  Write-Host "Elle est copiée dans le presse-papiers. Elle change si le PC ou Docker redémarre :"
  Write-Host "double-cliquez alors sur ADRESSE.bat pour obtenir la nouvelle."
  try { Set-Clipboard -Value $url } catch {}
  Start-Process $url
} else {
  Write-Host "Adresse introuvable. Journal du tunnel : docker compose --profile internet logs tunnel" -ForegroundColor Red
}
Read-Host "Appuyez sur Entrée pour fermer" | Out-Null
