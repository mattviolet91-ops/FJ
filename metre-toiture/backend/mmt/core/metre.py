"""Calcul complet d'un métré à partir du document « toiture » d'un chantier.

Le document (JSON) est la source de vérité éditable par l'utilisateur ; ce module en
déduit toutes les grandeurs (surfaces, longueurs, pentes), leur provenance, un niveau
de confiance justifié et les contrôles de cohérence.

Provenance des valeurs :
  * « modele_3d »  : calculé à partir du modèle 3D reconstruit (plan ajusté sur les points) ;
  * « estimation » : estimé (photo unique, détection automatique non confirmée…) ;
  * « saisie »     : saisi manuellement par l'utilisateur.
"""
from __future__ import annotations

import math
from typing import Any

from . import geometry as geo

NIVEAUX = ["faible", "moyenne", "elevee"]


def nfr(v: float, d: int = 1) -> str:
    """Nombre au format français (virgule décimale)."""
    return f"{v:.{d}f}".replace(".", ",")

LIBELLES_SOURCE = {
    "modele_3d": "Modèle 3D",
    "estimation": "Estimation",
    "saisie": "Saisie manuelle",
}

TYPES_OBSTACLES = {
    "cheminee": "Cheminée",
    "fenetre_toit": "Fenêtre de toit",
    "ventilation": "Sortie de ventilation",
    "emergence": "Émergence (à identifier)",
    "panneau_solaire": "Panneaux solaires",
    "lucarne": "Lucarne",
    "autre": "Autre",
}


def document_vide() -> dict:
    return {
        "version": 1,
        "repere": {"type": "local", "source": "saisie", "epsg": None, "origine": None},
        "echelle": {"facteur": 1.0, "source": "aucune", "references": []},
        "pans": [],
        "lignes_types": {},
        "lignes_manuelles": [],
        "obstacles": [],
        "auto": None,
    }


# ---------------------------------------------------------------------------
def _pan_geo(p: dict) -> geo.Pan | None:
    if not p.get("contour") or len(p["contour"]) < 3 or not p.get("plan"):
        return None
    return geo.Pan(p["id"], [(float(x), float(y)) for x, y in p["contour"]], geo.Plan.from_dict(p["plan"]),
                   p.get("nom", ""))


def _saisie(p: dict) -> dict | None:
    s = p.get("saisie")
    if not s:
        return None
    pente = float(s.get("pente_deg") or 0.0)
    bas = float(s.get("longueur_bas") or 0.0)
    forme = s.get("forme", "rectangle")
    haut = 0.0 if forme == "triangle" else float(s.get("longueur_haut") if s.get("longueur_haut") not in (None, "") else bas)
    if forme == "rectangle":
        haut = bas
    ramp = float(s.get("rampant") or 0.0)
    surf = (bas + haut) / 2 * ramp
    return {"surface": surf, "surface_plan": surf * math.cos(math.radians(pente)), "pente_deg": pente,
            "rampant": ramp, "perimetre": bas + haut + 2 * math.hypot(ramp, abs(bas - haut) / 2),
            "azimut": s.get("azimut_deg")}


def incertitude_echelle(echelle: dict) -> tuple[float | None, str]:
    """Incertitude relative (fraction) sur l'échelle et message explicatif."""
    src = echelle.get("source", "aucune")
    refs = [r for r in echelle.get("references", []) if r.get("reelle") and r.get("mesuree")]
    if refs:
        facteurs = [r["reelle"] / r["mesuree"] for r in refs]
        sigma_pt = max(0.02, float(echelle.get("precision_pointe_m") or 0.03))
        u = min(math.sqrt(2) * sigma_pt / r["reelle"] for r in refs)
        if len(facteurs) >= 2:
            moy = sum(facteurs) / len(facteurs)
            disp = max(abs(f - moy) / moy for f in facteurs)
            u = max(u / math.sqrt(len(refs)), disp)
            return u, f"Échelle contrôlée par {len(refs)} cotes de référence (dispersion {nfr(disp * 100)} %)."
        return u, "Échelle contrôlée par une cote de référence."
    if src == "gcp":
        return 0.005, "Échelle issue de points de contrôle au sol."
    if src == "gps":
        return None, ("Échelle déduite du GPS du drone, non vérifiée par une cote mesurée : "
                      "ajoutez une dimension de référence pour la confirmer.")
    if src == "photo_exif":
        return None, ("Échelle estimée à partir de l'altitude et de l'optique (photo unique) : "
                      "précision non garantie, contrôlez avec une cote mesurée.")
    if src == "saisie":
        return 0.0, "Dimensions saisies manuellement."
    return None, "Aucune échelle métrique fiable : les longueurs ne sont pas exploitables sans cote de référence."


