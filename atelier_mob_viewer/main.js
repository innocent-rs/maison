import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.querySelector("#viewer-canvas");
const viewport = document.querySelector(".viewport");
const status = document.querySelector("#viewer-status");
const statusText = document.querySelector("#status-text");
const layerList = document.querySelector("#layer-list");
const visibleMass = document.querySelector("#visible-mass");
const massNote = document.querySelector("#mass-note");
const modelRoot = new THREE.Group();
const layerObjects = new Map();
let manifest;
let modelBounds;
let explosionProgress = 0;
let explosionTarget = 0;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xe7ebe6, 0.018);
scene.add(modelRoot);

const camera = new THREE.PerspectiveCamera(38, 1, 0.02, 200);
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 3;
controls.maxDistance = 55;
controls.maxPolarAngle = Math.PI * 0.91;
controls.screenSpacePanning = true;

const hemisphere = new THREE.HemisphereLight(0xf7f5e9, 0x6b7a71, 2.4);
scene.add(hemisphere);

const sun = new THREE.DirectionalLight(0xfff4df, 4.2);
sun.position.set(-8, 16, 11);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -14;
sun.shadow.camera.right = 14;
sun.shadow.camera.top = 14;
sun.shadow.camera.bottom = -14;
sun.shadow.camera.near = 0.1;
sun.shadow.camera.far = 45;
sun.shadow.bias = -0.0003;
scene.add(sun);

