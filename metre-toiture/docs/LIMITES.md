# Limites connues et pistes d'évolution

Ce document liste honnêtement ce que l'application **ne fait pas** (ou pas encore) et ce qu'il faut savoir
avant de s'appuyer sur ses résultats.

## Précision des mesures

* **Échelle** : sans cote de référence ni points de contrôle, l'échelle provient du GPS du drone. Elle est
  souvent bonne mais **jamais garantie** ; l'application l'affiche comme « non vérifiée » et n'inclut pas
  cette erreur dans l'incertitude chiffrée. Ajoutez systématiquement une cote mesurée.
* **Incertitude affichée** : modèle simplifié (erreur de contour ≈ 1,5 cellule du MNS, erreur de pente
  déduite de l'écart au plan, erreur d'échelle). C'est un ordre de grandeur, pas une garantie métrologique.
* **Bords de toiture** : la limite exacte de l'égout (débord de tuile, gouttière) dépend de la netteté du
  MNS ; contrôlez les longueurs d'égout sur l'orthophoto et avec une cote.
* **Végétation et zones masquées** : non reconstruites ; la part interpolée de chaque pan est signalée.
* **Photo unique** : distorsion de l'objectif non corrigée, altitude barométrique approximative, photo
  supposée parfaitement verticale : estimation uniquement.

## Détection automatique

* Fonctionne sur les toitures composées de **pans plans**. Les surfaces courbes (dômes, tourelles, bacs
  cintrés) sont découpées en facettes ou ignorées.
* Les **fenêtres de toit affleurantes** ne sont pas détectées (pas de relief) : à dessiner sur l'orthophoto.
* Les **lucarnes** et petits pans (< 1 m²) peuvent être fusionnés ou ignorés : à vérifier/dessiner.
* La classification des éléments (faîtage, noue, arêtier, égout, rive, bris) est **géométrique** ; elle
  ne reconnaît pas un solin contre un mur (à requalifier à la main). Aucun modèle d'apprentissage
  automatique n'est utilisé : cela évite des résultats non explicables, mais limite la reconnaissance
  sémantique (nature exacte d'une émergence, matériau de couverture).
* Le choix du bâtiment se fait par la position GPS du chantier, le centre des prises de vue ou le cadre tracé
  avec l'outil « Détecter » : en zone dense ou arborée, encadrez le bâtiment.
* **Végétation** : écartée par un indice de vert calculé sur l'orthophoto ; les feuillages d'automne
  (orangés) ou sans couleur marquée sont mal reconnus et peuvent produire de faux pans à supprimer.

## Fonctionnel

* **Matériaux** : les ouvrages fournis sont des structures de calcul ; consommations, pertes et prix
  doivent être saisis depuis vos fiches fabricants et tarifs. Pas de règles DTU intégrées (choix du pureau
  selon la pente et la zone, etc.) : elles relèvent de votre expertise et des documents de référence.
* **Logiciel de devis** : l'export `devis.json` (schéma `mmt-devis/1`, voir INTEGRATION_DEVIS.md) est prêt,
  mais le connecteur vers le logiciel de Matt's Couverture reste à écrire quand son format d'import ou son
  API seront connus.
* **Hors ligne** : le guide et les écrans déjà ouverts fonctionnent sans réseau ; l'import des photos, les
  calculs et l'enregistrement du métré nécessitent le serveur.
* **Multi-utilisateurs** : comptes et rôles simples (administrateur / utilisateur), sans cloisonnement des
  chantiers par utilisateur. L'enregistrement détecte les modifications concurrentes (conflit de version).
* **Visualisation 3D** : nuage de points (pas de maillage texturé, désactivé pour réduire temps de calcul et
  volume) ; l'édition se fait en plan.
* **Base de données** : SQLite par défaut (adapté à une entreprise) ; PostgreSQL possible mais sans outil
  de migration de schéma (les nouvelles tables sont créées automatiquement ; une évolution de colonne
  nécessiterait d'ajouter Alembic).

## Pistes d'évolution réalistes

1. Connecteur vers le logiciel de devis (dès que son format est connu).
2. Ajustement fin des égouts sur l'orthophoto (contours par détection de bords).
3. Bibliothèque partagée de fiches fabricants (import CSV des catalogues).
4. Classification par apprentissage (fenêtres de toit, panneaux solaires) sur l'orthophoto, entraînée sur
   vos propres chantiers validés — à n'envisager qu'avec suffisamment d'exemples.
5. Planification de vol exportable vers les applications de vol automatique (KMZ / waypoints).
6. Notifications (e-mail) en fin de calcul.
