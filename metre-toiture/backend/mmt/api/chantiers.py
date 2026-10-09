from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import config
from ..core import photos as ph
from ..core.plan_vol import DRONES, PRECISIONS, TYPES_TOITURE, generer_plan
from ..db import Chantier, Journal, Photo, Traitement, Utilisateur, VersionMetre, get_db, journaliser, maintenant
from ..securite import utilisateur_courant
from .commun import STATUTS, chantier_dict, chantier_ou_404

router = APIRouter(prefix="/api", tags=["chantiers"])
EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png"}


class ChantierIn(BaseModel):
    nom: str
    reference: str | None = None
    client_nom: str = ""
    client_tel: str = ""
    client_email: str = ""
    adresse: str = ""
    lat: float | None = None
    lon: float | None = None
    type_toiture: str = ""
    mode: str = "3d"
    notes: str = ""


class ChantierMaj(BaseModel):
    nom: str | None = None
    reference: str | None = None
    client_nom: str | None = None
    client_tel: str | None = None
    client_email: str | None = None
    adresse: str | None = None
    lat: float | None = None
    lon: float | None = None
    type_toiture: str | None = None
    mode: str | None = None
    notes: str | None = None
    statut: str | None = None
    reserves: str | None = None
    archive: bool | None = None
    checklists: dict | None = None
    confirmations: dict | None = None


def _reference(db: Session) -> str:
    an = maintenant().year
    n = db.scalar(select(func.count(Chantier.id)).where(Chantier.reference.like(f"MT-{an}-%"))) or 0
    while True:
        n += 1
        ref = f"MT-{an}-{n:04d}"
        if not db.scalar(select(Chantier.id).where(Chantier.reference == ref)):
            return ref


