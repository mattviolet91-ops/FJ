"""File de traitements asynchrones, persistée en base (reprise automatique après redémarrage).

* reconstruction : envoi des photos à NodeODM, suivi, téléchargement, préparation du modèle,
  puis détection automatique des pans ;
* detection : segmentation des pans sur le MNS autour d'un point / d'une zone.
"""
from __future__ import annotations

import logging
import math
import shutil
import statistics
import threading
import time
import traceback
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import config
from ..core import geometry as geo
from ..core import metre as metre_core
from ..core.segmentation import Parametres, segmenter
from ..db import Chantier, Parametre, Photo, SessionLocal, Traitement, VersionMetre, journaliser, maintenant
from . import modele as mod
from .nodeodm import CANCELED, COMPLETED, FAILED, LIBELLES, PRESETS, SORTIES, ClientNodeODM, ErreurNodeODM

log = logging.getLogger("mmt.traitements")
ACTIFS = ("en_attente", "envoi", "en_cours", "telechargement")
SECONDES_PAR_IMAGE_DEFAUT = 32.0  # mesuré : 87 photos 12 MP, 4 cœurs ; recalé ensuite par l'historique
LOT_ENVOI = 10


def client_odm(db: Session) -> ClientNodeODM:
    p = db.get(Parametre, "calcul")
    v = p.valeur if p and isinstance(p.valeur, dict) else {}
    return ClientNodeODM(v.get("nodeodm_url") or config.nodeodm_url, v.get("nodeodm_token") or config.nodeodm_token)


def dossier_modele(chantier_id: int) -> Path:
    return config.modeles_dir / str(chantier_id)


def estimer_duree(db: Session, nb_images: int, preset: str) -> dict:
    """Estimation du temps de calcul, recalée sur l'historique réel de ce serveur."""
    f = PRESETS.get(preset, PRESETS["devis"])["facteur_temps"]
    hist = []
    for t in db.scalars(select(Traitement).where(Traitement.type == "reconstruction",
                                                 Traitement.statut == "termine")).all():
        if t.debut and t.fin and t.nb_images and t.resultats and t.resultats.get("duree_calcul_s"):
            fp = PRESETS.get((t.options or {}).get("preset", "devis"), PRESETS["devis"])["facteur_temps"]
            hist.append(t.resultats["duree_calcul_s"] / t.nb_images / fp)
    spi = statistics.median(hist) if hist else SECONDES_PAR_IMAGE_DEFAUT
    # croissance légèrement plus que linéaire (appariement des images)
    s = spi * f * nb_images * (1 + max(0, nb_images - 100) / 400)
    return {"secondes": s, "base": "historique" if hist else "valeur par défaut",
            "nb_references": len(hist)}


# ---------------------------------------------------------------------------
# Construction du document de métré à partir de la détection
def document_depuis_detection(res, info: dict, echelle_source: str, doc_existant: dict | None) -> dict:
    doc = metre_core.document_vide()
    if doc_existant:
        doc["echelle"] = doc_existant.get("echelle") or doc["echelle"]
        doc["lignes_manuelles"] = doc_existant.get("lignes_manuelles", [])
    if not (doc["echelle"].get("references")):
        doc["echelle"]["source"] = echelle_source
    doc["repere"] = {"type": "odm", "source": "odm", "epsg": info.get("epsg"), "origine": info.get("origine")}
    for i, p in enumerate(res.pans):
        pl = geo.Plan.from_dict(p["plan"])
        doc["pans"].append({
            "id": f"p{i + 1}", "nom": f"Pan {i + 1} ({geo.orientation_texte(pl.azimut_deg)})",
            "contour": p["contour"], "plan": p["plan"], "stats": p["stats"],
            "source_plan": "modele_3d", "source_contour": "auto", "valide": False, "notes": "",
        })
    for j, o in enumerate(res.obstacles):
        doc["obstacles"].append({
            "id": f"o{j + 1}", "type": "emergence", "contour": o["contour"], "hauteur": o["hauteur"],
            "pan_id": f"p{o['pan_index'] + 1}", "deduire": False, "valide": False, "source": "auto",
        })
    doc["auto"] = {
        "date": maintenant().isoformat(),
        "pans": [{"id": pp["id"], "nom": pp["nom"],
                  "surface": geo.Pan(pp["id"], [tuple(c) for c in pp["contour"]],
                                     geo.Plan.from_dict(pp["plan"])).aire_reelle,
                  "pente_deg": geo.Plan.from_dict(pp["plan"]).pente_deg} for pp in doc["pans"]],
        "avertissements": res.avertissements,
        "emprise": res.emprise,
    }
    return doc


