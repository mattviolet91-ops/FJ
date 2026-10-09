# Architecture et choix techniques

## Vue d'ensemble

```
 Navigateur (PC, tablette, téléphone)            Serveur applicatif                 Serveur de calcul 3D
 ┌───────────────────────────────┐   HTTPS    ┌─────────────────────────────┐ HTTP  ┌──────────────────────┐
 │ React + TypeScript (PWA)      │──────────▶ │ FastAPI (Python)            │─────▶ │ NodeODM / OpenDroneMap│
 │ • tableau de bord, guide      │            │ • API REST + fichiers       │       │ (Docker, local ou     │
 │ • éditeur de plan (SVG)       │            │ • file de traitements       │       │  distant, ou service  │
 │ • vue 3D (three.js)           │            │   persistée (reprise)       │       │  compatible)          │
 └───────────────────────────────┘            │ • détection des pans (MNS)  │       └──────────────────────┘
                                              │ • calcul du métré, matériaux│
                                              │ • PDF (ReportLab), exports  │
                                              │ SQLite (ou PostgreSQL)      │
                                              │ photos / modèles sur disque │
                                              └─────────────────────────────┘
```

Un seul processus applicatif sert l'API et l'interface compilée. Le calcul photogrammétrique, lourd
(plusieurs Go de mémoire, des dizaines de minutes de CPU), tourne dans un service séparé que l'on peut
placer sur une machine plus puissante ou démarrer à la demande.

## Choix du moteur de photogrammétrie

| Critère | OpenDroneMap (NodeODM) | COLMAP (+ OpenMVS) | Meshroom (AliceVision) | Logiciels commerciaux (Pix4D, Metashape, RealityCapture) |
|---|---|---|---|---|
| Licence | AGPL-3.0, gratuit | BSD / AGPL (OpenMVS) | MPL-2.0 | Licences payantes (abonnement ou perpétuelle) |
| Sorties utiles au métré | MNS (GeoTIFF), orthophoto, nuage géoréférencé, rapport qualité | Nuage / maillage non géoréférencés : chaîne à assembler soi-même | Maillage texturé, pas de MNS ni d'orthophoto | Complètes |
| Géoréférencement GPS / GCP | Natif (EXIF, gcp_list.txt) | À développer | Limité | Natif |
| Exploitation serveur | API REST prête (NodeODM), Docker officiel, file d'attente, ClusterODM | Ligne de commande, GPU recommandé | Interface graphique, GPU NVIDIA requis | Poste de travail, API selon édition |
| Maintenance | Projet actif, communauté importante | Actif | Actif | Éditeurs |

**Décision : OpenDroneMap via l'API NodeODM.** C'est la seule option libre qui fournit directement, à partir
de photos de drone géolocalisées, un modèle numérique de surface et une orthophoto géoréférencés — exactement
les données nécessaires au métré — avec une API de traitement asynchrone prête à l'emploi. COLMAP est
excellent pour la reconstruction mais imposerait de développer le géoréférencement, le MNS et l'orthophoto.

Licence : l'application dialogue avec NodeODM par le réseau sans en modifier le code ; l'AGPL n'impose
donc pas de publier le code de l'application. Si NodeODM/ODM étaient modifiés et proposés à des tiers via
le réseau, les modifications devraient être publiées.

Le client NodeODM de l'application fonctionne avec : un NodeODM local (Docker), un serveur dédié,
ClusterODM (plusieurs nœuds) ou un service compatible (ex. WebODM Lightning, payant, avec jeton).

## Chaîne de traitement

1. **Import** : contrôle du format, empreinte SHA-256 (doublons exacts), lecture EXIF/XMP (GPS, altitude
   relative, orientation de nacelle, focale), netteté (variance du laplacien sur les zones texturées),
   exposition, empreinte perceptuelle (doublons de cadrage), miniature.
2. **Analyse de la série** : nombre, netteté relative à la série, exposition, doublons, GPS, angles,
   couverture en 8 secteurs autour du point visé (estimé par moindres carrés sur les rayons de visée des
   obliques), recouvrement des verticales (GPS + altitude + optique), taille du pixel au sol. Chaque
   conclusion « non évaluable » est affichée comme telle.
