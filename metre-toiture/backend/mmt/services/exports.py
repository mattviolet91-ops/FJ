"""Exports en formats ouverts : JSON, CSV (zip), DXF, GeoJSON, OBJ et JSON « devis »."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime

from ..core import geometry as geo

SCHEMA_DEVIS = "mmt-devis/1"


def _fr(v, d=2):
    return "" if v is None else f"{v:.{d}f}".replace(".", ",")


def export_csv(calcul: dict, materiaux: dict | None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def ecrire(nom, lignes):
            s = io.StringIO()
            w = csv.writer(s, delimiter=";")
            for l in lignes:
                w.writerow(l)
            z.writestr(nom, "﻿" + s.getvalue())

        ecrire("pans.csv", [["id", "nom", "orientation", "pente_deg", "pente_pct", "surface_plan_m2", "surface_m2",
                             "deductions_m2", "surface_nette_m2", "rampant_m", "source", "confiance", "valide"]] +
               [[p["id"], p["nom"], p["orientation"], _fr(p["pente_deg"], 1), _fr(p["pente_pct"], 1),
                 _fr(p["surface_plan"]), _fr(p["surface"]), _fr(p["deductions"]), _fr(p["surface_nette"]),
                 _fr(p["rampant"]), p["source_plan"], p["confiance"]["niveau"], "oui" if p["valide"] else "non"]
                for p in calcul["pans"]])
        ecrire("lignes.csv", [["type", "libelle", "longueur_m", "pans", "source"]] +
               [[l["type"], l["libelle"], _fr(l["longueur"]), " ".join(l.get("pans", [])), l.get("source", "")]
                for l in calcul["lignes"]])
        ecrire("obstacles.csv", [["type", "nombre", "surface_m2", "perimetre_m", "deduit", "pan"]] +
               [[o["type"], o["nombre"], _fr(o["surface"]), _fr(o["perimetre"]), "oui" if o["deduire"] else "non",
                 o.get("pan_id") or ""] for o in calcul["obstacles"]])
        if materiaux:
            ecrire("materiaux.csv", [["ouvrage", "article", "reference", "unite", "quantite_base", "consommation",
                                      "perte_pct", "quantite_totale", "conditionnements", "prix_unitaire_ht",
                                      "montant_ht", "statut"]] +
                   [[l["ouvrage"], l["article"], l.get("reference") or "", l["unite"], _fr(l.get("quantite_base")),
                     _fr(l.get("consommation"), 4), _fr(l.get("perte_pct"), 1), _fr(l.get("quantite_totale")),
                     l.get("conditionnements", ""), _fr(l.get("prix_unitaire")), _fr(l.get("montant_ht")),
                     l["statut"]] for l in materiaux["lignes"]])
    return buf.getvalue()


def export_dxf(document: dict, calcul: dict) -> bytes:
    import ezdxf

    k = calcul["echelle"]["facteur"] or 1.0
    d = ezdxf.new("R2010", setup=True)
    d.units = ezdxf.units.M
    msp = d.modelspace()
    couleurs = {"faitage": 1, "aretier": 30, "noue": 3, "egout": 5, "rive": 6, "rive_haute": 6, "bris": 34,
                "solin": 8, "autre": 7}
    d.layers.add("PANS", color=4)
    d.layers.add("PANS_3D", color=4)
    d.layers.add("TEXTES", color=7)
    d.layers.add("OBSTACLES", color=8)
    for t, c in couleurs.items():
        d.layers.add(f"LIGNE_{t.upper()}", color=c)
    infos = {p["id"]: p for p in calcul["pans"]}
    for p in document.get("pans", []):
        if not p.get("contour") or len(p["contour"]) < 3:
            continue
        pl = geo.Plan.from_dict(p["plan"])
        pts2 = [(x * k, y * k) for x, y in p["contour"]]
        msp.add_lwpolyline(pts2, close=True, dxfattribs={"layer": "PANS"})
        pts3 = [(x * k, y * k, pl.z(x, y) * k) for x, y in p["contour"]]
        msp.add_polyline3d(pts3, close=True, dxfattribs={"layer": "PANS_3D"})
        c = geo.centroide([tuple(v) for v in p["contour"]])
        inf = infos.get(p["id"])
        if inf:
            txt = f"{p.get('nom', '')} - {inf['surface']:.2f} m2 - {inf['pente_deg']:.0f} deg"
            msp.add_text(txt, height=0.25, dxfattribs={"layer": "TEXTES"}).set_placement((c[0] * k, c[1] * k))
    for o in document.get("obstacles", []):
        if o.get("contour") and len(o["contour"]) >= 3:
            msp.add_lwpolyline([(x * k, y * k) for x, y in o["contour"]], close=True,
                               dxfattribs={"layer": "OBSTACLES"})
    for l in calcul["lignes"]:
        if l.get("manuelle"):
            continue
        msp.add_line((l["p1"][0] * k, l["p1"][1] * k, l["p1"][2] * k), (l["p2"][0] * k, l["p2"][1] * k, l["p2"][2] * k),
                     dxfattribs={"layer": f"LIGNE_{l['type'].upper()}"})
    s = io.StringIO()
    d.write(s)
    return s.getvalue().encode("utf-8")


def export_obj(document: dict, calcul: dict) -> bytes:
    k = calcul["echelle"]["facteur"] or 1.0
    out = ["# Matt's Métré Toiture - pans de toiture (repère local, mètres)"]
    n = 0
    for p in document.get("pans", []):
        if not p.get("contour") or len(p["contour"]) < 3:
            continue
        pl = geo.Plan.from_dict(p["plan"])
        out.append(f"o {p['id']}")
        for x, y in geo.antihoraire([tuple(v) for v in p["contour"]]):
            # OBJ : y vers le haut
            out.append(f"v {x * k:.4f} {pl.z(x, y) * k:.4f} {-y * k:.4f}")
        m = len(p["contour"])
        out.append("f " + " ".join(str(n + i + 1) for i in range(m)))
        n += m
    return ("\n".join(out) + "\n").encode()


def export_geojson(document: dict, calcul: dict, info_modele: dict) -> bytes:
    from .modele import vers_wgs84

    feats = []
    infos = {p["id"]: p for p in calcul["pans"]}
    for p in document.get("pans", []):
        if not p.get("contour") or len(p["contour"]) < 3:
            continue
        coords = vers_wgs84(info_modele, [tuple(v) for v in p["contour"]])
        coords.append(coords[0])
        inf = infos.get(p["id"], {})
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[list(c) for c in coords]]},
                      "properties": {"id": p["id"], "nom": p.get("nom"), "surface_m2": inf.get("surface"),
                                     "pente_deg": inf.get("pente_deg"), "orientation": inf.get("orientation"),
                                     "source": inf.get("source_plan")}})
    for l in calcul["lignes"]:
        if l.get("manuelle"):
            continue
        c = vers_wgs84(info_modele, [(l["p1"][0], l["p1"][1]), (l["p2"][0], l["p2"][1])])
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [list(x) for x in c]},
                      "properties": {"type": l["type"], "longueur_m": l["longueur"]}})
    return json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False).encode()


def export_devis(chantier: dict, calcul: dict, materiaux: dict | None, validation: dict | None) -> dict:
    """Format d'échange stable destiné au logiciel de devis (voir docs/INTEGRATION_DEVIS.md)."""
    return {
        "schema": SCHEMA_DEVIS,
        "genere_le": datetime.now().isoformat(timespec="seconds"),
        "chantier": chantier,
        "metre": {
            "surface_nette_m2": calcul["totaux"]["surface_nette"],
            "surface_brute_m2": calcul["totaux"]["surface_brute"],
            "surface_projetee_m2": calcul["totaux"]["surface_plan"],
            "incertitude_m2": calcul["totaux"].get("incertitude_m2"),
            "pente_moyenne_deg": calcul["totaux"]["pente_moyenne_deg"],
            "longueurs_ml": {k: v for k, v in calcul["totaux_lignes"].items() if v},
            "pans": [{"id": p["id"], "nom": p["nom"], "surface_m2": p["surface_nette"], "pente_deg": p["pente_deg"],
                      "orientation": p["orientation"], "source": p["source_plan"], "valide": p["valide"]}
                     for p in calcul["pans"]],
            "obstacles": [{"type": o["type"], "nombre": o["nombre"], "perimetre_ml": o["perimetre"]}
                          for o in calcul["obstacles"]],
            "confiance": calcul["confiance_globale"],
            "echelle": {"source": calcul["echelle"]["source"], "incertitude_rel": calcul["echelle"]["incertitude_rel"]},
        },
        "materiaux": [{"ouvrage": l["ouvrage"], "article": l["article"], "reference": l.get("reference"),
                       "unite": l["unite"], "quantite": l.get("quantite_commandee", l.get("quantite_totale")),
                       "prix_unitaire_ht": l.get("prix_unitaire"), "statut": l["statut"]}
                      for l in (materiaux or {}).get("lignes", [])],
        "pret_pour_devis": (validation or {}).get("pret_pour_devis"),
    }
