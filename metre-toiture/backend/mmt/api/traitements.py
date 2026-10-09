from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import photos as ph
from ..db import Chantier, Photo, Traitement, Utilisateur, get_db, journaliser
from ..securite import utilisateur_courant
from ..services import modele as mod
from ..services.nodeodm import PRESETS, ErreurNodeODM
from ..services.traitements import ACTIFS, client_odm, dossier_modele, estimer_duree
from .commun import chantier_ou_404

router = APIRouter(prefix="/api", tags=["traitements"])
ETAPES = {"en_attente": "En attente", "envoi": "Envoi des photos", "en_cours": "Calcul en cours",
          "telechargement": "Récupération des résultats", "termine": "Terminé", "erreur": "Erreur",
          "annule": "Annulé"}


def traitement_dict(t: Traitement, chantier: Chantier | None = None) -> dict:
    d = {"id": t.id, "chantier_id": t.chantier_id, "type": t.type, "statut": t.statut,
         "statut_libelle": ETAPES.get(t.statut, t.statut), "etape": t.etape, "progression": round(t.progression, 1),
         "message": t.message, "erreur": t.erreur, "nb_images": t.nb_images, "options": t.options,
         "duree_estimee_s": t.duree_estimee_s, "resultats": t.resultats,
         "cree_le": t.cree_le.isoformat() if t.cree_le else None,
         "debut": t.debut.isoformat() if t.debut else None, "fin": t.fin.isoformat() if t.fin else None}
    if chantier:
        d["chantier"] = {"id": chantier.id, "nom": chantier.nom, "reference": chantier.reference}
    return d