3. **Reconstruction** (traitement persistant, repris après redémarrage) : création de la tâche NodeODM,
   envoi des photos par lots (reprise de l'envoi), suivi, téléchargement de l'archive restreinte aux
   sorties utiles (`outputs`), extraction du MNS, de l'orthophoto, du nuage de points et du rapport ODM.
4. **Préparation du modèle** : repère local métrique (Est/Nord − origine arrondie, en projection UTM du
   modèle), cache du nuage sous-échantillonné (≤ 6 M points).
5. **Détection automatique des pans** (`mmt/core/segmentation.py`) sur le MNS recadré autour du bâtiment
   (position GPS du chantier, point touché par l'utilisateur ou centre du modèle) :
   - lissage, normales locales par gradient ;
   - isolement du bâtiment (cellules à plus de 1,8 m du sol, composante connexe) ;
   - extraction itérative de plans par RANSAC « un point + normale » avec contrainte de connexité, puis
     moindres carrés ;
   - comblement des bords, fusion des régions coplanaires partageant une vraie frontière, séparation des
     régions reliées par un point ;
   - contour exact des régions, simplification, puis **régularisation** : chaque arête commune à deux pans
     est remplacée par la droite d'intersection des deux plans (faîtages, arêtiers, noues exacts), les
     bords libres sont ajustés sur le contour et recalés sur l'orientation dominante du bâtiment ;
   - soudure des sommets voisins entre pans ;
   - émergences (cheminées…) : cellules à plus de 25 cm au-dessus du plan du pan.
6. **Métré** (`mmt/core/metre.py`, `geometry.py`) : surface réelle = surface projetée × √(1 + a² + b²),
   classification des lignes par le sens des pentes, longueurs 3D, déductions, contrôles de cohérence,
   confiance par pan, incertitude indicative, comparaison automatique/manuel.

Validation sur toitures synthétiques bruitées (tests automatisés) : deux pans, quatre pans et toit en L
(8 pans, noues) — surfaces à moins de 1 % de la valeur exacte, classification des lignes correcte.

## Données

* `chantiers` : informations, statut, préparation et plan de vol, analyse des photos, modèle, matériaux,
  confirmations, réserves.
* `versions_metre` : **chaque enregistrement crée une version** (document JSON complet + résumé) — historique
  des corrections, restauration possible, comparaison automatique / manuel.
* `traitements` : file persistée (état interne pour la reprise : identifiant NodeODM, photos envoyées).
* `photos`, `ouvrages` (catalogue), `parametres`, `journal` (traçabilité), `utilisateurs`, `sessions`.

Le document de métré (JSON) contient : repère, échelle (cotes de référence), pans (contour en plan +
plan z = ax + by + c, ou saisie par dimensions), types de lignes forcés, lignes saisies, obstacles,
instantané de la détection automatique. Toutes les grandeurs sont **recalculées par le serveur** :
aucune valeur dérivée n'est stockée comme vérité.

## Sécurité

* Mots de passe hachés (scrypt, sel aléatoire), 10 caractères minimum, limitation des tentatives.
* Session par jeton aléatoire (seul son hachage est stocké) en cookie `HttpOnly`, `SameSite=Lax`,
  `Secure` en production ; en-tête anti-CSRF obligatoire pour toute requête modifiante.
* Contrôle des fichiers importés (taille, format réellement lisible), noms de fichiers assainis,
  chemins de téléchargement vérifiés, formules de matériaux évaluées sans `eval` (arbre syntaxique filtré).
* Archivage réversible ; suppression définitive uniquement avec saisie de la référence du chantier.
* Données hébergées chez vous : aucune donnée client n'est envoyée à un tiers, sauf si vous configurez un
  service de calcul externe (les photos y sont alors transmises).

## Interface

* React 18 + TypeScript + Vite, sans bibliothèque d'interface (CSS propre, charte #2BABE2 / gris / blanc).
* Éditeur de plan en SVG : souris et tactile (pincer pour zoomer), sommets aimantés et **liés entre pans**
  (une arête commune reste commune), annuler/rétablir, calcul en direct par le serveur.
* Vue 3D three.js chargée à la demande (nuage de points + pans + lignes).
* Application installable (PWA) : le guide et les écrans déjà ouverts restent consultables hors réseau.
