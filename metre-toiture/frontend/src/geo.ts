// Géométrie côté navigateur (affichage et édition). Les calculs de référence restent ceux du serveur.
import type { Pan, Plan, Pt } from "./types";

export const zPlan = (p: Plan, x: number, y: number) => p.a * x + p.b * y + p.c;

export function aireSignee(poly: Pt[]) {
  let s = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    s += x1 * y2 - x2 * y1;
  }
  return s / 2;
}

export const aire = (poly: Pt[]) => Math.abs(aireSignee(poly));

export function centroide(poly: Pt[]): Pt {
  const a = aireSignee(poly);
  if (Math.abs(a) < 1e-9) {
    const n = poly.length;
    return [poly.reduce((s, p) => s + p[0], 0) / n, poly.reduce((s, p) => s + p[1], 0) / n];
  }
  let cx = 0, cy = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    const f = x1 * y2 - x2 * y1;
    cx += (x1 + x2) * f;
    cy += (y1 + y2) * f;
  }
  return [cx / (6 * a), cy / (6 * a)];
}

export function dansPolygone([x, y]: Pt, poly: Pt[]) {
  let dedans = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dedans = !dedans;
  }
  return dedans;
}

export function projeterSurSegment(p: Pt, a: Pt, b: Pt): { pt: Pt; t: number; d: number } {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const L2 = dx * dx + dy * dy;
  let t = L2 > 0 ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2 : 0;
  t = Math.max(0, Math.min(1, t));
  const pt: Pt = [a[0] + t * dx, a[1] + t * dy];
  return { pt, t, d: Math.hypot(p[0] - pt[0], p[1] - pt[1]) };
}

export const dist = (a: Pt, b: Pt) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/** Plan à partir d'une pente (°) et d'une exposition (azimut de la descente, ° depuis le nord). */
export function planDepuisPente(pente: number, azimut: number, x0 = 0, y0 = 0, z0 = 0): Plan {
  const t = Math.tan((pente * Math.PI) / 180);
  const th = (azimut * Math.PI) / 180;
  const a = -t * Math.sin(th);
  const b = -t * Math.cos(th);
  return { a, b, c: z0 - a * x0 - b * y0 };
}

export function penteDe(p: Plan) {
  return (Math.atan(Math.hypot(p.a, p.b)) * 180) / Math.PI;
}

export function azimutDe(p: Plan) {
  if (Math.hypot(p.a, p.b) < 1e-9) return 0;
  return ((Math.atan2(-p.a, -p.b) * 180) / Math.PI + 360) % 360;
}

/** Altitude d'un point : plan du pan qui le contient (sinon null). */
export function zSurPans(pt: Pt, pans: Pan[]): number | null {
  for (const p of pans) if (p.contour && p.plan && dansPolygone(pt, p.contour)) return zPlan(p.plan, pt[0], pt[1]);
  return null;
}

/** Longueur 3D d'un segment posé sur un plan. */
export function longueur3d(a: Pt, b: Pt, plan?: Plan) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const dz = plan ? plan.a * dx + plan.b * dy : 0;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

export function nouvelId(prefixe: string, existants: { id: string }[]) {
  let n = existants.length + 1;
  const ids = new Set(existants.map((e) => e.id));
  while (ids.has(`${prefixe}${n}`)) n++;
  return `${prefixe}${n}`;
}

export const ORIENTATIONS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
export const orientation = (az: number) => ORIENTATIONS[Math.floor(((az + 22.5) % 360) / 45)];

export const COULEURS_LIGNES: Record<string, string> = {
  faitage: "#ff4d5e", aretier: "#ffa53a", noue: "#22c3a6", egout: "#4aa3ff", rive: "#b67cf0",
  rive_haute: "#8c7cf0", bris: "#c27a4c", solin: "#a0a8ad", autre: "#d0d0d0",
};
