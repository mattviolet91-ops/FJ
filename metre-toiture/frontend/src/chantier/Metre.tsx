import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, fr } from "../api";
import { Badge, Chargement, Icone, LIBELLE_CONFIANCE, LIBELLE_SOURCE, Modale, useToast } from "../components/ui";
import { azimutDe, COULEURS_LIGNES, dansPolygone, dist, nouvelId, orientation, penteDe,
  planDepuisPente, projeterSurSegment, zSurPans } from "../geo";
import type { Calcul, Chantier, DocumentMetre, MetreComplet, Pan, Pt, Traitement } from "../types";
import { EditeurPlan, Outil, Selection } from "./EditeurPlan";
import { SaisieComplements } from "./Saisie";

const Vue3D = lazy(() => import("./Vue3D"));

const CONSIGNES: Record<Outil, string> = {
  selection: "Touchez un pan, une ligne ou un obstacle pour le sélectionner. Glissez un sommet pour corriger le contour.",
  pan: "Touchez chaque angle du pan, puis « Terminer » (ou touchez le premier point).",
  obstacle: "Touchez les angles de l'obstacle (fenêtre de toit, cheminée…), puis « Terminer ».",
  point: "Touchez une arête du pan sélectionné pour y ajouter un sommet.",
  reference: "Touchez les deux extrémités d'une longueur mesurée sur place.",
  mesure: "Touchez deux points pour mesurer leur distance réelle (pente comprise).",
  detection: "Touchez le toit à mesurer : les pans seront détectés automatiquement autour de ce point.",
  egout: "Touchez le bord bas (égout) du pan : la pente descendra vers ce bord.",
};

