from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import config
from ..core import materiaux as mat
from ..core import metre as metre_core
from ..core import validation as val
from ..core.geometry import TYPES_LIGNES
from ..db import Chantier, Ouvrage, Photo, Traitement, Utilisateur, VersionMetre, get_db, journaliser
from ..securite import utilisateur_courant
from ..services import exports as exp
from ..services import modele as mod
from ..services import rapport as rap
from ..services.traitements import dossier_modele, enregistrer_version, version_courante
from .commun import chantier_dict, chantier_ou_404, parametre

router = APIRouter(prefix="/api", tags=["metre"])


def _document(db: Session, c: Chantier) -> tuple[dict, VersionMetre | None]:
    v = version_courante(db, c.id)
    if v:
        return v.document, v
    doc = metre_core.document_vide()
    if c.mode == "photo" and c.modele:
        doc["echelle"]["source"] = "photo_exif"
        doc["repere"] = {"type": "photo", "source": "photo", "rotation_deg": c.modele.get("rotation_deg", 0)}
    elif c.mode == "saisie":
        doc["echelle"]["source"] = "saisie"
    elif c.modele and c.modele.get("type") == "odm":
        doc["echelle"]["source"] = "gps"
    return doc, None


def _contexte(db: Session, c: Chantier) -> dict:
    rec = None
    type_modele = (c.modele or {}).get("type")
    mode = "3d" if type_modele == "odm" else ("photo" if type_modele == "photo" else "saisie")
    if c.mode == "3d":
        t = db.scalar(select(Traitement).where(Traitement.chantier_id == c.id, Traitement.type == "reconstruction")
                      .order_by(Traitement.id.desc()).limit(1))
        rec = "ok" if (c.modele and c.modele.get("type") == "odm") else ("echec" if t and t.statut == "erreur" else None)
    return {"mode": mode, "reconstruction": rec,
            "analyse_photos": (c.analyse_photos or {}).get("verdict")}


def _tout(db: Session, c: Chantier) -> dict:
    doc, v = _document(db, c)
    calc = metre_core.calculer(doc)
    validation = val.checklist(calc, _contexte(db, c), c.confirmations or {})
    return {"document": doc, "calcul": calc, "validation": validation,
            "version": {"numero": v.numero, "date": v.cree_le.isoformat(), "commentaire": v.commentaire} if v else None,
            "types_lignes": TYPES_LIGNES, "types_obstacles": metre_core.TYPES_OBSTACLES,
            "confirmations_libelles": val.CONFIRMATIONS}


