#!/usr/bin/env bash
# Affiche l'adresse internet (https) de l'application, publiée par le tunnel Cloudflare.
cd "$(dirname "$0")"
for _ in $(seq 1 60); do
  URL=$(docker compose --profile internet logs tunnel 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
  if [ -n "$URL" ]; then
    echo
    echo "Adresse de l'application : $URL"
    echo "(elle change si le PC ou Docker redémarre : relancez ./adresse.sh pour l'obtenir)"
    exit 0
  fi
  if docker compose --profile internet logs tunnel 2>/dev/null | grep -q "Registered tunnel connection"; then
    echo "Tunnel à adresse fixe actif : utilisez l'adresse configurée dans votre compte Cloudflare."
    exit 0
  fi
  sleep 2
done
echo "Adresse introuvable. Journal du tunnel : docker compose --profile internet logs tunnel" >&2
exit 1
