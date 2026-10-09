import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";

// ---------- icônes (traits simples, aucune dépendance) ----------
const chemins: Record<string, string> = {
  accueil: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  plus: "M12 5v14M5 12h14",
  photo: "M4 7h3l2-2h6l2 2h3v12H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  guide: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM8 7h8M8 11h6",
  engrenage: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-1-3-2 .3-1.5-1.5L17 5l-3-1-1 2h-2l-1-2-3 1 .3 2L6 8.5 4 8l-1 3 2 1v2l-2 1 1 3 2-.3 1.5 1.5L7 21l3 1 1-2h2l1 2 3-1-.3-2 1.5-1.5 2 .5 1-3-2-1z",
  verifier: "M9 12l2 2 4-4M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6z",
  termine: "M5 13l4 4L19 7",
  rapport: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7",
  liste: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  toit: "M2 12l10-8 10 8M5 10v10h14V10",
  cube: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5",
  aide: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7v.5M12 17h.01",
  fermer: "M6 6l12 12M18 6L6 18",
  poubelle: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
  telecharger: "M12 3v12M7 10l5 5 5-5M5 21h14",
  crayon: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  regle: "M3 17L17 3l4 4L7 21zM7 13l2 2M10 10l2 2M13 7l2 2",
  cible: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01",
  annuler: "M9 14L4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3",
  refaire: "M15 14l5-5-5-5M20 9H9a5 5 0 0 0 0 10h3",
  sauver: "M5 3h11l3 3v15H5zM8 3v6h7V3M8 21v-7h8v7",
  copier: "M8 8h12v12H8zM4 16V4h12",
  horloge: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
  attention: "M12 3l10 18H2zM12 10v5M12 18h.01",
  main: "M7 11V5a1.5 1.5 0 0 1 3 0v5M10 10V3.5a1.5 1.5 0 0 1 3 0V10M13 10V5a1.5 1.5 0 0 1 3 0v6M16 11V8a1.5 1.5 0 0 1 3 0v6a7 7 0 0 1-14 0v-3a1.5 1.5 0 0 1 3 0",
  zoom: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4M8 11h6M11 8v6",
  calque: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
  porte: "M10 17l5-5-5-5M15 12H3M14 3h6v18h-6",
};

export function Icone({ nom, taille = 20 }: { nom: string; taille?: number }) {
  return (
    <svg width={taille} height={taille} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={chemins[nom] || chemins.aide} />
    </svg>
  );
}

// ---------- notifications ----------
type Toast = { id: number; texte: string; type?: "ok" | "erreur" };
const ToastCtx = createContext<(t: string, type?: "ok" | "erreur") => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [liste, setListe] = useState<Toast[]>([]);
  const ajouter = useCallback((texte: string, type?: "ok" | "erreur") => {
    const id = Date.now() + Math.random();
    setListe((l) => [...l, { id, texte, type }]);
    setTimeout(() => setListe((l) => l.filter((t) => t.id !== id)), type === "erreur" ? 7000 : 3500);
  }, []);
  return (
    <ToastCtx.Provider value={ajouter}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {liste.map((t) => (
          <div key={t.id} className={`toast ${t.type || ""}`}>{t.texte}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ---------- divers ----------
export function Chargement({ texte = "Chargement…" }: { texte?: string }) {
  return (
    <div className="vide"><span className="spinner" /> {texte}</div>
  );
}

export function Progression({ valeur }: { valeur: number }) {
  return (
    <div className="progression" role="progressbar" aria-valuenow={Math.round(valeur)} aria-valuemin={0} aria-valuemax={100}>
      <div style={{ width: `${Math.max(0, Math.min(100, valeur))}%` }} />
    </div>
  );
}

export function Modale({ titre, children, fermer }: { titre: string; children: ReactNode; fermer: () => void }) {
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === "Escape" && fermer();
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [fermer]);
  return (
    <div className="modale-fond" onMouseDown={(e) => e.target === e.currentTarget && fermer()}>
      <div className="modale" role="dialog" aria-label={titre}>
        <div className="ligne" style={{ marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>{titre}</h2>
          <span className="espace" />
          <button className="btn petit" onClick={fermer} aria-label="Fermer"><Icone nom="fermer" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

const STATUT_COULEUR: Record<string, string> = {
  preparation: "", photos: "bleu", traitement: "orange", a_verifier: "orange", valide: "vert", termine: "vert",
  en_attente: "", envoi: "bleu", en_cours: "bleu", telechargement: "bleu", erreur: "rouge", annule: "",
  ok: "vert", attention: "orange", bloquant: "rouge", elevee: "vert", moyenne: "orange", faible: "rouge", saisie: "bleu",
  correct: "vert", a_ameliorer: "orange", insuffisant: "rouge",
};

export function Badge({ statut, children }: { statut: string; children: ReactNode }) {
  return <span className={`badge ${STATUT_COULEUR[statut] ?? ""}`}>{children}</span>;
}

export const LIBELLE_CONFIANCE: Record<string, string> = {
  elevee: "Confiance élevée", moyenne: "Confiance moyenne", faible: "Confiance faible", saisie: "Valeur saisie",
};
export const LIBELLE_SOURCE: Record<string, string> = {
  modele_3d: "Modèle 3D", saisie: "Saisie", estimation: "Estimation",
};
