"""Modèle de données (SQLAlchemy 2). SQLite par défaut, PostgreSQL possible via MMT_DATABASE_URL."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import config


def maintenant() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(200), default="")
    mot_de_passe: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), default="utilisateur")
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


class SessionWeb(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    jeton_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    expire_le: Mapped[datetime] = mapped_column(DateTime)
    utilisateur: Mapped[Utilisateur] = relationship()


class Chantier(Base):
    __tablename__ = "chantiers"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(50), index=True)
    nom: Mapped[str] = mapped_column(String(200))
    client_nom: Mapped[str] = mapped_column(String(200), default="")
    client_tel: Mapped[str] = mapped_column(String(50), default="")
    client_email: Mapped[str] = mapped_column(String(200), default="")
    adresse: Mapped[str] = mapped_column(String(400), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    type_toiture: Mapped[str] = mapped_column(String(50), default="")
    statut: Mapped[str] = mapped_column(String(30), default="preparation", index=True)
    mode: Mapped[str] = mapped_column(String(20), default="3d")  # 3d | photo | saisie
    notes: Mapped[str] = mapped_column(Text, default="")
    preparation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan_vol: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analyse_photos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    modele: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    materiaux: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reserves: Mapped[str] = mapped_column(Text, default="")
    checklists: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("chantiers.id", ondelete="SET NULL"), nullable=True)
    archive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    cree_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant, onupdate=maintenant)


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(primary_key=True)
    chantier_id: Mapped[int] = mapped_column(ForeignKey("chantiers.id", ondelete="CASCADE"), index=True)
    nom_fichier: Mapped[str] = mapped_column(String(300))
    chemin: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    taille: Mapped[int] = mapped_column(Integer)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analyse: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exclue: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str] = mapped_column(String(20), default="photo")  # photo | gcp
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


class Traitement(Base):
    __tablename__ = "traitements"
    id: Mapped[int] = mapped_column(primary_key=True)
    chantier_id: Mapped[int] = mapped_column(ForeignKey("chantiers.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))  # reconstruction | detection
    statut: Mapped[str] = mapped_column(String(20), default="en_attente", index=True)
    etape: Mapped[str] = mapped_column(String(60), default="")
    progression: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    etat: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # état interne (reprise)
    resultats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    erreur: Mapped[str] = mapped_column(Text, default="")
    nb_images: Mapped[int] = mapped_column(Integer, default=0)
    duree_estimee_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    tentatives: Mapped[int] = mapped_column(Integer, default=0)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    debut: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fin: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    annulation_demandee: Mapped[bool] = mapped_column(Boolean, default=False)


class VersionMetre(Base):
    __tablename__ = "versions_metre"
    id: Mapped[int] = mapped_column(primary_key=True)
    chantier_id: Mapped[int] = mapped_column(ForeignKey("chantiers.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict] = mapped_column(JSON)
    resume: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    commentaire: Mapped[str] = mapped_column(Text, default="")
    auteur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


class Ouvrage(Base):
    __tablename__ = "ouvrages"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), default="")
    nom: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    donnees: Mapped[dict] = mapped_column(JSON)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant, onupdate=maintenant)


class Parametre(Base):
    __tablename__ = "parametres"
    cle: Mapped[str] = mapped_column(String(80), primary_key=True)
    valeur: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)


class Journal(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(primary_key=True)
    chantier_id: Mapped[int | None] = mapped_column(ForeignKey("chantiers.id", ondelete="CASCADE"),
                                                    index=True, nullable=True)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"),
                                                       nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text, default="")
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=maintenant)


_args = {"check_same_thread": False, "timeout": 30} if config.database_url.startswith("sqlite") else {}
engine = create_engine(config.database_url, connect_args=_args, pool_pre_ping=True)

if config.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    config.preparer()
    Base.metadata.create_all(engine)
    from .core.materiaux import MODELES_OUVRAGES
    with SessionLocal() as s:
        if not s.scalar(select(Ouvrage.id).limit(1)):
            for m in MODELES_OUVRAGES:
                s.add(Ouvrage(code=m["code"], nom=m["nom"], description=m.get("description", ""),
                              donnees={"parametres": m["parametres"], "articles": m["articles"]}))
            s.commit()


def get_db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def journaliser(s, action: str, detail: str = "", chantier_id: int | None = None, utilisateur_id: int | None = None):
    s.add(Journal(action=action, detail=detail, chantier_id=chantier_id, utilisateur_id=utilisateur_id))
