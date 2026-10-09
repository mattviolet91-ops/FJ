import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, dateFr, envoyerFichiers, fr } from "../api";
import { useUtilisateur } from "../App";
import { Chargement, Icone, useToast } from "../components/ui";
import type { Article, Ouvrage } from "../types";

const ONGLETS: Record<string, string> = {
  entreprise: "Entreprise", calcul: "Serveur de calcul", catalogue: "Catalogue matériaux",
  utilisateurs: "Utilisateurs", sauvegardes: "Sauvegardes", compte: "Mon compte", aide: "Aide",
};

export function Parametres({ deconnecter }: { deconnecter: () => void }) {
  const { onglet = "entreprise" } = useParams();
  const nav = useNavigate();
  const u = useUtilisateur();
  return (
    <>
      <div className="entete-page"><h1>Paramètres et aide</h1></div>
      <div className="etapes">
        {Object.entries(ONGLETS).filter(([k]) => u?.role === "admin" || !["utilisateurs", "sauvegardes"].includes(k)).map(([k, v]) => (
          <button key={k} className={k === onglet ? "active" : ""} onClick={() => nav(`/parametres/${k}`)}>{v}</button>
        ))}
      </div>
      {onglet === "entreprise" && <Entreprise />}
      {onglet === "calcul" && <Calcul />}
      {onglet === "catalogue" && <Catalogue />}
      {onglet === "utilisateurs" && <Utilisateurs />}
      {onglet === "sauvegardes" && <Sauvegardes />}
      {onglet === "compte" && <Compte deconnecter={deconnecter} />}
      {onglet === "aide" && <Aide />}
    </>
  );
}

function Entreprise() {
  const [e, setE] = useState<Record<string, string> | null>(null);
  const [logo, setLogo] = useState(0);
  const toast = useToast();
  const admin = useUtilisateur()?.role === "admin";
  useEffect(() => {
    api.get<{ entreprise: Record<string, string>; logo: boolean }>("/api/parametres").then((d) => {
      setE({ nom: "", adresse: "", telephone: "", email: "", siret: "", site: "", ...d.entreprise });
      setLogo(d.logo ? Date.now() : 0);
    });
  }, []);
  if (!e) return <Chargement />;
  const enregistrer = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await api.put("/api/parametres/entreprise", e);
      toast("Informations enregistrées", "ok");
    } catch (err) {
      toast((err as Error).message, "erreur");
    }
  };
  const champs: [string, string][] = [["nom", "Raison sociale"], ["adresse", "Adresse"], ["telephone", "Téléphone"], ["email", "E-mail"], ["siret", "SIRET"], ["site", "Site web"]];
  return (
    <form className="carte pile" onSubmit={enregistrer} style={{ maxWidth: 760 }}>
      <p className="discret">Ces informations apparaissent dans l'en-tête et le pied de page des rapports PDF.</p>
      <div className="grille g2">
        {champs.map(([k, l]) => (
          <label key={k} className="champ">{l}<input value={e[k] || ""} disabled={!admin} onChange={(x) => setE({ ...e, [k]: x.target.value })} /></label>
        ))}
      </div>
      <div className="ligne">
        {logo ? <img src={`/api/parametres/logo?${logo}`} alt="Logo" style={{ height: 48, background: "#fff", border: "1px solid var(--bordure)", borderRadius: 6 }} /> : <small>Aucun logo</small>}
        {admin && (
          <label className="btn petit">Choisir un logo
            <input type="file" accept="image/*" hidden onChange={async (x) => {
              const f = x.target.files?.[0];
              if (!f) return;
              const fd = new FormData();
              fd.append("fichier", f);
              try {
                await api.post("/api/parametres/logo", fd);
                setLogo(Date.now());
                toast("Logo enregistré", "ok");
              } catch (err) {
                toast((err as Error).message, "erreur");
              }
            }} />
          </label>
        )}
      </div>
      {admin && <div><button className="btn primaire">Enregistrer</button></div>}
    </form>
  );
}

