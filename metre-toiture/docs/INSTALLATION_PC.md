# Installer l'application sur le PC de l'entreprise (Windows)

Résultat : l'application tourne sur votre PC et reste accessible **depuis le chantier** (téléphone, tablette)
par une adresse `https://….trycloudflare.com`, sans ouvrir de port sur votre box et sans frais.

## Ce qu'il faut

* Un PC Windows 10/11 avec **16 Go de mémoire** (8 Go minimum pour de petits chantiers) et ~30 Go libres.
* Le PC doit rester **allumé** pour que l'application soit joignable.

## Étapes

1. **Installer Docker Desktop** : <https://www.docker.com/products/docker-desktop/>. Acceptez l'option WSL 2
   proposée, redémarrez si demandé, puis lancez Docker Desktop. Dans ses réglages, cochez « Start Docker
   Desktop when you sign in » (démarrage automatique).
   *Docker Desktop est gratuit pour les entreprises de moins de 250 salariés et 10 M$ de chiffre d'affaires.*
2. **Récupérer l'application** : sur GitHub, dépôt `mattviolet91-ops/FJ`, choisissez la branche
   `metre-toiture`, bouton « Code » → « Download ZIP ». Décompressez-le, par exemple dans `C:\MattsMetre`.
3. **Installer** : ouvrez le dossier `metre-toiture` et double-cliquez sur **`INSTALLER.bat`**.
   * Saisissez l'e-mail et le mot de passe du compte administrateur (10 caractères minimum).
   * La première fois, le téléchargement et la construction prennent 10 à 20 minutes.
4. **Le lien s'affiche** à la fin (et s'ouvre dans le navigateur) : `https://xxxx-xxxx.trycloudflare.com`.
   Il est copié dans le presse-papiers : envoyez-le sur votre téléphone, ajoutez-le à l'écran d'accueil.

## Au quotidien

* **Après un redémarrage du PC**, l'application redémarre seule mais **l'adresse change** :
  double-cliquez sur **`ADRESSE.bat`** pour obtenir la nouvelle.
* Sur le PC lui-même, l'application est aussi à <http://localhost:8000>.
* Mise à jour : téléchargez la nouvelle version au même endroit, puis relancez `INSTALLER.bat`
  (les chantiers sont conservés).

## Avoir une adresse fixe (recommandé ensuite)

Avec un nom de domaine (ex. `metre.mattscouverture.fr`) et un compte Cloudflare gratuit :
Cloudflare Zero Trust → Networks → Tunnels → créer un tunnel « cloudflared », recopier le **jeton**, et ajouter
une « Public hostname » pointant vers `http://app:8000`. Puis ajoutez dans le fichier `.env` :

```
CLOUDFLARE_TUNNEL_TOKEN=le-jeton
TUNNEL_COMMANDE=tunnel --no-autoupdate run
```

et relancez `INSTALLER.bat`. L'adresse ne changera plus.

## Sécurité

* L'adresse est publique : seul le **mot de passe** protège les données. Choisissez-le long et ne le
  partagez pas ; créez un compte par personne (Paramètres → Utilisateurs).
* Le compte administrateur est créé pendant l'installation : personne ne peut « prendre » l'application avant
  vous. Le mot de passe est ensuite effacé du fichier `.env`.
* Le trafic est chiffré (HTTPS) de bout en bout jusqu'à votre PC.
* Faites des sauvegardes complètes régulières (Paramètres → Sauvegardes) et copiez-les hors du PC.

## Si ça ne marche pas

* « Docker Desktop n'est pas démarré » : lancez Docker Desktop et attendez qu'il indique « Running ».
* Calcul 3D qui échoue faute de mémoire : créez le fichier `C:\Users\<vous>\.wslconfig` contenant
  `[wsl2]` puis `memory=12GB` sur la ligne suivante, et redémarrez le PC.
* Diagnostic : dans le dossier `metre-toiture`, `docker compose logs app` et
  `docker compose --profile internet logs tunnel`.
