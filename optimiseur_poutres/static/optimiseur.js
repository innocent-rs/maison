function actualiserSurface() {
  const longueur = Number(document.querySelector('[name="longueur_m"]').value);
  const largeur = Number(document.querySelector('[name="largeur_m"]').value);
  document.querySelector("#surface").textContent =
    Number.isFinite(longueur * largeur) ? `${(longueur * largeur).toLocaleString("fr-FR", {maximumFractionDigits: 2})} m²` : "—";
}

document.querySelector('[name="longueur_m"]')?.addEventListener("input", actualiserSurface);
document.querySelector('[name="largeur_m"]')?.addEventListener("input", actualiserSurface);
actualiserSurface();

const profilFleche = document.querySelector("#profil-fleche");
const limitePersonnalisee = document.querySelector("#limite-personnalisee");

function actualiserProfilFleche() {
  if (!profilFleche || !limitePersonnalisee) return;
  const personnalise = profilFleche.value === "personnalise";
  limitePersonnalisee.hidden = !personnalise;
  limitePersonnalisee.querySelector("input").required = personnalise;
}

profilFleche?.addEventListener("change", actualiserProfilFleche);
actualiserProfilFleche();

const profilUsage = document.querySelector("#profil-usage");
profilUsage?.addEventListener("change", () => {
  const option = profilUsage.selectedOptions[0];
  if (!option?.dataset.g) return;
  document.querySelector('[name="masse_permanente_kg_m2"]').value = option.dataset.g;
  document.querySelector('[name="masse_exploitation_kg_m2"]').value = option.dataset.q;
});

const racineOnglets = document.querySelector("main[data-onglet-initial]");
const boutonsOnglets = [...document.querySelectorAll(".onglet-bouton")];
const contenusOnglets = [...document.querySelectorAll("[data-onglet-contenu]")];

function ouvrirOnglet(cible) {
  const onglet = cible === "solives" ? "solives" : "principales";
  boutonsOnglets.forEach((bouton) => {
    const actif = bouton.dataset.cible === onglet;
    bouton.classList.toggle("actif", actif);
    bouton.setAttribute("aria-selected", String(actif));
  });
  contenusOnglets.forEach((contenu) => {
    contenu.hidden = contenu.dataset.ongletContenu !== onglet;
  });
  window.history.replaceState(null, "", `#${onglet}`);
}

boutonsOnglets.forEach((bouton) => {
  bouton.addEventListener("click", () => ouvrirOnglet(bouton.dataset.cible));
});

if (racineOnglets) {
  const ongletHash = window.location.hash.slice(1);
  ouvrirOnglet(ongletHash || racineOnglets.dataset.ongletInitial);
}
