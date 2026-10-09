import { PointerEvent as RPointerEvent, useCallback, useEffect, useMemo, useRef, useState, WheelEvent } from "react";
import { api, fr } from "../api";
import { centroide, COULEURS_LIGNES, dist, projeterSurSegment } from "../geo";
import type { Calcul, Chantier, DocumentMetre, Pan, Pt } from "../types";

export type Outil = "selection" | "pan" | "obstacle" | "point" | "reference" | "mesure" | "detection" | "egout";
export type Selection =
  | { type: "pan"; id: string; sommet?: number }
  | { type: "obstacle"; id: string }
  | { type: "ligne"; cle: string }
  | { type: "reference"; id: string }
  | null;

interface Vue { cx: number; cy: number; s: number }

interface Props {
  chantier: Chantier;
  doc: DocumentMetre;
  calcul: Calcul | null;
  outil: Outil;
  selection: Selection;
  setSelection: (s: Selection) => void;
  /** déplacement d'un sommet en cours (sans historique) */
  apercu: (d: DocumentMetre) => void;
  /** modification validée (avec historique) */
  modifier: (d: DocumentMetre, description: string) => void;
  surTrace: (pts: Pt[], outil: Outil) => void;
  surClic: (pt: Pt, outil: Outil) => void;
  fond: "ortho" | "mns" | "aucun";
  aimant: boolean;
  enCours: Pt[];
  mesure: { p1: Pt; p2?: Pt; longueur?: number } | null;
}

const RAYON_SOMMET = 7;
const AIMANT_PX = 14;

