# Validation

## 1. Tests automatisés

```bash
cd backend && python -m pytest      # 28 tests
cd frontend && npm test             # 3 tests (géométrie de l'éditeur)
```

| Domaine | Ce qui est vérifié |
|---|---|
| Géométrie | Plans (pente, exposition, facteur de pente), ajustement, polygones croisés, classification faîtage / noue / égout / rive |
| Détection des pans | MNS synthétiques bruités à géométrie connue : deux pans (+ cheminée), quatre pans (croupes), toit en L (8 pans, noues) |
| Métré | Surfaces brutes/nettes, déductions, longueurs, cote de référence (facteur d'échelle), pans saisis, recouvrements, contours croisés, comparaison auto/actuel, checklist |
| Matériaux | Articles « à compléter » sans valeurs fabricant ; calculs avec paramètres, pertes, conditionnements, prix ; formules sûres |
| Plan de vol | Taille du pixel visée, passages, orbites, conseils (obturateur) ; caméra inconnue signalée |
| API de bout en bout | Sécurité (session, anti-CSRF, jeton d'API), import (doublons, fichiers invalides), analyse, métré versionné et conflits, matériaux, validation, PDF, exports, duplication, restauration, archivage / suppression confirmée, sauvegardes, paramètres |
| Chaîne de reconstruction | Machine à états complète avec un serveur NodeODM simulé : envoi par lots, suivi, téléchargement, extraction GeoTIFF (UTM), préparation du repère, détection automatique, fond de plan, export GeoJSON (contrôle des coordonnées WGS84), détection ciblée asynchrone |
| Couverture | Part d'un pan réellement observée par le nuage de points |

### Exactitude sur toitures synthétiques (MNS 5 cm, bruit 1 cm)

| Toiture | Surface exacte | Surface détectée | Écart |
|---|---|---|---|
| Deux pans 10 × 8 m, 35° | 97,66 m² | 97,66 m² | < 0,01 % |
| Quatre pans 12 × 8 m, 30° | 110,85 m² | 110,85 m² | < 0,01 % |
| Toit en L (deux ailes à 35°, 8 pans) | 131,85 m² | 131,84 m² | < 0,01 % |

Faîtages, arêtiers (longueur théorique 6,11 m), noues et égouts sont correctement classés et mesurés
(écarts < 2 %). Ces résultats valident les **algorithmes** ; ils ne disent rien de la qualité d'un modèle
photogrammétrique réel, qui dépend des photos (voir § 2).

## 2. Essai réel avec OpenDroneMap

Jeu de données public **OpenDroneMap « Toledo »** (87 photos, DJI Phantom 3, 12 MP, 2015, vues verticales
uniquement, vol à ≈ 100 m) — une maison, une grange et des arbres.

### Moteur 3D

* NodeODM 3.6.2 (Docker), machine 4 cœurs / 16 Go.
* Calcul complet (réglages par défaut + MNS) : **46,8 min** ; MNS à **5 cm**, orthophoto à **4,3 cm/pixel**,
  5,6 millions de points, géoréférencement UTM 17N.
* L'application a également piloté **sa propre reconstruction** de bout en bout (envoi des 87 photos, file
  d'attente, suivi de progression, **redémarrage volontaire du serveur applicatif pendant le calcul** →
  reprise automatique du suivi), voir § 3.

### Analyse des photos

Verdict « série à améliorer » : 1 photo partiellement surexposée, deux références d'appareil, et surtout
**orientation de la nacelle absente** des métadonnées → diversité des angles, couverture par côté et
recouvrement déclarés **« non évaluables »** (et non supposés corrects).

### Détection des pans

* **Grange** (avec cadre de détection) : les deux versants principaux sont trouvés, mais le MNS de ce jeu
  est lissé et « en escalier » (vues verticales seules, pixel de 4 cm à 100 m) : bords inclinés parasites et
  fragments sur les appentis. Correction manuelle nécessaire.
* **Maison** (toit à pignons croisés, en partie sous un grand arbre) : faîtage principal N-S et faîtage de
  l'aile E-O correctement identifiés, pans E/O et cheminée détectés ; contours irréguliers sous la végétation
  (18 % du volume non rattaché, signalé par l'application). Correction manuelle nécessaire.
* La végétation d'automne (feuillages orangés) est imparfaitement écartée par l'indice de vert.

**Conclusion honnête** : sur des photos verticales seules prises de haut, la détection automatique fournit
une base à corriger, pas un métré prêt à l'emploi — exactement ce que le guide de prise de vue annonce
(orbites obliques et vol plus bas recommandés). Faute de dimensions réelles connues pour ces bâtiments,
**l'exactitude absolue sur ce jeu ne peut pas être chiffrée**. Une validation terrain par Matt's Couverture
(chantier mesuré au mètre + vol suivant le plan de l'assistant) est la prochaine étape indispensable
avant tout usage en devis.

## 3. Reconstruction pilotée par l'application

Voir le résultat consigné ci-dessous (préréglage « Aperçu rapide », 87 photos).

## 4. Interface

Parcours testés dans Chromium (bureau 1440 px et mobile 390 px) : création du compte, tableau de bord,
guide, assistant et plan de vol, import et analyse des 87 photos réelles, suivi de calcul, éditeur (sélection,
glissé de sommet lié, annuler / rétablir, cote de référence, dessin d'un pan avec pente ajustée sur le modèle
3D, vue 3D), validation, génération du PDF, aide contextuelle.