@router.get("/tableau-de-bord")
def tableau(u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    actifs = db.scalars(select(Traitement).where(Traitement.statut.in_(("en_attente", "envoi", "en_cours",
                                                                        "telechargement")))).all()
    def compte(*statuts):
        return db.scalar(select(func.count(Chantier.id)).where(Chantier.statut.in_(statuts),
                                                               Chantier.archive == False))  # noqa
    recents = db.scalars(select(Chantier).where(Chantier.archive == False)  # noqa
                         .order_by(Chantier.modifie_le.desc()).limit(8)).all()
    return {
        "traitements_en_cours": len(actifs),
        "a_verifier": compte("a_verifier"),
        "termines": compte("valide", "termine"),
        "en_preparation": compte("preparation", "photos"),
        "total": db.scalar(select(func.count(Chantier.id)).where(Chantier.archive == False)),  # noqa
        "recents": [chantier_dict(c) for c in recents],
        "utilisateur": {"nom": u.nom, "email": u.email},
    }


@router.get("/chantiers")
def lister(statut: str | None = None, q: str | None = None, archives: bool = False,
           _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    req = select(Chantier).where(Chantier.archive == archives)
    if statut:
        req = req.where(Chantier.statut.in_(statut.split(",")))
    if q:
        m = f"%{q}%"
        req = req.where(or_(Chantier.nom.ilike(m), Chantier.reference.ilike(m), Chantier.client_nom.ilike(m),
                            Chantier.adresse.ilike(m)))
    out = []
    for c in db.scalars(req.order_by(Chantier.modifie_le.desc()).limit(500)).all():
        d = chantier_dict(c)
        v = db.scalar(select(VersionMetre).where(VersionMetre.chantier_id == c.id)
                      .order_by(VersionMetre.numero.desc()).limit(1))
        d["resume_metre"] = v.resume if v else None
        out.append(d)
    return out


@router.post("/chantiers")
def creer(d: ChantierIn, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    if not d.nom.strip():
        raise HTTPException(400, "Le nom du chantier est obligatoire")
    c = Chantier(nom=d.nom.strip(), reference=(d.reference or "").strip() or _reference(db), client_nom=d.client_nom,
                 client_tel=d.client_tel, client_email=d.client_email, adresse=d.adresse, lat=d.lat, lon=d.lon,
                 type_toiture=d.type_toiture, mode=d.mode if d.mode in ("3d", "photo", "saisie") else "3d",
                 notes=d.notes, cree_par=u.id)
    db.add(c)
    db.flush()
    journaliser(db, "creation", c.nom, c.id, u.id)
    db.commit()
    return chantier_dict(c, True)


@router.get("/chantiers/{cid}")
def lire(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    d = chantier_dict(c, True)
    d["nb_photos"] = db.scalar(select(func.count(Photo.id)).where(Photo.chantier_id == cid, Photo.type == "photo"))
    t = db.scalar(select(Traitement).where(Traitement.chantier_id == cid).order_by(Traitement.id.desc()).limit(1))
    from .traitements import traitement_dict
    d["dernier_traitement"] = traitement_dict(t) if t else None
    return d


@router.patch("/chantiers/{cid}")
def maj(cid: int, d: ChantierMaj, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    valeurs = d.model_dump(exclude_unset=True)
    if "statut" in valeurs and valeurs["statut"] not in STATUTS:
        raise HTTPException(400, "Statut inconnu")
    for k, v in valeurs.items():
        setattr(c, k, v)
    journaliser(db, "modification", ", ".join(valeurs.keys()), c.id, u.id)
    db.commit()
    return chantier_dict(c, True)


@router.delete("/chantiers/{cid}")
def supprimer(cid: int, definitif: bool = Query(False), confirmation: str = Query(""),
              u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    """Par défaut : archivage (réversible). Suppression définitive : confirmation = référence du chantier."""
    c = chantier_ou_404(db, cid)
    if not definitif:
        c.archive = True
        journaliser(db, "archivage", "", c.id, u.id)
        db.commit()
        return {"archive": True}
    if confirmation != c.reference:
        raise HTTPException(400, "Pour supprimer définitivement, saisissez la référence exacte du chantier.")
    for d in (config.photos_dir / str(cid), config.modeles_dir / str(cid)):
        shutil.rmtree(d, ignore_errors=True)
    db.delete(c)
    journaliser(db, "suppression_definitive", c.reference, None, u.id)
    db.commit()
    return {"supprime": True}


@router.post("/chantiers/{cid}/dupliquer")
def dupliquer(cid: int, avec_metre: bool = True, u: Utilisateur = Depends(utilisateur_courant),
              db: Session = Depends(get_db)):
    src = chantier_ou_404(db, cid)
    c = Chantier(nom=f"{src.nom} (copie)", reference=_reference(db), client_nom=src.client_nom,
                 client_tel=src.client_tel, client_email=src.client_email, adresse=src.adresse, lat=src.lat,
                 lon=src.lon, type_toiture=src.type_toiture, mode="saisie" if not avec_metre else src.mode,
                 notes=src.notes, preparation=src.preparation, plan_vol=src.plan_vol, materiaux=src.materiaux,
                 reserves=src.reserves, parent_id=src.id, cree_par=u.id, statut="preparation")
    db.add(c)
    db.flush()
    if avec_metre:
        v = db.scalar(select(VersionMetre).where(VersionMetre.chantier_id == cid)
                      .order_by(VersionMetre.numero.desc()).limit(1))
        if v:
            doc = dict(v.document)
            for p in doc.get("pans", []):
                p["valide"] = False
            db.add(VersionMetre(chantier_id=c.id, numero=1, document=doc, resume=v.resume,
                                commentaire=f"Copie du métré de {src.reference} (version {v.numero})", auteur_id=u.id))
            c.statut = "a_verifier"
        # le modèle 3D est partagé par lien (lecture seule) pour éviter de dupliquer des Go
        if src.modele and (config.modeles_dir / str(cid)).exists():
            dst = config.modeles_dir / str(c.id)
            if not dst.exists():
                shutil.copytree(config.modeles_dir / str(cid), dst, copy_function=_lien_ou_copie)
            c.modele = src.modele
            c.mode = src.mode
    journaliser(db, "duplication", f"depuis {src.reference}", c.id, u.id)
    db.commit()
    return chantier_dict(c, True)


def _lien_ou_copie(a, b):
    try:
        Path(b).hardlink_to(a)
    except OSError:
        shutil.copy2(a, b)


@router.get("/chantiers/{cid}/journal")
def journal(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    lignes = db.scalars(select(Journal).where(Journal.chantier_id == cid).order_by(Journal.id.desc()).limit(200)).all()
    noms = {u.id: u.nom or u.email for u in db.scalars(select(Utilisateur)).all()}
    return [{"action": j.action, "detail": j.detail, "date": j.cree_le.isoformat(),
             "utilisateur": noms.get(j.utilisateur_id)} for j in lignes]


# ---------------------------------------------------------------------------
# Préparation et plan de prise de vue
@router.get("/plan-vol/referentiel")
def referentiel(_: Utilisateur = Depends(utilisateur_courant)):
    return {"drones": {k: v["nom"] for k, v in DRONES.items()},
            "precisions": {k: v["libelle"] for k, v in PRECISIONS.items()},
            "types_toiture": TYPES_TOITURE}


@router.post("/plan-vol/calculer")
def calculer_plan(params: dict, _: Utilisateur = Depends(utilisateur_courant)):
    return generer_plan(params)


@router.put("/chantiers/{cid}/preparation")
def preparation(cid: int, params: dict, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    c.preparation = params
    c.plan_vol = generer_plan(params)
    if params.get("type_toiture"):
        c.type_toiture = params["type_toiture"]
    journaliser(db, "preparation", "Plan de prise de vue généré", c.id, u.id)
    db.commit()
    return c.plan_vol


# ---------------------------------------------------------------------------
# Photos
def photo_dict(p: Photo) -> dict:
    m = p.meta or {}
    a = p.analyse or {}
    return {"id": p.id, "nom": p.nom_fichier, "taille": p.taille, "exclue": p.exclue, "type": p.type,
            "largeur": m.get("largeur"), "hauteur": m.get("hauteur"), "modele": m.get("modele"),
            "lat": m.get("lat"), "lon": m.get("lon"), "alt_relative": m.get("alt_relative"),
            "nacelle_tangage": m.get("nacelle_tangage"), "nacelle_lacet": m.get("nacelle_lacet"),
            "categorie": ph.categorie_angle(m.get("nacelle_tangage")), "date_prise": m.get("date_prise"),
            "nettete": a.get("nettete"), "luminosite": a.get("luminosite"), "problemes": a.get("problemes", [])}


def _analyse_serie(db: Session, c: Chantier) -> dict:
    photos = db.scalars(select(Photo).where(Photo.chantier_id == c.id, Photo.type == "photo")).all()
    items = []
    for p in photos:
        d = {"id": p.id, "sha256": p.sha256, "exclue": p.exclue}
        d.update(p.meta or {})
        d.update({k: v for k, v in (p.analyse or {}).items() if k != "problemes"})
        items.append(d)
    centre = None
    res = ph.analyser_serie(items, centre)
    for p in photos:
        a = dict(p.analyse or {})
        a["problemes"] = res["photos"].get(p.id, [])
        p.analyse = a
    res.pop("photos", None)
    res["date"] = maintenant().isoformat()
    c.analyse_photos = res
    return res


def _nom_sur(nom: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(nom).name)[:120]
    return base or "photo.jpg"


@router.post("/chantiers/{cid}/photos")
def importer(cid: int, fichiers: list[UploadFile] = File(...), u: Utilisateur = Depends(utilisateur_courant),
             db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    dossier = config.photos_dir / str(cid)
    (dossier / "miniatures").mkdir(parents=True, exist_ok=True)
    resultats = []
    for f in fichiers:
        nom = _nom_sur(f.filename or "photo")
        ext = Path(nom).suffix.lower()
        data = f.file.read(config.max_photo_mo * 1024 * 1024 + 1)
        if len(data) > config.max_photo_mo * 1024 * 1024:
            resultats.append({"nom": nom, "erreur": f"Fichier trop volumineux (> {config.max_photo_mo} Mo)"})
            continue
        sha = hashlib.sha256(data).hexdigest()
        if db.scalar(select(Photo.id).where(Photo.chantier_id == cid, Photo.sha256 == sha)):
            resultats.append({"nom": nom, "erreur": "Déjà importée"})
            continue
        if ext == ".txt":
            # fichier de points de contrôle (gcp_list.txt) ou de géolocalisation (geo.txt) au format ODM
            if not (nom.lower().startswith("gcp") or nom.lower() == "geo.txt"):
                resultats.append({"nom": nom, "erreur": "Seuls les fichiers gcp_list.txt et geo.txt sont acceptés"})
                continue
            chemin = dossier / nom.lower()
            chemin.write_bytes(data)
            p = Photo(chantier_id=cid, nom_fichier=nom, chemin=str(chemin), sha256=sha, taille=len(data), type="gcp")
            db.add(p)
            db.flush()
            resultats.append({"id": p.id, "nom": nom, "type": "gcp"})
            continue
        if ext not in EXTENSIONS:
            resultats.append({"nom": nom, "erreur": "Format non pris en charge (JPEG ou TIFF attendu)"})
            continue
        chemin = dossier / f"{sha[:10]}_{nom}"
        chemin.write_bytes(data)
        try:
            meta = ph.lire_metadonnees(chemin)
            an = ph.analyser_image(chemin)
        except (UnidentifiedImageError, OSError, ValueError) as e:
            chemin.unlink(missing_ok=True)
            resultats.append({"nom": nom, "erreur": f"Image illisible ou corrompue ({e.__class__.__name__})"})
            continue
        mini = an.pop("_miniature")
        mini.thumbnail((360, 360))
        mini.convert("RGB").save(dossier / "miniatures" / f"{chemin.stem}.jpg", "JPEG", quality=80)
        meta = {k: v for k, v in meta.items() if isinstance(v, (int, float, str, type(None), bool))}
        p = Photo(chantier_id=cid, nom_fichier=nom, chemin=str(chemin), sha256=sha, taille=len(data), meta=meta,
                  analyse=an)
        db.add(p)
        db.flush()
        resultats.append(photo_dict(p))
    if c.statut == "preparation":
        c.statut = "photos"
    db.flush()
    _analyse_serie(db, c)
    ok = sum(1 for r in resultats if "erreur" not in r)
    journaliser(db, "import_photos", f"{ok} fichier(s) importé(s)", cid, u.id)
    db.commit()
    return {"resultats": resultats, "analyse": c.analyse_photos}


@router.get("/chantiers/{cid}/photos")
def photos(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    chantier_ou_404(db, cid)
    return [photo_dict(p) for p in db.scalars(select(Photo).where(Photo.chantier_id == cid).order_by(Photo.id)).all()]


@router.get("/chantiers/{cid}/analyse-photos")
def analyse(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    r = _analyse_serie(db, c)
    db.commit()
    return r


class PhotoMaj(BaseModel):
    exclue: bool


@router.patch("/photos/{pid}")
def maj_photo(pid: int, d: PhotoMaj, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    p = db.get(Photo, pid)
    if not p:
        raise HTTPException(404, "Photo introuvable")
    p.exclue = d.exclue
    _analyse_serie(db, db.get(Chantier, p.chantier_id))
    db.commit()
    return photo_dict(p)


@router.post("/chantiers/{cid}/photos/exclure-problemes")
def exclure_problemes(cid: int, codes: list[str], _: Utilisateur = Depends(utilisateur_courant),
                      db: Session = Depends(get_db)):
    """Exclut en un clic les photos signalées (ex. ['floue', 'doublon'])."""
    c = chantier_ou_404(db, cid)
    n = 0
    for p in db.scalars(select(Photo).where(Photo.chantier_id == cid, Photo.exclue == False)).all():  # noqa
        if set((p.analyse or {}).get("problemes", [])) & set(codes):
            p.exclue = True
            n += 1
    _analyse_serie(db, c)
    db.commit()
    return {"exclues": n, "analyse": c.analyse_photos}


@router.delete("/photos/{pid}")
def suppr_photo(pid: int, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    p = db.get(Photo, pid)
    if not p:
        raise HTTPException(404, "Photo introuvable")
    Path(p.chemin).unlink(missing_ok=True)
    (Path(p.chemin).parent / "miniatures" / f"{Path(p.chemin).stem}.jpg").unlink(missing_ok=True)
    c = db.get(Chantier, p.chantier_id)
    db.delete(p)
    db.flush()
    _analyse_serie(db, c)
    journaliser(db, "suppression_photo", p.nom_fichier, c.id, u.id)
    db.commit()
    return {"ok": True}


@router.get("/photos/{pid}/miniature")
def miniature(pid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    p = db.get(Photo, pid)
    if not p or p.type != "photo":
        raise HTTPException(404, "Photo introuvable")
    m = Path(p.chemin).parent / "miniatures" / f"{Path(p.chemin).stem}.jpg"
    if not m.exists():
        raise HTTPException(404, "Miniature absente")
    return FileResponse(m, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/photos/{pid}/image")
def image(pid: int, max_px: int = 2400, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    p = db.get(Photo, pid)
    if not p or p.type != "photo":
        raise HTTPException(404, "Photo introuvable")
    import io
    with Image.open(p.chemin) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
    return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})
