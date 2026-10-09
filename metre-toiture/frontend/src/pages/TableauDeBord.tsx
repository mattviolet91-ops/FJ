import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, dateFr } from "../api";
import { Badge, Chargement, Icone } from "../components/ui";
import type { Chantier } from "../types";

interface Tableau {
  traitements_en_cours: number;
  a_verifier: number;
  termines: number;
  en_preparation: number;
  total: number;
  recents: Chantier[];
  utilisateur: { nom: string };
}

export function TableauDeBord() {
  const [d, setD] = useState<Tableau | null>(null);
  const nav = useNavigate();
  const [calcul, setCalcul] = useState<{ disponible: boolean; erreur?: string } | null>(null);
  useEffect(() => {
    api.get<Tableau>("/api/tableau-de-bord").then(setD);
    api.get<{ disponible: boolean; erreur?: string }>("/api/calcul/etat").then(setCalcul).catch(() => {});
  }, []);
  if (!d) return <Chargement />;
  const tuiles = [
    { to: "/chantiers/nouveau", icone: "plus", titre: "Nouveau chantier", texte: "Créer, préparer le vol", principale: true },
    { to: "/chantiers?vue=en_cours", icone: "photo", titre: "Importer des photos", texte: `${d.en_preparation} chantier(s) en préparation` },
    { to: "/guide", icone: "guide", titre: "Guide de prise de vue", texte: "Réussir ses photos de toiture" },
    { to: "/traitements", icone: "horloge", titre: "Traitements en cours", chiffre: d.traitements_en_cours },
    { to: "/chantiers?vue=a_verifier", icone: "verifier", titre: "Métrés à vérifier", chiffre: d.a_verifier },
    { to: "/chantiers?vue=termines", icone: "termine", titre: "Chantiers terminés", chiffre: d.termines },
    { to: "/rapports", icone: "rapport", titre: "Rapports et exports", texte: "PDF, CSV, DXF, devis" },
    { to: "/parametres", icone: "engrenage", titre: "Paramètres et aide", texte: "Entreprise, catalogue, calcul" },
  ];
  return (
    <>
      <div className="entete-page">
        <h1>Bonjour{d.utilisateur.nom ? ` ${d.utilisateur.nom}` : ""}</h1>
      </div>
      {calcul && !calcul.disponible && (
        <div className="alerte attention">
          <b>Serveur de calcul 3D injoignable</b>
          Les reconstructions ne peuvent pas démarrer (elles attendront). Le métré par photo unique ou par saisie
          reste disponible. <Link to="/parametres/calcul">Vérifier la configuration</Link>
        </div>
      )}
      <div className="tuiles">
        {tuiles.map((t) => (
          <Link key={t.titre} to={t.to} className={`tuile ${t.principale ? "principale" : ""}`}>
            <span className="icone"><Icone nom={t.icone} /></span>
            {t.chiffre !== undefined ? <span className="chiffre">{t.chiffre}</span> : null}
            <b>{t.titre}</b>
            {t.texte && <small>{t.texte}</small>}
          </Link>
        ))}
      </div>
      <div className="carte" style={{ marginTop: 18 }}>
        <div className="ligne"><h2 style={{ margin: 0 }}>Chantiers récents</h2><span className="espace" />
          <Link to="/chantiers?vue=tous">Tout voir</Link></div>
        {d.recents.length === 0 ? (
          <div className="vide">Aucun chantier pour l'instant. <Link to="/chantiers/nouveau">Créer le premier</Link></div>
        ) : (
          <div className="defile-x" style={{ marginTop: 8 }}>
            <table className="tableau">
              <thead><tr><th>Référence</th><th>Chantier</th><th className="masque-mobile">Client</th><th>Statut</th><th className="masque-mobile">Modifié</th></tr></thead>
              <tbody>
                {d.recents.map((c) => (
                  <tr key={c.id} className="cliquable" onClick={() => nav(`/chantiers/${c.id}`)}>
                    <td><Link to={`/chantiers/${c.id}`}>{c.reference}</Link></td>
                    <td>{c.nom}</td>
                    <td className="masque-mobile">{c.client_nom || "—"}</td>
                    <td><Badge statut={c.statut}>{c.statut_libelle}</Badge></td>
                    <td className="masque-mobile">{dateFr(c.modifie_le)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <p className="discret" style={{ marginTop: 14 }}>{d.total} chantier(s) actif(s)</p>
    </>
  );
}
