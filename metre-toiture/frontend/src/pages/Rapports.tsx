import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, dateFr, fr } from "../api";
import { Badge, Chargement } from "../components/ui";
import type { Chantier } from "../types";

export const FORMATS = [
  { f: "csv", t: "CSV (tableur)", d: "Pans, lignes, obstacles et matériaux, séparateur « ; »" },
  { f: "dxf", t: "DXF (DAO)", d: "Plan 2D/3D par calques : pans, faîtages, égouts…" },
  { f: "devis.json", t: "Format devis", d: "Échange avec le logiciel de devis (schéma mmt-devis/1)" },
  { f: "json", t: "JSON complet", d: "Toutes les données du métré" },
  { f: "obj", t: "OBJ (3D)", d: "Pans de toiture en 3D" },
  { f: "geojson", t: "GeoJSON (SIG)", d: "Si modèle 3D géoréférencé" },
];

export function Rapports() {
  const [liste, setListe] = useState<Chantier[] | null>(null);
  useEffect(() => {
    api.get<Chantier[]>("/api/chantiers?statut=a_verifier,valide,termine").then(setListe);
  }, []);
  return (
    <>
      <div className="entete-page"><h1>Rapports et exports</h1></div>
      <div className="alerte info">Le rapport PDF et les exports reflètent l'état actuel du métré. Pour un devis,
        privilégiez les chantiers au statut « Métré validé ».</div>
      {!liste ? <Chargement /> : liste.length === 0 ? <div className="carte vide">Aucun métré disponible.</div> : (
        <div className="carte defile-x">
          <table className="tableau">
            <thead><tr><th>Chantier</th><th>Statut</th><th className="num">Surface</th><th className="masque-mobile">Modifié</th><th>Rapport</th><th>Exports</th></tr></thead>
            <tbody>
              {liste.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/chantiers/${c.id}/validation`}>{c.reference}</Link><br /><small>{c.nom}</small></td>
                  <td><Badge statut={c.statut}>{c.statut_libelle}</Badge></td>
                  <td className="num">{c.resume_metre ? `${fr(c.resume_metre.surface, 1)} m²` : "—"}</td>
                  <td className="masque-mobile">{dateFr(c.modifie_le)}</td>
                  <td><a className="btn petit" href={`/api/chantiers/${c.id}/rapport.pdf`} target="_blank" rel="noreferrer">PDF</a></td>
                  <td><div className="ligne" style={{ gap: 4 }}>
                    {FORMATS.filter((x) => x.f !== "geojson" || c.mode === "3d").map((x) => (
                      <a key={x.f} className="btn petit" href={`/api/chantiers/${c.id}/export/${x.f}`} title={x.d}>{x.f.replace(".json", "")}</a>
                    ))}
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
