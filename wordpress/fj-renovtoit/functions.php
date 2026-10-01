<?php
/**
 * Thème F.J Renovtoit.
 *
 * header.php, front-page.php et footer.php sont générés depuis index.html
 * par tools/build-wordpress.py : modifier index.html puis relancer le script.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function fj_setup() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'post-thumbnails' );
}
add_action( 'after_setup_theme', 'fj_setup' );

function fj_assets() {
	$version = wp_get_theme()->get( 'Version' );
	wp_enqueue_style( 'fj-polices', 'https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700;800&family=Kaushan+Script&display=swap', array(), null );
	wp_enqueue_style( 'fj-main', get_template_directory_uri() . '/assets/css/style.css', array( 'fj-polices' ), $version );
	wp_enqueue_style( 'fj-style', get_stylesheet_uri(), array( 'fj-main' ), $version );
	wp_enqueue_script( 'fj-main', get_template_directory_uri() . '/assets/js/main.js', array(), $version, true );
}
add_action( 'wp_enqueue_scripts', 'fj_assets' );

/**
 * Coordonnées modifiables dans Apparence > Personnaliser > Coordonnées F.J Renovtoit.
 */
function fj_defaults() {
	return array(
		'fj_telephone' => '06 67 04 74 57',
		'fj_email'     => 'fj.couverture@gmail.com',
		'fj_adresse'   => '4 rue de Charaintru, 91600 Savigny-sur-Orge',
	);
}

function fj_option( $key ) {
	$defaults = fj_defaults();
	return get_theme_mod( $key, $defaults[ $key ] );
}

function fj_customize_register( $wp_customize ) {
	$wp_customize->add_section( 'fj_coordonnees', array(
		'title'    => __( 'Coordonnées F.J Renovtoit', 'fj-renovtoit' ),
		'priority' => 30,
	) );

	$champs = array(
		'fj_telephone' => array( __( 'Téléphone', 'fj-renovtoit' ), 'sanitize_text_field' ),
		'fj_email'     => array( __( 'E-mail (reçoit les demandes de devis)', 'fj-renovtoit' ), 'sanitize_email' ),
		'fj_adresse'   => array( __( 'Adresse', 'fj-renovtoit' ), 'sanitize_text_field' ),
	);
	$defaults = fj_defaults();

	foreach ( $champs as $id => $champ ) {
		$wp_customize->add_setting( $id, array(
			'default'           => $defaults[ $id ],
			'sanitize_callback' => $champ[1],
		) );
		$wp_customize->add_control( $id, array(
			'label'   => $champ[0],
			'section' => 'fj_coordonnees',
			'type'    => 'text',
		) );
	}
}
add_action( 'customize_register', 'fj_customize_register' );

/**
 * Numéro au format international pour les liens tel:.
 */
function fj_tel_international() {
	$numero = preg_replace( '/[^0-9+]/', '', fj_option( 'fj_telephone' ) );
	if ( 0 === strpos( $numero, '0' ) ) {
		$numero = '+33' . substr( $numero, 1 );
	}
	return $numero;
}

function fj_tel_href() {
	return 'tel:' . fj_tel_international();
}

function fj_maps_url() {
	return 'https://www.google.com/maps/search/?api=1&query=' . rawurlencode( fj_option( 'fj_adresse' ) );
}

/**
 * Meta description et données structurées (référencement local).
 */
function fj_seo_head() {
	if ( ! is_front_page() ) {
		return;
	}
	$description = 'F.J Renovtoit, couvreur à Savigny-sur-Orge : couverture, zinguerie, rénovation de toiture, ravalement de façade, réparation de fuites, démoussage. Devis gratuit au ' . fj_option( 'fj_telephone' ) . '.';
	echo '<meta name="description" content="' . esc_attr( $description ) . '">' . "\n";
	echo '<meta name="theme-color" content="#0b0d10">' . "\n";

	$donnees = array(
		'@context'   => 'https://schema.org',
		'@type'      => 'RoofingContractor',
		'name'       => 'F.J Renovtoit',
		'url'        => home_url( '/' ),
		'telephone'  => fj_tel_international(),
		'email'      => fj_option( 'fj_email' ),
		'address'    => fj_option( 'fj_adresse' ),
		'areaServed' => 'Savigny-sur-Orge et Essonne (91)',
	);
	echo '<script type="application/ld+json">' . wp_json_encode( $donnees, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . '</script>' . "\n";
}
add_action( 'wp_head', 'fj_seo_head', 1 );

function fj_titre( $titre ) {
	if ( is_front_page() ) {
		$titre['title'] = 'F.J Renovtoit – Couvreur à Savigny-sur-Orge (91)';
		unset( $titre['tagline'], $titre['site'] );
	}
	return $titre;
}
add_filter( 'document_title_parts', 'fj_titre' );

/**
 * Traitement du formulaire de devis (envoi par e-mail via wp_mail).
 */
function fj_traiter_devis() {
	$retour = home_url( '/' );

	if ( ! isset( $_POST['fj_devis_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['fj_devis_nonce'] ) ), 'fj_devis' ) ) {
		wp_safe_redirect( add_query_arg( 'devis', 'erreur', $retour ) . '#contact' );
		exit;
	}

	// Champ piège anti-spam : rempli uniquement par les robots.
	if ( ! empty( $_POST['site_web'] ) ) {
		wp_safe_redirect( add_query_arg( 'devis', 'ok', $retour ) . '#contact' );
		exit;
	}

	$nom       = sanitize_text_field( wp_unslash( $_POST['nom'] ?? '' ) );
	$telephone = sanitize_text_field( wp_unslash( $_POST['telephone'] ?? '' ) );
	$email     = sanitize_email( wp_unslash( $_POST['email'] ?? '' ) );
	$travaux   = sanitize_text_field( wp_unslash( $_POST['travaux'] ?? '' ) );
	$message   = sanitize_textarea_field( wp_unslash( $_POST['message'] ?? '' ) );

	if ( '' === $nom || '' === $telephone ) {
		wp_safe_redirect( add_query_arg( 'devis', 'erreur', $retour ) . '#contact' );
		exit;
	}

	$corps  = "Nom : $nom\n";
	$corps .= "Téléphone : $telephone\n";
	$corps .= "E-mail : $email\n";
	$corps .= "Type de travaux : $travaux\n\n";
	$corps .= $message;

	$entetes = array();
	if ( $email ) {
		$entetes[] = 'Reply-To: ' . $nom . ' <' . $email . '>';
	}

	$envoye = wp_mail( fj_option( 'fj_email' ), 'Demande de devis - ' . $nom, $corps, $entetes );

	wp_safe_redirect( add_query_arg( 'devis', $envoye ? 'ok' : 'erreur', $retour ) . '#contact' );
	exit;
}
add_action( 'admin_post_nopriv_fj_devis', 'fj_traiter_devis' );
add_action( 'admin_post_fj_devis', 'fj_traiter_devis' );
