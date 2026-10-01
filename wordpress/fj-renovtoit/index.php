<?php get_header(); ?>
<main class="page-content">
  <div class="container">
    <?php if ( have_posts() ) : while ( have_posts() ) : the_post(); ?>
      <article <?php post_class(); ?>>
        <h1><?php the_title(); ?></h1>
        <?php the_content(); ?>
      </article>
    <?php endwhile; else : ?>
      <p><?php esc_html_e( 'Aucun contenu trouvé.', 'fj-renovtoit' ); ?></p>
    <?php endif; ?>
  </div>
</main>
<?php get_footer(); ?>
