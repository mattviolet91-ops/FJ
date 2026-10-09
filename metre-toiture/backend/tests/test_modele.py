import numpy as np
import pytest

from mmt.services import modele as mod


def test_couverture_par_le_nuage(tmp_path):
    # nuage couvrant uniquement la moitié ouest d'un carré de 10 × 10 m, à z = 5
    rng = np.random.default_rng(0)
    pts = np.column_stack([rng.uniform(0, 5, 40000), rng.uniform(0, 10, 40000), np.full(40000, 5.0)])
    np.save(tmp_path / "nuage_xyz.npy", pts.astype(np.float32))
    carre = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert mod.couverture_nuage(tmp_path, carre) == pytest.approx(0.5, abs=0.03)
    # points éloignés du plan du pan (ex. végétation au-dessus) : non comptés
    assert mod.couverture_nuage(tmp_path, carre, z_plan=lambda x, y: x * 0 + 8.0) == pytest.approx(0.0)
    assert mod.couverture_nuage(tmp_path / "absent", carre) is None
