"""Sauvegardes : base de données (copie cohérente) + photos + modèles, archive datée avec rotation."""
from __future__ import annotations

import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path

from ..config import config


def creer_sauvegarde(inclure_fichiers: bool = True) -> Path:
    config.preparer()
    horo = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = config.sauvegardes_dir / f"mmt-{horo}.tar.gz"
    tmp_db = config.sauvegardes_dir / f"mmt-{horo}.db"
    if config.database_url.startswith("sqlite"):
        src = sqlite3.connect(config.database_url.replace("sqlite:///", ""))
        dst = sqlite3.connect(tmp_db)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    with tarfile.open(dest, "w:gz") as tar:
        if tmp_db.exists():
            tar.add(tmp_db, arcname="mmt.db")
        if inclure_fichiers:
            for d in (config.photos_dir, config.modeles_dir, config.fichiers_dir):
                if d.exists():
                    tar.add(d, arcname=d.name)
    tmp_db.unlink(missing_ok=True)
    rotation()
    return dest


def lister() -> list[dict]:
    out = []
    for f in sorted(config.sauvegardes_dir.glob("mmt-*.tar.gz"), reverse=True):
        st = f.stat()
        out.append({"nom": f.name, "taille": st.st_size, "date": datetime.fromtimestamp(st.st_mtime).isoformat()})
    return out


def rotation() -> None:
    fichiers = sorted(config.sauvegardes_dir.glob("mmt-*.tar.gz"), reverse=True)
    for f in fichiers[config.sauvegardes_a_garder:]:
        f.unlink(missing_ok=True)


def sauvegarde_quotidienne() -> Path | None:
    today = datetime.now().strftime("%Y%m%d")
    if any(f.name.startswith(f"mmt-{today}") for f in config.sauvegardes_dir.glob("mmt-*.tar.gz")):
        return None
    # sauvegarde quotidienne légère : base seule (les photos sont volumineuses et immuables)
    return creer_sauvegarde(inclure_fichiers=False)
