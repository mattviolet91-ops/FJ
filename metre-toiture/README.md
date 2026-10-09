# Matt's Métré Toiture

Application web de **métré de toiture à partir de photos de drone** pour Matt's Couverture :
reconstruction 3D (OpenDroneMap), détection automatique des pans, surfaces, pentes et longueurs,
correction manuelle, calcul des matériaux, rapport PDF et exports — avec un **guide de prise de vue
intégré** accessible à chaque étape.

![Capture](docs/captures/metre.png)

## En bref

* **Guide interactif** : prise de vue (hauteur, angles, orbites, recouvrement, exemples bons/mauvais,
  calculateur de taille de pixel), assistant de préparation avec plan de vol personnalisé, contrôle des photos
  à l'import, aide à la correction, checklist avant devis. Aide contextuelle sans quitter le chantier.
* **Reconstruction 3D réelle** via NodeODM (local, distant ou service compatible), file persistée avec reprise
  automatique, estimation de durée recalée sur l'historique.
* **Détection automatique des pans** sur le modèle de surface : plans, contours régularisés, faîtages /
  arêtiers / noues calés sur l'intersection des plans, émergences (cheminées).
* **Éditeur** 2D (souris et tactile) + vue 3D : sommets aimantés et liés, ajout/suppression de points,
  dessin de pans et d'obstacles, cote de référence (échelle), mesure, requalification des lignes,
  annuler/rétablir, versions restaurables.
* **Honnêteté des mesures** : chaque valeur indique sa source (modèle 3D, estimation, saisie), chaque pan
  un niveau de confiance justifié ; échelle non vérifiée signalée ; contrôles de cohérence ; aucune valeur
  par défaut inventée pour les matériaux.
* **Matériaux** : ouvrages paramétrables (tuiles, ardoises, zinguerie…), formules sur vos paramètres fabricant,
  pertes, conditionnements, prix.
* **Rapport PDF** (plan annoté, détail, matériaux, qualité des données, réserves) et **exports** CSV, DXF,
  OBJ, GeoJSON, JSON et format « devis » pour le futur connecteur.
* Également : mode photo unique (estimation), saisie manuelle, duplication de chantier, historique,
  sauvegardes automatiques, comptes utilisateurs, application installable (PWA) utilisable sur chantier.

## Démarrer

```bash
cd metre-toiture
docker compose up -d --build      # application + moteur 3D
# puis http://localhost:8000 (création du compte administrateur à la première visite)
```

Détails : [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Documentation

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Choix techniques justifiés (moteur 3D, stack, sécurité), algorithmes |
| [INSTALLATION.md](docs/INSTALLATION.md) | Installation Docker / manuelle, HTTPS, variables, mises à jour |
| [UTILISATION.md](docs/UTILISATION.md) | Parcours type, éditeur, modes sans 3D |
| [MAINTENANCE_COUTS.md](docs/MAINTENANCE_COUTS.md) | Sauvegardes, entretien, coûts d'hébergement, RGPD |
| [VALIDATION.md](docs/VALIDATION.md) | Tests automatisés et essai réel avec OpenDroneMap |
| [LIMITES.md](docs/LIMITES.md) | Limites connues et pistes d'évolution |
| [INTEGRATION_DEVIS.md](docs/INTEGRATION_DEVIS.md) | Format d'échange avec le logiciel de devis |

## Développement

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest     # API + calculs
cd frontend && npm ci && npm test && npm run build                        # interface
```

Structure : `backend/mmt/core` (calculs purs : géométrie, détection des pans, métré, photos, plan de vol,
matériaux, validation), `backend/mmt/services` (NodeODM, modèle 3D, file de traitements, PDF, exports,
sauvegardes), `backend/mmt/api` (routes), `frontend/src` (interface, guide, éditeur).
