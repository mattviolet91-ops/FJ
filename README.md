# F.J Renovtoit – site vitrine

Couvreur à Savigny-sur-Orge : couverture, zinguerie, rénovation, ravalement.
Thème sombre noir et or, reprenant la carte de visite de l'entreprise.

| Fichier / dossier | Contenu |
|---|---|
| `index.html` + `assets/` | Le site (publié sur GitHub Pages) |
| `wordpress/fj-renovtoit/` | Le même site sous forme de thème WordPress |
| `fj-renovtoit-theme.zip` | Le thème prêt à téléverser dans WordPress |
| `tools/build-wordpress.py` | Régénère le thème et le zip à partir de `index.html` |

## Voir le site en ligne
https://mattviolet91-ops.github.io/FJ/
(activé dans Settings → Pages → Deploy from a branch → `main` / `(root)`)

## Modifier le site
1. Modifier `index.html` et/ou `assets/css/style.css`
2. Lancer `python3 tools/build-wordpress.py` pour mettre à jour le thème WordPress et le zip

## Installer sur WordPress (auto-hébergé)
1. **Apparence → Thèmes → Ajouter → Téléverser un thème** → `fj-renovtoit-theme.zip` → Installer → **Activer**
2. **Réglages → Lecture** → « Une page statique » (créer une page vide « Accueil » et la choisir)
3. **Apparence → Personnaliser → Coordonnées F.J Renovtoit** : vérifier téléphone, e-mail, adresse

Le formulaire de devis envoie un e-mail via `wp_mail()`. Si les e-mails n'arrivent pas,
installer une extension SMTP (ex. WP Mail SMTP).

## À compléter
- Mentions légales (obligatoires : SIRET, assurance décennale, hébergeur…)
- Photos de vrais chantiers (les visuels actuels viennent de la carte de visite)
