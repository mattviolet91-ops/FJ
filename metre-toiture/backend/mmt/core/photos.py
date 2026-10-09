"""Analyse des photos de drone : métadonnées, netteté, exposition, doublons, couverture.

Toutes les conclusions sont prudentes : quand une information manque (pas de GPS,
pas d'orientation de nacelle…), le rapport l'indique comme « non évaluable » plutôt
que de présumer d'un résultat.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import ExifTags, Image, ImageOps

DIAG_35MM = 43.2666  # diagonale d'un capteur 24×36 (mm)

_XMP_CLES = {
    "RelativeAltitude": "alt_relative",
    "AbsoluteAltitude": "alt_absolue",
    "GimbalPitchDegree": "nacelle_tangage",
    "GimbalYawDegree": "nacelle_lacet",
    "GimbalRollDegree": "nacelle_roulis",
    "FlightYawDegree": "vol_lacet",
    "FlightPitchDegree": "vol_tangage",
    "RtkFlag": "rtk",
    "CalibratedFocalLength": "focale_calibree_px",
}


def _rationnel(v) -> float | None:
    try:
        if isinstance(v, tuple) and len(v) == 2:
            return float(v[0]) / float(v[1]) if v[1] else None
        return float(v)
    except Exception:
        return None


def _dms(v, ref) -> float | None:
    try:
        d, m, s = (_rationnel(x) for x in v)
        val = d + m / 60 + s / 3600
        if ref in ("S", "W", b"S", b"W"):
            val = -val
        return val
    except Exception:
        return None


def lire_xmp(data: bytes) -> dict:
    out: dict = {}
    debut = data.find(b"<x:xmpmeta")
    if debut < 0:
        return out
    fin = data.find(b"</x:xmpmeta>", debut)
    xmp = data[debut: fin if fin > 0 else debut + 65536].decode("utf-8", errors="ignore")
    for cle, nom in _XMP_CLES.items():
        m = re.search(r"(?:drone-dji|drone|Camera|dji)?:?" + cle + r'\s*=\s*"([^"]+)"', xmp) or \
            re.search(r"<[\w-]+:" + cle + r">([^<]+)<", xmp)
        if m:
            try:
                out[nom] = float(m.group(1).replace("+", ""))
            except ValueError:
                out[nom] = m.group(1)
    return out


def lire_metadonnees(chemin: str | Path) -> dict:
    chemin = Path(chemin)
    meta: dict = {}
    with Image.open(chemin) as im:
        meta["largeur"], meta["hauteur"] = im.size
        meta["format"] = im.format
        exif = im.getexif()
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        ifd = exif.get_ifd(0x8769) if exif else {}
        tags.update({ExifTags.TAGS.get(k, k): v for k, v in ifd.items()})
        gps = exif.get_ifd(0x8825) if exif else {}
        orientation = tags.get("Orientation")
        if orientation in (6, 8):
            meta["largeur"], meta["hauteur"] = meta["hauteur"], meta["largeur"]
    meta["fabricant"] = str(tags.get("Make", "") or "").strip("\x00 ").strip() or None
    meta["modele"] = str(tags.get("Model", "") or "").strip("\x00 ").strip() or None
    meta["focale_mm"] = _rationnel(tags.get("FocalLength"))
    f35 = tags.get("FocalLengthIn35mmFilm")
    meta["focale_35mm"] = float(f35) if f35 else None
    dt = tags.get("DateTimeOriginal") or tags.get("DateTime")
    if dt:
        try:
            meta["date_prise"] = datetime.strptime(str(dt).strip("\x00"), "%Y:%m:%d %H:%M:%S").isoformat()
        except ValueError:
            meta["date_prise"] = None
    meta["exposition_s"] = _rationnel(tags.get("ExposureTime"))
    meta["iso"] = tags.get("ISOSpeedRatings") or tags.get("PhotographicSensitivity")
    if isinstance(meta["iso"], tuple):
        meta["iso"] = meta["iso"][0]
    if gps:
        lat = _dms(gps.get(2), gps.get(1)) if gps.get(2) else None
        lon = _dms(gps.get(4), gps.get(3)) if gps.get(4) else None
        alt = _rationnel(gps.get(6)) if gps.get(6) is not None else None
        if alt is not None and gps.get(5) in (1, b"\x01"):
            alt = -alt
        meta.update({"lat": lat, "lon": lon, "alt_gps": alt})
    with open(chemin, "rb") as f:
        data = f.read(262144)
    meta.update(lire_xmp(data))
    return meta


def analyser_image(chemin: str | Path, largeur_analyse: int = 1200) -> dict:
    """Netteté (variance du laplacien), exposition et empreinte perceptuelle."""
    with Image.open(chemin) as im:
        im = ImageOps.exif_transpose(im)
        g = im.convert("L")
        r = largeur_analyse / max(g.size)
        if r < 1:
            g = g.resize((int(g.size[0] * r), int(g.size[1] * r)), Image.BILINEAR)
        a = np.asarray(g, dtype=np.float32)
        miniature = im.copy()
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    # netteté mesurée sur les zones texturées (les 25 % de blocs les plus contrastés)
    h, w = lap.shape
    b = 32
    blocs = []
    for i in range(0, h - b, b):
        for j in range(0, w - b, b):
            blocs.append(float(lap[i:i + b, j:j + b].var()))
    blocs.sort()
    nettete = float(np.mean(blocs[int(len(blocs) * 0.75):])) if blocs else float(lap.var())
    sur = float(np.mean(a >= 250))
    sous = float(np.mean(a <= 5))
    # dHash 64 bits
    petit = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (petit[:, 1:] > petit[:, :-1]).flatten()
    dh = 0
    for bit in bits:
        dh = (dh << 1) | int(bit)
    return {"nettete": nettete, "luminosite": float(a.mean()), "surexpose": sur, "sousexpose": sous,
            "dhash": f"{dh:016x}", "_miniature": miniature}


def gsd_cm(hauteur_m: float, focale_35mm: float, largeur_px: int, hauteur_px: int) -> float:
    """Taille d'un pixel au sol (cm/px) pour une prise de vue verticale."""
    diag = math.hypot(largeur_px, hauteur_px)
    return 100 * hauteur_m * DIAG_35MM / (focale_35mm * diag)


