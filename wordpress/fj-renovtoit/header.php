<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo( 'charset' ); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" href="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/logo.svg" type="image/svg+xml">
  <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
  <!-- Icônes -->
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="i-maison" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11 12 3l9 8M5 10v10h14V10M10 20v-6h4v6"/></symbol>
      <symbol id="i-gouttiere" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18v4a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3zM16 13v8M13 21h6"/></symbol>
      <symbol id="i-renovation" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12 12 4l9 8M5 11v9h6M14 14l6 6M17 12l3-3 2 2-3 3z"/></symbol>
      <symbol id="i-facade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V9l8-5 8 5v12zM8 12h3v3H8zM13 12h3v3h-3zM10 21v-3h4v3"/></symbol>
      <symbol id="i-goutte" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/></symbol>
      <symbol id="i-brosse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4l6 6-7 7H7v-6zM4 20l3-3M9 9l6 6"/></symbol>
      <symbol id="i-spray" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 10h7v11H8zM9.5 10V6h4v4M17 4h2M17 7h4M17 10h2"/></symbol>
      <symbol id="i-couches" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l10-5 10 5-10 5zM2 13l10 5 10-5M2 18l10 5 10-5"/></symbol>
      <symbol id="i-fenetre" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v16H4zM12 4v16M4 12h16"/></symbol>
      <symbol id="i-cheminee" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21V12l9-7 9 7v9M15 7V3h3v6.5"/></symbol>
      <symbol id="i-charpente" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20 12 4l10 16zM12 4v16M7 12l5 8 5-8"/></symbol>
      <symbol id="i-terrasse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11h18v9H3zM3 15h18M5 7c2-2 4 2 6 0s4-2 6 0 3 1 4 0"/></symbol>
      <symbol id="i-arbre" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l6 8h-4l4 6H6l4-6H6zM12 17v4"/></symbol>
      <symbol id="i-eclair" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></symbol>
      <symbol id="i-bouclier" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5"/></symbol>
      <symbol id="i-equipe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="9" r="2.5"/><path d="M16 15c3 0 5 1.5 5 4"/></symbol>
      <symbol id="i-medaille" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="6"/><path d="M9 14.5 7 22l5-3 5 3-2-7.5M9.5 9l2 2 3-3.5"/></symbol>
      <symbol id="i-horloge" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>
      <symbol id="i-tel" viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></symbol>
      <symbol id="i-mail" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h18v14H3zM3 7l9 6 9-6"/></symbol>
      <symbol id="i-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6 7-12a7 7 0 0 0-14 0c0 6 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></symbol>
    </defs>
  </svg>

  <header class="site-header">
    <div class="container">
      <a href="<?php echo esc_url( home_url( '/' ) ); ?>#accueil" class="logo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/logo.svg" alt="F.J Renovtoit" width="208" height="52"></a>
      <button class="nav-toggle" aria-label="Ouvrir le menu" aria-expanded="false">☰</button>
      <nav class="main-nav">
        <ul>
          <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#prestations">Prestations</a></li>
          <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#entreprise">L'entreprise</a></li>
          <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#zone">Zone d'intervention</a></li>
          <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#contact">Contact</a></li>
          <li><a href="<?php echo esc_attr( fj_tel_href() ); ?>" class="btn"><svg><use href="#i-tel"/></svg><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a></li>
        </ul>
      </nav>
    </div>
  </header>

