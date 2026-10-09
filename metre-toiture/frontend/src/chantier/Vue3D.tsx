import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { api } from "../api";
import { COULEURS_LIGNES, zPlan } from "../geo";
import type { Calcul, Chantier, DocumentMetre } from "../types";

/** Vue 3D : nuage de points du modèle + pans et lignes du métré. Repère three.js : x = Est, y = haut, z = Sud. */
export default function Vue3D({ chantier, doc, calcul }: { chantier: Chantier; doc: DocumentMetre; calcul: Calcul | null }) {
  const zone = useRef<HTMLDivElement>(null);
  const scene = useRef<{ scene: THREE.Scene; metre: THREE.Group; z0: number; rendu: () => void } | null>(null);
  const [etat, setEtat] = useState("Chargement du nuage de points…");
  const [nuageVisible, setNuageVisible] = useState(true);
  const nuageRef = useRef<THREE.Points | null>(null);

  useEffect(() => {
    const el = zone.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
    renderer.setSize(el.clientWidth, el.clientHeight);
    el.appendChild(renderer.domElement);
    const sc = new THREE.Scene();
    sc.background = new THREE.Color("#1e2226");
    const cam = new THREE.PerspectiveCamera(50, el.clientWidth / el.clientHeight, 0.1, 5000);
    const ctrl = new OrbitControls(cam, renderer.domElement);
    ctrl.enableDamping = true;
    sc.add(new THREE.AmbientLight(0xffffff, 0.9));
    const dl = new THREE.DirectionalLight(0xffffff, 0.8);
    dl.position.set(30, 60, 20);
    sc.add(dl);
    const metre = new THREE.Group();
    sc.add(metre);

    const pts = doc.pans.flatMap((p) => (p.contour && p.plan ? p.contour.map((c) => [c[0], c[1], zPlan(p.plan!, c[0], c[1])]) : []));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]), zs = pts.map((p) => p[2]);
    const b = pts.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : chantier.modele?.bornes || [-15, -15, 15, 15];
    const z0 = zs.length ? Math.min(...zs) - 3 : 0;
    const cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
    const R = Math.max(8, Math.hypot(b[2] - b[0], b[3] - b[1]));
    cam.position.set(cx + R * 0.8, R * 0.9, -cy + R * 0.9);
    ctrl.target.set(cx, (zs.length ? (Math.max(...zs) + Math.min(...zs)) / 2 : 0) - z0, -cy);
    ctrl.update();

    let actif = true;
    const boucle = () => {
      if (!actif) return;
      ctrl.update();
      renderer.render(sc, cam);
      requestAnimationFrame(boucle);
    };
    boucle();
    const ro = new ResizeObserver(() => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      cam.aspect = el.clientWidth / el.clientHeight;
      cam.updateProjectionMatrix();
    });
    ro.observe(el);
    scene.current = { scene: sc, metre, z0, rendu: () => renderer.render(sc, cam) };

    if (chantier.modele?.type === "odm") {
      const m = 0.4 * R;
      const bbox = [b[0] - m, b[1] - m, b[2] + m, b[3] + m].map((v) => v.toFixed(2)).join(",");
      api.brut(`/api/chantiers/${chantier.id}/nuage?bbox=${bbox}&max_points=600000`).then((r) => r.arrayBuffer()).then((buf) => {
        if (!actif) return;
        const n = new Uint32Array(buf, 0, 1)[0];
        const xyz = new Float32Array(buf, 4, n * 3);
        const rgb = new Uint8Array(buf, 4 + n * 12, n * 3);
        const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) {
          pos[3 * i] = xyz[3 * i];
          pos[3 * i + 1] = xyz[3 * i + 2] - z0;
          pos[3 * i + 2] = -xyz[3 * i + 1];
          col[3 * i] = rgb[3 * i] / 255;
          col[3 * i + 1] = rgb[3 * i + 1] / 255;
          col[3 * i + 2] = rgb[3 * i + 2] / 255;
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
        g.setAttribute("color", new THREE.BufferAttribute(col, 3));
        const nuage = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.06, vertexColors: true }));
        sc.add(nuage);
        nuageRef.current = nuage;
        setEtat(n ? "" : "Aucun point dans cette zone.");
      }).catch(() => setEtat("Nuage de points indisponible (seuls les pans sont affichés)."));
    } else setEtat("");
    return () => {
      actif = false;
      ro.disconnect();
      ctrl.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [chantier.id]); // eslint-disable-line

  // pans et lignes (mis à jour à chaque modification)
  useEffect(() => {
    const s = scene.current;
    if (!s) return;
    s.metre.clear();
    const z0 = s.z0;
    for (const p of doc.pans) {
      if (!p.contour || !p.plan || p.contour.length < 3) continue;
      const forme = new THREE.Shape(p.contour.map((c) => new THREE.Vector2(c[0], c[1])));
      const geom = new THREE.ShapeGeometry(forme);
      const pos = geom.getAttribute("position");
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i);
        pos.setXYZ(i, x, zPlan(p.plan, x, y) - z0 + 0.03, -y);
      }
      geom.computeVertexNormals();
      const mat = new THREE.MeshLambertMaterial({ color: p.valide ? 0x1f9d55 : 0x2babe2, transparent: true, opacity: 0.45, side: THREE.DoubleSide, depthWrite: false });
      s.metre.add(new THREE.Mesh(geom, mat));
    }
    for (const l of calcul?.lignes || []) {
      if (l.manuelle) continue;
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(l.p1[0], l.p1[2] - z0 + 0.06, -l.p1[1]), new THREE.Vector3(l.p2[0], l.p2[2] - z0 + 0.06, -l.p2[1])]);
      s.metre.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: COULEURS_LIGNES[l.type] || "#ccc" })));
    }
  }, [doc, calcul]);

  useEffect(() => {
    if (nuageRef.current) nuageRef.current.visible = nuageVisible;
  }, [nuageVisible]);

  return (
    <div className="plan-zone" style={{ position: "relative" }}>
      <div ref={zone} style={{ position: "absolute", inset: 0 }} />
      <div className="outils">
        {chantier.modele?.type === "odm" && <button className={`btn ${nuageVisible ? "actif" : ""}`} onClick={() => setNuageVisible(!nuageVisible)}>Nuage de points</button>}
      </div>
      <div className="consigne">{etat || "Glisser : tourner · molette / pincer : zoomer · clic droit / deux doigts : déplacer. Les corrections se font sur le plan."}</div>
    </div>
  );
}
