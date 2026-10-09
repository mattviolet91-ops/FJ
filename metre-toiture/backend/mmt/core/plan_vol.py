"""Assistant de préparation de chantier : plan de prise de vue personnalisé.

Les recommandations sont calculées à partir de la géométrie (taille du pixel au sol,
emprise des photos, recouvrement visé) et non tirées de règles universelles.
Les caractéristiques des drones sont indicatives : elles doivent être vérifiées sur la
fiche technique du constructeur (et l'utilisateur peut saisir les siennes).
"""
from __future__ import annotations

import math

from .metre import nfr
from .photos import DIAG_35MM

# Caractéristiques indicatives (photo standard 4:3). obturateur : « meca » ou « roulant »
DRONES = {
    "dji_mini_2": {"nom": "DJI Mini 2 / Mini 2 SE", "focale_35mm": 24, "largeur_px": 4000, "hauteur_px": 3000,
                    "obturateur": "roulant", "autonomie_min": 31},
    "dji_mini_3": {"nom": "DJI Mini 3 / Mini 3 Pro (12 MP)", "focale_35mm": 24, "largeur_px": 4032,
                    "hauteur_px": 3024, "obturateur": "roulant", "autonomie_min": 34},
    "dji_mini_4_pro": {"nom": "DJI Mini 4 Pro (12 MP)", "focale_35mm": 24, "largeur_px": 4032,
                        "hauteur_px": 3024, "obturateur": "roulant", "autonomie_min": 34},
    "dji_air_2s": {"nom": "DJI Air 2S", "focale_35mm": 22, "largeur_px": 5472, "hauteur_px": 3648,
                    "obturateur": "roulant", "autonomie_min": 31},
    "dji_air_3": {"nom": "DJI Air 3 (grand-angle, 12 MP)", "focale_35mm": 24, "largeur_px": 4032,
                   "hauteur_px": 3024, "obturateur": "roulant", "autonomie_min": 46},
    "dji_mavic_3": {"nom": "DJI Mavic 3 / 3 Classic (Hasselblad)", "focale_35mm": 24, "largeur_px": 5280,
                     "hauteur_px": 3956, "obturateur": "roulant", "autonomie_min": 46},
    "dji_mavic_3e": {"nom": "DJI Mavic 3 Enterprise", "focale_35mm": 24, "largeur_px": 5280, "hauteur_px": 3956,
                      "obturateur": "meca", "autonomie_min": 45},
    "dji_phantom_4_pro": {"nom": "DJI Phantom 4 Pro / Pro V2.0", "focale_35mm": 24, "largeur_px": 5472,
                           "hauteur_px": 3648, "obturateur": "meca", "autonomie_min": 30},
}

PRECISIONS = {
    "estimation": {"libelle": "Estimation rapide (avant-métré)", "gsd_cm": 2.0, "recouvrement": 0.70,
                   "pas_orbite_deg": 15},
    "devis": {"libelle": "Devis (recommandé)", "gsd_cm": 1.2, "recouvrement": 0.78, "pas_orbite_deg": 10},
    "precis": {"libelle": "Précis (grands toits, complexes)", "gsd_cm": 0.8, "recouvrement": 0.80,
               "pas_orbite_deg": 8},
}

TYPES_TOITURE = {
    "deux_pans": "Deux pans",
    "quatre_pans": "Quatre pans / croupes",
    "appentis": "Appentis (un pan)",
    "complexe": "Multi-pans / complexe (noues, lucarnes)",
    "mansarde": "Mansarde",
    "plat": "Toit plat / terrasse",
}


def camera(params: dict) -> dict:
    """Caméra à partir d'un modèle connu ou de valeurs saisies."""
    cle = params.get("drone")
    base = dict(DRONES.get(cle, {})) if cle in DRONES else {
        "nom": params.get("drone_nom") or "Drone non référencé",
        "focale_35mm": None, "largeur_px": None, "hauteur_px": None, "obturateur": None, "autonomie_min": None}
    for k in ("focale_35mm", "largeur_px", "hauteur_px", "autonomie_min"):
        if params.get(k):
            base[k] = float(params[k]) if k != "largeur_px" and k != "hauteur_px" else int(params[k])
    base["connue"] = bool(base.get("focale_35mm") and base.get("largeur_px") and base.get("hauteur_px"))
    return base


