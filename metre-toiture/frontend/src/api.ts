// Accès à l'API : cookie de session HttpOnly + en-tête anti-CSRF sur les requêtes modifiantes.

export class ErreurApi extends Error {
  constructor(message: string, public statut: number) {
    super(message);
  }
}

let surDeconnexion: (() => void) | null = null;
export function quandDeconnecte(f: () => void) {
  surDeconnexion = f;
}

async function requete<T>(methode: string, url: string, corps?: unknown, brut = false): Promise<T> {
  const init: RequestInit = { method: methode, credentials: "same-origin", headers: { "X-Requested-With": "mmt" } };
  if (corps instanceof FormData) {
    init.body = corps;
  } else if (corps !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(corps);
  }
  let rep: Response;
  try {
    rep = await fetch(url, init);
  } catch {
    throw new ErreurApi("Serveur injoignable : vérifiez la connexion réseau.", 0);
  }
  if (rep.status === 401 && !url.includes("/auth/")) {
    surDeconnexion?.();
  }
  if (!rep.ok) {
    let msg = `Erreur ${rep.status}`;
    try {
      const d = await rep.json();
      if (typeof d.detail === "string") msg = d.detail;
      else if (Array.isArray(d.detail)) msg = d.detail.map((x: { msg: string }) => x.msg).join(" ; ");
    } catch {
      /* réponse non JSON */
    }
    throw new ErreurApi(msg, rep.status);
  }
  if (brut) return rep as unknown as T;
  const type = rep.headers.get("content-type") || "";
  return (type.includes("json") ? rep.json() : rep.text()) as Promise<T>;
}

export const api = {
  get: <T,>(url: string) => requete<T>("GET", url),
  post: <T,>(url: string, corps?: unknown) => requete<T>("POST", url, corps ?? {}),
  put: <T,>(url: string, corps?: unknown) => requete<T>("PUT", url, corps ?? {}),
  patch: <T,>(url: string, corps?: unknown) => requete<T>("PATCH", url, corps ?? {}),
  del: <T,>(url: string) => requete<T>("DELETE", url),
  brut: (url: string) => requete<Response>("GET", url, undefined, true),
};

/** Envoi de fichiers avec suivi de progression (XMLHttpRequest). */
export function envoyerFichiers<T>(url: string, fichiers: File[], progression: (f: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    fichiers.forEach((f) => fd.append("fichiers", f, f.name));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("X-Requested-With", "mmt");
    xhr.upload.onprogress = (e) => e.lengthComputable && progression(e.loaded / e.total);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
      else {
        let m = `Erreur ${xhr.status}`;
        try {
          m = JSON.parse(xhr.responseText).detail || m;
        } catch {
          /* */
        }
        reject(new ErreurApi(m, xhr.status));
      }
    };
    xhr.onerror = () => reject(new ErreurApi("Envoi interrompu (réseau).", 0));
    xhr.send(fd);
  });
}

export const fr = (v: number | null | undefined, d = 2) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });

export const duree = (s: number | null | undefined) => {
  if (!s && s !== 0) return "—";
  if (s < 90) return `${Math.round(s)} s`;
  const m = Math.round(s / 60);
  if (m < 90) return `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}`;
};

export const dateFr = (iso?: string | null) => (iso ? new Date(iso + (iso.endsWith("Z") ? "" : "Z")).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "—");
