"""Point d'entrée de l'application Matt's Métré Toiture."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from . import __version__
from .api import admin, auth, chantiers, metre, traitements
from .config import config
from .db import SessionLocal, Utilisateur, init_db
from .securite import hacher_mot_de_passe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")


def _admin_initial():
    if not (config.admin_email and config.admin_password):
        return
    with SessionLocal() as s:
        if s.scalar(select(func.count(Utilisateur.id))) == 0:
            s.add(Utilisateur(email=config.admin_email.lower(), nom="Administrateur", role="admin",
                              mot_de_passe=hacher_mot_de_passe(config.admin_password)))
            s.commit()


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    init_db()
    _admin_initial()
    if config.worker:
        from .services.traitements import travailleur
        travailleur.demarrer()
    yield
    if config.worker:
        from .services.traitements import travailleur
        travailleur.arreter()


app = FastAPI(title="Matt's Métré Toiture", version=__version__, lifespan=cycle_de_vie,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
for r in (auth.router, auth.utilisateurs, chantiers.router, traitements.router, metre.router, admin.router):
    app.include_router(r)


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


@app.get("/api/sante")
def sante():
    return {"ok": True, "version": __version__}


@app.exception_handler(ValueError)
async def erreur_valeur(_: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


# Interface web compilée (frontend/dist) servie par le même serveur
if config.frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=config.frontend_dir / "assets"), name="assets")

    @app.get("/{chemin:path}", include_in_schema=False)
    def spa(chemin: str):
        if chemin.startswith("api/"):
            return JSONResponse({"detail": "Introuvable"}, status_code=404)
        f = (config.frontend_dir / chemin).resolve()
        if chemin and f.is_file() and config.frontend_dir in f.parents:
            return FileResponse(f)
        return FileResponse(config.frontend_dir / "index.html", headers={"Cache-Control": "no-cache"})
