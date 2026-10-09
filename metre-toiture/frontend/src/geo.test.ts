import { describe, expect, it } from "vitest";
import { aire, azimutDe, centroide, dansPolygone, longueur3d, orientation, penteDe, planDepuisPente, projeterSurSegment, zSurPans } from "./geo";
import type { Pan, Pt } from "./types";

const carre: Pt[] = [[0, 0], [10, 0], [10, 4], [0, 4]];

describe("géométrie de l'éditeur", () => {
  it("aire, centroïde et appartenance", () => {
    expect(aire(carre)).toBeCloseTo(40);
    expect(centroide(carre)).toEqual([5, 2]);
    expect(dansPolygone([5, 2], carre)).toBe(true);
    expect(dansPolygone([11, 2], carre)).toBe(false);
  });
  it("plan défini par pente et exposition (cohérent avec le serveur)", () => {
    const p = planDepuisPente(35, 180, 0, 4, 10);
    expect(penteDe(p)).toBeCloseTo(35);
    expect(azimutDe(p)).toBeCloseTo(180);
    expect(orientation(azimutDe(p))).toBe("S");
    // le pan descend vers le sud : z diminue quand y diminue
    expect(p.a * 0 + p.b * 0 + p.c).toBeLessThan(10);
    expect(longueur3d([0, 0], [0, 4], p)).toBeCloseTo(4 / Math.cos((35 * Math.PI) / 180));
  });
  it("altitude d'un point sur les pans et projection sur une arête", () => {
    const pan: Pan = { id: "p1", nom: "Pan", contour: carre, plan: planDepuisPente(30, 180, 0, 4, 8) };
    expect(zSurPans([5, 4 - 1e-9], [pan])).toBeCloseTo(8);
    expect(zSurPans([20, 20], [pan])).toBeNull();
    const pr = projeterSurSegment([5, 3], [0, 0], [10, 0]);
    expect(pr.pt).toEqual([5, 0]);
    expect(pr.d).toBeCloseTo(3);
  });
});