def enregistrer_version(db: Session, chantier_id: int, document: dict, commentaire: str,
                        auteur_id: int | None = None) -> VersionMetre:
    der = db.scalar(select(VersionMetre).where(VersionMetre.chantier_id == chantier_id)
                    .order_by(VersionMetre.numero.desc()).limit(1))
    calc = metre_core.calculer(document)
    resume = {"surface": calc["totaux"]["surface_nette"], "nb_pans": calc["totaux"]["nb_pans"],
              "valides": sum(1 for p in calc["pans"] if p["valide"])}
    v = VersionMetre(chantier_id=chantier_id, numero=(der.numero + 1) if der else 1, document=document,
                     resume=resume, commentaire=commentaire, auteur_id=auteur_id)
    db.add(v)
    return v


def version_courante(db: Session, chantier_id: int) -> VersionMetre | None:
    return db.scalar(select(VersionMetre).where(VersionMetre.chantier_id == chantier_id)
                     .order_by(VersionMetre.numero.desc()).limit(1))


def executer_detection(db: Session, chantier: Chantier, graine=None, zone=None, params: dict | None = None,
                       auteur_id: int | None = None) -> dict:
    dossier = dossier_modele(chantier.id)
    info = mod.lire_info(dossier)
    if zone and len(zone) >= 3:
        xs = [p[0] for p in zone]
        ys = [p[1] for p in zone]
        bbox = (min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3)
        if graine is None:
            graine = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    else:
        if graine is None:
            pos = [(p.meta or {}) for p in db.query(Photo).filter(Photo.chantier_id == chantier.id, Photo.exclue == False)  # noqa
                   .all() if (p.meta or {}).get("lat") is not None]
            if chantier.lat is not None and chantier.lon is not None and info.get("epsg"):
                graine = mod.depuis_wgs84(info, chantier.lon, chantier.lat)
            elif pos and (info.get("epsg") or info.get("crs_wkt")):
                # à défaut de position du chantier : centre des prises de vue (le vol est centré sur le toit)
                graine = mod.depuis_wgs84(info, sum(m["lon"] for m in pos) / len(pos), sum(m["lat"] for m in pos) / len(pos))
            b = info["bornes"]
            if graine is None or not (b[0] <= graine[0] <= b[2] and b[1] <= graine[1] <= b[3]):
                graine = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        r = float((params or {}).get("rayon", 30))
        bbox = (graine[0] - r, graine[1] - r, graine[0] + r, graine[1] + r)
    surface = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    res_max = max(info.get("res_mns", 0.05), math.sqrt(surface / 1.2e6))
    grille = mod.lire_mns(dossier, bbox, res_max=res_max)
    p = Parametres()
    for k, v in (params or {}).items():
        if hasattr(p, k) and v is not None:
            setattr(p, k, type(getattr(p, k))(v))
    vegetation = mod.vegetation_sur_grille(dossier, grille)
    res = segmenter(grille, graine_xy=tuple(graine), zone=zone, p=p, exclusion=vegetation)
    # couverture réelle par le nuage de points (le MNS d'ODM est interpolé et masque les lacunes)
    for i, pan in enumerate(res.pans):
        pl = geo.Plan.from_dict(pan["plan"])
        cv = mod.couverture_nuage(dossier, [tuple(c) for c in pan["contour"]], z_plan=lambda x, y, pl=pl: pl.z(x, y))
        if cv is not None:
            pan["stats"]["couverture"] = cv
            pan["stats"]["couverture_source"] = "nuage"
            if cv < 0.85:
                res.avertissements.append(
                    f"Pan {i + 1} : environ {round((1 - cv) * 100)} % de sa surface sans point observé "
                    "(zone peu ou pas photographiée, ou masquée). Contrôlez ce versant.")
    a_gcp = db.query(Photo).filter(Photo.chantier_id == chantier.id, Photo.type == "gcp").count() > 0
    source = "gcp" if a_gcp else ("gps" if (chantier.analyse_photos or {}).get("stats", {}).get("avec_gps") else "aucune")
    courante = version_courante(db, chantier.id)
    doc = document_depuis_detection(res, info, source, courante.document if courante else None)
    enregistrer_version(db, chantier.id, doc,
                        f"Détection automatique : {len(res.pans)} pan(s), {len(res.obstacles)} émergence(s)",
                        auteur_id)
    if chantier.statut in ("preparation", "photos", "traitement"):
        chantier.statut = "a_verifier"
    journaliser(db, "detection", f"{len(res.pans)} pans détectés", chantier.id, auteur_id)
    db.commit()
    return {"nb_pans": len(res.pans), "nb_obstacles": len(res.obstacles), "avertissements": res.avertissements,
            "graine": list(graine), "resolution": grille.res}