@router.get("/chantiers/{cid}/metre")
def lire(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    return _tout(db, chantier_ou_404(db, cid))


class Sauvegarde(BaseModel):
    document: dict
    commentaire: str = ""
    version_base: int | None = None


def _verifier_document(doc: dict) -> None:
    if not isinstance(doc.get("pans"), list):
        raise HTTPException(400, "Document de métré invalide")
    ids = [p.get("id") for p in doc["pans"]]
    if len(ids) != len(set(ids)) or any(not i for i in ids):
        raise HTTPException(400, "Identifiants de pans invalides ou en double")
    for p in doc["pans"]:
        if p.get("contour") is not None:
            if not isinstance(p["contour"], list) or len(p["contour"]) > 500:
                raise HTTPException(400, "Contour invalide")
            for pt in p["contour"]:
                if not (isinstance(pt, list) and len(pt) == 2 and all(isinstance(v, (int, float)) for v in pt)):
                    raise HTTPException(400, "Coordonnées de contour invalides")
    if len(json.dumps(doc)) > 5_000_000:
        raise HTTPException(400, "Document trop volumineux")


@router.put("/chantiers/{cid}/metre")
def enregistrer(cid: int, d: Sauvegarde, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    _verifier_document(d.document)
    cour = version_courante(db, cid)
    if d.version_base is not None and cour and cour.numero != d.version_base:
        raise HTTPException(409, f"Le métré a été modifié entre-temps (version {cour.numero}). Rechargez la page.")
    enregistrer_version(db, cid, d.document, d.commentaire or "Modification", u.id)
    if c.statut in ("preparation", "photos", "traitement"):
        c.statut = "a_verifier"
    if c.statut == "valide":
        c.statut = "a_verifier"   # toute modification après validation impose une nouvelle validation
    journaliser(db, "metre_modifie", d.commentaire, cid, u.id)
    db.commit()
    return _tout(db, c)


@router.post("/chantiers/{cid}/metre/calculer")
def simuler(cid: int, d: Sauvegarde, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    """Calcul sans enregistrement (aperçu en direct pendant l'édition)."""
    c = chantier_ou_404(db, cid)
    _verifier_document(d.document)
    calc = metre_core.calculer(d.document)
    return {"calcul": calc, "validation": val.checklist(calc, _contexte(db, c), c.confirmations or {})}


@router.get("/chantiers/{cid}/metre/versions")
def versions(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    vs = db.scalars(select(VersionMetre).where(VersionMetre.chantier_id == cid)
                    .order_by(VersionMetre.numero.desc())).all()
    noms = {u.id: u.nom or u.email for u in db.scalars(select(Utilisateur)).all()}
    return [{"numero": v.numero, "date": v.cree_le.isoformat(), "commentaire": v.commentaire, "resume": v.resume,
             "auteur": noms.get(v.auteur_id, "Automatique" if v.auteur_id is None else "?")} for v in vs]


@router.post("/chantiers/{cid}/metre/versions/{numero}/restaurer")
def restaurer(cid: int, numero: int, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    v = db.scalar(select(VersionMetre).where(VersionMetre.chantier_id == cid, VersionMetre.numero == numero))
    if not v:
        raise HTTPException(404, "Version introuvable")
    enregistrer_version(db, cid, v.document, f"Restauration de la version {numero}", u.id)
    c.statut = "a_verifier"
    db.commit()
    return _tout(db, c)


class Confirmations(BaseModel):
    confirmations: dict


@router.put("/chantiers/{cid}/confirmations")
def confirmations(cid: int, d: Confirmations, u: Utilisateur = Depends(utilisateur_courant),
                  db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    c.confirmations = {k: bool(v) for k, v in d.confirmations.items() if k in val.CONFIRMATIONS}
    db.commit()
    return _tout(db, c)["validation"]


@router.post("/chantiers/{cid}/valider")
def valider(cid: int, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    t = _tout(db, c)
    if not t["validation"]["pret_pour_devis"]:
        raise HTTPException(400, "Des points bloquants empêchent la validation : consultez la checklist.")
    c.statut = "valide"
    journaliser(db, "metre_valide", f"{t['calcul']['totaux']['surface_nette']:.2f} m²", cid, u.id)
    db.commit()
    return chantier_dict(c)


# ---------------------------------------------------------------------------
# Matériaux
def _ouvrage_dict(o: Ouvrage) -> dict:
    return {"id": o.id, "code": o.code, "nom": o.nom, "description": o.description, **o.donnees}


@router.get("/ouvrages")
def ouvrages(_: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    return {"ouvrages": [_ouvrage_dict(o) for o in db.scalars(select(Ouvrage).order_by(Ouvrage.nom)).all()],
            "bases": mat.BASES}


class OuvrageIn(BaseModel):
    nom: str
    code: str = ""
    description: str = ""
    parametres: list[dict] = []
    articles: list[dict] = []


def _verifier_ouvrage(d: OuvrageIn):
    for a in d.articles:
        if a.get("base") not in mat.BASES:
            raise HTTPException(400, f"Base de calcul inconnue pour « {a.get('nom')} »")
    cles = [p.get("cle") for p in d.parametres]
    if any(not c or not str(c).isidentifier() for c in cles):
        raise HTTPException(400, "Les clés de paramètres doivent être des identifiants simples (lettres, _)")


@router.post("/ouvrages")
def creer_ouvrage(d: OuvrageIn, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    _verifier_ouvrage(d)
    o = Ouvrage(nom=d.nom, code=d.code, description=d.description,
                donnees={"parametres": d.parametres, "articles": d.articles})
    db.add(o)
    db.commit()
    return _ouvrage_dict(o)


@router.put("/ouvrages/{oid}")
def maj_ouvrage(oid: int, d: OuvrageIn, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    o = db.get(Ouvrage, oid)
    if not o:
        raise HTTPException(404, "Ouvrage introuvable")
    _verifier_ouvrage(d)
    o.nom, o.code, o.description = d.nom, d.code, d.description
    o.donnees = {"parametres": d.parametres, "articles": d.articles}
    db.commit()
    return _ouvrage_dict(o)


@router.delete("/ouvrages/{oid}")
def suppr_ouvrage(oid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    o = db.get(Ouvrage, oid)
    if o:
        db.delete(o)
        db.commit()
    return {"ok": True}


class Selections(BaseModel):
    selections: list[dict]


def _materiaux(c: Chantier, calc: dict) -> dict | None:
    if not c.materiaux:
        return None
    return mat.calculer(calc, c.materiaux)


@router.get("/chantiers/{cid}/materiaux")
def lire_materiaux(cid: int, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    doc, _v = _document(db, c)
    calc = metre_core.calculer(doc)
    return {"selections": c.materiaux or [], "resultat": _materiaux(c, calc)}


@router.put("/chantiers/{cid}/materiaux")
def maj_materiaux(cid: int, d: Selections, u: Utilisateur = Depends(utilisateur_courant),
                  db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    for s in d.selections:
        if "ouvrage" not in s:
            raise HTTPException(400, "Sélection invalide")
    c.materiaux = d.selections
    journaliser(db, "materiaux", f"{len(d.selections)} ouvrage(s)", cid, u.id)
    db.commit()
    return lire_materiaux(cid, u, db)


# ---------------------------------------------------------------------------
# Rapports et exports
def _contexte_rapport(db: Session, c: Chantier):
    t = _tout(db, c)
    ch = chantier_dict(c, True)
    ch["nb_photos"] = db.scalar(select(func.count(Photo.id)).where(Photo.chantier_id == c.id, Photo.exclue == False,  # noqa
                                                                   Photo.type == "photo"))
    ch["res_mns"] = (c.modele or {}).get("res_mns")
    return t, ch


@router.get("/chantiers/{cid}/rapport.pdf")
def rapport(cid: int, materiaux: bool = True, prix: bool = False, fond: bool = True,
            u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    t, ch = _contexte_rapport(db, c)
    entreprise = parametre(db, "entreprise", {}) or {}
    fond_ortho = None
    tmp = None
    pans = [p for p in t["document"].get("pans", []) if p.get("contour")]
    if fond and pans and c.modele and c.modele.get("type") == "odm" and c.modele.get("ortho"):
        xs = [pt[0] for p in pans for pt in p["contour"]]
        ys = [pt[1] for p in pans for pt in p["contour"]]
        m = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1)
        try:
            img, bornes, _m = mod.image_recadree(dossier_modele(cid), "ortho",
                                                 (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m), 1600)
            tmp, b = rap.fond_temporaire(img, bornes)
            fond_ortho = (tmp, b)
        except Exception:
            fond_ortho = None
    logo = config.fichiers_dir / "logo.png"
    try:
        pdf = rap.generer(ch, entreprise, t["document"], t["calcul"], t["validation"],
                          _materiaux(c, t["calcul"]), c.analyse_photos, {"materiaux": materiaux, "prix": prix},
                          fond_ortho, logo if logo.exists() else None)
    finally:
        if tmp:
            os.unlink(tmp)
    journaliser(db, "rapport_pdf", "", cid, u.id)
    db.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="metre_{c.reference}.pdf"'})


@router.get("/chantiers/{cid}/export/{fmt}")
def exporter(cid: int, fmt: str, _: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    c = chantier_ou_404(db, cid)
    t, ch = _contexte_rapport(db, c)
    calc, doc = t["calcul"], t["document"]
    materiaux = _materiaux(c, calc)
    nom = f"metre_{c.reference}"
    if fmt == "json":
        data = json.dumps({"chantier": ch, "document": doc, "calcul": calc, "materiaux": materiaux,
                           "validation": t["validation"]}, ensure_ascii=False, indent=1, default=str).encode()
        return Response(data, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{nom}.json"'})
    if fmt == "devis.json":
        data = exp.export_devis({k: ch[k] for k in ("id", "reference", "nom", "client_nom", "client_tel",
                                                     "client_email", "adresse", "type_toiture")},
                                calc, materiaux, t["validation"])
        return Response(json.dumps(data, ensure_ascii=False, indent=1).encode(), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{nom}_devis.json"'})
    if fmt == "csv":
        return Response(exp.export_csv(calc, materiaux), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{nom}_csv.zip"'})
    if fmt == "dxf":
        return Response(exp.export_dxf(doc, calc), media_type="application/dxf",
                        headers={"Content-Disposition": f'attachment; filename="{nom}.dxf"'})
    if fmt == "obj":
        return Response(exp.export_obj(doc, calc), media_type="text/plain",
                        headers={"Content-Disposition": f'attachment; filename="{nom}.obj"'})
    if fmt == "geojson":
        if not c.modele or c.modele.get("type") != "odm" or not c.modele.get("epsg"):
            raise HTTPException(400, "Export GeoJSON disponible uniquement pour un modèle 3D géoréférencé")
        info = mod.lire_info(dossier_modele(cid))
        return Response(exp.export_geojson(doc, calc, info), media_type="application/geo+json",
                        headers={"Content-Disposition": f'attachment; filename="{nom}.geojson"'})
    raise HTTPException(404, "Format inconnu")
