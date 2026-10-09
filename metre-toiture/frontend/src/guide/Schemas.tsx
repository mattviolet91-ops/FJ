// Schémas explicatifs du guide (SVG en ligne, lisibles sur mobile et à l'impression).
const BLEU = "#2BABE2";
const GRIS = "#2F3438";
const ROUGE = "#C62828";
const VERT = "#1F9D55";

function Drone({ x, y, r = 0, couleur = GRIS }: { x: number; y: number; r?: number; couleur?: string }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r})`}>
      <rect x={-9} y={-4} width={18} height={8} rx={3} fill={couleur} />
      <line x1={-16} y1={-6} x2={16} y2={-6} stroke={couleur} strokeWidth={2} />
      <circle cx={0} cy={5} r={3} fill={BLEU} />
    </g>
  );
}

function Maison({ x, y, l = 120, h = 50, toit = 45 }: { x: number; y: number; l?: number; h?: number; toit?: number }) {
  return (
    <g>
      <rect x={x} y={y} width={l} height={h} fill="#e8e3da" stroke={GRIS} />
      <polygon points={`${x - 8},${y} ${x + l / 2},${y - toit} ${x + l + 8},${y}`} fill="#b5523b" stroke={GRIS} />
      <rect x={x + l * 0.42} y={y + h - 26} width={16} height={26} fill="#8a6e52" />
    </g>
  );
}

export function SchemaAngles() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 250" role="img" aria-label="Vues verticales et obliques">
        <line x1={0} y1={230} x2={520} y2={230} stroke="#9aa" />
        <Maison x={200} y={170} l={120} h={60} toit={48} />
        {/* verticale */}
        <polygon points="260,40 205,170 315,170" fill={BLEU} opacity={0.12} />
        <Drone x={260} y={36} />
        <text x={275} y={30} fontSize={13} fill={GRIS}>Vue verticale (−90°)</text>
        {/* oblique */}
        <polygon points="90,70 190,140 250,175 150,230" fill={VERT} opacity={0.12} />
        <line x1={90} y1={74} x2={220} y2={160} stroke={VERT} strokeDasharray="4 3" />
        <Drone x={90} y={70} r={35} couleur={VERT} />
        <text x={10} y={56} fontSize={13} fill={VERT}>Oblique (−30° à −50°)</text>
        <text x={10} y={72} fontSize={11} fill={GRIS}>voit les pans raides,</text>
        <text x={10} y={86} fontSize={11} fill={GRIS}>rives, égouts, noues</text>
        {/* horizontale */}
        <Drone x={470} y={160} r={-5} couleur={ROUGE} />
        <line x1={460} y1={162} x2={330} y2={170} stroke={ROUGE} strokeDasharray="4 3" />
        <text x={400} y={140} fontSize={12} fill={ROUGE}>Trop rasante :</text>
        <text x={400} y={154} fontSize={11} fill={GRIS}>voit les murs, pas le toit</text>
      </svg>
      <figcaption>Combinez des vues verticales (contours, orthophoto) et des vues obliques (pentes, détails).</figcaption>
    </figure>
  );
}

export function SchemaOrbite() {
  const pts = Array.from({ length: 12 }, (_, i) => (i * 30 * Math.PI) / 180);
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 300" role="img" aria-label="Orbite autour du bâtiment">
        <circle cx={260} cy={150} r={118} fill="none" stroke={BLEU} strokeDasharray="6 5" />
        <rect x={205} y={115} width={110} height={70} fill="#b5523b" stroke={GRIS} />
        <line x1={205} y1={150} x2={315} y2={150} stroke="#fff" strokeWidth={2} />
        <text x={260} y={110} textAnchor="middle" fontSize={11} fill={GRIS}>faîtage</text>
        {pts.map((a, i) => {
          const x = 260 + 118 * Math.sin(a), y = 150 - 118 * Math.cos(a);
          return (
            <g key={i}>
              <line x1={x} y1={y} x2={260 + 40 * Math.sin(a)} y2={150 - 40 * Math.cos(a)} stroke={BLEU} opacity={0.5} />
              <circle cx={x} cy={y} r={6} fill={BLEU} />
            </g>
          );
        })}
        <text x={392} y={40} fontSize={12} fill={GRIS}>Une photo tous les</text>
        <text x={392} y={56} fontSize={12} fill={GRIS}>8 à 15° (ici 30°</text>
        <text x={392} y={72} fontSize={12} fill={GRIS}>pour la lisibilité)</text>
        <text x={10} y={290} fontSize={12} fill={GRIS}>Nacelle orientée vers le centre du toit, tour COMPLET, toit entier dans le cadre.</text>
      </svg>
      <figcaption>Vue de dessus : orbite oblique autour du bâtiment.</figcaption>
    </figure>
  );
}

export function SchemaRecouvrement() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 210" role="img" aria-label="Recouvrement entre photos">
        {[0, 1, 2, 3].map((i) => (
          <rect key={i} x={40 + i * 50} y={30 + (i % 2) * 6} width={200} height={140} fill={BLEU} opacity={0.13}
            stroke={BLEU} />
        ))}
        <rect x={140} y={70} width={120} height={70} fill="#b5523b" opacity={0.8} />
        <line x1={40} y1={185} x2={240} y2={185} stroke={GRIS} />
        <line x1={90} y1={195} x2={240} y2={195} stroke={VERT} strokeWidth={3} />
        <text x={250} y={200} fontSize={12} fill={VERT}>partie commune ≈ 75 %</text>
        <text x={380} y={60} fontSize={12} fill={GRIS}>Chaque point du toit</text>
        <text x={380} y={76} fontSize={12} fill={GRIS}>doit apparaître sur</text>
        <text x={380} y={92} fontSize={12} fill={GRIS}>plusieurs photos,</text>
        <text x={380} y={108} fontSize={12} fill={GRIS}>prises de positions</text>
        <text x={380} y={124} fontSize={12} fill={GRIS}>différentes.</text>
      </svg>
      <figcaption>Recouvrement : deux photos successives partagent environ les trois quarts de leur surface.</figcaption>
    </figure>
  );
}

export function SchemaHauteur() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 230" role="img" aria-label="Hauteur et taille du pixel">
        <line x1={0} y1={210} x2={520} y2={210} stroke="#9aa" />
        <Maison x={190} y={150} l={140} h={60} toit={40} />
        <polygon points="260,30 150,110 370,110" fill={BLEU} opacity={0.12} />
        <Drone x={260} y={26} />
        <line x1={440} y1={30} x2={440} y2={110} stroke={GRIS} markerEnd="url(#f)" markerStart="url(#f)" />
        <text x={448} y={74} fontSize={12} fill={GRIS}>hauteur au-dessus</text>
        <text x={448} y={88} fontSize={12} fill={GRIS}>du faîtage</text>
        <text x={20} y={40} fontSize={12} fill={GRIS}>Plus bas = plus de détails</text>
        <text x={20} y={56} fontSize={12} fill={GRIS}>mais plus de photos.</text>
        <defs>
          <marker id="f" viewBox="0 0 10 10" refX={5} refY={5} markerWidth={6} markerHeight={6} orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill={GRIS} />
          </marker>
        </defs>
      </svg>
      <figcaption>La taille du pixel au sol (cm/pixel) dépend de la hauteur au-dessus du toit, de la focale et de la résolution.</figcaption>
    </figure>
  );
}

export function SchemaReference() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 200" role="img" aria-label="Dimension de référence">
        <rect x={110} y={40} width={300} height={110} fill="#b5523b" stroke={GRIS} />
        <line x1={110} y1={95} x2={410} y2={95} stroke="#fff" strokeWidth={2} />
        <line x1={110} y1={168} x2={410} y2={168} stroke={VERT} strokeWidth={3} />
        <line x1={110} y1={160} x2={110} y2={176} stroke={VERT} strokeWidth={3} />
        <line x1={410} y1={160} x2={410} y2={176} stroke={VERT} strokeWidth={3} />
        <text x={260} y={190} textAnchor="middle" fontSize={13} fill={VERT}>Longueur d'égout mesurée au mètre : 12,46 m</text>
        <text x={260} y={30} textAnchor="middle" fontSize={12} fill={GRIS}>Choisissez une cote longue, nette et facile à pointer sur le plan</text>
      </svg>
      <figcaption>Une cote réelle, mesurée sur place, permet de vérifier et corriger l'échelle du modèle.</figcaption>
    </figure>
  );
}

export function SchemaZoneCachee() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 220" role="img" aria-label="Zone cachée par un arbre">
        <line x1={0} y1={200} x2={520} y2={200} stroke="#9aa" />
        <Maison x={170} y={140} l={160} h={60} toit={50} />
        <circle cx={360} cy={110} r={46} fill="#3f7f3a" opacity={0.9} />
        <rect x={355} y={150} width={10} height={50} fill="#6b4f2e" />
        <Drone x={470} y={60} couleur={ROUGE} />
        <line x1={462} y1={66} x2={380} y2={110} stroke={ROUGE} strokeDasharray="4 3" />
        <text x={400} y={30} fontSize={11} fill={ROUGE}>caché par l'arbre</text>
        <Drone x={300} y={20} couleur={VERT} />
        <line x1={300} y1={26} x2={300} y2={95} stroke={VERT} strokeDasharray="4 3" />
        <Drone x={80} y={50} couleur={VERT} />
        <line x1={88} y1={56} x2={290} y2={110} stroke={VERT} strokeDasharray="4 3" />
        <text x={20} y={30} fontSize={11} fill={VERT}>autres angles : versant visible</text>
      </svg>
      <figcaption>Montez et changez de côté pour voir derrière l'obstacle ; sinon, mesurez la zone à la main.</figcaption>
    </figure>
  );
}

export function SchemaCorrection() {
  return (
    <figure className="schema">
      <svg viewBox="0 0 520 240" role="img" aria-label="Pans et lignes">
        <polygon points="80,200 260,200 260,40 140,40" fill={BLEU} opacity={0.25} stroke={BLEU} />
        <polygon points="260,200 440,200 380,40 260,40" fill={BLEU} opacity={0.4} stroke={BLEU} />
        <line x1={140} y1={40} x2={380} y2={40} stroke="#ffa53a" strokeWidth={4} />
        <line x1={260} y1={40} x2={260} y2={200} stroke="#ff4d5e" strokeWidth={4} />
        <line x1={80} y1={200} x2={440} y2={200} stroke="#4aa3ff" strokeWidth={4} />
        <line x1={80} y1={200} x2={140} y2={40} stroke="#b67cf0" strokeWidth={4} />
        <line x1={440} y1={200} x2={380} y2={40} stroke="#b67cf0" strokeWidth={4} />
        {[[80, 200], [260, 200], [440, 200], [140, 40], [260, 40], [380, 40]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={7} fill="white" stroke={GRIS} strokeWidth={2} />
        ))}
        <rect x={300} y={90} width={26} height={26} fill={GRIS} opacity={0.75} />
        <text x={331} y={108} fontSize={11} fill={GRIS}>cheminée</text>
        <text x={160} y={130} fontSize={13} fill={GRIS}>Pan 1</text>
        <text x={320} y={160} fontSize={13} fill={GRIS}>Pan 2</text>
        <text x={470} y={70} fontSize={11} fill={GRIS}>● sommet</text>
        <text x={470} y={86} fontSize={11} fill={GRIS}>déplaçable</text>
      </svg>
      <figcaption>Chaque pan est un contour ; les lignes (faîtage, égout, rives…) sont déduites des contours.</figcaption>
    </figure>
  );
}

/** Exemples de bonnes et mauvaises prises de vue (illustrations générées). */
export function ExemplesPrises() {
  const tuiles = (id: string) => (
    <pattern id={id} width={16} height={10} patternUnits="userSpaceOnUse">
      <rect width={16} height={10} fill="#b8573e" />
      <path d="M0 9.5H16M8 0V9.5" stroke="#7c3626" strokeWidth={1} />
      <path d="M0 0H16" stroke="#d07a5e" strokeWidth={1} />
    </pattern>
  );
  const scene = (id: string, filtre?: string, echelle = 1, decalage = 0) => (
    <svg viewBox="0 0 200 140" style={{ display: "block", width: "100%" }}>
      <defs>
        {tuiles(`t-${id}`)}
        <filter id={`flou-${id}`}><feGaussianBlur stdDeviation={2.6} /></filter>
        <filter id={`sur-${id}`}><feComponentTransfer><feFuncR type="linear" slope={2.2} intercept={0.35} /><feFuncG type="linear" slope={2.2} intercept={0.35} /><feFuncB type="linear" slope={2.2} intercept={0.35} /></feComponentTransfer></filter>
        <filter id={`sombre-${id}`}><feComponentTransfer><feFuncR type="linear" slope={0.28} /><feFuncG type="linear" slope={0.28} /><feFuncB type="linear" slope={0.32} /></feComponentTransfer></filter>
      </defs>
      <g filter={filtre ? `url(#${filtre}-${id})` : undefined}>
        <rect width={200} height={140} fill="#7da35a" />
        <g transform={`translate(${100 + decalage} 70) scale(${echelle}) translate(-100 -70)`}>
          <rect x={40} y={30} width={120} height={80} fill={`url(#t-${id})`} stroke="#3a2a22" />
          <line x1={40} y1={70} x2={160} y2={70} stroke="#e9e1d6" strokeWidth={3} />
          <rect x={120} y={40} width={12} height={12} fill="#6d6d6d" />
          <rect x={60} y={82} width={14} height={18} fill="#3b5a72" />
        </g>
      </g>
    </svg>
  );
  const ex = [
    { bon: true, titre: "Nette et bien exposée", texte: "Tuiles lisibles, toit entier dans le cadre.", el: scene("ok") },
    { bon: false, titre: "Floue (bougé)", texte: "Drone en mouvement ou vitesse lente : à refaire.", el: scene("flou", "flou") },
    { bon: false, titre: "Surexposée", texte: "Zones blanches sans détail : baissez l'exposition.", el: scene("sur", "sur") },
    { bon: false, titre: "Trop sombre", texte: "Contre-jour ou fin de journée.", el: scene("sombre", "sombre") },
    { bon: false, titre: "Trop loin", texte: "Le toit occupe peu de pixels : descendez.", el: scene("loin", undefined, 0.4) },
    { bon: false, titre: "Toit coupé", texte: "Une partie du versant est hors cadre.", el: scene("coupe", undefined, 1.25, 70) },
  ];
  return (
    <div className="exemples">
      {ex.map((e) => (
        <div key={e.titre} className={`exemple ${e.bon ? "bon" : "mauvais"}`}>
          {e.el}
          <div><b style={{ color: e.bon ? VERT : ROUGE }}>{e.bon ? "✓" : "✗"} {e.titre}</b>{e.texte}</div>
        </div>
      ))}
    </div>
  );
}
