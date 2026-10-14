// Place le modèle principal en tête de la chaîne de secours active.
// La config déclarative de FreeLLMAPI ne règle que la chaîne globale, alors que
// le routeur suit celle du profil actif ("Default") : on la règle via l'API.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(fs.readFileSync(path.join(here, 'freellmapi.config.json'), 'utf8'));
const primary = config.customProviders?.[0]?.models?.[0]?.model;
if (!primary) process.exit(0);
if (!config.admin) {
  console.warn('[principal] ADMIN_EMAIL/ADMIN_PASSWORD manquants : placez le modèle principal en tête à la main (page Fallback).');
  process.exit(0);
}

const base = `http://127.0.0.1:${process.env.PORT || 3001}`;
let token;
for (let i = 0; i < 60 && !token; i++) {
  try {
    const res = await fetch(`${base}/api/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(config.admin),
    });
    if (res.ok) token = (await res.json()).token;
    else if (res.status === 401) throw new Error('identifiants admin refusés');
  } catch (err) {
    if (err.message.includes('admin')) throw err;
  }
  if (!token) await new Promise(r => setTimeout(r, 1000));
}
if (!token) throw new Error('le serveur ne répond pas sur ' + base);

const auth = { authorization: `Bearer ${token}` };
const chain = await (await fetch(`${base}/api/fallback`, { headers: auth })).json();
const row = chain.find(r => r.platform === 'custom' && r.modelId === primary);
if (!row) throw new Error(`modèle principal "${primary}" absent de la chaîne`);

// Priorité 0 : devant toutes les lignes du catalogue (qui commencent à 1).
const res = await fetch(`${base}/api/fallback`, {
  method: 'PUT',
  headers: { ...auth, 'content-type': 'application/json' },
  body: JSON.stringify([{ modelDbId: row.modelDbId, priority: 0, enabled: true }]),
});
if (!res.ok) throw new Error(`mise à jour de la chaîne refusée : HTTP ${res.status}`);
await fetch(`${base}/api/auth/logout`, { method: 'POST', headers: auth }).catch(() => {});
console.log(`[principal] ${primary} est en tête de la chaîne ; bascule vers les modèles gratuits sur 429/5xx.`);