@router.get("/calcul/etat")
def etat_calcul(_: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    cli = client_odm(db)
    try:
        info = cli.info()
        return {"disponible": True, "url": cli.url, "version": info.get("version"),
                "moteur": info.get("engine"), "version_moteur": info.get("engineVersion"),
                "file_attente": info.get("taskQueueCount"), "coeurs": info.get("cpuCores"),
                "memoire_go": round((info.get("totalMemory") or 0) / 1e9, 1),
                "max_images": info.get("maxImages")}
    except ErreurNodeODM as e:
        return {"disponible": False, "url": cli.url, "erreur": str(e)}


@router.get("/calcul/presets")
def presets(nb_images: int = 0, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    return {k: {"libelle": v["libelle"], "description": v["description"],
                "estimation": estimer_duree(db, nb_images, k) if nb_images else None}
            for k, v in PRESETS.items()}


@router.get("/traitements")
def lister(actifs: bool = False, chantier_id: int | None = None, _: Utilisateur = Depends(utilisateur_courant),
           db: Session = Depends(get_db)):
    q = select(Traitement)
    if actifs:
        q = q.where(Traitement.statut.in_(ACTIFS))
    if chantier_id:
        q = q.where(Traitement.chantier_id == chantier_id)
    ts = db.scalars(q.order_by(Traitement.id.desc()).limit(100)).all()
    return [traitement_dict(t, db.get(Chantier, t.chantier_id)) for t in ts]


@router.get("/traitements/{tid}")
def lire(tid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    t = db.get(Traitement, tid)
    if not t:
        raise HTTPException(404, "Traitement introuvable")
    return traitement_dict(t, db.get(Chantier, t.chantier_id))


class Reconstruction(BaseModel):
    preset: str = "devis"


@router.post("/chantiers/{cid}/reconstruction")
def lancer(cid: int, d: Reconstruction, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    if db.scalar(select(Traitement).where(Traitement.chantier_id == cid, Traitement.type == "reconstruction",
                                          Traitement.statut.in_(ACTIFS))):
        raise HTTPException(409, "Une reconstruction est déjà en cours pour ce chantier")
    n = db.query(Photo).filter(Photo.chantier_id == cid, Photo.exclue == False, Photo.type == "photo").count()  # noqa
    if n < 5:
        raise HTTPException(400, "Au moins 5 photos (non exclues) sont nécessaires pour une reconstruction 3D.")
    if d.preset not in PRESETS:
        raise HTTPException(400, "Préréglage inconnu")
    est = estimer_duree(db, n, d.preset)
    t = Traitement(chantier_id=cid, type="reconstruction", options={"preset": d.preset}, nb_images=n,
                   duree_estimee_s=est["secondes"], message="En attente du serveur de calcul")
    db.add(t)
    c.statut = "traitement"
    c.mode = "3d"
    journaliser(db, "reconstruction_lancee", f"{n} photos, préréglage {d.preset}", cid, u.id)
    db.commit()
    return traitement_dict(t)


@router.post("/traitements/{tid}/annuler")
def annuler(tid: int, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    t = db.get(Traitement, tid)
    if not t or t.statut not in ACTIFS:
        raise HTTPException(400, "Ce traitement n'est pas en cours")
    if t.statut == "en_attente" and not (t.etat or {}).get("uuid"):
        t.statut = "annule"
        t.message = "Annulé"
        c = db.get(Chantier, t.chantier_id)
        if c.statut == "traitement":
            c.statut = "photos"
    else:
        t.annulation_demandee = True
        t.message = "Annulation demandée…"
    journaliser(db, "traitement_annule", str(tid), t.chantier_id, u.id)
    db.commit()
    return traitement_dict(t)


@router.post("/traitements/{tid}/relancer")
def relancer(tid: int, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    t = db.get(Traitement, tid)
    if not t or t.statut not in ("erreur", "annule"):
        raise HTTPException(400, "Seul un traitement en erreur ou annulé peut être relancé")
    if t.type == "reconstruction":
        return lancer(t.chantier_id, Reconstruction(preset=(t.options or {}).get("preset", "devis")), u, db)
    n = Traitement(chantier_id=t.chantier_id, type=t.type, options=t.options)
    db.add(n)
    db.commit()
    return traitement_dict(n)


class Detection(BaseModel):
    graine: list[float] | None = None
    zone: list[list[float]] | None = None
    params: dict | None = None


@router.post("/chantiers/{cid}/detection")
def detection(cid: int, d: Detection, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    if not c.modele or c.modele.get("type") != "odm":
        raise HTTPException(400, "Aucun modèle 3D disponible pour ce chantier")
    t = Traitement(chantier_id=cid, type="detection", options={**d.model_dump(), "auteur_id": u.id},
                   message="Détection des pans en attente")
    db.add(t)
    db.commit()
    return traitement_dict(t)


# ---------------------------------------------------------------------------
# Données du modèle
def _bbox(bbox: str | None, c: Chantier) -> tuple:
    if bbox:
        try:
            v = [float(x) for x in bbox.split(",")]
            assert len(v) == 4 and v[2] > v[0] and v[3] > v[1]
            return tuple(v)
        except (ValueError, AssertionError):
            raise HTTPException(400, "bbox invalide (x0,y0,x1,y1)")
    return tuple(c.modele["bornes"])


@router.get("/chantiers/{cid}/fond")
def fond(cid: int, quoi: str = "ortho", bbox: str | None = None, max_px: int = Query(2048, le=4096),
         _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    """Image de fond du plan de travail, avec ses bornes (en-tête X-Bornes) dans le repère local."""
    c = chantier_ou_404(db, cid)
    m = c.modele or {}
    if m.get("type") == "photo":
        p = db.get(Photo, m["photo_id"])
        import io

        from PIL import Image, ImageOps
        with Image.open(p.chemin) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((max_px, max_px))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=88)
        return Response(buf.getvalue(), media_type="image/jpeg",
                        headers={"X-Bornes": ",".join(f"{v:.4f}" for v in m["bornes"])})
    if m.get("type") != "odm":
        raise HTTPException(404, "Pas de fond disponible")
    try:
        data, bornes, mime = mod.image_recadree(dossier_modele(cid), quoi, _bbox(bbox, c), max_px)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(data, media_type=mime, headers={"X-Bornes": ",".join(f"{v:.4f}" for v in bornes),
                                                    "Cache-Control": "private, max-age=600"})


@router.get("/chantiers/{cid}/nuage")
def nuage(cid: int, bbox: str | None = None, max_points: int = Query(400_000, le=2_000_000),
          _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    if not c.modele or c.modele.get("type") != "odm" or not (dossier_modele(cid) / "nuage_xyz.npy").exists():
        raise HTTPException(404, "Nuage de points indisponible")
    return Response(mod.nuage_recadre(dossier_modele(cid), _bbox(bbox, c), max_points),
                    media_type="application/octet-stream")


@router.get("/chantiers/{cid}/altitude")
def altitude(cid: int, x: float, y: float, _: Utilisateur = Depends(utilisateur_courant),
             db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    if not c.modele or c.modele.get("type") != "odm":
        return {"z": None}
    return {"z": mod.altitude(dossier_modele(cid), x, y)}


@router.get("/chantiers/{cid}/rapport-odm")
def rapport_odm(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    chantier_ou_404(db, cid)
    f = dossier_modele(cid) / "report.pdf"
    if not f.exists():
        raise HTTPException(404, "Rapport de reconstruction indisponible")
    return FileResponse(f, media_type="application/pdf", filename="rapport_reconstruction.pdf")


class Contour(BaseModel):
    contour: list[list[float]]


@router.post("/chantiers/{cid}/ajuster-plan")
def ajuster_plan(cid: int, d: Contour, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    """Plan ajusté sur le modèle 3D à l'intérieur d'un contour dessiné ou corrigé à la main."""
    c = chantier_ou_404(db, cid)
    if not c.modele or c.modele.get("type") != "odm":
        raise HTTPException(400, "Aucun modèle 3D pour ce chantier : saisissez la pente.")
    if len(d.contour) < 3 or len(d.contour) > 500:
        raise HTTPException(400, "Contour invalide")
    try:
        return mod.ajuster_plan_contour(dossier_modele(cid), [(float(p[0]), float(p[1])) for p in d.contour])
    except ValueError as e:
        raise HTTPException(400, str(e))


class PhotoUnique(BaseModel):
    photo_id: int
    hauteur_toit: float            # hauteur du toit (m) au-dessus du point de décollage
    altitude: float | None = None  # hauteur de vol relative (m) si absente des métadonnées
    focale_35mm: float | None = None


@router.post("/chantiers/{cid}/photo-unique")
def photo_unique(cid: int, d: PhotoUnique, u: Utilisateur = Depends(utilisateur_courant),
                 db: Session = Depends(get_db)):
    """Mode estimation : mesure sur une photo verticale, échelle tirée de l'altitude et de l'optique."""
    c = chantier_ou_404(db, cid)
    p = db.get(Photo, d.photo_id)
    if not p or p.chantier_id != cid:
        raise HTTPException(404, "Photo introuvable")
    m = p.meta or {}
    alt = d.altitude or m.get("alt_relative")
    f35 = d.focale_35mm or m.get("focale_35mm")
    if not alt or not f35:
        raise HTTPException(400, "Altitude relative ou focale équivalente inconnue : renseignez-les manuellement.")
    h = alt - d.hauteur_toit
    if h <= 1:
        raise HTTPException(400, "La hauteur du toit doit être inférieure à l'altitude de vol.")
    gsd = ph.gsd_cm(h, f35, m["largeur"], m["hauteur"]) / 100
    w, hh = m["largeur"] * gsd, m["hauteur"] * gsd
    avert = []
    tang = m.get("nacelle_tangage")
    if tang is None:
        avert.append("Inclinaison de la nacelle inconnue : la photo doit être parfaitement verticale.")
    elif tang > -85:
        avert.append(f"Nacelle inclinée à {tang:.0f}° : la photo n'est pas verticale, les cotes seront faussées.")
    avert.append("L'échelle n'est valable qu'à la hauteur du toit indiquée ; les pentes doivent être saisies. "
                 "Contrôlez au moins une cote au mètre.")
    c.modele = {"type": "photo", "photo_id": p.id, "gsd_m": gsd, "bornes": [-w / 2, -hh / 2, w / 2, hh / 2],
                "rotation_deg": m.get("nacelle_lacet") or 0.0, "altitude": alt, "hauteur_toit": d.hauteur_toit,
                "avertissements": avert}
    c.mode = "photo"
    if c.statut in ("preparation", "photos"):
        c.statut = "a_verifier"
    journaliser(db, "photo_unique", f"Photo {p.nom_fichier}, {gsd * 100:.2f} cm/px", cid, u.id)
    db.commit()
    return c.modele
