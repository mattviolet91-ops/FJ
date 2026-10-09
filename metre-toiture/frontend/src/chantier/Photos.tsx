import { DragEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, envoyerFichiers, fr } from "../api";
import { Badge, Chargement, Icone, Progression, useToast } from "../components/ui";
import type { AnalysePhotos, Chantier, Photo } from "../types";

const LIB_PB: Record<string, string> = { floue: "Floue", surexposee: "Surexposée", sombre: "Sombre", doublon: "Doublon" };
const LOT = 6;

export function EtapePhotos({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [photos, setPhotos] = useState<Photo[] | null>(null);
  const [analyse, setAnalyse] = useState<AnalysePhotos | null>(chantier.analyse_photos || null);
  const [envoi, setEnvoi] = useState<{ fait: number; total: number; erreurs: string[] } | null>(null);
  const [survol, setSurvol] = useState(false);
  const [filtre, setFiltre] = useState("tous");
  const input = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const charger = () => api.get<Photo[]>(`/api/chantiers/${chantier.id}/photos`).then(setPhotos);
  useEffect(() => { charger(); }, [chantier.id]); // eslint-disable-line

  const importer = async (fichiers: File[]) => {
    const liste = fichiers.filter((f) => /\.(jpe?g|tiff?|png|txt)$/i.test(f.name));
    if (!liste.length) return toast("Aucun fichier image reconnu (JPEG ou TIFF attendus)", "erreur");
    const total = liste.reduce((s, f) => s + f.size, 0);
    let envoye = 0;
    const erreurs: string[] = [];
    setEnvoi({ fait: 0, total, erreurs });
    for (let i = 0; i < liste.length; i += LOT) {
      const lot = liste.slice(i, i + LOT);
      const taille = lot.reduce((s, f) => s + f.size, 0);
      try {
        const r = await envoyerFichiers<{ resultats: { nom: string; erreur?: string }[]; analyse: AnalysePhotos }>(
          `/api/chantiers/${chantier.id}/photos`, lot, (f) => setEnvoi({ fait: envoye + f * taille, total, erreurs }));
        r.resultats.filter((x) => x.erreur).forEach((x) => erreurs.push(`${x.nom} : ${x.erreur}`));
        setAnalyse(r.analyse);
      } catch (e) {
        erreurs.push(`Lot ${i / LOT + 1} : ${(e as Error).message}`);
      }
      envoye += taille;
      setEnvoi({ fait: envoye, total, erreurs: [...erreurs] });
    }
    await charger();
    maj();
    toast(`${liste.length - erreurs.length} fichier(s) importé(s)${erreurs.length ? `, ${erreurs.length} refusé(s)` : ""}`, erreurs.length ? undefined : "ok");
    setTimeout(() => setEnvoi((e) => (e && e.erreurs.length ? e : null)), 1500);
  };

  const deposer = (e: DragEvent) => {
    e.preventDefault();
    setSurvol(false);
    importer(Array.from(e.dataTransfer.files));
  };
  const basculer = async (p: Photo) => {
    await api.patch(`/api/photos/${p.id}`, { exclue: !p.exclue });
    charger();
    setAnalyse(await api.get(`/api/chantiers/${chantier.id}/analyse-photos`));
  };
  const exclure = async (codes: string[]) => {
    const r = await api.post<{ exclues: number; analyse: AnalysePhotos }>(`/api/chantiers/${chantier.id}/photos/exclure-problemes`, codes);
    toast(`${r.exclues} photo(s) exclue(s)`);
    setAnalyse(r.analyse);
    charger();
  };
  const visibles = (photos || []).filter((p) => p.type === "photo").filter((p) =>
    filtre === "tous" ? true : filtre === "problemes" ? p.problemes.length > 0 : filtre === "exclues" ? p.exclue : p.categorie === filtre);
  const gcp = (photos || []).filter((p) => p.type === "gcp");
  const nb = (photos || []).filter((p) => p.type === "photo" && !p.exclue).length;

  return (
    <div className="pile">
      <div className={`depot ${survol ? "survol" : ""}`} onClick={() => input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setSurvol(true); }} onDragLeave={() => setSurvol(false)} onDrop={deposer}>
        <Icone nom="photo" taille={34} />
        <h3 style={{ margin: "6px 0" }}>Glissez les photos du vol ici</h3>
        <small>ou touchez pour les sélectionner — JPEG/TIFF d'origine, non retouchés. Fichier <code>gcp_list.txt</code> accepté.</small>
        <input ref={input} type="file" multiple hidden accept="image/jpeg,image/tiff,image/png,.jpg,.jpeg,.tif,.tiff,.txt"
          onChange={(e) => { importer(Array.from(e.target.files || [])); e.target.value = ""; }} />
      </div>
      {envoi && (
        <div className="carte pile">
          <div className="ligne"><b>Import en cours</b><span className="espace" /><small>{fr(envoi.fait / 1e6, 0)} / {fr(envoi.total / 1e6, 0)} Mo</small></div>
          <Progression valeur={(100 * envoi.fait) / Math.max(1, envoi.total)} />
          {envoi.erreurs.length > 0 && <div className="alerte attention"><b>Fichiers refusés</b>{envoi.erreurs.slice(0, 12).map((e, i) => <div key={i}><small>{e}</small></div>)}
            <button className="lien" onClick={() => setEnvoi(null)}>Masquer</button></div>}
        </div>
      )}
      {analyse && <RapportAnalyse a={analyse} exclure={exclure} />}
      <div className="carte">
        <div className="ligne" style={{ marginBottom: 10 }}>
          <h3 style={{ margin: 0 }}>{nb} photo(s) retenue(s)</h3>
          <span className="espace" />
          {[["tous", "Toutes"], ["problemes", "À problème"], ["verticale", "Verticales"], ["oblique", "Obliques"], ["exclues", "Exclues"]].map(([k, l]) => (
            <button key={k} className={`btn petit ${filtre === k ? "actif" : ""}`} onClick={() => setFiltre(k)}>{l}</button>
          ))}
        </div>
        {!photos ? <Chargement /> : visibles.length === 0 ? <div className="vide">Aucune photo.</div> : (
          <div className="vignettes">
            {visibles.map((p) => (
              <div key={p.id} className={`vignette ${p.exclue ? "exclue" : ""} ${p.problemes.length ? "probleme" : ""}`} title={p.nom}>
                <img src={`/api/photos/${p.id}/miniature`} alt={p.nom} loading="lazy" />
                <div className="etiquettes">
                  {p.categorie !== "inconnue" && <span>{p.categorie === "verticale" ? "Vert." : p.categorie === "oblique" ? "Obl." : "Horiz."}</span>}
                  {p.problemes.map((x) => <span key={x} style={{ background: "rgba(198,40,40,.85)" }}>{LIB_PB[x] || x}</span>)}
                  {p.exclue && <span>Exclue</span>}
                </div>
                <button className="btn petit" onClick={() => basculer(p)} title={p.exclue ? "Réintégrer" : "Exclure"} style={{ minHeight: 28, padding: "2px 6px" }}>
                  {p.exclue ? "↺" : "✕"}
                </button>
              </div>
            ))}
          </div>
        )}
        {gcp.length > 0 && <p style={{ marginTop: 10 }}><Badge statut="ok">Points de contrôle</Badge> {gcp.map((g) => g.nom).join(", ")}</p>}
      </div>
      <div className="ligne">
        <Link className="btn primaire" to={`/chantiers/${chantier.id}/traitement`}>Étape suivante : {chantier.mode === "photo" ? "configurer la photo unique" : "lancer le calcul 3D"} →</Link>
      </div>
    </div>
  );
}

