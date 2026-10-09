from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import config
from ..db import Utilisateur, get_db, journaliser
from ..securite import (COOKIE, admin_requis, fermer_session, hacher_mot_de_passe, ouvrir_session,
                        utilisateur_courant, valider_mot_de_passe, verifier_mot_de_passe)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_echecs: dict[str, list[float]] = {}


class Identifiants(BaseModel):
    email: str
    mot_de_passe: str


class NouvelUtilisateur(BaseModel):
    email: str
    nom: str = ""
    mot_de_passe: str
    role: str = "utilisateur"


def _u(u: Utilisateur) -> dict:
    return {"id": u.id, "email": u.email, "nom": u.nom, "role": u.role, "actif": u.actif}


def _cookie(resp: Response, jeton: str):
    resp.set_cookie(COOKIE, jeton, httponly=True, samesite="lax", secure=config.cookie_secure,
                    max_age=config.session_jours * 86400, path="/")


@router.get("/etat")
def etat(db: Session = Depends(get_db)):
    n = db.scalar(select(func.count(Utilisateur.id)))
    return {"initialise": n > 0}


@router.post("/initialiser")
def initialiser(d: NouvelUtilisateur, resp: Response, db: Session = Depends(get_db)):
    if db.scalar(select(func.count(Utilisateur.id))) > 0:
        raise HTTPException(409, "L'application est déjà initialisée")
    valider_mot_de_passe(d.mot_de_passe)
    u = Utilisateur(email=d.email.strip().lower(), nom=d.nom, mot_de_passe=hacher_mot_de_passe(d.mot_de_passe),
                    role="admin")
    db.add(u)
    db.commit()
    _cookie(resp, ouvrir_session(db, u))
    return _u(u)


@router.post("/connexion")
def connexion(d: Identifiants, resp: Response, request: Request, mode: str = "", db: Session = Depends(get_db)):
    """Connexion. Avec ?mode=api, le jeton est renvoyé dans la réponse (intégrations, ex. logiciel de devis)
    au lieu d'être placé dans un cookie : à transmettre dans l'en-tête « Authorization: Bearer <jeton> »."""
    import time
    cle = (request.client.host if request.client else "?") + "|" + d.email.lower()
    t = time.time()
    recents = [x for x in _echecs.get(cle, []) if t - x < 900]
    if len(recents) >= 8:
        raise HTTPException(429, "Trop de tentatives, réessayez dans quelques minutes.")
    u = db.scalar(select(Utilisateur).where(Utilisateur.email == d.email.strip().lower()))
    if not u or not u.actif or not verifier_mot_de_passe(d.mot_de_passe, u.mot_de_passe):
        recents.append(t)
        _echecs[cle] = recents
        raise HTTPException(401, "Identifiants incorrects")
    _echecs.pop(cle, None)
    jeton = ouvrir_session(db, u)
    if mode == "api":
        return {**_u(u), "jeton": jeton}
    _cookie(resp, jeton)
    return _u(u)


@router.post("/deconnexion")
def deconnexion(request: Request, resp: Response, db: Session = Depends(get_db)):
    fermer_session(db, request.cookies.get(COOKIE))
    resp.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/moi")
def moi(u: Utilisateur = Depends(utilisateur_courant)):
    return _u(u)


class ChangementMdp(BaseModel):
    ancien: str
    nouveau: str


@router.post("/mot-de-passe")
def changer_mdp(d: ChangementMdp, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    if not verifier_mot_de_passe(d.ancien, u.mot_de_passe):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    valider_mot_de_passe(d.nouveau)
    u = db.get(Utilisateur, u.id)
    u.mot_de_passe = hacher_mot_de_passe(d.nouveau)
    db.commit()
    return {"ok": True}


utilisateurs = APIRouter(prefix="/api/utilisateurs", tags=["utilisateurs"])


@utilisateurs.get("")
def lister(_: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    return [_u(u) for u in db.scalars(select(Utilisateur).order_by(Utilisateur.id)).all()]


@utilisateurs.post("")
def creer(d: NouvelUtilisateur, admin: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    valider_mot_de_passe(d.mot_de_passe)
    if db.scalar(select(Utilisateur).where(Utilisateur.email == d.email.strip().lower())):
        raise HTTPException(409, "Cet e-mail est déjà utilisé")
    u = Utilisateur(email=d.email.strip().lower(), nom=d.nom, mot_de_passe=hacher_mot_de_passe(d.mot_de_passe),
                    role="admin" if d.role == "admin" else "utilisateur")
    db.add(u)
    journaliser(db, "utilisateur_cree", u.email, utilisateur_id=admin.id)
    db.commit()
    return _u(u)


class MajUtilisateur(BaseModel):
    nom: str | None = None
    role: str | None = None
    actif: bool | None = None
    mot_de_passe: str | None = None


@utilisateurs.patch("/{uid}")
def maj(uid: int, d: MajUtilisateur, admin: Utilisateur = Depends(admin_requis), db: Session = Depends(get_db)):
    u = db.get(Utilisateur, uid)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    if d.nom is not None:
        u.nom = d.nom
    if d.role in ("admin", "utilisateur"):
        if u.id == admin.id and d.role != "admin":
            raise HTTPException(400, "Vous ne pouvez pas retirer vos propres droits d'administrateur")
        u.role = d.role
    if d.actif is not None:
        if u.id == admin.id and not d.actif:
            raise HTTPException(400, "Vous ne pouvez pas désactiver votre propre compte")
        u.actif = d.actif
    if d.mot_de_passe:
        valider_mot_de_passe(d.mot_de_passe)
        u.mot_de_passe = hacher_mot_de_passe(d.mot_de_passe)
    db.commit()
    return _u(u)
