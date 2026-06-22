import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const viewer = document.getElementById('viewer');
const statusEl = document.getElementById('viewerStatus');
const resetBtn = document.getElementById('resetViewBtn');
const metricsEl = document.getElementById('runtimeMetrics');
const selectionEl = document.getElementById('selectionPanel');

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0xf4f6f8, 1);
viewer.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0xb8c4d0, 1.8));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
keyLight.position.set(20, 35, 25);
scene.add(keyLight);

const root = new THREE.Group();
scene.add(root);

let packageBounds = new THREE.Box3();
let objectIndex = new Map();
let selectableMeshes = [];
let selectedMesh = null;
let selectedHighlight = null;
let runtimeStats = {
  renderMode: 'merged-color-buckets',
  meshCount: 0,
  renderBatchCount: 0,
  pickProxyCount: 0,
  tileCount: 0,
  triangleCount: 0,
  elapsedMs: 0,
  fps: 0,
  drawCalls: 0,
  geometryCount: 0,
  textureCount: 0,
  pickLatencyMs: 0,
  metadataLatencyMs: 0,
  package: null,
};
let framesSinceFpsSample = 0;
let lastFpsSampleAt = performance.now();

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const gltfLoader = new GLTFLoader();
const pickProxyMaterial = new THREE.MeshBasicMaterial({ visible: false });
const highlightMaterial = new THREE.MeshBasicMaterial({
  color: 0xffb020,
  wireframe: true,
  depthTest: false,
  transparent: true,
  opacity: 0.95,
});

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);
}

function renderMetrics() {
  if (!metricsEl) return;
  const pkg = runtimeStats.package || {};
  const bounds = pkg.bounds || {};
  const origins = (pkg.tiles || []).map(tile => tile.rtc_origin || [0, 0, 0]);
  metricsEl.innerHTML = [
    `<p class="kv"><span>Render Mode</span><strong>${escapeHtml(runtimeStats.renderMode)}</strong></p>`,
    `<p class="kv"><span>Loaded Meshes</span><strong>${runtimeStats.meshCount}</strong></p>`,
    `<p class="kv"><span>Render Batches</span><strong>${runtimeStats.renderBatchCount}</strong></p>`,
    `<p class="kv"><span>Pick Proxies</span><strong>${runtimeStats.pickProxyCount}</strong></p>`,
    `<p class="kv"><span>Triangles</span><strong>${runtimeStats.triangleCount}</strong></p>`,
    `<p class="kv"><span>Tiles</span><strong>${runtimeStats.tileCount}</strong></p>`,
    `<p class="kv"><span>Load Time</span><strong>${runtimeStats.elapsedMs} ms</strong></p>`,
    `<p class="kv"><span>FPS</span><strong>${runtimeStats.fps}</strong></p>`,
    `<p class="kv"><span>Draw Calls</span><strong>${runtimeStats.drawCalls}</strong></p>`,
    `<p class="kv"><span>GPU Geometries</span><strong>${runtimeStats.geometryCount}</strong></p>`,
    `<p class="kv"><span>GPU Textures</span><strong>${runtimeStats.textureCount}</strong></p>`,
    `<p class="kv"><span>Pick Latency</span><strong>${runtimeStats.pickLatencyMs} ms</strong></p>`,
    `<p class="kv"><span>Metadata Latency</span><strong>${runtimeStats.metadataLatencyMs} ms</strong></p>`,
    `<p class="kv"><span>Package Bytes</span><strong>${pkg.byte_size || 0}</strong></p>`,
    `<p class="kv"><span>Tile Origin(s)</span><strong>${escapeHtml(JSON.stringify(origins))}</strong></p>`,
    `<p class="kv"><span>Raw Bounds</span><strong>${escapeHtml(JSON.stringify(bounds))}</strong></p>`,
  ].join('');
}

function setMetrics(pkg, meshCount, renderBatchCount, pickProxyCount, tileCount, triangleCount, elapsedMs) {
  runtimeStats = {
    ...runtimeStats,
    package: pkg,
    meshCount,
    renderBatchCount,
    pickProxyCount,
    tileCount,
    triangleCount,
    elapsedMs,
  };
  renderMetrics();
}

function objectLookupKeys(item) {
  const properties = item.properties || {};
  return [
    properties.global_id ? `ifc:${properties.global_id}` : '',
    properties.global_id || '',
    item.uid ? String(item.uid) : '',
  ].filter(Boolean);
}

function objectSummaryForItem(item) {
  for (const key of objectLookupKeys(item)) {
    if (objectIndex.has(key)) return objectIndex.get(key);
  }
  return null;
}

function colorArrayForItem(item) {
  const color = item.mesh?.color;
  return Array.isArray(color) && color.length >= 3 ? color.slice(0, 3) : [0.45, 0.55, 0.72];
}

