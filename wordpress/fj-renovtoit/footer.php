  <footer class="site-footer">
    <div class="container">
      <div class="footer-grille">
        <div>
          <a href="<?php echo esc_url( home_url( '/' ) ); ?>#accueil" class="logo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/logo.svg" alt="F.J Renovtoit" width="224" height="56"></a>
          <p>Couverture, zinguerie, rénovation et ravalement à Savigny-sur-Orge et en Essonne.</p>
        </div>
        <div>
          <h4>Prestations</h4>
          <ul>
            <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#prestations">Couverture à Savigny-sur-Orge</a></li>
            <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#prestations">Zinguerie à Savigny-sur-Orge</a></li>
            <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#prestations">Rénovation de toiture à Savigny-sur-Orge</a></li>
            <li><a href="<?php echo esc_url( home_url( '/' ) ); ?>#prestations">Ravalement à Savigny-sur-Orge</a></li>
          </ul>
        </div>
        <div>
          <h4>Contact</h4>
          <ul>
            <li><a href="<?php echo esc_attr( fj_tel_href() ); ?>"><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a></li>
            <li><a href="mailto:<?php echo esc_attr( fj_option( 'fj_email' ) ); ?>"><?php echo esc_html( fj_option( 'fj_email' ) ); ?></a></li>
            <li><?php echo esc_html( fj_option( 'fj_adresse' ) ); ?></li>
          </ul>
        </div>
      </div>
      <p class="footer-bas">© <?php echo esc_html( gmdate( 'Y' ) ); ?> F.J Renovtoit – Couvreur à Savigny-sur-Orge – Tous droits réservés</p>
    </div>
  </footer>

  <a href="<?php echo esc_attr( fj_tel_href() ); ?>" class="appel-flottant" aria-label="Appeler F.J Renovtoit"><svg><use href="#i-tel"/></svg></a>


<?php wp_footer(); ?>
</body>
</html>
