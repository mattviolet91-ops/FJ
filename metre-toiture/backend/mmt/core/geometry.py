"""Géométrie des toitures : pans plans, surfaces réelles, longueurs, classification des lignes.

Conventions
-----------
* Repère local métrique : x vers l'Est, y vers le Nord, z vers le haut (mètres).
* Un pan est décrit par son contour en plan (projection horizontale, liste de [x, y])
  et par l'équation de son plan  z = a·x + b·y + c.
  La surface réelle (rampante) vaut  surface_plan × sqrt(1 + a² + b²).
* Ce module est pur (aucune E/S) afin d'être testé exhaustivement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

Point2 = tuple[float, float]

# Types de lignes reconnus
FAITAGE = "faitage"          # ligne haute horizontale commune à deux pans
ARETIER = "aretier"          # ligne haute inclinée commune à deux pans (croupe)
NOUE = "noue"                # ligne basse commune à deux pans (angle rentrant)
EGOUT = "egout"              # bord bas horizontal (reçoit la gouttière)
RIVE = "rive"                # bord libre incliné (pignon)
RIVE_HAUTE = "rive_haute"    # bord haut horizontal libre (tête d'appentis)
BRIS = "bris"                # changement de pente entre deux pans (brisis / terrasson)
SOLIN = "solin"              # raccord contre un mur (défini par l'utilisateur)
AUTRE = "autre"

TYPES_LIGNES = {
    FAITAGE: "Faîtage",
    ARETIER: "Arêtier",
    NOUE: "Noue",
    EGOUT: "Égout",
    RIVE: "Rive",
    RIVE_HAUTE: "Rive haute / tête d'appentis",
    BRIS: "Ligne de bris",
    SOLIN: "Solin / raccord mur",
    AUTRE: "Autre",
}

ORIENTATIONS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------
@dataclass
class Plan:
    a: float
    b: float
    c: float

    def z(self, x: float, y: float) -> float:
        return self.a * x + self.b * y + self.c

    @property
    def facteur_pente(self) -> float:
        """Rapport surface réelle / surface projetée."""
        return math.sqrt(1.0 + self.a * self.a + self.b * self.b)

    @property
    def pente_rad(self) -> float:
        return math.atan(math.hypot(self.a, self.b))

    @property
    def pente_deg(self) -> float:
        return math.degrees(self.pente_rad)

    @property
    def pente_pct(self) -> float:
        return 100.0 * math.hypot(self.a, self.b)

    @property
    def descente(self) -> Point2 | None:
        """Vecteur unitaire (plan) de la ligne de plus grande pente, vers le bas."""
        g = math.hypot(self.a, self.b)
        if g < 1e-9:
            return None
        return (-self.a / g, -self.b / g)

    @property
    def azimut_deg(self) -> float | None:
        """Azimut de la descente (0 = Nord, 90 = Est), c.-à-d. l'exposition du pan."""
        d = self.descente
        if d is None:
            return None
        return math.degrees(math.atan2(d[0], d[1])) % 360.0

    @staticmethod
    def depuis_pente(pente_deg: float, azimut_deg: float, x0: float = 0.0, y0: float = 0.0,
                     z0: float = 0.0) -> "Plan":
        """Construit un plan à partir d'une pente, d'une exposition et d'un point."""
        t = math.tan(math.radians(pente_deg))
        th = math.radians(azimut_deg)
        a = -t * math.sin(th)
        b = -t * math.cos(th)
        return Plan(a, b, z0 - a * x0 - b * y0)

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "c": self.c}

    @staticmethod
    def from_dict(d: dict) -> "Plan":
        return Plan(float(d["a"]), float(d["b"]), float(d.get("c", 0.0)))


def ajuster_plan(points: Iterable[tuple[float, float, float]]) -> tuple[Plan, float]:
    """Ajuste z = a x + b y + c par moindres carrés. Retourne le plan et l'écart-type
    des résidus orthogonaux (m)."""
    import numpy as np

    p = np.asarray(list(points), dtype=float)
    if p.shape[0] < 3:
        raise ValueError("Au moins 3 points sont nécessaires pour ajuster un plan")
    cx, cy = p[:, 0].mean(), p[:, 1].mean()
    A = np.column_stack([p[:, 0] - cx, p[:, 1] - cy, np.ones(len(p))])
    sol, *_ = np.linalg.lstsq(A, p[:, 2], rcond=None)
    a, b, c0 = sol
    plan = Plan(float(a), float(b), float(c0 - a * cx - b * cy))
    res = (p[:, 2] - (a * (p[:, 0] - cx) + b * (p[:, 1] - cy) + c0)) / plan.facteur_pente
    return plan, float(np.sqrt(np.mean(res ** 2)))