def _confiance_pan(p: dict, pg: geo.Pan | None, echelle: dict, u_ech: float | None, k: float) -> dict:
    raisons: list[str] = []
    niveau = 2
    source = p.get("source_plan", "saisie")
    sigma_bord = None
    if p.get("saisie") and pg is None:
        return {"niveau": "saisie", "raisons": ["Dimensions et pente saisies par l'utilisateur."], "incertitude_m2": None}
    if source == "saisie":
        raisons.append("Pente saisie manuellement.")
    if source == "estimation":
        niveau = min(niveau, 1)
        raisons.append("Valeurs estimées (sans modèle 3D) : à confirmer.")
    st = p.get("stats") or {}
    if source == "modele_3d":
        rms = st.get("rms")
        if rms is not None:
            if rms > 0.06:
                niveau = min(niveau, 0)
                raisons.append(f"Surface du pan irrégulière ou bruitée (écart au plan {nfr(rms * 100)} cm).")
            elif rms > 0.03:
                niveau = min(niveau, 1)
                raisons.append(f"Écart moyen au plan de {nfr(rms * 100)} cm.")
        couv = st.get("couverture")
        if couv is not None:
            if couv < 0.7:
                niveau = min(niveau, 0)
                raisons.append(f"Seulement {couv * 100:.0f} % du pan réellement observé.")
            elif couv < 0.9:
                niveau = min(niveau, 1)
                raisons.append(f"{(1 - couv) * 100:.0f} % du pan interpolé (zone peu photographiée).")
        sigma_bord = max(0.03, 1.5 * float(st.get("resolution") or 0.05))
    if u_ech is None and echelle.get("source") != "saisie":
        niveau = min(niveau, 1)
        raisons.append("Échelle non vérifiée par une cote de référence.")
    if p.get("source_contour") == "modifie":
        raisons.append("Contour corrigé manuellement.")
    if not p.get("valide"):
        raisons.append("Pan non encore validé.")
    inc = None
    if pg is not None and sigma_bord is not None:
        A = pg.aire_reelle * k * k
        per = geo.perimetre(pg.contour) * k * pg.plan.facteur_pente
        # erreur de contour + erreur de pente (σ ≈ rms / rampant) + échelle
        ramp = max(pg.rampant() * k, 0.5)
        sig_p = (st.get("rms") or 0.02) / ramp * 2
        rel = (per * sigma_bord / A if A > 0 else 0) + math.tan(pg.plan.pente_rad) * sig_p
        if u_ech:
            rel += 2 * u_ech
        inc = A * rel
    if not raisons:
        raisons.append("Pan bien observé, plan régulier, échelle contrôlée.")
    return {"niveau": NIVEAUX[niveau], "raisons": raisons, "incertitude_m2": inc}


