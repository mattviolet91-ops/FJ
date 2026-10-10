#!/usr/bin/env bash
# Installation de Matt's Métré Toiture sur un PC Linux ou Mac avec Docker.
# Usage :  ./installer.sh            (accès par internet via un tunnel HTTPS)
#          ./installer.sh --local    (accès sur le réseau local uniquement)
set -euo pipefail
cd "$(dirname "$0")"

PROFIL="--profile internet"
[ "${1:-}" = "--local" ] && PROFIL=""

if ! docker info >/dev/null 2>&1; then
  echo "Docker n'est pas démarré ou pas installé : installez Docker Desktop (ou Docker Engine) puis relancez." >&2
  exit 1
fi

if [ ! -f .env ] || ! grep -q '^MMT_ADMIN_EMAIL=.' .env; then
  echo "Création du compte administrateur de l'application"
  read -r -p "  E-mail : " EMAIL
  while true; do
    read -r -s -p "  Mot de passe (10 caractères minimum) : " MDP; echo
    read -r -s -p "  Confirmez le mot de passe : " MDP2; echo
    if [ "${#MDP}" -lt 10 ]; then echo "  Trop court."; continue; fi
    if [ "$MDP" != "$MDP2" ]; then echo "  Les deux saisies diffèrent."; continue; fi
    case "$MDP" in *"'"*) echo "  L'apostrophe ' n'est pas acceptée dans ce mot de passe."; continue;; esac
    break
  done
  umask 077
  cat > .env <<EOF
MMT_COOKIE_SECURE=true
MMT_ADMIN_EMAIL='$EMAIL'
MMT_ADMIN_PASSWORD='$MDP'
EOF
fi

echo "Construction et démarrage (la première fois : 10 à 20 minutes de téléchargement)…"
docker compose $PROFIL up -d --build

echo -n "Attente du démarrage de l'application"
for _ in $(seq 1 120); do
  if curl -fs http://localhost:8000/api/sante >/dev/null 2>&1; then break; fi
  echo -n "."; sleep 2
done
echo
curl -fs http://localhost:8000/api/sante >/dev/null || { echo "L'application ne répond pas : docker compose logs app" >&2; exit 1; }

# le compte est créé : le mot de passe n'a plus à rester sur le disque
sed -i.bak "s/^MMT_ADMIN_PASSWORD=.*/MMT_ADMIN_PASSWORD=/" .env && rm -f .env.bak

echo "Application démarrée : http://localhost:8000 (sur ce PC)"
[ -n "$PROFIL" ] && ./adresse.sh