# ---------------------------------------------------------------------------
def _erreur_odm_lisible(journal: str) -> str:
    j = journal.lower()
    conseils = []
    if "not enough" in j or "no reconstruction" in j or "reconstruction is empty" in j or "could not" in j:
        conseils.append("Les photos ne se recoupent pas assez pour être assemblées : augmentez le recouvrement, "
                        "ajoutez des vues obliques et vérifiez qu'elles proviennent du même site.")
    if "gps" in j and "missing" in j:
        conseils.append("Positions GPS absentes : prévoyez une cote de référence.")
    if "memory" in j or "killed" in j or "out of memory" in j:
        conseils.append("Mémoire insuffisante sur le serveur de calcul : utilisez le préréglage « Aperçu » ou un "
                        "serveur plus puissant.")
    return " ".join(conseils) or "Consultez le journal technique ci-dessous."


class Travailleur:
    """Deux fils : reconstructions (longues, pilotées par étapes) et calculs (détection)."""

    def __init__(self):
        self._stop = threading.Event()
        self._fils: list[threading.Thread] = []

    def demarrer(self):
        with SessionLocal() as db:
            for t in db.scalars(select(Traitement).where(Traitement.type == "detection",
                                                         Traitement.statut == "en_cours")).all():
                t.statut = "en_attente"
            db.commit()
        for cible in (self._boucle_reconstructions, self._boucle_calculs, self._boucle_sauvegardes):
            th = threading.Thread(target=cible, daemon=True)
            th.start()
            self._fils.append(th)

    def arreter(self):
        self._stop.set()

    # --- reconstructions
    def _boucle_reconstructions(self):
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    jobs = db.scalars(select(Traitement).where(Traitement.type == "reconstruction",
                                                               Traitement.statut.in_(ACTIFS))
                                      .order_by(Traitement.id)).all()
                    for job in jobs:
                        try:
                            avancer_reconstruction(db, job)
                        except ErreurNodeODM as e:
                            job.tentatives += 1
                            job.message = f"Serveur de calcul indisponible, nouvel essai automatique ({job.tentatives}/30)…"
                            if job.tentatives > 30:
                                job.statut = "erreur"
                                job.erreur = str(e)
                                job.fin = maintenant()
                            db.commit()
                        except Exception as e:  # erreur inattendue : on arrête ce traitement proprement
                            log.exception("reconstruction %s", job.id)
                            job.statut = "erreur"
                            job.erreur = f"{e}\n{traceback.format_exc()[-1500:]}"
                            job.fin = maintenant()
                            db.commit()
            except Exception:
                log.exception("boucle reconstructions")
            self._stop.wait(config.intervalle_sondage_s)

    def _boucle_calculs(self):
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    job = db.scalar(select(Traitement).where(Traitement.type == "detection",
                                                             Traitement.statut == "en_attente")
                                    .order_by(Traitement.id).limit(1))
                    if job:
                        executer_job_detection(db, job)
                        continue
            except Exception:
                log.exception("boucle calculs")
            self._stop.wait(1.0)

    def _boucle_sauvegardes(self):
        from .sauvegarde import sauvegarde_quotidienne
        while not self._stop.is_set():
            if config.sauvegarde_auto:
                try:
                    sauvegarde_quotidienne()
                except Exception:
                    log.exception("sauvegarde")
            self._stop.wait(3600)


