"""Checklist de validation avant devis (guide E)."""
from __future__ import annotations

from .metre import nfr

OK, ATTENTION, BLOQUANT = "ok", "attention", "bloquant"

CONFIRMATIONS = {
    "obstacles_tous_saisis": "J'ai vérifié qu'aucune cheminée, fenêtre de toit ou sortie n'a été oubliée.",
    "pentes_plausibles": "Les pentes affichées sont cohérentes avec ce que j'ai vu sur place.",
    "zones_cachees_traitees": "Les zones masquées (arbres, mitoyens) ont été mesurées ou signalées.",
}


def checklist(metre: dict, contexte: dict, confirmations: dict) -> dict:
    """contexte : reconstruction (None | 'ok' | 'echec' | 'sans_3d'), analyse_photos (verdict),
    mode ('3d' | 'photo' | 'saisie')."""
    items = []
    mode = contexte.get("mode", "saisie")
    rec = contexte.get("reconstruction")
    if mode == "3d":
        items.append({"code": "reconstruction", "titre": "Reconstruction 3D",
                      "statut": OK if rec == "ok" else BLOQUANT,
                      "detail": "Modèle 3D calculé." if rec == "ok" else "La reconstruction n'a pas abouti."})
    else:
        items.append({"code": "reconstruction", "titre": "Reconstruction 3D", "statut": ATTENTION,
                      "detail": "Métré réalisé sans modèle 3D (photo unique ou saisie) : précision réduite, "
                                "contrôlez les cotes principales sur place."})
    ech = metre["echelle"]
    if ech.get("source") == "saisie":
        st, det = OK, "Cotes saisies manuellement."
    elif ech.get("incertitude_rel") is not None:
        u = ech["incertitude_rel"]
        st = OK if u <= 0.02 else ATTENTION
        det = ech["message"] + f" Incertitude d'échelle estimée : ±{nfr(u * 100)} %."
    else:
        st, det = BLOQUANT if mode == "photo" else ATTENTION, ech["message"]
    items.append({"code": "echelle", "titre": "Échelle métrique fiable", "statut": st, "detail": det})

    pans = metre["pans"]
    nv = [p for p in pans if not p["valide"]]
    items.append({"code": "pans", "titre": "Tous les pans contrôlés",
                  "statut": BLOQUANT if not pans else (OK if not nv else ATTENTION),
                  "detail": "Aucun pan." if not pans else (
                      f"{len(pans)} pan(s) validé(s)." if not nv else
                      f"{len(nv)} pan(s) non validé(s) : " + ", ".join(p["nom"] or p["id"] for p in nv))})
    obs_nc = [o for o in metre["obstacles"] if o["source"] != "saisie" and not o["valide"]]
    conf_obs = confirmations.get("obstacles_tous_saisis")
    items.append({"code": "obstacles", "titre": "Obstacles pris en compte",
                  "statut": OK if (not obs_nc and conf_obs) else ATTENTION,
                  "detail": (f"{len(obs_nc)} émergence(s) détectée(s) à confirmer. " if obs_nc else "") +
                            ("Confirmation donnée." if conf_obs else "Confirmez qu'aucun obstacle n'a été oublié."),
                  "confirmation": "obstacles_tous_saisis"})
    erreurs = [c for c in metre["controles"] if c["niveau"] == "erreur"]
    alertes = [c for c in metre["controles"] if c["niveau"] == "alerte"]
    items.append({"code": "surfaces", "titre": "Surfaces validées",
                  "statut": BLOQUANT if erreurs else (ATTENTION if alertes else OK),
                  "detail": (f"{len(erreurs)} erreur(s), " if erreurs else "") + f"{len(alertes)} alerte(s) de cohérence."})
    items.append({"code": "pentes", "titre": "Pentes plausibles", "statut": OK if confirmations.get("pentes_plausibles") else ATTENTION,
                  "detail": "Comparez les pentes calculées à votre appréciation sur place.",
                  "confirmation": "pentes_plausibles"})
    a_controler = []
    for p in pans:
        if p["confiance"]["niveau"] == "faible":
            a_controler.append(f"{p['nom'] or p['id']} : " + "; ".join(p["confiance"]["raisons"][:2]))
    if contexte.get("analyse_photos") == "insuffisant":
        a_controler.append("La série de photos présentait des lacunes importantes.")
    items.append({"code": "sur_place", "titre": "Mesures à contrôler sur place",
                  "statut": ATTENTION if a_controler else OK,
                  "detail": "Aucune mesure signalée." if not a_controler else "À vérifier : " + " | ".join(a_controler),
                  "liste": a_controler})
    items.append({"code": "zones_cachees", "titre": "Zones masquées traitées",
                  "statut": OK if confirmations.get("zones_cachees_traitees") else ATTENTION,
                  "detail": "Arbres, mitoyennetés ou parties non visibles mesurées ou signalées en réserve.",
                  "confirmation": "zones_cachees_traitees"})
    statuts = [i["statut"] for i in items]
    global_ = BLOQUANT if BLOQUANT in statuts else (ATTENTION if ATTENTION in statuts else OK)
    return {"items": items, "statut": global_, "pret_pour_devis": global_ != BLOQUANT}
