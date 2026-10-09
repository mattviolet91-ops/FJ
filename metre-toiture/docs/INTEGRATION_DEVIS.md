# Intégration avec le logiciel de devis

L'application expose un format d'échange stable, versionné, destiné au logiciel de devis de Matt's
Couverture : `GET /api/chantiers/{id}/export/devis.json`.

Authentification d'un programme externe : `POST /api/auth/connexion?mode=api` avec
`{"email": "...", "mot_de_passe": "..."}` (compte dédié conseillé) renvoie un `jeton`, à transmettre dans
l'en-tête `Authorization: Bearer <jeton>` (validité : `MMT_SESSION_JOURS`). Documentation interactive de
toute l'API : `/api/docs`.

## Schéma `mmt-devis/1`

```json
{
  "schema": "mmt-devis/1",
  "genere_le": "2026-10-09T18:30:00",
  "chantier": {"id": 12, "reference": "MT-2026-0012", "nom": "…", "client_nom": "…", "client_tel": "…",
               "client_email": "…", "adresse": "…", "type_toiture": "deux_pans"},
  "metre": {
    "surface_nette_m2": 97.66,
    "surface_brute_m2": 98.86,
    "surface_projetee_m2": 80.0,
    "incertitude_m2": 2.1,
    "pente_moyenne_deg": 35.0,
    "longueurs_ml": {"faitage": 10.0, "egout": 20.0, "rive": 19.53, "gouttiere": 20.0},
    "pans": [{"id": "p1", "nom": "Pan 1 (S)", "surface_m2": 48.83, "pente_deg": 35.0, "orientation": "S",
              "source": "modele_3d", "valide": true}],
    "obstacles": [{"type": "cheminee", "nombre": 1, "perimetre_ml": 2.4}],
    "confiance": "elevee",
    "echelle": {"source": "reference", "incertitude_rel": 0.004}
  },
  "materiaux": [{"ouvrage": "…", "article": "Tuiles courantes", "reference": "…", "unite": "u",
                 "quantite": 1400, "prix_unitaire_ht": null, "statut": "ok"}],
  "pret_pour_devis": true
}
```

* `source` : `modele_3d` (calculé sur le modèle reconstruit), `estimation` (photo unique / non confirmé),
  `saisie` (valeur saisie).
* `statut` d'un article : `ok`, `zero` (quantité nulle), `a_completer` (paramètre fabricant manquant).
* `pret_pour_devis` : `false` tant qu'un point bloquant subsiste dans la checklist.

Règle de compatibilité : les champs existants ne changent pas de sens au sein de `mmt-devis/1` ; un
changement incompatible donnera `mmt-devis/2`.

## Pistes de connecteur

* **Import de fichier** : la plupart des logiciels de devis acceptent un import CSV/Excel d'ouvrages ;
  l'export CSV (`materiaux.csv`, séparateur `;`, décimales à la virgule) peut servir directement, ou une
  table de correspondance « article → code ouvrage du logiciel » peut être ajoutée au catalogue.
* **API** : si le logiciel expose une API, un module `mmt/services/devis_<logiciel>.py` lira ce même format
  et créera le devis (le champ `reference` des articles est prévu pour porter le code article du logiciel).
