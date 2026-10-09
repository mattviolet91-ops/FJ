export type Pt = [number, number];

export interface Plan {
  a: number;
  b: number;
  c: number;
}

export interface Pan {
  id: string;
  nom: string;
  contour?: Pt[];
  plan?: Plan;
  source_plan?: "modele_3d" | "saisie" | "estimation";
  source_contour?: "auto" | "modifie" | "manuel";
  stats?: { rms?: number; n_points?: number; couverture?: number; resolution?: number };
  valide?: boolean;
  notes?: string;
  saisie?: { forme: string; longueur_bas?: number; longueur_haut?: number; rampant?: number; pente_deg?: number; azimut_deg?: number };
}

export interface Obstacle {
  id: string;
  type: string;
  contour?: Pt[];
  largeur?: number;
  longueur?: number;
  nombre?: number;
  deduire?: boolean;
  valide?: boolean;
  source?: "auto" | "manuel";
  pan_id?: string;
  hauteur?: number;
}

export interface Reference {
  id: string;
  libelle?: string;
  p1: [number, number, number];
  p2: [number, number, number];
  reelle: number;
  mesuree?: number;
}

export interface DocumentMetre {
  version: number;
  repere: { type: string; source?: string; epsg?: number | null; origine?: number[] | null; rotation_deg?: number };
  echelle: { facteur: number; source: string; references: Reference[]; precision_pointe_m?: number };
  pans: Pan[];
  lignes_types: Record<string, string>;
  lignes_manuelles: { id: string; type: string; longueur?: number; p1?: number[]; p2?: number[]; pans?: string[] }[];
  obstacles: Obstacle[];
  auto: null | { date: string; pans: { id: string; nom: string; surface: number; pente_deg: number }[]; avertissements: string[]; emprise?: Pt[] };
}

export interface Confiance {
  niveau: "elevee" | "moyenne" | "faible" | "saisie";
  raisons: string[];
  incertitude_m2: number | null;
}

export interface PanCalcule {
  id: string;
  nom: string;
  surface: number;
  surface_plan: number;
  surface_nette: number;
  deductions: number;
  pente_deg: number;
  pente_pct: number;
  azimut: number | null;
  orientation: string;
  rampant: number;
  perimetre: number;
  source_plan: string;
  source_contour: string;
  valide: boolean;
  confiance: Confiance;
}

export interface LigneCalculee {
  cle: string;
  type: string;
  type_auto?: string;
  libelle: string;
  p1: number[];
  p2: number[];
  longueur: number;
  pans: string[];
  source: string;
  modifie?: boolean;
  manuelle?: boolean;
  ecart_hauteur?: number;
}

export interface Controle {
  niveau: "erreur" | "alerte" | "info";
  code: string;
  message: string;
  pan_id?: string;
}

export interface Calcul {
  pans: PanCalcule[];
  lignes: LigneCalculee[];
  totaux_lignes: Record<string, number>;
  obstacles: { id: string; type: string; libelle: string; surface: number; perimetre: number; pan_id?: string; deduire: boolean; valide: boolean; source: string; nombre: number }[];
  totaux: { nb_pans: number; surface_brute: number; deductions: number; surface_nette: number; surface_plan: number; pente_moyenne_deg: number; incertitude_m2: number | null };
  dimensions: { longueur: number; largeur: number; hauteur_toiture: number } | null;
  echelle: { facteur: number; source: string; incertitude_rel: number | null; message: string; references: Reference[] };
  confiance_globale: string;
  controles: Controle[];
  comparaison_auto: null | { total_auto: number; total_actuel: number; ecart: number; ecart_pct: number | null; pans: { id: string; nom: string; auto: number; actuel: number | null; ecart: number | null }[]; pans_ajoutes: string[] };
}

export interface ItemValidation {
  code: string;
  titre: string;
  statut: "ok" | "attention" | "bloquant";
  detail: string;
  confirmation?: string;
  liste?: string[];
}

export interface Validation {
  items: ItemValidation[];
  statut: "ok" | "attention" | "bloquant";
  pret_pour_devis: boolean;
}

export interface MetreComplet {
  document: DocumentMetre;
  calcul: Calcul;
  validation: Validation;
  version: { numero: number; date: string; commentaire: string } | null;
  types_lignes: Record<string, string>;
  types_obstacles: Record<string, string>;
  confirmations_libelles: Record<string, string>;
}

