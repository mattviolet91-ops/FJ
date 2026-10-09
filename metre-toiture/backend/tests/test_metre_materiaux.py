import math

import pytest

from mmt.core import materiaux as mat
from mmt.core import metre
from mmt.core import validation as val
from mmt.core.geometry import Plan
from mmt.core.plan_vol import generer_plan


def doc_deux_pans(valide=False, reference=None):
    d = metre.document_vide()
    d["echelle"]["source"] = "gps"
    sud = Plan.depuis_pente(35, 180, 0, 0, 5).to_dict()
    nord = Plan.depuis_pente(35, 0, 0, 8, 5).to_dict()
    d["pans"] = [
        {"id": "p1", "nom": "Sud", "contour": [[0, 0], [10, 0], [10, 4], [0, 4]], "plan": sud,
         "source_plan": "modele_3d", "stats": {"rms": 0.01, "couverture": 0.98, "resolution": 0.04}, "valide": valide},
        {"id": "p2", "nom": "Nord", "contour": [[0, 4], [10, 4], [10, 8], [0, 8]], "plan": nord,
         "source_plan": "modele_3d", "stats": {"rms": 0.01, "couverture": 0.98, "resolution": 0.04}, "valide": valide},
    ]
    d["obstacles"] = [{"id": "o1", "type": "fenetre_toit", "contour": [[2, 1], [3, 1], [3, 2.2], [2, 2.2]],
                       "deduire": True, "source": "manuel", "valide": True}]
    if reference:
        d["echelle"]["references"] = [reference]
    return d


def test_calcul_complet():
    c = metre.calculer(doc_deux_pans())
    s = 40 / math.cos(math.radians(35))
    assert c["totaux"]["surface_brute"] == pytest.approx(2 * s)
    deduc = 1.2 / math.cos(math.radians(35))
    assert c["totaux"]["deductions"] == pytest.approx(deduc)
    assert c["totaux"]["surface_nette"] == pytest.approx(2 * s - deduc)
    assert c["totaux_lignes"]["faitage"] == pytest.approx(10)
    assert c["totaux_lignes"]["egout"] == pytest.approx(20)
    assert c["totaux_lignes"]["gouttiere"] == pytest.approx(20)
    assert c["totaux_lignes"]["rive"] == pytest.approx(4 * 4 / math.cos(math.radians(35)))
    # échelle GPS non vérifiée => alerte et confiance plafonnée à « moyenne »
    assert any(x["code"] == "echelle" for x in c["controles"])
    assert c["confiance_globale"] == "moyenne"
    assert c["dimensions"]["longueur"] == pytest.approx(10)


def test_reference_corrige_echelle():
    # sur le modèle, l'égout mesure 10 ; en réalité 10,30 m
    ref = {"id": "r1", "p1": [0, 0, 5], "p2": [10, 0, 5], "reelle": 10.30}
    c = metre.calculer(doc_deux_pans(reference=ref))
    k = 1.03
    assert c["echelle"]["facteur"] == pytest.approx(k)
    assert c["echelle"]["source"] == "reference"
    assert c["totaux_lignes"]["faitage"] == pytest.approx(10 * k)
    assert c["totaux"]["surface_brute"] == pytest.approx(2 * 40 / math.cos(math.radians(35)) * k * k)
    assert c["echelle"]["incertitude_rel"] is not None
    assert not any(x["code"] == "echelle" for x in c["controles"])


def test_pan_saisi_par_dimensions():
    d = metre.document_vide()
    d["echelle"]["source"] = "saisie"
    d["pans"] = [{"id": "p1", "nom": "Long pan", "saisie": {"forme": "trapeze", "longueur_bas": 12,
                                                             "longueur_haut": 6, "rampant": 5, "pente_deg": 40}}]
    c = metre.calculer(d)
    assert c["totaux"]["surface_brute"] == pytest.approx(45)
    assert c["pans"][0]["source_plan"] == "saisie"
    assert c["pans"][0]["confiance"]["niveau"] == "saisie"


def test_recouvrement_signale():
    d = doc_deux_pans()
    d["pans"][1]["contour"] = [[0, 3], [10, 3], [10, 8], [0, 8]]
    c = metre.calculer(d)
    assert any(x["code"] == "recouvrement" for x in c["controles"])


def test_contour_croise_signale():
    d = doc_deux_pans()
    d["pans"][0]["contour"] = [[0, 0], [10, 4], [10, 0], [0, 4]]
    c = metre.calculer(d)
    assert any(x["code"] == "contour_croise" for x in c["controles"])


def test_comparaison_auto():
    d = doc_deux_pans()
    d["auto"] = {"pans": [{"id": "p1", "surface": 50.0}, {"id": "p2", "surface": 48.83}]}
    c = metre.calculer(d)
    comp = c["comparaison_auto"]
    assert comp["total_auto"] == pytest.approx(98.83)
    assert comp["pans"][0]["ecart"] == pytest.approx(48.83 - 50, abs=0.01)


