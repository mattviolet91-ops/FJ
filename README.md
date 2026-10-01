# FJ Couverture – site vitrine

Site vitrine pour FJ Couverture (couvreur), en deux versions :

| Dossier | Contenu |
|---|---|
| `index.html` + `assets/` | Version HTML/CSS statique (publiable sur GitHub Pages) |
| `wordpress/fj-couverture/` | Le même site sous forme de thème WordPress |
| `fj-couverture-theme.zip` | Le thème prêt à installer |

## Voir le site statique
Ouvrir `index.html` dans un navigateur, ou activer **GitHub Pages** sur le dépôt `FJ` :
Settings → Pages → Branch `main` / `(root)` → Save.
Le site sera alors visible à l'adresse `https://mattviolet91-ops.github.io/FJ/`.

Couleurs : noir et bronze (variables en haut de `assets/css/style.css`).

## À personnaliser avant mise en ligne
- Téléphone `00 00 00 00 00` et e-mail `contact@exemple.fr` (dans `index.html`)
- Photos des réalisations (actuellement des visuels provisoires)
- Mentions légales (obligatoires : SIRET, assurance décennale, etc.)

## Installer sur WordPress (auto-hébergé)
1. Tableau de bord WordPress → **Apparence → Thèmes → Ajouter → Téléverser un thème**
2. Choisir `fj-couverture-theme.zip` → Installer → **Activer**
3. **Réglages → Lecture** : « La page d'accueil affiche » → *Une page statique*
   (créer une page vide « Accueil » et la choisir). Le thème affiche automatiquement le site vitrine.
4. **Apparence → Personnaliser → Coordonnées FJ Couverture** : saisir téléphone, e-mail, zone, horaires.
5. (Optionnel) Ajouter un logo dans *Identité du site* et un menu dans *Menus* (emplacement « Menu principal »).

Le formulaire de devis envoie un e-mail via `wp_mail()` à l'adresse saisie dans le Personnaliseur.
Si les e-mails n'arrivent pas, installer une extension SMTP (ex. WP Mail SMTP).

## Mettre à jour le thème zip
```
cd wordpress && zip -r ../fj-couverture-theme.zip fj-couverture
```