function Calcul() {
  const [url, setUrl] = useState("");
  const [jeton, setJeton] = useState("");
  const [defini, setDefini] = useState(false);
  const [etat, setEtat] = useState<Record<string, unknown> | null>(null);
  const toast = useToast();
  const admin = useUtilisateur()?.role === "admin";
  useEffect(() => {
    api.get<{ calcul: { nodeodm_url: string; jeton_defini: boolean } }>("/api/parametres").then((d) => {
      setUrl(d.calcul.nodeodm_url);
      setDefini(d.calcul.jeton_defini);
    });
    api.get<Record<string, unknown>>("/api/calcul/etat").then(setEtat);
  }, []);
  const tester = async () => {
    const r = await api.post<{ ok: boolean; erreur?: string; info?: Record<string, unknown> }>("/api/parametres/calcul/tester", { nodeodm_url: url, nodeodm_token: jeton || null });
    if (r.ok) toast(`Connexion réussie : NodeODM ${r.info?.version}, ${r.info?.cpuCores} cœurs`, "ok");
    else toast(r.erreur || "Échec", "erreur");
  };
  const enregistrer = async () => {
    try {
      await api.put("/api/parametres/calcul", { nodeodm_url: url, nodeodm_token: jeton || null });
      toast("Serveur de calcul enregistré", "ok");
      setEtat(await api.get("/api/calcul/etat"));
    } catch (err) {
      toast((err as Error).message, "erreur");
    }
  };
  return (
    <div className="grille g2">
      <div className="carte pile">
        <h3>Serveur de reconstruction (NodeODM)</h3>
        <label className="champ">Adresse<input value={url} disabled={!admin} onChange={(e) => setUrl(e.target.value)} placeholder="http://localhost:3000" /></label>
        <label className="champ">Jeton d'accès <small>{defini ? "(un jeton est enregistré — laissez vide pour le conserver)" : "(facultatif)"}</small>
          <input type="password" value={jeton} disabled={!admin} onChange={(e) => setJeton(e.target.value)} autoComplete="off" /></label>
        {admin && <div className="ligne"><button className="btn" onClick={tester}>Tester</button><button className="btn primaire" onClick={enregistrer}>Enregistrer</button></div>}
        <small>Compatible avec un NodeODM local (Docker), un serveur dédié, ClusterODM ou un service compatible
          (ex. WebODM Lightning, payant, avec jeton). Voir docs/INSTALLATION.md.</small>
      </div>
      <div className="carte">
        <h3>État actuel</h3>
        {!etat ? <Chargement /> : etat.disponible ? (
          <div className="pile">
            <div className="alerte ok"><b>Disponible</b>{String(etat.url)}</div>
            <div className="indicateur"><span>Moteur</span><b>{String(etat.moteur)} {String(etat.version_moteur)}</b></div>
            <div className="indicateur"><span>Cœurs / mémoire</span><b>{String(etat.coeurs)} / {fr(Number(etat.memoire_go), 1)} Go</b></div>
            <div className="indicateur"><span>Tâches en file</span><b>{String(etat.file_attente)}</b></div>
          </div>
        ) : <div className="alerte erreur"><b>Injoignable</b>{String(etat.erreur)}</div>}
      </div>
    </div>
  );
}

const ARTICLE_VIDE: Article = { nom: "", base: "surface", unite: "u", consommation: null, perte_pct: null, categorie: "couverture", actif: true };

