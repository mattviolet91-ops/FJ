import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Icone } from "../components/ui";
import { SECTIONS } from "./contenu";

export function PageGuide() {
  const { section } = useParams();
  const courante = SECTIONS.find((s) => s.id === section) || SECTIONS[0];
  const idx = SECTIONS.indexOf(courante);
  useEffect(() => window.scrollTo(0, 0), [courante.id]);
  const groupes = [...new Set(SECTIONS.map((s) => s.groupe))];
  return (
    <>
      <div className="entete-page">
        <h1>Guide pratique</h1>
        <span className="badge bleu">Accessible hors ligne une fois ouvert</span>
      </div>
      <div className="guide-grille">
        <nav className="carte guide-sommaire" aria-label="Sommaire du guide">
          {groupes.map((g) => (
            <div key={g}>
              <div className="groupe">{g}</div>
              {SECTIONS.filter((s) => s.groupe === g).map((s) => (
                <Link key={s.id} to={`/guide/${s.id}`} className={s.id === courante.id ? "active" : ""}>{s.titre}</Link>
              ))}
            </div>
          ))}
        </nav>
        <article className="carte guide-texte">
          <small>{courante.groupe}</small>
          <h2>{courante.titre}</h2>
          {courante.contenu()}
          <div className="ligne" style={{ marginTop: 24 }}>
            {idx > 0 && <Link className="btn" to={`/guide/${SECTIONS[idx - 1].id}`}>← {SECTIONS[idx - 1].titre}</Link>}
            <span className="espace" />
            {idx < SECTIONS.length - 1 && (
              <Link className="btn primaire" to={`/guide/${SECTIONS[idx + 1].id}`}>{SECTIONS[idx + 1].titre} →</Link>
            )}
          </div>
        </article>
      </div>
    </>
  );
}

// ---------- aide contextuelle (tiroir), sans quitter la page en cours ----------
const AideCtx = createContext<(ids: string[]) => void>(() => {});
export const useAide = () => useContext(AideCtx);

export function AideProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[] | null>(null);
  const [actif, setActif] = useState(0);
  const ouvrir = useCallback((liste: string[]) => {
    setIds(liste);
    setActif(0);
  }, []);
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === "Escape" && setIds(null);
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, []);
  const sections = (ids || []).map((i) => SECTIONS.find((s) => s.id === i)).filter(Boolean) as typeof SECTIONS;
  const s = sections[actif];
  return (
    <AideCtx.Provider value={ouvrir}>
      {children}
      {ids && s && (
        <>
          <div className="tiroir-fond" onClick={() => setIds(null)} />
          <aside className="tiroir" aria-label="Aide">
            <header>
              <Icone nom="aide" />
              <h2>Aide</h2>
              <span className="espace" />
              <Link className="btn petit" to={`/guide/${s.id}`} onClick={() => setIds(null)}>Guide complet</Link>
              <button className="btn petit" onClick={() => setIds(null)} aria-label="Fermer l'aide"><Icone nom="fermer" /></button>
            </header>
            {sections.length > 1 && (
              <div className="ligne" style={{ padding: "8px 16px", gap: 6, borderBottom: "1px solid var(--bordure)" }}>
                {sections.map((x, i) => (
                  <button key={x.id} className={`btn petit ${i === actif ? "actif" : ""}`} onClick={() => setActif(i)}>{x.titre}</button>
                ))}
              </div>
            )}
            <div className="corps guide-texte">
              <h2>{s.titre}</h2>
              {s.contenu()}
            </div>
          </aside>
        </>
      )}
    </AideCtx.Provider>
  );
}

export function BoutonAide({ ids, libelle = "Aide" }: { ids: string[]; libelle?: string }) {
  const ouvrir = useAide();
  return (
    <button className="btn petit" onClick={() => ouvrir(ids)} title="Ouvrir l'aide de cette étape">
      <Icone nom="aide" taille={18} /> {libelle}
    </button>
  );
}
