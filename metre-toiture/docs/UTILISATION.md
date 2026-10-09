# Guide d'utilisation

Le guide pratique complet (prise de vue, préparation, contrôle, correction, validation) est intégré à
l'application : menu **Guide de prise de vue**, ou bouton **Aide** à chaque étape d'un chantier. Ce document
résume le déroulement.

## Parcours type (reconstruction 3D)

| Étape | Où | Ce que vous faites | Ce que fait l'application |
|---|---|---|---|
| 1. Nouveau chantier | Tableau de bord → Nouveau chantier | Nom, client, adresse ; « enregistrer ma position » si vous êtes sur place | Référence `MT-AAAA-NNNN` |
| 2. Préparation | Onglet Préparation | Type de toit, dimensions approx., drone, précision, conditions | Plan de prise de vue : hauteur, lignes, orbites, nombre de photos, batteries, conseils, checklist terrain |
| 3. Vol | Sur le terrain | Suivre le plan ; mesurer une cote de référence | — |
| 4. Photos | Onglet Photos | Glisser-déposer le dossier de photos | Contrôle de chaque photo et de la série : problèmes et actions correctives ; exclusion en un clic |
| 5. Traitement | Onglet Traitement | Choisir le préréglage, lancer | Envoi au moteur 3D, suivi, durée estimée ; détection automatique des pans à la fin |
| 6. Métré | Onglet Métré | Contrôler chaque pan, corriger, ajouter la cote de référence, valider les pans | Surfaces, pentes, longueurs, contrôles de cohérence, confiance, comparaison auto/actuel |
| 7. Matériaux | Onglet Matériaux | Choisir les ouvrages, saisir les valeurs fabricant | Quantités, conditionnements, montants si prix saisis |
| 8. Validation | Onglet Validation & rapport | Cocher les confirmations, rédiger les réserves, valider | Checklist, rapport PDF, exports |

## L'éditeur de métré

* **Sélection** : touchez un pan (ses sommets apparaissent), une ligne (pour changer son type) ou un
  obstacle. Faites glisser un sommet : les sommets confondus des pans voisins suivent, l'aimant colle aux
  sommets et arêtes proches.
* **Pan** : dessinez un pan angle par angle. Avec un modèle 3D, sa pente est calculée automatiquement sur le
  modèle ; sinon saisissez-la (et désignez l'égout pour le sens de la pente).
* **Point** : ajoute un sommet sur une arête du pan sélectionné. Suppr supprime le sommet sélectionné.
* **Obstacle** : dessinez une fenêtre de toit ou une cheminée ; choisissez sa nature et s'il faut le déduire.
* **Cote réf.** : touchez les extrémités d'une longueur mesurée sur place et saisissez sa valeur réelle.
* **Mesurer** : distance réelle entre deux points (pente comprise), sans rien modifier.
* **Détecter** : relance la détection automatique autour du point touché (utile si le mauvais bâtiment a été
  choisi ou après une correction de la zone).
* **Vue 3D** : nuage de points et pans en 3D, pour vérifier visuellement.
* **Compléments / saisie** : lignes non dessinables (solins, gouttières hors plan), obstacles par
  dimensions, pans saisis par dimensions.
* Ctrl+Z / Ctrl+Y : annuler / rétablir. Ctrl+S : enregistrer. Chaque enregistrement crée une **version**
  consultable et restaurable (onglet Validation).

## Autres méthodes

* **Photo unique (estimation)** : importez une photo verticale, indiquez la hauteur du toit (et l'altitude de
  vol si elle n'est pas dans la photo), puis dessinez les pans sur la photo et saisissez les pentes.
* **Saisie manuelle** : pans par dimensions (rectangle, trapèze, triangle + rampant + pente) et lignes en
  mètres linéaires.

Ces métrés sont clairement identifiés comme « estimation » ou « saisie » dans l'application et le rapport.

## Duplication et historique

* **Dupliquer** un chantier copie les informations, le métré (pans à revalider) et les matériaux — pratique
  pour un bâtiment voisin identique ou une variante de devis.
* L'historique des actions (bouton Infos) trace imports, calculs, modifications et validations.

## Utilisation sur chantier

* Installez l'application sur l'écran d'accueil de la tablette ou du téléphone.
* Le guide et les plans de vol ouverts restent consultables sans réseau.
* L'import des photos depuis la tablette permet de contrôler la série **avant de quitter le chantier**.
