"""Exploitation des résultats de reconstruction (MNS, orthophoto, nuage de points).

Toutes les coordonnées exposées à l'application sont dans un repère local métrique :
x = Est − E0, y = Nord − N0 (projection cartographique du modèle, en général UTM), z = altitude.
"""
from __future__ import annotations

import io
import json
import math
import shutil
import zipfile
from pathlib import Path

import numpy as np

from ..core.segmentation import Grille

FICHIERS = {
    "dsm": "odm_dem/dsm.tif",
    "dtm": "odm_dem/dtm.tif",
    "ortho": "odm_orthophoto/odm_orthophoto.tif",
    "nuage": "odm_georeferencing/odm_georeferenced_model.laz",
    "rapport": "odm_report/report.pdf",
    "journal": "task_output.txt",
}
MAX_POINTS_STOCKES = 6_000_000


def extraire(zip_path: Path, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    trouves = {}
    with zipfile.ZipFile(zip_path) as z:
        noms = set(z.namelist())
        for cle, chemin in FICHIERS.items():
            if chemin in noms:
                cible = dest / Path(chemin).name
                with z.open(chemin) as src, open(cible, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                trouves[cle] = cible.name
    return trouves


def preparer(dossier: Path, fichiers: dict) -> dict:
    """Construit info.json (repère local, emprises) et le cache du nuage de points."""
    import rasterio

    if "dsm" not in fichiers:
        raise ValueError("Le calcul n'a pas produit de modèle numérique de surface (MNS).")
    with rasterio.open(dossier / fichiers["dsm"]) as ds:
        b = ds.bounds
        crs = ds.crs
        res = float(abs(ds.res[0]))
        e0 = round((b.left + b.right) / 2)
        n0 = round((b.bottom + b.top) / 2)
        epsg = crs.to_epsg() if crs else None
        info = {
            "type": "odm",
            "epsg": epsg,
            "crs_wkt": crs.to_wkt() if crs else None,
            "origine": [e0, n0],
            "bornes": [b.left - e0, b.bottom - n0, b.right - e0, b.top - n0],
            "res_mns": res,
            "fichiers": fichiers,
        }
        # altitude de référence (sol) approximative
        dec = ds.read(1, out_shape=(max(1, ds.height // 16), max(1, ds.width // 16)), masked=True)
        if dec.count():
            info["z_min"] = float(np.percentile(dec.compressed(), 2))
            info["z_max"] = float(np.percentile(dec.compressed(), 99.5))
    if "ortho" in fichiers:
        with rasterio.open(dossier / fichiers["ortho"]) as o:
            info["res_ortho"] = float(abs(o.res[0]))
            ob = o.bounds
            info["bornes_ortho"] = [ob.left - e0, ob.bottom - n0, ob.right - e0, ob.top - n0]
    if "nuage" in fichiers:
        try:
            info["nb_points"] = _cacher_nuage(dossier / fichiers["nuage"], dossier, e0, n0)
        except Exception as e:  # le nuage n'est pas indispensable au métré
            info["erreur_nuage"] = str(e)
    (dossier / "info.json").write_text(json.dumps(info, indent=1))
    return info


def _cacher_nuage(laz: Path, dossier: Path, e0: float, n0: float) -> int:
    import laspy

    with laspy.open(laz) as f:
        n = f.header.point_count
        pas = max(1, math.ceil(n / MAX_POINTS_STOCKES))
        xyz, rgb = [], []
        for bloc in f.chunk_iterator(2_000_000):
            sel = slice(None, None, pas)
            x = np.asarray(bloc.x)[sel] - e0
            y = np.asarray(bloc.y)[sel] - n0
            z = np.asarray(bloc.z)[sel]
            xyz.append(np.column_stack([x, y, z]).astype(np.float32))
            try:
                c = np.column_stack([bloc.red[sel], bloc.green[sel], bloc.blue[sel]]).astype(np.float32)
                if c.max() > 255:
                    c = c / 256.0
                rgb.append(c.astype(np.uint8))
            except Exception:
                rgb.append(np.full((len(x), 3), 180, np.uint8))
    xyz = np.concatenate(xyz)
    rgb = np.concatenate(rgb)
    np.save(dossier / "nuage_xyz.npy", xyz)
    np.save(dossier / "nuage_rgb.npy", rgb)
    return int(len(xyz))


def lire_info(dossier: Path) -> dict:
    return json.loads((dossier / "info.json").read_text())


def _fenetre(ds, info, bbox):
    from rasterio.windows import from_bounds
    e0, n0 = info["origine"]
    x0, y0, x1, y1 = bbox
    w = from_bounds(x0 + e0, y0 + n0, x1 + e0, y1 + n0, transform=ds.transform)
    return w.round_offsets().round_lengths()


def lire_mns(dossier: Path, bbox: tuple[float, float, float, float], res_max: float | None = None) -> Grille:
    """MNS recadré sur bbox (repère local), rééchantillonné si res_max est plus grossier."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import Window

    info = lire_info(dossier)
    with rasterio.open(dossier / info["fichiers"]["dsm"]) as ds:
        w = _fenetre(ds, info, bbox)
        w = w.intersection(Window(0, 0, ds.width, ds.height))
        res = float(abs(ds.res[0]))
        h, wd = int(w.height), int(w.width)
        if h < 4 or wd < 4:
            raise ValueError("La zone demandée est en dehors du modèle 3D.")
        facteur = 1.0
        if res_max and res_max > res:
            facteur = res_max / res
        oh, ow = max(4, int(h / facteur)), max(4, int(wd / facteur))
        a = ds.read(1, window=w, out_shape=(oh, ow), masked=True,
                    resampling=Resampling.average if facteur > 1 else Resampling.nearest)
        tr = ds.window_transform(w)
        e0, n0 = info["origine"]
        z = a.filled(np.nan).astype(float)
        nodata = ds.nodata
        if nodata is not None:
            z[z == nodata] = np.nan
        z[z < -1000] = np.nan
        res_eff = res * wd / ow
        return Grille(z=z, res=res_eff, x0=tr.c - e0, y0=tr.f - n0, valide=np.isfinite(z))


def image_recadree(dossier: Path, quoi: str, bbox, max_px: int = 2048) -> tuple[bytes, list[float], str]:
    """Image JPEG (orthophoto) ou PNG (ombrage du MNS) recadrée sur bbox."""
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.windows import Window

    info = lire_info(dossier)
    e0, n0 = info["origine"]
    if quoi == "ortho" and "ortho" in info["fichiers"]:
        with rasterio.open(dossier / info["fichiers"]["ortho"]) as ds:
            w = _fenetre(ds, info, bbox).intersection(Window(0, 0, ds.width, ds.height))
            f = max(1.0, max(w.width, w.height) / max_px)
            oh, ow = max(1, int(w.height / f)), max(1, int(w.width / f))
            bandes = min(ds.count, 4)
            a = ds.read(list(range(1, bandes + 1)), window=w, out_shape=(bandes, oh, ow),
                        resampling=Resampling.average)
            tr = ds.window_transform(w)
            bornes = [tr.c - e0, tr.f - n0 - w.height * abs(tr.e), tr.c - e0 + w.width * tr.a, tr.f - n0]
        rgb = np.moveaxis(a[:3], 0, -1)
        if rgb.dtype != np.uint8:
            rgb = np.clip(rgb / max(1, np.percentile(rgb, 99.5)) * 255, 0, 255).astype(np.uint8)
        if bandes == 4:
            alpha = a[3] == 0
            rgb = rgb.copy()
            rgb[alpha] = (40, 44, 52)
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, "JPEG", quality=85)
        return buf.getvalue(), bornes, "image/jpeg"
    # ombrage du MNS
    g = lire_mns(dossier, bbox, res_max=max(bbox[2] - bbox[0], bbox[3] - bbox[1]) / max_px)
    z = g.z.copy()
    zf = np.where(np.isfinite(z), z, np.nanmin(z) if np.isfinite(z).any() else 0)
    gy, gx = np.gradient(zf, g.res)
    pente = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(315), math.radians(45)
    omb = np.sin(alt) * np.cos(pente) + np.cos(alt) * np.sin(pente) * np.cos(az - aspect)
    zn = (zf - np.nanpercentile(zf, 2)) / max(1e-6, np.nanpercentile(zf, 98) - np.nanpercentile(zf, 2))
    zn = np.clip(zn, 0, 1)
    base = np.stack([0.17 + 0.6 * zn, 0.67 * zn + 0.2, 0.89 - 0.4 * zn], -1)
    img = np.clip(base * (0.35 + 0.65 * np.clip(omb, 0, 1))[..., None] * 255, 0, 255).astype(np.uint8)
    img[~np.isfinite(z)] = (30, 30, 30)
    buf = io.BytesIO()
    from PIL import Image as _I
    _I.fromarray(img).save(buf, "PNG")
    H, W = z.shape
    return buf.getvalue(), [g.x0, g.y0 - H * g.res, g.x0 + W * g.res, g.y0], "image/png"


def nuage_recadre(dossier: Path, bbox, max_points: int = 400_000) -> bytes:
    """Nuage de points binaire : en-tête uint32 n, puis n×3 float32 (xyz), puis n×3 uint8 (rgb)."""
    xyz = np.load(dossier / "nuage_xyz.npy", mmap_mode="r")
    rgb = np.load(dossier / "nuage_rgb.npy", mmap_mode="r")
    x0, y0, x1, y1 = bbox
    m = (xyz[:, 0] >= x0) & (xyz[:, 0] <= x1) & (xyz[:, 1] >= y0) & (xyz[:, 1] <= y1)
    idx = np.nonzero(m)[0]
    if len(idx) > max_points:
        idx = idx[:: math.ceil(len(idx) / max_points)]
    p = np.ascontiguousarray(xyz[idx], dtype=np.float32)
    c = np.ascontiguousarray(rgb[idx], dtype=np.uint8)
    return np.uint32(len(idx)).tobytes() + p.tobytes() + c.tobytes()


def altitude(dossier: Path, x: float, y: float) -> float | None:
    import rasterio
    info = lire_info(dossier)
    e0, n0 = info["origine"]
    with rasterio.open(dossier / info["fichiers"]["dsm"]) as ds:
        v = next(ds.sample([(x + e0, y + n0)], masked=True))[0]
        return None if np.ma.is_masked(v) else float(v)


def vers_wgs84(info: dict, pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    from rasterio.crs import CRS
    from rasterio.warp import transform

    e0, n0 = info["origine"]
    src = CRS.from_epsg(info["epsg"]) if info.get("epsg") else CRS.from_wkt(info["crs_wkt"])
    xs = [p[0] + e0 for p in pts]
    ys = [p[1] + n0 for p in pts]
    lon, lat = transform(src, "EPSG:4326", xs, ys)
    return list(zip(lon, lat))


def depuis_wgs84(info: dict, lon: float, lat: float) -> tuple[float, float]:
    from rasterio.crs import CRS
    from rasterio.warp import transform

    e0, n0 = info["origine"]
    dst = CRS.from_epsg(info["epsg"]) if info.get("epsg") else CRS.from_wkt(info["crs_wkt"])
    xs, ys = transform("EPSG:4326", dst, [lon], [lat])
    return xs[0] - e0, ys[0] - n0