def _distance_hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _enu(lat0, lon0, lat, lon):
    R = 6378137.0
    x = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R
    return x, y


CATEGORIES = {"verticale": "Verticale (nadir)", "oblique": "Oblique", "horizontale": "Quasi horizontale",
              "inconnue": "Angle inconnu"}
SECTEURS = ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"]


def categorie_angle(tangage: float | None) -> str:
    if tangage is None:
        return "inconnue"
    if tangage <= -75:
        return "verticale"
    if tangage <= -15:
        return "oblique"
    return "horizontale"


def analyser_serie(photos: list[dict], centre: tuple[float, float] | None = None) -> dict:
    """Analyse globale d'une série de photos (dictionnaires issus des fonctions ci-dessus,
    avec la clé « id »). Retourne problèmes, actions et statistiques."""
    pb: list[dict] = []
    stats: dict = {"nombre": len(photos)}
    actives = [p for p in photos if not p.get("exclue")]
    n = len(actives)
    if n == 0:
        return {"stats": stats, "problemes": [{"niveau": "bloquant", "code": "aucune_photo",
                                                "message": "Aucune photo importée.",
                                                "action": "Importez les photos du vol (JPEG d'origine, non retouchées)."}],
                "photos": {}, "verdict": "insuffisant"}
    par_photo: dict = {p["id"]: [] for p in actives}

    # --- nombre
    if n < 5:
        pb.append({"niveau": "bloquant", "code": "trop_peu",
                   "message": f"Seulement {n} photo(s) : une reconstruction 3D en exige bien davantage.",
                   "action": "Pour un pavillon simple, prévoyez plusieurs dizaines de photos (passages verticaux "
                             "+ orbite oblique). Consultez le plan de prise de vue."})
    elif n < 20:
        pb.append({"niveau": "alerte", "code": "peu_photos",
                   "message": f"{n} photos : c'est peu pour reconstruire une toiture complète.",
                   "action": "Ajoutez une orbite de photos obliques tout autour du bâtiment."})

    # --- netteté (relative à la série + seuil absolu prudent)
    net = [p["nettete"] for p in actives if p.get("nettete") is not None]
    if net:
        med = float(np.median(net))
        stats["nettete_mediane"] = med
        floues = []
        for p in actives:
            v = p.get("nettete")
            if v is None:
                continue
            if v < 0.35 * med or v < 15:
                floues.append(p)
                par_photo[p["id"]].append("floue")
        if floues:
            pb.append({"niveau": "alerte" if len(floues) < 0.2 * n else "bloquant", "code": "floues",
                       "message": f"{len(floues)} photo(s) nettement moins nettes que le reste de la série.",
                       "action": "Excluez-les ou refaites-les : stabilisez le drone avant chaque déclenchement, "
                                 "réduisez la vitesse et évitez les vitesses d'obturation lentes.",
                       "photos": [p["id"] for p in floues]})

    # --- exposition
    sur = [p for p in actives if (p.get("surexpose") or 0) > 0.05]
    sous = [p for p in actives if (p.get("sousexpose") or 0) > 0.10 or (p.get("luminosite") or 128) < 40]
    for p in sur:
        par_photo[p["id"]].append("surexposee")
    for p in sous:
        par_photo[p["id"]].append("sombre")
    if sur:
        pb.append({"niveau": "alerte", "code": "surexposees",
                   "message": f"{len(sur)} photo(s) avec des zones « brûlées » (blanc pur).",
                   "action": "Baissez la correction d'exposition (−0,3 à −0,7 IL) : les tuiles claires et le zinc "
                             "saturent facilement au soleil.", "photos": [p["id"] for p in sur]})
    if sous:
        pb.append({"niveau": "alerte", "code": "sombres",
                   "message": f"{len(sous)} photo(s) trop sombres.",
                   "action": "Évitez les contre-jours et les heures de faible lumière ; augmentez l'exposition.",
                   "photos": [p["id"] for p in sous]})

    # --- doublons
    doublons = []
    for i in range(len(actives)):
        for j in range(i + 1, len(actives)):
            a, b = actives[i], actives[j]
            if not a.get("dhash") or not b.get("dhash"):
                continue
            if a.get("sha256") and a.get("sha256") == b.get("sha256"):
                doublons.append((a, b))
                continue
            if _distance_hamming(a["dhash"], b["dhash"]) <= 2:
                if a.get("lat") is not None and b.get("lat") is not None:
                    dx, dy = _enu(a["lat"], a["lon"], b["lat"], b["lon"])
                    dz = (a.get("alt_relative") or 0) - (b.get("alt_relative") or 0)
                    if math.sqrt(dx * dx + dy * dy + dz * dz) > 0.5:
                        continue
                doublons.append((a, b))
    if doublons:
        for _, b in doublons:
            par_photo[b["id"]].append("doublon")
        pb.append({"niveau": "info", "code": "doublons",
                   "message": f"{len(doublons)} doublon(s) probable(s) (même position, même cadrage).",
                   "action": "Les doublons n'apportent rien et ralentissent le calcul : excluez-les.",
                   "photos": [b["id"] for _, b in doublons]})

    # --- métadonnées / GPS
    avec_gps = [p for p in actives if p.get("lat") is not None and p.get("lon") is not None]
    stats["avec_gps"] = len(avec_gps)
    if not avec_gps:
        pb.append({"niveau": "bloquant", "code": "sans_gps",
                   "message": "Aucune position GPS dans les photos : le modèle 3D n'aura pas d'échelle métrique.",
                   "action": "Activez l'enregistrement de la position dans l'application du drone, ou prévoyez au "
                             "moins une dimension de référence mesurée au mètre (ex. longueur d'égout)."})
    elif len(avec_gps) < n:
        pb.append({"niveau": "alerte", "code": "gps_partiel",
                   "message": f"{n - len(avec_gps)} photo(s) sans position GPS.",
                   "action": "Vérifiez qu'elles proviennent bien du même vol ; sinon excluez-les."})
    modeles = {(p.get("fabricant"), p.get("modele"), p.get("largeur"), p.get("hauteur")) for p in actives}
    stats["cameras"] = [{"fabricant": m[0], "modele": m[1], "largeur": m[2], "hauteur": m[3]} for m in modeles]
    if len(modeles) > 1:
        pb.append({"niveau": "info", "code": "cameras_multiples",
                   "message": f"{len(modeles)} configurations d'appareil différentes détectées.",
                   "action": "Le mélange de résolutions ou d'appareils est possible mais peut dégrader le calibrage."})
    if any(p.get("rtk") for p in actives):
        stats["rtk"] = True

    # --- angles
    cats = {c: 0 for c in CATEGORIES}
    for p in actives:
        cats[categorie_angle(p.get("nacelle_tangage"))] += 1
    stats["angles"] = cats
    if cats["inconnue"] == n:
        pb.append({"niveau": "info", "code": "angles_inconnus",
                   "message": "Orientation de la nacelle absente des métadonnées : diversité des angles non évaluable.",
                   "action": "Assurez-vous d'avoir à la fois des vues verticales et des vues obliques (≈ −45°)."})
    else:
        if cats["oblique"] < max(8, 0.25 * n):
            pb.append({"niveau": "alerte", "code": "peu_obliques",
                       "message": f"Seulement {cats['oblique']} vue(s) oblique(s).",
                       "action": "Ajoutez une orbite complète autour du bâtiment, nacelle vers −30° à −50° : les "
                                 "obliques sont indispensables pour les pans raides, les rives et les noues."})
        if cats["verticale"] == 0:
            pb.append({"niveau": "info", "code": "pas_de_nadir",
                       "message": "Aucune vue verticale.",
                       "action": "Quelques passages à la verticale améliorent l'orthophoto et le contrôle des contours."})
        if cats["horizontale"] > 0.3 * n:
            pb.append({"niveau": "info", "code": "horizontales",
                       "message": f"{cats['horizontale']} photos quasi horizontales.",
                       "action": "Les vues trop rasantes voient peu la couverture ; inclinez davantage la nacelle."})

    # --- couverture autour du bâtiment
    couverture = None
    if len(avec_gps) >= 4:
        lat0 = sum(p["lat"] for p in avec_gps) / len(avec_gps)
        lon0 = sum(p["lon"] for p in avec_gps) / len(avec_gps)
        pos = {p["id"]: _enu(lat0, lon0, p["lat"], p["lon"]) for p in avec_gps}
        cx, cy = centre if centre else _centre_vise(avec_gps, pos)
        obl = [p for p in avec_gps if categorie_angle(p.get("nacelle_tangage")) in ("oblique", "horizontale")]
        if len(obl) >= 4:
            secteurs = [0] * 8
            for p in obl:
                x, y = pos[p["id"]]
                az = math.degrees(math.atan2(x - cx, y - cy)) % 360
                secteurs[int(((az + 22.5) % 360) // 45)] += 1
            couverture = {SECTEURS[i]: secteurs[i] for i in range(8)}
            vides = [SECTEURS[i] for i in range(8) if secteurs[i] == 0]
            faibles = [SECTEURS[i] for i in range(8) if 0 < secteurs[i] < 2]
            if vides:
                pb.append({"niveau": "alerte", "code": "secteurs_vides",
                           "message": "Côté(s) " + ", ".join(vides) + " du bâtiment sans photo oblique.",
                           "action": "Le versant correspondant risque d'être mal reconstruit. Ajoutez plusieurs photos "
                                     "obliques depuis ces positions, en variant l'altitude."})
            if faibles:
                pb.append({"niveau": "info", "code": "secteurs_faibles",
                           "message": "Côté(s) " + ", ".join(faibles) + " peu photographié(s) (1 seule vue oblique).",
                           "action": "Ajoutez au moins 2 à 3 vues supplémentaires de ces côtés."})
            # pas angulaire d'orbite
            angs = sorted(math.degrees(math.atan2(pos[p["id"]][0] - cx, pos[p["id"]][1] - cy)) % 360 for p in obl)
            ecarts = [(angs[(i + 1) % len(angs)] - angs[i]) % 360 for i in range(len(angs))]
            stats["ecart_angulaire_max_deg"] = max(ecarts) if ecarts else None
        else:
            stats["couverture"] = "non évaluable (moins de 4 vues obliques géolocalisées)"
        # recouvrement des verticales
        rec = _recouvrement_verticales(avec_gps, pos)
        if rec is not None:
            stats["recouvrement_vertical_min"] = rec
            if rec < 0.6:
                pb.append({"niveau": "alerte", "code": "recouvrement",
                           "message": f"Recouvrement estimé entre vues verticales successives : {rec * 100:.0f} % "
                                      "au plus faible (estimation à partir du GPS et de l'altitude).",
                           "action": "Visez environ 75 à 80 % : rapprochez les photos ou montez légèrement."})
        else:
            stats["recouvrement"] = ("non évaluable (altitude relative, focale équivalente ou vues verticales "
                                     "successives manquantes)")
        stats["emprise_vol_m"] = _etendue(pos.values())
    stats["couverture_secteurs"] = couverture
    # GSD
    gsds = []
    for p in actives:
        if p.get("alt_relative") and p.get("focale_35mm") and p.get("largeur"):
            gsds.append(gsd_cm(p["alt_relative"], p["focale_35mm"], p["largeur"], p["hauteur"]))
    if gsds:
        stats["gsd_sol_cm"] = {"min": min(gsds), "max": max(gsds), "median": float(np.median(gsds))}

    niveaux = [x["niveau"] for x in pb]
    verdict = "insuffisant" if "bloquant" in niveaux else ("a_ameliorer" if "alerte" in niveaux else "correct")
    return {"stats": stats, "problemes": pb, "photos": par_photo, "verdict": verdict}


def _centre_vise(photos, pos) -> tuple[float, float]:
    """Point visé par les obliques (moindres carrés sur les rayons de visée en plan)."""
    A = np.zeros((2, 2))
    b = np.zeros(2)
    m = 0
    for p in photos:
        yaw = p.get("nacelle_lacet")
        if yaw is None or categorie_angle(p.get("nacelle_tangage")) != "oblique":
            continue
        d = np.array([math.sin(math.radians(yaw)), math.cos(math.radians(yaw))])
        P = np.eye(2) - np.outer(d, d)
        o = np.array(pos[p["id"]])
        A += P
        b += P @ o
        m += 1
    if m >= 4 and abs(np.linalg.det(A)) > 1e-6:
        c = np.linalg.solve(A, b)
        return float(c[0]), float(c[1])
    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _recouvrement_verticales(photos, pos) -> float | None:
    vert = [p for p in photos if categorie_angle(p.get("nacelle_tangage")) == "verticale"
            and p.get("alt_relative") and p.get("focale_35mm") and p.get("date_prise")]
    if len(vert) < 3:
        return None
    vert.sort(key=lambda p: p["date_prise"])
    valeurs = []
    for a, b in zip(vert, vert[1:]):
        d = math.dist(pos[a["id"]], pos[b["id"]])
        if d < 0.3:
            continue
        g = gsd_cm(a["alt_relative"], a["focale_35mm"], a["largeur"], a["hauteur"]) / 100
        # empreinte la plus courte (cas défavorable)
        emprise = g * min(a["largeur"], a["hauteur"])
        if d > 3 * emprise:   # changement de ligne de vol, ignoré
            continue
        valeurs.append(max(0.0, 1 - d / emprise))
    return min(valeurs) if valeurs else None


def _etendue(points) -> dict:
    pts = list(points)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {"est_ouest": max(xs) - min(xs), "nord_sud": max(ys) - min(ys)}
