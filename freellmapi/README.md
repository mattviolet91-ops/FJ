# FreeLLMAPI — bascule automatique vers des modèles gratuits

Installe [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) (proxy local
compatible OpenAI) et le règle ainsi :

1. **Votre modèle principal** (facultatif, n'importe quelle API compatible OpenAI) est essayé en premier.
2. Dès qu'il répond **429 « limite atteinte »** (ou une erreur 5xx), la requête
   repart **automatiquement** vers le premier modèle gratuit disponible — sans erreur côté application.
3. Le principal est mis en pause le temps de sa limite, puis redevient prioritaire tout seul.

Stratégie de routage : `priority` (ordre strict de la chaîne). Les fournisseurs
gratuits sans clé (Kilo, OVHcloud) sont toujours activés comme filet de sécurité ;
chaque clé gratuite ajoutée (Groq, Gemini, OpenRouter…) élargit le pool.

## Installation

Prérequis : Node.js 20 à 24, git.

```bash
cd freellmapi
./install.sh          # clone dans ~/freellmapi, compile, crée la clé de chiffrement
nano .env             # modèle principal, clés gratuites, compte admin
./start.sh            # http://localhost:3001
```

`install.sh` peut être relancé pour mettre à jour (`FREELLMAPI_REF=main ./install.sh`
pour la dernière version ; par défaut, la version testée est utilisée).

## Utilisation

Récupérez la **clé unifiée** (`freellmapi-…`) dans le tableau de bord, page **Keys**, puis :

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:3001/v1", api_key="freellmapi-...")
r = client.chat.completions.create(model="auto", messages=[{"role": "user", "content": "Bonjour"}])
```

Les en-têtes de réponse indiquent ce qui s'est passé :
`X-Routed-Via` (modèle qui a répondu) et `X-Fallback-Trail` (ex. `custom/mon-modele key1=rate_limited`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `install.sh` | Installe / met à jour FreeLLMAPI depuis GitHub |
| `start.sh` | Démarre le serveur et met le modèle principal en tête de chaîne |
| `.env.example` | Modèle de configuration (copié en `.env`, jamais committé) |
| `generate-config.mjs` | `.env` → `freellmapi.config.json` (config appliquée à chaque démarrage) |
| `prioritize-primary.mjs` | Place le modèle principal en tête de la chaîne du profil actif |

`.env` et `freellmapi.config.json` contiennent vos clés : ils sont ignorés par git.
La clé de chiffrement est dans `~/freellmapi/.env` — sauvegardez-la, sans elle les clés stockées sont illisibles.

## Limites

- FreeLLMAPI est prévu pour un usage personnel, pas pour la production ; ne l'exposez pas sur Internet.
- Les modèles gratuits sont moins puissants et leurs quotas varient ; ils se réinitialisent en général à minuit UTC.
- Certains fournisseurs gratuits (dont Kilo) journalisent les requêtes : n'y envoyez pas de données sensibles.
