import { fr } from "../api";
import { Icone } from "../components/ui";
import { nouvelId } from "../geo";
import type { Calcul, Chantier, DocumentMetre, Pan } from "../types";

const TYPES_LIGNES: Record<string, string> = {
  faitage: "Faîtage", aretier: "Arêtier", noue: "Noue", egout: "Égout / gouttière", rive: "Rive", rive_haute: "Rive haute",
  bris: "Ligne de bris", solin: "Solin / raccord mur", autre: "Autre",
};
const TYPES_OBS: Record<string, string> = {
  cheminee: "Cheminée", fenetre_toit: "Fenêtre de toit", ventilation: "Sortie de ventilation", panneau_solaire: "Panneaux solaires",
  lucarne: "Lucarne", autre: "Autre",
};

/** Saisie des dimensions (sans modèle) et compléments (lignes et obstacles non visibles sur le plan). */
export function SaisieComplements({ doc, calcul, modifier, chantier }: {
  doc: DocumentMetre; calcul: Calcul | null; modifier: (d: DocumentMetre, desc: string) => void; chantier: Chantier;
}) {
  const pansSaisis = doc.pans.filter((p) => p.saisie && !p.contour);
  const majPan = (id: string, s: Partial<NonNullable<Pan["saisie"]>>, extra: Partial<Pan> = {}) =>
    modifier({ ...doc, pans: doc.pans.map((p) => (p.id === id ? { ...p, ...extra, saisie: { ...p.saisie!, ...s } } : p)) }, "Dimensions d'un pan saisies");
  const num = (v: string) => (v === "" ? undefined : parseFloat(v.replace(",", ".")));
  const calc = (id: string) => calcul?.pans.find((p) => p.id === id);
  return (
    <div className="pile">
      <div className="carte pile">
        <div className="ligne"><h3 style={{ margin: 0 }}>Pans saisis par dimensions</h3><span className="espace" />
          <button className="btn petit primaire" onClick={() => {
            const id = nouvelId("p", doc.pans);
            modifier({ ...doc, echelle: chantier.modele ? doc.echelle : { ...doc.echelle, source: "saisie" },
              pans: [...doc.pans, { id, nom: `Pan ${id.slice(1)}`, source_plan: "saisie", source_contour: "manuel", valide: false,
                saisie: { forme: "rectangle", longueur_bas: undefined, rampant: undefined, pente_deg: 35 } }] }, "Pan saisi ajouté");
          }}><Icone nom="plus" taille={16} /> Ajouter un pan</button></div>
        <small>Longueur à l'égout, longueur en tête (trapèze), rampant (longueur mesurée dans la pente) et pente. La surface
          réelle = (bas + haut) / 2 × rampant.</small>
        {pansSaisis.length === 0 ? <p className="discret">Aucun pan saisi.</p> : (
          <div className="defile-x"><table className="tableau">
            <thead><tr><th>Nom</th><th>Forme</th><th>Long. égout (m)</th><th>Long. tête (m)</th><th>Rampant (m)</th><th>Pente (°)</th><th className="num">Surface</th><th>Contrôlé</th><th /></tr></thead>
            <tbody>{pansSaisis.map((p) => (
              <tr key={p.id}>
                <td><input value={p.nom} onChange={(e) => modifier({ ...doc, pans: doc.pans.map((q) => (q.id === p.id ? { ...q, nom: e.target.value } : q)) }, "Pan renommé")} style={{ minWidth: 120 }} /></td>
                <td><select value={p.saisie!.forme} onChange={(e) => majPan(p.id, { forme: e.target.value })} style={{ minWidth: 110 }}>
                  <option value="rectangle">Rectangle</option><option value="trapeze">Trapèze</option><option value="triangle">Triangle</option></select></td>
                <td><input inputMode="decimal" defaultValue={p.saisie!.longueur_bas ?? ""} onBlur={(e) => majPan(p.id, { longueur_bas: num(e.target.value) })} style={{ width: 90 }} /></td>
                <td><input inputMode="decimal" disabled={p.saisie!.forme !== "trapeze"} defaultValue={p.saisie!.longueur_haut ?? ""} onBlur={(e) => majPan(p.id, { longueur_haut: num(e.target.value) })} style={{ width: 90 }} /></td>
                <td><input inputMode="decimal" defaultValue={p.saisie!.rampant ?? ""} onBlur={(e) => majPan(p.id, { rampant: num(e.target.value) })} style={{ width: 90 }} /></td>
                <td><input inputMode="decimal" defaultValue={p.saisie!.pente_deg ?? ""} onBlur={(e) => majPan(p.id, { pente_deg: num(e.target.value) })} style={{ width: 70 }} /></td>
                <td className="num">{calc(p.id) ? `${fr(calc(p.id)!.surface)} m²` : "—"}</td>
                <td><input type="checkbox" checked={!!p.valide} onChange={(e) => modifier({ ...doc, pans: doc.pans.map((q) => (q.id === p.id ? { ...q, valide: e.target.checked } : q)) }, "Validation d'un pan")} /></td>
                <td><button className="btn petit danger" onClick={() => modifier({ ...doc, pans: doc.pans.filter((q) => q.id !== p.id) }, `${p.nom} supprimé`)}><Icone nom="poubelle" taille={16} /></button></td>
              </tr>))}</tbody>
          </table></div>
        )}
      </div>

      <div className="carte pile">
        <div className="ligne"><h3 style={{ margin: 0 }}>Lignes saisies (mètres linéaires)</h3><span className="espace" />
          <button className="btn petit" onClick={() => modifier({ ...doc, lignes_manuelles: [...doc.lignes_manuelles, { id: nouvelId("l", doc.lignes_manuelles), type: "egout", longueur: undefined }] }, "Ligne saisie ajoutée")}>
            <Icone nom="plus" taille={16} /> Ajouter une ligne</button></div>
        <small>Pour les longueurs non dessinées : solins contre un mur, gouttières hors plan, pans saisis par dimensions…
          Elles s'ajoutent aux lignes déduites du plan.</small>
        {doc.lignes_manuelles.length > 0 && (
          <table className="tableau"><tbody>{doc.lignes_manuelles.map((l) => (
            <tr key={l.id}>
              <td><select value={l.type} onChange={(e) => modifier({ ...doc, lignes_manuelles: doc.lignes_manuelles.map((x) => (x.id === l.id ? { ...x, type: e.target.value } : x)) }, "Type de ligne saisie")}>
                {Object.entries(TYPES_LIGNES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td><input inputMode="decimal" defaultValue={l.longueur ?? ""} placeholder="m" onBlur={(e) => modifier({ ...doc, lignes_manuelles: doc.lignes_manuelles.map((x) => (x.id === l.id ? { ...x, longueur: num(e.target.value) } : x)) }, "Longueur saisie")} style={{ width: 110 }} /></td>
              <td className="num"><button className="btn petit danger" onClick={() => modifier({ ...doc, lignes_manuelles: doc.lignes_manuelles.filter((x) => x.id !== l.id) }, "Ligne saisie supprimée")}><Icone nom="poubelle" taille={16} /></button></td>
            </tr>))}</tbody></table>
        )}
      </div>

      <div className="carte pile">
        <div className="ligne"><h3 style={{ margin: 0 }}>Obstacles saisis par dimensions</h3><span className="espace" />
          <button className="btn petit" onClick={() => modifier({ ...doc, obstacles: [...doc.obstacles, { id: nouvelId("o", doc.obstacles), type: "fenetre_toit", nombre: 1, largeur: undefined, longueur: undefined, deduire: false, valide: true, source: "manuel" }] }, "Obstacle saisi ajouté")}>
            <Icone nom="plus" taille={16} /> Ajouter</button></div>
        {doc.obstacles.filter((o) => !o.contour).length > 0 && (
          <div className="defile-x"><table className="tableau">
            <thead><tr><th>Nature</th><th>Nombre</th><th>Largeur (m)</th><th>Hauteur (m)</th><th>Déduire</th><th /></tr></thead>
            <tbody>{doc.obstacles.filter((o) => !o.contour).map((o) => {
              const maj = (x: Partial<typeof o>, d: string) => modifier({ ...doc, obstacles: doc.obstacles.map((q) => (q.id === o.id ? { ...q, ...x } : q)) }, d);
              return (
                <tr key={o.id}>
                  <td><select value={o.type} onChange={(e) => maj({ type: e.target.value }, "Nature d'obstacle")}>{Object.entries(TYPES_OBS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
                  <td><input type="number" min={1} value={o.nombre ?? 1} onChange={(e) => maj({ nombre: +e.target.value }, "Nombre d'obstacles")} style={{ width: 70 }} /></td>
                  <td><input inputMode="decimal" defaultValue={o.largeur ?? ""} onBlur={(e) => maj({ largeur: num(e.target.value) }, "Dimension d'obstacle")} style={{ width: 80 }} /></td>
                  <td><input inputMode="decimal" defaultValue={o.longueur ?? ""} onBlur={(e) => maj({ longueur: num(e.target.value) }, "Dimension d'obstacle")} style={{ width: 80 }} /></td>
                  <td><input type="checkbox" checked={!!o.deduire} onChange={(e) => maj({ deduire: e.target.checked }, "Déduction d'obstacle")} /></td>
                  <td><button className="btn petit danger" onClick={() => modifier({ ...doc, obstacles: doc.obstacles.filter((q) => q.id !== o.id) }, "Obstacle supprimé")}><Icone nom="poubelle" taille={16} /></button></td>
                </tr>);
            })}</tbody>
          </table></div>
        )}
      </div>
      {calcul && (
        <div className="carte">
          <b>Total : {fr(calcul.totaux.surface_nette)} m² nets</b> · égouts {fr(calcul.totaux_lignes.egout)} ml · faîtages {fr(calcul.totaux_lignes.faitage)} ml
        </div>
      )}
    </div>
  );
}
