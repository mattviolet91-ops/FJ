#!/usr/bin/env bash
# Démarre FreeLLMAPI (API + tableau de bord sur http://localhost:3001).
# La config est régénérée depuis freellmapi/.env à chaque démarrage.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${FREELLMAPI_DIR:-$HOME/freellmapi}"
node "$HERE/generate-config.mjs"
cd "$DIR"
FREEAPI_CONFIG_PATH="$HERE/freellmapi.config.json" node server/dist/index.js &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' INT TERM
node "$HERE/prioritize-primary.mjs" || echo "[principal] échec : $?" >&2
wait $SERVER
