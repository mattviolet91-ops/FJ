"""Authentification : mots de passe scrypt, sessions par jeton aléatoire en cookie HttpOnly."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import config
from .db import SessionWeb, Utilisateur, get_db, maintenant

COOKIE = "mmt_session"
_N, _R, _P = 2 ** 14, 8, 1


def hacher_mot_de_passe(mdp: str) -> str:
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(mdp.encode(), salt=sel, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(sel).decode()}${base64.b64encode(h).decode()}"


def verifier_mot_de_passe(mdp: str, stocke: str) -> bool:
    try:
        _, n, r, p, sel, h = stocke.split("$")
        calc = hashlib.scrypt(mdp.encode(), salt=base64.b64decode(sel), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(h))
    except Exception:
        return False


def valider_mot_de_passe(mdp: str) -> None:
    if len(mdp) < 10:
        raise HTTPException(400, "Le mot de passe doit contenir au moins 10 caractères.")


def _h(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


def ouvrir_session(db: Session, u: Utilisateur) -> str:
    jeton = secrets.token_urlsafe(32)
    db.add(SessionWeb(jeton_hash=_h(jeton), utilisateur_id=u.id,
                      expire_le=maintenant() + timedelta(days=config.session_jours)))
    db.commit()
    return jeton


def fermer_session(db: Session, jeton: str | None) -> None:
    if jeton:
        s = db.scalar(select(SessionWeb).where(SessionWeb.jeton_hash == _h(jeton)))
        if s:
            db.delete(s)
            db.commit()


def utilisateur_courant(request: Request, db: Session = Depends(get_db)) -> Utilisateur:
    jeton = request.cookies.get(COOKIE)
    if not jeton:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            jeton = auth[7:]
    if not jeton:
        raise HTTPException(401, "Connexion requise")
    s = db.scalar(select(SessionWeb).where(SessionWeb.jeton_hash == _h(jeton)))
    if not s or s.expire_le < maintenant() or not s.utilisateur.actif:
        raise HTTPException(401, "Session expirée, reconnectez-vous")
    # protection CSRF : les requêtes modifiantes doivent porter l'en-tête ajouté par l'application
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.cookies.get(COOKIE) \
            and request.headers.get("x-requested-with") != "mmt":
        raise HTTPException(403, "Requête refusée (en-tête de sécurité manquant)")
    return s.utilisateur


def admin_requis(u: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
    if u.role != "admin":
        raise HTTPException(403, "Réservé aux administrateurs")
    return u
