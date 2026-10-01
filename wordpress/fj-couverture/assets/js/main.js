document.addEventListener("DOMContentLoaded", function () {
  // Menu mobile
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Année du pied de page
  var annee = document.getElementById("annee");
  if (annee) annee.textContent = new Date().getFullYear();

  // Formulaire de devis (version statique : ouvre la messagerie)
  var form = document.getElementById("form-devis");
  if (form && form.dataset.mode === "mailto") {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var d = new FormData(form);
      var corps =
        "Nom : " + d.get("nom") + "\n" +
        "Téléphone : " + d.get("telephone") + "\n" +
        "E-mail : " + d.get("email") + "\n" +
        "Type de travaux : " + d.get("travaux") + "\n\n" +
        d.get("message");
      window.location.href =
        "mailto:" + form.dataset.email +
        "?subject=" + encodeURIComponent("Demande de devis - " + d.get("nom")) +
        "&body=" + encodeURIComponent(corps);
    });
  }
});
