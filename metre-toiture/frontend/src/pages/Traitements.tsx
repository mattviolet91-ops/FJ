import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, dateFr, duree } from "../api";
import { Badge, Chargement, Progression, useToast } from "../components/ui";
import type { Traitement } from "../types";

export function tempsRestant(t: Traitement): string | null {
  if (!t.debut || !t.duree_estimee_s || !["envoi", "en_cours", "telechargement"].includes(t.statut)) return null;
  const ecoule = (Date.now() - new Date(t.debut + "Z").getTime()) / 1000;
  const reste = t.duree_estimee_s - ecoule;
  return reste > 0 ? `≈ ${duree(reste)} restantes (estimation)` : "Dépassement de l'estimation — calcul toujours en cours";
}

export function Traitements() {
  const [liste, setListe] = useState<Traitement[] | null>(null);
  const [tous, setTous] = useState(false);
  const toast = useToast();
  useEffect(() => {
    const maj = () => api.get<Traitement[]>(`/api/traitements${tous ? "" : "?actifs=true"}`).then(setListe).catch(() => {});
    maj();
    const t = setInterval(maj, 5000);
    return () => clearInterval(t);
  }, [tous]);
  const annuler = async (id: number) => {
    if (!confirm("Annuler ce traitement ? Le calcul en cours sera perdu.")) return;
    try {
      await api.post(`/api/traitements/${id}/annuler`);
      toast("Annulation demandée");
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
  };
  return (
    <>
      <div className="entete-page">
        <h1>Traitements</h1>
        <div className="actions">
          <button className={`btn petit ${!tous ? "actif" : ""}`} onClick={() => setTous(false)}>En cours</button>
          <button className={`btn petit ${tous ? "actif" : ""}`} onClick={() => setTous(true)}>Historique</button>
        </div>
      </div>
      {!liste ? <Chargement /> : liste.length === 0 ? (
        <div className="carte vide">Aucun traitement {tous ? "" : "en cours"}.</div>
      ) : liste.map((t) => (
        <div key={t.id} className="carte pile">
          <div className="ligne">
            <b>{t.type === "reconstruction" ? "Reconstruction 3D" : "Détection des pans"}</b>
            {t.chantier && <Link to={`/chantiers/${t.chantier.id}/traitement`}>{t.chantier.reference} — {t.chantier.nom}</Link>}
            <span className="espace" />
            <Badge statut={t.statut}>{t.statut_libelle}</Badge>
          </div>
          {["en_attente", "envoi", "en_cours", "telechargement"].includes(t.statut) && <Progression valeur={t.progression} />}
          <div className="ligne">
            <small>{t.message}</small>
            <span className="espace" />
            <small>{tempsRestant(t) || (t.fin ? `Terminé le ${dateFr(t.fin)}` : `Créé le ${dateFr(t.cree_le)}`)}</small>
          </div>
          {t.nb_images > 0 && <small>{t.nb_images} photos · préréglage {(t.options?.preset as string) || "—"}</small>}
          {t.statut === "erreur" && <pre style={{ whiteSpace: "pre-wrap", fontSize: ".8rem", maxHeight: 200, overflow: "auto", background: "var(--rouge-pale)", padding: 8, borderRadius: 6 }}>{t.erreur}</pre>}
          {["en_attente", "envoi", "en_cours"].includes(t.statut) && (
            <div><button className="btn petit danger" onClick={() => annuler(t.id)}>Annuler</button></div>
          )}
        </div>
      ))}
    </>
  );
}
