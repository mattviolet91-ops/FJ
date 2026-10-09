"""Génération de MNS synthétiques de toitures à géométrie connue (tests uniquement)."""
import math

import numpy as np

from mmt.core.segmentation import Grille


def grille_vide(res=0.05, taille=24.0, sol=100.0):
    n = int(taille / res)
    z = np.full((n, n), sol)
    x0, y0 = -taille / 2, taille / 2
    jj, ii = np.meshgrid(np.arange(n), np.arange(n))
    X = x0 + (jj + 0.5) * res
    Y = y0 - (ii + 0.5) * res
    return z, X, Y, x0, y0


def deux_pans(L=10.0, l=8.0, pente_deg=35.0, h_egout=5.0, res=0.05, bruit=0.01, seed=0, cheminee=False):
    """Toit à deux pans : faîtage parallèle à x, longueur L, largeur (en plan) l."""
    z, X, Y, x0, y0 = grille_vide(res)
    t = math.tan(math.radians(pente_deg))
    dans = (np.abs(X) <= L / 2) & (np.abs(Y) <= l / 2)
    toit = 100 + h_egout + (l / 2 - np.abs(Y)) * t
    z = np.where(dans, toit, z)
    if cheminee:
        c = (np.abs(X - 2) <= 0.3) & (np.abs(Y - 1.5) <= 0.3)
        z = np.where(c, toit + 1.0, z)
    z = z + np.random.default_rng(seed).normal(0, bruit, z.shape)
    return Grille(z, res, x0, y0)


def quatre_pans(L=12.0, l=8.0, pente_deg=30.0, h_egout=5.0, res=0.05, bruit=0.01, seed=0):
    """Toit à quatre pans (croupes de même pente)."""
    z, X, Y, x0, y0 = grille_vide(res)
    t = math.tan(math.radians(pente_deg))
    dans = (np.abs(X) <= L / 2) & (np.abs(Y) <= l / 2)
    d = np.minimum(L / 2 - np.abs(X), l / 2 - np.abs(Y))
    z = np.where(dans, 100 + h_egout + d * t, z)
    z = z + np.random.default_rng(seed).normal(0, bruit, z.shape)
    return Grille(z, res, x0, y0)


def surface_quatre_pans(L, l, pente_deg):
    return L * l / math.cos(math.radians(pente_deg))


def en_L(pente_deg=35.0, res=0.05, bruit=0.01, seed=0):
    """Toit en L : deux toits à deux pans de même pente qui se croisent (noues)."""
    z, X, Y, x0, y0 = grille_vide(res)
    t = math.tan(math.radians(pente_deg))
    # aile A : x in [-8, 4], y in [-3, 3], faîtage y=0
    A = (X >= -8) & (X <= 4) & (np.abs(Y) <= 3)
    zA = 105 + (3 - np.abs(Y)) * t
    # aile B : x in [-2, 4], y in [-9, 3] ... faîtage x=1
    B = (np.abs(X - 1) <= 3) & (Y >= -9) & (Y <= 3)
    zB = 105 + (3 - np.abs(X - 1)) * t
    zt = np.where(A & B, np.maximum(zA, zB), np.where(A, zA, zB))
    z = np.where(A | B, zt, z)
    z = z + np.random.default_rng(seed).normal(0, bruit, z.shape)
    return Grille(z, res, x0, y0)
