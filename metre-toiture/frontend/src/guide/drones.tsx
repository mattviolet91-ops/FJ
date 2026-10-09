// Fiches pratiques par drone. Caractéristiques indicatives (fiche constructeur) : à vérifier selon la version
// du firmware et de l'application DJI Fly.
import { Checklist } from "./contenu";

export const REGLAGES_MINI_4K: [string, string][] = [
  ["Format photo", "JPEG, ratio 4:3 (12 MP, 4000 × 3000). Jamais 16:9 : l'image est rognée."],
  ["Zoom", "Aucun (×1). Le zoom numérique dégrade l'image et fausse le calibrage."],
  ["Mode photo", "« Simple » pour l'orbite et les détails ; « Photo à intervalle » (3 s) pour les passages verticaux."],
  ["Exposition", "Auto avec correction −0,3 IL ; −0,7 IL si tuiles claires, zinc ou bac acier au soleil. En mode Pro (si disponible) : ISO 100 et vitesse ≥ 1/500 s."],
  ["Balance des blancs", "Fixe (préréglage « ensoleillé » ou « nuageux » selon le ciel), pas en automatique : couleurs constantes d'une photo à l'autre."],
  ["Nacelle", "−90° pour les verticales, −45° pour l'orbite principale, −30° pour l'orbite basse."],
  ["Mode de vol", "Cine (le plus doux) pendant les prises de vue, Normal pour les déplacements. Arrêt complet avant chaque photo."],
  ["Affichage", "Grille et histogramme activés (cadrage et contrôle de l'exposition)."],
  ["Retour au point de départ", "Altitude RTH au-dessus du plus haut obstacle du secteur (ex. 40 m) ; action en cas de perte de signal : RTH."],
  ["Carte mémoire", "microSD rapide (U3 / V30), vidée avant le vol."],
  ["Avant le vol", "Firmware à jour, hélices en bon état, compas calibré loin du métal si l'application le demande, batteries pleines (2 conseillées)."],
];

export const AVANTAGES_MINI_4K = [
  "Moins de 250 g : léger, discret, catégorie de drone aux formalités allégées (vérifiez tout de même l'enregistrement exploitant, l'assurance et les zones).",
  "Capteur 12 MP et focale 24 mm : environ 1,2 cm/pixel sur le toit à ~33 m au-dessus du faîtage, suffisant pour un métré de devis.",
  "Nacelle stabilisée 3 axes inclinable jusqu'à −90° : vues verticales et obliques.",
  "Position GPS et orientation de la nacelle enregistrées dans les photos : l'analyse automatique de l'application fonctionne pleinement.",
  "Peu coûteux et rapide à déployer sur chantier.",
];

export const INCONVENIENTS_MINI_4K = [
  "Pas de vol automatique par points de passage dans DJI Fly (à ma connaissance) : quadrillage et orbite se font à la main, ce qui demande de la régularité.",
  "Aucune détection d'obstacles (seulement un capteur vers le bas) : vigilance absolue près des cheminées, antennes, arbres et câbles.",
  "Obturateur électronique : photo floue ou déformée si le drone bouge ; il faut s'arrêter à chaque déclenchement.",
  "Petit capteur 1/2,3\" : bruit en faible lumière ; volez plutôt en journée sous un ciel lumineux.",
  "Très léger : sensible au vent, évitez les rafales (la tenue au vent annoncée par DJI est un maximum, pas une condition de travail).",
  "GPS grand public : l'échelle du modèle n'est pas garantie — une cote mesurée au mètre est indispensable.",
  "Autonomie réelle d'environ 18–20 min sur l'annonce de 31 min : prévoyez 2 batteries pour un toit complexe.",
];

export const DEROULE_MINI_4K = [
  "Décollez d'un point dégagé, montez à la hauteur indiquée par le plan (≈ 41 m au-dessus du sol pour un pavillon de 8 m au faîtage, précision « devis »).",
  "Passages verticaux : nacelle à −90°, mode « Photo à intervalle » 3 s, avancez en ligne droite à ≈ 2,5 m/s le long du faîtage ; décalez-vous d'environ 14 m et revenez en sens inverse (4 lignes pour un pavillon 12 × 9 m). Débordez de 5 m autour du bâtiment.",
  "Orbite principale : nacelle à −45°, ≈ 35 m de hauteur et ≈ 29 m du centre du toit. Faites le tour complet en vous arrêtant tous les ~10° (36 photos), toit entier dans le cadre. Le mode « Cercle » des QuickShots filme une vidéo : il ne remplace pas les photos.",
  "Toit complexe : seconde orbite plus basse (nacelle −30°), en restant à bonne distance des obstacles.",
  "Détails : noues, cheminées, raccords contre mur, chacun pris de 2 ou 3 positions.",
  "Avant de partir : agrandissez quelques photos, puis importez-les dans l'application pour lancer l'analyse.",
];

export function FicheMini4K({ compacte = false }: { compacte?: boolean }) {
  return (
    <div className="pile">
      <p>Caractéristiques indicatives (fiche DJI) : capteur 1/2,3" 12 MP (4000 × 3000), focale équivalente 24 mm,
        ouverture f/2,8, obturateur électronique, nacelle 3 axes (jusqu'à −90°), moins de 249 g, autonomie annoncée
        31 min, application DJI Fly. <small>À vérifier selon votre firmware.</small></p>
      <h3>Réglages à faire dans DJI Fly</h3>
      <div className="defile-x">
        <table className="tableau"><tbody>
          {REGLAGES_MINI_4K.map(([k, v]) => <tr key={k}><td style={{ whiteSpace: "nowrap" }}><b>{k}</b></td><td>{v}</td></tr>)}
        </tbody></table>
      </div>
      {!compacte && (
        <>
          <h3>Déroulé du vol (pavillon type)</h3>
          <ol>{DEROULE_MINI_4K.map((d, i) => <li key={i}>{d}</li>)}</ol>
          <p><small>Pour votre chantier, l'assistant de préparation recalcule hauteurs, espacements et nombre de photos
            selon les dimensions du toit.</small></p>
        </>
      )}
      <div className="grille g2">
        <div className="alerte ok" style={{ marginBottom: 0 }}><b>Avantages</b><ul style={{ margin: 0, paddingLeft: "1.1em" }}>{AVANTAGES_MINI_4K.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
        <div className="alerte attention" style={{ marginBottom: 0 }}><b>Inconvénients et précautions</b><ul style={{ margin: 0, paddingLeft: "1.1em" }}>{INCONVENIENTS_MINI_4K.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
      </div>
      {!compacte && <Checklist id="reglages-mini4k" items={REGLAGES_MINI_4K.map(([k]) => `Réglage vérifié : ${k}`)} />}
    </div>
  );
}
