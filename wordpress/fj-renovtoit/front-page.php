<?php get_header(); ?>

  <main>
    <section class="hero" id="accueil">
      <div class="container">
        <p class="metiers">Couverture<span>•</span>Zinguerie<span>•</span>Rénovation<span>•</span>Ravalement</p>
        <h1>Couvreur à <span class="or">Savigny-sur-Orge</span></h1>
        <span class="script">Votre toit, notre expertise !</span>
        <p class="intro">Une entreprise de confiance pour tous vos travaux de <strong class="or">toiture</strong> et de <strong class="or">rénovation</strong> à Savigny-sur-Orge et dans toute l'Essonne.</p>
        <div class="actions">
          <a href="#contact" class="btn">Devis gratuit</a>
          <a href="<?php echo esc_attr( fj_tel_href() ); ?>" class="btn btn-outline"><svg><use href="#i-tel"/></svg><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a>
        </div>
      </div>
    </section>

    <div class="engagements">
      <div class="container">
        <ul>
          <li><svg><use href="#i-bouclier"/></svg>Travail de qualité et finitions soignées</li>
          <li><svg><use href="#i-equipe"/></svg>Équipe expérimentée et à l'écoute</li>
          <li><svg><use href="#i-medaille"/></svg>Devis gratuit et sans engagement</li>
          <li><svg><use href="#i-horloge"/></svg>Intervention rapide dans votre secteur</li>
        </ul>
      </div>
    </div>

    <section id="prestations">
      <div class="container">
        <div class="section-title">
          <span class="surtitre">Nos prestations</span>
          <h2>Tous vos travaux de toiture à Savigny-sur-Orge</h2>
          <p>Pose, rénovation et réparation de tous types de toitures : ardoises, tuiles, zinc, bac acier…</p>
        </div>

        <div class="prestations-principales">
          <article class="presta-photo">
            <div class="photo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/toiture.jpg" alt="Toiture en tuiles avec fenêtre de toit" loading="lazy"><span class="etiquette">Toiture</span></div>
            <div class="corps">
              <h3>Couverture <small>à Savigny-sur-Orge</small></h3>
              <p>Pose, rénovation et réparation de tous types de toitures.</p>
              <ul><li>Tuiles mécaniques et plates</li><li>Ardoises naturelles</li><li>Zinc et bac acier</li></ul>
            </div>
          </article>
          <article class="presta-photo">
            <div class="photo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/zinguerie.jpg" alt="Gouttière et descente en zinc" loading="lazy"><span class="etiquette">Zinguerie</span></div>
            <div class="corps">
              <h3>Zinguerie <small>à Savigny-sur-Orge</small></h3>
              <p>Gouttières, chéneaux, habillages, étanchéité et finitions.</p>
              <ul><li>Gouttières et descentes d'eau pluviale</li><li>Noues, solins et abergements</li><li>Habillage de rives et bandeaux</li></ul>
            </div>
          </article>
          <article class="presta-photo">
            <div class="photo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/renovation.jpg" alt="Rénovation de toiture en cours avec liteaux" loading="lazy"><span class="etiquette">Rénovation</span></div>
            <div class="corps">
              <h3>Rénovation de toiture <small>à Savigny-sur-Orge</small></h3>
              <p>Rénovation de toiture et aménagements extérieurs.</p>
              <ul><li>Réfection complète ou partielle</li><li>Remplacement de liteaux et d'écran sous toiture</li><li>Reprise des faîtages et des rives</li></ul>
            </div>
          </article>
          <article class="presta-photo">
            <div class="photo"><img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/ravalement.jpg" alt="Maison avec façade rénovée" loading="lazy"><span class="etiquette">Ravalement</span></div>
            <div class="corps">
              <h3>Ravalement de façade <small>à Savigny-sur-Orge</small></h3>
              <p>Nettoyage, traitement et remise en état de vos façades.</p>
              <ul><li>Nettoyage haute pression</li><li>Traitement des fissures</li><li>Peinture et enduit de façade</li></ul>
            </div>
          </article>
        </div>

        <h3 class="sous-titre">Et aussi <span class="or">à Savigny-sur-Orge</span></h3>
        <div class="prestations-grille">
          <article class="presta">
            <div class="icone"><svg><use href="#i-goutte"/></svg></div>
            <h3>Recherche et réparation de fuites <small>à Savigny-sur-Orge</small></h3>
            <p>Diagnostic de la fuite, remplacement des tuiles cassées, reprise des solins.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-brosse"/></svg></div>
            <h3>Nettoyage et démoussage <small>à Savigny-sur-Orge</small></h3>
            <p>Élimination des mousses et lichens pour prolonger la durée de vie du toit.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-spray"/></svg></div>
            <h3>Traitement hydrofuge <small>à Savigny-sur-Orge</small></h3>
            <p>Protection de vos tuiles contre l'humidité et l'encrassement.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-couches"/></svg></div>
            <h3>Isolation de toiture <small>à Savigny-sur-Orge</small></h3>
            <p>Isolation des combles et sous toiture pour plus de confort et d'économies.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-fenetre"/></svg></div>
            <h3>Pose de fenêtres de toit <small>à Savigny-sur-Orge</small></h3>
            <p>Création ou remplacement de fenêtres de toit avec raccords étanches.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-cheminee"/></svg></div>
            <h3>Réfection de cheminée <small>à Savigny-sur-Orge</small></h3>
            <p>Rejointoiement de souche, solins et chapeaux de cheminée.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-charpente"/></svg></div>
            <h3>Charpente <small>à Savigny-sur-Orge</small></h3>
            <p>Réparation, renforcement et traitement des bois de charpente.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-terrasse"/></svg></div>
            <h3>Étanchéité de toit terrasse <small>à Savigny-sur-Orge</small></h3>
            <p>Membranes d'étanchéité pour toits plats, terrasses et garages.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-arbre"/></svg></div>
            <h3>Aménagements extérieurs <small>à Savigny-sur-Orge</small></h3>
            <p>Finitions et aménagements autour de la maison après vos travaux.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-maison"/></svg></div>
            <h3>Entretien de toiture <small>à Savigny-sur-Orge</small></h3>
            <p>Contrôle, remplacement des tuiles abîmées et vérification des points sensibles.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-gouttiere"/></svg></div>
            <h3>Nettoyage de gouttières <small>à Savigny-sur-Orge</small></h3>
            <p>Débouchage et nettoyage des gouttières et descentes pour un bon écoulement.</p>
          </article>
          <article class="presta">
            <div class="icone"><svg><use href="#i-eclair"/></svg></div>
            <h3>Dépannage d'urgence <small>à Savigny-sur-Orge</small></h3>
            <p>Bâchage et mise en sécurité de votre toiture après une tempête ou un sinistre.</p>
          </article>
        </div>
      </div>
    </section>

    <section id="entreprise" class="section-alt">
      <div class="container apropos">
        <div>
          <span class="surtitre or">L'entreprise</span>
          <h2>F.J Renovtoit, votre couvreur <span class="or">à Savigny-sur-Orge</span></h2>
          <p>Couverture, zinguerie, rénovation et ravalement : nous prenons en charge vos travaux de A à Z, pour les particuliers comme pour les professionnels.</p>
          <p>Conseils honnêtes, devis clair et détaillé, chantier propre et respect des délais : c'est notre façon de travailler.</p>
          <span class="script">Un travail soigné, des résultats durables !</span>
          <a href="#contact" class="btn">Demander mon devis</a>
        </div>
        <div class="apropos-visuel">
          <img src="<?php echo esc_url( get_template_directory_uri() ); ?>/assets/img/hero-toit.jpg" alt="Toiture rénovée avec cheminée en briques" loading="lazy">
          <div class="pastille"><strong>Devis gratuit</strong>et sans engagement</div>
        </div>
      </div>
    </section>

    <section id="zone">
      <div class="container">
        <div class="section-title">
          <span class="surtitre">Zone d'intervention</span>
          <h2>Savigny-sur-Orge et alentours</h2>
          <p>Nous intervenons rapidement à Savigny-sur-Orge et dans les communes voisines de l'Essonne (91).</p>
        </div>
        <ul class="villes">
          <li class="principale">Savigny-sur-Orge</li>
          <li>Épinay-sur-Orge</li>
          <li>Morsang-sur-Orge</li>
          <li>Viry-Châtillon</li>
          <li>Juvisy-sur-Orge</li>
          <li>Athis-Mons</li>
          <li>Paray-Vieille-Poste</li>
          <li>Villemoisson-sur-Orge</li>
          <li>Sainte-Geneviève-des-Bois</li>
          <li>Grigny</li>
          <li>Chilly-Mazarin</li>
          <li>Longjumeau</li>
        </ul>
      </div>
    </section>

    <div class="bandeau-appel">
      <div class="container">
        <div>
          <a href="<?php echo esc_attr( fj_tel_href() ); ?>" class="tel"><span class="rond"><svg><use href="#i-tel"/></svg></span><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a>
          <p class="adresse"><?php echo esc_html( fj_option( 'fj_adresse' ) ); ?></p>
        </div>
        <span class="script">Contactez-nous dès maintenant !</span>
      </div>
    </div>

    <section id="contact" class="section-alt">
      <div class="container contact">
        <div>
          <div class="section-title gauche">
            <span class="surtitre">Contact</span>
            <h2>Votre devis gratuit</h2>
            <p>Décrivez-nous votre projet, nous vous recontactons rapidement.</p>
          </div>
          <ul class="contact-infos">
            <li><span class="icone"><svg><use href="#i-tel"/></svg></span><div><strong>Téléphone</strong><a href="<?php echo esc_attr( fj_tel_href() ); ?>"><?php echo esc_html( fj_option( 'fj_telephone' ) ); ?></a></div></li>
            <li><span class="icone"><svg><use href="#i-mail"/></svg></span><div><strong>E-mail</strong><a href="mailto:<?php echo esc_attr( fj_option( 'fj_email' ) ); ?>"><?php echo esc_html( fj_option( 'fj_email' ) ); ?></a></div></li>
            <li><span class="icone"><svg><use href="#i-pin"/></svg></span><div><strong>Adresse</strong><a href="<?php echo esc_url( fj_maps_url() ); ?>" target="_blank" rel="noopener"><?php echo esc_html( fj_option( 'fj_adresse' ) ); ?></a></div></li>
          </ul>
        </div>
        <form id="form-devis" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <?php if ( isset( $_GET['devis'] ) && 'ok' === $_GET['devis'] ) : ?>
            <p class="form-message">Merci, votre demande a bien été envoyée. Nous vous recontactons rapidement.</p>
          <?php elseif ( isset( $_GET['devis'] ) ) : ?>
            <p class="form-message form-erreur">Une erreur est survenue. Merci de nous appeler directement.</p>
          <?php endif; ?>
          <input type="hidden" name="action" value="fj_devis">
          <?php wp_nonce_field( 'fj_devis', 'fj_devis_nonce' ); ?>
          <div class="screen-reader-text" aria-hidden="true"><label for="site_web">Ne pas remplir</label><input id="site_web" name="site_web" tabindex="-1" autocomplete="off"></div>
          <h3>Demande de devis</h3>
          <div class="form-row">
            <div><label for="nom">Nom *</label><input id="nom" name="nom" autocomplete="name" required></div>
            <div><label for="telephone">Téléphone *</label><input id="telephone" name="telephone" type="tel" autocomplete="tel" required></div>
          </div>
          <div><label for="email">E-mail</label><input id="email" name="email" type="email" autocomplete="email"></div>
          <div>
            <label for="travaux">Type de travaux</label>
            <select id="travaux" name="travaux">
              <option>Couverture</option>
              <option>Zinguerie</option>
              <option>Rénovation de toiture</option>
              <option>Ravalement de façade</option>
              <option>Fuite / réparation</option>
              <option>Entretien / nettoyage de gouttières</option>
              <option>Nettoyage / démoussage</option>
              <option>Isolation</option>
              <option>Fenêtre de toit</option>
              <option>Cheminée / charpente</option>
              <option>Étanchéité toit terrasse</option>
              <option>Dépannage d'urgence</option>
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
