import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, dateFr, duree, fr } from "../api";
import { Badge, Chargement, Progression, useToast } from "../components/ui";
import { tempsRestant } from "../pages/Traitements";
import type { Chantier, Photo, Traitement } from "../types";

interface Preset { libelle: string; description: string; estimation: { secondes: number; base: string } | null }

export function EtapeTraitement({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  if (chantier.mode === "photo") return <PhotoUnique chantier={chantier} maj={maj} />;
  return <Reconstruction chantier={chantier} maj={maj} />;
}

function Reconstruction({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [etat, setEtat] = useState<{ disponible: boolean; erreur?: string; coeurs?: number; memoire_go?: number; file_attente?: number } | null>(null);
  const [presets, setPresets] = useState<Record<string, Preset> | null>(null);
  const [preset, setPreset] = useState("devis");
  const [jobs, setJobs] = useState<Traitement[]>([]);
  const toast = useToast();
  const n = chantier.nb_photos || 0;
  const charger = () => api.get<Traitement[]>(`/api/traitements?chantier_id=${chantier.id}`).then(setJobs);
  useEffect(() => {
    api.get<typeof etat>("/api/calcul/etat").then(setEtat);
    api.get<Record<string, Preset>>(`/api/calcul/presets?nb_images=${n}`).then(setPresets);
    charger();
  }, [chantier.id]); // eslint-disable-line
  const actif = jobs.find((j) => ["en_attente", "envoi", "en_cours", "telechargement"].includes(j.statut));
  useEffect(() => {
    if (!actif) return;
    const t = setInterval(async () => {
      const j = await api.get<Traitement>(`/api/traitements/${actif.id}`);
      setJobs((l) => l.map((x) => (x.id === j.id ? j : x)));
      if (["termine", "erreur", "annule"].includes(j.statut)) {
        maj();
        if (j.statut === "termine") toast("Modèle 3D prêt : vérifiez le métré", "ok");
      }
    }, 4000);
    return () => clearInterval(t);
  }, [actif?.id]); // eslint-disable-line

  const lancer = async () => {
    try {
      await api.post(`/api/chantiers/${chantier.id}/reconstruction`, { preset });
      toast("Reconstruction lancée");
      charger();
      maj();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  const dernier = jobs.find((j) => j.type === "reconstruction");
  return (
    <div className="pile">
      <div className="grille g2">
        <div className="carte pile">
          <h2>Reconstruction 3D</h2>
          {!etat ? <Chargement /> : etat.disponible
            ? <div className="alerte ok"><b>Serveur de calcul disponible</b>{etat.coeurs} cœurs, {fr(etat.memoire_go || 0, 1)} Go de mémoire, {etat.file_attente} tâche(s) en file.</div>
            : <div className="alerte attention"><b>Serveur de calcul injoignable</b>Le traitement sera mis en attente et démarrera automatiquement dès que le serveur répondra. <Link to="/parametres/calcul">Configuration</Link></div>}
          <p>{n} photo(s) retenue(s).</p>
          {presets && Object.entries(presets).map(([k, p]) => (
            <label key={k} className="case">
              <input type="radio" name="preset" checked={preset === k} onChange={() => setPreset(k)} />
              <span><b>{p.libelle}</b> {p.estimation && <small>— durée estimée ≈ {duree(p.estimation.secondes)}</small>}<br /><small>{p.description}</small></span>
            </label>
          ))}
          {presets?.devis?.estimation?.base === "valeur par défaut" && <small>Estimation par défaut : elle s'affinera automatiquement après les premiers calculs sur votre serveur.</small>}
          <div><button className="btn primaire grand" disabled={!!actif || n < 5} onClick={lancer}>{chantier.modele ? "Relancer la reconstruction" : "Lancer la reconstruction"}</button></div>
          {n < 5 && <small>Importez au moins 5 photos (plusieurs dizaines recommandées).</small>}
        </div>
        <div className="carte pile">
          <h3>Suivi</h3>
          {!dernier ? <p className="discret">Aucun calcul lancé pour ce chantier.</p> : <SuiviJob t={dernier} recharger={charger} />}
          {chantier.modele?.type === "odm" && (
            <div className="pile">
              <div className="alerte ok"><b>Modèle 3D disponible</b>
                Résolution du modèle de surface : {fr((chantier.modele.res_mns || 0) * 100, 1)} cm
                {chantier.modele.res_ortho ? ` · orthophoto ${fr(chantier.modele.res_ortho * 100, 1)} cm/px` : ""}
                {chantier.modele.nb_points ? ` · ${fr(chantier.modele.nb_points / 1e6, 1)} M points` : ""}
              </div>
              <div className="ligne">
                <Link className="btn primaire" to={`/chantiers/${chantier.id}/metre`}>Vérifier le métré →</Link>
                {chantier.modele.rapport_odm && <a className="btn" href={`/api/chantiers/${chantier.id}/rapport-odm`} target="_blank" rel="noreferrer">Rapport technique de reconstruction</a>}
              </div>
            </div>
          )}
        </div>
      </div>
      {jobs.length > 1 && (
        <details className="carte"><summary>Historique des calculs ({jobs.length})</summary>
          <table className="tableau"><tbody>{jobs.map((j) => (
            <tr key={j.id}><td>{j.type === "reconstruction" ? "Reconstruction" : "Détection"}</td><td><Badge statut={j.statut}>{j.statut_libelle}</Badge></td><td><small>{j.message}</small></td><td>{dateFr(j.cree_le)}</td></tr>))}</tbody></table>
        </details>
      )}
    </div>
  );
}

function SuiviJob({ t, recharger }: { t: Traitement; recharger: () => void }) {
  const toast = useToast();
  const encours = ["en_attente", "envoi", "en_cours", "telechargement"].includes(t.statut);
  return (
    <div className="pile">
      <div className="ligne"><Badge statut={t.statut}>{t.statut_libelle}</Badge><small>{t.etape}</small><span className="espace" /><small>{fr(t.progression, 0)} %</small></div>
      {encours && <Progression valeur={t.progression} />}
      <small>{t.message}</small>
      {encours && <small>{tempsRestant(t) || `Durée estimée : ≈ ${duree(t.duree_estimee_s)}`}. Vous pouvez fermer cette page : le calcul continue.</small>}
      {t.statut === "erreur" && (
        <>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: ".8rem", maxHeight: 240, overflow: "auto", background: "var(--rouge-pale)", padding: 8, borderRadius: 6 }}>{t.erreur}</pre>
          <div><button className="btn" onClick={async () => { try { await api.post(`/api/traitements/${t.id}/relancer`); recharger(); } catch (e) { toast((e as Error).message, "erreur"); } }}>Relancer</button></div>
        </>
      )}
      {encours && <div><button className="btn petit danger" onClick={async () => { if (confirm("Annuler le calcul en cours ?")) { await api.post(`/api/traitements/${t.id}/annuler`); recharger(); } }}>Annuler</button></div>}
    </div>
  );
}

function PhotoUnique({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [photos, setPhotos] = useState<Photo[] | null>(null);
  const [choix, setChoix] = useState<number | null>(chantier.modele?.photo_id || null);
  const [hToit, setHToit] = useState(7);
  const [alt, setAlt] = useState("");
  const [f35, setF35] = useState("");
  const toast = useToast();
  useEffect(() => { api.get<Photo[]>(`/api/chantiers/${chantier.id}/photos`).then((l) => setPhotos(l.filter((p) => p.type === "photo"))); }, [chantier.id]);
  const p = photos?.find((x) => x.id === choix);
  const valider = async () => {
    try {
      await api.post(`/api/chantiers/${chantier.id}/photo-unique`, { photo_id: choix, hauteur_toit: hToit, altitude: alt ? +alt : null, focale_35mm: f35 ? +f35 : null });
      toast("Photo configurée : dessinez les pans", "ok");
      maj();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  return (
    <div className="pile">
      <div className="alerte attention"><b>Mode estimation</b>L'échelle est déduite de l'altitude de vol et de l'optique :
        la précision dépend de la verticalité de la photo, de l'altitude enregistrée et de la hauteur du toit saisie.
        Contrôlez au moins une cote au mètre dans l'éditeur.</div>
      <div className="carte pile">
        <h3>1. Choisissez une photo verticale au-dessus du toit</h3>
        {!photos ? <Chargement /> : photos.length === 0 ? <p>Importez d'abord une photo (étape Photos).</p> : (
          <div className="vignettes">
            {photos.map((x) => (
              <button key={x.id} className="vignette" onClick={() => setChoix(x.id)} style={{ borderColor: x.id === choix ? "var(--bleu)" : undefined, borderWidth: 3, padding: 0, cursor: "pointer" }}>
                <img src={`/api/photos/${x.id}/miniature`} alt={x.nom} />
                <div className="etiquettes"><span>{x.categorie === "verticale" ? "Verticale" : x.nacelle_tangage !== undefined ? `${Math.round(x.nacelle_tangage)}°` : "angle ?"}</span>{x.alt_relative ? <span>{Math.round(x.alt_relative)} m</span> : null}</div>
              </button>
            ))}
          </div>
        )}
      </div>
      {p && (
        <div className="carte pile">
          <h3>2. Hauteurs</h3>
          <div className="grille g3">
            <label className="champ">Hauteur du toit au-dessus du décollage (m)<small>Hauteur moyenne de la couverture (entre égout et faîtage)</small><input inputMode="decimal" type="number" value={hToit} onChange={(e) => setHToit(+e.target.value)} /></label>
            <label className="champ">Altitude de vol relative (m)<small>{p.alt_relative ? `Lue dans la photo : ${fr(p.alt_relative, 1)} m` : "Absente de la photo : à saisir"}</small><input inputMode="decimal" value={alt} onChange={(e) => setAlt(e.target.value)} placeholder={p.alt_relative ? String(p.alt_relative) : ""} /></label>
            <label className="champ">Focale équiv. 24×36 (mm)<small>Si absente des métadonnées</small><input inputMode="decimal" value={f35} onChange={(e) => setF35(e.target.value)} /></label>
          </div>
          <div><button className="btn primaire" onClick={valider}>Utiliser cette photo</button></div>
        </div>
      )}
      {chantier.modele?.type === "photo" && (
        <div className="carte pile">
          <div className="alerte ok"><b>Photo configurée</b>Échelle estimée : {fr((chantier.modele.gsd_m || 0) * 100, 2)} cm par pixel à la hauteur du toit.</div>
          {chantier.modele.avertissements?.map((a, i) => <div key={i} className="alerte attention">{a}</div>)}
          <div><Link className="btn primaire" to={`/chantiers/${chantier.id}/metre`}>Dessiner les pans →</Link></div>
        </div>
      )}
    </div>
  );
}
