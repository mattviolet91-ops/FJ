from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.plan_vol import TYPES_TOITURE
from ..db import Chantier, Parametre

STATUTS = {
    "preparation": "Préparation",
    "photos": "Photos importées",
    "traitement": "Traitement en cours",
    "a_verifier": "Métré à vérifier",
    "valide": "Métré validé",
    "termine": "Terminé",
}


def chantier_ou_404(db: Session, cid: int) -> Chantier:
    c = db.get(Chantier, cid)
    if not c:
        raise HTTPException(404, "Chantier introuvable")
    return c


def chantier_dict(c: Chantier, complet: bool = False) -> dict:
    d = {
        "id": c.id, "reference": c.reference, "nom": c.nom, "client_nom": c.client_nom, "client_tel": c.client_tel,
        "client_email": c.client_email, "adresse": c.adresse, "lat": c.lat, "lon": c.lon,
        "type_toiture": c.type_toiture, "type_toiture_libelle": TYPES_TOITURE.get(c.type_toiture, ""),
        "statut": c.statut, "statut_libelle": STATUTS.get(c.statut, c.statut), "mode": c.mode,
        "archive": c.archive, "parent_id": c.parent_id,
        "cree_le": c.cree_le.isoformat() if c.cree_le else None,
        "modifie_le": c.modifie_le.isoformat() if c.modifie_le else None,
    }
    if complet:
        d.update({"notes": c.notes, "preparation": c.preparation, "plan_vol": c.plan_vol,
                  "analyse_photos": c.analyse_photos, "modele": c.modele, "confirmations": c.confirmations or {},
                  "reserves": c.reserves, "checklists": c.checklists or {}})
    return d


def parametre(db: Session, cle: str, defaut=None):
    p = db.get(Parametre, cle)
    return p.valeur if p and p.valeur is not None else defaut


def definir_parametre(db: Session, cle: str, valeur) -> None:
    p = db.get(Parametre, cle)
    if p:
        p.valeur = valeur
    else:
        db.add(Parametre(cle=cle, valeur=valeur))
