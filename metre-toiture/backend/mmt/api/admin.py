from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import config
from ..db import Utilisateur, get_db, journaliser
from ..securite import admin_requis, utilisateur_courant
from ..services import sauvegarde as sv
from ..services.nodeodm import ClientNodeODM, ErreurNodeODM
from .commun import definir_parametre, parametre

router = APIRouter(prefix="/api", tags=["administration"])


@router.get("/parametres")
def lire(_: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    calc = parametre(db, "calcul", {}) or {}
    return {"entreprise": parametre(db, "entreprise", {}) or {},
            "calcul": {"nodeodm_url": calc.get("nodeodm_url") or config.nodeodm_url,
                       "jeton_defini": bool(calc.get("nodeodm_token") or config.nodeodm_token)},
            "logo": (config.fichiers_dir / "logo.png").exists()}


class Entreprise(BaseModel):
    nom: str = ""
    adresse: str = ""
    telephone: str = ""
    email: str = ""
    siret: str = ""
    site: str = ""


@router.put("/parametres/entreprise")
def entreprise(d: Entreprise, u: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    definir_parametre(db, "entreprise", d.model_dump())
    journaliser(db, "parametres", "entreprise", utilisateur_id=u.id)
    db.commit()
    return d


class Calcul(BaseModel):
    nodeodm_url: str
    nodeodm_token: str | None = None


@router.put("/parametres/calcul")
def calcul(d: Calcul, u: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    if not d.nodeodm_url.startswith(("http://", "https://")):
        raise HTTPException(400, "Adresse invalide (http:// ou https://)")
    ancien = parametre(db, "calcul", {}) or {}
    v = {"nodeodm_url": d.nodeodm_url.rstrip("/"),
         "nodeodm_token": d.nodeodm_token if d.nodeodm_token is not None else ancien.get("nodeodm_token", "")}
    definir_parametre(db, "calcul", v)
    journaliser(db, "parametres", "serveur de calcul", utilisateur_id=u.id)
    db.commit()
    return {"nodeodm_url": v["nodeodm_url"], "jeton_defini": bool(v["nodeodm_token"])}


@router.post("/parametres/calcul/tester")
def tester(d: Calcul, _: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    jeton = d.nodeodm_token if d.nodeodm_token is not None else (parametre(db, "calcul", {}) or {}).get("nodeodm_token", "")
    try:
        info = ClientNodeODM(d.nodeodm_url, jeton or "").info()
        return {"ok": True, "info": info}
    except ErreurNodeODM as e:
        return {"ok": False, "erreur": str(e)}


@router.post("/parametres/logo")
def logo(fichier: UploadFile = File(...), _: Utilisateur = Depends(admin_requis)):
    data = fichier.file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Logo trop volumineux (5 Mo max)")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise HTTPException(400, "Image illisible")
    im.thumbnail((800, 800))
    config.fichiers_dir.mkdir(parents=True, exist_ok=True)
    im.convert("RGBA").save(config.fichiers_dir / "logo.png", "PNG")
    return {"ok": True}


@router.get("/parametres/logo")
def lire_logo(_: Utilisateur = Depends(utilisateur_courant)):
    f = config.fichiers_dir / "logo.png"
    if not f.exists():
        raise HTTPException(404, "Pas de logo")
    return FileResponse(f, media_type="image/png")


@router.get("/sauvegardes")
def sauvegardes(_: Utilisateur = Depends(admin_requis)):
    return sv.lister()


@router.post("/sauvegardes")
def nouvelle(complete: bool = True, u: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    f = sv.creer_sauvegarde(inclure_fichiers=complete)
    journaliser(db, "sauvegarde", f.name, utilisateur_id=u.id)
    db.commit()
    return {"nom": f.name, "taille": f.stat().st_size}


@router.get("/sauvegardes/{nom}")
def telecharger(nom: str, _: Utilisateur = Depends(admin_requis)):
    f = (config.sauvegardes_dir / nom).resolve()
    if f.parent != config.sauvegardes_dir.resolve() or not f.exists() or not nom.startswith("mmt-"):
        raise HTTPException(404, "Sauvegarde introuvable")
    return FileResponse(f, media_type="application/gzip", filename=nom)
