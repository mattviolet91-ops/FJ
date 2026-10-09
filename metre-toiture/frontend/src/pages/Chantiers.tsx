import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, dateFr, fr } from "../api";
import { Badge, Chargement, Icone, useToast } from "../components/ui";
import type { Chantier } from "../types";

const VUES: Record<string, { titre: string; statut?: string; archives?: boolean }> = {
  en_cours: { titre: "Chantiers en cours", statut: "preparation,photos,traitement,a_verifier" },
  a_verifier: { titre: "Métrés à vérifier", statut: "a_verifier" },
  termines: { titre: "Chantiers terminés", statut: "valide,termine" },
  tous: { titre: "Tous les chantiers" },
  archives: { titre: "Chantiers archivés", archives: true },
};

export function ListeChantiers() {
  const [params, setParams] = useSearchParams();
  const vue = params.get("vue") || "en_cours";
  const conf = VUES[vue] || VUES.en_cours;
  const [q, setQ] = useState("");
  const [liste, setListe] = useState<Chantier[] | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    setListe(null);
    const p = new URLSearchParams();
    if (conf.statut) p.set("statut", conf.statut);
    if (conf.archives) p.set("archives", "true");
    if (q) p.set("q", q);
    const t = setTimeout(() => api.get<Chantier[]>(`/api/chantiers?${p}`).then(setListe), q ? 250 : 0);
    return () => clearTimeout(t);
  }, [vue, q]); // eslint-disable-line

  return (
    <>
      <div className="entete-page">
        <h1>{conf.titre}</h1>
        <div className="actions"><Link to="/chantiers/nouveau" className="btn primaire"><Icone nom="plus" /> Nouveau chantier</Link></div>
      </div>
      <div className="ligne" style={{ marginBottom: 12 }}>
        {Object.entries(VUES).map(([k, v]) => (
          <button key={k} className={`btn petit ${k === vue ? "actif" : ""}`} onClick={() => setParams({ vue: k })}>{v.titre.replace("Chantiers ", "").replace("Tous les chantiers", "Tous")}</button>
        ))}
        <span className="espace" />
        <input placeholder="Rechercher (nom, client, adresse, référence)" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 340 }} />
      </div>
      <div className="carte">
        {!liste ? <Chargement /> : liste.length === 0 ? <div className="vide">Aucun chantier.</div> : (
          <div className="defile-x">
            <table className="tableau">
              <thead><tr><th>Référence</th><th>Chantier</th><th className="masque-mobile">Client</th><th className="masque-mobile">Adresse</th>
                <th className="num">Surface</th><th>Statut</th><th className="masque-mobile">Modifié</th></tr></thead>
              <tbody>
                {liste.map((c) => (
                  <tr key={c.id} className="cliquable" onClick={() => nav(`/chantiers/${c.id}`)}>
                    <td><Link to={`/chantiers/${c.id}`}>{c.reference}</Link></td>
                    <td>{c.nom}</td>
                    <td className="masque-mobile">{c.client_nom || "—"}</td>
                    <td className="masque-mobile">{c.adresse || "—"}</td>
                    <td className="num">{c.resume_metre ? `${fr(c.resume_metre.surface, 1)} m²` : "—"}</td>
                    <td><Badge statut={c.statut}>{c.statut_libelle}</Badge></td>
                    <td className="masque-mobile">{dateFr(c.modifie_le)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

export function NouveauChantier() {
  const [f, setF] = useState({ nom: "", client_nom: "", client_tel: "", client_email: "", adresse: "", type_toiture: "", mode: "3d" });
  const [types, setTypes] = useState<Record<string, string>>({});
  const [gps, setGps] = useState<{ lat: number; lon: number } | null>(null);
  const [encours, setEncours] = useState(false);
  const toast = useToast();
  const nav = useNavigate();
  useEffect(() => {
    api.get<{ types_toiture: Record<string, string> }>("/api/plan-vol/referentiel").then((d) => setTypes(d.types_toiture));
  }, []);
  const maj = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  const localiser = () => {
    if (!navigator.geolocation) return toast("Géolocalisation indisponible sur cet appareil", "erreur");
    navigator.geolocation.getCurrentPosition(
      (p) => { setGps({ lat: p.coords.latitude, lon: p.coords.longitude }); toast("Position enregistrée", "ok"); },
      () => toast("Position refusée ou indisponible", "erreur"), { enableHighAccuracy: true, timeout: 15000 });
  };
  const envoyer = async (e: FormEvent) => {
    e.preventDefault();
    setEncours(true);
    try {
      const c = await api.post<Chantier>("/api/chantiers", { ...f, ...(gps || {}) });
      nav(`/chantiers/${c.id}/${f.mode === "saisie" ? "metre" : "preparation"}`);
    } catch (err) {
      toast((err as Error).message, "erreur");
      setEncours(false);
    }
  };
  return (
    <>
      <div className="entete-page"><h1>Nouveau chantier</h1></div>
      <form className="carte pile" onSubmit={envoyer} style={{ maxWidth: 760 }}>
        <label className="champ">Nom du chantier *<input required value={f.nom} onChange={(e) => maj("nom", e.target.value)} placeholder="ex. Réfection toiture Dupont" autoFocus /></label>
        <div className="grille g2">
          <label className="champ">Client<input value={f.client_nom} onChange={(e) => maj("client_nom", e.target.value)} /></label>
          <label className="champ">Téléphone<input type="tel" value={f.client_tel} onChange={(e) => maj("client_tel", e.target.value)} /></label>
          <label className="champ">E-mail<input type="email" value={f.client_email} onChange={(e) => maj("client_email", e.target.value)} /></label>
          <label className="champ">Type de toiture
            <select value={f.type_toiture} onChange={(e) => maj("type_toiture", e.target.value)}>
              <option value="">— à préciser —</option>
              {Object.entries(types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </div>
        <label className="champ">Adresse du chantier<input value={f.adresse} onChange={(e) => maj("adresse", e.target.value)} /></label>
        <div className="ligne">
          <button type="button" className="btn petit" onClick={localiser}><Icone nom="cible" taille={16} /> Je suis sur le chantier : enregistrer ma position</button>
          {gps && <small>{gps.lat.toFixed(5)}, {gps.lon.toFixed(5)} — sert à cibler le bon bâtiment dans le modèle 3D</small>}
        </div>
        <fieldset style={{ border: "1px solid var(--bordure)", borderRadius: 8, padding: 12 }}>
          <legend style={{ fontWeight: 700, fontSize: ".9rem" }}>Méthode de métré</legend>
          <div className="pile">
            {[
              ["3d", "Reconstruction 3D à partir des photos de drone (recommandé)", "Plusieurs dizaines de photos, calcul automatique des pans, pentes et longueurs."],
              ["photo", "Estimation sur une photo verticale", "Rapide, précision limitée : contours dessinés sur la photo, pentes saisies."],
              ["saisie", "Saisie manuelle des dimensions", "Relevé traditionnel au mètre, sans drone."],
            ].map(([k, t, d]) => (
              <label key={k} className="case">
                <input type="radio" name="mode" checked={f.mode === k} onChange={() => maj("mode", k)} />
                <span><b>{t}</b><br /><small>{d}</small></span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="ligne">
          <button className="btn primaire grand" disabled={encours}>Créer le chantier</button>
        </div>
      </form>
    </>
  );
}
