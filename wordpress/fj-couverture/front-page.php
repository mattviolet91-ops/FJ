<?php get_header(); ?>

  <main>
    <section class="hero" id="accueil">
      <div class="container">
        <h1>Votre toiture entre de bonnes mains</h1>
        <p>FJ Couverture réalise vos travaux de couverture, zinguerie et réparation de toiture, avec un travail soigné et des délais respectés.</p>
        <div class="actions">
          <a href="#contact" class="btn">Demander un devis</a>
          <a href="<?php echo esc_attr( fj_tel_href() ); ?>" class="btn btn-outline">📞 Appeler</a>
        </div>
        <ul class="badges">
          <li>Devis gratuit</li>
          <li>Intervention rapide</li>
          <li>Travail soigné</li>
        </ul>
      </div>
    </section>

    <section id="services" class="section-alt">
      <div class="container">
        <div class="section-title">
          <h2>Nos services</h2>
          <p>Du neuf à la rénovation, nous intervenons sur tous types de toitures.</p>
        </div>
        <div class="grid">
          <article class="card">
            <div class="icon">🏠</div>
            <h3>Couverture neuve</h3>
            <p>Pose de tuiles, ardoises et bacs acier pour vos constructions et extensions.</p>
          </article>
          <article class="card">
            <div class="icon">🔨</div>
            <h3>Rénovation de toiture</h3>
            <p>Remplacement complet ou partiel de votre couverture, mise aux normes.</p>
          </article>
          <article class="card">
            <div class="icon">💧</div>
            <h3>Recherche et réparation de fuites</h3>
            <p>Diagnostic, remplacement des tuiles cassées, reprise des faîtages et solins.</p>
          </article>
          <article class="card">
            <div class="icon">🔧</div>
            <h3>Zinguerie</h3>
            <p>Gouttières, descentes d'eau pluviale, noues, chéneaux et habillages.</p>
          </article>
          <article class="card">
            <div class="icon">🧹</div>
            <h3>Nettoyage et démoussage</h3>
            <p>Démoussage, traitement hydrofuge et entretien pour prolonger la vie du toit.</p>
          </article>
          <article class="card">
            <div class="icon">🌡️</div>
            <h3>Isolation de toiture</h3>
            <p>Isolation des combles et sous toiture pour plus de confort et d'économies.</p>
          </article>
        </div>
      </div>
    </section>

    <section id="apropos">
      <div class="container about">
        <div>
          <h2>L'entreprise FJ Couverture</h2>
          <p>Artisan couvreur, FJ Couverture accompagne les particuliers et les professionnels pour tous leurs travaux de toiture.</p>
          <p>Notre priorité : vous conseiller honnêtement, réaliser un travail durable et laisser un chantier propre.</p>
          <a href="#contact" class="btn">Parlons de votre projet</a>
        </div>
        <div class="stats">
          <div class="stat"><strong>100%</strong>Devis gratuits</div>
          <div class="stat"><strong>48h</strong>Réponse rapide</div>
          <div class="stat"><strong>🏠</strong>Particuliers</div>
          <div class="stat"><strong>🏢</strong>Professionnels</div>
        </div>
      </div>
    </section>

    <section id="realisations" class="section-alt">
      <div class="container">
        <div class="section-title">
          <h2>Nos réalisations</h2>
          <p>Quelques exemples de chantiers (photos à ajouter).</p>
        </div>
        <div class="grid">
          <article class="realisation">
            <div class="visuel">🏠</div>
            <div class="texte">
              <h3>Réfection complète en tuiles</h3>
              <p>Dépose de l'ancienne couverture, pose d'un écran sous toiture et de tuiles neuves.</p>
            </div>
          </article>
          <article class="realisation">
            <div class="visuel">🔧</div>
            <div class="texte">
              <h3>Zinguerie et gouttières</h3>
              <p>Remplacement des gouttières et descentes en zinc.</p>
            </div>
          </article>
          <article class="realisation">
            <div class="visuel">🧹</div>
            <div class="texte">
              <h3>Démoussage et traitement</h3>
              <p>Nettoyage complet de la toiture et application d'un hydrofuge.</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section id="contact">
      <div class="container contact">
        <div>
          <div class="section-title" style="text-align:left">
            <h2>Contact &amp; devis</h2>
            <p>Décrivez-nous votre projet, nous vous recontactons rapidement.</p>
          </div>
          <ul class="contact-infos">
            <li><strong>Téléphone</strong><a href="<?php echo esc_attr( fj_tel_href() ); ?>"><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a></li>
            <li><strong>E-mail</strong><a href="mailto:<?php echo esc_attr( fj_option( 'fj_email' ) ); ?>"><?php echo esc_html( fj_option( 'fj_email' ) ); ?></a></li>
            <li><strong>Adresse</strong><a href="<?php echo esc_url( 'https://www.google.com/maps/search/?api=1&query=' . rawurlencode( fj_option( 'fj_adresse' ) ) ); ?>" target="_blank" rel="noopener"><?php echo esc_html( fj_option( 'fj_adresse' ) ); ?></a></li>
            <li><strong>Zone d'intervention</strong><?php echo esc_html( fj_option( 'fj_zone' ) ); ?></li>
            <li><strong>Horaires</strong><?php echo esc_html( fj_option( 'fj_horaires' ) ); ?></li>
          </ul>
        </div>
        <form id="form-devis" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <?php if ( isset( $_GET['devis'] ) && 'ok' === $_GET['devis'] ) : ?>
            <p class="form-message">Merci, votre demande a bien été envoyée. Nous vous recontactons rapidement.</p>
          <?php elseif ( isset( $_GET['devis'] ) ) : ?>
            <p class="form-message" style="color:#b3261e">Une erreur est survenue. Merci de nous appeler directement.</p>
          <?php endif; ?>
          <input type="hidden" name="action" value="fj_devis">
          <?php wp_nonce_field( 'fj_devis', 'fj_devis_nonce' ); ?>
          <div class="screen-reader-text" aria-hidden="true"><label for="site_web">Ne pas remplir</label><input id="site_web" name="site_web" tabindex="-1" autocomplete="off"></div>
          <div class="form-row">
            <div><label for="nom">Nom *</label><input id="nom" name="nom" required></div>
            <div><label for="telephone">Téléphone *</label><input id="telephone" name="telephone" type="tel" required></div>
          </div>
          <div><label for="email">E-mail</label><input id="email" name="email" type="email"></div>
          <div>
            <label for="travaux">Type de travaux</label>
            <select id="travaux" name="travaux">
              <option>Couverture neuve</option>
              <option>Rénovation de toiture</option>
              <option>Fuite / réparation</option>
              <option>Zinguerie</option>
              <option>Nettoyage / démoussage</option>
              <option>Isolation</option>
              <option>Autre</option>
            </select>
          </div>
          <div><label for="message">Votre projet</label><textarea id="message" name="message" rows="5"></textarea></div>
          <button type="submit" class="btn">Envoyer ma demande</button>
        </form>
      </div>
    </section>
  </main>

<?php get_footer(); ?>