function RapportAnalyse({ a, exclure }: { a: AnalysePhotos; exclure: (c: string[]) => void }) {
  const verdict = { correct: ["ok", "Série correcte"], a_ameliorer: ["attention", "Série à améliorer"], insuffisant: ["bloquant", "Série insuffisante"] }[a.verdict];
  const s = a.stats;
  return (
    <div className="carte pile">
      <div className="ligne"><h3 style={{ margin: 0 }}>Analyse de la série</h3><Badge statut={a.verdict}>{verdict[1]}</Badge></div>
      <div className="grille g4">
        <div className="indicateur"><span>Photos analysées</span><b>{s.nombre}</b></div>
        <div className="indicateur"><span>Avec GPS</span><b>{s.avec_gps ?? 0}</b></div>
        <div className="indicateur"><span>Verticales / obliques</span><b>{s.angles && s.angles.inconnue < s.nombre ? `${s.angles.verticale} / ${s.angles.oblique}` : "non évaluable"}</b></div>
        <div className="indicateur"><span>Pixel au sol (verticales)</span><b>{s.gsd_sol_cm ? `≈ ${fr(s.gsd_sol_cm.median, 1)} cm` : "non évaluable"}</b></div>
      </div>
      {s.couverture_secteurs && (
        <div>
          <small>Vues obliques par côté du bâtiment</small>
          <Rose secteurs={s.couverture_secteurs} />
        </div>
      )}
      {a.problemes.length === 0 && <div className="alerte ok">Aucun problème détecté sur les critères évaluables. Le résultat final dépendra aussi de la reconstruction.</div>}
      {a.problemes.map((p, i) => (
        <div key={i} className={`alerte ${p.niveau === "bloquant" ? "erreur" : p.niveau === "alerte" ? "attention" : "info"}`}>
          <b>{p.message}</b>{p.action}
          {(p.code === "floues" || p.code === "doublons") && (
            <div style={{ marginTop: 6 }}><button className="btn petit" onClick={() => exclure([p.code === "floues" ? "floue" : "doublon"])}>Exclure ces photos</button></div>
          )}
        </div>
      ))}
      {typeof s.recouvrement === "string" && <small>Recouvrement : {s.recouvrement}</small>}
    </div>
  );
}

