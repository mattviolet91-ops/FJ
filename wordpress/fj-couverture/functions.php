<?php
/**
 * Thème FJ Couverture.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function fj_setup() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'custom-logo' );
	register_nav_menus( array( 'principal' => __( 'Menu principal', 'fj-couverture' ) ) );
}
add_action( 'after_setup_theme', 'fj_setup' );

function fj_assets() {
	$version = wp_get_theme()->get( 'Version' );
	wp_enqueue_style( 'fj-main', get_template_directory_uri() . '/assets/css/main.css', array(), $version );
	wp_enqueue_style( 'fj-style', get_stylesheet_uri(), array( 'fj-main' ), $version );
	wp_enqueue_script( 'fj-main', get_template_directory_uri() . '/assets/js/main.js', array(), $version, true );
}
add_action( 'wp_enqueue_scripts', 'fj_assets' );

/**
 * Coordonnées modifiables dans Apparence > Personnaliser.
 */
function fj_defaults() {
	return array(
		'fj_telephone' => '00 00 00 00 00',
		'fj_email'     => get_option( 'admin_email' ),
		'fj_zone'      => '[Votre ville et alentours]',
		'fj_horaires'  => 'Du lundi au vendredi, 8h – 18h',
	);
}

function fj_option( $key ) {
	$defaults = fj_defaults();
	return get_theme_mod( $key, $defaults[ $key ] );
}

function fj_customize_register( $wp_customize ) {
	$wp_customize->add_section( 'fj_coordonnees', array(
		'title'    => __( 'Coordonnées FJ Couverture', 'fj-couverture' ),
		'priority' => 30,
	) );

	$champs = array(
		'fj_telephone' => array( __( 'Téléphone', 'fj-couverture' ), 'sanitize_text_field' ),
		'fj_email'     => array( __( 'E-mail (reçoit les demandes de devis)', 'fj-couverture' ), 'sanitize_email' ),
		'fj_zone'      => array( __( "Zone d'intervention", 'fj-couverture' ), 'sanitize_text_field' ),
		'fj_horaires'  => array( __( 'Horaires', 'fj-couverture' ), 'sanitize_text_field' ),
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
 * Lien tel: à partir du numéro saisi.
 */
function fj_tel_href() {
	$numero = preg_replace( '/[^0-9+]/', '', fj_option( 'fj_telephone' ) );
	if ( 0 === strpos( $numero, '0' ) ) {
		$numero = '+33' . substr( $numero, 1 );
	}
	return 'tel:' . $numero;
}

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
