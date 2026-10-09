import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Chargement, Icone, Modale, useToast } from "../components/ui";
import { BoutonAide } from "../guide/Guide";
import { AIDE_ETAPES } from "../guide/contenu";
import type { Chantier } from "../types";
import { EtapeMateriaux } from "./Materiaux";
import { EtapeMetre } from "./Metre";
import { EtapePhotos } from "./Photos";
import { EtapePreparation } from "./Preparation";
import { EtapeTraitement } from "./Traitement";
import { EtapeValidation } from "./Validation";

const ETAPES = [
  { id: "preparation", titre: "Préparation" },
  { id: "photos", titre: "Photos" },
  { id: "traitement", titre: "Traitement" },
  { id: "metre", titre: "Métré" },
  { id: "materiaux", titre: "Matériaux" },
  { id: "validation", titre: "Validation & rapport" },
];

function etapeParDefaut(c: Chantier) {
  if (c.mode === "saisie") return "metre";
  return ({ preparation: "preparation", photos: "photos", traitement: "traitement", a_verifier: "metre",
    valide: "validation", termine: "validation" } as Record<string, string>)[c.statut] || "preparation";
}

function etapeFaite(c: Chantier, id: string) {
  const ordre = ["preparation", "photos", "traitement", "a_verifier", "valide", "termine"];
  const i = ordre.indexOf(c.statut);
  switch (id) {
    case "preparation": return !!c.plan_vol || i >= 1;
    case "photos": return (c.nb_photos || 0) > 0;
    case "traitement": return !!c.modele;
    case "metre": return i >= 4;
    case "validation": return i >= 4;
    default: return false;
  }
}

export function PageChantier() {
  const { id, etape } = useParams();
  const [c, setC] = useState<Chantier | null>(null);
  const [erreur, setErreur] = useState("");
  const [infos, setInfos] = useState(false);
  const nav = useNavigate();
  const toast = useToast();
  const recharger = useCallback(() => api.get<Chantier>(`/api/chantiers/${id}`).then(setC).catch((e) => setErreur(e.message)), [id]);
  useEffect(() => {
    recharger();
  }, [recharger]);
  if (erreur) return <div className="alerte erreur">{erreur}</div>;
  if (!c) return <Chargement />;
  const courante = etape || etapeParDefaut(c);
  const etapes = ETAPES.filter((e) => !(c.mode === "saisie" && (e.id === "photos" || e.id === "traitement")));

  const dupliquer = async () => {
    if (!confirm("Dupliquer ce chantier (informations, métré et matériaux) ?")) return;
    const d = await api.post<Chantier>(`/api/chantiers/${c.id}/dupliquer`);
    toast(`Chantier dupliqué : ${d.reference}`, "ok");
    nav(`/chantiers/${d.id}`);
  };
  const archiver = async () => {
    if (!confirm("Archiver ce chantier ? Il restera consultable dans « Archivés ».")) return;
    await api.del(`/api/chantiers/${c.id}`);
    toast("Chantier archivé");
    nav("/chantiers");
  };

  return (
    <>
      <div className="entete-page">
        <div>
          <small>{c.reference}{c.client_nom ? ` · ${c.client_nom}` : ""}{c.adresse ? ` · ${c.adresse}` : ""}</small>
          <h1>{c.nom}</h1>
        </div>
        <Badge statut={c.statut}>{c.statut_libelle}</Badge>
        {c.archive && <Badge statut="annule">Archivé</Badge>}
        <div className="actions">
          <BoutonAide ids={AIDE_ETAPES[courante] || ["a-preparer"]} />
          <button className="btn petit" onClick={() => setInfos(true)}><Icone nom="crayon" taille={16} /> Infos</button>
          <button className="btn petit" onClick={dupliquer}><Icone nom="copier" taille={16} /> Dupliquer</button>
          {c.archive
            ? <button className="btn petit" onClick={async () => { await api.patch(`/api/chantiers/${c.id}`, { archive: false }); recharger(); }}>Désarchiver</button>
            : <button className="btn petit" onClick={archiver}>Archiver</button>}
        </div>
      </div>
      <nav className="etapes" aria-label="Étapes du chantier">
        {etapes.map((e, i) => (
          <button key={e.id} className={`${courante === e.id ? "active" : ""} ${etapeFaite(c, e.id) ? "fait" : ""}`}
            onClick={() => nav(`/chantiers/${c.id}/${e.id}`)}>
            <span className="num">{etapeFaite(c, e.id) && courante !== e.id ? "✓" : i + 1}</span>{e.titre}
          </button>
        ))}
      </nav>
      {courante === "preparation" && <EtapePreparation chantier={c} maj={recharger} />}
      {courante === "photos" && <EtapePhotos chantier={c} maj={recharger} />}
      {courante === "traitement" && <EtapeTraitement chantier={c} maj={recharger} />}
      {courante === "metre" && <EtapeMetre chantier={c} maj={recharger} />}
      {courante === "materiaux" && <EtapeMateriaux chantier={c} />}
      {courante === "validation" && <EtapeValidation chantier={c} maj={recharger} />}
      {infos && <InfosChantier c={c} fermer={() => setInfos(false)} maj={recharger} />}
    </>
  );
}

