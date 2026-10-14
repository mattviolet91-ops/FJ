// Génère freellmapi.config.json (config déclarative appliquée à chaque démarrage)
// à partir des variables de freellmapi/.env.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const env = {};
const envFile = path.join(here, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*([^#]*?)\s*(#.*)?$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}
const get = (name) => (process.env[name] ?? env[name] ?? '').trim();

const config = {
  // "priority" : le routeur suit l'ordre exact de la chaîne de secours,
  // donc le modèle principal passe toujours en premier tant qu'il n'est pas limité.
  routing: { strategy: 'priority' },
};

if (get('ADMIN_EMAIL') && get('ADMIN_PASSWORD')) {
  config.admin = { email: get('ADMIN_EMAIL'), password: get('ADMIN_PASSWORD') };
}

const freeKeys = [
  ['groq', 'GROQ_API_KEY'],
  ['google', 'GEMINI_API_KEY'],
  ['openrouter', 'OPENROUTER_API_KEY'],
  ['cerebras', 'CEREBRAS_API_KEY'],
  ['mistral', 'MISTRAL_API_KEY'],
  ['github', 'GITHUB_MODELS_TOKEN'],
];
config.keys = [
  // Fournisseurs gratuits sans clé : toujours activés, ils garantissent un secours.
  { platform: 'kilo' },
  { platform: 'ovh' },
  ...freeKeys
    .filter(([, name]) => get(name))
    .map(([platform, name]) => ({ platform, key: get(name), label: 'gratuit' })),
];

const primaryUrl = get('PRIMARY_BASE_URL');
const primaryModel = get('PRIMARY_MODEL');
if (primaryUrl && primaryModel) {
  config.customProviders = [{
    baseUrl: primaryUrl,
    ...(get('PRIMARY_API_KEY') ? { apiKey: get('PRIMARY_API_KEY') } : {}),
    label: 'Principal',
    models: [{ model: primaryModel, displayName: `${primaryModel} (principal)`, supportsTools: true, fallbackEnabled: true }],
  }];
  // Priorité 1 dans la chaîne globale. La chaîne du profil actif est réglée
  // par prioritize-primary.mjs au démarrage (start.sh).
  config.fallback = [{ platform: 'custom', modelId: primaryModel, endpoint: primaryUrl, priority: 1 }];
} else if (primaryUrl || primaryModel) {
  console.warn('PRIMARY_BASE_URL et PRIMARY_MODEL doivent être renseignés ensemble — modèle principal ignoré.');
}

const out = path.join(here, 'freellmapi.config.json');
fs.writeFileSync(out, JSON.stringify(config, null, 2) + '\n', { mode: 0o600 });
console.log(`Config écrite : ${out}`);
console.log(`  modèle principal : ${config.customProviders ? primaryModel : '(aucun — gratuits uniquement)'}`);
console.log(`  clés gratuites   : ${config.keys.slice(2).map(k => k.platform).join(', ') || '(aucune — Kilo et OVH sans clé seulement)'}`);