function Rose({ secteurs }: { secteurs: Record<string, number> }) {
  const noms = ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"];
  const max = Math.max(1, ...Object.values(secteurs));
  return (
    <svg viewBox="-110 -110 220 220" style={{ width: 200, height: 200, display: "block" }} role="img" aria-label="Couverture par côté">
      {noms.map((n, i) => {
        const v = secteurs[n] || 0;
        const r = 20 + (70 * v) / max;
        const a0 = ((i * 45 - 22.5 - 90) * Math.PI) / 180, a1 = ((i * 45 + 22.5 - 90) * Math.PI) / 180;
        const d = `M0 0 L${r * Math.cos(a0)} ${r * Math.sin(a0)} A${r} ${r} 0 0 1 ${r * Math.cos(a1)} ${r * Math.sin(a1)} Z`;
        const am = ((i * 45 - 90) * Math.PI) / 180;
        return (
          <g key={n}>
            <path d={d} fill={v === 0 ? "#fdeaea" : "#2BABE2"} opacity={v === 0 ? 1 : 0.35 + 0.65 * (v / max)} stroke="white" />
            <text x={100 * Math.cos(am)} y={100 * Math.sin(am) + 4} textAnchor="middle" fontSize={11} fill="#2F3438">{n === "nord" ? "N" : n === "est" ? "E" : n === "sud" ? "S" : n === "ouest" ? "O" : ""}</text>
            <text x={(r + 8) * Math.cos(am) * 0.6} y={(r + 8) * Math.sin(am) * 0.6 + 4} textAnchor="middle" fontSize={10} fill={v === 0 ? "#C62828" : "#23272A"}>{v}</text>
          </g>
        );
      })}
      <rect x={-12} y={-8} width={24} height={16} fill="#b5523b" />
    </svg>
  );
}