function InfosChantier({ c, fermer, maj }: { c: Chantier; fermer: () => void; maj: () => void }) {
  const [f, setF] = useState({ nom: c.nom, client_nom: c.client_nom, client_tel: c.client_tel, client_email: c.client_email,
    adresse: c.adresse, notes: c.notes || "", mode: c.mode });
  const [journal, setJournal] = useState<{ action: string; detail: string; date: string; utilisateur: string | null }[]>([]);
  const toast = useToast();
  const [suppr, setSuppr] = useState("");
  const nav = useNavigate();
  useEffect(() => { api.get<typeof journal>(`/api/chantiers/${c.id}/journal`).then(setJournal); }, [c.id]);
  return (
    <Modale titre="Informations du chantier" fermer={fermer}>
      <div className="pile">
        <label className="champ">Nom<input value={f.nom} onChange={(e) => setF({ ...f, nom: e.target.value })} /></label>
        <div className="grille g2">
          <label className="champ">Client<input value={f.client_nom} onChange={(e) => setF({ ...f, client_nom: e.target.value })} /></label>
          <label className="champ">Téléphone<input value={f.client_tel} onChange={(e) => setF({ ...f, client_tel: e.target.value })} /></label>
        </div>
        <label className="champ">E-mail<input value={f.client_email} onChange={(e) => setF({ ...f, client_email: e.target.value })} /></label>
        <label className="champ">Adresse<input value={f.adresse} onChange={(e) => setF({ ...f, adresse: e.target.value })} /></label>
        <label className="champ">Méthode de métré<select value={f.mode} onChange={(e) => setF({ ...f, mode: e.target.value as Chantier["mode"] })}>
          <option value="3d">Reconstruction 3D</option><option value="photo">Photo unique (estimation)</option><option value="saisie">Saisie manuelle</option></select></label>
        <label className="champ">Notes<textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
        <div className="ligne"><button className="btn primaire" onClick={async () => { await api.patch(`/api/chantiers/${c.id}`, f); toast("Enregistré", "ok"); maj(); fermer(); }}>Enregistrer</button></div>
        <details><summary>Historique des actions</summary>
          <table className="tableau"><tbody>{journal.map((j, i) => (
            <tr key={i}><td><small>{new Date(j.date + "Z").toLocaleString("fr-FR")}</small></td><td>{j.action.replace(/_/g, " ")}</td><td><small>{j.detail} {j.utilisateur ? `— ${j.utilisateur}` : ""}</small></td></tr>))}</tbody></table>
        </details>
        {c.archive && (
          <details><summary style={{ color: "var(--rouge)" }}>Supprimer définitivement</summary>
            <p className="discret">Supprime le chantier, ses photos, son modèle 3D et ses métrés. Irréversible. Saisissez la référence <b>{c.reference}</b> pour confirmer.</p>
            <div className="ligne"><input value={suppr} onChange={(e) => setSuppr(e.target.value)} style={{ maxWidth: 220 }} />
              <button className="btn danger" disabled={suppr !== c.reference} onClick={async () => {
                await api.del(`/api/chantiers/${c.id}?definitif=true&confirmation=${encodeURIComponent(suppr)}`);
                toast("Chantier supprimé");
                nav("/chantiers?vue=archives");
              }}>Supprimer</button></div>
          </details>
        )}
      </div>
    </Modale>
  );
}
