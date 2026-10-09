"""Rapport PDF professionnel (ReportLab) : synthèse, plan annoté, détail des pans, lignes,
matériaux, qualité des données et réserves."""
from __future__ import annotations

import io
import math
import tempfile
from datetime import datetime
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Group, Image as DImage, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from ..core import geometry as geo

BLEU = colors.HexColor("#2BABE2")
GRIS = colors.HexColor("#2F3438")
GRIS_CLAIR = colors.HexColor("#EEF2F4")

COULEURS_LIGNES = {
    "faitage": "#D7263D", "aretier": "#F49D37", "noue": "#1B998B", "egout": "#2E86DE", "rive": "#8E44AD",
    "rive_haute": "#6C5CE7", "bris": "#A0522D", "solin": "#7F8C8D", "autre": "#555555",
}

_POLICE, _GRAS = "Helvetica", "Helvetica-Bold"
for chemin, nom in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu"),
                    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVu-Bold")):
    try:
        if Path(chemin).exists():
            pdfmetrics.registerFont(TTFont(nom, chemin))
    except Exception:
        pass
if "DejaVu" in pdfmetrics.getRegisteredFontNames() and "DejaVu-Bold" in pdfmetrics.getRegisteredFontNames():
    _POLICE, _GRAS = "DejaVu", "DejaVu-Bold"


def _n(v, d=2, unite=""):
    if v is None:
        return "—"
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return f"{s} {unite}".strip()


def _styles():
    base = ParagraphStyle("b", fontName=_POLICE, fontSize=9, leading=12, textColor=GRIS, alignment=TA_LEFT)
    return {
        "b": base,
        "petit": ParagraphStyle("p", parent=base, fontSize=7.5, leading=9.5),
        "h1": ParagraphStyle("h1", parent=base, fontName=_GRAS, fontSize=17, leading=21, textColor=GRIS),
        "h2": ParagraphStyle("h2", parent=base, fontName=_GRAS, fontSize=12, leading=16, textColor=BLEU,
                             spaceBefore=10, spaceAfter=4),
        "cell": ParagraphStyle("c", parent=base, fontSize=8, leading=10),
        "cellb": ParagraphStyle("cb", parent=base, fontSize=8, leading=10, fontName=_GRAS),
    }


def _table(data, largeurs, entete=True, zebra=True):
    t = Table(data, colWidths=largeurs, repeatRows=1 if entete else 0)
    st = [("FONT", (0, 0), (-1, -1), _POLICE, 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DCE0")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if entete:
        st += [("BACKGROUND", (0, 0), (-1, 0), GRIS), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("FONT", (0, 0), (-1, 0), _GRAS, 8)]
    if zebra:
        for i in range(1 if entete else 0, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), GRIS_CLAIR))
    t.setStyle(TableStyle(st))
    return t


