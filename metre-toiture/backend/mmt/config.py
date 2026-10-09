"""Configuration par variables d'environnement (voir docs/INSTALLATION.md)."""
from __future__ import annotations

import os
from pathlib import Path


def _bool(v: str | None, defaut: bool) -> bool:
    if v is None:
        return defaut
    return v.strip().lower() in ("1", "true", "oui", "yes", "on")


class Config:
    def __init__(self) -> None:
        self.data_dir = Path(os.environ.get("MMT_DATA_DIR", Path(__file__).resolve().parents[1] / "data")).resolve()
        self.database_url = os.environ.get("MMT_DATABASE_URL", f"sqlite:///{self.data_dir / 'mmt.db'}")
        self.nodeodm_url = os.environ.get("MMT_NODEODM_URL", "http://localhost:3000").rstrip("/")
        self.nodeodm_token = os.environ.get("MMT_NODEODM_TOKEN", "")
        self.cookie_secure = _bool(os.environ.get("MMT_COOKIE_SECURE"), False)
        self.session_jours = int(os.environ.get("MMT_SESSION_JOURS", "14"))
        self.max_photo_mo = int(os.environ.get("MMT_MAX_PHOTO_MO", "60"))
        self.sauvegardes_a_garder = int(os.environ.get("MMT_SAUVEGARDES_A_GARDER", "14"))
        self.sauvegarde_auto = _bool(os.environ.get("MMT_SAUVEGARDE_AUTO"), True)
        self.worker = _bool(os.environ.get("MMT_WORKER"), True)
        self.frontend_dir = Path(os.environ.get(
            "MMT_FRONTEND_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist")).resolve()
        self.admin_email = os.environ.get("MMT_ADMIN_EMAIL")
        self.admin_password = os.environ.get("MMT_ADMIN_PASSWORD")
        self.intervalle_sondage_s = float(os.environ.get("MMT_INTERVALLE_SONDAGE_S", "10"))

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    @property
    def modeles_dir(self) -> Path:
        return self.data_dir / "modeles"

    @property
    def sauvegardes_dir(self) -> Path:
        return self.data_dir / "sauvegardes"

    @property
    def fichiers_dir(self) -> Path:
        return self.data_dir / "fichiers"

    def preparer(self) -> None:
        for d in (self.data_dir, self.photos_dir, self.modeles_dir, self.sauvegardes_dir, self.fichiers_dir):
            d.mkdir(parents=True, exist_ok=True)


config = Config()
