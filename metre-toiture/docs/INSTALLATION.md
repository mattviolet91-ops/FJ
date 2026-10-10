# Installation

> L'application **ne peut pas** tourner sur un hébergement WordPress mutualisé : elle a besoin d'un
> processus Python permanent et le calcul 3D demande plusieurs Go de mémoire. Le site vitrine reste sur
> son hébergement actuel ; l'application s'installe à part (sous-domaine conseillé, ex.
> `metre.mattscouverture.fr`).

## Le plus simple : le PC de l'entreprise

Double-clic sur `INSTALLER.bat` (Windows) ou `./installer.sh` (Linux/Mac) : l'application démarre et une
adresse internet HTTPS s'affiche. Pas à pas : [INSTALLATION_PC.md](INSTALLATION_PC.md).

## Option A — tout sur un serveur avec Docker

Prérequis : une machine Linux (ou Windows/Mac avec Docker Desktop) avec **au moins 4 cœurs et 16 Go de
mémoire** si elle fait aussi les calculs 3D (8 Go suffisent pour de petits jeux de photos en préréglage
« Aperçu »), et de l'espace disque (compter 1 à 3 Go par chantier : photos + modèle).

```bash
git clone <dépôt> && cd FJ/metre-toiture
docker compose up -d --build
```

Ouvrez `http://<adresse-du-serveur>:8000` : la première visite propose de créer le compte administrateur.

Pour créer l'administrateur sans interface (installation automatisée) :

```bash
MMT_ADMIN_EMAIL=matt@exemple.fr MMT_ADMIN_PASSWORD='un-mot-de-passe-long' docker compose up -d
```

### Accès HTTPS (indispensable si l'application est accessible depuis Internet)

Placez un reverse proxy devant le port 8000 (Caddy est le plus simple : certificat Let's Encrypt
automatique) :

```
# /etc/caddy/Caddyfile
metre.mattscouverture.fr {
    reverse_proxy 127.0.0.1:8000
    request_body {
        max_size 2GB
    }
}
```

Puis définissez `MMT_COOKIE_SECURE=true` (fichier `.env` à côté de `docker-compose.yml`) et relancez.
Dans `docker-compose.yml`, remplacez `"8000:8000"` par `"127.0.0.1:8000:8000"` pour que seul le proxy y accède.

## Option B — calcul 3D sur une autre machine

L'application (petite machine, 2 Go de RAM suffisent) et NodeODM (machine puissante) peuvent être séparés :

* sur la machine de calcul : `docker run -d -p 3000:3000 opendronemap/nodeodm --token <jeton-secret>`
  (n'exposez ce port qu'au serveur applicatif : pare-feu, VPN ou réseau privé) ;
* dans l'application : **Paramètres → Serveur de calcul**, adresse `http://<machine>:3000` et jeton,
  bouton « Tester ».

La machine de calcul peut être un PC de bureau allumé à la demande ou un serveur loué à l'heure : les
traitements en attente démarrent automatiquement dès qu'il répond.

Un service compatible NodeODM (par exemple WebODM Lightning, payant) peut aussi être utilisé : renseignez
son adresse et votre jeton. **Les photos des clients sont alors envoyées à ce prestataire.**

## Option C — installation sans Docker (développement)

```bash
# API
cd metre-toiture/backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest            # tests
uvicorn mmt.main:app --reload --port 8000

# Interface (autre terminal)
cd metre-toiture/frontend
npm ci
npm run dev                 # http://localhost:5173 (l'API est relayée vers le port 8000)
npm run build               # version de production servie par l'API (frontend/dist)

# Moteur 3D
docker run -d -p 3000:3000 opendronemap/nodeodm
```

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `MMT_DATA_DIR` | `backend/data` (`/data` en Docker) | Base SQLite, photos, modèles, sauvegardes |
| `MMT_DATABASE_URL` | SQLite dans `MMT_DATA_DIR` | ex. `postgresql+psycopg://user:mdp@hote/mmt` (installer `psycopg[binary]`) |
| `MMT_NODEODM_URL` | `http://localhost:3000` | Serveur de calcul (modifiable dans l'interface) |
| `MMT_NODEODM_TOKEN` | vide | Jeton du serveur de calcul |
| `MMT_COOKIE_SECURE` | `false` | `true` derrière HTTPS |
| `MMT_SESSION_JOURS` | `14` | Durée des sessions |
| `MMT_MAX_PHOTO_MO` | `60` | Taille maximale d'une photo |
| `MMT_SAUVEGARDE_AUTO` | `true` | Sauvegarde quotidienne de la base |
| `MMT_SAUVEGARDES_A_GARDER` | `14` | Rotation des sauvegardes |
| `MMT_ADMIN_EMAIL` / `MMT_ADMIN_PASSWORD` | — | Création de l'administrateur au premier démarrage |
| `MMT_WORKER` | `true` | Désactiver la file de traitements (tests) |

## Mises à jour

```bash
cd FJ/metre-toiture
git pull
docker compose up -d --build        # la base est migrée/complétée automatiquement au démarrage
docker compose pull nodeodm && docker compose up -d nodeodm   # moteur 3D
```

Faites une sauvegarde complète (Paramètres → Sauvegardes) avant chaque mise à jour.

## Installation sur tablette / téléphone

Ouvrez l'adresse de l'application dans le navigateur, puis « Ajouter à l'écran d'accueil ». Le guide et
les plans de vol déjà consultés restent accessibles sans réseau sur le chantier.