def test_materiaux_sans_valeurs_inventees():
    c = metre.calculer(doc_deux_pans())
    modele = next(m for m in mat.MODELES_OUVRAGES if m["code"] == "tuile_emboitement")
    r = mat.calculer(c, [{"ouvrage": modele}])
    # aucun paramètre fabricant renseigné : les articles dépendants sont « à compléter »
    tuiles = next(l for l in r["lignes"] if l["article"] == "Tuiles courantes")
    assert tuiles["statut"] == "a_completer"
    assert not r["total_complet"]
    closoir = next(l for l in r["lignes"] if l["article"] == "Closoir de faîtage")
    assert closoir["statut"] == "ok" and closoir["quantite_totale"] == pytest.approx(10)


def test_materiaux_avec_parametres():
    c = metre.calculer(doc_deux_pans())
    modele = next(m for m in mat.MODELES_OUVRAGES if m["code"] == "tuile_emboitement")
    import copy
    o = copy.deepcopy(modele)
    vals = {"tuiles_m2": 13.5, "pureau": 0.37, "entraxe_chevrons": 0.6, "faitieres_ml": 2.5, "rives_ml": 3,
            "recouvrement_ecran": 10, "entraxe_crochets": 0.5}
    for p in o["parametres"]:
        p["valeur"] = vals[p["cle"]]
    for a in o["articles"]:
        if a["nom"] == "Tuiles courantes":
            a["perte_pct"] = 5
            a["conditionnement"] = 200
            a["prix_unitaire"] = 1.2
    r = mat.calculer(c, [{"ouvrage": o}])
    surf = c["totaux"]["surface_nette"]
    t = next(l for l in r["lignes"] if l["article"] == "Tuiles courantes")
    assert t["quantite_totale"] == pytest.approx(surf * 13.5 * 1.05)
    assert t["conditionnements"] == math.ceil(surf * 13.5 * 1.05 / 200)
    assert t["montant_ht"] == pytest.approx(t["conditionnements"] * 200 * 1.2)
    li = next(l for l in r["lignes"] if l["article"] == "Liteaux")
    assert li["quantite_totale"] == pytest.approx(surf / 0.37)
    cro = next(l for l in r["lignes"] if l["article"] == "Crochets de gouttière")
    assert cro["quantite_totale"] == pytest.approx(40)
    assert r["a_completer"] == 0


def test_formule_refuse_code():
    with pytest.raises(ValueError):
        mat.evaluer("__import__('os')", {})
    with pytest.raises(mat.ParametreManquant):
        mat.evaluer("1/pureau", {"pureau": None})


def test_checklist_validation():
    c = metre.calculer(doc_deux_pans(valide=True, reference={"p1": [0, 0, 5], "p2": [10, 0, 5], "reelle": 10}))
    v = val.checklist(c, {"mode": "3d", "reconstruction": "ok"},
                      {"obstacles_tous_saisis": True, "pentes_plausibles": True, "zones_cachees_traitees": True})
    assert v["statut"] == "ok" and v["pret_pour_devis"]
    v2 = val.checklist(metre.calculer(doc_deux_pans()), {"mode": "3d", "reconstruction": "ok"}, {})
    assert v2["statut"] == "attention"


def test_plan_de_vol():
    p = generer_plan({"type_toiture": "deux_pans", "longueur": 12, "largeur": 9, "hauteur_faitage": 8,
                      "drone": "dji_mini_3", "precision": "devis", "complexite": "simple"})
    # GSD visé 1,2 cm/px sur le toit
    assert p["gsd_toit_cm"] == pytest.approx(1.2, rel=0.01)
    assert p["hauteur_vol_sol_m"] > 8
    assert p["passages_verticaux"]["total"] > 10
    assert p["orbites"][0]["nb_photos"] == 36
    assert any("roulant" in c for c in p["conseils"])
    inconnu = generer_plan({"longueur": 10, "largeur": 8})
    assert inconnu["passages_verticaux"] is None and inconnu["alertes"]


def test_plan_dji_mini_4k():
    p = generer_plan({"type_toiture": "quatre_pans", "longueur": 14, "largeur": 10, "hauteur_faitage": 9,
                      "complexite": "moyenne", "drone": "dji_mini_4k", "precision": "devis"})
    assert p["camera"]["nom"] == "DJI Mini 4K"
    assert p["gsd_toit_cm"] == pytest.approx(1.2, rel=0.01)
    assert any("photo à intervalle" in c for c in p["conseils"])
    assert any("obstacles" in a for a in p["alertes"])
    assert p["batteries_estimees"] >= 2
