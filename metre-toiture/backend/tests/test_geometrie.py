import math

import pytest

from mmt.core import geometry as geo
from mmt.core.segmentation import segmenter

from synth import deux_pans, en_L, quatre_pans, surface_quatre_pans


def _pans(res):
    return [geo.Pan(f"p{i}", [tuple(c) for c in d["contour"]], geo.Plan.from_dict(d["plan"]))
            for i, d in enumerate(res.pans)]


def test_plan_depuis_pente():
    p = geo.Plan.depuis_pente(30, 180)  # pan exposé au sud
    assert p.pente_deg == pytest.approx(30)
    assert p.azimut_deg == pytest.approx(180)
    assert geo.orientation_texte(p.azimut_deg) == "S"
    assert p.facteur_pente == pytest.approx(1 / math.cos(math.radians(30)))
    assert p.pente_pct == pytest.approx(57.735, rel=1e-4)


def test_ajuster_plan_exact():
    pl = geo.Plan(0.2, -0.5, 3)
    pts = [(x, y, pl.z(x, y)) for x in range(5) for y in range(4)]
    fit, rms = geo.ajuster_plan(pts)
    assert fit.a == pytest.approx(0.2) and fit.b == pytest.approx(-0.5) and fit.c == pytest.approx(3)
    assert rms < 1e-9


def test_surface_rectangle_incline():
    pan = geo.Pan("a", [(0, 0), (10, 0), (10, 4), (0, 4)], geo.Plan.depuis_pente(45, 180, z0=5))
    assert pan.aire_plan == pytest.approx(40)
    assert pan.aire_reelle == pytest.approx(40 * math.sqrt(2))
    assert pan.rampant() == pytest.approx(4 * math.sqrt(2))


def test_polygone_croise_detecte():
    assert geo.polygone_simple([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert not geo.polygone_simple([(0, 0), (1, 1), (1, 0), (0, 1)])


def test_classification_deux_pans_manuels():
    # deux pans dessinés à la main partageant un faîtage horizontal (y = 4)
    sud = geo.Pan("s", [(0, 0), (10, 0), (10, 4), (0, 4)], geo.Plan.depuis_pente(35, 180, 0, 0, 5))
    nord = geo.Pan("n", [(0, 4), (10, 4), (10, 8), (0, 8)], geo.Plan.depuis_pente(35, 0, 0, 8, 5))
    lignes = geo.classer_lignes([sud, nord])
    types = sorted(l.type for l in lignes)
    assert types == ["egout", "egout", "faitage", "rive", "rive", "rive", "rive"]
    fait = [l for l in lignes if l.type == "faitage"][0]
    assert fait.longueur == pytest.approx(10)
    assert fait.incoherence_z < 1e-6


def test_noue_detectee():
    # deux pans formant un angle rentrant : ils descendent tous deux vers la ligne commune
    a = geo.Pan("a", [(0, 0), (4, 0), (4, 4), (0, 4)], geo.Plan.depuis_pente(30, 90, 4, 0, 0))
    b = geo.Pan("b", [(4, 0), (8, 0), (8, 4), (4, 4)], geo.Plan.depuis_pente(30, 270, 4, 0, 0))
    lignes = geo.classer_lignes([a, b])
    assert any(l.type == "noue" and l.longueur == pytest.approx(4) for l in lignes)


@pytest.mark.parametrize("bruit", [0.0, 0.015])
def test_detection_deux_pans(bruit):
    res = segmenter(deux_pans(bruit=bruit, cheminee=True))
    pans = _pans(res)
    assert len(pans) == 2
    attendu = 10 * 8 / math.cos(math.radians(35))
    assert sum(p.aire_reelle for p in pans) == pytest.approx(attendu, rel=0.01)
    for p in pans:
        assert p.plan.pente_deg == pytest.approx(35, abs=0.5)
    lignes = geo.classer_lignes(pans)
    fait = sum(l.longueur for l in lignes if l.type == "faitage")
    assert fait == pytest.approx(10, rel=0.02)
    eg = sum(l.longueur for l in lignes if l.type == "egout")
    assert eg == pytest.approx(20, rel=0.02)
    assert len(res.obstacles) == 1  # la cheminée


def test_detection_quatre_pans():
    res = segmenter(quatre_pans())
    pans = _pans(res)
    assert len(pans) == 4
    assert sum(p.aire_reelle for p in pans) == pytest.approx(surface_quatre_pans(12, 8, 30), rel=0.01)
    lignes = geo.classer_lignes(pans)
    aretiers = [l for l in lignes if l.type == "aretier"]
    assert len(aretiers) == 4
    # arêtier : projection 4·√2, dénivelé 4·tan(30°)
    L = math.sqrt(32 + (4 * math.tan(math.radians(30))) ** 2)
    for a in aretiers:
        assert a.longueur == pytest.approx(L, rel=0.03)
    assert sum(l.longueur for l in lignes if l.type == "faitage") == pytest.approx(4, rel=0.05)


def test_detection_en_L_surface_et_noues():
    g = en_L()
    res = segmenter(g)
    pans = _pans(res)
    # emprise de l'union des deux ailes : 72 + 72 - 36 = 108 m², partout à 35°
    ref = 108 / math.cos(math.radians(35))
    assert sum(p.aire_reelle for p in pans) == pytest.approx(ref, rel=0.01)
    lignes = geo.classer_lignes(pans)
    assert sum(1 for l in lignes if l.type == "noue") >= 2
