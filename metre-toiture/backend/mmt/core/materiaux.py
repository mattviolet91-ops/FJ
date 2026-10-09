"""Calcul des quantités de matériaux à partir d'un métré validé.

Aucune consommation ni aucun prix n'est inventé : chaque article d'un ouvrage porte une
consommation qui est soit un nombre saisi (fiche fabricant), soit une formule à partir de
paramètres saisis (ex. liteaux = 1 / pureau). Tant qu'une valeur manque, l'article est
signalé « à compléter » et n'est pas chiffré.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

BASES = {
    "surface": "Surface de couverture nette (m²)",
    "surface_brute": "Surface de couverture brute (m²)",
    "surface_plan": "Surface projetée au sol (m²)",
    "ligne:faitage": "Longueur de faîtage (ml)",
    "ligne:aretier": "Longueur d'arêtiers (ml)",
    "ligne:noue": "Longueur de noues (ml)",
    "ligne:egout": "Longueur d'égouts (ml)",
    "ligne:rive": "Longueur de rives (ml)",
    "ligne:rive_haute": "Longueur de rives hautes (ml)",
    "ligne:solin": "Longueur de solins (ml)",
    "ligne:bris": "Longueur de lignes de bris (ml)",
    "ligne:gouttiere": "Longueur de gouttières (ml)",
    "obstacles:cheminee:perimetre": "Périmètre des cheminées (ml)",
    "obstacles:cheminee:nombre": "Nombre de cheminées",
    "obstacles:fenetre_toit:nombre": "Nombre de fenêtres de toit",
    "obstacles:ventilation:nombre": "Nombre de sorties de ventilation",
    "obstacles:tous:perimetre": "Périmètre de toutes les émergences (ml)",
    "forfait": "Forfait (quantité fixe)",
}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


class ParametreManquant(Exception):
    pass


def evaluer(expr: Any, params: dict) -> float:
    """Évalue un nombre ou une formule simple (+ − × ÷, parenthèses, paramètres)."""
    if expr is None or expr == "":
        raise ParametreManquant("consommation")
    if isinstance(expr, (int, float)):
        return float(expr)
    try:
        return float(str(expr).replace(",", "."))
    except ValueError:
        pass
    arbre = ast.parse(str(expr).replace(",", "."), mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name):
            v = params.get(n.id)
            if v is None or v == "":
                raise ParametreManquant(n.id)
            return float(v)
        raise ValueError("Formule non autorisée")

    return ev(arbre)


def quantite_base(base: str, metre: dict, pans: set[str] | None) -> float:
    """Quantité de référence tirée du métré (éventuellement limitée à certains pans)."""
    ps = [p for p in metre["pans"] if pans is None or p["id"] in pans]
    if base == "surface":
        return sum(p["surface_nette"] for p in ps)
    if base == "surface_brute":
        return sum(p["surface"] for p in ps)
    if base == "surface_plan":
        return sum(p["surface_plan"] for p in ps)
    if base.startswith("ligne:"):
        t = base.split(":", 1)[1]
        types = {"egout"} if t == "gouttiere" else {t}
        tot = 0.0
        for lg in metre["lignes"]:
            if lg["type"] in types and (pans is None or not lg.get("pans") or set(lg["pans"]) & pans):
                tot += lg["longueur"]
        return tot
    if base.startswith("obstacles:"):
        _, typ, quoi = base.split(":")
        obs = [o for o in metre["obstacles"] if (typ == "tous" or o["type"] == typ)
               and (pans is None or o.get("pan_id") is None or o.get("pan_id") in pans)]
        if quoi == "nombre":
            return float(sum(o.get("nombre", 1) for o in obs))
        return sum(o["perimetre"] for o in obs)
    if base == "forfait":
        return 1.0
    raise ValueError(f"Base inconnue : {base}")


def calculer(metre: dict, selections: list[dict]) -> dict:
    """selections : [{ouvrage: {...articles, parametres}, pans: [ids] | None}]"""
    lignes = []
    manquants = 0
    total_ht = 0.0
    total_complet = True
    for sel in selections:
        ouv = sel["ouvrage"]
        params = {p["cle"]: p.get("valeur") for p in ouv.get("parametres", [])}
        pans = set(sel["pans"]) if sel.get("pans") else None
        for art in ouv.get("articles", []):
            if art.get("actif") is False:
                continue
            ligne = {"ouvrage": ouv.get("nom"), "article": art.get("nom"), "reference": art.get("reference"),
                     "fabricant": art.get("fabricant"), "unite": art.get("unite", "u"), "base": art.get("base"),
                     "base_libelle": BASES.get(art.get("base"), art.get("base")), "categorie": art.get("categorie")}
            try:
                q = quantite_base(art["base"], metre, pans)
                ligne["quantite_base"] = q
                if art["base"] == "forfait":
                    conso = evaluer(art.get("consommation") or 1, params)
                else:
                    conso = evaluer(art.get("consommation"), params)
                perte = evaluer(art.get("perte_pct") if art.get("perte_pct") not in (None, "") else 0, params)
                brut = q * conso
                tot = brut * (1 + perte / 100)
                ligne.update({"consommation": conso, "perte_pct": perte, "quantite": brut, "quantite_totale": tot,
                              "statut": "ok"})
                cond = art.get("conditionnement")
                if cond:
                    c = evaluer(cond, params)
                    if c > 0:
                        ligne["conditionnements"] = math.ceil(tot / c - 1e-9)
                        ligne["libelle_conditionnement"] = art.get("libelle_conditionnement") or "colis"
                        ligne["quantite_commandee"] = ligne["conditionnements"] * c
                pu = art.get("prix_unitaire")
                if pu not in (None, ""):
                    q_fact = ligne.get("quantite_commandee", tot)
                    ligne["prix_unitaire"] = float(pu)
                    ligne["montant_ht"] = q_fact * float(pu)
                    total_ht += ligne["montant_ht"]
                else:
                    total_complet = False
                if q == 0:
                    ligne["statut"] = "zero"
            except ParametreManquant as e:
                manquants += 1
                total_complet = False
                ligne.update({"statut": "a_completer",
                              "manque": "consommation (fiche fabricant)" if str(e) == "consommation" else str(e)})
            except (ValueError, ZeroDivisionError, SyntaxError) as e:
                manquants += 1
                total_complet = False
                ligne.update({"statut": "erreur", "manque": f"formule invalide ({e})"})
            lignes.append(ligne)
    return {"lignes": lignes, "a_completer": manquants, "total_ht": total_ht,
            "total_complet": total_complet and manquants == 0}


# ---------------------------------------------------------------------------
# Modèles d'ouvrages fournis : structure seulement, valeurs fabricant à compléter.
def _a(nom, base, unite, consommation=None, categorie="couverture", perte=None, **kw):
    d = {"nom": nom, "base": base, "unite": unite, "consommation": consommation, "categorie": categorie,
         "perte_pct": perte, "reference": None, "fabricant": None, "prix_unitaire": None,
         "conditionnement": None, "libelle_conditionnement": None, "actif": True}
    d.update(kw)
    return d


def _p(cle, libelle, unite, aide=""):
    return {"cle": cle, "libelle": libelle, "unite": unite, "valeur": None, "aide": aide}


MODELES_OUVRAGES = [
    {
        "code": "tuile_emboitement",
        "nom": "Tuiles à emboîtement (terre cuite ou béton)",
        "description": "Structure type à compléter avec la fiche technique de la tuile retenue.",
        "parametres": [
            _p("tuiles_m2", "Nombre de tuiles au m²", "u/m²", "Fiche fabricant, selon le pureau retenu."),
            _p("pureau", "Pureau (écartement des liteaux)", "m", "Fiche fabricant / DTU 40.21 ou 40.24."),
            _p("entraxe_chevrons", "Entraxe des chevrons (contre-liteaux)", "m", "Relevé sur place."),
            _p("faitieres_ml", "Faîtières par mètre", "u/ml", "Fiche fabricant."),
            _p("rives_ml", "Tuiles de rive par mètre", "u/ml", "Fiche fabricant."),
            _p("recouvrement_ecran", "Recouvrement de l'écran sous-toiture", "%", "Notice de l'écran."),
            _p("entraxe_crochets", "Entraxe des crochets de gouttière", "m", "DTU 40.5 / notice."),
        ],
        "articles": [
            _a("Tuiles courantes", "surface", "u", "tuiles_m2"),
            _a("Liteaux", "surface", "ml", "1/pureau", "support"),
            _a("Contre-liteaux", "surface", "ml", "1/entraxe_chevrons", "support"),
            _a("Écran sous-toiture", "surface", "m²", "1+recouvrement_ecran/100", "ecran"),
            _a("Tuiles faîtières", "ligne:faitage", "u", "faitieres_ml"),
            _a("Closoir de faîtage", "ligne:faitage", "ml", 1, "accessoire"),
            _a("Arêtiers", "ligne:aretier", "u", "faitieres_ml"),
            _a("Closoir d'arêtier", "ligne:aretier", "ml", 1, "accessoire"),
            _a("Tuiles de rive", "ligne:rive", "u", "rives_ml"),
            _a("Noue (zinc ou aluminium)", "ligne:noue", "ml", 1, "zinguerie"),
            _a("Bande d'égout / grille anti-rongeurs", "ligne:egout", "ml", 1, "accessoire"),
            _a("Gouttière", "ligne:gouttiere", "ml", 1, "zinguerie"),
            _a("Crochets de gouttière", "ligne:gouttiere", "u", "1/entraxe_crochets", "zinguerie"),
            _a("Abergement / solin de cheminée", "obstacles:cheminee:nombre", "u", 1, "zinguerie"),
            _a("Raccord de fenêtre de toit", "obstacles:fenetre_toit:nombre", "u", 1, "accessoire"),
        ],
    },
    {
        "code": "ardoise_naturelle",
        "nom": "Ardoises naturelles au crochet",
        "description": "Structure type (DTU 40.11) à compléter avec le format et le pureau retenus.",
        "parametres": [
            _p("ardoises_m2", "Nombre d'ardoises au m²", "u/m²", "Selon format et pureau (fiche / abaque)."),
            _p("pureau", "Pureau", "m", "Selon pente, format et zone climatique."),
            _p("crochets_ardoise", "Crochets par ardoise", "u", "En général 1 par ardoise courante."),
            _p("entraxe_crochets", "Entraxe des crochets de gouttière", "m", ""),
            _p("recouvrement_ecran", "Recouvrement de l'écran sous-toiture", "%", ""),
        ],
        "articles": [
            _a("Ardoises", "surface", "u", "ardoises_m2"),
            _a("Crochets inox", "surface", "u", "ardoises_m2*crochets_ardoise", "fixation"),
            _a("Voliges ou liteaux", "surface", "ml", "1/pureau", "support"),
            _a("Écran sous-toiture", "surface", "m²", "1+recouvrement_ecran/100", "ecran"),
            _a("Faîtage (zinc ou lignolet)", "ligne:faitage", "ml", 1, "zinguerie"),
            _a("Arêtiers", "ligne:aretier", "ml", 1, "zinguerie"),
            _a("Noues", "ligne:noue", "ml", 1, "zinguerie"),
            _a("Bandes de rive", "ligne:rive", "ml", 1, "zinguerie"),
            _a("Gouttière", "ligne:gouttiere", "ml", 1, "zinguerie"),
            _a("Crochets de gouttière", "ligne:gouttiere", "u", "1/entraxe_crochets", "zinguerie"),
            _a("Abergement de cheminée", "obstacles:cheminee:nombre", "u", 1, "zinguerie"),
        ],
    },
    {
        "code": "zinguerie_seule",
        "nom": "Zinguerie (gouttières et descentes)",
        "description": "Remplacement de gouttières et accessoires.",
        "parametres": [
            _p("entraxe_crochets", "Entraxe des crochets", "m", ""),
            _p("nb_descentes", "Nombre de descentes", "u", "Selon le relevé sur place."),
            _p("hauteur_descente", "Hauteur moyenne d'une descente", "m", ""),
        ],
        "articles": [
            _a("Gouttière", "ligne:gouttiere", "ml", 1, "zinguerie"),
            _a("Crochets", "ligne:gouttiere", "u", "1/entraxe_crochets", "zinguerie"),
            _a("Descentes EP", "forfait", "ml", "nb_descentes*hauteur_descente", "zinguerie"),
            _a("Naissances", "forfait", "u", "nb_descentes", "zinguerie"),
        ],
    },
    {
        "code": "demoussage",
        "nom": "Nettoyage / traitement de couverture",
        "description": "Chiffrage à la surface ; consommation produit selon fiche.",
        "parametres": [_p("conso_produit", "Consommation de produit", "L/m²", "Fiche du produit.")],
        "articles": [_a("Produit de traitement", "surface", "L", "conso_produit", "accessoire")],
    },
]