export function EditeurPlan(p: Props) {
  const zone = useRef<HTMLDivElement>(null);
  const [taille, setTaille] = useState({ w: 800, h: 600 });
  const [vue, setVue] = useState<Vue | null>(null);
  const [img, setImg] = useState<{ url: string; b: number[] } | null>(null);
  const [curseur, setCurseur] = useState<Pt | null>(null);
  const glisse = useRef<null | { type: "vue"; x: number; y: number; v: Vue } | { type: "sommet"; pan: string; idx: number; lies: [string, number][]; depart: DocumentMetre; bouge: boolean }>(null);
  const pointeurs = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ d: number; v: Vue; cx: number; cy: number } | null>(null);
  const m = p.chantier.modele;

  // taille de la zone
  useEffect(() => {
    const el = zone.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setTaille({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setTaille({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // vue initiale : emprise des pans, sinon du modèle
  useEffect(() => {
    if (vue || taille.w < 10) return;
    const pts = p.doc.pans.flatMap((x) => x.contour || []);
    let b: number[];
    if (pts.length >= 3) {
      const xs = pts.map((q) => q[0]), ys = pts.map((q) => q[1]);
      const mg = Math.max(3, 0.25 * Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)));
      b = [Math.min(...xs) - mg, Math.min(...ys) - mg, Math.max(...xs) + mg, Math.max(...ys) + mg];
    } else if (m?.type === "photo") {
      b = m.bornes;
    } else if (m?.bornes) {
      const cx = (m.bornes[0] + m.bornes[2]) / 2, cy = (m.bornes[1] + m.bornes[3]) / 2;
      const r = Math.min(30, (m.bornes[2] - m.bornes[0]) / 2);
      b = [cx - r, cy - r, cx + r, cy + r];
    } else b = [-10, -10, 10, 10];
    const s = Math.min(taille.w / (b[2] - b[0]), taille.h / (b[3] - b[1]));
    setVue({ cx: (b[0] + b[2]) / 2, cy: (b[1] + b[3]) / 2, s });
  }, [taille, vue, p.doc.pans, m]);

  // image de fond recadrée sur la zone visible (rechargée après zoom / déplacement)
  const cleImg = useRef("");
  useEffect(() => {
    if (!vue || !m || p.fond === "aucun") {
      if (p.fond === "aucun") setImg(null);
      return;
    }
    const t = setTimeout(async () => {
      let url: string;
      if (m.type === "photo") {
        url = `/api/chantiers/${p.chantier.id}/fond?max_px=3000`;
      } else {
        const demi = { x: taille.w / vue.s / 2, y: taille.h / vue.s / 2 };
        const bbox = [vue.cx - demi.x * 1.4, vue.cy - demi.y * 1.4, vue.cx + demi.x * 1.4, vue.cy + demi.y * 1.4];
        if (img && cleImg.current.startsWith(p.fond)) {
          const [x0, y0, x1, y1] = img.b;
          const resActuelle = (x1 - x0) / 2048;
          const contient = bbox[0] >= x0 && bbox[1] >= y0 && bbox[2] <= x1 && bbox[3] <= y1;
          if (contient && resActuelle < 2.2 / vue.s) return;
        }
        url = `/api/chantiers/${p.chantier.id}/fond?quoi=${p.fond}&max_px=2048&bbox=${bbox.map((v) => v.toFixed(2)).join(",")}`;
      }
      const cle = p.fond + url;
      if (cle === cleImg.current) return;
      cleImg.current = cle;
      try {
        const r = await api.brut(url);
        const b = (r.headers.get("X-Bornes") || "").split(",").map(Number);
        const blob = await r.blob();
        setImg((ancien) => {
          if (ancien) URL.revokeObjectURL(ancien.url);
          return { url: URL.createObjectURL(blob), b };
        });
      } catch {
        /* fond indisponible : l'édition reste possible */
      }
    }, img ? 500 : 0);
    return () => clearTimeout(t);
  }, [vue, p.fond, m, p.chantier.id]); // eslint-disable-line

  const versEcran = useCallback((q: Pt | number[]): Pt => {
    const v = vue!;
    return [taille.w / 2 + (q[0] - v.cx) * v.s, taille.h / 2 - (q[1] - v.cy) * v.s];
  }, [vue, taille]);
  const versMonde = useCallback((x: number, y: number): Pt => {
    const v = vue!;
    return [v.cx + (x - taille.w / 2) / v.s, v.cy - (y - taille.h / 2) / v.s];
  }, [vue, taille]);

  const local = (e: { clientX: number; clientY: number }) => {
    const r = zone.current!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  /** Aimantation sur les sommets puis les arêtes des autres pans / obstacles. */
  const aimanter = useCallback((pt: Pt, exclure?: { pan: string; idx: number }): Pt => {
    if (!p.aimant || !vue) return pt;
    const tol = AIMANT_PX / vue.s;
    let meilleur: Pt | null = null, d0 = tol;
    for (const pan of p.doc.pans) for (let i = 0; i < (pan.contour?.length || 0); i++) {
      if (exclure && pan.id === exclure.pan && i === exclure.idx) continue;
      const d = dist(pt, pan.contour![i]);
      if (d < d0) { d0 = d; meilleur = pan.contour![i]; }
    }
    for (const q of p.enCours) {
      const d = dist(pt, q);
      if (d < d0) { d0 = d; meilleur = q; }
    }
    if (meilleur) return [meilleur[0], meilleur[1]];
    d0 = tol * 0.7;
    for (const pan of p.doc.pans) {
      const c = pan.contour || [];
      for (let i = 0; i < c.length; i++) {
        if (exclure && pan.id === exclure.pan && (i === exclure.idx || (i + 1) % c.length === exclure.idx)) continue;
        const pr = projeterSurSegment(pt, c[i], c[(i + 1) % c.length]);
        if (pr.d < d0) { d0 = pr.d; meilleur = pr.pt; }
      }
    }
    return meilleur || pt;
  }, [p.aimant, p.doc.pans, p.enCours, vue]);

  // ---------------- événements
  const bas = (e: RPointerEvent) => {
    if (!vue) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    const { x, y } = local(e);
    pointeurs.current.set(e.pointerId, { x, y });
    if (pointeurs.current.size === 2) {
      const [a, b] = [...pointeurs.current.values()];
      pinch.current = { d: Math.hypot(a.x - b.x, a.y - b.y), v: vue, cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
      glisse.current = null;
      return;
    }
    const cible = (e.target as Element).closest("[data-cible]") as HTMLElement | null;
    const pt = versMonde(x, y);
    if (p.outil === "selection" && cible?.dataset.cible === "sommet") {
      const pan = cible.dataset.pan!, idx = +cible.dataset.idx!;
      const pos = p.doc.pans.find((q) => q.id === pan)!.contour![idx];
      const lies: [string, number][] = [];
      for (const q of p.doc.pans) q.contour?.forEach((c, i) => {
        if (!(q.id === pan && i === idx) && dist(c, pos) < 0.01) lies.push([q.id, i]);
      });
      glisse.current = { type: "sommet", pan, idx, lies, depart: p.doc, bouge: false };
      p.setSelection({ type: "pan", id: pan, sommet: idx });
      return;
    }
    if (p.outil === "selection") {
      if (cible?.dataset.cible === "pan") p.setSelection({ type: "pan", id: cible.dataset.id! });
      else if (cible?.dataset.cible === "obstacle") p.setSelection({ type: "obstacle", id: cible.dataset.id! });
      else if (cible?.dataset.cible === "ligne") p.setSelection({ type: "ligne", cle: cible.dataset.cle! });
      else if (cible?.dataset.cible === "reference") p.setSelection({ type: "reference", id: cible.dataset.id! });
      else p.setSelection(null);
      glisse.current = { type: "vue", x, y, v: vue };
      return;
    }
    // outils de tracé : un appui court ajoute un point, un glissé déplace la vue
    glisse.current = { type: "vue", x, y, v: vue };
    (glisse.current as { clic?: Pt }).clic = pt;
  };

  const mouvement = (e: RPointerEvent) => {
    if (!vue) return;
    const { x, y } = local(e);
    if (pointeurs.current.has(e.pointerId)) pointeurs.current.set(e.pointerId, { x, y });
    if (pinch.current && pointeurs.current.size === 2) {
      const [a, b] = [...pointeurs.current.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      const pc = pinch.current;
      const s = Math.max(2, Math.min(800, pc.v.s * (d / pc.d)));
      const wx = pc.v.cx + (pc.cx - taille.w / 2) / pc.v.s, wy = pc.v.cy - (pc.cy - taille.h / 2) / pc.v.s;
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      setVue({ s, cx: wx - (mx - taille.w / 2) / s, cy: wy + (my - taille.h / 2) / s });
      return;
    }
    const pt = versMonde(x, y);
    setCurseur(p.outil === "selection" ? null : aimanter(pt));
    const g = glisse.current;
    if (!g) return;
    if (g.type === "vue") {
      if (Math.hypot(x - g.x, y - g.y) > 4) (g as { clic?: Pt }).clic = undefined;
      setVue({ ...g.v, cx: g.v.cx - (x - g.x) / g.v.s, cy: g.v.cy + (y - g.y) / g.v.s });
    } else if (g.type === "sommet") {
      g.bouge = true;
      const q = aimanter(pt, { pan: g.pan, idx: g.idx });
      const cibles: [string, number][] = [[g.pan, g.idx], ...g.lies];
      const doc = {
        ...g.depart,
        pans: g.depart.pans.map((pan) => {
          const ici = cibles.filter(([id]) => id === pan.id);
          if (!ici.length) return pan;
          const contour = pan.contour!.map((c, i) => (ici.some(([, j]) => j === i) ? q : c));
          const sc: Pan["source_contour"] = pan.source_contour === "manuel" ? "manuel" : "modifie";
          return { ...pan, contour, source_contour: sc, valide: false };
        }),
      };
      p.apercu(doc);
    }
  };

  const haut = (e: RPointerEvent) => {
    pointeurs.current.delete(e.pointerId);
    if (pointeurs.current.size < 2) pinch.current = null;
    const g = glisse.current;
    glisse.current = null;
    if (!g) return;
    if (g.type === "sommet" && g.bouge) {
      const nom = g.depart.pans.find((q) => q.id === g.pan)?.nom || g.pan;
      p.modifier(p.doc, `${nom} : sommet déplacé`);
    } else if (g.type === "vue" && (g as { clic?: Pt }).clic && p.outil !== "selection") {
      p.surClic(aimanter((g as { clic?: Pt }).clic!), p.outil);
    }
  };

  const molette = (e: WheelEvent) => {
    if (!vue) return;
    const { x, y } = local(e);
    const f = Math.exp(-e.deltaY * 0.0015);
    const s = Math.max(2, Math.min(800, vue.s * f));
    const w = versMonde(x, y);
    setVue({ s, cx: w[0] - (x - taille.w / 2) / s, cy: w[1] + (y - taille.h / 2) / s });
  };

  const recentrer = () => setVue(null);

  // ---------------- rendu
  const lignes = p.calcul?.lignes.filter((l) => !l.manuelle) || [];
  const infos = useMemo(() => Object.fromEntries((p.calcul?.pans || []).map((x) => [x.id, x])), [p.calcul]);
  if (!vue) return <div ref={zone} className="plan-zone" />;
  const poly = (c: Pt[]) => c.map((q) => versEcran(q).join(",")).join(" ");
  const sel = p.selection;
  const echelleBarre = (() => {
    const cible = 120 / vue.s;
    const pu = Math.pow(10, Math.floor(Math.log10(cible)));
    const v = [5, 2, 1].map((k) => k * pu).find((k) => k <= cible) || pu;
    return { m: v, px: v * vue.s };
  })();

  return (
    <div ref={zone} className="plan-zone" onPointerDown={bas} onPointerMove={mouvement} onPointerUp={haut}
      onPointerCancel={haut} onWheel={molette} onPointerLeave={() => setCurseur(null)}
      style={{ cursor: p.outil === "selection" ? "default" : "crosshair" }}>
      <svg>
        {img && (() => {
          const [x0, y0, x1, y1] = img.b;
          const a = versEcran([x0, y1]), b = versEcran([x1, y0]);
          return <image href={img.url} x={a[0]} y={a[1]} width={b[0] - a[0]} height={b[1] - a[1]} preserveAspectRatio="none" />;
        })()}
        {/* pans */}
        {p.doc.pans.map((pan) => pan.contour && pan.contour.length >= 3 && (
          <polygon key={pan.id} data-cible="pan" data-id={pan.id} points={poly(pan.contour)}
            fill={sel?.type === "pan" && sel.id === pan.id ? "rgba(43,171,226,.38)" : pan.valide ? "rgba(31,157,85,.22)" : "rgba(43,171,226,.18)"}
            stroke={sel?.type === "pan" && sel.id === pan.id ? "#fff" : "#2BABE2"} strokeWidth={sel?.type === "pan" && sel.id === pan.id ? 2.5 : 1.5}
            style={{ cursor: p.outil === "selection" ? "pointer" : undefined }} />
        ))}
        {/* obstacles */}
        {p.doc.obstacles.map((o) => o.contour && o.contour.length >= 3 && (
          <polygon key={o.id} data-cible="obstacle" data-id={o.id} points={poly(o.contour)}
            fill={o.valide || o.source !== "auto" ? "rgba(20,20,20,.55)" : "rgba(217,119,6,.55)"}
            stroke={sel?.type === "obstacle" && sel.id === o.id ? "#fff" : "#111"} strokeWidth={sel?.type === "obstacle" && sel.id === o.id ? 2.5 : 1}
            strokeDasharray={o.source === "auto" && !o.valide ? "4 3" : undefined} />
        ))}
        {/* lignes */}
        {lignes.map((l) => {
          const a = versEcran(l.p1), b = versEcran(l.p2);
          const choisie = sel?.type === "ligne" && sel.cle === l.cle;
          return (
            <g key={l.cle + l.pans.join()}>
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={COULEURS_LIGNES[l.type] || "#ccc"} strokeWidth={choisie ? 6 : 3.5} strokeLinecap="round" />
              <line data-cible="ligne" data-cle={l.cle} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="transparent" strokeWidth={16}
                style={{ cursor: p.outil === "selection" ? "pointer" : undefined, pointerEvents: p.outil === "selection" ? "stroke" : "none" }} />
            </g>
          );
        })}
        {/* étiquettes */}
        {p.doc.pans.map((pan) => {
          if (!pan.contour || pan.contour.length < 3 || !infos[pan.id]) return null;
          const c = versEcran(centroide(pan.contour));
          const i = infos[pan.id];
          return (
            <g key={"t" + pan.id} style={{ pointerEvents: "none" }} fontFamily="system-ui" textAnchor="middle">
              <text x={c[0]} y={c[1] - 4} fontSize={12} fontWeight={700} fill="#fff" stroke="#000" strokeWidth={3} paintOrder="stroke">{pan.nom.split(" (")[0]}</text>
              <text x={c[0]} y={c[1] + 11} fontSize={11} fill="#fff" stroke="#000" strokeWidth={3} paintOrder="stroke">{fr(i.surface, 1)} m² · {Math.round(i.pente_deg)}°</text>
            </g>
          );
        })}
        {/* cotes de référence */}
        {p.doc.echelle.references.map((r) => {
          const a = versEcran([r.p1[0], r.p1[1]]), b = versEcran([r.p2[0], r.p2[1]]);
          return (
            <g key={r.id} data-cible="reference" data-id={r.id} style={{ cursor: "pointer" }}>
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#1F9D55" strokeWidth={3} strokeDasharray="8 4" />
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="transparent" strokeWidth={14} />
              <text x={(a[0] + b[0]) / 2} y={(a[1] + b[1]) / 2 - 8} textAnchor="middle" fontSize={12} fill="#fff" stroke="#1F9D55" strokeWidth={3} paintOrder="stroke">réf. {fr(r.reelle, 2)} m</text>
            </g>
          );
        })}
        {/* sommets du pan sélectionné */}
        {sel?.type === "pan" && p.outil === "selection" && p.doc.pans.find((q) => q.id === sel.id)?.contour?.map((c, i) => {
          const e = versEcran(c);
          return <circle key={i} data-cible="sommet" data-pan={sel.id} data-idx={i} cx={e[0]} cy={e[1]} r={sel.sommet === i ? RAYON_SOMMET + 2 : RAYON_SOMMET}
            fill={sel.sommet === i ? "#2BABE2" : "#fff"} stroke="#23272A" strokeWidth={2} style={{ cursor: "grab" }} />;
        })}
        {/* tracé en cours */}
        {p.enCours.length > 0 && (
          <g style={{ pointerEvents: "none" }}>
            <polyline points={[...p.enCours, ...(curseur ? [curseur] : [])].map((q) => versEcran(q).join(",")).join(" ")} fill="rgba(255,255,255,.12)" stroke="#fff" strokeWidth={2} strokeDasharray="6 4" />
            {p.enCours.map((q, i) => { const e = versEcran(q); return <circle key={i} cx={e[0]} cy={e[1]} r={i === 0 ? 8 : 5} fill={i === 0 ? "#2BABE2" : "#fff"} stroke="#000" />; })}
          </g>
        )}
        {p.mesure && (() => {
          const a = versEcran(p.mesure.p1), b = versEcran(p.mesure.p2 || curseur || p.mesure.p1);
          return (
            <g style={{ pointerEvents: "none" }}>
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#FFD43B" strokeWidth={3} />
              {p.mesure.longueur !== undefined && <text x={(a[0] + b[0]) / 2} y={(a[1] + b[1]) / 2 - 8} textAnchor="middle" fontSize={13} fontWeight={700} fill="#000" stroke="#FFD43B" strokeWidth={4} paintOrder="stroke">{fr(p.mesure.longueur, 2)} m</text>}
            </g>
          );
        })()}
        {curseur && p.outil !== "selection" && (() => { const e = versEcran(curseur); return <circle cx={e[0]} cy={e[1]} r={4} fill="#FFD43B" stroke="#000" style={{ pointerEvents: "none" }} />; })()}
        {/* échelle graphique et nord */}
        <g style={{ pointerEvents: "none" }}>
          <rect x={12} y={taille.h - 26} width={echelleBarre.px} height={5} fill="#fff" stroke="#000" />
          <text x={16 + echelleBarre.px} y={taille.h - 20} fontSize={12} fill="#fff" stroke="#000" strokeWidth={3} paintOrder="stroke">{echelleBarre.m} m</text>
          {m?.type !== "photo" && <g transform={`translate(${taille.w - 26} ${taille.h - 44})`}>
            <path d="M0 -14 L6 6 L0 2 L-6 6 Z" fill="#fff" stroke="#000" />
            <text y={20} textAnchor="middle" fontSize={11} fill="#fff" stroke="#000" strokeWidth={3} paintOrder="stroke">N</text>
          </g>}
        </g>
      </svg>
      <button className="btn petit" style={{ position: "absolute", right: 8, top: 96, zIndex: 2 }} onClick={recentrer} onPointerDown={(e) => e.stopPropagation()}>Recentrer</button>
    </div>
  );
}