export function EtapeMetre({ chantier, maj }: { chantier: Chantier; maj: () => void }) {
  const [donnees, setDonnees] = useState<MetreComplet | null>(null);
  const [doc, setDoc] = useState<DocumentMetre | null>(null);
  const [calcul, setCalcul] = useState<Calcul | null>(null);
  const [hist, setHist] = useState<{ passe: DocumentMetre[]; futur: DocumentMetre[] }>({ passe: [], futur: [] });
  const [modifs, setModifs] = useState<string[]>([]);
  const [outil, setOutil] = useState<Outil>("selection");
  const [selection, setSelection] = useState<Selection>(null);
  const [enCours, setEnCours] = useState<Pt[]>([]);
  const [mesure, setMesure] = useState<{ p1: Pt; p2?: Pt; longueur?: number } | null>(null);
  const [refAttente, setRefAttente] = useState<{ p1: Pt; p2: Pt } | null>(null);
  const [vue, setVue] = useState<"plan" | "3d" | "saisie">(chantier.modele ? "plan" : "saisie");
  const [fond, setFond] = useState<"ortho" | "mns" | "aucun">(chantier.modele?.type === "odm" && !chantier.modele.ortho ? "mns" : "ortho");
  const [aimant, setAimant] = useState(true);
  const [detection, setDetection] = useState<Traitement | null>(null);
  const [sauvegarde, setSauvegarde] = useState(false);
  const toast = useToast();
  const avecModele = chantier.modele?.type === "odm";

  const charger = useCallback(async () => {
    const d = await api.get<MetreComplet>(`/api/chantiers/${chantier.id}/metre`);
    setDonnees(d);
    setDoc(d.document);
    setCalcul(d.calcul);
    setHist({ passe: [], futur: [] });
    setModifs([]);
  }, [chantier.id]);
  useEffect(() => { charger(); }, [charger]);

  // calcul en direct (serveur = référence unique des calculs)
  const docRef = useRef(doc);
  docRef.current = doc;
  useEffect(() => {
    if (!doc || !donnees) return;
    if (doc === donnees.document) {
      setCalcul(donnees.calcul);
      return;
    }
    const t = setTimeout(() => {
      api.post<{ calcul: Calcul }>(`/api/chantiers/${chantier.id}/metre/calculer`, { document: doc })
        .then((r) => docRef.current === doc && setCalcul(r.calcul)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [doc]); // eslint-disable-line

  const sale = modifs.length > 0;
  useEffect(() => {
    const f = (e: BeforeUnloadEvent) => { if (sale) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [sale]);

  const modifier = useCallback((nouveau: DocumentMetre, description: string, avant?: DocumentMetre) => {
    setHist((h) => ({ passe: [...h.passe.slice(-99), avant || docRef.current!], futur: [] }));
    setDoc(nouveau);
    setModifs((m) => [...m, description]);
  }, []);
  // pendant un glissé, l'aperçu ne crée pas d'entrée d'historique ; à la fin on empile l'état initial
  const debutGlisse = useRef<DocumentMetre | null>(null);
  const apercu = (d: DocumentMetre) => {
    if (!debutGlisse.current) debutGlisse.current = docRef.current;
    setDoc(d);
  };
  const finGlisse = (d: DocumentMetre, desc: string) => {
    const avant = debutGlisse.current || docRef.current!;
    debutGlisse.current = null;
    modifier(d, desc, avant);
  };
  const annuler = () => {
    if (!hist.passe.length || !doc) return;
    const prec = hist.passe[hist.passe.length - 1];
    setHist({ passe: hist.passe.slice(0, -1), futur: [doc, ...hist.futur] });
    setDoc(prec);
    setModifs((m) => m.slice(0, -1));
  };
  const retablir = () => {
    if (!hist.futur.length || !doc) return;
    setHist({ passe: [...hist.passe, doc], futur: hist.futur.slice(1) });
    setDoc(hist.futur[0]);
    setModifs((m) => [...m, "rétablissement"]);
  };

  const enregistrer = async () => {
    if (!doc) return;
    setSauvegarde(true);
    try {
      const resume = [...new Set(modifs)].slice(0, 8).join(" ; ") + (modifs.length > 8 ? "…" : "");
      const d = await api.put<MetreComplet>(`/api/chantiers/${chantier.id}/metre`, {
        document: doc, commentaire: resume || "Modification", version_base: donnees?.version?.numero ?? null });
      setDonnees(d);
      setDoc(d.document);
      setCalcul(d.calcul);
      setModifs([]);
      toast(`Métré enregistré (version ${d.version?.numero})`, "ok");
      maj();
    } catch (e) {
      toast((e as Error).message, "erreur");
    }
    setSauvegarde(false);
  };

  // raccourcis clavier
  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, textarea, select")) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? retablir() : annuler(); }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); retablir(); }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); enregistrer(); }
      else if (e.key === "Escape") { setEnCours([]); setMesure(null); setOutil("selection"); }
      else if (e.key === "Delete" || e.key === "Backspace") supprimerSelection();
      else if (e.key === "Enter" && enCours.length >= 3) terminerTrace();
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }); // eslint-disable-line

  // détection : suivi du traitement
  useEffect(() => {
    if (!detection || ["termine", "erreur"].includes(detection.statut)) return;
    const t = setInterval(async () => {
      const j = await api.get<Traitement>(`/api/traitements/${detection.id}`);
      setDetection(j);
      if (j.statut === "termine") {
        toast(j.message, "ok");
        await charger();
        maj();
      } else if (j.statut === "erreur") toast(`Détection impossible : ${j.erreur}`, "erreur");
    }, 1500);
    return () => clearInterval(t);
  }, [detection]); // eslint-disable-line

  if (!donnees || !doc) return <Chargement />;
  if (!chantier.modele && chantier.mode !== "saisie" && vue !== "saisie") {
    return (
      <div className="carte pile">
        <div className="alerte info"><b>Pas encore de support de mesure</b>
          {chantier.mode === "photo" ? "Choisissez la photo verticale à utiliser (étape Traitement)." : "Lancez la reconstruction 3D (étape Traitement), ou saisissez les dimensions à la main."}</div>
        <div className="ligne"><Link className="btn primaire" to={`/chantiers/${chantier.id}/traitement`}>Aller à l'étape Traitement</Link>
          <button className="btn" onClick={() => setVue("saisie")}>Saisir les dimensions</button></div>
      </div>
    );
  }

  // ---------------- actions de l'éditeur
  const majPan = (id: string, f: (p: Pan) => Pan, desc: string) =>
    modifier({ ...doc, pans: doc.pans.map((p) => (p.id === id ? f(p) : p)) }, desc);

  const zDe = async (pt: Pt): Promise<number> => {
    const z = zSurPans(pt, doc.pans);
    if (z !== null) return z;
    if (avecModele) {
      try {
        const r = await api.get<{ z: number | null }>(`/api/chantiers/${chantier.id}/altitude?x=${pt[0]}&y=${pt[1]}`);
        if (r.z !== null) return r.z;
      } catch { /* */ }
    }
    return 0;
  };

  const nouveauPlan = async (contour: Pt[]): Promise<Pick<Pan, "plan" | "source_plan" | "stats">> => {
    if (avecModele) {
      try {
        const r = await api.post<{ plan: Pan["plan"]; stats: Pan["stats"] }>(`/api/chantiers/${chantier.id}/ajuster-plan`, { contour });
        return { plan: r.plan, source_plan: "modele_3d", stats: r.stats };
      } catch (e) {
        toast(`${(e as Error).message} — pente à saisir.`, "erreur");
      }
    }
    // sans modèle 3D : pente par défaut à saisir, descente perpendiculaire à l'arête la plus longue
    let best = 0, az = 180;
    for (let i = 0; i < contour.length; i++) {
      const a = contour[i], b = contour[(i + 1) % contour.length];
      const L = dist(a, b);
      if (L > best) {
        best = L;
        const n: Pt = [b[1] - a[1], -(b[0] - a[0])];
        const m: Pt = [(a[0] + b[0]) / 2 + n[0] * 0.01, (a[1] + b[1]) / 2 + n[1] * 0.01];
        const sens = dansPolygone(m, contour) ? -1 : 1;
        az = (Math.atan2(sens * n[0], sens * n[1]) * 180) / Math.PI;
      }
    }
    return { plan: planDepuisPente(30, (az + 360) % 360), source_plan: chantier.mode === "photo" ? "estimation" : "saisie" };
  };

  const terminerTrace = async () => {
    const pts = enCours;
    if (pts.length < 3) return;
    setEnCours([]);
    if (outil === "pan") {
      const id = nouvelId("p", doc.pans);
      const plan = await nouveauPlan(pts);
      const pan: Pan = { id, nom: `Pan ${id.slice(1)}`, contour: pts, ...plan, source_contour: "manuel", valide: false };
      modifier({ ...docRef.current!, pans: [...docRef.current!.pans, pan] }, `${pan.nom} dessiné`);
      setSelection({ type: "pan", id });
      if (plan.source_plan !== "modele_3d") toast("Pente par défaut 30° : saisissez la pente réelle du pan.");
    } else if (outil === "obstacle") {
      const id = nouvelId("o", doc.obstacles);
      const pan = doc.pans.find((p) => p.contour && dansPolygone(pts[0], p.contour));
      modifier({ ...doc, obstacles: [...doc.obstacles, { id, type: "fenetre_toit", contour: pts, deduire: false, valide: true, source: "manuel", nombre: 1, pan_id: pan?.id }] }, "Obstacle ajouté");
      setSelection({ type: "obstacle", id });
    }
    setOutil("selection");
  };

  const surClic = async (pt: Pt, o: Outil) => {
    if (o === "pan" || o === "obstacle") {
      if (enCours.length >= 3 && dist(pt, enCours[0]) < 1e-6) return terminerTrace();
      setEnCours((l) => [...l, pt]);
    } else if (o === "point") {
      if (selection?.type !== "pan") return toast("Sélectionnez d'abord un pan");
      const pan = doc.pans.find((p) => p.id === selection.id);
      if (!pan?.contour) return;
      let best = { d: Infinity, i: -1, pt: pt as Pt };
      pan.contour.forEach((a, i) => {
        const pr = projeterSurSegment(pt, a, pan.contour![(i + 1) % pan.contour!.length]);
        if (pr.d < best.d) best = { d: pr.d, i, pt: pr.pt };
      });
      const c = [...pan.contour];
      c.splice(best.i + 1, 0, best.pt);
      majPan(pan.id, (p) => ({ ...p, contour: c, source_contour: p.source_contour === "manuel" ? "manuel" : "modifie" }), `${pan.nom} : sommet ajouté`);
      setSelection({ type: "pan", id: pan.id, sommet: best.i + 1 });
    } else if (o === "mesure") {
      if (!mesure || mesure.p2) setMesure({ p1: pt });
      else {
        const z1 = await zDe(mesure.p1), z2 = await zDe(pt);
        const k = calcul?.echelle.facteur || 1;
        const L = Math.sqrt((pt[0] - mesure.p1[0]) ** 2 + (pt[1] - mesure.p1[1]) ** 2 + (z2 - z1) ** 2) * k;
        setMesure({ p1: mesure.p1, p2: pt, longueur: L });
      }
    } else if (o === "reference") {
      if (!mesure || mesure.p2) setMesure({ p1: pt });
      else { setRefAttente({ p1: mesure.p1, p2: pt }); setMesure(null); setOutil("selection"); }
    } else if (o === "detection") {
      setOutil("selection");
      if (doc.pans.length && !confirm("La détection remplace les pans actuels (une nouvelle version est créée, l'ancienne reste dans l'historique). Continuer ?")) return;
      if (sale && !confirm("Des modifications ne sont pas enregistrées et seront perdues. Continuer ?")) return;
      try {
        const t = await api.post<Traitement>(`/api/chantiers/${chantier.id}/detection`, { graine: pt });
        setDetection(t);
        toast("Détection des pans en cours…");
      } catch (e) { toast((e as Error).message, "erreur"); }
    } else if (o === "egout") {
      if (selection?.type !== "pan") return;
      const pan = doc.pans.find((p) => p.id === selection.id);
      if (!pan?.contour || !pan.plan) return;
      let best = { d: Infinity, i: 0 };
      pan.contour.forEach((a, i) => { const pr = projeterSurSegment(pt, a, pan.contour![(i + 1) % pan.contour!.length]); if (pr.d < best.d) best = { d: pr.d, i }; });
      const a = pan.contour[best.i], b = pan.contour[(best.i + 1) % pan.contour.length];
      const mid: Pt = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      const c = pan.contour.reduce((s, q) => [s[0] + q[0] / pan.contour!.length, s[1] + q[1] / pan.contour!.length], [0, 0]);
      const ux = b[0] - a[0], uy = b[1] - a[1];
      let n: Pt = [uy, -ux];
      if ((mid[0] - c[0]) * n[0] + (mid[1] - c[1]) * n[1] < 0) n = [-n[0], -n[1]];
      const az = ((Math.atan2(n[0], n[1]) * 180) / Math.PI + 360) % 360;
      const plan = planDepuisPente(penteDe(pan.plan), az, mid[0], mid[1], 0);
      majPan(pan.id, (p) => ({ ...p, plan, source_plan: p.source_plan === "modele_3d" ? "saisie" : p.source_plan }), `${pan.nom} : sens de la pente défini`);
      setOutil("selection");
    }
  };

  function supprimerSelection() {
    if (!selection || !doc) return;
    if (selection.type === "pan" && selection.sommet !== undefined) {
      const pan = doc.pans.find((p) => p.id === selection.id);
      if (!pan?.contour || pan.contour.length <= 3) return toast("Un pan doit garder au moins 3 sommets");
      majPan(pan.id, (p) => ({ ...p, contour: p.contour!.filter((_, i) => i !== selection.sommet), source_contour: p.source_contour === "manuel" ? "manuel" : "modifie", valide: false }), `${pan.nom} : sommet supprimé`);
      setSelection({ type: "pan", id: pan.id });
    } else if (selection.type === "pan") {
      const pan = doc.pans.find((p) => p.id === selection.id);
      if (!confirm(`Supprimer « ${pan?.nom} » ?`)) return;
      modifier({ ...doc, pans: doc.pans.filter((p) => p.id !== selection.id), obstacles: doc.obstacles.filter((o) => o.pan_id !== selection.id || !o.contour) }, `${pan?.nom} supprimé`);
      setSelection(null);
    } else if (selection.type === "obstacle") {
      modifier({ ...doc, obstacles: doc.obstacles.filter((o) => o.id !== selection.id) }, "Obstacle supprimé");
      setSelection(null);
    } else if (selection.type === "reference") {
      modifier({ ...doc, echelle: { ...doc.echelle, references: doc.echelle.references.filter((r) => r.id !== selection.id) } }, "Cote de référence supprimée");
      setSelection(null);
    }
  }

  const outils: [Outil, string, string][] = [
    ["selection", "main", "Sélection"],
    ["pan", "crayon", "Pan"],
    ["point", "plus", "Point"],
    ["obstacle", "calque", "Obstacle"],
    ["reference", "regle", "Cote réf."],
    ["mesure", "regle", "Mesurer"],
    ...(avecModele ? [["detection", "cible", "Détecter"] as [Outil, string, string]] : []),
  ];

  return (
    <div className="pile">
      <div className="ligne">
        {(chantier.modele ? ["plan", ...(avecModele ? ["3d"] : []), "saisie"] : ["saisie"]).map((v) => (
          <button key={v} className={`btn ${vue === v ? "actif" : ""}`} onClick={() => setVue(v as typeof vue)}>
            {v === "plan" ? "Plan" : v === "3d" ? "Vue 3D" : chantier.modele ? "Compléments / saisie" : "Saisie des dimensions"}
          </button>
        ))}
        <span className="espace" />
        <button className="btn petit" disabled={!hist.passe.length} onClick={annuler} title="Annuler (Ctrl+Z)"><Icone nom="annuler" taille={16} /></button>
        <button className="btn petit" disabled={!hist.futur.length} onClick={retablir} title="Rétablir (Ctrl+Y)"><Icone nom="refaire" taille={16} /></button>
        <button className={`btn ${sale ? "primaire" : ""}`} disabled={!sale || sauvegarde} onClick={enregistrer}>
          <Icone nom="sauver" taille={18} /> {sale ? `Enregistrer (${modifs.length})` : "Enregistré"}
        </button>
      </div>
      {donnees.document.auto?.avertissements?.map((a, i) => <div key={i} className="alerte attention">{a}</div>)}
      {chantier.modele?.type === "photo" && chantier.modele.avertissements?.map((a, i) => <div key={i} className="alerte attention">{a}</div>)}
      {detection && !["termine", "erreur"].includes(detection.statut) && <div className="alerte info"><span className="spinner" /> Détection des pans en cours…</div>}
      <div className="editeur">
        <div>
          {vue === "plan" && (
            <div style={{ position: "relative" }}>
              <EditeurPlan chantier={chantier} doc={doc} calcul={calcul} outil={outil} selection={selection} setSelection={setSelection}
                apercu={apercu} modifier={(d, desc) => finGlisse(d, desc)} surTrace={() => {}} surClic={surClic} fond={fond} aimant={aimant}
                enCours={enCours} mesure={mesure} />
              <div className="outils">
                {outils.map(([o, ic, l]) => (
                  <button key={o} title={l} className={`btn ${outil === o ? "actif" : ""}`} onClick={() => { setOutil(o); setEnCours([]); setMesure(null); }}>
                    <Icone nom={ic} taille={16} /> <span className="masque-mobile">{l}</span>
                  </button>
                ))}
                <span className="espace" />
                {chantier.modele?.type === "odm" && (
                  <select value={fond} onChange={(e) => setFond(e.target.value as typeof fond)} style={{ width: "auto", minHeight: 38 }} onPointerDown={(e) => e.stopPropagation()}>
                    {chantier.modele.ortho && <option value="ortho">Orthophoto</option>}
                    <option value="mns">Relief (MNS)</option><option value="aucun">Sans fond</option>
                  </select>
                )}
                <button className={`btn ${aimant ? "actif" : ""}`} onClick={() => setAimant(!aimant)} title="Aimantation aux sommets et arêtes">Aimant</button>
              </div>
              <div className="consigne">
                <span>{CONSIGNES[outil]}</span>
                {(outil === "pan" || outil === "obstacle") && enCours.length > 0 && <>
                  <button className="btn petit" onClick={() => setEnCours((l) => l.slice(0, -1))}>Retirer le dernier point</button>
                  <button className="btn petit primaire" disabled={enCours.length < 3} onClick={terminerTrace}>Terminer</button>
                </>}
                {outil !== "selection" && <button className="btn petit" onClick={() => { setOutil("selection"); setEnCours([]); setMesure(null); }}>Fermer l'outil</button>}
              </div>
            </div>
          )}
          {vue === "3d" && (
            <Suspense fallback={<Chargement texte="Chargement de la vue 3D…" />}>
              <Vue3D chantier={chantier} doc={doc} calcul={calcul} />
            </Suspense>
          )}
          {vue === "saisie" && <SaisieComplements doc={doc} calcul={calcul} modifier={modifier} chantier={chantier} />}
        </div>
        <Panneau doc={doc} calcul={calcul} selection={selection} setSelection={setSelection} majPan={majPan} modifier={modifier}
          supprimer={supprimerSelection} chantier={chantier} setOutil={setOutil} donnees={donnees} avecModele={avecModele} nouveauPlan={nouveauPlan} />
      </div>
      {refAttente && <ModaleReference p={refAttente} zDe={zDe} fermer={() => setRefAttente(null)} ajouter={(r) => {
        modifier({ ...doc, echelle: { ...doc.echelle, references: [...doc.echelle.references, r] } }, `Cote de référence ${fr(r.reelle)} m`);
        setRefAttente(null);
      }} facteur={calcul?.echelle.facteur || 1} existantes={doc.echelle.references} />}
    </div>
  );
}

function ModaleReference({ p, zDe, fermer, ajouter, facteur, existantes }: {
  p: { p1: Pt; p2: Pt }; zDe: (pt: Pt) => Promise<number>; fermer: () => void; facteur: number;
  ajouter: (r: DocumentMetre["echelle"]["references"][number]) => void; existantes: { id: string }[];
}) {
  const [z, setZ] = useState<[number, number] | null>(null);
  const [val, setVal] = useState("");
  const [lib, setLib] = useState("");
  useEffect(() => { Promise.all([zDe(p.p1), zDe(p.p2)]).then((v) => setZ([v[0], v[1]])); }, []); // eslint-disable-line
  const mod = z ? Math.sqrt((p.p2[0] - p.p1[0]) ** 2 + (p.p2[1] - p.p1[1]) ** 2 + (z[1] - z[0]) ** 2) : null;
  const v = parseFloat(val.replace(",", "."));
  return (
    <Modale titre="Cote de référence" fermer={fermer}>
      {!z ? <Chargement /> : (
        <div className="pile">
          <p>Longueur actuelle sur le modèle : <b>{fr((mod || 0) * facteur, 3)} m</b>{facteur !== 1 && <small> (échelle actuelle ×{fr(facteur, 4)})</small>}</p>
          <label className="champ">Longueur réelle mesurée sur place (m)<input autoFocus inputMode="decimal" value={val} onChange={(e) => setVal(e.target.value)} placeholder="ex. 12,46" /></label>
          <label className="champ">Libellé (facultatif)<input value={lib} onChange={(e) => setLib(e.target.value)} placeholder="ex. égout façade rue" /></label>
          {mod && v > 0 && <div className={`alerte ${Math.abs(v / mod - 1) > 0.1 ? "attention" : "info"}`}>
            Facteur d'échelle de cette cote : ×{fr(v / mod, 4)} ({v / mod >= 1 ? "+" : ""}{fr((v / mod - 1) * 100, 1)} %).
            {Math.abs(v / mod - 1) > 0.1 && " Écart important : vérifiez les deux points pointés et la valeur saisie."}</div>}
          <div className="ligne"><button className="btn" onClick={fermer}>Annuler</button>
            <button className="btn primaire" disabled={!(v > 0)} onClick={() => ajouter({ id: nouvelId("r", existantes), libelle: lib, p1: [p.p1[0], p.p1[1], z[0]], p2: [p.p2[0], p.p2[1], z[1]], reelle: v })}>Appliquer</button></div>
        </div>
      )}
    </Modale>
  );
}

function Panneau({ doc, calcul, selection, setSelection, majPan, modifier, supprimer, chantier, setOutil, donnees, avecModele, nouveauPlan }: {
  doc: DocumentMetre; calcul: Calcul | null; selection: Selection; setSelection: (s: Selection) => void;
  majPan: (id: string, f: (p: Pan) => Pan, d: string) => void; modifier: (d: DocumentMetre, desc: string) => void;
  supprimer: () => void; chantier: Chantier; setOutil: (o: Outil) => void; donnees: MetreComplet; avecModele: boolean;
  nouveauPlan: (c: Pt[]) => Promise<Pick<Pan, "plan" | "source_plan" | "stats">>;
}) {
  const toast = useToast();
  if (!calcul) return <div className="carte"><Chargement /></div>;
  const t = calcul.totaux;
  const tl = calcul.totaux_lignes;
  const pan = selection?.type === "pan" ? doc.pans.find((p) => p.id === selection.id) : null;
  const panCalc = pan ? calcul.pans.find((p) => p.id === pan.id) : null;
  const obs = selection?.type === "obstacle" ? doc.obstacles.find((o) => o.id === selection.id) : null;
  const ligne = selection?.type === "ligne" ? calcul.lignes.find((l) => l.cle === selection.cle) : null;
  const ref = selection?.type === "reference" ? calcul.echelle.references.find((r) => r.id === selection.id) : null;
  return (
    <div className="panneau pile">
      {pan && panCalc && (
        <div className="carte pile" style={{ borderLeft: "4px solid var(--bleu)" }}>
          <div className="ligne"><input value={pan.nom} onChange={(e) => majPan(pan.id, (p) => ({ ...p, nom: e.target.value }), "Pan renommé")} style={{ fontWeight: 700 }} /></div>
          <div className="ligne" style={{ gap: 4 }}>
            <Badge statut={panCalc.confiance.niveau}>{LIBELLE_CONFIANCE[panCalc.confiance.niveau]}</Badge>
            <Badge statut="">Pente : {LIBELLE_SOURCE[panCalc.source_plan] || panCalc.source_plan}</Badge>
            <Badge statut="">Contour : {panCalc.source_contour === "auto" ? "automatique" : panCalc.source_contour === "modifie" ? "corrigé" : "manuel"}</Badge>
          </div>
          <div className="indicateur"><span>Surface réelle</span><b>{fr(panCalc.surface)} m²{panCalc.confiance.incertitude_m2 ? ` ± ${fr(panCalc.confiance.incertitude_m2, 1)}` : ""}</b></div>
          <div className="indicateur"><span>Surface projetée</span><b>{fr(panCalc.surface_plan)} m²</b></div>
          <div className="indicateur"><span>Pente</span><b>{fr(panCalc.pente_deg, 1)}° · {fr(panCalc.pente_pct, 0)} %</b></div>
          <div className="indicateur"><span>Exposition</span><b>{panCalc.orientation}{panCalc.azimut !== null ? ` (${Math.round(panCalc.azimut)}°)` : ""}</b></div>
          <div className="indicateur"><span>Rampant max.</span><b>{fr(panCalc.rampant)} m</b></div>
          {panCalc.deductions > 0 && <div className="indicateur"><span>Déductions</span><b>− {fr(panCalc.deductions)} m²</b></div>}
          <ul style={{ margin: 0, paddingLeft: "1.1em", fontSize: ".85rem" }}>{panCalc.confiance.raisons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          {pan.plan && (
            <details open={pan.source_plan !== "modele_3d"}>
              <summary style={{ cursor: "pointer", fontWeight: 600 }}>Modifier la pente</summary>
              <div className="pile" style={{ marginTop: 8 }}>
                <label className="champ">Pente (°)<input type="number" inputMode="decimal" step="0.5" value={Math.round(penteDe(pan.plan) * 10) / 10}
                  onChange={(e) => { const v = +e.target.value; if (v >= 0 && v < 85) majPan(pan.id, (p) => {
                    const c = p.contour![0];
                    const z0 = p.plan!.a * c[0] + p.plan!.b * c[1] + p.plan!.c;
                    return { ...p, plan: planDepuisPente(v, azimutDe(p.plan!), c[0], c[1], z0), source_plan: avecModele && p.source_plan === "modele_3d" ? "saisie" : (p.source_plan === "estimation" ? "estimation" : "saisie") };
                  }, `${pan.nom} : pente saisie`); }} /></label>
                <div className="ligne">
                  <button className="btn petit" onClick={() => setOutil("egout")}>Désigner l'égout du pan</button>
                  <small>Exposition : {orientation(azimutDe(pan.plan))}</small>
                </div>
                {avecModele && pan.contour && (
                  <button className="btn petit" onClick={async () => {
                    const r = await nouveauPlan(pan.contour!);
                    if (r.source_plan === "modele_3d") majPan(pan.id, (p) => ({ ...p, ...r }), `${pan.nom} : plan réajusté sur le modèle 3D`);
                  }}>Réajuster sur le modèle 3D</button>
                )}
              </div>
            </details>
          )}
          <label className="case"><input type="checkbox" checked={!!pan.valide} onChange={(e) => majPan(pan.id, (p) => ({ ...p, valide: e.target.checked }), `${pan.nom} ${e.target.checked ? "validé" : "dévalidé"}`)} /> <b>Pan contrôlé (contour et pente vérifiés)</b></label>
          <div className="ligne">
            {selection?.type === "pan" && selection.sommet !== undefined && <button className="btn petit" onClick={supprimer}>Supprimer le point</button>}
            <button className="btn petit danger" onClick={() => { setSelection({ type: "pan", id: pan.id }); setTimeout(supprimer, 0); }}><Icone nom="poubelle" taille={16} /> Supprimer le pan</button>
          </div>
        </div>
      )}
      {obs && (
        <div className="carte pile" style={{ borderLeft: "4px solid var(--gris)" }}>
          <b>Obstacle {obs.source === "auto" ? "(détecté automatiquement)" : ""}</b>
          <label className="champ">Nature<select value={obs.type} onChange={(e) => modifier({ ...doc, obstacles: doc.obstacles.map((o) => (o.id === obs.id ? { ...o, type: e.target.value, valide: true } : o)) }, "Nature d'obstacle précisée")}>
            {Object.entries(donnees.types_obstacles).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          {obs.hauteur !== undefined && <small>Dépasse d'environ {fr(obs.hauteur, 2)} m au-dessus du pan.</small>}
          {(() => { const c = calcul.obstacles.find((o) => o.id === obs.id); return c && <small>Surface {fr(c.surface)} m² · périmètre {fr(c.perimetre)} m</small>; })()}
          <label className="case"><input type="checkbox" checked={!!obs.deduire} onChange={(e) => modifier({ ...doc, obstacles: doc.obstacles.map((o) => (o.id === obs.id ? { ...o, deduire: e.target.checked } : o)) }, "Déduction d'obstacle modifiée")} /> Déduire de la surface de couverture</label>
          <label className="case"><input type="checkbox" checked={!!obs.valide} onChange={(e) => modifier({ ...doc, obstacles: doc.obstacles.map((o) => (o.id === obs.id ? { ...o, valide: e.target.checked } : o)) }, "Obstacle confirmé")} /> Obstacle confirmé</label>
          <div><button className="btn petit danger" onClick={supprimer}><Icone nom="poubelle" taille={16} /> Supprimer</button></div>
        </div>
      )}
      {ligne && (
        <div className="carte pile" style={{ borderLeft: `4px solid ${COULEURS_LIGNES[ligne.type]}` }}>
          <b>{ligne.libelle} — {fr(ligne.longueur)} m</b>
          <label className="champ">Type de ligne<select value={ligne.type} onChange={(e) => {
            const lt = { ...doc.lignes_types };
            if (e.target.value === ligne.type_auto) delete lt[ligne.cle]; else lt[ligne.cle] = e.target.value;
            modifier({ ...doc, lignes_types: lt }, `Ligne requalifiée en ${donnees.types_lignes[e.target.value]}`);
          }}>{Object.entries(donnees.types_lignes).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          {ligne.modifie && <small>Type modifié manuellement (automatique : {donnees.types_lignes[ligne.type_auto || ""]}). Le type automatique est rétabli si le tracé change.</small>}
          {(ligne.ecart_hauteur || 0) > 0.1 && <div className="alerte attention">Les deux pans ne se rejoignent pas à la même hauteur ({fr((ligne.ecart_hauteur || 0) * 100, 0)} cm).</div>}
        </div>
      )}
      {ref && (
        <div className="carte pile" style={{ borderLeft: "4px solid var(--vert)" }}>
          <b>Cote de référence {ref.libelle ? `— ${ref.libelle}` : ""}</b>
          <div className="indicateur"><span>Réelle</span><b>{fr(ref.reelle, 3)} m</b></div>
          <div className="indicateur"><span>Sur le modèle</span><b>{fr(ref.mesuree, 3)} m</b></div>
          <div className="indicateur"><span>Rapport</span><b>×{fr(ref.reelle / (ref.mesuree || 1), 4)}</b></div>
          <div><button className="btn petit danger" onClick={supprimer}>Supprimer la cote</button></div>
        </div>
      )}

      <div className="carte pile">
        <small>Surface de couverture nette</small>
        <div className="gros-chiffre">{fr(t.surface_nette)} m²</div>
        {t.incertitude_m2 ? <small>± {fr(t.incertitude_m2, 1)} m² (estimation{calcul.echelle.incertitude_rel === null ? ", hors erreur d'échelle" : ""})</small> : null}
        <div className="indicateur"><span>Surface brute / déductions</span><b>{fr(t.surface_brute)} / {fr(t.deductions)} m²</b></div>
        <div className="indicateur"><span>Surface projetée</span><b>{fr(t.surface_plan)} m²</b></div>
        <div className="indicateur"><span>Pans / pente moyenne</span><b>{t.nb_pans} / {fr(t.pente_moyenne_deg, 0)}°</b></div>
        {["faitage", "aretier", "noue", "egout", "rive", "rive_haute", "bris", "solin"].filter((k) => tl[k] > 0).map((k) => (
          <div key={k} className="indicateur"><span><i style={{ display: "inline-block", width: 12, height: 4, background: COULEURS_LIGNES[k], marginRight: 6, verticalAlign: "middle" }} />{donnees.types_lignes[k]}</span><b>{fr(tl[k])} ml</b></div>
        ))}
        {calcul.dimensions && <div className="indicateur"><span>Emprise toiture</span><b>{fr(calcul.dimensions.longueur, 1)} × {fr(calcul.dimensions.largeur, 1)} m</b></div>}
        <div className={`alerte ${calcul.echelle.incertitude_rel !== null ? "ok" : "attention"}`} style={{ marginTop: 6, marginBottom: 0 }}>
          <b>Échelle {calcul.echelle.facteur !== 1 ? `×${fr(calcul.echelle.facteur, 4)}` : ""}</b>{calcul.echelle.message}
          {calcul.echelle.incertitude_rel === null && chantier.modele && <div><button className="btn petit" style={{ marginTop: 6 }} onClick={() => setOutil("reference")}>Ajouter une cote de référence</button></div>}
        </div>
      </div>

      {calcul.controles.filter((c) => c.niveau !== "info" || c.code === "pans_non_valides").length > 0 && (
        <div className="carte pile">
          <b>Contrôles de cohérence</b>
          {calcul.controles.map((c, i) => (
            <div key={i} className={`alerte ${c.niveau === "erreur" ? "erreur" : c.niveau === "alerte" ? "attention" : "info"}`} style={{ cursor: c.pan_id ? "pointer" : undefined, marginBottom: 0 }}
              onClick={() => c.pan_id && setSelection({ type: "pan", id: c.pan_id })}>{c.message}</div>
          ))}
        </div>
      )}

      <div className="carte">
        <b>Pans</b>
        <table className="tableau" style={{ marginTop: 6 }}>
          <thead><tr><th>Pan</th><th className="num">m²</th><th className="num">Pente</th><th /></tr></thead>
          <tbody>{calcul.pans.map((p) => (
            <tr key={p.id} className={`cliquable ${selection?.type === "pan" && selection.id === p.id ? "selection" : ""}`} onClick={() => setSelection({ type: "pan", id: p.id })}>
              <td>{p.nom}</td><td className="num">{fr(p.surface, 1)}</td><td className="num">{Math.round(p.pente_deg)}°</td>
              <td>{p.valide ? <Badge statut="ok">✓</Badge> : <Badge statut={p.confiance.niveau}>{p.confiance.niveau === "saisie" ? "saisie" : "à voir"}</Badge>}</td>
            </tr>))}</tbody>
        </table>
        {calcul.pans.length > 0 && calcul.pans.some((p) => !p.valide) && (
          <button className="btn petit" style={{ marginTop: 8 }} onClick={() => {
            if (confirm("Marquer tous les pans comme contrôlés ? Ne le faites qu'après les avoir réellement vérifiés.")) {
              modifier({ ...doc, pans: doc.pans.map((p) => ({ ...p, valide: true })) }, "Tous les pans validés");
              toast("Pans validés");
            }
          }}>Valider tous les pans</button>
        )}
      </div>

      {calcul.comparaison_auto && (
        <details className="carte">
          <summary style={{ cursor: "pointer", fontWeight: 700 }}>Détection automatique / métré actuel ({calcul.comparaison_auto.ecart_pct !== null ? `${calcul.comparaison_auto.ecart_pct >= 0 ? "+" : ""}${fr(calcul.comparaison_auto.ecart_pct, 1)} %` : "—"})</summary>
          <table className="tableau" style={{ marginTop: 6 }}>
            <thead><tr><th>Pan</th><th className="num">Auto</th><th className="num">Actuel</th><th className="num">Écart</th></tr></thead>
            <tbody>{calcul.comparaison_auto.pans.map((p) => (
              <tr key={p.id}><td>{p.nom}</td><td className="num">{fr(p.auto, 1)}</td><td className="num">{p.actuel === null ? "supprimé" : fr(p.actuel, 1)}</td><td className="num">{p.ecart === null ? "—" : fr(p.ecart, 1)}</td></tr>))}</tbody>
            <tfoot><tr><td>Total</td><td className="num">{fr(calcul.comparaison_auto.total_auto, 1)}</td><td className="num">{fr(calcul.comparaison_auto.total_actuel, 1)}</td><td className="num">{fr(calcul.comparaison_auto.ecart, 1)}</td></tr></tfoot>
          </table>
          {calcul.comparaison_auto.pans_ajoutes.length > 0 && <small>Pans ajoutés manuellement : {calcul.comparaison_auto.pans_ajoutes.join(", ")}</small>}
        </details>
      )}
      <Legende types={donnees.types_lignes} />
    </div>
  );
}

function Legende({ types }: { types: Record<string, string> }) {
  return (
    <div className="legende">
      {Object.entries(COULEURS_LIGNES).filter(([k]) => k !== "autre").map(([k, c]) => (
        <span key={k}><i style={{ background: c }} />{types[k]?.split(" /")[0]}</span>
      ))}
    </div>
  );
}
