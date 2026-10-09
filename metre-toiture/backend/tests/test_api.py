"""Tests de bout en bout de l'API, y compris la chaîne de reconstruction avec un serveur
NodeODM simulé (le calcul photogrammétrique lui-même est testé à part, avec le vrai moteur)."""
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from mmt.db import SessionLocal, Traitement
from mmt.main import app
from mmt.services import traitements as tr

from synth import deux_pans

H = {"X-Requested-With": "mmt"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        r = c.post("/api/auth/initialiser", json={"email": "matt@example.fr", "nom": "Matt",
                                                  "mot_de_passe": "motdepasse-solide"})
        assert r.status_code == 200, r.text
        yield c


def _jpeg(lat, lon, couleur=(120, 90, 60), motif=0):
    im = Image.new("RGB", (640, 480), couleur)
    a = np.asarray(im).copy()
    rng = np.random.default_rng(motif)
    a[::8, :, :] = rng.integers(0, 255, (60, 640, 3))
    im = Image.fromarray(a)
    exif = Image.Exif()
    exif[0x010F] = "DJI"
    exif[0x0110] = "FC3582"
    gps = {1: "N", 2: (float(int(lat)), float(int((lat % 1) * 60)), ((lat * 3600) % 60)),
           3: "E", 4: (float(int(lon)), float(int((lon % 1) * 60)), ((lon * 3600) % 60)), 6: 120.0}
    exif[0x8825] = gps
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_securite(client):
    anon = TestClient(app)
    assert anon.get("/api/chantiers").status_code == 401
    # requête modifiante sans l'en-tête anti-CSRF
    r = client.post("/api/chantiers", json={"nom": "x"})
    assert r.status_code == 403
    assert client.post("/api/auth/initialiser", json={"email": "a@b.c", "mot_de_passe": "xxxxxxxxxxxx"}).status_code == 409
    assert anon.post("/api/auth/connexion", json={"email": "matt@example.fr", "mot_de_passe": "faux"}).status_code == 401
    # jeton d'API pour les intégrations (sans cookie, sans en-tête anti-CSRF)
    j = anon.post("/api/auth/connexion?mode=api", json={"email": "matt@example.fr", "mot_de_passe": "motdepasse-solide"}).json()
    api = TestClient(app)
    assert api.get("/api/chantiers", headers={"Authorization": f"Bearer {j['jeton']}"}).status_code == 200
    assert api.post("/api/chantiers", json={"nom": "via API"}, headers={"Authorization": f"Bearer {j['jeton']}"}).status_code == 200


def test_parcours_chantier(client):
    r = client.post("/api/chantiers", json={"nom": "Maison Dupont", "client_nom": "M. Dupont",
                                            "adresse": "1 rue des Tuiles", "type_toiture": "deux_pans"}, headers=H)
    assert r.status_code == 200
    c = r.json()
    cid = c["id"]
    assert c["reference"].startswith("MT-")
    # préparation
    plan = client.put(f"/api/chantiers/{cid}/preparation", json={"longueur": 10, "largeur": 8, "hauteur_faitage": 7,
                                                                "drone": "dji_mini_4_pro", "precision": "devis"},
                      headers=H).json()
    assert plan["total_photos"] > 20
    # import : 6 photos valides, un doublon exact, un fichier invalide
    fichiers = [("fichiers", (f"DJI_{i:04d}.JPG", _jpeg(48.7 + i * 1e-5, 2.3 + i * 1e-5, motif=i), "image/jpeg"))
                for i in range(6)]
    fichiers.append(("fichiers", ("DJI_0000_bis.JPG", fichiers[0][1][1], "image/jpeg")))
    fichiers.append(("fichiers", ("notes.pdf", b"%PDF-1.4", "application/pdf")))
    fichiers.append(("fichiers", ("casse.jpg", b"\xff\xd8\xff\xe0pas une image", "image/jpeg")))
    r = client.post(f"/api/chantiers/{cid}/photos", files=fichiers, headers=H)
    assert r.status_code == 200, r.text
    res = r.json()["resultats"]
    assert sum(1 for x in res if "erreur" not in x) == 6
    erreurs = [x["erreur"] for x in res if "erreur" in x]
    assert "Déjà importée" in erreurs and len(erreurs) == 3
    an = r.json()["analyse"]
    assert an["stats"]["avec_gps"] == 6
    assert an["verdict"] in ("insuffisant", "a_ameliorer")  # 6 photos : forcément insuffisant
    assert any(p["code"] == "peu_photos" for p in an["problemes"])

    # métré saisi
    doc = client.get(f"/api/chantiers/{cid}/metre").json()["document"]
    doc["echelle"] = {"facteur": 1, "source": "saisie", "references": []}
    doc["pans"] = [{"id": "p1", "nom": "Pan avant", "saisie": {"forme": "rectangle", "longueur_bas": 10,
                                                                "rampant": 5, "pente_deg": 37}, "valide": True}]
    doc["lignes_manuelles"] = [{"id": "l1", "type": "egout", "longueur": 10}]
    r = client.put(f"/api/chantiers/{cid}/metre", json={"document": doc, "commentaire": "Saisie"}, headers=H)
    assert r.status_code == 200
    t = r.json()
    assert t["calcul"]["totaux"]["surface_brute"] == pytest.approx(50)
    assert t["version"]["numero"] == 1
    # conflit de version
    r = client.put(f"/api/chantiers/{cid}/metre", json={"document": doc, "version_base": 0}, headers=H)
    assert r.status_code == 409
    # document invalide
    bad = dict(doc, pans=[{"id": "p1", "contour": [[0, "a"]]}])
    assert client.put(f"/api/chantiers/{cid}/metre", json={"document": bad}, headers=H).status_code == 400

    # matériaux
    ouv = client.get("/api/ouvrages").json()["ouvrages"]
    zing = next(o for o in ouv if o["code"] == "zinguerie_seule")
    for p in zing["parametres"]:
        p["valeur"] = {"entraxe_crochets": 0.5, "nb_descentes": 2, "hauteur_descente": 6}[p["cle"]]
    r = client.put(f"/api/chantiers/{cid}/materiaux", json={"selections": [{"ouvrage": zing}]}, headers=H)
    lignes = r.json()["resultat"]["lignes"]
    assert next(l for l in lignes if l["article"] == "Gouttière")["quantite_totale"] == pytest.approx(10)
    assert next(l for l in lignes if l["article"] == "Descentes EP")["quantite_totale"] == pytest.approx(12)

    # validation : confirmations puis validation
    client.put(f"/api/chantiers/{cid}/confirmations", json={"confirmations": {
        "obstacles_tous_saisis": True, "pentes_plausibles": True, "zones_cachees_traitees": True}}, headers=H)
    r = client.post(f"/api/chantiers/{cid}/valider", headers=H)
    assert r.status_code == 200 and r.json()["statut"] == "valide"

    # rapport et exports
    r = client.get(f"/api/chantiers/{cid}/rapport.pdf?prix=true")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    for fmt in ("json", "devis.json", "csv", "dxf", "obj"):
        r = client.get(f"/api/chantiers/{cid}/export/{fmt}")
        assert r.status_code == 200, fmt
    devis = client.get(f"/api/chantiers/{cid}/export/devis.json").json()
    assert devis["schema"] == "mmt-devis/1" and devis["metre"]["surface_nette_m2"] == pytest.approx(50)
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/chantiers/{cid}/export/csv").content))
    assert {"pans.csv", "lignes.csv", "materiaux.csv"} <= set(z.namelist())

    # duplication et versions
    d = client.post(f"/api/chantiers/{cid}/dupliquer", headers=H).json()
    assert d["parent_id"] == cid
    m2 = client.get(f"/api/chantiers/{d['id']}/metre").json()
    assert m2["calcul"]["totaux"]["surface_brute"] == pytest.approx(50)
    assert not m2["calcul"]["pans"][0]["valide"]
    doc["pans"][0]["saisie"]["rampant"] = 6
    client.put(f"/api/chantiers/{cid}/metre", json={"document": doc, "commentaire": "rampant 6"}, headers=H)
    assert client.get(f"/api/chantiers/{cid}").json()["statut"] == "a_verifier"  # validation à refaire
    r = client.post(f"/api/chantiers/{cid}/metre/versions/1/restaurer", headers=H).json()
    assert r["calcul"]["totaux"]["surface_brute"] == pytest.approx(50)
    assert len(client.get(f"/api/chantiers/{cid}/metre/versions").json()) == 3

    # archivage puis suppression définitive avec confirmation
    assert client.delete(f"/api/chantiers/{d['id']}", headers=H).json()["archive"]
    assert client.delete(f"/api/chantiers/{d['id']}?definitif=true&confirmation=faux", headers=H).status_code == 400
    ref = d["reference"]
    assert client.delete(f"/api/chantiers/{d['id']}?definitif=true&confirmation={ref}", headers=H).json()["supprime"]
    tb = client.get("/api/tableau-de-bord").json()
    assert tb["termines"] >= 0 and tb["total"] >= 1


def _zip_odm(tmp: Path) -> Path:
    """Archive « all.zip » minimale au format ODM : MNS GeoTIFF (UTM 31N) d'un toit à deux pans."""
    import rasterio
    from rasterio.transform import from_origin

    g = deux_pans(bruit=0.01)
    e0, n0 = 450000.0, 5400000.0
    tif = tmp / "dsm.tif"
    with rasterio.open(tif, "w", driver="GTiff", width=g.z.shape[1], height=g.z.shape[0], count=1,
                       dtype="float32", crs="EPSG:32631", nodata=-9999,
                       transform=from_origin(e0 + g.x0, n0 + g.y0, g.res, g.res)) as ds:
        ds.write(g.z.astype("float32"), 1)
    z = tmp / "all.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(tif, "odm_dem/dsm.tif")
        zf.writestr("odm_report/report.pdf", b"%PDF-1.4 rapport")
    return z


class FauxNodeODM:
    def __init__(self, archive):
        self.archive = archive
        self.envoyees = 0
        self.etats = [{"status": {"code": 10}, "options": [{"name": "dsm", "value": True}]},
                      {"status": {"code": 20}, "progress": 40}, {"status": {"code": 40}, "progress": 100,
                                                                   "processingTime": 120000}]

    def info(self):
        return {"version": "faux"}

    def creer(self, nom, options, sorties):
        assert options["dsm"] is True
        return "uuid-test"

    def envoyer(self, uuid, fichiers):
        self.envoyees += len(fichiers)

    def valider(self, uuid):
        pass

    def etat(self, uuid):
        return self.etats.pop(0)

    def telecharger(self, uuid, dest, progression=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.archive.read_bytes())
        return dest

    def supprimer(self, uuid):
        pass

    def annuler(self, uuid):
        pass


def test_reconstruction_simulee(client, tmp_path, monkeypatch):
    cid = client.post("/api/chantiers", json={"nom": "Reconstruction"}, headers=H).json()["id"]
    fichiers = [("fichiers", (f"IMG_{i}.JPG", _jpeg(48.7 + i * 1e-5, 2.3, motif=100 + i), "image/jpeg"))
                for i in range(6)]
    client.post(f"/api/chantiers/{cid}/photos", files=fichiers, headers=H)
    faux = FauxNodeODM(_zip_odm(tmp_path))
    monkeypatch.setattr(tr, "client_odm", lambda db: faux)
    t = client.post(f"/api/chantiers/{cid}/reconstruction", json={"preset": "devis"}, headers=H).json()
    assert t["statut"] == "en_attente" and t["duree_estimee_s"] > 0
    assert client.post(f"/api/chantiers/{cid}/reconstruction", json={"preset": "devis"}, headers=H).status_code == 409
    for _ in range(6):
        with SessionLocal() as db:
            job = db.get(Traitement, t["id"])
            if job.statut == "termine":
                break
            tr.avancer_reconstruction(db, job)
    t = client.get(f"/api/traitements/{t['id']}").json()
    assert t["statut"] == "termine", t
    assert faux.envoyees == 6
    assert t["resultats"]["detection"]["nb_pans"] == 2
    ch = client.get(f"/api/chantiers/{cid}").json()
    assert ch["statut"] == "a_verifier" and ch["modele"]["epsg"] == 32631
    m = client.get(f"/api/chantiers/{cid}/metre").json()
    attendu = 10 * 8 / math.cos(math.radians(35))
    assert m["calcul"]["totaux"]["surface_brute"] == pytest.approx(attendu, rel=0.01)
    assert m["document"]["auto"]["pans"]
    assert m["calcul"]["echelle"]["source"] == "gps"
    assert m["calcul"]["obstacles"] == []
    # fond de plan (ombrage du MNS, pas d'orthophoto) et export géoréférencé
    r = client.get(f"/api/chantiers/{cid}/fond?quoi=mns&max_px=400")
    assert r.status_code == 200 and r.headers["x-bornes"]
    gj = client.get(f"/api/chantiers/{cid}/export/geojson").json()
    lon, lat = gj["features"][0]["geometry"]["coordinates"][0][0]
    assert 2.0 < lon < 4.0 and 48.0 < lat < 49.5   # UTM 31N, E=450 km, N=5400 km
    # réajustement d'un plan sur un contour dessiné à la main (pan sud : y de -4 à 0)
    r = client.post(f"/api/chantiers/{cid}/ajuster-plan", json={"contour": [[-4, -3.5], [4, -3.5], [4, -0.5], [-4, -0.5]]},
                    headers=H).json()
    assert math.degrees(math.atan(math.hypot(r["plan"]["a"], r["plan"]["b"]))) == pytest.approx(35, abs=0.5)
    assert r["stats"]["rms"] < 0.03
    # nouvelle détection ciblée (traitement asynchrone)
    d = client.post(f"/api/chantiers/{cid}/detection", json={"graine": [0, 0]}, headers=H).json()
    with SessionLocal() as db:
        tr.executer_job_detection(db, db.get(Traitement, d["id"]))
    assert client.get(f"/api/traitements/{d['id']}").json()["statut"] == "termine"
    assert len(client.get(f"/api/chantiers/{cid}/metre/versions").json()) == 2


def test_photo_unique(client):
    cid = client.post("/api/chantiers", json={"nom": "Photo unique", "mode": "photo"}, headers=H).json()["id"]
    r = client.post(f"/api/chantiers/{cid}/photos",
                    files=[("fichiers", ("nadir.jpg", _jpeg(48.7, 2.3), "image/jpeg"))], headers=H).json()
    pid = r["resultats"][0]["id"]
    # métadonnées sans altitude relative : il faut la fournir
    assert client.post(f"/api/chantiers/{cid}/photo-unique", json={"photo_id": pid, "hauteur_toit": 7},
                       headers=H).status_code == 400
    m = client.post(f"/api/chantiers/{cid}/photo-unique",
                    json={"photo_id": pid, "hauteur_toit": 7, "altitude": 37, "focale_35mm": 24}, headers=H).json()
    diag = math.hypot(640, 480)
    assert m["gsd_m"] == pytest.approx(30 * 43.2666 / (24 * diag))
    assert any("verticale" in a for a in m["avertissements"])
    doc = client.get(f"/api/chantiers/{cid}/metre").json()["document"]
    assert doc["echelle"]["source"] == "photo_exif"
    r = client.get(f"/api/chantiers/{cid}/fond")
    assert r.status_code == 200


def test_sauvegarde(client):
    r = client.post("/api/sauvegardes?complete=false", headers=H)
    assert r.status_code == 200
    nom = r.json()["nom"]
    assert any(s["nom"] == nom for s in client.get("/api/sauvegardes").json())
    assert client.get("/api/sauvegardes/../mmt.db").status_code == 404
    assert client.get(f"/api/sauvegardes/{nom}").status_code == 200


def test_parametres(client):
    r = client.put("/api/parametres/entreprise", json={"nom": "Matt's Couverture", "siret": "123"}, headers=H)
    assert r.status_code == 200
    assert client.get("/api/parametres").json()["entreprise"]["nom"] == "Matt's Couverture"
    assert client.put("/api/parametres/calcul", json={"nodeodm_url": "ftp://x"}, headers=H).status_code == 400
    r = client.post("/api/parametres/calcul/tester", json={"nodeodm_url": "http://127.0.0.1:9"}, headers=H).json()
    assert r["ok"] is False
    json.dumps(r)