const fill = new THREE.DirectionalLight(0xbcd4df, 1.6);
fill.position.set(10, 7, -10);
scene.add(fill);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(50, 50),
  new THREE.ShadowMaterial({ color: 0x425048, opacity: 0.12 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.07;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(30, 30, 0x9da8a1, 0xcbd2cd);
grid.position.y = -0.065;
grid.material.opacity = 0.24;
grid.material.transparent = true;
scene.add(grid);

const formatMass = (kilograms) => {
  if (kilograms >= 1000) {
    return `${(kilograms / 1000).toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} t`;
  }
  return `${kilograms.toLocaleString("fr-FR", {
    maximumFractionDigits: 1,
  })} kg`;
};

function createLayerRow(layer) {
  const unitDetail = layer.linearMassKgM
    ? `${layer.linearMassKgM.toLocaleString("fr-FR")} kg/m`
    : layer.unitMassKg
      ? `${layer.unitMassKg.toLocaleString("fr-FR")} kg/pce`
      : null;
  const row = document.createElement("label");
  row.className = "layer-row";
  row.style.setProperty("--layer-color", layer.color);
  row.title = layer.description;
  row.innerHTML = `
    <input type="checkbox" ${layer.visible ? "checked" : ""} />
    <span class="layer-switch" aria-hidden="true"></span>
    <span class="layer-copy">
      <strong>${layer.label}</strong>
      <small>${formatMass(layer.massKg)}${unitDetail ? ` · ${unitDetail}` : ""}</small>
    </span>
    <span class="layer-count">${layer.count}</span>
  `;
  const checkbox = row.querySelector("input");
  checkbox.dataset.layerId = layer.id;
  checkbox.addEventListener("change", () => {
    setLayerVisibility(layer.id, checkbox.checked, false);
  });
  row.classList.toggle("is-hidden", !layer.visible);
  layerList.append(row);
}

function setLayerVisibility(id, isVisible, syncCheckbox = true) {
  const layerObject = layerObjects.get(id);
  if (layerObject) layerObject.visible = isVisible;

  const checkbox = layerList.querySelector(`[data-layer-id="${id}"]`);
  if (checkbox && syncCheckbox) checkbox.checked = isVisible;
  checkbox?.closest(".layer-row")?.classList.toggle("is-hidden", !isVisible);
  updateVisibleMass();
}

function applyPreset(visibleIds) {
  const visibleSet = new Set(visibleIds);
  manifest.layers.forEach((layer) => {
    setLayerVisibility(layer.id, visibleSet.has(layer.id));
  });
}

function updateVisibleMass() {
  if (!manifest) return;
  const mass = manifest.layers.reduce((total, layer) => {
    const object = layerObjects.get(layer.id);
    return total + (object?.visible ? layer.massKg : 0);
  }, 0);
  visibleMass.textContent = formatMass(mass);

  const allVisible = manifest.layers.every(
    (layer) => layerObjects.get(layer.id)?.visible,
  );
  document.querySelector("#toggle-all").textContent = allVisible
    ? "Tout masquer"
    : "Tout afficher";
}

function fitCamera(direction = new THREE.Vector3(1, 0.72, 1)) {
  if (!modelBounds) return;
  const center = modelBounds.getCenter(new THREE.Vector3());
  const size = modelBounds.getSize(new THREE.Vector3());
  const maxSize = Math.max(size.x, size.y, size.z);
  const distance = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
  const normalizedDirection = direction.clone().normalize();
  camera.position.copy(center).addScaledVector(normalizedDirection, distance * 1.18);
  camera.near = Math.max(distance / 1000, 0.01);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function updateModelBoundsAndFit() {
  const currentDirection = camera.position.clone().sub(controls.target);
  modelBounds = new THREE.Box3().setFromObject(modelRoot);
  fitCamera(currentDirection);
}

function setExploded(isExploded) {
  explosionTarget = isExploded ? 1 : 0;
  const button = document.querySelector("#explode-toggle");
  button.classList.toggle("active", isExploded);
  button.setAttribute("aria-pressed", String(isExploded));

  window.setTimeout(updateModelBoundsAndFit, 520);
}

function setView(view) {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  if (view === "top") fitCamera(new THREE.Vector3(0.001, 1, 0));
  else if (view === "front") fitCamera(new THREE.Vector3(0, 0.18, 1));
  else fitCamera(new THREE.Vector3(1, 0.72, 1));
}

async function loadModel() {
  try {
    const response = await fetch("./public/models/manifest.json");
    if (!response.ok) throw new Error(`manifeste indisponible (${response.status})`);
    manifest = await response.json();

    document.querySelector("#project-size").textContent =
      `${manifest.project.widthM} × ${manifest.project.lengthM} m`;
    document.querySelector("#object-count").textContent =
      `${manifest.project.objectCount.toLocaleString("fr-FR")} pièces`;
    massNote.textContent =
      `Ensemble complet avec fixations : ${formatMass(manifest.summary.totalMassIncludingFastenersKg)}.`;
    manifest.layers.forEach(createLayerRow);

    const loader = new GLTFLoader();
    let loaded = 0;
    await Promise.all(manifest.layers.map(async (layer) => {
      const gltf = await loader.loadAsync(`./public/models/${layer.file}`);
      const layerGroup = gltf.scene;
      layerGroup.name = layer.label;
      layerGroup.userData.layerId = layer.id;
      layerGroup.visible = layer.visible;

      layerGroup.traverse((object) => {
        if (!object.isMesh) return;
        object.material = new THREE.MeshStandardMaterial({
          color: layer.color,
          roughness: layer.id.includes("connecteurs") || layer.id === "fondations" ? 0.48 : 0.78,
          metalness: layer.id.includes("connecteurs") || layer.id === "fondations" ? 0.55 : 0.04,
          side: THREE.DoubleSide,
        });
        object.castShadow = true;
        object.receiveShadow = true;
        object.userData.layerId = layer.id;
      });

      modelRoot.add(layerGroup);
      layerObjects.set(layer.id, layerGroup);
      loaded += 1;
      statusText.textContent = `Chargement ${loaded}/${manifest.layers.length}`;
    }));

    modelBounds = new THREE.Box3().setFromObject(modelRoot);
    fitCamera();
    updateVisibleMass();
    status.classList.add("is-hidden");
  } catch (error) {
    console.error(error);
    status.classList.add("is-error");
    statusText.textContent = `Impossible de charger le modèle : ${error.message}`;
  }
}

document.querySelector("#toggle-all").addEventListener("click", () => {
  if (!manifest) return;
  const allVisible = manifest.layers.every(
    (layer) => layerObjects.get(layer.id)?.visible,
  );
  applyPreset(allVisible ? [] : manifest.layers.map((layer) => layer.id));
});

document.querySelector("#show-all").addEventListener("click", () => {
  if (!manifest) return;
  applyPreset(manifest.layers.map((layer) => layer.id));
});

document.querySelector("#show-structure").addEventListener("click", () => {
  if (!manifest) return;
  applyPreset([
    "fondations",
    "poutres_primaires",
    "connecteurs_primaires",
    "solives_i",
    "connecteurs_solives",
    "tasseaux",
  ]);
});

document.querySelector("#show-caissons").addEventListener("click", () => {
  if (!manifest) return;
  applyPreset([
    "fondations",
    "poutres_primaires",
    "connecteurs_primaires",
    "solives_i",
    "connecteurs_solives",
    "tasseaux",
    "fonds_osb",
  ]);
});

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    setView(button.dataset.view === "fit" ? "iso" : button.dataset.view);
  });
});

document.querySelector("#explode-toggle").addEventListener("click", (event) => {
  if (!manifest) return;
  setExploded(event.currentTarget.getAttribute("aria-pressed") !== "true");
});

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const selectionCard = document.querySelector("#selection-card");
canvas.addEventListener("dblclick", (event) => {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObject(modelRoot, true)[0];
  if (!hit) {
    selectionCard.hidden = true;
    return;
  }
  const layer = manifest.layers.find(
    (candidate) => candidate.id === hit.object.userData.layerId,
  );
  if (!layer) return;
  document.querySelector("#selection-name").textContent = layer.label;
  document
    .querySelector("#selection-dot")
    .style.setProperty("--selection-color", layer.color);
  selectionCard.hidden = false;
});

function resize() {
  const { width, height } = viewport.getBoundingClientRect();
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

const resizeObserver = new ResizeObserver(resize);
resizeObserver.observe(viewport);

function render() {
  explosionProgress = THREE.MathUtils.damp(
    explosionProgress,
    explosionTarget,
    9,
    1 / 60,
  );
  if (manifest) {
    manifest.layers.forEach((layer) => {
      const object = layerObjects.get(layer.id);
      if (object) object.position.y = layer.explodeOffsetM * explosionProgress;
    });
  }
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}

resize();
render();
await loadModel();
