"""Détection automatique des pans de toiture sur un modèle numérique de surface (MNS).

Entrée : grille de hauteurs (MNS) issue de la reconstruction photogrammétrique.
Sortie : pans (contour en plan + plan ajusté + statistiques de qualité), émergences
détectées (cheminées, sorties de toit…) et avertissements.

Méthode (documentée dans docs/ARCHITECTURE.md) :
 1. lissage léger, normales locales par gradient ;
 2. isolement du bâtiment (cellules surélevées, composante connexe autour du point choisi) ;
 3. extraction itérative de plans par RANSAC « un point + normale » avec contrainte de
    connexité, puis ajustement par moindres carrés ;
 4. croissance des régions pour combler les bords, fusion des plans quasi coplanaires ;
 5. contour exact des régions, simplification, régularisation selon l'orientation
    dominante et recalage des arêtes communes sur l'intersection des plans voisins ;
 6. détection des émergences (cellules nettement au-dessus du plan du pan).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from . import geometry as geo


@dataclass
class Grille:
    """MNS régulier. z[i, j] : ligne i (vers le sud), colonne j (vers l'est)."""
    z: np.ndarray
    res: float
    x0: float  # abscisse du bord gauche
    y0: float  # ordonnée du bord haut
    valide: np.ndarray | None = None  # cellules réellement observées (avant bouchage)

    def xy(self, i, j):
        return self.x0 + (np.asarray(j) + 0.5) * self.res, self.y0 - (np.asarray(i) + 0.5) * self.res

    def ij(self, x, y):
        return int((self.y0 - y) / self.res), int((x - self.x0) / self.res)


@dataclass
class Parametres:
    hauteur_min_batiment: float = 1.8     # m au-dessus du sol
    tolerance_plan: float = 0.07          # m, distance max au plan (inliers)
    tolerance_angle: float = 12.0         # degrés, écart de normale max
    surface_min_pan: float = 1.0          # m²
    tolerance_comblement: float = 0.20    # m, pour rattacher les bords au pan voisin
    hauteur_emergence: float = 0.25       # m au-dessus du pan
    surface_min_emergence: float = 0.08   # m²
    max_pans: int = 40
    rms_max_pan: float = 0.06            # m, écart au plan maximal d'un pan accepté
    pente_max: float = 70.0              # degrés (au-delà : mur, façade, végétation)
    compacite_min: float = 0.45          # surface / surface de l'enveloppe convexe
    surface_fragment: float = 4.0        # m², fragments rattachés au pan voisin compatible
    lissage_m: float = 0.10               # écart-type du lissage (m)
    graine: int = 1


@dataclass
class Resultat:
    pans: list[dict] = field(default_factory=list)
    obstacles: list[dict] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    emprise: list[list[float]] = field(default_factory=list)
    z_sol: float = 0.0
    orientation_dominante_deg: float = 0.0
    labels: np.ndarray | None = None


# ---------------------------------------------------------------------------
def _boucher(z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valide = np.isfinite(z)
    if valide.all():
        return z.copy(), valide
    if not valide.any():
        raise ValueError("Le modèle de surface ne contient aucune donnée exploitable")
    idx = ndimage.distance_transform_edt(~valide, return_distances=False, return_indices=True)
    return z[tuple(idx)], valide


def _contour_masque(m: np.ndarray) -> list[tuple[float, float]]:
    """Contour extérieur exact (sur les coins des cellules) du masque, en coordonnées
    grille (u = colonne, v = ligne). Retourne la plus longue boucle."""
    H, W = m.shape
    p = np.zeros((H + 2, W + 2), dtype=bool)
    p[1:-1, 1:-1] = m
    succ: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def ajout(a, b):
        succ.setdefault(a, []).append(b)

    ii, jj = np.nonzero(p[1:-1, 1:-1])
    for i, j in zip(ii.tolist(), jj.tolist()):
        if not p[i, j + 1]:          # haut
            ajout((j, i), (j + 1, i))
        if not p[i + 1, j + 2]:      # droite
            ajout((j + 1, i), (j + 1, i + 1))
        if not p[i + 2, j + 1]:      # bas
            ajout((j + 1, i + 1), (j, i + 1))
        if not p[i + 1, j]:          # gauche
            ajout((j, i + 1), (j, i))
    boucles = []
    while succ:
        depart = next(iter(succ))
        boucle = [depart]
        cur = depart
        prev_dir = None
        while True:
            options = succ.get(cur)
            if not options:
                break
            if len(options) > 1 and prev_dir is not None:
                # au point de pincement, tourner à droite (sens écran) en priorité
                def rang(o):
                    d = (o[0] - cur[0], o[1] - cur[1])
                    cross = prev_dir[0] * d[1] - prev_dir[1] * d[0]
                    return -cross
                options.sort(key=rang)
            nxt = options.pop(0)
            if not options:
                del succ[cur]
            prev_dir = (nxt[0] - cur[0], nxt[1] - cur[1])
            cur = nxt
            if cur == depart:
                break
            boucle.append(cur)
        boucles.append(boucle)
    boucle = max(boucles, key=len)
    # supprimer les points alignés
    out = []
    n = len(boucle)
    for k in range(n):
        a, b, c = boucle[k - 1], boucle[k], boucle[(k + 1) % n]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0:
            out.append((float(b[0]), float(b[1])))
    return out


def _vers_monde(g: Grille, pts_uv) -> list[tuple[float, float]]:
    return [(g.x0 + u * g.res, g.y0 - v * g.res) for u, v in pts_uv]


def _orientation_dominante(polys: list[list[tuple[float, float]]]) -> float:
    """Angle (0-90°) dominant des arêtes, pondéré par la longueur."""
    angles, poids = [], []
    for poly in polys:
        n = len(poly)
        for k in range(n):
            (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % n]
            L = math.hypot(x2 - x1, y2 - y1)
            if L > 1e-6:
                angles.append(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 90)
                poids.append(L)
    if not angles:
        return 0.0
    a = np.array(angles)
    w = np.array(poids)
    hist = np.bincount(np.round(a).astype(int) % 90, weights=w, minlength=90)
    pic = int(np.argmax(ndimage.uniform_filter1d(hist, 5, mode="wrap")))
    ecart = (a - pic + 45) % 90 - 45
    proche = np.abs(ecart) < 5
    if not proche.any():
        return float(pic)
    return float((pic + np.sum(ecart[proche] * w[proche]) / w[proche].sum()) % 90)


def _ajuster(xs, ys, zs) -> tuple[geo.Plan, float]:
    return geo.ajuster_plan(np.column_stack([xs, ys, zs]))


# ---------------------------------------------------------------------------
def segmenter(g: Grille, graine_xy: tuple[float, float] | None = None,
              zone: list[tuple[float, float]] | None = None,
              p: Parametres | None = None, exclusion: np.ndarray | None = None) -> Resultat:
    """exclusion : cellules à écarter (ex. végétation détectée sur l'orthophoto)."""
    p = p or Parametres()
    rng = np.random.default_rng(p.graine)
    res = Resultat()
    z, valide = _boucher(g.z.astype(float))
    if g.valide is not None:
        valide = valide & g.valide
    H, W = z.shape
    cell_a = g.res * g.res
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    X, Y = g.xy(ii, jj)

    # --- 1. lissage et normales
    sig = max(0.6, p.lissage_m / g.res)
    zm = ndimage.median_filter(z, size=3)
    zs = ndimage.gaussian_filter(zm, sig)
    gy_r, gx_c = np.gradient(zs, g.res)
    gx = gx_c            # dz/dx (x = colonnes)
    gy = -gy_r           # dz/dy (y vers le haut = lignes décroissantes)
    courbure = np.abs(ndimage.laplace(zs)) / (g.res * g.res)

    # --- 2. bâtiment
    zone_mask = np.ones_like(z, dtype=bool)
    if zone and len(zone) >= 3:
        zone_mask = geo._masque_polygone(X, Y, zone)
    z_sol = float(np.nanpercentile(zm, 5))
    res.z_sol = z_sol
    sureleve = (zm > z_sol + p.hauteur_min_batiment) & zone_mask
    if exclusion is not None:
        # la végétation n'appartient pas au bâtiment (ouverture pour supprimer les pixels isolés)
        veg = ndimage.binary_opening(exclusion, iterations=2)
        sureleve &= ~veg
    lab, n = ndimage.label(sureleve)
    if n == 0:
        res.avertissements.append("Aucun volume surélevé détecté : vérifiez la zone ou la hauteur minimale.")
        return res
    if graine_xy is not None:
        gi, gj = g.ij(*graine_xy)
        gi, gj = min(max(gi, 0), H - 1), min(max(gj, 0), W - 1)
        k = lab[gi, gj]
        if k == 0:
            # composante la plus proche de la graine
            d, ind = ndimage.distance_transform_edt(lab == 0, return_indices=True)
            k = lab[ind[0][gi, gj], ind[1][gi, gj]]
    else:
        tailles = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        ci, cj = H / 2, W / 2
        coms = ndimage.center_of_mass(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        score = [t / (1 + math.hypot(c[0] - ci, c[1] - cj) * g.res / 10) for t, c in zip(tailles, coms)]
        k = int(np.argmax(score)) + 1
    batiment = ndimage.binary_fill_holes(lab == k)
    batiment = ndimage.binary_opening(batiment, iterations=1)
    if batiment.sum() * cell_a < p.surface_min_pan:
        res.avertissements.append("Le volume sélectionné est trop petit pour être une toiture.")
        return res

    # --- 3. extraction de plans
    cosmax = math.cos(math.radians(p.tolerance_angle))
    nrm = np.sqrt(1 + gx ** 2 + gy ** 2)
    nx, ny, nz = -gx / nrm, -gy / nrm, 1 / nrm
    seuil_courb = np.percentile(courbure[batiment], 60)
    candidat = batiment & (courbure <= max(seuil_courb, 1e-6))
    labels = -np.ones((H, W), dtype=int)
    plans: list[geo.Plan] = []
    echecs = 0
    while len(plans) < p.max_pans and echecs < 8:
        restant = candidat & (labels < 0)
        nr = int(restant.sum())
        if nr * cell_a < p.surface_min_pan:
            break
        ri, rj = np.nonzero(restant)
        sub = rng.choice(nr, size=min(nr, 25000), replace=False)
        si, sj = ri[sub], rj[sub]
        meilleurs = (-1, None)
        graines = rng.choice(nr, size=min(nr, 150), replace=False)
        for s in graines:
            i0, j0 = ri[s], rj[s]
            a, b = gx[i0, j0], gy[i0, j0]
            c = zs[i0, j0] - a * X[i0, j0] - b * Y[i0, j0]
            d = np.abs(zm[si, sj] - (a * X[si, sj] + b * Y[si, sj] + c)) / math.sqrt(1 + a * a + b * b)
            na, nb, nc = -a, -b, 1.0
            nn = math.sqrt(na * na + nb * nb + 1)
            cosang = (nx[si, sj] * na + ny[si, sj] * nb + nz[si, sj] * nc) / nn
            score = int(np.count_nonzero((d < p.tolerance_plan * 1.5) & (cosang > cosmax)))
            if score > meilleurs[0]:
                meilleurs = (score, (a, b, c))
        a, b, c = meilleurs[1]
        plan = geo.Plan(a, b, c)
        region = None
        for _ in range(3):
            d = np.abs(zm - plan.z(X, Y)) / plan.facteur_pente
            nn = plan.facteur_pente
            cosang = (nx * (-plan.a) + ny * (-plan.b) + nz) / nn
            inl = batiment & (labels < 0) & (d < p.tolerance_plan) & (cosang > cosmax)
            cl, nc_ = ndimage.label(inl, structure=np.ones((3, 3)))
            if nc_ == 0:
                region = None
                break
            tailles = ndimage.sum(inl, cl, index=np.arange(1, nc_ + 1))
            kk = int(np.argmax(tailles)) + 1
            region = cl == kk
            if region.sum() < 10:
                break
            plan, _ = _ajuster(X[region], Y[region], zm[region])
        acceptable = region is not None and region.sum() * cell_a >= p.surface_min_pan
        if acceptable:
            resid = (zm[region] - plan.z(X[region], Y[region])) / plan.facteur_pente
            rms_r = float(np.sqrt(np.mean(resid ** 2)))
            acceptable = rms_r <= p.rms_max_pan and plan.pente_deg <= p.pente_max and \
                _compacite(region) >= p.compacite_min
        if not acceptable:
            echecs += 1
            # neutraliser les meilleures graines pour ne pas boucler
            if region is not None:
                candidat &= ~region
            continue
        echecs = 0
        labels[region] = len(plans)
        plans.append(plan)

    if not plans:
        res.avertissements.append("Aucun pan plan n'a pu être identifié sur ce volume.")
        return res

    # --- 4. comblement des bords : croissance simultanée de toutes les régions, cellule par cellule,
    # en n'acceptant que les cellules proches du plan de la région voisine (vectorisé)
    _combler(labels, plans, batiment, zm, X, Y, p.tolerance_comblement)

    # --- fusion des plans coplanaires voisins
    def _coplanaires(p1: geo.Plan, p2: geo.Plan) -> bool:
        n1 = np.array([-p1.a, -p1.b, 1]) / p1.facteur_pente
        n2 = np.array([-p2.a, -p2.b, 1]) / p2.facteur_pente
        return float(n1 @ n2) > math.cos(math.radians(4))

    croix = ndimage.generate_binary_structure(2, 1)
    contact_min = max(3, int(0.5 / g.res))
    fusion = True
    while fusion:
        fusion = False
        for k1 in range(len(plans)):
            m1 = labels == k1
            if not m1.any():
                continue
            bord = ndimage.binary_dilation(m1, croix) & ~m1
            vois = set(np.unique(labels[bord]).tolist()) - {-1, k1}
            for k2 in vois:
                # fusion seulement si les régions partagent une vraie frontière (pas un simple point)
                if np.count_nonzero(bord & (labels == k2)) < contact_min:
                    continue
                if not _coplanaires(plans[k1], plans[k2]):
                    continue
                m = m1 | (labels == k2)
                pl, rms = _ajuster(X[m], Y[m], zm[m])
                if rms < p.tolerance_plan * 0.8:
                    labels[labels == k2] = k1
                    plans[k1] = pl
                    fusion = True
                    break
            if fusion:
                break

    # rattachement des petits fragments (MNS bruité ou « en escalier ») au voisin qui les explique
    for _ in range(3):
        tailles = {k: int((labels == k).sum()) for k in range(len(plans))}
        petits = sorted((k for k, n in tailles.items() if 0 < n * cell_a < p.surface_fragment), key=tailles.get)
        modif = False
        for k in petits:
            m = labels == k
            if not m.any():
                continue
            bord = ndimage.binary_dilation(m, croix) & ~m
            vois, nb = np.unique(labels[bord], return_counts=True)
            ordre = [v for v, c in sorted(zip(vois.tolist(), nb.tolist()), key=lambda t: -t[1]) if v >= 0 and v != k and c >= 2]
            for v in ordre:
                pv = plans[v]
                if np.median(np.abs(zm[m] - pv.z(X[m], Y[m]))) > p.tolerance_comblement / 2:
                    continue
                mm = m | (labels == v)
                pl, rms = _ajuster(X[mm], Y[mm], zm[mm])
                if rms <= p.rms_max_pan:
                    labels[m] = v
                    plans[v] = pl
                    modif = True
                    break
        if not modif:
            break

    # séparation des régions reliées par un simple point ou un isthme étroit
    it = max(1, int(round(0.15 / g.res)))
    for k in range(len(plans)):
        m = labels == k
        if not m.any():
            continue
        ouvert = ndimage.binary_opening(m, structure=croix, iterations=it)
        cl, ncl = ndimage.label(ouvert)
        if ncl < 2:
            continue
        tailles = ndimage.sum(ouvert, cl, index=np.arange(1, ncl + 1))
        gardes = [i + 1 for i, t in enumerate(tailles) if t * cell_a >= p.surface_min_pan]
        if len(gardes) < 2:
            continue
        cible = np.where(np.isin(cl, gardes), cl, 0)
        _, (ri, rj) = ndimage.distance_transform_edt(cible == 0, return_indices=True)
        affect = cible[ri, rj]
        for n, comp in enumerate(gardes):
            zone_c = m & (affect == comp)
            if n == 0:
                labels[zone_c] = k
                plans[k], _ = _ajuster(X[zone_c], Y[zone_c], zm[zone_c])
            else:
                labels[zone_c] = len(plans)
                pl, _ = _ajuster(X[zone_c], Y[zone_c], zm[zone_c])
                plans.append(pl)

    # régions disjointes : composantes significatives séparées, miettes supprimées
    ids = []
    for k in range(len(plans)):
        m = labels == k
        cl, ncl = ndimage.label(m)
        if ncl > 1:
            tailles = ndimage.sum(m, cl, index=np.arange(1, ncl + 1))
            ordre = np.argsort(tailles)[::-1]
            for rang, i in enumerate(ordre):
                comp = cl == (i + 1)
                if rang == 0:
                    continue
                if tailles[i] * cell_a >= p.surface_min_pan:
                    labels[comp] = len(plans)
                    pl, _ = _ajuster(X[comp], Y[comp], zm[comp])
                    plans.append(pl)
                else:
                    labels[comp] = -1
    for k in range(len(plans)):
        m = labels == k
        aire_k = m.sum() * cell_a
        if aire_k < p.surface_min_pan:
            labels[m] = -1
        elif aire_k < 6.0 and _compacite(m) < 0.4:
            # petite région très irrégulière : typiquement de la végétation ou du bruit
            labels[m] = -1
        elif m.any():
            ids.append(k)
    res.labels = labels

    # --- 5. contours
    polys: dict[int, list[tuple[float, float]]] = {}
    masques: dict[int, np.ndarray] = {}
    bruts: dict[int, np.ndarray] = {}
    # tolérance de simplification adaptée au bruit réel du modèle (écart au plan médian des pans)
    rms_pans = []
    for k in ids:
        m = labels == k
        r = (zm[m] - plans[k].z(X[m], Y[m])) / plans[k].facteur_pente
        rms_pans.append(float(np.sqrt(np.mean(r ** 2))))
    bruit = float(np.median(rms_pans)) if rms_pans else 0.0
    tol_dp = max(1.5 * g.res, 0.08, 2.5 * bruit)
    for k in ids:
        m = labels == k
        # combler les trous qui ne contiennent aucun autre pan
        plein = ndimage.binary_fill_holes(m)
        trous = plein & ~m
        if trous.any():
            tl, nt = ndimage.label(trous)
            for t in range(1, nt + 1):
                if (labels[tl == t] >= 0).any():
                    plein[tl == t] = False
        masques[k] = plein
        uv = _contour_masque(plein)
        brut = geo.antihoraire(_vers_monde(g, uv))
        poly = geo.simplifier_anneau(brut, tol_dp)
        if len(poly) >= 3:
            polys[k] = poly
            bruts[k] = _densifier(brut, g.res / 2)
    ids = [k for k in ids if k in polys]
    theta = _orientation_dominante(list(polys.values()))
    res.orientation_dominante_deg = theta

    # recalage
    regul = {}
    for k in ids:
        regul[k] = _regulariser(k, polys[k], bruts[k], plans, labels, g, theta)
    regul = _souder(regul, tol=max(0.15, 3 * g.res))

    # --- 6. statistiques et émergences
    for k in ids:
        m = labels == k
        poly = regul[k]
        pl = plans[k]
        resid = (zm[m] - pl.z(X[m], Y[m])) / pl.facteur_pente
        pm = masques[k]
        couverture = float(valide[pm].mean()) if pm.any() else 0.0
        res.pans.append({
            "contour": [[float(x), float(y)] for x, y in poly],
            "plan": pl.to_dict(),
            "stats": {
                "rms": float(np.sqrt(np.mean(resid ** 2))),
                "n_points": int(m.sum()),
                "couverture": couverture,
                "resolution": g.res,
            },
        })
        sur = pm & (labels != k) & ((zm - pl.z(X, Y)) > p.hauteur_emergence)
        sur &= ~np.isin(labels, [q for q in ids if q != k])
        ol, no = ndimage.label(sur)
        for o in range(1, no + 1):
            mo = ol == o
            if mo.sum() * cell_a < p.surface_min_emergence:
                continue
            pts = np.column_stack([X[mo], Y[mo]])
            rect = _rectangle_oriente(pts, g.res)
            res.obstacles.append({
                "type": "emergence",
                "contour": [[float(x), float(y)] for x, y in rect],
                "hauteur": float(np.max(zm[mo] - pl.z(X[mo], Y[mo]))),
                "pan_index": len(res.pans) - 1,
            })
        if couverture < 0.85:
            res.avertissements.append(
                f"Pan {len(res.pans)} : {round((1 - couverture) * 100)} % de la surface n'a pas été observée "
                "directement (zone interpolée). Complétez les prises de vue de ce versant.")
    emp = ndimage.binary_fill_holes(labels >= 0)
    if emp.any():
        e = geo.antihoraire(_vers_monde(g, _contour_masque(emp)))
        res.emprise = [[x, y] for x, y in geo.simplifier_anneau(e, tol_dp)]
    non_couvert = batiment & (labels < 0)
    part = non_couvert.sum() / max(1, batiment.sum())
    if part > 0.15:
        res.avertissements.append(
            f"{round(part * 100)} % du volume du bâtiment n'a été rattaché à aucun pan "
            "(végétation, superstructures ou zones mal reconstruites). Contrôlez les contours.")
    return res


def _compacite(m: np.ndarray) -> float:
    """Rapport entre la surface d'une région et celle de son enveloppe convexe (1 = convexe)."""
    from scipy.spatial import ConvexHull
    ii, jj = np.nonzero(m)
    if len(ii) < 10:
        return 0.0
    pts = np.column_stack([ii, jj]).astype(float)
    try:
        h = ConvexHull(pts)
    except Exception:
        return 0.0
    return float(min(1.0, len(ii) / max(h.volume, 1.0)))


def _combler(labels: np.ndarray, plans: list[geo.Plan], masque: np.ndarray, z: np.ndarray, X: np.ndarray,
             Y: np.ndarray, tol: float, max_iter: int = 400) -> None:
    H, W = labels.shape
    A = np.array([pl.a for pl in plans])
    B = np.array([pl.b for pl in plans])
    C = np.array([pl.c for pl in plans])
    voisins = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for _ in range(max_iter):
        libre = masque & (labels < 0)
        # seules les cellules libres au contact d'une région sont candidates
        front = libre & ndimage.binary_dilation(labels >= 0, structure=np.ones((3, 3)))
        ii, jj = np.nonzero(front)
        if not len(ii):
            break
        meilleur_r = np.full(len(ii), np.inf)
        meilleur_l = np.full(len(ii), -1)
        zc, xc, yc = z[ii, jj], X[ii, jj], Y[ii, jj]
        for di, dj in voisins:
            ni, nj = ii + di, jj + dj
            ok = (ni >= 0) & (ni < H) & (nj >= 0) & (nj < W)
            L = np.full(len(ii), -1)
            L[ok] = labels[ni[ok], nj[ok]]
            v = L >= 0
            if not v.any():
                continue
            r = np.full(len(ii), np.inf)
            Lv = L[v]
            r[v] = np.abs(zc[v] - (A[Lv] * xc[v] + B[Lv] * yc[v] + C[Lv]))
            maj = (r < tol) & (r < meilleur_r)
            meilleur_r[maj] = r[maj]
            meilleur_l[maj] = L[maj]
        sel = meilleur_l >= 0
        if not sel.any():
            break
        labels[ii[sel], jj[sel]] = meilleur_l[sel]


def _rectangle_oriente(pts: np.ndarray, res: float) -> list[tuple[float, float]]:
    """Rectangle d'aire minimale englobant les centres de cellules (élargi d'une demi-cellule)."""
    from scipy.spatial import ConvexHull
    if len(pts) < 3:
        x, y = pts.mean(axis=0)
        h = res / 2
        return [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]
    try:
        hull = pts[ConvexHull(pts).vertices]
    except Exception:
        hull = pts
    best = None
    for k in range(len(hull)):
        e = hull[(k + 1) % len(hull)] - hull[k]
        L = np.hypot(*e)
        if L < 1e-9:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        pu, pv = hull @ u, hull @ v
        a = (pu.max() - pu.min() + res) * (pv.max() - pv.min() + res)
        if best is None or a < best[0]:
            best = (a, u, v, pu.min() - res / 2, pu.max() + res / 2, pv.min() - res / 2, pv.max() + res / 2)
    _, u, v, u0, u1, v0, v1 = best
    coins = [u0 * u + v0 * v, u1 * u + v0 * v, u1 * u + v1 * v, u0 * u + v1 * v]
    return geo.antihoraire([(float(c[0]), float(c[1])) for c in coins])


def _voisin_arete(a, b, k, labels, g: Grille) -> int:
    """Étiquette majoritaire juste à l'extérieur de l'arête (a,b) du pan k."""
    L = math.dist(a, b)
    if L < 1e-9:
        return -1
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    # contour antihoraire : extérieur à droite
    ox, oy = uy, -ux
    H, W = labels.shape
    votes: dict[int, int] = {}
    n = max(3, int(L / g.res / 2))
    for t in np.linspace(0.15, 0.85, n):
        for off in (1.5, 3.0):
            x = a[0] + (b[0] - a[0]) * t + ox * off * g.res
            y = a[1] + (b[1] - a[1]) * t + oy * off * g.res
            i, j = g.ij(x, y)
            if 0 <= i < H and 0 <= j < W:
                l = int(labels[i, j])
                if l != k:
                    votes[l] = votes.get(l, 0) + 1
    if not votes:
        return -1
    l, c = max(votes.items(), key=lambda kv: kv[1])
    if l >= 0 and c >= 0.5 * sum(votes.values()):
        return l
    return -1


def _densifier(poly, pas: float) -> np.ndarray:
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.dist(a, b)
        m = max(1, int(L / pas))
        for t in range(m):
            out.append((a[0] + (b[0] - a[0]) * t / m, a[1] + (b[1] - a[1]) * t / m))
    return np.array(out)


def _regulariser(k, poly, brut, plans, labels, g: Grille, theta: float):
    """Remplace chaque arête par une droite : intersection des plans voisins pour les
    arêtes communes, droite ajustée sur le contour brut (et recalée sur l'orientation
    dominante) pour les bords libres. Les sommets sont les intersections des droites."""
    n = len(poly)
    aretes = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        aretes.append([a, b, _voisin_arete(a, b, k, labels, g)])
    # fusion des arêtes consécutives ayant le même voisin (>=0)
    fus = []
    for a, b, v in aretes:
        if fus and v >= 0 and fus[-1][2] == v:
            fus[-1][1] = b
        else:
            fus.append([a, b, v])
    if len(fus) > 1 and fus[0][2] >= 0 and fus[0][2] == fus[-1][2]:
        fus[0][0] = fus[-1][0]
        fus.pop()
    tol = max(1.5 * g.res, 0.08)
    droites = []
    for a, b, v in fus:
        L = math.dist(a, b)
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L) if L > 1e-9 else (1.0, 0.0)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        droite = None
        if v >= 0:
            p1, p2 = plans[k], plans[v]
            da, db, dc = p1.a - p2.a, p1.b - p2.b, p1.c - p2.c
            nn = math.hypot(da, db)
            if nn > 1e-3:
                # droite da·x + db·y + dc = 0
                dirv = (-db / nn, da / nn)
                if dirv[0] * d[0] + dirv[1] * d[1] < 0:
                    dirv = (-dirv[0], -dirv[1])
                t = -(da * m[0] + db * m[1] + dc) / (nn * nn)
                pt = (m[0] + da * t, m[1] + db * t)
                if geo.distance_point_segment(pt, a, b) < max(0.4, 6 * g.res) and \
                        abs(dirv[0] * d[0] + dirv[1] * d[1]) > math.cos(math.radians(15)):
                    droite = (pt, dirv, True, L)
        if droite is None:
            # points du contour brut appartenant à l'arête
            if L > 1e-9 and len(brut):
                rel = brut - np.array(a)
                t = (rel @ np.array(d)) / L
                dist = np.abs(rel @ np.array([-d[1], d[0]]))
                sel = brut[(t > 0.08) & (t < 0.92) & (dist < 1.5 * tol)]
            else:
                sel = np.zeros((0, 2))
            if len(sel) >= 4:
                c = sel.mean(axis=0)
                u, s_, vt = np.linalg.svd(sel - c)
                dd = vt[0]
                if dd @ np.array(d) < 0:
                    dd = -dd
                d = (float(dd[0]), float(dd[1]))
                m = (float(c[0]), float(c[1]))
            ang = math.degrees(math.atan2(d[1], d[0]))
            rel_ = (ang - theta) % 90
            ecart = rel_ if rel_ < 45 else rel_ - 90
            if abs(ecart) < 8 and L > 0.5:
                r = math.radians(ang - ecart)
                d = (math.cos(r), math.sin(r))
                if len(sel) >= 4:
                    # recentrer : décalage moyen perpendiculaire
                    nrm = np.array([-d[1], d[0]])
                    off = float(((sel - np.array(m)) @ nrm).mean())
                    m = (m[0] + off * nrm[0], m[1] + off * nrm[1])
            droite = (m, d, False, L)
        droites.append(droite)

    # suppression des petites arêtes libres (coins écornés par la pixellisation)
    court = max(4 * g.res, 0.3)
    change = True
    while change and len(droites) > 3:
        change = False
        for i in range(len(droites)):
            pm, dm, partage, L = droites[i]
            if partage or L >= court:
                continue
            p0, d0, _, _ = droites[i - 1]
            p2, d2, _, _ = droites[(i + 1) % len(droites)]
            x = geo.intersection_droites(p0, d0, p2, d2)
            if x is not None and math.dist(x, pm) < 3 * court:
                droites.pop(i)
                fus.pop(i)
                change = True
                break

    m_ = len(droites)
    if m_ < 3:
        return poly
    out = []
    for i in range(m_):
        p1, d1, _, _ = droites[i - 1]
        p2, d2, _, _ = droites[i]
        orig = fus[i][0]
        x = geo.intersection_droites(p1, d1, p2, d2)
        if x is None or math.dist(x, orig) > max(1.0, 10 * g.res):
            t = (orig[0] - p2[0]) * d2[0] + (orig[1] - p2[1]) * d2[1]
            x = (p2[0] + t * d2[0], p2[1] + t * d2[1])
        out.append(x)
    out = geo.antihoraire(out)
    a0, a1 = geo.aire(poly), geo.aire(out)
    if not geo.polygone_simple(out) or abs(a1 - a0) > 0.15 * a0:
        return poly
    return out


def _souder(polys: dict, tol: float) -> dict:
    """Fusionne les sommets proches de pans différents (jonctions de 3 pans, etc.)."""
    pts = [(k, i, p) for k, poly in polys.items() for i, p in enumerate(poly)]
    groupes: list[list[int]] = []
    vu = [False] * len(pts)
    for a in range(len(pts)):
        if vu[a]:
            continue
        g_ = [a]
        vu[a] = True
        for b in range(a + 1, len(pts)):
            if not vu[b] and pts[b][0] != pts[a][0] and math.dist(pts[a][2], pts[b][2]) < tol:
                g_.append(b)
                vu[b] = True
        groupes.append(g_)
    out = {k: list(poly) for k, poly in polys.items()}
    for g_ in groupes:
        if len(g_) < 2:
            continue
        mx = sum(pts[i][2][0] for i in g_) / len(g_)
        my = sum(pts[i][2][1] for i in g_) / len(g_)
        for i in g_:
            k, idx, _ = pts[i]
            out[k][idx] = (mx, my)
    for k in out:
        if not geo.polygone_simple(out[k]):
            out[k] = polys[k]
    return out
