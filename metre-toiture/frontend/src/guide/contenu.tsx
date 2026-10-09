import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { ExemplesPrises, SchemaAngles, SchemaCorrection, SchemaHauteur, SchemaOrbite, SchemaRecouvrement,
  SchemaReference, SchemaZoneCachee } from "./Schemas";

export interface Section {
  id: string;
  groupe: string;
  titre: string;
  contenu: () => ReactNode;
}

function lireLocal(cle: string): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(cle) || "{}");
  } catch {
    return {};
  }
}

/** Liste de contrôle cochable, mémorisée sur l'appareil (utile sur le chantier, même hors ligne). */
export function Checklist({ id, items }: { id: string; items: string[] }) {
  const cle = `mmt-checklist-${id}`;
  const [etat, setEtat] = useState<Record<string, boolean>>(() => lireLocal(cle));
  const basculer = (i: number) => {
    const n = { ...etat, [i]: !etat[i] };
    setEtat(n);
    try {
      localStorage.setItem(cle, JSON.stringify(n));
    } catch {
      /* stockage indisponible : la liste fonctionne sans mémorisation */
    }
  };
  const faits = items.filter((_, i) => etat[i]).length;
  return (
    <div className="carte" style={{ background: "#f7fafb", boxShadow: "none", border: "1px solid var(--bordure)" }}>
      <div className="ligne" style={{ marginBottom: 6 }}>
        <b>Liste de contrôle</b>
        <span className="espace" />
        <span className={`badge ${faits === items.length ? "vert" : ""}`}>{faits}/{items.length}</span>
        {faits > 0 && (
          <button className="lien" onClick={() => { setEtat({}); try { localStorage.removeItem(cle); } catch { /* */ } }}>
            Réinitialiser
          </button>
        )}
      </div>
      <div className="pile">
        {items.map((t, i) => (
          <label key={i} className="case">
            <input type="checkbox" checked={!!etat[i]} onChange={() => basculer(i)} />
            <span style={{ textDecoration: etat[i] ? "line-through" : undefined, opacity: etat[i] ? 0.65 : 1 }}>{t}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

export function CalculateurGSD() {
  const [f35, setF35] = useState(24);
  const [w, setW] = useState(4032);
  const [h, setH] = useState(3024);
  const [haut, setHaut] = useState(30);
  const diag = Math.hypot(w, h);
  const gsd = (100 * haut * 43.2666) / (f35 * diag);
  const ok = f35 > 0 && w > 0 && h > 0 && haut > 0;
  return (
    <div className="carte" style={{ background: "#f7fafb", boxShadow: "none", border: "1px solid var(--bordure)" }}>
      <b>Calculateur : taille du pixel sur le toit</b>
      <div className="grille g4" style={{ marginTop: 8 }}>
        <label className="champ">Focale équiv. 24×36 (mm)<input type="number" inputMode="decimal" value={f35} onChange={(e) => setF35(+e.target.value)} /></label>
        <label className="champ">Largeur image (px)<input type="number" inputMode="numeric" value={w} onChange={(e) => setW(+e.target.value)} /></label>
        <label className="champ">Hauteur image (px)<input type="number" inputMode="numeric" value={h} onChange={(e) => setH(+e.target.value)} /></label>
        <label className="champ">Hauteur au-dessus du toit (m)<input type="number" inputMode="decimal" value={haut} onChange={(e) => setHaut(+e.target.value)} /></label>
      </div>
      {ok && (
        <p style={{ marginTop: 10, marginBottom: 0 }}>
          ≈ <b>{gsd.toFixed(2).replace(".", ",")} cm par pixel</b> sur le toit ; une photo couvre environ{" "}
          <b>{((gsd * w) / 100).toFixed(0)} × {((gsd * h) / 100).toFixed(0)} m</b>.
          <br /><small>Ces valeurs se trouvent dans les propriétés d'une photo (EXIF). Calcul pour une vue verticale.</small>
        </p>
      )}
    </div>
  );
}

const CONTROLE_TERRAIN = [
  "Agrandir 3 ou 4 photos au hasard : tuiles nettes, sans flou de bougé",
  "Chaque versant apparaît sur de nombreuses photos, sous plusieurs angles",
  "Le tour complet en oblique a été fait (aucun côté oublié, y compris mitoyen ou arbres)",
  "Les détails délicats (noues, cheminées, fenêtres de toit, raccords) ont des photos rapprochées",
  "Au moins une cote de référence a été mesurée au mètre et notée",
  "Photos importées dans l'application et analyse de qualité consultée",
];

export const SECTIONS: Section[] = [
  // ------------------------------------------------------------------ A
  {
    id: "a-preparer", groupe: "A. Prise de vue par drone", titre: "Préparer un vol de toiture",
    contenu: () => (
      <>
        <p>Un bon métré se joue <b>avant le décollage</b>. La reconstruction 3D ne peut mesurer que ce qui a été
          photographié correctement : un versant oublié ou flou ne sera pas « rattrapé » par le calcul.</p>
        <h3>La veille</h3>
        <ul>
          <li>Vérifiez la réglementation du lieu (zones restreintes, survol de tiers, vol en agglomération, catégorie
            d'exploitation et formation requises) et obtenez l'accord du propriétaire. En cas de doute, ne volez pas.</li>
          <li>Préparez le plan de prise de vue du chantier avec l'<b>assistant de préparation</b> (onglet
            « Préparation » du chantier) : il calcule hauteur, espacements et nombre de photos pour votre drone.</li>
          <li>Chargez les batteries, videz la carte mémoire, nettoyez l'objectif.</li>
          <li>Météo : évitez vent fort, pluie (toiture mouillée = reflets) et soleil rasant (ombres longues).</li>
        </ul>
        <h3>Réglages de l'appareil photo</h3>
        <ul>
          <li>Photos <b>JPEG d'origine</b> (pas de capture d'écran, pas de retouche, pas de recadrage).</li>
          <li>Géolocalisation et horodatage activés ; ratio 4:3 (pleine résolution du capteur).</li>
          <li>Mise au point automatique ; si possible vitesse d'obturation rapide (1/500 s ou plus).</li>
          <li>Ne zoomez pas : la reconstruction a besoin d'une focale constante.</li>
        </ul>
        <h3>Sur place</h3>
        <ul>
          <li>Faites le tour à pied : arbres, câbles, antennes, mitoyennetés, accès au point de décollage.</li>
          <li><b>Mesurez au mètre au moins une cote</b> facile à retrouver sur le plan (voir « Dimension de
            référence »).</li>
        </ul>
      </>
    ),
  },
  {
    id: "a-hauteur", groupe: "A. Prise de vue par drone", titre: "Quelle hauteur de vol ?",
    contenu: () => (
      <>
        <p>Il n'existe pas de hauteur « universelle » : elle dépend de la caméra, de la taille du toit et de la
          précision recherchée. Le bon repère est la <b>taille du pixel sur le toit</b> (en cm/pixel).</p>
        <SchemaHauteur />
        <ul>
          <li><b>≈ 2 cm/pixel</b> : suffisant pour un avant-métré rapide d'un toit simple.</li>
          <li><b>≈ 1 à 1,5 cm/pixel</b> : recommandé pour un devis (contours et pentes fiables).</li>
          <li><b>&lt; 1 cm/pixel</b> : toits complexes, petits éléments, ou besoin de grande précision.</li>
        </ul>
        <p>Descendre améliore le détail mais multiplie les photos et le temps de calcul. Restez toujours à une
          hauteur de sécurité suffisante au-dessus du point le plus haut (cheminée, antenne, arbre).</p>
        <CalculateurGSD />
      </>
    ),
  },
  {
    id: "a-angles", groupe: "A. Prise de vue par drone", titre: "Angles de prise de vue",
    contenu: () => (
      <>
        <SchemaAngles />
        <ul>
          <li><b>Vues verticales</b> (nacelle à −90°) : donnent l'orthophoto et des contours précis en plan. Seules,
            elles reconstruisent mal les pans raides et les rives.</li>
          <li><b>Vues obliques</b> (nacelle entre −30° et −50°) : indispensables pour la 3D des pans, égouts, rives,
            noues, lucarnes et souches de cheminée.</li>
          <li>Évitez les vues quasi horizontales : elles voient les façades mais très peu la couverture.</li>
          <li>Pour une mansarde ou des brisis, ajoutez une orbite plus basse (−20° à −30°).</li>
        </ul>
      </>
    ),
  },
  {
    id: "a-versants", groupe: "A. Prise de vue par drone", titre: "Photographier chaque versant",
    contenu: () => (
      <>
        <SchemaOrbite />
        <ol>
          <li>Placez-vous à une distance qui permet de voir <b>tout le toit</b> dans le cadre, nacelle vers −45°.</li>
          <li>Tournez autour du bâtiment en gardant le centre du toit au milieu de l'image (le mode « point
            d'intérêt » de votre drone facilite cette orbite).</li>
          <li>Déclenchez à intervalles réguliers : environ tous les 10° pour un devis (36 photos par tour), 15° pour
            une estimation.</li>
          <li>Pour un toit complexe, faites une seconde orbite à une autre hauteur et inclinaison.</li>
          <li>Complétez par des photos rapprochées des détails, chacun pris depuis 2 ou 3 positions.</li>
        </ol>
        <div className="alerte info">Un versant photographié depuis un seul point de vue est mal reconstruit :
          ce qui compte, c'est la <b>diversité des positions</b>, pas le nombre de photos identiques.</div>
      </>
    ),
  },
  {
    id: "a-recouvrement", groupe: "A. Prise de vue par drone", titre: "Recouvrement entre les images",
    contenu: () => (
      <>
        <SchemaRecouvrement />
        <ul>
          <li>Passages verticaux : visez environ <b>75 à 80 %</b> de recouvrement entre deux photos successives et
            environ 65 à 70 % entre deux lignes de vol.</li>
          <li>Orbite : un écart d'environ 10° entre deux photos assure un recouvrement largement suffisant.</li>
          <li>En vol manuel, utilisez le déclenchement par intervalle (2 à 3 s) et une vitesse lente et constante.</li>
        </ul>
        <p>L'application estime le recouvrement des vues verticales à partir du GPS, de l'altitude et de l'optique
          <b> quand ces informations sont présentes</b>. Sinon, elle l'indique « non évaluable » plutôt que de
          supposer qu'il est suffisant.</p>
      </>
    ),
  },
  {
    id: "a-nombre", groupe: "A. Prise de vue par drone", titre: "Combien de photos ?",
    contenu: () => (
      <>
        <p>Ordres de grandeur calculés par l'assistant pour un drone 12 MP à focale équivalente 24 mm
          (ex. DJI Mini 3), passages verticaux + orbite(s) + détails :</p>
        <div className="defile-x">
          <table className="tableau">
            <thead><tr><th>Toiture</th><th className="num">Estimation (≈2 cm/px)</th><th className="num">Devis (≈1,2 cm/px)</th></tr></thead>
            <tbody>
              <tr><td>Deux pans, 12 × 9 m</td><td className="num">≈ 40</td><td className="num">≈ 65</td></tr>
              <tr><td>Quatre pans, 14 × 10 m</td><td className="num">≈ 70</td><td className="num">≈ 100</td></tr>
              <tr><td>Complexe (noues, lucarnes), 18 × 12 m</td><td className="num">≈ 110</td><td className="num">≈ 125</td></tr>
              <tr><td>Grand bâtiment deux pans, 30 × 15 m</td><td className="num">≈ 50</td><td className="num">≈ 70</td></tr>
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: 10 }}>Ces chiffres varient avec la caméra, la hauteur et la complexité : utilisez
          l'assistant de préparation du chantier pour obtenir le plan adapté à <i>votre</i> situation. Au-delà d'un
          certain nombre, ajouter des photos semblables n'améliore plus le résultat mais allonge le calcul.</p>
      </>
    ),
  },
  {
    id: "a-qualite", groupe: "A. Prise de vue par drone", titre: "Photos nettes et bien exposées",
    contenu: () => (
      <>
        <ExemplesPrises />
        <h3>Éviter le flou</h3>
        <ul>
          <li>Marquez un temps d'arrêt avant chaque photo, surtout avec un obturateur électronique (la plupart des
            drones grand public) qui déforme les images prises en mouvement.</li>
          <li>Par vent, réduisez la vitesse et augmentez la vitesse d'obturation.</li>
        </ul>
        <h3>Éviter la surexposition et les photos sombres</h3>
        <ul>
          <li>Tuiles claires, zinc, bacs acier : baissez la correction d'exposition (−0,3 à −0,7 IL).</li>
          <li>Évitez le contre-jour et les fins de journée ; une lumière voilée et homogène est idéale.</li>
          <li>Gardez une exposition aussi constante que possible pendant tout le vol.</li>
        </ul>
        <p>À l'import, l'application mesure la netteté de chaque photo <b>par rapport au reste de la série</b> et
          repère les zones « brûlées » ou trop sombres ; vous pouvez exclure les photos en cause d'un clic.</p>
      </>
    ),
  },
  {
    id: "a-obstacles", groupe: "A. Prise de vue par drone", titre: "Obstacles, arbres, cheminées, zones cachées",
    contenu: () => (
      <>
        <SchemaZoneCachee />
        <ul>
          <li><b>Arbres en surplomb</b> : la photogrammétrie ne voit pas à travers le feuillage. Multipliez les vues
            depuis les côtés dégagés ; mesurez au mètre ce qui reste caché et signalez-le en réserve.</li>
          <li><b>Cheminées, sorties, antennes</b> : photographiez-les de plusieurs côtés ; elles sont détectées comme
            « émergences » à confirmer et peuvent être déduites de la surface si besoin.</li>
          <li><b>Fenêtres de toit</b> : affleurantes, elles ne se voient pas en 3D ; elles se repèrent sur
            l'orthophoto et se saisissent dans l'éditeur.</li>
          <li><b>Mitoyenneté</b> : le versant contre le voisin se photographie depuis plus haut. Repérez la limite
            sur place.</li>
          <li><b>Câbles</b> : souvent invisibles à l'écran du drone ; gardez une marge importante.</li>
        </ul>
      </>
    ),
  },
  {
    id: "a-gps", groupe: "A. Prise de vue par drone", titre: "GPS et métadonnées du drone",
    contenu: () => (
      <>
        <p>Chaque photo contient des métadonnées (EXIF/XMP) que l'application exploite :</p>
        <ul>
          <li><b>Position GPS</b> : donne l'échelle et l'orientation (nord) du modèle 3D. Sans GPS, le modèle n'a pas
            d'échelle métrique : une dimension de référence devient obligatoire.</li>
          <li><b>Altitude relative</b> et <b>orientation de la nacelle</b> (drones DJI notamment) : permettent
            d'évaluer les angles de vue, la couverture autour du bâtiment et le recouvrement.</li>
          <li><b>Focale et résolution</b> : permettent de calculer la taille du pixel.</li>
        </ul>
        <div className="alerte attention"><b>Le GPS d'un drone grand public n'est pas un instrument de mesure.</b>
          L'échelle qui en résulte est souvent correcte à quelques pourcents près, mais ce n'est pas garanti :
          c'est pourquoi l'application signale une échelle « non vérifiée » tant qu'aucune cote réelle n'a été
          saisie.</div>
        <p>Ne passez pas les photos par un logiciel qui supprime les métadonnées (messageries, retouche).
          Transférez directement la carte mémoire ou le dossier d'origine.</p>
      </>
    ),
  },
  {
    id: "a-reference", groupe: "A. Prise de vue par drone", titre: "Dimension de référence et points de contrôle",
    contenu: () => (
      <>
        <SchemaReference />
        <h3>Dimension de référence (recommandée à chaque chantier)</h3>
        <ul>
          <li>Mesurez au mètre ruban ou au télémètre une longueur nette : égout, gouttière, largeur de pignon,
            longueur de façade sous l'égout.</li>
          <li>Plus la cote est longue, plus le contrôle est précis : une erreur de pointé de 3 cm pèse 0,3 % sur
            10 m mais 3 % sur 1 m.</li>
          <li>Deux cotes dans des directions différentes permettent de vérifier la cohérence de l'échelle.</li>
          <li>Dans l'éditeur, outil « Cote de référence » : cliquez les deux extrémités et saisissez la valeur
            réelle. L'échelle de tout le métré est alors recalée.</li>
        </ul>
        <h3>Points de contrôle au sol (GCP)</h3>
        <p>Pour une précision absolue (grands bâtiments, géoréférencement), des cibles mesurées au GNSS RTK peuvent
          être fournies au format OpenDroneMap (<code>gcp_list.txt</code>) lors de l'import des photos. C'est
          rarement nécessaire pour un devis de couverture : une bonne cote de référence suffit en général.</p>
      </>
    ),
  },
  {
    id: "a-controle", groupe: "A. Prise de vue par drone", titre: "Vérifier avant de quitter le chantier",
    contenu: () => (
      <>
        <p>Revenir sur un chantier coûte bien plus cher que cinq minutes de contrôle. Avant de ranger le drone :</p>
        <Checklist id="terrain" items={CONTROLE_TERRAIN} />
        <p style={{ marginTop: 10 }}>Si vous avez du réseau, importez les photos depuis la tablette ou le téléphone :
          l'analyse automatique signale les versants peu photographiés <b>pendant que vous êtes encore sur place</b>.</p>
      </>
    ),
  },
  // ------------------------------------------------------------------ B
  {
    id: "b-assistant", groupe: "B. Préparation du chantier", titre: "Assistant de préparation",
    contenu: () => (
      <>
        <p>Dans chaque chantier, l'onglet <b>Préparation</b> pose uniquement les questions utiles :</p>
        <ul>
          <li>type de toiture, dimensions approximatives et hauteur du faîtage ;</li>
          <li>complexité (noues, lucarnes, cheminées…) ;</li>
          <li>modèle de drone (ou focale et résolution s'il n'est pas référencé) ;</li>
          <li>précision recherchée ;</li>
          <li>conditions : vent, lumière, arbres, câbles, mitoyenneté.</li>
        </ul>
        <p>Il produit un <b>plan de prise de vue</b> : hauteur de vol, lignes de vol verticales et espacements,
          orbite(s) oblique(s) avec rayon et pas angulaire, photos de détail, nombre total de photos, nombre de
          batteries et conseils adaptés (obturateur, vent, soleil, arbres…). Ce plan est consultable sur le terrain
          depuis le téléphone, même sans réseau une fois la page ouverte.</p>
        <p>Les caractéristiques des drones proposés sont indicatives : vérifiez-les sur la fiche du constructeur
          ou saisissez directement focale et résolution.</p>
        <p><Link to="/chantiers/nouveau">Créer un chantier et ouvrir l'assistant →</Link></p>
      </>
    ),
  },
  // ------------------------------------------------------------------ C
  {
    id: "c-import", groupe: "C. Import et contrôle", titre: "Importer les photos",
    contenu: () => (
      <>
        <ul>
          <li>Glissez-déposez le dossier de photos (ou sélectionnez-les depuis la tablette). Formats : JPEG, TIFF.</li>
          <li>Les doublons exacts sont ignorés automatiquement ; les fichiers illisibles sont signalés.</li>
          <li>Un fichier <code>gcp_list.txt</code> (points de contrôle) peut être joint aux photos.</li>
          <li>L'import peut se faire en plusieurs fois : l'analyse est mise à jour à chaque ajout.</li>
        </ul>
      </>
    ),
  },
  {
    id: "c-analyse", groupe: "C. Import et contrôle", titre: "Comprendre l'analyse des photos",
    contenu: () => (
      <>
        <p>Après chaque import, l'application contrôle la série et affiche les problèmes avec l'action corrective :</p>
        <div className="defile-x">
          <table className="tableau">
            <thead><tr><th>Contrôle</th><th>Ce qui est vérifié</th></tr></thead>
            <tbody>
              <tr><td>Nombre</td><td>Assez de photos pour une reconstruction.</td></tr>
              <tr><td>Netteté</td><td>Photos nettement moins nettes que le reste de la série (flou de bougé, mise au point).</td></tr>
              <tr><td>Exposition</td><td>Zones brûlées (blanc pur) ou image trop sombre.</td></tr>
              <tr><td>Doublons</td><td>Même cadrage depuis la même position (inutile, ralentit le calcul).</td></tr>
              <tr><td>Métadonnées</td><td>Présence du GPS, appareils différents, données RTK.</td></tr>
              <tr><td>Angles</td><td>Répartition verticales / obliques (si l'orientation de la nacelle est enregistrée).</td></tr>
              <tr><td>Couverture</td><td>Côtés du bâtiment (8 secteurs) sans vue oblique — exemple : « Côté nord-est sans photo oblique ».</td></tr>
              <tr><td>Recouvrement</td><td>Estimé pour les verticales successives quand altitude, focale et GPS sont connus.</td></tr>
            </tbody>
          </table>
        </div>
        <div className="alerte info" style={{ marginTop: 10 }}>Un contrôle « non évaluable » signifie que
          l'information manque pour conclure : ce n'est pas une validation. Le verdict final dépend aussi du
          résultat de la reconstruction.</div>
      </>
    ),
  },
  {
    id: "c-traitement", groupe: "C. Import et contrôle", titre: "Lancer la reconstruction 3D",
    contenu: () => (
      <>
        <p>La reconstruction utilise <b>OpenDroneMap</b>, moteur de photogrammétrie libre, sur le serveur de calcul
          configuré dans les paramètres. Trois préréglages :</p>
        <ul>
          <li><b>Aperçu rapide</b> : pour vérifier la couverture, pas pour chiffrer.</li>
          <li><b>Métré pour devis</b> : réglage recommandé.</li>
          <li><b>Haute précision</b> : toits complexes, nettement plus long.</li>
        </ul>
        <p>La durée affichée est une estimation, recalée automatiquement sur les calculs déjà réalisés sur votre
          serveur. Vous pouvez fermer la page : le traitement continue et reprend même après un redémarrage.</p>
        <p>À la fin, les pans sont <b>détectés automatiquement</b> sur le modèle de surface. Si le mauvais bâtiment a
          été choisi ou si des arbres voisins perturbent le résultat, utilisez l'outil « Détecter » et encadrez le
          bâtiment (deux coins opposés, au plus près du toit).</p>
      </>
    ),
  },
  // ------------------------------------------------------------------ D
  {
    id: "d-echelle", groupe: "D. Correction des mesures", titre: "Contrôler l'échelle",
    contenu: () => (
      <>
        <p>L'échelle conditionne toutes les longueurs (et les surfaces au carré : 2 % d'erreur d'échelle font
          ≈ 4 % sur la surface). Le bandeau d'échelle indique son origine :</p>
        <ul>
          <li><b>GPS du drone</b> : non vérifiée — ajoutez une cote de référence ;</li>
          <li><b>Cote(s) de référence</b> : vérifiée, avec l'incertitude correspondante ;</li>
          <li><b>Photo unique</b> : estimation à partir de l'altitude, à contrôler impérativement.</li>
        </ul>
        <ol>
          <li>Outil <b>Cote de référence</b>, puis touchez les deux extrémités de la cote mesurée sur place.</li>
          <li>Saisissez la longueur réelle. Le facteur d'échelle est recalculé immédiatement.</li>
          <li>Avec deux cotes ou plus, l'écart entre elles est affiché : au-delà de 1 à 2 %, vérifiez vos pointés.</li>
        </ol>
        <p>Outil <b>Mesurer</b> : mesure temporaire entre deux points (longueur réelle sur le pan), pratique pour
          comparer avec une cote relevée sur place.</p>
      </>
    ),
  },
  {
    id: "d-pan", groupe: "D. Correction des mesures", titre: "Délimiter et corriger un pan",
    contenu: () => (
      <>
        <SchemaCorrection />
        <ul>
          <li><b>Déplacer un sommet</b> : en mode Sélection, faites glisser le point. Il s'aimante aux sommets des
            pans voisins pour que les arêtes communes restent jointives.</li>
          <li><b>Ajouter un sommet</b> : outil « + Point » puis touchez une arête.</li>
          <li><b>Supprimer un sommet</b> : sélectionnez le pan, touchez le sommet puis « Supprimer le point ».</li>
          <li><b>Dessiner un pan</b> : outil « Pan », touchez chaque angle puis « Terminer ».</li>
          <li><b>Pente</b> : issue du modèle 3D (plan ajusté sur les points) ; après une modification importante du
            contour, utilisez « Réajuster sur le modèle 3D ». Vous pouvez aussi saisir une pente mesurée sur place.</li>
          <li><b>Valider</b> : cochez « Pan contrôlé » une fois le contour et la pente vérifiés.</li>
        </ul>
        <p>Raccourcis clavier : Ctrl+Z / Ctrl+Y (annuler / rétablir), Suppr (supprimer la sélection), Échap.</p>
      </>
    ),
  },
  {
    id: "d-lignes", groupe: "D. Correction des mesures", titre: "Corriger un faîtage, une noue, une rive…",
    contenu: () => (
      <>
        <p>Les lignes sont <b>déduites automatiquement</b> des contours des pans et du sens des pentes :</p>
        <ul>
          <li>arête commune, les deux pans descendent de part et d'autre : <b>faîtage</b> (horizontal) ou
            <b> arêtier</b> (incliné) ;</li>
          <li>arête commune, les deux pans descendent vers elle : <b>noue</b> ;</li>
          <li>bord libre bas et horizontal : <b>égout</b> (longueur de gouttière) ; bord libre incliné : <b>rive</b> ;</li>
          <li>une pente monte, l'autre descend : <b>ligne de bris</b> (mansarde).</li>
        </ul>
        <p>Si une ligne est mal classée (par exemple une rive qui est en réalité un <b>solin</b> contre un mur),
          touchez-la et changez son type. Si deux pans qui devraient se toucher ne forment pas de ligne commune,
          rapprochez leurs sommets : l'aimantation les rend jointifs.</p>
      </>
    ),
  },
  {
    id: "d-obstacles", groupe: "D. Correction des mesures", titre: "Cheminées et fenêtres de toit",
    contenu: () => (
      <>
        <ul>
          <li>Les volumes qui dépassent du pan sont détectés comme <b>émergences</b> : précisez leur nature
            (cheminée, ventilation…) ou supprimez-les.</li>
          <li>Outil <b>Obstacle</b> : dessinez un rectangle autour d'une fenêtre de toit visible sur l'orthophoto,
            ou saisissez ses dimensions et leur nombre.</li>
          <li>Option <b>« Déduire de la surface »</b> : à cocher selon vos habitudes de chiffrage (souvent pour les
            grandes ouvertures seulement). Le périmètre des cheminées sert au calcul des solins / abergements.</li>
        </ul>
      </>
    ),
  },
  {
    id: "d-surfaces", groupe: "D. Correction des mesures", titre: "Vérifier les surfaces",
    contenu: () => (
      <>
        <ul>
          <li>Comparez la <b>surface projetée</b> (au sol) avec l'emprise du bâtiment que vous connaissez.</li>
          <li>Contrôlez que la surface réelle ≈ surface projetée ÷ cos(pente) pour chaque pan.</li>
          <li>Les <b>contrôles de cohérence</b> signalent : contours croisés, pans qui se chevauchent, pans qui ne se
            rejoignent pas à la même hauteur, pentes atypiques, échelle non vérifiée.</li>
          <li>Le tableau « Auto / Actuel » compare la détection automatique et vos corrections : un écart important
            mérite une explication.</li>
          <li>L'historique conserve chaque version enregistrée ; vous pouvez revenir à une version antérieure.</li>
        </ul>
      </>
    ),
  },
  {
    id: "d-erreurs", groupe: "D. Correction des mesures", titre: "Comprendre les marges d'erreur",
    contenu: () => (
      <>
        <p>Chaque pan affiche un <b>niveau de confiance</b> (élevée, moyenne, faible) avec ses raisons :</p>
        <ul>
          <li>régularité du plan ajusté (écart moyen des points au plan) ;</li>
          <li>part du pan réellement observée (et non interpolée) ;</li>
          <li>état de l'échelle (vérifiée ou non) ;</li>
          <li>origine des valeurs : <b>modèle 3D</b>, <b>estimation</b> ou <b>saisie</b> manuelle.</li>
        </ul>
        <p>L'incertitude en m² est une <b>estimation simplifiée</b> (erreur de contour + pente + échelle). Elle n'est
          affichée que si les données permettent de l'évaluer ; sans échelle vérifiée, l'erreur d'échelle n'y est pas
          incluse et le message le précise.</p>
        <div className="alerte attention">L'application n'affiche jamais une précision qu'elle ne peut pas
          justifier. Une mesure marquée « à contrôler sur place » doit l'être avant commande.</div>
      </>
    ),
  },
  {
    id: "d-modes", groupe: "D. Correction des mesures", titre: "Sans modèle 3D : photo unique ou saisie",
    contenu: () => (
      <>
        <h3>Photo unique (estimation)</h3>
        <p>À partir d'une photo <b>verticale</b> prise au-dessus du toit : l'échelle est déduite de l'altitude de vol,
          de la hauteur du toit et de l'optique. Les contours se dessinent sur la photo, les pentes se saisissent.
          Précision limitée (distorsion, altitude barométrique, inclinaison) : contrôlez avec une cote.</p>
        <h3>Saisie des dimensions</h3>
        <p>Pour un relevé traditionnel : chaque pan est saisi par sa forme (rectangle, trapèze, triangle), ses
          longueurs et son rampant ; les lignes (égouts, faîtages…) se saisissent en mètres linéaires. Le calcul des
          matériaux et le rapport fonctionnent de la même manière.</p>
      </>
    ),
  },
  // ------------------------------------------------------------------ E
  {
    id: "e-validation", groupe: "E. Validation avant devis", titre: "Checklist avant devis",
    contenu: () => (
      <>
        <p>L'onglet <b>Validation</b> établit automatiquement la checklist :</p>
        <ul>
          <li>reconstruction 3D réussie (ou métré sans 3D signalé) ;</li>
          <li>échelle métrique suffisamment fiable ;</li>
          <li>tous les pans contrôlés et validés ;</li>
          <li>obstacles pris en compte (émergences confirmées + votre confirmation) ;</li>
          <li>surfaces sans erreur de cohérence ;</li>
          <li>pentes jugées plausibles par vous ;</li>
          <li>liste des mesures à contrôler sur place.</li>
        </ul>
        <p>Un point <b>bloquant</b> empêche de marquer le métré comme validé. Les points « à surveiller » restent
          visibles dans le rapport, avec vos réserves.</p>
      </>
    ),
  },
  {
    id: "e-rapport", groupe: "E. Validation avant devis", titre: "Matériaux, rapport et exports",
    contenu: () => (
      <>
        <ul>
          <li><b>Matériaux</b> : choisissez un ou plusieurs ouvrages (tuiles, ardoises, zinguerie…), affectés à tout
            ou partie des pans. Renseignez les valeurs des fiches fabricants (tuiles/m², pureau, entraxes…) et vos
            coefficients de perte : rien n'est inventé, un article incomplet est signalé « à compléter ».</li>
          <li>Les ouvrages se créent et se modifient dans <b>Paramètres → Catalogue</b> pour être réutilisés.</li>
          <li><b>Rapport PDF</b> : plan annoté, surfaces et longueurs, détail des pans, matériaux, qualité des
            données, réserves. Prix affichés ou non selon votre choix.</li>
          <li><b>Exports</b> : CSV (tableur), DXF (DAO), OBJ (3D), GeoJSON (SIG), JSON complet, et format
            « devis » prévu pour l'intégration du logiciel de devis.</li>
        </ul>
      </>
    ),
  },
];

/** Sections d'aide associées à chaque étape d'un chantier (aide contextuelle). */
export const AIDE_ETAPES: Record<string, string[]> = {
  preparation: ["b-assistant", "a-preparer", "a-hauteur", "a-angles", "a-versants", "a-controle"],
  photos: ["c-import", "c-analyse", "a-qualite", "a-versants", "a-gps"],
  traitement: ["c-traitement", "d-modes"],
  metre: ["d-pan", "d-echelle", "d-lignes", "d-obstacles", "d-surfaces", "d-erreurs"],
  materiaux: ["e-rapport"],
  validation: ["e-validation", "d-erreurs", "e-rapport"],
};
