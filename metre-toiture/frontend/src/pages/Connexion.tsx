import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Utilisateur } from "../App";

export function Connexion({ surConnexion }: { surConnexion: (u: Utilisateur) => void }) {
  const [initialise, setInitialise] = useState<boolean | null>(null);
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [mdp, setMdp] = useState("");
  const [mdp2, setMdp2] = useState("");
  const [erreur, setErreur] = useState("");
  const [encours, setEncours] = useState(false);

  useEffect(() => {
    api.get<{ initialise: boolean }>("/api/auth/etat").then((d) => setInitialise(d.initialise)).catch(() => setInitialise(true));
  }, []);

  const envoyer = async (e: FormEvent) => {
    e.preventDefault();
    setErreur("");
    if (!initialise && mdp !== mdp2) return setErreur("Les deux mots de passe ne correspondent pas.");
    setEncours(true);
    try {
      const u = initialise
        ? await api.post<Utilisateur>("/api/auth/connexion", { email, mot_de_passe: mdp })
        : await api.post<Utilisateur>("/api/auth/initialiser", { email, nom, mot_de_passe: mdp });
      surConnexion(u);
    } catch (err) {
      setErreur((err as Error).message);
    } finally {
      setEncours(false);
    }
  };

  return (
    <div className="connexion">
      <form className="carte pile" onSubmit={envoyer}>
        <div className="ligne">
          <img src="/icone-192.png" alt="" width={44} height={44} style={{ borderRadius: 10 }} />
          <div>
            <h1 style={{ margin: 0, fontSize: "1.3rem" }}>Matt's Métré Toiture</h1>
            <small>Métrés de toiture par drone</small>
          </div>
        </div>
        {initialise === false && (
          <div className="alerte info">
            <b>Première utilisation</b>Créez le compte administrateur de l'application.
          </div>
        )}
        {initialise === false && (
          <label className="champ">Nom<input value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name" /></label>
        )}
        <label className="champ">E-mail
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        </label>
        <label className="champ">Mot de passe {initialise === false && <small>(10 caractères minimum)</small>}
          <input type="password" required value={mdp} onChange={(e) => setMdp(e.target.value)}
            autoComplete={initialise ? "current-password" : "new-password"} minLength={initialise ? undefined : 10} />
        </label>
        {initialise === false && (
          <label className="champ">Confirmer le mot de passe
            <input type="password" required value={mdp2} onChange={(e) => setMdp2(e.target.value)} autoComplete="new-password" />
          </label>
        )}
        {erreur && <div className="alerte erreur">{erreur}</div>}
        <button className="btn primaire grand" disabled={encours || initialise === null}>
          {initialise === false ? "Créer le compte" : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
