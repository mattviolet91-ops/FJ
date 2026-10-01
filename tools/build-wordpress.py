#!/usr/bin/env python3
"""Génère le thème WordPress (wordpress/fj-renovtoit) à partir du site statique.

Usage, depuis la racine du dépôt :
    python3 tools/build-wordpress.py

- copie assets/ dans le thème
- découpe index.html en header.php / front-page.php / footer.php
- remplace téléphone, e-mail et adresse par les réglages du Personnaliseur
- recrée fj-renovtoit-theme.zip
"""
import pathlib
import re
import shutil
import zipfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
THEME = RACINE / "wordpress" / "fj-renovtoit"

TEL = "06 67 04 74 57"
TEL_HREF = "tel:+33667047457"
EMAIL = "fj.couverture@gmail.com"
ADRESSE = "4 rue de Charaïntru, 91360 Épinay-sur-Orge"
ADRESSE_BR = "4 rue de Charaïntru<br>91360 Épinay-sur-Orge"
MAPS = "https://www.google.com/maps/search/?api=1&amp;query=4+rue+de+Chara%C3%AFntru+91360+%C3%89pinay-sur-Orge"

URI = "<?php echo esc_url( get_template_directory_uri() ); ?>/assets/"
ACCUEIL = "<?php echo esc_url( home_url( '/' ) ); ?>"


def remplacer(texte, avant, apres):
    if avant not in texte:
        raise SystemExit(f"Introuvable dans index.html : {avant[:60]!r}")
    return texte.replace(avant, apres)


def coordonnees(texte):
    texte = texte.replace(MAPS, "<?php echo esc_url( fj_maps_url() ); ?>")
    texte = texte.replace(TEL_HREF, "<?php echo esc_attr( fj_tel_href() ); ?>")
    texte = texte.replace(TEL, "<?php echo esc_html( fj_option( 'fj_telephone' ) ); ?>")
    texte = texte.replace("mailto:" + EMAIL, "mailto:<?php echo esc_attr( fj_option( 'fj_email' ) ); ?>")
    texte = texte.replace(EMAIL, "<?php echo esc_html( fj_option( 'fj_email' ) ); ?>")
    texte = texte.replace(ADRESSE_BR, "<?php echo esc_html( fj_option( 'fj_adresse' ) ); ?>")
    texte = texte.replace(ADRESSE, "<?php echo esc_html( fj_option( 'fj_adresse' ) ); ?>")
    return texte.replace('src="assets/', 'src="' + URI)


def main():
    html = (RACINE / "index.html").read_text(encoding="utf-8")

    debut_body = html.index("<body>") + len("<body>")
    debut_main = html.index("  <main>")
    fin_main = html.index("  </main>") + len("  </main>")
    fin_body = html.index("  <script src=\"assets/js/main.js\"></script>")

    # En-tête
    entete = html[debut_body:debut_main]
    entete = re.sub(r'href="#(accueil|prestations|entreprise|zone|contact)"', 'href="' + ACCUEIL + r'#\1"', entete)
    header_php = (
        "<!DOCTYPE html>\n<html <?php language_attributes(); ?>>\n<head>\n"
        "  <meta charset=\"<?php bloginfo( 'charset' ); ?>\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "  <link rel=\"icon\" href=\"" + URI + "img/logo.svg\" type=\"image/svg+xml\">\n"
        "  <?php wp_head(); ?>\n</head>\n<body <?php body_class(); ?>>\n<?php wp_body_open(); ?>"
        + coordonnees(entete)
    )

    # Page d'accueil
    principal = html[debut_main:fin_main]
    principal = remplacer(
        principal,
        '<form id="form-devis" data-mode="mailto" data-email="' + EMAIL + '">',
        """<form id="form-devis" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <?php if ( isset( $_GET['devis'] ) && 'ok' === $_GET['devis'] ) : ?>
            <p class="form-message">Merci, votre demande a bien été envoyée. Nous vous recontactons rapidement.</p>
          <?php elseif ( isset( $_GET['devis'] ) ) : ?>
            <p class="form-message form-erreur">Une erreur est survenue. Merci de nous appeler directement.</p>
          <?php endif; ?>
          <input type="hidden" name="action" value="fj_devis">
          <?php wp_nonce_field( 'fj_devis', 'fj_devis_nonce' ); ?>
          <div class="screen-reader-text" aria-hidden="true"><label for="site_web">Ne pas remplir</label><input id="site_web" name="site_web" tabindex="-1" autocomplete="off"></div>""",
    )
    front_php = "<?php get_header(); ?>\n\n" + coordonnees(principal) + "\n\n<?php get_footer(); ?>\n"

    # Pied de page
    pied = html[fin_main:fin_body]
    pied = re.sub(r'href="#(accueil|prestations|entreprise|zone|contact)"', 'href="' + ACCUEIL + r'#\1"', pied)
    pied = remplacer(pied, '<span id="annee"></span>', "<?php echo esc_html( gmdate( 'Y' ) ); ?>")
    footer_php = coordonnees(pied).lstrip("\n") + "\n<?php wp_footer(); ?>\n</body>\n</html>\n"

    for nom, contenu in (("header.php", header_php), ("front-page.php", front_php), ("footer.php", footer_php)):
        if any(v in contenu for v in (TEL, EMAIL, "91360")):
            raise SystemExit(f"Coordonnée restée en dur dans {nom}")
        (THEME / nom).write_text(contenu, encoding="utf-8")

    # Ressources
    shutil.rmtree(THEME / "assets", ignore_errors=True)
    shutil.copytree(RACINE / "assets", THEME / "assets")
    (THEME / "assets" / "img" / "carte-fj-renovtoit.jpg").unlink(missing_ok=True)

    # Archive à téléverser dans WordPress
    archive = RACINE / "fj-renovtoit-theme.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(THEME.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(THEME.parent))
    print("Thème généré :", archive.name)


if __name__ == "__main__":
    main()