function Catalogue() {
  const [data, setData] = useState<{ ouvrages: Ouvrage[]; bases: Record<string, string> } | null>(null);
  const [edit, setEdit] = useState<Ouvrage | null>(null);
  const toast = useToast();
  const charger = () => api.get<{ ouvrages: Ouvrage[]; bases: Record<string, string> }>("/api/ouvrages").then(setData);
  useEffect(() => { charger(); }, []);
  if (!data) return <Chargement />;
  const enregistrer = async () => {
    if (!edit) return;
    try {
      if (edit.id) await api.put(`/api/ouvrages/${edit.id}`, edit);
      else await api.post("/api/ouvrages", edit);
      toast("Ouvrage enregistré", "ok");
      setEdit(null);
      charger();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  if (edit) {
    const majA = (i: number, k: keyof Article, v: unknown) => setEdit({ ...edit, articles: edit.articles.map((a, j) => (j === i ? { ...a, [k]: v } : a)) });
    const majP = (i: number, k: string, v: unknown) => setEdit({ ...edit, parametres: edit.parametres.map((a, j) => (j === i ? { ...a, [k]: v } : a)) });
    const num = (v: string) => (v === "" ? null : isNaN(+v.replace(",", ".")) ? v : +v.replace(",", "."));
    return (
      <div className="carte pile">
        <div className="ligne"><h3 style={{ margin: 0 }}>{edit.id ? "Modifier l'ouvrage" : "Nouvel ouvrage"}</h3><span className="espace" />
          <button className="btn" onClick={() => setEdit(null)}>Annuler</button><button className="btn primaire" onClick={enregistrer}>Enregistrer</button></div>
        <div className="grille g2">
          <label className="champ">Nom<input value={edit.nom} onChange={(e) => setEdit({ ...edit, nom: e.target.value })} /></label>
          <label className="champ">Description<input value={edit.description || ""} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></label>
        </div>
        <h4>Paramètres (valeurs par défaut, modifiables à chaque chantier)</h4>
        <div className="defile-x"><table className="tableau">
          <thead><tr><th>Clé (formules)</th><th>Libellé</th><th>Unité</th><th>Valeur par défaut</th><th /></tr></thead>
          <tbody>{edit.parametres.map((p, i) => (
            <tr key={i}>
              <td><input value={p.cle} onChange={(e) => majP(i, "cle", e.target.value)} style={{ minWidth: 120 }} /></td>
              <td><input value={p.libelle} onChange={(e) => majP(i, "libelle", e.target.value)} style={{ minWidth: 200 }} /></td>
              <td><input value={p.unite} onChange={(e) => majP(i, "unite", e.target.value)} style={{ width: 70 }} /></td>
              <td><input inputMode="decimal" value={p.valeur ?? ""} onChange={(e) => majP(i, "valeur", e.target.value === "" ? null : +e.target.value.replace(",", "."))} style={{ width: 100 }} placeholder="à saisir" /></td>
              <td><button className="btn petit danger" onClick={() => setEdit({ ...edit, parametres: edit.parametres.filter((_, j) => j !== i) })}><Icone nom="poubelle" taille={16} /></button></td>
            </tr>))}</tbody>
        </table></div>
        <div><button className="btn petit" onClick={() => setEdit({ ...edit, parametres: [...edit.parametres, { cle: "", libelle: "", unite: "", valeur: null }] })}>+ Paramètre</button></div>
        <h4>Articles</h4>
        <small>Consommation : un nombre (ex. 13,5) ou une formule utilisant les clés des paramètres (ex. <code>1/pureau</code>).</small>
        <div className="defile-x"><table className="tableau">
          <thead><tr><th>Article</th><th>Base de calcul</th><th>Unité</th><th>Consommation</th><th>Perte %</th><th>Condit.</th><th>Réf.</th><th>Prix HT</th><th /></tr></thead>
          <tbody>{edit.articles.map((a, i) => (
            <tr key={i}>
              <td><input value={a.nom} onChange={(e) => majA(i, "nom", e.target.value)} style={{ minWidth: 170 }} /></td>
              <td><select value={a.base} onChange={(e) => majA(i, "base", e.target.value)} style={{ minWidth: 190 }}>{Object.entries(data.bases).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td><input value={a.unite} onChange={(e) => majA(i, "unite", e.target.value)} style={{ width: 60 }} /></td>
              <td><input value={a.consommation ?? ""} onChange={(e) => majA(i, "consommation", num(e.target.value))} style={{ width: 130 }} placeholder="fiche fabricant" /></td>
              <td><input inputMode="decimal" value={a.perte_pct ?? ""} onChange={(e) => majA(i, "perte_pct", num(e.target.value))} style={{ width: 70 }} /></td>
              <td><input inputMode="decimal" value={a.conditionnement ?? ""} onChange={(e) => majA(i, "conditionnement", num(e.target.value))} style={{ width: 70 }} /></td>
              <td><input value={a.reference ?? ""} onChange={(e) => majA(i, "reference", e.target.value)} style={{ width: 100 }} /></td>
              <td><input inputMode="decimal" value={a.prix_unitaire ?? ""} onChange={(e) => majA(i, "prix_unitaire", e.target.value === "" ? null : +e.target.value.replace(",", "."))} style={{ width: 80 }} /></td>
              <td><button className="btn petit danger" onClick={() => setEdit({ ...edit, articles: edit.articles.filter((_, j) => j !== i) })}><Icone nom="poubelle" taille={16} /></button></td>
            </tr>))}</tbody>
        </table></div>
        <div><button className="btn petit" onClick={() => setEdit({ ...edit, articles: [...edit.articles, { ...ARTICLE_VIDE }] })}>+ Article</button></div>
      </div>
    );
  }
  return (
    <div className="carte">
      <div className="ligne"><p className="discret" style={{ margin: 0 }}>Les ouvrages fournis ne contiennent que la structure de calcul : les consommations et prix
        sont à renseigner à partir de vos fiches fabricants et tarifs.</p><span className="espace" />
        <button className="btn primaire" onClick={() => setEdit({ nom: "Nouvel ouvrage", parametres: [], articles: [{ ...ARTICLE_VIDE }] })}>+ Ouvrage</button></div>
      <table className="tableau" style={{ marginTop: 10 }}>
        <thead><tr><th>Ouvrage</th><th className="num">Articles</th><th /></tr></thead>
        <tbody>{data.ouvrages.map((o) => (
          <tr key={o.id}>
            <td><b>{o.nom}</b><br /><small>{o.description}</small></td>
            <td className="num">{o.articles.length}</td>
            <td className="num"><div className="ligne" style={{ justifyContent: "flex-end" }}>
              <button className="btn petit" onClick={() => setEdit(JSON.parse(JSON.stringify(o)))}><Icone nom="crayon" taille={16} /> Modifier</button>
              <button className="btn petit" onClick={() => setEdit({ ...JSON.parse(JSON.stringify(o)), id: undefined, nom: `${o.nom} (copie)` })}><Icone nom="copier" taille={16} /></button>
              <button className="btn petit danger" onClick={async () => { if (confirm(`Supprimer l'ouvrage « ${o.nom} » du catalogue ?`)) { await api.del(`/api/ouvrages/${o.id}`); charger(); } }}><Icone nom="poubelle" taille={16} /></button>
            </div></td>
          </tr>))}</tbody>
      </table>
    </div>
  );
}

function Utilisateurs() {
  const [liste, setListe] = useState<{ id: number; email: string; nom: string; role: string; actif: boolean }[] | null>(null);
  const [n, setN] = useState({ email: "", nom: "", mot_de_passe: "", role: "utilisateur" });
  const toast = useToast();
  const charger = () => api.get<typeof liste>("/api/utilisateurs").then(setListe);
  useEffect(() => { charger(); }, []);
  const creer = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/api/utilisateurs", n);
      setN({ email: "", nom: "", mot_de_passe: "", role: "utilisateur" });
      toast("Utilisateur créé", "ok");
      charger();
    } catch (err) {
      toast((err as Error).message, "erreur");
    }
  };
  if (!liste) return <Chargement />;
  return (
    <div className="grille g2">
      <div className="carte"><h3>Comptes</h3>
        <table className="tableau"><tbody>{liste.map((u) => (
          <tr key={u.id}><td>{u.nom || "—"}<br /><small>{u.email}</small></td><td>{u.role === "admin" ? "Administrateur" : "Utilisateur"}</td>
            <td className="num"><button className="btn petit" onClick={async () => {
              try { await api.patch(`/api/utilisateurs/${u.id}`, { actif: !u.actif }); charger(); } catch (e) { toast((e as Error).message, "erreur"); }
            }}>{u.actif ? "Désactiver" : "Réactiver"}</button></td></tr>))}</tbody></table>
      </div>
      <form className="carte pile" onSubmit={creer}><h3>Ajouter un compte</h3>
        <label className="champ">Nom<input value={n.nom} onChange={(e) => setN({ ...n, nom: e.target.value })} /></label>
        <label className="champ">E-mail<input type="email" required value={n.email} onChange={(e) => setN({ ...n, email: e.target.value })} /></label>
        <label className="champ">Mot de passe provisoire (10 caractères min.)<input type="password" required minLength={10} value={n.mot_de_passe} onChange={(e) => setN({ ...n, mot_de_passe: e.target.value })} autoComplete="new-password" /></label>
        <label className="champ">Rôle<select value={n.role} onChange={(e) => setN({ ...n, role: e.target.value })}><option value="utilisateur">Utilisateur</option><option value="admin">Administrateur</option></select></label>
        <div><button className="btn primaire">Créer</button></div>
      </form>
    </div>
  );
}

function Sauvegardes() {
  const [liste, setListe] = useState<{ nom: string; taille: number; date: string }[] | null>(null);
  const [encours, setEncours] = useState(false);
  const toast = useToast();
  const charger = () => api.get<typeof liste>("/api/sauvegardes").then(setListe);
  useEffect(() => { charger(); }, []);
  const creer = async (complete: boolean) => {
    setEncours(true);
    try {
      await api.post(`/api/sauvegardes?complete=${complete}`);
      toast("Sauvegarde créée", "ok");
      charger();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
    setEncours(false);
  };
  return (
    <div className="carte pile">
      <p className="discret">Une sauvegarde de la base de données est faite automatiquement chaque jour. Les sauvegardes complètes
        incluent photos et modèles 3D (volumineuses). Copiez régulièrement les sauvegardes hors du serveur.</p>
      <div className="ligne"><button className="btn" disabled={encours} onClick={() => creer(false)}>Sauvegarder la base</button>
        <button className="btn primaire" disabled={encours} onClick={() => creer(true)}>Sauvegarde complète</button>{encours && <span className="spinner" />}</div>
      {!liste ? <Chargement /> : (
        <table className="tableau"><tbody>{liste.map((s) => (
          <tr key={s.nom}><td>{s.nom}</td><td>{dateFr(s.date.replace(/\.\d+$/, ""))}</td><td className="num">{(s.taille / 1e6).toFixed(1)} Mo</td>
            <td className="num"><a className="btn petit" href={`/api/sauvegardes/${s.nom}`}><Icone nom="telecharger" taille={16} /></a></td></tr>))}</tbody></table>
      )}
    </div>
  );
}

function Compte({ deconnecter }: { deconnecter: () => void }) {
  const [a, setA] = useState("");
  const [n, setN] = useState("");
  const toast = useToast();
  const u = useUtilisateur();
  return (
    <form className="carte pile" style={{ maxWidth: 520 }} onSubmit={async (e) => {
      e.preventDefault();
      try { await api.post("/api/auth/mot-de-passe", { ancien: a, nouveau: n }); toast("Mot de passe modifié", "ok"); setA(""); setN(""); } catch (err) { toast((err as Error).message, "erreur"); }
    }}>
      <p>Connecté en tant que <b>{u?.email}</b></p>
      <label className="champ">Mot de passe actuel<input type="password" value={a} onChange={(e) => setA(e.target.value)} autoComplete="current-password" required /></label>
      <label className="champ">Nouveau mot de passe<input type="password" value={n} onChange={(e) => setN(e.target.value)} minLength={10} autoComplete="new-password" required /></label>
      <div className="ligne"><button className="btn primaire">Modifier</button><span className="espace" /><button type="button" className="btn" onClick={deconnecter}><Icone nom="porte" /> Se déconnecter</button></div>
    </form>
  );
}

function Aide() {
  return (
    <div className="grille g2">
      <div className="carte pile">
        <h3>Guide pratique</h3>
        <p>Le guide couvre la prise de vue, la préparation, l'import, la correction des mesures et la validation avant
          devis. Il est aussi accessible depuis chaque étape d'un chantier (bouton « Aide »).</p>
        <Link className="btn primaire" to="/guide">Ouvrir le guide</Link>
      </div>
      <div className="carte pile">
        <h3>Sur le chantier</h3>
        <p>Installez l'application sur l'écran d'accueil de la tablette ou du téléphone (menu du navigateur →
          « Ajouter à l'écran d'accueil ») : le guide et les plans de vol déjà ouverts restent consultables sans réseau.</p>
        <p className="discret">Documentation technique : dossier <code>metre-toiture/docs</code> (installation, utilisation,
          maintenance, coûts, limites).</p>
      </div>
    </div>
  );
}

// utilisé par la page chantier pour envoyer des photos
export { envoyerFichiers };