def executer_job_detection(db: Session, job: Traitement):
    job.statut, job.debut, job.progression = "en_cours", maintenant(), 10
    job.etape = "Détection des pans"
    db.commit()
    try:
        ch = db.get(Chantier, job.chantier_id)
        o = job.options or {}
        r = executer_detection(db, ch, o.get("graine"), o.get("zone"), o.get("params"), o.get("auteur_id"))
        job.resultats = r
        job.statut, job.progression, job.fin = "termine", 100, maintenant()
        job.message = f"{r['nb_pans']} pan(s) détecté(s)"
    except Exception as e:
        log.exception("détection")
        db.rollback()
        job = db.get(Traitement, job.id)
        job.statut, job.fin = "erreur", maintenant()
        job.erreur = str(e)
    db.commit()


def avancer_reconstruction(db: Session, job: Traitement):
    cli = client_odm(db)
    etat = dict(job.etat or {})
    ch = db.get(Chantier, job.chantier_id)
    if job.annulation_demandee:
        if etat.get("uuid"):
            try:
                cli.annuler(etat["uuid"])
                cli.supprimer(etat["uuid"])
            except ErreurNodeODM:
                pass
        job.statut, job.fin, job.message = "annule", maintenant(), "Traitement annulé"
        if ch.statut == "traitement":
            ch.statut = "photos"
        db.commit()
        return

    photos = db.scalars(select(Photo).where(Photo.chantier_id == job.chantier_id, Photo.exclue == False)  # noqa
                        .order_by(Photo.id)).all()
    if job.statut == "en_attente":
        cli.info()
        preset = (job.options or {}).get("preset", "devis")
        opts = dict(PRESETS.get(preset, PRESETS["devis"])["options"])
        opts.update((job.options or {}).get("options_odm") or {})
        uuid = cli.creer(f"MMT-{ch.reference}-{job.id}", opts, SORTIES)
        etat = {"uuid": uuid, "envoyees": []}
        job.etat, job.statut, job.debut = etat, "envoi", job.debut or maintenant()
        job.etape, job.message, job.tentatives = "Envoi des photos", "Envoi des photos au serveur de calcul…", 0
        db.commit()
        return
    if job.statut == "envoi":
        deja = set(etat.get("envoyees", []))
        reste = [p for p in photos if p.id not in deja]
        envoyes_ce_tour = 0
        while reste and envoyes_ce_tour < 50:
            lot = reste[:LOT_ENVOI]
            try:
                cli.envoyer(etat["uuid"], [Path(p.chemin) for p in lot])
            except ErreurNodeODM as e:
                if "not found" in str(e).lower() or "404" in str(e):
                    job.statut, job.etat = "en_attente", {}
                    job.message = "Session d'envoi perdue (serveur redémarré) : nouvel envoi complet."
                    db.commit()
                    return
                raise
            deja.update(p.id for p in lot)
            reste = reste[LOT_ENVOI:]
            envoyes_ce_tour += len(lot)
            etat["envoyees"] = sorted(deja)
            job.etat = dict(etat)
            job.progression = 10 * len(deja) / max(1, len(photos))
            job.message = f"Envoi des photos : {len(deja)}/{len(photos)}"
            job.tentatives = 0
            db.commit()
        if not reste:
            cli.valider(etat["uuid"])
            job.statut, job.etape = "en_cours", "Reconstruction 3D"
            job.message = "Photos envoyées, calcul en file d'attente"
            etat["debut_calcul"] = time.time()
            job.etat = dict(etat)
            db.commit()
        return
    if job.statut == "en_cours":
        try:
            info = cli.etat(etat["uuid"])
        except ErreurNodeODM as e:
            if "not found" in str(e).lower():
                job.statut, job.fin = "erreur", maintenant()
                job.erreur = "La tâche n'existe plus sur le serveur de calcul (redémarré ou purgé). Relancez le calcul."
                db.commit()
                return
            raise
        code = info.get("status", {}).get("code")
        job.tentatives = 0
        if code == COMPLETED:
            job.statut, job.etape, job.progression = "telechargement", "Téléchargement des résultats", 90
            etat["duree_calcul_s"] = (info.get("processingTime") or 0) / 1000
            job.etat = dict(etat)
            job.message = "Calcul terminé, récupération des résultats…"
        elif code == FAILED:
            j = ""
            try:
                j = cli.journal(etat["uuid"], 60)
            except ErreurNodeODM:
                pass
            job.statut, job.fin = "erreur", maintenant()
            job.erreur = _erreur_odm_lisible(j) + "\n\n--- Journal (fin) ---\n" + j[-4000:]
            job.message = "La reconstruction 3D a échoué"
            if ch.statut == "traitement":
                ch.statut = "photos"
        elif code == CANCELED:
            job.statut, job.fin, job.message = "annule", maintenant(), "Annulé sur le serveur de calcul"
        else:
            prog = float(info.get("progress") or 0)
            job.progression = 10 + 0.8 * prog
            job.message = f"{LIBELLES.get(code, 'En cours')} — {prog:.0f} %"
        db.commit()
        return
    if job.statut == "telechargement":
        dossier = dossier_modele(ch.id)
        tmp = config.data_dir / "tmp" / f"odm_{job.id}.zip"

        def prog(f):
            job.progression = 90 + 6 * f

        cli.telecharger(etat["uuid"], tmp, prog)
        if dossier.exists():
            shutil.rmtree(dossier)
        fichiers = mod.extraire(tmp, dossier)
        tmp.unlink(missing_ok=True)
        job.message = "Préparation du modèle…"
        db.commit()
        info = mod.preparer(dossier, fichiers)
        ch.modele = {"type": "odm", "traitement_id": job.id, "epsg": info.get("epsg"),
                     "origine": info.get("origine"), "bornes": info.get("bornes"), "res_mns": info.get("res_mns"),
                     "res_ortho": info.get("res_ortho"), "nb_points": info.get("nb_points"),
                     "ortho": "ortho" in fichiers, "rapport_odm": "rapport" in fichiers}
        ch.mode = "3d"
        try:
            cli.supprimer(etat["uuid"])
        except ErreurNodeODM:
            pass
        res = {"duree_calcul_s": etat.get("duree_calcul_s"), "fichiers": fichiers}
        try:
            r = executer_detection(db, ch, None, None, None, None)
            res["detection"] = r
        except Exception as e:
            log.exception("détection automatique")
            db.rollback()
            ch = db.get(Chantier, job.chantier_id)
            job = db.get(Traitement, job.id)
            res["detection_erreur"] = str(e)
            ch.statut = "a_verifier"
        job.resultats = res
        job.statut, job.progression, job.fin = "termine", 100, maintenant()
        job.message = "Modèle 3D prêt" + (f" — {res['detection']['nb_pans']} pan(s) détecté(s)"
                                          if res.get("detection") else " — désignez le toit à mesurer")
        journaliser(db, "reconstruction", job.message, ch.id)
        db.commit()


travailleur = Travailleur()
