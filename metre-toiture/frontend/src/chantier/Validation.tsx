import { useEffect, useState } from "react";
import { api, dateFr, fr } from "../api";
import { Badge, Chargement, Icone, useToast } from "../components/ui";
import { FORMATS } from "../pages/Rapports";
import type { Chantier, MetreComplet, Validation } from "../types";

export function EtapeValidation({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [m, setM] = useState<MetreComplet | null>(null);
  const [val, setVal] = useState<Validation | null>(null);
  const [conf, setConf] = useState<Record<string, boolean>>(chantier.confirmations || {});
  const [reserves, setReserves] = useState(chantier.reserves || "");
  const [versions, setVersions] = useState<{ numero: number; date: string; commentaire: string; auteur: string; resume: { surface: number; nb_pans: number } }[]>([]);
  const [opt, setOpt] = useState({ materiaux: true, prix: false, fond: true });
  const toast = useToast();
  const charger = () => {
    api.get<MetreComplet>(`/api/chantiers/${chantier.id}/metre`).then((d) => { setM(d); setVal(d.validation); });
    api.get<typeof versions>(`/api/chantiers/${chantier.id}/metre/versions`).then(setVersions);
  };
  useEffect(charger, [chantier.id]); // eslint-disable-line
  if (!m || !val) return <Chargement />;

  const confirmer = async (cle: string, v: boolean) => {
    const n = { ...conf, [cle]: v };
    setConf(n);
    setVal(await api.put<Validation>(`/api/chantiers/${chantier.id}/confirmations`, { confirmations: n }));
  };
  const valider = async () => {
    try {
      await api.patch(`/api/chantiers/${chantier.id}`, { reserves });
      await api.post(`/api/chantiers/${chantier.id}/valider`);
      toast("Métré validé : prêt pour le devis", "ok");
      maj();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  const t = m.calcul.totaux;
  const icone = { ok: "✓", attention: "!", bloquant: "✕" };
  const qs = `materiaux=${opt.materiaux}&prix=${opt.prix}&fond=${opt.fond}`;
  return (
    <div className="pile">
      <div className="grille g2">
        <div className="carte pile">
          <div className="ligne"><h2 style={{ margin: 0 }}>Checklist avant devis</h2><span className="espace" />
            <Badge statut={val.statut}>{val.statut === "ok" ? "Prêt" : val.statut === "attention" ? "À surveiller" : "Bloquant"}</Badge></div>
          {val.items.map((it) => (
            <div key={it.code} className={`alerte ${it.statut === "ok" ? "ok" : it.statut === "attention" ? "attention" : "erreur"}`} style={{ marginBottom: 0 }}>
              <b>{icone[it.statut]} {it.titre}</b>{it.detail}
              {it.confirmation && (
                <label className="case" style={{ marginTop: 6 }}>
                  <input type="checkbox" checked={!!conf[it.confirmation]} onChange={(e) => confirmer(it.confirmation!, e.target.checked)} />
                  {m.confirmations_libelles[it.confirmation]}
                </label>
              )}
            </div>
          ))}
          <label className="champ">Réserves (reprises dans le rapport)
            <textarea value={reserves} onChange={(e) => setReserves(e.target.value)} placeholder="ex. Versant nord partiellement masqué par un arbre : longueur d'égout mesurée sur place." /></label>
          <div className="ligne">
            <button className="btn" onClick={async () => { await api.patch(`/api/chantiers/${chantier.id}`, { reserves }); toast("Réserves enregistrées", "ok"); }}>Enregistrer les réserves</button>
            <button className="btn primaire" disabled={!val.pret_pour_devis || chantier.statut === "valide"} onClick={valider}>
              {chantier.statut === "valide" ? "Métré validé ✓" : "Valider le métré"}</button>
            {chantier.statut === "valide" && <button className="btn" onClick={async () => { await api.patch(`/api/chantiers/${chantier.id}`, { statut: "termine" }); maj(); }}>Marquer le chantier terminé</button>}
          </div>
        </div>
        <div className="pile">
          <div className="carte pile">
            <h2>Rapport PDF</h2>
            <div className="indicateur"><span>Surface nette</span><b>{fr(t.surface_nette)} m²</b></div>
            <div className="indicateur"><span>Pans</span><b>{t.nb_pans}</b></div>
            <label className="case"><input type="checkbox" checked={opt.materiaux} onChange={(e) => setOpt({ ...opt, materiaux: e.target.checked })} /> Inclure les matériaux</label>
            <label className="case"><input type="checkbox" checked={opt.prix} onChange={(e) => setOpt({ ...opt, prix: e.target.checked })} /> Afficher les prix (usage interne)</label>
            {chantier.modele?.ortho && <label className="case"><input type="checkbox" checked={opt.fond} onChange={(e) => setOpt({ ...opt, fond: e.target.checked })} /> Orthophoto en fond du plan</label>}
            <div className="ligne">
              <a className="btn primaire" href={`/api/chantiers/${chantier.id}/rapport.pdf?${qs}`} target="_blank" rel="noreferrer"><Icone nom="rapport" /> Ouvrir le rapport</a>
            </div>
            {val.statut !== "ok" && <small>Le rapport mentionne les points restant à contrôler.</small>}
          </div>
          <div className="carte pile">
            <h3>Exports</h3>
            {FORMATS.filter((x) => x.f !== "geojson" || chantier.modele?.type === "odm").map((x) => (
              <div key={x.f} className="ligne"><a className="btn petit" href={`/api/chantiers/${chantier.id}/export/${x.f}`}><Icone nom="telecharger" taille={16} /> {x.t}</a><small>{x.d}</small></div>
            ))}
          </div>
        </div>
      </div>
      <div className="carte">
        <h3>Historique des versions du métré</h3>
        {versions.length === 0 ? <p className="discret">Aucune version enregistrée.</p> : (
          <div className="defile-x"><table className="tableau">
            <thead><tr><th>Version</th><th>Date</th><th>Auteur</th><th>Modification</th><th className="num">Surface</th><th /></tr></thead>
            <tbody>{versions.map((v, i) => (
              <tr key={v.numero}><td>{v.numero}</td><td>{dateFr(v.date)}</td><td>{v.auteur}</td><td><small>{v.commentaire}</small></td>
                <td className="num">{v.resume ? `${fr(v.resume.surface, 1)} m²` : "—"}</td>
                <td>{i > 0 && <button className="btn petit" onClick={async () => {
                  if (!confirm(`Revenir à la version ${v.numero} ? (une nouvelle version est créée, rien n'est perdu)`)) return;
                  await api.post(`/api/chantiers/${chantier.id}/metre/versions/${v.numero}/restaurer`);
                  toast(`Version ${v.numero} restaurée`, "ok");
                  charger();
                  maj();
                }}>Restaurer</button>}</td></tr>))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