def plan_annote(document: dict, calcul: dict, largeur: float, hauteur: float, fond: tuple | None = None) -> Drawing:
    """Plan vectoriel des pans, lignes et obstacles, avec flèche du nord et échelle graphique."""
    d = Drawing(largeur, hauteur)
    pans = [p for p in document.get("pans", []) if p.get("contour") and len(p["contour"]) >= 3]
    k = calcul["echelle"]["facteur"] or 1.0
    if not pans:
        d.add(String(largeur / 2, hauteur / 2, "Aucun pan dessiné (saisie par dimensions)", fontName=_POLICE,
                     fontSize=9, textAnchor="middle", fillColor=GRIS))
        return d
    pts = [pt for p in pans for pt in p["contour"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    marge = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1)
    x0, x1, y0, y1 = min(xs) - marge, max(xs) + marge, min(ys) - marge, max(ys) + marge
    e = min((largeur - 20) / (x1 - x0), (hauteur - 30) / (y1 - y0))
    ox = (largeur - (x1 - x0) * e) / 2
    oy = 20 + (hauteur - 30 - (y1 - y0) * e) / 2

    def T(x, y):
        return ox + (x - x0) * e, oy + (y - y0) * e

    d.add(Rect(0, 0, largeur, hauteur, fillColor=colors.white, strokeColor=colors.HexColor("#D5DCE0")))
    if fond:
        chemin, (bx0, by0, bx1, by1) = fond
        ax, ay = T(bx0, by0)
        bx, by = T(bx1, by1)
        # recadrer à la zone de dessin
        g = Group()
        g.add(DImage(ax, ay, bx - ax, by - ay, chemin))
        d.add(g)
    infos = {p["id"]: p for p in calcul["pans"]}
    for i, p in enumerate(pans):
        poly = []
        for x, y in p["contour"]:
            poly += list(T(x, y))
        teinte = colors.Color(0.17, 0.67, 0.89, alpha=0.22 if not fond else 0.35)
        d.add(Polygon(poly, fillColor=teinte, strokeColor=colors.HexColor("#1D7FA8"), strokeWidth=0.6))
    for o in document.get("obstacles", []):
        if o.get("contour") and len(o["contour"]) >= 3:
            poly = []
            for x, y in o["contour"]:
                poly += list(T(x, y))
            d.add(Polygon(poly, fillColor=colors.Color(0.2, 0.2, 0.2, alpha=0.55), strokeColor=colors.black,
                          strokeWidth=0.5))
    for lg in calcul["lignes"]:
        if lg.get("manuelle"):
            continue
        a = T(lg["p1"][0], lg["p1"][1])
        b = T(lg["p2"][0], lg["p2"][1])
        d.add(Line(a[0], a[1], b[0], b[1], strokeColor=colors.HexColor(COULEURS_LIGNES.get(lg["type"], "#555")),
                   strokeWidth=1.8))
    for p in pans:
        c = geo.centroide([tuple(v) for v in p["contour"]])
        cx, cy = T(*c)
        inf = infos.get(p["id"])
        if not inf:
            continue
        etiquette = f"{p.get('nom', '').split(' (')[0]}"
        for j, (txt, taille, police) in enumerate(((etiquette, 7.5, _GRAS),
                                                    (f"{_n(inf['surface'], 1)} m²", 7, _POLICE),
                                                    (f"{inf['pente_deg']:.0f}°", 6.5, _POLICE))):
            d.add(String(cx, cy + 4 - j * 8, txt, fontName=police, fontSize=taille, textAnchor="middle",
                         fillColor=GRIS, strokeColor=colors.white, strokeWidth=0))
    # nord (le repère local est orienté nord en haut, sauf rotation de photo)
    rot = math.radians(float((document.get("repere") or {}).get("rotation_deg") or 0))
    nx, ny = largeur - 22, hauteur - 26
    dx, dy = -math.sin(rot) * 14, math.cos(rot) * 14
    d.add(Line(nx - dx / 2, ny - dy / 2, nx + dx / 2, ny + dy / 2, strokeColor=GRIS, strokeWidth=1.5))
    d.add(String(nx + dx / 2 * 1.3, ny + dy / 2 * 1.3 + 2, "N", fontName=_GRAS, fontSize=8, textAnchor="middle",
                 fillColor=GRIS))
    # échelle graphique
    longueur_m = 10 ** math.floor(math.log10(max((x1 - x0) * k / 4, 0.1)))
    for m_ in (5, 2):
        if longueur_m * m_ * e / k < largeur / 3:
            longueur_m *= m_
            break
    L = longueur_m * e / k
    d.add(Rect(12, 8, L, 3, fillColor=GRIS, strokeColor=GRIS))
    d.add(String(12 + L + 4, 7, f"{_n(longueur_m, 0 if longueur_m >= 1 else 1)} m", fontName=_POLICE, fontSize=7,
                 fillColor=GRIS))
    return d


def _legende():
    d = Drawing(170 * mm, 12)
    x = 0
    for t, c in COULEURS_LIGNES.items():
        if t in ("autre",):
            continue
        d.add(Line(x, 5, x + 14, 5, strokeColor=colors.HexColor(c), strokeWidth=2))
        lib = geo.TYPES_LIGNES[t].split(" /")[0]
        d.add(String(x + 17, 2.5, lib, fontName=_POLICE, fontSize=6.5, fillColor=GRIS))
        x += 20 + pdfmetrics.stringWidth(lib, _POLICE, 6.5) + 6
    return d


def generer(ch: dict, entreprise: dict, document: dict, calcul: dict, validation: dict | None,
            materiaux: dict | None, analyse_photos: dict | None, options: dict, fond_ortho=None,
            logo: Path | None = None) -> bytes:
    S = _styles()
    buf = io.BytesIO()
    nom_ent = entreprise.get("nom") or "Matt's Couverture"

    def deco(c, doc):
        c.saveState()
        c.setFillColor(BLEU)
        c.rect(0, A4[1] - 9 * mm, A4[0], 9 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(_GRAS, 9)
        c.drawString(15 * mm, A4[1] - 6 * mm, f"{nom_ent} — Métré de toiture")
        c.drawRightString(A4[0] - 15 * mm, A4[1] - 6 * mm, f"{ch.get('reference', '')}")
        c.setFillColor(GRIS)
        c.setFont(_POLICE, 7)
        pied = " · ".join(x for x in (entreprise.get("adresse"), entreprise.get("telephone"),
                                       entreprise.get("email"), entreprise.get("siret") and
                                       f"SIRET {entreprise.get('siret')}") if x)
        c.drawString(15 * mm, 8 * mm, pied[:150])
        c.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm,
                            bottomMargin=15 * mm, title=f"Métré {ch.get('reference')}", author=nom_ent)
    el = []
    entete = []
    if logo and Path(logo).exists():
        from reportlab.platypus import Image as PImage
        try:
            entete.append(PImage(str(logo), width=30 * mm, height=18 * mm, kind="proportional"))
        except Exception:
            pass
    el.append(Paragraph("Rapport de métré de toiture", S["h1"]))
    el.append(Spacer(1, 3))
    infos = [
        ["Chantier", ch.get("nom", ""), "Référence", ch.get("reference", "")],
        ["Client", ch.get("client_nom", "") or "—", "Date", datetime.now().strftime("%d/%m/%Y")],
        ["Adresse", ch.get("adresse", "") or "—", "Type de toiture", ch.get("type_toiture_libelle", "") or "—"],
    ]
    t = Table([[Paragraph(str(c), S["cellb"] if i % 2 == 0 else S["cell"]) for i, c in enumerate(r)] for r in infos],
              colWidths=[22 * mm, 68 * mm, 28 * mm, 62 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    if entete:
        el.append(Table([[t, entete[0]]], colWidths=[150 * mm, 30 * mm]))
    else:
        el.append(t)
    el.append(Spacer(1, 6))

    tot = calcul["totaux"]
    tl = calcul["totaux_lignes"]
    inc = tot.get("incertitude_m2")
    synth = [
        ["Surface de couverture nette", f"{_n(tot['surface_nette'])} m²" + (f"  (± {_n(inc, 1)} m²)" if inc else "")],
        ["Surface brute / déductions", f"{_n(tot['surface_brute'])} m² / {_n(tot['deductions'])} m²"],
        ["Surface projetée au sol", f"{_n(tot['surface_plan'])} m²"],
        ["Nombre de pans / pente moyenne", f"{tot['nb_pans']} / {_n(tot['pente_moyenne_deg'], 0)}°"],
        ["Faîtages", f"{_n(tl.get('faitage'))} ml"], ["Arêtiers", f"{_n(tl.get('aretier'))} ml"],
        ["Noues", f"{_n(tl.get('noue'))} ml"], ["Égouts (gouttières)", f"{_n(tl.get('egout'))} ml"],
        ["Rives", f"{_n((tl.get('rive') or 0) + (tl.get('rive_haute') or 0))} ml"],
    ]
    if (tl.get("solin") or 0) > 0:
        synth.append(["Solins / raccords", f"{_n(tl.get('solin'))} ml"])
    niv = {"elevee": "Élevée", "moyenne": "Moyenne", "faible": "Faible", "saisie": "Valeurs saisies"}
    synth.append(["Niveau de confiance global", niv.get(calcul["confiance_globale"], calcul["confiance_globale"])])
    st = _table([[Paragraph(a, S["cellb"]), Paragraph(b, S["cell"])] for a, b in synth], [70 * mm, 110 * mm],
                entete=False)
    el.append(Paragraph("Synthèse", S["h2"]))
    el.append(st)
    el.append(Paragraph(calcul["echelle"]["message"], S["petit"]))

    el.append(Paragraph("Plan annoté", S["h2"]))
    el.append(plan_annote(document, calcul, 180 * mm, 120 * mm, fond_ortho))
    el.append(_legende())

    # --- pans
    entetes = ["Pan", "Orient.", "Pente", "Projetée", "Réelle", "Déduc-tions", "Nette", "Rampant", "Source",
               "Confiance", "Validé"]
    st_ent = ParagraphStyle("ent", parent=S["cell"], textColor=colors.white, fontName=_GRAS, fontSize=7, leading=8.5)
    lignes = [[Paragraph(e.replace("-", ""), st_ent) for e in entetes]]
    src = {"modele_3d": "Modèle 3D", "saisie": "Saisie", "estimation": "Estimation"}
    for p in calcul["pans"]:
        lignes.append([Paragraph(p["nom"] or p["id"], S["cell"]), p["orientation"],
                       f"{p['pente_deg']:.0f}° / {p['pente_pct']:.0f} %", _n(p["surface_plan"]), _n(p["surface"]),
                       _n(p["deductions"]), _n(p["surface_nette"]), _n(p["rampant"]),
                       src.get(p["source_plan"], p["source_plan"]), niv.get(p["confiance"]["niveau"], "—"),
                       "Oui" if p["valide"] else "Non"])
    lignes.append(["Total", "", "", _n(tot["surface_plan"]), _n(tot["surface_brute"]), _n(tot["deductions"]),
                   _n(tot["surface_nette"]), "", "", "", ""])
    el.append(PageBreak())
    el.append(Paragraph("Détail des pans (surfaces en m², longueurs en m)", S["h2"]))
    el.append(_table(lignes, [29 * mm, 12 * mm, 20 * mm, 15 * mm, 15 * mm, 14 * mm, 15 * mm, 15 * mm, 17 * mm,
                              16 * mm, 12 * mm]))

    # --- lignes
    el.append(Paragraph("Longueurs par type de ligne", S["h2"]))
    lt = [["Type", "Longueur totale (ml)", "Nombre de segments"]]
    for typ, lib in geo.TYPES_LIGNES.items():
        segs = [l for l in calcul["lignes"] if l["type"] == typ]
        if segs:
            lt.append([lib, _n(sum(s["longueur"] for s in segs)), str(len(segs))])
    el.append(_table(lt, [70 * mm, 50 * mm, 40 * mm]))

    if calcul["obstacles"]:
        el.append(Paragraph("Ouvertures et obstacles", S["h2"]))
        ot = [["Élément", "Nombre", "Surface (m²)", "Périmètre (ml)", "Déduit", "Confirmé"]]
        for o in calcul["obstacles"]:
            ot.append([o["libelle"], str(o["nombre"]), _n(o["surface"]), _n(o["perimetre"]),
                       "Oui" if o["deduire"] else "Non", "Oui" if (o["valide"] or o["source"] == "saisie") else "Non"])
        el.append(_table(ot, [55 * mm, 18 * mm, 28 * mm, 30 * mm, 20 * mm, 20 * mm]))

    # --- matériaux
    if materiaux and options.get("materiaux", True) and materiaux.get("lignes"):
        el.append(Paragraph("Matériaux estimés", S["h2"]))
        prix = options.get("prix", False)
        mt = [["Ouvrage / article", "Base", "Quantité", "Unité"] + (["Montant HT"] if prix else [])]
        for l in materiaux["lignes"]:
            if l["statut"] in ("ok", "zero"):
                q = l.get("quantite_commandee", l["quantite_totale"])
                qtxt = _n(q, 2 if l["unite"] in ("m²", "ml", "L", "kg") else 0)
                if l.get("conditionnements"):
                    qtxt += f" ({l['conditionnements']} {l['libelle_conditionnement']})"
            else:
                qtxt = f"à compléter : {l.get('manque')}"
            row = [Paragraph(f"{l['ouvrage']} — {l['article']}" + (f" <i>({l['reference']})</i>" if l.get('reference') else ""),
                             S["cell"]), Paragraph(l["base_libelle"] or "", S["cell"]), Paragraph(qtxt, S["cell"]),
                   l["unite"]]
            if prix:
                row.append(_n(l.get("montant_ht"), 2, "€") if l.get("montant_ht") is not None else "—")
            mt.append(row)
        if prix:
            mt.append(["Total HT (articles chiffrés)", "", "", "", _n(materiaux["total_ht"], 2, "€")])
        el.append(_table(mt, [75 * mm, 50 * mm, 35 * mm, 15 * mm] + ([25 * mm] if prix else [])
                         if not prix else [65 * mm, 45 * mm, 35 * mm, 12 * mm, 23 * mm]))
        el.append(Paragraph("Quantités calculées à partir des paramètres saisis (fiches fabricants) et des coefficients "
                            "de perte choisis ; à confirmer avant commande.", S["petit"]))

    # --- qualité des données
    el.append(Paragraph("Qualité des données et contrôles", S["h2"]))
    q = []
    mode = {"3d": "Reconstruction 3D photogrammétrique", "photo": "Mesure sur photo unique (estimation)",
            "saisie": "Saisie manuelle des dimensions"}.get(ch.get("mode"), ch.get("mode"))
    q.append(["Méthode", mode])
    if ch.get("nb_photos") is not None:
        q.append(["Photos exploitées", str(ch.get("nb_photos"))])
    if analyse_photos:
        v = {"correct": "Correcte", "a_ameliorer": "À améliorer", "insuffisant": "Insuffisante"}
        q.append(["Analyse de la série de photos", v.get(analyse_photos.get("verdict"), "—")])
    q.append(["Échelle", calcul["echelle"]["message"]])
    if ch.get("res_mns"):
        q.append(["Résolution du modèle de surface", f"{_n(ch['res_mns'] * 100, 1)} cm"])
    el.append(_table([[Paragraph(a, S["cellb"]), Paragraph(b, S["cell"])] for a, b in q], [55 * mm, 125 * mm],
                     entete=False))
    if validation:
        el.append(Spacer(1, 4))
        sv = {"ok": "Conforme", "attention": "À surveiller", "bloquant": "Bloquant"}
        vt = [["Contrôle avant devis", "Statut", "Détail"]]
        for it in validation["items"]:
            vt.append([Paragraph(it["titre"], S["cell"]), sv[it["statut"]], Paragraph(it["detail"], S["cell"])])
        el.append(_table(vt, [50 * mm, 25 * mm, 105 * mm]))
    alertes = [c for c in calcul["controles"] if c["niveau"] in ("erreur", "alerte")]
    if alertes:
        el.append(Spacer(1, 4))
        el.append(Paragraph("Points d'attention", S["cellb"]))
        for c in alertes:
            el.append(Paragraph("• " + c["message"], S["cell"]))
    if ch.get("reserves"):
        el.append(Paragraph("Réserves", S["h2"]))
        for ligne in str(ch["reserves"]).splitlines():
            if ligne.strip():
                el.append(Paragraph(ligne, S["b"]))
    el.append(Spacer(1, 8))
    el.append(KeepTogether([Paragraph(
        "Ce document est une aide au chiffrage établie à partir de prises de vue par drone et/ou de saisies. "
        "Les valeurs indiquées dépendent de la qualité des photos et de l'échelle utilisée ; les mesures signalées "
        "comme à contrôler doivent être vérifiées sur place avant toute commande ou exécution.", S["petit"])]))
    doc.build(el, onFirstPage=deco, onLaterPages=deco)
    return buf.getvalue()


def fond_temporaire(image_bytes: bytes, bornes) -> tuple[str, tuple]:
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    f.write(image_bytes)
    f.close()
    return f.name, tuple(bornes)