def orientation_texte(azimut: float | None) -> str:
    if azimut is None:
        return "Plat"
    return ORIENTATIONS[int(((azimut + 22.5) % 360) // 45)]


# ---------------------------------------------------------------------------
# Polygones
# ---------------------------------------------------------------------------
def aire_signee(poly: list[Point2]) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def aire(poly: list[Point2]) -> float:
    return abs(aire_signee(poly))


def perimetre(poly: list[Point2]) -> float:
    n = len(poly)
    return sum(math.dist(poly[i], poly[(i + 1) % n]) for i in range(n))


def antihoraire(poly: list[Point2]) -> list[Point2]:
    return list(poly) if aire_signee(poly) >= 0 else list(reversed(poly))


def centroide(poly: list[Point2]) -> Point2:
    a = aire_signee(poly)
    if abs(a) < 1e-12:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (cx / (6 * a), cy / (6 * a))


def point_dans_polygone(pt: Point2, poly: list[Point2]) -> bool:
    x, y = pt
    dedans = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                dedans = not dedans
        j = i
    return dedans


def _orient(p, q, r) -> float:
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def segments_se_coupent(p1, p2, p3, p4) -> bool:
    """Intersection stricte (hors extrémités partagées)."""
    d1 = _orient(p3, p4, p1)
    d2 = _orient(p3, p4, p2)
    d3 = _orient(p1, p2, p3)
    d4 = _orient(p1, p2, p4)
    return ((d1 > 1e-12 and d2 < -1e-12) or (d1 < -1e-12 and d2 > 1e-12)) and \
           ((d3 > 1e-12 and d4 < -1e-12) or (d3 < -1e-12 and d4 > 1e-12))


def polygone_simple(poly: list[Point2]) -> bool:
    n = len(poly)
    if n < 3:
        return False
    for i in range(n):
        a1, a2 = poly[i], poly[(i + 1) % n]
        for j in range(i + 1, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            if segments_se_coupent(a1, a2, poly[j], poly[(j + 1) % n]):
                return False
    return True


def distance_point_segment(p: Point2, a: Point2, b: Point2) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def douglas_peucker(pts: list[Point2], tol: float) -> list[Point2]:
    if len(pts) < 3:
        return list(pts)
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = distance_point_segment(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        g = douglas_peucker(pts[: idx + 1], tol)
        d = douglas_peucker(pts[idx:], tol)
        return g[:-1] + d
    return [pts[0], pts[-1]]


def simplifier_anneau(poly: list[Point2], tol: float) -> list[Point2]:
    """Douglas-Peucker sur un anneau fermé, en partant des deux points les plus éloignés."""
    n = len(poly)
    if n <= 4:
        return list(poly)
    i0 = 0
    i1 = max(range(n), key=lambda k: math.dist(poly[0], poly[k]))
    a = poly[i0: i1 + 1]
    b = poly[i1:] + poly[: 1]
    s = douglas_peucker(a, tol)[:-1] + douglas_peucker(b, tol)[:-1]
    # retirer les sommets quasi alignés restants
    out = []
    m = len(s)
    for k in range(m):
        if distance_point_segment(s[k], s[k - 1], s[(k + 1) % m]) > tol * 0.5:
            out.append(s[k])
    return out if len(out) >= 3 else s


def intersection_droites(p1: Point2, d1: Point2, p2: Point2, d2: Point2) -> Point2 | None:
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def longueur_3d(p: Point2, q: Point2, plan: Plan) -> float:
    dx, dy = q[0] - p[0], q[1] - p[1]
    dz = plan.a * dx + plan.b * dy
    return math.sqrt(dx * dx + dy * dy + dz * dz)


# ---------------------------------------------------------------------------
# Pans, obstacles et lignes
# ---------------------------------------------------------------------------
@dataclass
class Pan:
    id: str
    contour: list[Point2]
    plan: Plan
    nom: str = ""

    @property
    def aire_plan(self) -> float:
        return aire(self.contour)

    @property
    def aire_reelle(self) -> float:
        return self.aire_plan * self.plan.facteur_pente

    def rampant(self) -> float:
        """Longueur maximale mesurée suivant la ligne de plus grande pente (m)."""
        d = self.plan.descente
        if d is None:
            return 0.0
        proj = [p[0] * d[0] + p[1] * d[1] for p in self.contour]
        return (max(proj) - min(proj)) / math.cos(self.plan.pente_rad)

    def sommets_3d(self) -> list[tuple[float, float, float]]:
        return [(x, y, self.plan.z(x, y)) for x, y in self.contour]


@dataclass
class Ligne:
    type: str
    p1: Point2
    p2: Point2
    longueur: float
    pans: list[str]
    z1: float = 0.0
    z2: float = 0.0
    cle: str = ""
    auto_type: str = ""
    incoherence_z: float = 0.0   # écart de hauteur entre les deux pans (lignes partagées)

    def to_dict(self) -> dict:
        return {
            "cle": self.cle, "type": self.type, "type_auto": self.auto_type,
            "libelle": TYPES_LIGNES.get(self.type, self.type),
            "p1": [self.p1[0], self.p1[1], self.z1], "p2": [self.p2[0], self.p2[1], self.z2],
            "longueur": self.longueur, "pans": self.pans, "ecart_hauteur": self.incoherence_z,
        }


def _cote_haut(pan: Pan, a: Point2, b: Point2) -> tuple[bool, bool]:
    """Pour le segment (a,b) situé sur le bord d'un pan, indique (horizontale, haute).

    haute = l'intérieur du pan est en contrebas du segment.
    """
    d = pan.plan.descente
    ex, ey = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ex, ey)
    if d is None or L < 1e-9:
        return True, False
    ux, uy = ex / L, ey / L
    horizontale = abs(ux * d[0] + uy * d[1]) < math.sin(math.radians(12))
    nx, ny = -uy, ux
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    eps = min(0.05, L / 4)
    if not point_dans_polygone((m[0] + eps * nx, m[1] + eps * ny), pan.contour):
        nx, ny = -nx, -ny
    haute = (nx * d[0] + ny * d[1]) > 0
    return horizontale, haute


def _intervalle_commun(a1: Point2, a2: Point2, b1: Point2, b2: Point2, tol: float):
    """Portion de [a1,a2] confondue avec [b1,b2] (paramètres t0<t1 sur a), ou None."""
    L = math.dist(a1, a2)
    if L < 1e-9:
        return None
    if distance_point_segment(b1, a1, a2) > tol * 3 and distance_point_segment(b2, a1, a2) > tol * 3:
        return None
    ux, uy = (a2[0] - a1[0]) / L, (a2[1] - a1[1]) / L
    # distance des extrémités de b à la droite de a
    for p in (b1, b2):
        if abs(-(p[0] - a1[0]) * uy + (p[1] - a1[1]) * ux) > tol:
            return None
    tb1 = ((b1[0] - a1[0]) * ux + (b1[1] - a1[1]) * uy) / L
    tb2 = ((b2[0] - a1[0]) * ux + (b2[1] - a1[1]) * uy) / L
    t0, t1 = max(0.0, min(tb1, tb2)), min(1.0, max(tb1, tb2))
    if (t1 - t0) * L < max(tol, 0.05):
        return None
    return t0, t1


def cle_ligne(p1: Point2, p2: Point2) -> str:
    """Clé stable d'une ligne (indépendante du sens), arrondie au centimètre."""
    a = (round(p1[0], 2), round(p1[1], 2))
    b = (round(p2[0], 2), round(p2[1], 2))
    if b < a:
        a, b = b, a
    return f"{a[0]:.2f},{a[1]:.2f};{b[0]:.2f},{b[1]:.2f}"


def _interp(a: Point2, b: Point2, t: float) -> Point2:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def classer_lignes(pans: list[Pan], tol: float = 0.12) -> list[Ligne]:
    """Déduit toutes les lignes de la toiture à partir des contours des pans.

    Une arête commune à deux pans est classée faîtage / arêtier / noue / bris selon
    le sens des pentes ; une arête libre est classée égout / rive / rive haute.
    """
    lignes: list[Ligne] = []
    deja: set[tuple] = set()
    for i, pa in enumerate(pans):
        n = len(pa.contour)
        for k in range(n):
            a1, a2 = pa.contour[k], pa.contour[(k + 1) % n]
            communs: list[tuple[float, float, Pan]] = []
            for j, pb in enumerate(pans):
                if j == i:
                    continue
                m = len(pb.contour)
                for q in range(m):
                    iv = _intervalle_commun(a1, a2, pb.contour[q], pb.contour[(q + 1) % m], tol)
                    if iv:
                        communs.append((iv[0], iv[1], pb))
            communs.sort(key=lambda c: c[0])
            t = 0.0
            morceaux: list[tuple[float, float, Pan | None]] = []
            for t0, t1, pb in communs:
                if t0 > t + 1e-6:
                    morceaux.append((t, t0, None))
                if t1 > t:
                    morceaux.append((max(t, t0), t1, pb))
                    t = t1
            if t < 1 - 1e-6:
                morceaux.append((t, 1.0, None))
            for t0, t1, pb in morceaux:
                p, q = _interp(a1, a2, t0), _interp(a1, a2, t1)
                if math.dist(p, q) < 0.02:
                    continue
                h_a, haut_a = _cote_haut(pa, p, q)
                if pb is None:
                    if pa.plan.pente_deg < 3:
                        typ = RIVE
                    elif h_a:
                        typ = RIVE_HAUTE if haut_a else EGOUT
                    else:
                        typ = RIVE
                    L = longueur_3d(p, q, pa.plan)
                    lg = Ligne(typ, p, q, L, [pa.id], pa.plan.z(*p), pa.plan.z(*q))
                else:
                    paire = tuple(sorted((pa.id, pb.id))) + (cle_ligne(p, q),)
                    if paire in deja:
                        continue
                    deja.add(paire)
                    h_b, haut_b = _cote_haut(pb, p, q)
                    if haut_a and haut_b:
                        typ = FAITAGE if (h_a and h_b) else ARETIER
                    elif not haut_a and not haut_b:
                        typ = NOUE
                    else:
                        typ = BRIS
                    L = 0.5 * (longueur_3d(p, q, pa.plan) + longueur_3d(p, q, pb.plan))
                    za1, za2 = pa.plan.z(*p), pa.plan.z(*q)
                    zb1, zb2 = pb.plan.z(*p), pb.plan.z(*q)
                    lg = Ligne(typ, p, q, L, [pa.id, pb.id], (za1 + zb1) / 2, (za2 + zb2) / 2,
                               incoherence_z=max(abs(za1 - zb1), abs(za2 - zb2)))
                lg.cle = cle_ligne(p, q)
                lg.auto_type = lg.type
                lignes.append(lg)
    return lignes


def recouvrement_polygones(p1: list[Point2], p2: list[Point2], pas: float = 0.05) -> float:
    """Estimation de la surface (plan) commune à deux polygones par échantillonnage."""
    xs = [p[0] for p in p1] + [p[0] for p in p2]
    ys = [p[1] for p in p1] + [p[1] for p in p2]
    x0, x1 = max(min(p[0] for p in p1), min(p[0] for p in p2)), min(max(p[0] for p in p1), max(p[0] for p in p2))
    y0, y1 = max(min(p[1] for p in p1), min(p[1] for p in p2)), min(max(p[1] for p in p1), max(p[1] for p in p2))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    import numpy as np
    del xs, ys
    nx = max(2, int((x1 - x0) / pas))
    ny = max(2, int((y1 - y0) / pas))
    if nx * ny > 400_000:
        f = math.sqrt(nx * ny / 400_000)
        nx, ny = int(nx / f), int(ny / f)
    gx, gy = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny))
    m = _masque_polygone(gx, gy, p1) & _masque_polygone(gx, gy, p2)
    return float(m.mean() * (x1 - x0) * (y1 - y0))


def _masque_polygone(gx, gy, poly):
    import numpy as np
    dedans = np.zeros(gx.shape, dtype=bool)
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cond = (yi > gy) != (yj > gy)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (gy - yi) / (yj - yi) + xi
        dedans ^= cond & (gx < xint)
        j = i
    return dedans
