import { createContext, useContext, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, quandDeconnecte } from "./api";
import { Chargement, Icone, ToastProvider } from "./components/ui";
import { AideProvider, PageGuide } from "./guide/Guide";
import { PageChantier } from "./chantier/PageChantier";
import { Connexion } from "./pages/Connexion";
import { ListeChantiers, NouveauChantier } from "./pages/Chantiers";
import { Parametres } from "./pages/Parametres";
import { Rapports } from "./pages/Rapports";
import { TableauDeBord } from "./pages/TableauDeBord";
import { Traitements } from "./pages/Traitements";

export interface Utilisateur {
  id: number;
  email: string;
  nom: string;
  role: string;
}

const UtilCtx = createContext<Utilisateur | null>(null);
export const useUtilisateur = () => useContext(UtilCtx);

function Navigation({ compteurs, deconnecter }: { compteurs: Record<string, number>; deconnecter: () => void }) {
  const u = useUtilisateur();
  const liens = [
    { to: "/", fin: true, icone: "accueil", texte: "Tableau de bord" },
    { to: "/chantiers/nouveau", icone: "plus", texte: "Nouveau chantier" },
    { to: "/chantiers?vue=en_cours", icone: "liste", texte: "Chantiers" },
    { to: "/traitements", icone: "horloge", texte: "Traitements", n: compteurs.traitements },
    { to: "/chantiers?vue=a_verifier", icone: "verifier", texte: "Métrés à vérifier", n: compteurs.a_verifier },
    { to: "/chantiers?vue=termines", icone: "termine", texte: "Chantiers terminés" },
    { to: "/rapports", icone: "rapport", texte: "Rapports et exports" },
    { to: "/guide", icone: "guide", texte: "Guide de prise de vue" },
    { to: "/parametres", icone: "engrenage", texte: "Paramètres et aide" },
  ];
  const loc = useLocation();
  const actif = (to: string, fin?: boolean) => {
    const [chemin, qs] = to.split("?");
    if (fin) return loc.pathname === chemin;
    if (qs) return loc.pathname === chemin && loc.search.includes(qs);
    return loc.pathname.startsWith(chemin) && !(chemin === "/chantiers" && loc.pathname === "/chantiers/nouveau");
  };
  return (
    <>
      <aside className="barre-laterale">
        <NavLink to="/" className="marque">
          <img src="/icone-192.png" alt="" />
          <div><b>Matt's Métré Toiture</b><span>Matt's Couverture</span></div>
        </NavLink>
        <nav className="nav" aria-label="Navigation principale">
          {liens.map((l) => (
            <NavLink key={l.to} to={l.to} className={() => (actif(l.to, l.fin) ? "active" : "")}>
              <Icone nom={l.icone} /> {l.texte}
              {!!l.n && <span className="compteur">{l.n}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="pied-nav">
          {u?.nom || u?.email}
          <br />
          <button className="lien" onClick={deconnecter}>Se déconnecter</button>
        </div>
      </aside>
      <nav className="nav-mobile" aria-label="Navigation">
        <NavLink to="/" end><Icone nom="accueil" />Accueil</NavLink>
        <NavLink to="/chantiers/nouveau"><Icone nom="plus" />Nouveau</NavLink>
        <NavLink to="/chantiers?vue=en_cours" className={() => (loc.pathname.startsWith("/chantiers") && loc.pathname !== "/chantiers/nouveau" ? "active" : "")}><Icone nom="liste" />Chantiers</NavLink>
        <NavLink to="/guide"><Icone nom="guide" />Guide</NavLink>
        <NavLink to="/parametres"><Icone nom="engrenage" />Plus</NavLink>
      </nav>
    </>
  );
}

export default function App() {
  const [u, setU] = useState<Utilisateur | null | undefined>(undefined);
  const [compteurs, setCompteurs] = useState<Record<string, number>>({});
  const nav = useNavigate();

  useEffect(() => {
    quandDeconnecte(() => setU(null));
    api.get<Utilisateur>("/api/auth/moi").then(setU).catch(() => setU(null));
  }, []);

  useEffect(() => {
    if (!u) return;
    const maj = () =>
      api.get<{ traitements_en_cours: number; a_verifier: number }>("/api/tableau-de-bord")
        .then((d) => setCompteurs({ traitements: d.traitements_en_cours, a_verifier: d.a_verifier }))
        .catch(() => {});
    maj();
    const t = setInterval(maj, 20000);
    return () => clearInterval(t);
  }, [u]);

  const deconnecter = async () => {
    await api.post("/api/auth/deconnexion").catch(() => {});
    setU(null);
    nav("/");
  };

  if (u === undefined) return <Chargement />;
  return (
    <ToastProvider>
      <AideProvider>
        {u === null ? (
          <Connexion surConnexion={setU} />
        ) : (
          <UtilCtx.Provider value={u}>
            <div className="app">
              <Navigation compteurs={compteurs} deconnecter={deconnecter} />
              <main className="contenu">
                <Routes>
                  <Route path="/" element={<TableauDeBord />} />
                  <Route path="/chantiers" element={<ListeChantiers />} />
                  <Route path="/chantiers/nouveau" element={<NouveauChantier />} />
                  <Route path="/chantiers/:id/:etape?" element={<PageChantier />} />
                  <Route path="/traitements" element={<Traitements />} />
                  <Route path="/rapports" element={<Rapports />} />
                  <Route path="/guide/:section?" element={<PageGuide />} />
                  <Route path="/parametres/:onglet?" element={<Parametres deconnecter={deconnecter} />} />
                  <Route path="*" element={<Navigate to="/" />} />
                </Routes>
              </main>
            </div>
          </UtilCtx.Provider>
        )}
      </AideProvider>
    </ToastProvider>
  );
}