function colorKey(colorArray) {
  return colorArray.map(value => Number(value || 0).toFixed(4)).join(',');
}

function materialForColor(colorArray) {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(colorArray[0], colorArray[1], colorArray[2]),
    roughness: 0.75,
    metalness: 0.05,
    side: THREE.DoubleSide,
  });
}

function geometryFromPayload(item) {
  const meshData = item.mesh || {};
  const positions = Array.isArray(meshData.positions) ? meshData.positions : [];
  const indices = Array.isArray(meshData.indices) ? meshData.indices : [];
  if (!positions.length || !indices.length) return null;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

function userDataFromPayload(item) {
  const objectSummary = objectSummaryForItem(item);
  return {
    objectId: objectSummary?.id || null,
    objectUrl: objectSummary?.url || '',
    stableId: item.properties?.global_id || item.uid,
    ifcClass: item.properties?.ifc_class || item.kind || '',
    name: item.properties?.name || item.properties?.component_ref || '',
  };
}

function resize() {
  const rect = viewer.getBoundingClientRect();
  renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
  camera.aspect = Math.max(1, rect.width) / Math.max(1, rect.height);
  camera.updateProjectionMatrix();
}

function frameScene() {
  packageBounds = new THREE.Box3().setFromObject(root);
  if (packageBounds.isEmpty()) {
    camera.position.set(8, 8, 8);
    controls.target.set(0, 0, 0);
    controls.update();
    return;
  }

  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  packageBounds.getSize(size);
  packageBounds.getCenter(center);
  const radius = Math.max(size.x, size.y, size.z, 1);
  camera.position.set(center.x + radius * 1.4, center.y + radius * 1.0, center.z + radius * 1.4);
  camera.near = Math.max(radius / 10000, 0.01);
  camera.far = Math.max(radius * 100, 1000);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

async function loadPackage() {
  const packageUrl = viewer.dataset.packageUrl;
  const started = performance.now();
  const response = await fetch(packageUrl);
  if (!response.ok) throw new Error(`Package request failed: ${response.status}`);
  const pkg = await response.json();
  if (pkg.package_format === 'GLB') {
    await loadGlbPackage(pkg, started);
    return;
  }
  await loadJsonPackage(pkg, started);
}

async function loadJsonPackage(pkg, started) {
  objectIndex = new Map();
  for (const obj of pkg.objects || []) {
    if (obj.stable_id) objectIndex.set(obj.stable_id, obj);
    if (obj.source_object_id) objectIndex.set(obj.source_object_id, obj);
  }

  let meshCount = 0;
  let renderBatchCount = 0;
  let tileCount = 0;
  let triangleCount = 0;
  const buckets = new Map();

  for (const tile of pkg.tiles || []) {
    const tileResponse = await fetch(tile.url);
    if (!tileResponse.ok) throw new Error(`Tile request failed: ${tileResponse.status}`);
    const payload = await tileResponse.json();
    for (const item of payload.meshes || []) {
      const geometry = geometryFromPayload(item);
      if (!geometry) continue;
      const itemColor = colorArrayForItem(item);
      const key = colorKey(itemColor);
      if (!buckets.has(key)) {
        buckets.set(key, {
          color: itemColor,
          geometries: [],
        });
      }
      buckets.get(key).geometries.push(geometry);

      const pickMesh = new THREE.Mesh(geometry, pickProxyMaterial);
      pickMesh.userData = userDataFromPayload(item);
      pickMesh.updateMatrixWorld(true);
      selectableMeshes.push(pickMesh);

      meshCount += 1;
      triangleCount += Array.isArray(item.mesh?.indices) ? Math.floor(item.mesh.indices.length / 3) : 0;
    }
    tileCount += 1;
  }

  for (const bucket of buckets.values()) {
    const mergedGeometry = bucket.geometries.length === 1 ? bucket.geometries[0].clone() : mergeGeometries(bucket.geometries, false);
    if (!mergedGeometry) continue;
    const renderMesh = new THREE.Mesh(mergedGeometry, materialForColor(bucket.color));
    root.add(renderMesh);
    renderBatchCount += 1;
  }

  frameScene();
  const elapsedMs = Math.round(performance.now() - started);
  setStatus(`Loaded ${meshCount} mesh(es) as ${renderBatchCount} render batch(es) from ${tileCount} tile(s) in ${elapsedMs} ms.`);
  setMetrics(pkg, meshCount, renderBatchCount, selectableMeshes.length, tileCount, triangleCount, elapsedMs);
}

async function loadGlbPackage(pkg, started) {
  runtimeStats.renderMode = 'glb-sidecar';
  objectIndex = new Map();
  selectableMeshes = [];
  let meshCount = 0;
  let renderBatchCount = 0;
  let triangleCount = 0;
  let tileCount = 0;

  for (const tile of pkg.tiles || []) {
    const blobUrl = tile.blob_url || tile.url;
    if (!blobUrl) continue;
    const gltf = await gltfLoader.loadAsync(blobUrl);
    const tileRoot = gltf.scene || new THREE.Group();
    tileRoot.traverse(node => {
      if (!node.isMesh) return;
      meshCount += 1;
      renderBatchCount += 1;
      const geometry = node.geometry;
      const index = geometry?.index;
      const position = geometry?.getAttribute?.('position');
      if (index) {
        triangleCount += Math.floor(index.count / 3);
      } else if (position) {
        triangleCount += Math.floor(position.count / 3);
      }
    });
    root.add(tileRoot);
    tileCount += 1;
  }

  frameScene();
  const elapsedMs = Math.round(performance.now() - started);
  setStatus(`Loaded GLB package with ${meshCount} render mesh(es) from ${tileCount} tile(s) in ${elapsedMs} ms. Object picking is deferred for GLB packages.`);
  setMetrics(pkg, meshCount, renderBatchCount, 0, tileCount, triangleCount, elapsedMs);
}

function clearSelection() {
  if (selectedHighlight) {
    root.remove(selectedHighlight);
    selectedHighlight = null;
  }
  selectedMesh = null;
}

async function showSelection(mesh) {
  clearSelection();
  selectedMesh = mesh;
  selectedHighlight = new THREE.Mesh(mesh.geometry, highlightMaterial);
  selectedHighlight.renderOrder = 10;
  root.add(selectedHighlight);

  const baseRows = [
    `<p class="kv"><span>Stable ID</span><strong>${escapeHtml(mesh.userData.stableId)}</strong></p>`,
    `<p class="kv"><span>Class</span><strong>${escapeHtml(mesh.userData.ifcClass)}</strong></p>`,
    `<p class="kv"><span>Name</span><strong>${escapeHtml(mesh.userData.name)}</strong></p>`,
  ];
  if (!selectionEl) return;
  selectionEl.innerHTML = baseRows.join('') + '<p class="meta">Loading indexed metadata...</p>';

  if (!mesh.userData.objectUrl) {
    selectionEl.innerHTML = baseRows.join('') + '<p class="meta">No indexed object metadata for this mesh.</p>';
    return;
  }

  try {
    const metadataStarted = performance.now();
    const response = await fetch(mesh.userData.objectUrl);
    if (!response.ok) throw new Error(`Metadata request failed: ${response.status}`);
    const data = await response.json();
    runtimeStats.metadataLatencyMs = Math.round(performance.now() - metadataStarted);
    renderMetrics();
    selectionEl.innerHTML = [
      `<p class="kv"><span>Stable ID</span><strong>${escapeHtml(data.stable_id)}</strong></p>`,
      `<p class="kv"><span>Type</span><strong>${escapeHtml(data.object_type)}</strong></p>`,
      `<p class="kv"><span>Tag</span><strong>${escapeHtml(data.tag)}</strong></p>`,
      `<p class="kv"><span>Source Object</span><strong>${escapeHtml(data.source_object_id)}</strong></p>`,
      `<p class="kv"><span>Bounds</span><strong>${escapeHtml(JSON.stringify(data.bounds || {}))}</strong></p>`,
      `<p class="kv"><span>Metadata</span><strong>${escapeHtml(JSON.stringify(data.metadata || {}))}</strong></p>`,
    ].join('');
  } catch (error) {
    selectionEl.innerHTML = baseRows.join('') + `<p class="meta">${escapeHtml(error.message || 'Unable to load metadata.')}</p>`;
  }
}

function pick(event) {
  if (!selectableMeshes.length) {
    runtimeStats.pickLatencyMs = 0;
    renderMetrics();
    if (selectionEl) selectionEl.textContent = 'Object picking is not available for this package format yet.';
    return;
  }
  const pickStarted = performance.now();
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(selectableMeshes, false);
  runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
  renderMetrics();
  if (!hits.length) {
    clearSelection();
    if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
    return;
  }
  showSelection(hits[0].object);
}

function animate() {
  controls.update();
  renderer.render(scene, camera);
  runtimeStats.drawCalls = renderer.info.render.calls;
  runtimeStats.geometryCount = renderer.info.memory.geometries;
  runtimeStats.textureCount = renderer.info.memory.textures;
  framesSinceFpsSample += 1;
  const now = performance.now();
  if (now - lastFpsSampleAt >= 1000) {
    runtimeStats.fps = Math.round((framesSinceFpsSample * 1000) / (now - lastFpsSampleAt));
    framesSinceFpsSample = 0;
    lastFpsSampleAt = now;
    renderMetrics();
  }
  requestAnimationFrame(animate);
}

window.addEventListener('resize', resize);
if (resetBtn) resetBtn.addEventListener('click', frameScene);
renderer.domElement.addEventListener('click', pick);
resize();
animate();

loadPackage().catch(error => {
  setStatus(error.message || 'Unable to load package.');
});
