import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fr } from "../api";
import { Badge, Chargement, Icone, useToast } from "../components/ui";
import type { Chantier, Ouvrage } from "../types";

interface Ligne {
  ouvrage: string; article: string; reference?: string; unite: string; base_libelle: string; statut: string; manque?: string;
  quantite_base?: number; consommation?: number; perte_pct?: number; quantite_totale?: number; conditionnements?: number;
  libelle_conditionnement?: string; quantite_commandee?: number; prix_unitaire?: number; montant_ht?: number;
}
interface Resultat { lignes: Ligne[]; a_completer: number; total_ht: number; total_complet: boolean }
interface Selection { ouvrage: Ouvrage; pans: string[] | null }

export function EtapeMateriaux({ chantier }: { chantier: Chantier }) {
  const [catalogue, setCatalogue] = useState<Ouvrage[] | null>(null);
  const [sel, setSel] = useState<Selection[]>([]);
  const [res, setRes] = useState<Resultat | null>(null);
  const [pans, setPans] = useState<{ id: string; nom: string }[]>([]);
  const [sale, setSale] = useState(false);
  const toast = useToast();
  useEffect(() => {
    api.get<{ ouvrages: Ouvrage[] }>("/api/ouvrages").then((d) => setCatalogue(d.ouvrages));
    api.get<{ selections: Selection[]; resultat: Resultat | null }>(`/api/chantiers/${chantier.id}/materiaux`).then((d) => {
      setSel(d.selections);
      setRes(d.resultat);
    });
    api.get<{ calcul: { pans: { id: string; nom: string }[] } }>(`/api/chantiers/${chantier.id}/metre`).then((d) => setPans(d.calcul.pans));
  }, [chantier.id]);

  const enregistrer = async (s = sel) => {
    try {
      const d = await api.put<{ selections: Selection[]; resultat: Resultat | null }>(`/api/chantiers/${chantier.id}/materiaux`, { selections: s });
      setRes(d.resultat);
      setSale(false);
      toast("Quantités recalculées", "ok");
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  const majSel = (i: number, f: (s: Selection) => Selection) => { setSel((l) => l.map((x, j) => (j === i ? f(x) : x))); setSale(true); };

  if (!catalogue) return <Chargement />;
  return (
    <div className="pile">
      <div className="alerte info">Les quantités sont calculées à partir du métré et des valeurs que <b>vous</b> renseignez
        (fiches fabricants, pertes, conditionnements, prix). Aucune valeur n'est inventée : un article incomplet est signalé.</div>
      <div className="carte pile">
        <div className="ligne">
          <h3 style={{ margin: 0 }}>Ouvrages du chantier</h3><span className="espace" />
          <select defaultValue="" onChange={(e) => {
            const o = catalogue.find((x) => String(x.id) === e.target.value);
            if (o) { const n = [...sel, { ouvrage: JSON.parse(JSON.stringify(o)), pans: null }]; setSel(n); enregistrer(n); }
            e.target.value = "";
          }} style={{ maxWidth: 320 }}>
            <option value="">+ Ajouter un ouvrage du catalogue…</option>
            {catalogue.map((o) => <option key={o.id} value={o.id}>{o.nom}</option>)}
          </select>
        </div>
        {sel.length === 0 && <p className="discret">Ajoutez un ouvrage (ex. tuiles, ardoises, zinguerie). Les modèles se gèrent dans <Link to="/parametres/catalogue">Paramètres → Catalogue</Link>.</p>}
        {sel.map((s, i) => (
          <details key={i} className="carte" open style={{ boxShadow: "none", border: "1px solid var(--bordure)" }}>
            <summary style={{ cursor: "pointer" }}><b>{s.ouvrage.nom}</b> <small>— {s.pans ? `${s.pans.length} pan(s)` : "toute la toiture"}</small></summary>
            <div className="pile" style={{ marginTop: 10 }}>
              <div className="ligne">
                <span className="discret">S'applique à :</span>
                <label className="case"><input type="checkbox" checked={!s.pans} onChange={(e) => majSel(i, (x) => ({ ...x, pans: e.target.checked ? null : pans.map((p) => p.id) }))} /> Tous les pans</label>
                {s.pans && pans.map((p) => (
                  <label key={p.id} className="case"><input type="checkbox" checked={s.pans!.includes(p.id)} onChange={(e) => majSel(i, (x) => ({ ...x, pans: e.target.checked ? [...x.pans!, p.id] : x.pans!.filter((q) => q !== p.id) }))} />{p.nom}</label>
                ))}
              </div>
              {s.ouvrage.parametres.length > 0 && (
                <div className="grille g3">
                  {s.ouvrage.parametres.map((p, k) => (
                    <label key={p.cle} className="champ">{p.libelle} ({p.unite})
                      {p.aide && <small>{p.aide}</small>}
                      <input inputMode="decimal" value={p.valeur ?? ""} placeholder="à renseigner" style={{ borderColor: p.valeur === null ? "var(--orange)" : undefined }}
                        onChange={(e) => majSel(i, (x) => ({ ...x, ouvrage: { ...x.ouvrage, parametres: x.ouvrage.parametres.map((q, j) => (j === k ? { ...q, valeur: e.target.value === "" ? null : (+e.target.value.replace(",", ".") as number) } : q)) } }))} />
                    </label>
                  ))}
                </div>
              )}
              <details><summary style={{ cursor: "pointer" }}>Articles, pertes et prix ({s.ouvrage.articles.length})</summary>
                <div className="defile-x"><table className="tableau">
                  <thead><tr><th>Actif</th><th>Article</th><th>Consommation</th><th>Perte %</th><th>Condit.</th><th>Prix HT/u</th><th>Réf.</th></tr></thead>
                  <tbody>{s.ouvrage.articles.map((a, k) => {
                    const majA = (champ: string, v: unknown) => majSel(i, (x) => ({ ...x, ouvrage: { ...x.ouvrage, articles: x.ouvrage.articles.map((q, j) => (j === k ? { ...q, [champ]: v } : q)) } }));
                    const num = (v: string) => (v === "" ? null : isNaN(+v.replace(",", ".")) ? v : +v.replace(",", "."));
                    return (
                      <tr key={k}>
                        <td><input type="checkbox" checked={a.actif !== false} onChange={(e) => majA("actif", e.target.checked)} /></td>
                        <td>{a.nom} <small>({a.unite})</small></td>
                        <td><input value={a.consommation ?? ""} onChange={(e) => majA("consommation", num(e.target.value))} style={{ width: 130 }} placeholder="fiche fabricant" /></td>
                        <td><input inputMode="decimal" value={a.perte_pct ?? ""} onChange={(e) => majA("perte_pct", num(e.target.value))} style={{ width: 70 }} /></td>
                        <td><input inputMode="decimal" value={a.conditionnement ?? ""} onChange={(e) => majA("conditionnement", num(e.target.value))} style={{ width: 70 }} /></td>
                        <td><input inputMode="decimal" value={a.prix_unitaire ?? ""} onChange={(e) => majA("prix_unitaire", e.target.value === "" ? null : +e.target.value.replace(",", "."))} style={{ width: 80 }} /></td>
                        <td><input value={a.reference ?? ""} onChange={(e) => majA("reference", e.target.value)} style={{ width: 100 }} /></td>
                      </tr>);
                  })}</tbody>
                </table></div>
              </details>
              <div><button className="btn petit danger" onClick={() => { const n = sel.filter((_, j) => j !== i); setSel(n); enregistrer(n); }}><Icone nom="poubelle" taille={16} /> Retirer l'ouvrage</button></div>
            </div>
          </details>
        ))}
        {sale && <div><button className="btn primaire" onClick={() => enregistrer()}>Recalculer et enregistrer</button></div>}
      </div>

      {res && (
        <div className="carte pile">
          <div className="ligne"><h3 style={{ margin: 0 }}>Quantités estimées</h3>
            {res.a_completer > 0 ? <Badge statut="attention">{res.a_completer} article(s) à compléter</Badge> : <Badge statut="ok">Complet</Badge>}
            <span className="espace" />{res.total_ht > 0 && <b>Total HT (articles chiffrés) : {fr(res.total_ht)} €</b>}</div>
          <div className="defile-x"><table className="tableau">
            <thead><tr><th>Article</th><th>Base</th><th className="num">Quantité de base</th><th className="num">Quantité (avec pertes)</th><th className="num">À commander</th><th className="num">Montant HT</th></tr></thead>
            <tbody>{res.lignes.map((l, i) => (
              <tr key={i} style={{ opacity: l.statut === "zero" ? 0.55 : 1 }}>
                <td>{l.article}<br /><small>{l.ouvrage}{l.reference ? ` · ${l.reference}` : ""}</small></td>
                <td><small>{l.base_libelle}</small></td>
                <td className="num">{l.quantite_base !== undefined ? fr(l.quantite_base) : "—"}</td>
                {l.statut === "a_completer" || l.statut === "erreur"
                  ? <td colSpan={3}><Badge statut="attention">À compléter : {l.manque}</Badge></td>
                  : <>
                    <td className="num">{fr(l.quantite_totale, l.unite === "u" ? 0 : 2)} {l.unite}</td>
                    <td className="num">{l.conditionnements !== undefined ? `${l.conditionnements} ${l.libelle_conditionnement}` : `${fr(l.quantite_totale, l.unite === "u" ? 0 : 2)} ${l.unite}`}</td>
                    <td className="num">{l.montant_ht !== undefined ? `${fr(l.montant_ht)} €` : "—"}</td>
                  </>}
              </tr>))}</tbody>
          </table></div>
          <small>Les quantités en unités sont arrondies à l'affichage ; les colis sont arrondis au supérieur.</small>
        </div>
      )}
      <div><Link className="btn primaire" to={`/chantiers/${chantier.id}/validation`}>Étape suivante : validation et rapport →</Link></div>
    </div>
  );
}