def generer_plan(params: dict) -> dict:
    """params : type_toiture, longueur, largeur, hauteur_faitage, complexite (simple|moyenne|complexe),
    drone / focale_35mm / largeur_px / hauteur_px, precision, vent (faible|moyen|fort),
    lumiere (soleil|nuageux|variable), obstacles (liste), mitoyen (bool)."""
    L = float(params.get("longueur") or 12)
    l = float(params.get("largeur") or 9)
    h = float(params.get("hauteur_faitage") or 8)
    complexite = params.get("complexite") or "simple"
    prec = PRECISIONS.get(params.get("precision") or "devis", PRECISIONS["devis"])
    cam = camera(params)
    obstacles = params.get("obstacles") or []
    etapes: list[dict] = []
    alertes: list[str] = []

    hauteur_securite = h + (5 if "arbres" not in obstacles else 8)
    if cam["connue"]:
        diag = math.hypot(cam["largeur_px"], cam["hauteur_px"])
        # hauteur au-dessus du toit pour le GSD visé
        h_toit = prec["gsd_cm"] / 100 * cam["focale_35mm"] * diag / DIAG_35MM
        h_sol = h + h_toit
        if h_sol < hauteur_securite:
            h_sol = hauteur_securite
            h_toit = h_sol - h
        if h_sol > 120:
            alertes.append("La hauteur calculée dépasse 120 m : la précision visée n'est pas atteignable "
                           "avec cette caméra dans le cadre réglementaire courant.")
            h_sol = 120
            h_toit = h_sol - h
        gsd_toit = 100 * h_toit * DIAG_35MM / (cam["focale_35mm"] * diag)
        emprise_l = gsd_toit / 100 * cam["largeur_px"]
        emprise_h = gsd_toit / 100 * cam["hauteur_px"]
        rec = prec["recouvrement"]
        pas_photo = emprise_h * (1 - rec)
        pas_ligne = emprise_l * (1 - min(rec, 0.70))
        marge = max(5.0, 0.3 * emprise_h)
        zone_l, zone_w = L + 2 * marge, l + 2 * marge
        nb_lignes = max(2, math.ceil(zone_w / pas_ligne) + 1)
        photos_ligne = max(3, math.ceil(zone_l / pas_photo) + 1)
        nb_nadir = nb_lignes * photos_ligne
    else:
        h_sol = h_toit = gsd_toit = emprise_l = emprise_h = pas_photo = pas_ligne = None
        nb_lignes = photos_ligne = None
        nb_nadir = None
        alertes.append("Caméra inconnue : renseignez la focale équivalente 24×36 et la résolution (visibles dans les "
                       "propriétés d'une photo) pour obtenir des hauteurs et espacements calculés.")

    # orbite oblique : nacelle à -45°, viser le centre du toit
    rayon_bat = math.hypot(L, l) / 2
    pas_orb = prec["pas_orbite_deg"]
    if complexite == "complexe":
        pas_orb = min(pas_orb, 8)
    nb_orbite = math.ceil(360 / pas_orb)
    orbites = []
    h_orbite = max(hauteur_securite, h + (h_toit if h_toit else 15) * 0.8)
    dist_horiz = max(rayon_bat + 3, (h_orbite - h * 0.75) / math.tan(math.radians(45)))
    orbites.append({"nom": "Orbite principale", "hauteur_sol_m": round(h_orbite), "rayon_m": round(dist_horiz),
                    "inclinaison_nacelle_deg": -45, "nb_photos": nb_orbite, "pas_deg": pas_orb})
    if complexite in ("moyenne", "complexe") or params.get("type_toiture") in ("complexe", "mansarde"):
        h2 = max(hauteur_securite, h + 6)
        d2 = max(rayon_bat + 2, (h2 - h * 0.75) / math.tan(math.radians(30)))
        orbites.append({"nom": "Orbite basse (rives, noues, brisis)", "hauteur_sol_m": round(h2),
                        "rayon_m": round(d2), "inclinaison_nacelle_deg": -30,
                        "nb_photos": math.ceil(360 / (pas_orb + 2)), "pas_deg": pas_orb + 2})
    nb_details = {"simple": 4, "moyenne": 10, "complexe": 20}.get(complexite, 8)
    total = (nb_nadir or 0) + sum(o["nb_photos"] for o in orbites) + nb_details

    # --- étapes
    etapes.append({"titre": "Avant de partir", "points": [
        "Vérifiez la réglementation applicable au lieu de vol (carte des zones restreintes, vol en agglomération, "
        "catégorie d'exploitation, assurance) et l'accord du propriétaire.",
        "Chargez toutes les batteries, formatez la carte mémoire, nettoyez l'objectif.",
        "Réglez l'appareil : format JPEG d'origine, horodatage et géolocalisation activés, "
        "ratio 4:3, mise au point automatique.",
        "Consultez la météo : vent, pluie (toiture humide = reflets), position du soleil.",
    ]})
    etapes.append({"titre": "Sur place, avant le décollage", "points": [
        "Faites le tour du bâtiment à pied : repérez arbres, câbles, antennes, mitoyennetés.",
        "Mesurez au mètre au moins UNE dimension de référence facile à retrouver sur les photos "
        "(longueur d'égout, largeur de pignon, longueur de gouttière) — elle servira à contrôler l'échelle.",
        f"Choisissez un point de décollage dégagé, à plus de {max(10, round(rayon_bat))} m du bâtiment si possible.",
    ]})
    if nb_nadir:
        etapes.append({"titre": "Passages verticaux (nacelle à −90°)", "points": [
            f"Hauteur de vol : environ {h_sol:.0f} m au-dessus du point de décollage "
            f"(≈ {h_toit:.0f} m au-dessus du faîtage) pour ≈ {nfr(gsd_toit)} cm/pixel sur le toit.",
            f"{nb_lignes} lignes parallèles au faîtage, espacées d'environ {nfr(pas_ligne)} m.",
            f"Une photo tous les {nfr(pas_photo)} m environ ({photos_ligne} par ligne), soit ≈ {nb_nadir} photos.",
            "Débordez d'environ 5 m autour du bâtiment de chaque côté.",
            "Une application de vol automatique (quadrillage) est idéale ; en manuel, utilisez le déclenchement "
            "par intervalle et une vitesse constante et lente.",
        ]})
    for o in orbites:
        etapes.append({"titre": o["nom"] + f" (nacelle à {o['inclinaison_nacelle_deg']}°)", "points": [
            f"Hauteur ≈ {o['hauteur_sol_m']} m, à ≈ {o['rayon_m']} m du centre du bâtiment.",
            f"Une photo tous les {o['pas_deg']}° environ, soit ≈ {o['nb_photos']} photos sur le tour complet.",
            "Gardez tout le toit dans le cadre, centré ; ne coupez pas les égouts.",
            "Faites le tour COMPLET, même côté mitoyen ou arbres (montez si nécessaire).",
        ]})
    etapes.append({"titre": "Photos de détail", "points": [
        f"≈ {nb_details} photos rapprochées des points délicats : noues, cheminées, fenêtres de toit, "
        "raccords contre murs, rives et égouts masqués.",
        "Prenez chaque détail depuis 2 à 3 positions différentes (pas seulement en zoomant).",
    ]})
    etapes.append({"titre": "Contrôle avant de quitter le chantier", "points": [
        "Agrandissez quelques photos au hasard : les tuiles doivent être nettes, sans flou de bougé.",
        "Vérifiez que chaque versant apparaît sur de nombreuses photos, sous plusieurs angles.",
        "Importez les photos dans l'application dès que possible : l'analyse de qualité signale les manques "
        "pendant que vous êtes encore sur place.",
    ]})

    conseils = []
    if cam.get("obturateur") == "roulant":
        conseils.append("Obturateur électronique (roulant) : marquez un arrêt ou ralentissez fortement à chaque "
                        "photo pour éviter les déformations, surtout en vol automatique.")
    vent = params.get("vent")
    if vent == "fort":
        alertes.append("Vent fort annoncé : risque de photos floues et de vol instable. Reportez si possible.")
    elif vent == "moyen":
        conseils.append("Vent modéré : réduisez la vitesse, augmentez la vitesse d'obturation (≤ 1/500 s).")
    lum = params.get("lumiere")
    if lum == "soleil":
        conseils.append("Plein soleil : ombres portées marquées. Évitez le soleil rasant ; baissez l'exposition "
                        "si la couverture est claire ou en zinc.")
    elif lum == "variable":
        conseils.append("Lumière changeante : gardez une exposition aussi constante que possible pendant le vol.")
    if "arbres" in obstacles:
        conseils.append("Arbres proches : les zones cachées seront mal reconstruites. Multipliez les obliques "
                        "depuis les côtés dégagés et prévoyez une mesure manuelle des parties masquées.")
    if "cables" in obstacles:
        alertes.append("Câbles ou lignes à proximité : invisibles sur l'écran du drone, gardez une marge importante.")
    if params.get("mitoyen"):
        conseils.append("Bâtiment mitoyen : le versant contre le voisin doit être photographié depuis plus haut, "
                        "et la limite de propriété repérée sur place.")
    if params.get("type_toiture") == "plat":
        conseils.append("Toit plat : la hauteur des acrotères et les relevés ne sont pas mesurables précisément "
                        "par photo ; contrôlez-les sur place.")
    batteries = None
    if cam.get("autonomie_min"):
        # rythme indicatif : ~ 4 s par photo + transitions, autonomie utile 60 %
        duree_min = total * 4 / 60 + 4 * len(orbites) + 3
        batteries = max(1, math.ceil(duree_min / (cam["autonomie_min"] * 0.6)))
    return {
        "camera": cam,
        "precision": prec,
        "hauteur_vol_sol_m": h_sol, "hauteur_au_dessus_toit_m": h_toit, "gsd_toit_cm": gsd_toit,
        "emprise_photo_m": [emprise_l, emprise_h] if emprise_l else None,
        "passages_verticaux": {"lignes": nb_lignes, "photos_par_ligne": photos_ligne, "total": nb_nadir,
                                "espacement_lignes_m": pas_ligne, "espacement_photos_m": pas_photo} if nb_nadir else None,
        "orbites": orbites,
        "photos_detail": nb_details,
        "total_photos": total,
        "batteries_estimees": batteries,
        "etapes": etapes,
        "conseils": conseils,
        "alertes": alertes,
        "avertissement": "Recommandations calculées à titre indicatif : adaptez-les au terrain, à la réglementation "
                         "et aux capacités réelles de votre drone.",
    }
