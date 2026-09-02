const tableBody = document.querySelector("#catalogue-table tbody");

function renumeroter() {
  [...tableBody.rows].forEach((row, index) => {
    row.querySelector(".active").value = String(index);
  });
}

document.querySelector("#ajouter")?.addEventListener("click", () => {
  const index = tableBody.rows.length;
  const row = tableBody.insertRow();
  row.innerHTML = `
    <td><input class="active" name="section_active" type="checkbox" value="${index}" checked></td>
    <td><input name="section_nom" required value="Nouvelle section"></td>
    <td><input name="section_largeur" type="number" min="1" step="any" required value="100"></td>
    <td><input name="section_hauteur" type="number" min="1" step="any" required value="200"></td>
    <td><input name="section_prix" type="number" min="0.01" step="any" required value="30"></td>
    <td><input name="section_longueur_max" type="number" min="0.1" step="any" required value="13"></td>
    <td><button class="supprimer" type="button" aria-label="Supprimer cette section">×</button></td>`;
});

tableBody?.addEventListener("click", (event) => {
  const button = event.target.closest(".supprimer");
  if (!button) return;
  if (tableBody.rows.length === 1) return;
  button.closest("tr").remove();
  renumeroter();
});

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
