<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo( 'charset' ); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<header class="site-header">
  <div class="container">
    <?php if ( has_custom_logo() ) : ?>
      <?php the_custom_logo(); ?>
    <?php else : ?>
      <a href="<?php echo esc_url( home_url( '/' ) ); ?>" class="logo">FJ <span>Couverture</span></a>
    <?php endif; ?>
    <button class="nav-toggle" aria-label="<?php esc_attr_e( 'Ouvrir le menu', 'fj-couverture' ); ?>" aria-expanded="false">☰</button>
    <nav class="main-nav">
      <?php
      if ( has_nav_menu( 'principal' ) ) {
          wp_nav_menu( array(
              'theme_location' => 'principal',
              'container'      => false,
          ) );
      } else {
          $accueil = esc_url( home_url( '/' ) );
          ?>
          <ul>
            <li><a href="<?php echo $accueil; ?>#services">Services</a></li>
            <li><a href="<?php echo $accueil; ?>#apropos">L'entreprise</a></li>
            <li><a href="<?php echo $accueil; ?>#realisations">Réalisations</a></li>
            <li><a href="<?php echo $accueil; ?>#contact" class="btn">Devis gratuit</a></li>
          </ul>
          <?php
      }
      ?>
    </nav>
  </div>
</header>