# ---------------------------------------------------------------------------
def appliquer_references(echelle: dict) -> dict:
    """Calcule la longueur mesurée sur le modèle de chaque cote de référence et en déduit
    le facteur d'échelle (médiane des rapports cote réelle / cote modèle)."""
    e = dict(echelle)
    refs = []
    for r in e.get("references", []) or []:
        r = dict(r)
        if r.get("p1") and r.get("p2"):
            p1, p2 = list(r["p1"]), list(r["p2"])
            if len(p1) == 2:
                p1.append(0.0)
            if len(p2) == 2:
                p2.append(0.0)
            r["mesuree"] = math.dist(p1, p2)
        refs.append(r)
    e["references"] = refs
    valides = [r for r in refs if r.get("reelle") and r.get("mesuree")]
    if valides:
        rap = sorted(float(r["reelle"]) / float(r["mesuree"]) for r in valides)
        m = len(rap)
        e["facteur"] = rap[m // 2] if m % 2 else (rap[m // 2 - 1] + rap[m // 2]) / 2
        if e.get("source") not in ("gcp",):
            e["source_initiale"] = e.get("source_initiale") or e.get("source")
            e["source"] = "reference"
    return e


def calculer(doc: dict) -> dict[str, Any]:
    echelle = appliquer_references(doc.get("echelle") or {"facteur": 1.0, "source": "aucune"})
    k = float(echelle.get("facteur") or 1.0)
    u_ech, msg_ech = incertitude_echelle(echelle)
    controles: list[dict] = []

    pans_out = []
    geos: list[geo.Pan] = []
    for p in doc.get("pans", []):
        pg = _pan_geo(p)
        sa = _saisie(p) if pg is None else None
        if pg is None and sa is None:
            controles.append({"niveau": "erreur", "code": "pan_incomplet", "pan_id": p.get("id"),
                              "message": f"{p.get('nom') or 'Pan'} : contour ou dimensions manquants."})
            continue
        if pg is not None:
            geos.append(pg)
            if not geo.polygone_simple(pg.contour):
                controles.append({"niveau": "erreur", "code": "contour_croise", "pan_id": p["id"],
                                  "message": f"{p.get('nom')} : le contour se croise, la surface est fausse."})
            surf = pg.aire_reelle * k * k
            surf_plan = pg.aire_plan * k * k
            pente = pg.plan.pente_deg
            az = pg.plan.azimut_deg
            rot = float((doc.get("repere") or {}).get("rotation_deg") or 0.0)
            if az is not None and rot:
                az = (az + rot) % 360
            ramp = pg.rampant() * k
            per = sum(geo.longueur_3d(pg.contour[i], pg.contour[(i + 1) % len(pg.contour)], pg.plan)
                      for i in range(len(pg.contour))) * k
        else:
            surf, surf_plan, pente = sa["surface"], sa["surface_plan"], sa["pente_deg"]
            az, ramp, per = sa["azimut"], sa["rampant"], sa["perimetre"]
        conf = _confiance_pan(p, pg, echelle, u_ech, k)
        if pente < 5 and pente > 0.5:
            controles.append({"niveau": "info", "code": "pente_faible", "pan_id": p["id"],
                              "message": f"{p.get('nom')} : pente de {nfr(pente)}° — vérifiez la pente minimale "
                                         "admissible du matériau (DTU / avis technique)."})
        if pente > 65:
            controles.append({"niveau": "alerte", "code": "pente_forte", "pan_id": p["id"],
                              "message": f"{p.get('nom')} : pente de {pente:.0f}° inhabituelle, vérifiez le pan "
                                         "(mur ou brisis de mansarde ?)."})
        pans_out.append({
            "id": p["id"], "nom": p.get("nom") or "", "surface": surf, "surface_plan": surf_plan,
            "pente_deg": pente, "pente_pct": 100 * math.tan(math.radians(pente)),
            "azimut": az, "orientation": geo.orientation_texte(az) if az is not None or pente > 0.5 else "Plat",
            "rampant": ramp, "perimetre": per,
            "source_plan": p.get("source_plan", "saisie"),
            "source_contour": p.get("source_contour", "manuel"),
            "valide": bool(p.get("valide")), "confiance": conf,
            "deductions": 0.0, "surface_nette": surf,
        })

    # --- obstacles
    idx = {po["id"]: po for po in pans_out}
    pans_par_id = {pg.id: pg for pg in geos}
    obs_out = []
    for o in doc.get("obstacles", []):
        pan_id = o.get("pan_id")
        pg = None
        surf_plan = per = None
        if o.get("contour") and len(o["contour"]) >= 3:
            c = [(float(x), float(y)) for x, y in o["contour"]]
            if pan_id not in pans_par_id:
                cen = geo.centroide(c)
                for cand in geos:
                    if geo.point_dans_polygone(cen, cand.contour):
                        pan_id = cand.id
                        break
            pg = pans_par_id.get(pan_id)
            surf_plan = geo.aire(c) * k * k
            facteur = pg.plan.facteur_pente if pg else 1.0
            surf = surf_plan * facteur
            per = (sum(geo.longueur_3d(c[i], c[(i + 1) % len(c)], pg.plan) for i in range(len(c))) * k
                   if pg else geo.perimetre(c) * k)
            src = "modele_3d" if o.get("source") == "auto" else "saisie"
        else:
            la, lo = float(o.get("largeur") or 0), float(o.get("longueur") or 0)
            surf = la * lo
            per = 2 * (la + lo)
            src = "saisie"
        nb = int(o.get("nombre") or 1)
        surf *= nb
        per *= nb
        entree = {"id": o.get("id"), "type": o.get("type", "autre"),
                  "libelle": TYPES_OBSTACLES.get(o.get("type", "autre"), "Autre"),
                  "surface": surf, "perimetre": per, "pan_id": pan_id, "nombre": nb,
                  "deduire": bool(o.get("deduire")), "valide": bool(o.get("valide")),
                  "source": src, "hauteur": o.get("hauteur")}
        obs_out.append(entree)
        if entree["deduire"] and pan_id in idx:
            idx[pan_id]["deductions"] += surf
            idx[pan_id]["surface_nette"] = idx[pan_id]["surface"] - idx[pan_id]["deductions"]
        if o.get("source") == "auto" and not o.get("valide"):
            controles.append({"niveau": "alerte", "code": "obstacle_a_confirmer", "obstacle_id": o.get("id"),
                              "message": "Émergence détectée automatiquement : précisez sa nature "
                                         "(cheminée, ventilation…) ou supprimez-la."})

    # --- lignes
    lignes_out = []
    overrides = doc.get("lignes_types") or {}
    for lg in geo.classer_lignes(geos):
        if lg.cle in overrides:
            lg.type = overrides[lg.cle]
        d = lg.to_dict()
        d["longueur"] = lg.longueur * k
        d["source"] = "modele_3d" if all(
            (next((p for p in doc["pans"] if p["id"] == pid), {}) or {}).get("source_plan") == "modele_3d"
            for pid in lg.pans) else "saisie"
        d["modifie"] = lg.cle in overrides
        lignes_out.append(d)
        if lg.incoherence_z > 0.10 and lg.type in (geo.FAITAGE, geo.ARETIER, geo.NOUE):
            controles.append({"niveau": "alerte", "code": "ecart_hauteur", "ligne": lg.cle,
                              "message": f"{geo.TYPES_LIGNES[lg.type]} : les deux pans ne se rejoignent pas "
                                         f"à la même hauteur (écart {lg.incoherence_z * k * 100:.0f} cm). "
                                         "Contrôlez les pentes."})
    for lm in doc.get("lignes_manuelles", []):
        if lm.get("p1") and lm.get("p2"):
            L = math.dist(lm["p1"], lm["p2"]) * k
        else:
            L = float(lm.get("longueur") or 0.0)
        lignes_out.append({"cle": lm.get("id"), "type": lm.get("type", "autre"),
                           "libelle": geo.TYPES_LIGNES.get(lm.get("type"), lm.get("type")),
                           "longueur": L, "pans": lm.get("pans", []), "source": "saisie", "modifie": True,
                           "manuelle": True})
    totaux_lignes: dict[str, float] = {t: 0.0 for t in geo.TYPES_LIGNES}
    for d in lignes_out:
        totaux_lignes[d["type"]] = totaux_lignes.get(d["type"], 0.0) + d["longueur"]
    totaux_lignes["gouttiere"] = totaux_lignes.get(geo.EGOUT, 0.0)

    # --- contrôles globaux
    for i in range(len(geos)):
        for j in range(i + 1, len(geos)):
            ov = geo.recouvrement_polygones(geos[i].contour, geos[j].contour)
            if ov * k * k > 0.10:
                controles.append({"niveau": "alerte", "code": "recouvrement", "pan_id": geos[i].id,
                                  "message": f"Les pans « {geos[i].nom or geos[i].id} » et « {geos[j].nom or geos[j].id} » "
                                             f"se chevauchent en plan ({nfr(ov * k * k, 2)} m²) : risque de double comptage."})
    if any(not p["valide"] for p in pans_out):
        n = sum(1 for p in pans_out if not p["valide"])
        controles.append({"niveau": "info", "code": "pans_non_valides",
                          "message": f"{n} pan(s) restent à contrôler et valider."})
    if u_ech is None and echelle.get("source") != "saisie" and geos:
        controles.append({"niveau": "alerte", "code": "echelle", "message": msg_ech})
    if not pans_out:
        controles.append({"niveau": "info", "code": "vide", "message": "Aucun pan défini pour l'instant."})

    surf_brute = sum(p["surface"] for p in pans_out)
    deduc = sum(p["deductions"] for p in pans_out)
    surf_plan = sum(p["surface_plan"] for p in pans_out)
    pente_moy = (sum(p["pente_deg"] * p["surface"] for p in pans_out) / surf_brute) if surf_brute else 0.0
    inc = [p["confiance"]["incertitude_m2"] for p in pans_out if p["confiance"].get("incertitude_m2") is not None]
    dims = _dimensions(geos, k)
    niv = [p["confiance"]["niveau"] for p in pans_out if p["confiance"]["niveau"] in NIVEAUX]
    conf_glob = NIVEAUX[min((NIVEAUX.index(n) for n in niv), default=0)] if niv else "saisie"

    comparaison = _comparer_auto(doc, pans_out, k)
    return {
        "pans": pans_out,
        "lignes": lignes_out,
        "totaux_lignes": totaux_lignes,
        "obstacles": obs_out,
        "totaux": {
            "nb_pans": len(pans_out),
            "surface_brute": surf_brute,
            "deductions": deduc,
            "surface_nette": surf_brute - deduc,
            "surface_plan": surf_plan,
            "pente_moyenne_deg": pente_moy,
            "incertitude_m2": (math.sqrt(sum(x * x for x in inc)) if len(inc) == len(pans_out) and inc else None),
        },
        "dimensions": dims,
        "echelle": {"facteur": k, "source": echelle.get("source"), "incertitude_rel": u_ech, "message": msg_ech,
                    "references": echelle.get("references", [])},
        "confiance_globale": conf_glob,
        "controles": controles,
        "comparaison_auto": comparaison,
    }


def _dimensions(geos: list[geo.Pan], k: float) -> dict | None:
    pts = [pt for g in geos for pt in g.contour]
    if len(pts) < 3:
        return None
    # rectangle orienté d'aire minimale (sur les sommets)
    best = None
    n = len(pts)
    for g in geos:
        m = len(g.contour)
        for i in range(m):
            a, b = g.contour[i], g.contour[(i + 1) % m]
            L = math.dist(a, b)
            if L < 1e-6:
                continue
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            pu = [p[0] * u[0] + p[1] * u[1] for p in pts]
            pv = [-p[0] * u[1] + p[1] * u[0] for p in pts]
            A = (max(pu) - min(pu)) * (max(pv) - min(pv))
            if best is None or A < best[0]:
                best = (A, max(pu) - min(pu), max(pv) - min(pv))
    del n
    zs = [z for g in geos for (_, _, z) in g.sommets_3d()]
    return {"longueur": max(best[1], best[2]) * k, "largeur": min(best[1], best[2]) * k,
            "hauteur_toiture": (max(zs) - min(zs)) * k}


def _comparer_auto(doc: dict, pans_out: list[dict], k: float) -> dict | None:
    auto = doc.get("auto")
    if not auto or not auto.get("pans"):
        return None
    total_auto = sum(p["surface"] for p in auto["pans"]) * k * k
    total = sum(p["surface"] for p in pans_out)
    lignes = []
    actuels = {p["id"]: p for p in pans_out}
    for pa in auto["pans"]:
        cur = actuels.get(pa["id"])
        lignes.append({"id": pa["id"], "nom": pa.get("nom"), "auto": pa["surface"] * k * k,
                       "actuel": cur["surface"] if cur else None,
                       "ecart": (cur["surface"] - pa["surface"] * k * k) if cur else None})
    nouveaux = [p["id"] for p in pans_out if p["id"] not in {a["id"] for a in auto["pans"]}]
    return {"total_auto": total_auto, "total_actuel": total, "ecart": total - total_auto,
            "ecart_pct": (100 * (total - total_auto) / total_auto) if total_auto else None,
            "pans": lignes, "pans_ajoutes": nouveaux}
