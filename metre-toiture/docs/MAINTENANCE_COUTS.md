# Maintenance, sauvegardes et coûts

## Sauvegardes

* **Automatique** : une copie cohérente de la base de données est créée chaque jour dans
  `MMT_DATA_DIR/sauvegardes` (rotation : 14 par défaut).
* **Complète** (base + photos + modèles 3D) : Paramètres → Sauvegardes → « Sauvegarde complète ».
* **À faire vous-même** : copier régulièrement le dossier `sauvegardes` **hors du serveur** (disque externe,
  stockage distant). Une sauvegarde qui reste sur le même disque ne protège pas d'une panne de ce disque.

Restauration : arrêter l'application, extraire l'archive dans `MMT_DATA_DIR` (le fichier `mmt.db` et les
dossiers `photos`, `modeles`, `fichiers`), redémarrer.

## Entretien courant

| Fréquence | Action |
|---|---|
| Chaque semaine | Vérifier l'espace disque (photos + modèles ≈ 1 à 3 Go par chantier) ; archiver puis supprimer définitivement les vieux chantiers si besoin |
| Chaque mois | Copier les sauvegardes hors serveur ; mettre à jour l'application et NodeODM (voir INSTALLATION.md) |
| Chaque mise à jour | Sauvegarde complète avant ; lancer `python -m pytest` si installation manuelle |

Journaux : `docker compose logs app` / `docker compose logs nodeodm`. Un traitement en erreur affiche la fin
du journal du moteur 3D et un conseil (photos insuffisantes, mémoire…).

Les traitements interrompus (redémarrage du serveur, coupure du moteur 3D) **reprennent automatiquement** :
l'envoi des photos continue là où il s'était arrêté, le suivi reprend la tâche existante, et un serveur de
calcul injoignable est réessayé automatiquement (30 tentatives) avant de signaler une erreur.

## Coûts

L'application et ses composants (OpenDroneMap, Python, React, three.js…) sont **libres et gratuits**.
Les seuls coûts sont l'hébergement et, éventuellement, la puissance de calcul. Les tarifs ci-dessous sont des
**ordres de grandeur indicatifs à vérifier** auprès des fournisseurs au moment de la commande ; aucune
dépense n'a été engagée.

| Option | Pour qui | Coût indicatif | Remarques |
|---|---|---|---|
| PC de l'entreprise (16–32 Go RAM) + Docker | Démarrage, quelques chantiers par semaine | 0 € (matériel existant) | Accès depuis le chantier via un VPN ou un tunnel sécurisé, ou import au retour |
| VPS 4 vCPU / 16 Go (application + calcul) | Usage régulier, accès partout | de l'ordre de 20 à 60 € HT/mois selon l'hébergeur | Calcul d'un pavillon : quelques dizaines de minutes |
| Petit VPS (application) + serveur de calcul loué à l'heure | Optimisation des coûts | VPS de l'ordre de 5 à 10 €/mois + quelques dizaines de centimes à quelques euros par heure de calcul | Le serveur de calcul peut être éteint entre deux chantiers ; les traitements attendent son retour |
| Service de calcul compatible NodeODM (ex. WebODM Lightning) | Pas de serveur de calcul à gérer | abonnement ou crédits, voir le site du fournisseur | Les photos des clients sont envoyées au prestataire (à mentionner aux clients / RGPD) |
| Nom de domaine + HTTPS | Accès propre et sécurisé | ≈ 10–15 €/an (certificat Let's Encrypt gratuit) | Sous-domaine du domaine existant possible |

Repères mesurés sur la machine de développement (4 cœurs, 16 Go) avec le jeu public OpenDroneMap
« Toledo » (87 photos 12 MP) : voir `docs/VALIDATION.md`. L'estimation de durée de l'application se
recale automatiquement sur les calculs réalisés sur **votre** serveur.

## Données personnelles (RGPD)

Les chantiers contiennent des données clients (nom, adresse, photos de propriétés). Recommandations :
accès HTTPS uniquement, comptes nominatifs, sauvegardes chiffrées hors serveur, suppression définitive des
chantiers dont la durée de conservation est dépassée, information des clients si un service de calcul
externe est utilisé.
