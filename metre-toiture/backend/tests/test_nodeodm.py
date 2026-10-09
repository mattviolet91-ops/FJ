"""Client NodeODM : format des requêtes attendu par le vrai serveur."""
import json

import httpx

from mmt.services.nodeodm import ClientNodeODM


def test_init_en_multipart():
    recu = {}

    def gestion(req: httpx.Request):
        recu["type"] = req.headers.get("content-type", "")
        recu["corps"] = req.read().decode()
        recu["chemin"] = req.url.path
        recu["jeton"] = req.url.params.get("token")
        return httpx.Response(200, json={"uuid": "abc"})

    cli = ClientNodeODM("http://odm:3000", "secret", transport=httpx.MockTransport(gestion))
    assert cli.creer("MMT-test", {"dsm": True, "dem-resolution": 4}, ["odm_dem/dsm.tif"]) == "abc"
    assert recu["chemin"] == "/task/new/init" and recu["jeton"] == "secret"
    # NodeODM (multer) ignore les champs d'un formulaire urlencodé : le multipart est indispensable
    assert recu["type"].startswith("multipart/form-data")
    assert 'name="options"' in recu["corps"] and 'name="name"' in recu["corps"]
    opts = json.loads(recu["corps"].split('name="options"')[1].split("\r\n\r\n", 1)[1].split("\r\n--")[0])
    assert {"name": "dsm", "value": True} in opts


def test_erreur_lisible():
    cli = ClientNodeODM("http://odm:3000", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"error": "Token invalide"})))
    try:
        cli.info()
    except Exception as e:
        assert "Token invalide" in str(e)
    else:
        raise AssertionError("erreur attendue")
