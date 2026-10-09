import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fr } from "../api";
import { Icone, useToast } from "../components/ui";
import { Checklist } from "../guide/contenu";
import { FicheMini4K } from "../guide/drones";
import type { Chantier, PlanVol } from "../types";

interface Ref {
  drones: Record<string, string>;
  precisions: Record<string, string>;
  types_toiture: Record<string, string>;
}

const DEFAUT = { type_toiture: "deux_pans", longueur: 12, largeur: 9, hauteur_faitage: 8, complexite: "simple",
  drone: "dji_mini_4k", focale_35mm: "", largeur_px: "", hauteur_px: "", precision: "devis", vent: "faible", lumiere: "nuageux",
  obstacles: [] as string[], mitoyen: false };

export function EtapePreparation({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [ref, setRef] = useState<Ref | null>(null);
  const [p, setP] = useState({ ...DEFAUT, type_toiture: chantier.type_toiture || DEFAUT.type_toiture, ...(chantier.preparation || {}) });
  const [plan, setPlan] = useState<PlanVol | null>(chantier.plan_vol || null);
  const toast = useToast();
  useEffect(() => { api.get<Ref>("/api/plan-vol/referentiel").then(setRef); }, []);
  const set = (k: string, v: unknown) => setP((x) => ({ ...x, [k]: v }));
  const generer = async () => {
    try {
      const r = await api.put<PlanVol>(`/api/chantiers/${chantier.id}/preparation`, p);
      setPlan(r);
      maj();
      toast("Plan de prise de vue généré", "ok");
      setTimeout(() => document.getElementById("plan-vol")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  const obst = (k: string) => set("obstacles", p.obstacles.includes(k) ? p.obstacles.filter((x: string) => x !== k) : [...p.obstacles, k]);
  return (
    <div className="pile">
      <div className="carte pile">
        <h2>Assistant de préparation</h2>
        <p className="discret">Quelques questions pour calculer un plan de prise de vue adapté à ce toit et à votre drone.</p>
        <div className="grille g3">
          <label className="champ">Type de toiture
            <select value={p.type_toiture} onChange={(e) => set("type_toiture", e.target.value)}>
              {ref && Object.entries(ref.types_toiture).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select></label>
          <label className="champ">Longueur approx. du bâtiment (m)<input type="number" inputMode="decimal" value={p.longueur} onChange={(e) => set("longueur", +e.target.value)} /></label>
          <label className="champ">Largeur approx. (m)<input type="number" inputMode="decimal" value={p.largeur} onChange={(e) => set("largeur", +e.target.value)} /></label>
          <label className="champ">Hauteur du faîtage (m)<input type="number" inputMode="decimal" value={p.hauteur_faitage} onChange={(e) => set("hauteur_faitage", +e.target.value)} /></label>
          <label className="champ">Complexité
            <select value={p.complexite} onChange={(e) => set("complexite", e.target.value)}>
              <option value="simple">Simple (pans réguliers)</option><option value="moyenne">Moyenne (croupes, 1–2 noues, cheminées)</option>
              <option value="complexe">Complexe (lucarnes, multiples noues)</option></select></label>
          <label className="champ">Précision recherchée
            <select value={p.precision} onChange={(e) => set("precision", e.target.value)}>
              {ref && Object.entries(ref.precisions).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label className="champ">Drone
            <select value={p.drone} onChange={(e) => set("drone", e.target.value)}>
              <option value="">Autre / je saisis la caméra</option>
              {ref && Object.entries(ref.drones).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          {!p.drone && <>
            <label className="champ">Focale équiv. 24×36 (mm)<input inputMode="decimal" value={p.focale_35mm} onChange={(e) => set("focale_35mm", e.target.value)} placeholder="ex. 24" /></label>
            <label className="champ">Résolution (largeur × hauteur px)
              <div className="ligne" style={{ flexWrap: "nowrap" }}><input inputMode="numeric" value={p.largeur_px} onChange={(e) => set("largeur_px", e.target.value)} placeholder="4000" />×<input inputMode="numeric" value={p.hauteur_px} onChange={(e) => set("hauteur_px", e.target.value)} placeholder="3000" /></div></label>
          </>}
          <label className="champ">Vent prévu<select value={p.vent} onChange={(e) => set("vent", e.target.value)}><option value="faible">Faible</option><option value="moyen">Modéré</option><option value="fort">Fort</option></select></label>
          <label className="champ">Lumière<select value={p.lumiere} onChange={(e) => set("lumiere", e.target.value)}><option value="nuageux">Voilée / nuageuse</option><option value="soleil">Plein soleil</option><option value="variable">Variable</option></select></label>
        </div>
        <div className="ligne">
          <label className="case"><input type="checkbox" checked={p.obstacles.includes("arbres")} onChange={() => obst("arbres")} /> Arbres proches</label>
          <label className="case"><input type="checkbox" checked={p.obstacles.includes("cables")} onChange={() => obst("cables")} /> Câbles / lignes</label>
          <label className="case"><input type="checkbox" checked={!!p.mitoyen} onChange={(e) => set("mitoyen", e.target.checked)} /> Bâtiment mitoyen</label>
        </div>
        <div><button className="btn primaire grand" onClick={generer}>Générer le plan de prise de vue</button></div>
      </div>
      {plan && <AffichagePlan plan={plan} chantierId={chantier.id} />}
      {p.drone === "dji_mini_4k" && (
        <details className="carte" open={!plan}>
          <summary style={{ cursor: "pointer", fontWeight: 700 }}>Réglages et conseils DJI Mini 4K</summary>
          <div style={{ marginTop: 10 }}><FicheMini4K compacte /></div>
        </details>
      )}
    </div>
  );
}

function AffichagePlan({ plan, chantierId }: { plan: PlanVol; chantierId: number }) {
  return (
    <div className="carte pile" id="plan-vol">
      <div className="ligne"><h2 style={{ margin: 0 }}>Plan de prise de vue</h2><span className="espace" />
        <button className="btn petit" onClick={() => window.print()}><Icone nom="rapport" taille={16} /> Imprimer</button></div>
      {plan.alertes.map((a, i) => <div key={i} className="alerte attention">{a}</div>)}
      <div className="grille g4">
        <div className="carte" style={{ background: "var(--bleu-pale)", boxShadow: "none" }}><small>Photos à prévoir</small><div className="gros-chiffre">≈ {plan.total_photos}</div></div>
        <div className="carte" style={{ background: "var(--bleu-pale)", boxShadow: "none" }}><small>Hauteur passages verticaux</small><div className="gros-chiffre">{plan.hauteur_vol_sol_m ? `${Math.round(plan.hauteur_vol_sol_m)} m` : "—"}</div><small>au-dessus du décollage</small></div>
        <div className="carte" style={{ background: "var(--bleu-pale)", boxShadow: "none" }}><small>Détail sur le toit</small><div className="gros-chiffre">{plan.gsd_toit_cm ? `${fr(plan.gsd_toit_cm, 1)} cm` : "—"}</div><small>par pixel</small></div>
        <div className="carte" style={{ background: "var(--bleu-pale)", boxShadow: "none" }}><small>Batteries (indicatif)</small><div className="gros-chiffre">{plan.batteries_estimees ?? "—"}</div></div>
      </div>
      <div className="grille g2">
        {plan.etapes.map((e, i) => (
          <div key={i}>
            <h3>{i + 1}. {e.titre}</h3>
            <ul style={{ paddingLeft: "1.2em", margin: 0 }}>{e.points.map((x, j) => <li key={j}>{x}</li>)}</ul>
          </div>
        ))}
      </div>
      {plan.conseils.length > 0 && <div className="alerte info"><b>Conseils pour ce chantier</b><ul style={{ margin: 0, paddingLeft: "1.2em" }}>{plan.conseils.map((c, i) => <li key={i}>{c}</li>)}</ul></div>}
      <small>{plan.avertissement}</small>
      <Checklist id={`terrain-${chantierId}`} items={[
        "Réglementation vérifiée, accord du propriétaire obtenu",
        "Cote de référence mesurée au mètre et notée",
        "Passages verticaux réalisés",
        ...plan.orbites.map((o) => `${o.nom} réalisée (tour complet)`),
        "Photos de détail (noues, cheminées, raccords) prises",
        "Quelques photos agrandies : nettes",
      ]} />
      <div><Link className="btn primaire" to={`/chantiers/${chantierId}/photos`}>Étape suivante : importer les photos →</Link></div>
    </div>
  );
}
