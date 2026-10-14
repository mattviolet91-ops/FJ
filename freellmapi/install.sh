#!/usr/bin/env bash
# Installe FreeLLMAPI depuis GitHub et le configure avec bascule automatique
# vers les modèles gratuits quand le modèle principal atteint sa limite.
#
#   ./install.sh                 # installe dans ~/freellmapi
#   FREELLMAPI_DIR=/opt/x ./install.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${FREELLMAPI_DIR:-$HOME/freellmapi}"
REPO="https://github.com/tashfeenahmed/freellmapi.git"
# Version testée ; mettez FREELLMAPI_REF=main pour la toute dernière.
REF="${FREELLMAPI_REF:-bf1660454fd4e1889fe0c1b5cd10f2af6605afa0}"

command -v node >/dev/null || { echo "Node.js 20+ est requis (https://nodejs.org)"; exit 1; }
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] && [ "$NODE_MAJOR" -lt 25 ] || { echo "Node.js 20 à 24 requis (trouvé : $(node -v))"; exit 1; }

if [ -d "$DIR/.git" ]; then
  echo "→ Mise à jour de $DIR"
  git -C "$DIR" fetch --quiet origin
else
  echo "→ Clonage de $REPO dans $DIR"
  git clone --quiet "$REPO" "$DIR"
fi
git -C "$DIR" checkout --quiet "$REF"

echo "→ Installation des dépendances et compilation (quelques minutes)"
(cd "$DIR" && npm ci --no-audit --no-fund && npm run build)

# Clé de chiffrement des clés API : générée une seule fois, puis conservée.
if ! grep -q '^ENCRYPTION_KEY=' "$DIR/.env" 2>/dev/null; then
  KEY="$(node -e 'console.log(require("crypto").randomBytes(32).toString("hex"))')"
  printf 'ENCRYPTION_KEY=%s\nPORT=3001\nNODE_ENV=production\n' "$KEY" >> "$DIR/.env"
  chmod 600 "$DIR/.env"
  echo "→ Clé de chiffrement créée dans $DIR/.env (à sauvegarder)"
fi

[ -f "$HERE/.env" ] || { cp "$HERE/.env.example" "$HERE/.env"; chmod 600 "$HERE/.env"; \
  echo "→ $HERE/.env créé : renseignez-y votre modèle principal et vos clés gratuites"; }
node "$HERE/generate-config.mjs"

echo
echo "Installation terminée. Lancez :  $HERE/start.sh"
