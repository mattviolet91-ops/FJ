"""Client de l'API NodeODM (OpenDroneMap).

Compatible avec un NodeODM local (Docker), un serveur distant, ClusterODM, ou tout service
exposant la même API (ex. WebODM Lightning, avec jeton).
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

QUEUED, RUNNING, FAILED, COMPLETED, CANCELED = 10, 20, 30, 40, 50
LIBELLES = {QUEUED: "En file d'attente", RUNNING: "Calcul en cours", FAILED: "Échec",
            COMPLETED: "Terminé", CANCELED: "Annulé"}

# Fichiers utiles au métré (réduit fortement la taille de l'archive téléchargée)
SORTIES = [
    "odm_orthophoto/odm_orthophoto.tif",
    "odm_dem/dsm.tif",
    "odm_dem/dtm.tif",
    "odm_georeferencing",
    "odm_report",
    "images.json",
    "cameras.json",
    "task_output.txt",
    "log.json",
]

PRESETS = {
    "apercu": {
        "libelle": "Aperçu rapide",
        "description": "Calcul allégé pour vérifier la couverture photo. Ne pas utiliser pour un devis.",
        "options": {"dsm": True, "dem-resolution": 8, "orthophoto-resolution": 4, "pc-quality": "low",
                    "feature-quality": "medium", "auto-boundary": True, "skip-3dmodel": True},
        "facteur_temps": 0.45,
    },
    "devis": {
        "libelle": "Métré pour devis (recommandé)",
        "description": "Bon compromis précision / temps de calcul.",
        "options": {"dsm": True, "dem-resolution": 4, "orthophoto-resolution": 2, "pc-quality": "high",
                    "feature-quality": "high", "auto-boundary": True, "skip-3dmodel": True},
        "facteur_temps": 1.0,
    },
    "precis": {
        "libelle": "Haute précision",
        "description": "Pour toitures complexes ou grandes surfaces. Calcul nettement plus long.",
        "options": {"dsm": True, "dem-resolution": 2.5, "orthophoto-resolution": 1.5, "pc-quality": "ultra",
                    "feature-quality": "ultra", "auto-boundary": True, "skip-3dmodel": True,
                    "use-3dmesh": False},
        "facteur_temps": 2.6,
    },
}


class ErreurNodeODM(Exception):
    pass


class ClientNodeODM:
    def __init__(self, url: str, jeton: str = "", timeout: float = 60.0):
        self.url = url.rstrip("/")
        self.jeton = jeton
        self.timeout = timeout

    def _p(self, extra: dict | None = None) -> dict:
        p = dict(extra or {})
        if self.jeton:
            p["token"] = self.jeton
        return p

    def _req(self, methode: str, chemin: str, **kw):
        try:
            with httpx.Client(timeout=kw.pop("timeout", self.timeout)) as c:
                r = c.request(methode, self.url + chemin, params=self._p(kw.pop("params", None)), **kw)
        except httpx.HTTPError as e:
            raise ErreurNodeODM(f"Serveur de calcul injoignable ({self.url}) : {e}") from e
        if r.status_code >= 400:
            raise ErreurNodeODM(f"Erreur du serveur de calcul ({r.status_code}) : {r.text[:300]}")
        try:
            d = r.json()
        except ValueError:
            return r.text
        if isinstance(d, dict) and d.get("error"):
            raise ErreurNodeODM(str(d["error"]))
        return d

    def info(self) -> dict:
        return self._req("GET", "/info", timeout=10)

    def creer(self, nom: str, options: dict, sorties: list[str] | None = None) -> str:
        opts = [{"name": k, "value": v} for k, v in options.items()]
        data = {"name": nom, "options": json.dumps(opts)}
        if sorties:
            data["outputs"] = json.dumps(sorties)
        d = self._req("POST", "/task/new/init", data=data)
        return d["uuid"]

    def envoyer(self, uuid: str, fichiers: list[Path]) -> None:
        handles = [("images", (f.name, open(f, "rb"), "application/octet-stream")) for f in fichiers]
        try:
            self._req("POST", f"/task/new/upload/{uuid}", files=handles, timeout=600)
        finally:
            for _, (_, fh, _) in handles:
                fh.close()

    def valider(self, uuid: str) -> None:
        self._req("POST", f"/task/new/commit/{uuid}")

    def etat(self, uuid: str) -> dict:
        return self._req("GET", f"/task/{uuid}/info")

    def journal(self, uuid: str, lignes: int = 40) -> str:
        d = self._req("GET", f"/task/{uuid}/output", params={"line": -lignes})
        return "\n".join(d) if isinstance(d, list) else str(d)

    def annuler(self, uuid: str) -> None:
        self._req("POST", "/task/cancel", data={"uuid": uuid})

    def supprimer(self, uuid: str) -> None:
        self._req("POST", "/task/remove", data={"uuid": uuid})

    def telecharger(self, uuid: str, dest: Path, progression=None) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        try:
            with httpx.Client(timeout=httpx.Timeout(60, read=600)) as c:
                with c.stream("GET", f"{self.url}/task/{uuid}/download/all.zip", params=self._p()) as r:
                    if r.status_code >= 400:
                        raise ErreurNodeODM(f"Téléchargement impossible ({r.status_code})")
                    total = int(r.headers.get("content-length") or 0)
                    recu = 0
                    with open(tmp, "wb") as f:
                        for bloc in r.iter_bytes(1 << 20):
                            f.write(bloc)
                            recu += len(bloc)
                            if progression and total:
                                progression(recu / total)
        except httpx.HTTPError as e:
            raise ErreurNodeODM(f"Téléchargement interrompu : {e}") from e
        tmp.replace(dest)
        return dest