export interface Chantier {
  id: number;
  reference: string;
  nom: string;
  client_nom: string;
  client_tel: string;
  client_email: string;
  adresse: string;
  lat: number | null;
  lon: number | null;
  type_toiture: string;
  type_toiture_libelle: string;
  statut: string;
  statut_libelle: string;
  mode: "3d" | "photo" | "saisie";
  archive: boolean;
  parent_id: number | null;
  cree_le: string;
  modifie_le: string;
  notes?: string;
  preparation?: Record<string, unknown> | null;
  plan_vol?: PlanVol | null;
  analyse_photos?: AnalysePhotos | null;
  modele?: Modele | null;
  confirmations?: Record<string, boolean>;
  reserves?: string;
  checklists?: Record<string, Record<string, boolean>>;
  nb_photos?: number;
  dernier_traitement?: Traitement | null;
  resume_metre?: { surface: number; nb_pans: number; valides: number } | null;
}

export interface Modele {
  type: "odm" | "photo";
  bornes: [number, number, number, number];
  epsg?: number;
  origine?: number[];
  res_mns?: number;
  res_ortho?: number;
  nb_points?: number;
  ortho?: boolean;
  rapport_odm?: boolean;
  gsd_m?: number;
  photo_id?: number;
  rotation_deg?: number;
  avertissements?: string[];
}

export interface Probleme {
  niveau: "bloquant" | "alerte" | "info";
  code: string;
  message: string;
  action: string;
  photos?: number[];
}

export interface AnalysePhotos {
  stats: Record<string, unknown> & {
    nombre: number;
    avec_gps?: number;
    angles?: Record<string, number>;
    couverture_secteurs?: Record<string, number> | null;
    gsd_sol_cm?: { min: number; max: number; median: number };
  };
  problemes: Probleme[];
  verdict: "correct" | "a_ameliorer" | "insuffisant";
  date?: string;
}

export interface Photo {
  id: number;
  nom: string;
  taille: number;
  exclue: boolean;
  type: string;
  largeur?: number;
  hauteur?: number;
  modele?: string;
  lat?: number;
  lon?: number;
  alt_relative?: number;
  nacelle_tangage?: number;
  categorie: string;
  problemes: string[];
  nettete?: number;
}

export interface Traitement {
  id: number;
  chantier_id: number;
  type: string;
  statut: string;
  statut_libelle: string;
  etape: string;
  progression: number;
  message: string;
  erreur: string;
  nb_images: number;
  options: Record<string, unknown> | null;
  duree_estimee_s: number | null;
  resultats: Record<string, unknown> | null;
  cree_le: string;
  debut: string | null;
  fin: string | null;
  chantier?: { id: number; nom: string; reference: string };
}

export interface PlanVol {
  camera: { nom: string; connue: boolean; focale_35mm?: number; obturateur?: string };
  precision: { libelle: string; gsd_cm: number };
  hauteur_vol_sol_m: number | null;
  hauteur_au_dessus_toit_m: number | null;
  gsd_toit_cm: number | null;
  passages_verticaux: null | { lignes: number; photos_par_ligne: number; total: number; espacement_lignes_m: number; espacement_photos_m: number };
  orbites: { nom: string; hauteur_sol_m: number; rayon_m: number; inclinaison_nacelle_deg: number; nb_photos: number; pas_deg: number }[];
  photos_detail: number;
  total_photos: number;
  batteries_estimees: number | null;
  etapes: { titre: string; points: string[] }[];
  conseils: string[];
  alertes: string[];
  avertissement: string;
}

export interface Article {
  nom: string;
  base: string;
  unite: string;
  consommation: number | string | null;
  categorie?: string;
  perte_pct: number | string | null;
  reference?: string | null;
  fabricant?: string | null;
  prix_unitaire?: number | null;
  conditionnement?: number | string | null;
  libelle_conditionnement?: string | null;
  actif?: boolean;
}

export interface Ouvrage {
  id?: number;
  code?: string;
  nom: string;
  description?: string;
  parametres: { cle: string; libelle: string; unite: string; valeur: number | null; aide?: string }[];
  articles: Article[];
}
