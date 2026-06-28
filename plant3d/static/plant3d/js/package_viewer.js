import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const viewer = document.getElementById('viewer');
const statusEl = document.getElementById('viewerStatus');
const resetBtn = document.getElementById('resetViewBtn');
const metricsEl = document.getElementById('runtimeMetrics');
const selectionEl = document.getElementById('selectionPanel');

const devicePixelRatio = window.devicePixelRatio || 1;
const maxIdlePixelRatio = Math.max(0.75, Math.min(devicePixelRatio, 1.5));
const interactionPixelRatio = Math.max(0.75, Math.min(maxIdlePixelRatio, 1.0));
const minPixelRatio = Math.min(interactionPixelRatio, 0.75);

const renderer = new THREE.WebGLRenderer({
  antialias: false,
  powerPreference: 'high-performance',
});
renderer.setClearColor(0xf4f6f8, 1);
viewer.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.zoomSpeed = 0.65;
controls.panSpeed = 0.75;

scene.add(new THREE.HemisphereLight(0xffffff, 0xb8c4d0, 1.8));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
keyLight.position.set(20, 35, 25);
scene.add(keyLight);

const root = new THREE.Group();
scene.add(root);

let packageBounds = new THREE.Box3();
let objectIndex = new Map();
let featureIndex = new Map();
let selectableMeshes = [];
let selectedMesh = null;
let selectedHighlight = null;
let runtimeStats = {
  renderMode: 'merged-color-buckets',
  meshCount: 0,
  renderBatchCount: 0,
  pickProxyCount: 0,
  featureCount: 0,
  tileCount: 0,
  triangleCount: 0,
  elapsedMs: 0,
  fps: 0,
  frameMs: 0,
  renderTriangles: 0,
  drawCalls: 0,
  geometryCount: 0,
  textureCount: 0,
  pixelRatio: maxIdlePixelRatio,
  qualityMode: 'adaptive-idle',
  pickLatencyMs: 0,
  metadataLatencyMs: 0,
  totalTileCount: 0,
  loadedTileCount: 0,
  loadingTileCount: 0,
  failedTileCount: 0,
  streamingMode: '',
  completeness: '',
  browserHeapMb: '',
  webglVendor: '',
  webglRenderer: '',
  webglVersion: '',
  package: null,
};
let framesSinceFpsSample = 0;
let lastFpsSampleAt = performance.now();
let lastFrameAt = performance.now();
let isInteracting = false;
let lowFpsSamples = 0;
let highFpsSamples = 0;
let restoreQualityTimer = null;
let glbTileStates = [];
let glbPackageOrigin = [0, 0, 0];
let isStreamingUpdateRunning = false;
let lastStreamingUpdateAt = 0;

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const gltfLoader = new GLTFLoader();
gltfLoader.setMeshoptDecoder(MeshoptDecoder);
const pickProxyMaterial = new THREE.MeshBasicMaterial({ visible: false });
const MAX_LOADED_GLB_TILES = 6;
const MAX_RETAINED_GLB_TILES = 18;
const REVIEW_MODE_MAX_TILES = 24;
const REVIEW_MODE_MAX_PACKAGE_BYTES = 64 * 1024 * 1024;
const TILE_UNLOAD_GRACE_MS = 4000;
const TILE_STREAM_INTERVAL_MS = 500;
const TILE_LOAD_BATCH_SIZE = 2;
const MAX_GLB_TILE_LOAD_ATTEMPTS = 3;
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

function applyPixelRatio(value, qualityMode) {
  const nextRatio = Math.max(minPixelRatio, Math.min(maxIdlePixelRatio, Number(value) || maxIdlePixelRatio));
  if (Math.abs(runtimeStats.pixelRatio - nextRatio) > 0.01) {
    renderer.setPixelRatio(nextRatio);
    const rect = viewer.getBoundingClientRect();
    renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
  }
  runtimeStats.pixelRatio = Number(nextRatio.toFixed(2));
  runtimeStats.qualityMode = qualityMode;
}

applyPixelRatio(maxIdlePixelRatio, 'adaptive-idle');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);
}

function getWebglDiagnostics() {
  try {
    const gl = renderer.getContext();
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
      renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      version: gl.getParameter(gl.VERSION),
    };
  } catch (error) {
    return {
      vendor: 'unavailable',
      renderer: 'unavailable',
      version: 'unavailable',
    };
  }
}

function getBrowserHeapMb() {
  const memory = performance.memory;
  if (!memory || !memory.usedJSHeapSize) return '';
  return Math.round(memory.usedJSHeapSize / (1024 * 1024));
}

const webglDiagnostics = getWebglDiagnostics();
runtimeStats.webglVendor = webglDiagnostics.vendor;
runtimeStats.webglRenderer = webglDiagnostics.renderer;
runtimeStats.webglVersion = webglDiagnostics.version;

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
    `<p class="kv"><span>Feature IDs</span><strong>${runtimeStats.featureCount}</strong></p>`,
    `<p class="kv"><span>Triangles</span><strong>${runtimeStats.triangleCount}</strong></p>`,
    `<p class="kv"><span>Tiles</span><strong>${runtimeStats.tileCount}</strong></p>`,
    `<p class="kv"><span>Loaded Tiles</span><strong>${runtimeStats.loadedTileCount}/${runtimeStats.totalTileCount || runtimeStats.tileCount}</strong></p>`,
    `<p class="kv"><span>Loading Tiles</span><strong>${runtimeStats.loadingTileCount}</strong></p>`,
    `<p class="kv"><span>Failed Tiles</span><strong>${runtimeStats.failedTileCount}</strong></p>`,
    `<p class="kv"><span>Load Time</span><strong>${runtimeStats.elapsedMs} ms</strong></p>`,
    `<p class="kv"><span>Streaming</span><strong>${escapeHtml(runtimeStats.streamingMode)}</strong></p>`,
    `<p class="kv"><span>Completeness</span><strong>${escapeHtml(runtimeStats.completeness)}</strong></p>`,
    `<p class="kv"><span>FPS</span><strong>${runtimeStats.fps}</strong></p>`,
    `<p class="kv"><span>Frame Time</span><strong>${runtimeStats.frameMs} ms</strong></p>`,
    `<p class="kv"><span>Draw Calls</span><strong>${runtimeStats.drawCalls}</strong></p>`,
    `<p class="kv"><span>Render Triangles</span><strong>${runtimeStats.renderTriangles}</strong></p>`,
    `<p class="kv"><span>GPU Geometries</span><strong>${runtimeStats.geometryCount}</strong></p>`,
    `<p class="kv"><span>GPU Textures</span><strong>${runtimeStats.textureCount}</strong></p>`,
    `<p class="kv"><span>Pixel Ratio</span><strong>${runtimeStats.pixelRatio}</strong></p>`,
    `<p class="kv"><span>Quality Mode</span><strong>${escapeHtml(runtimeStats.qualityMode)}</strong></p>`,
    `<p class="kv"><span>Browser Heap</span><strong>${runtimeStats.browserHeapMb === '' ? 'n/a' : `${runtimeStats.browserHeapMb} MB`}</strong></p>`,
    `<p class="kv"><span>WebGL Renderer</span><strong>${escapeHtml(runtimeStats.webglRenderer || 'unknown')}</strong></p>`,
    `<p class="kv"><span>WebGL Vendor</span><strong>${escapeHtml(runtimeStats.webglVendor || 'unknown')}</strong></p>`,
    `<p class="kv"><span>WebGL Version</span><strong>${escapeHtml(runtimeStats.webglVersion || 'unknown')}</strong></p>`,
    `<p class="kv"><span>Pick Latency</span><strong>${runtimeStats.pickLatencyMs} ms</strong></p>`,
    `<p class="kv"><span>Metadata Latency</span><strong>${runtimeStats.metadataLatencyMs} ms</strong></p>`,
    `<p class="kv"><span>Package Bytes</span><strong>${pkg.byte_size || 0}</strong></p>`,
    `<p class="kv"><span>Tile Origin(s)</span><strong>${escapeHtml(JSON.stringify(origins))}</strong></p>`,
    `<p class="kv"><span>Raw Bounds</span><strong>${escapeHtml(JSON.stringify(bounds))}</strong></p>`,
  ].join('');
}

function setMetrics(pkg, meshCount, renderBatchCount, pickProxyCount, tileCount, triangleCount, elapsedMs, featureCount = 0) {
  runtimeStats = {
    ...runtimeStats,
    package: pkg,
    meshCount,
    renderBatchCount,
    pickProxyCount,
    featureCount,
    tileCount,
    totalTileCount: pkg.tile_count || tileCount,
    loadedTileCount: tileCount,
    loadingTileCount: 0,
    failedTileCount: 0,
    streamingMode: '',
    completeness: 'Complete JSON debug package loaded.',
    triangleCount,
    elapsedMs,
  };
  renderMetrics();
}

function shouldUseReviewMode(pkg) {
  const tileCount = glbTileStates.length || Number(pkg.tile_count || 0);
  const packageBytes = Number(pkg.byte_size || 0);
  return tileCount <= REVIEW_MODE_MAX_TILES && packageBytes <= REVIEW_MODE_MAX_PACKAGE_BYTES;
}

function glbStreamingMode(pkg) {
  if (shouldUseReviewMode(pkg)) return 'review-complete';
  return `partial-active-cap-${MAX_LOADED_GLB_TILES}-retain-${MAX_RETAINED_GLB_TILES}`;
}

function glbCompletenessText(pkg, loadedCount, loadingCount, failedCount) {
  const total = glbTileStates.length || Number(pkg.tile_count || 0);
  if (!total) return 'No GLB tiles available.';
  if (failedCount > 0) {
    const loadingText = loadingCount > 0 ? `, ${loadingCount} loading` : '';
    if (shouldUseReviewMode(pkg)) return `Model INCOMPLETE: ${loadedCount}/${total} tile(s) loaded, ${failedCount} failed${loadingText}.`;
    return `Partial model visible: ${loadedCount}/${total} tile(s) retained, ${failedCount} failed${loadingText}. Some geometry is unavailable.`;
  }
  if (loadedCount >= total && loadingCount === 0) return 'Complete model loaded.';
  if (shouldUseReviewMode(pkg)) return `Loading complete model: ${loadedCount}/${total} tile(s) loaded, ${loadingCount} loading.`;
  return `Partial model visible: ${loadedCount}/${total} tile(s) retained, ${loadingCount} loading. Some geometry may be hidden until its tile is loaded.`;
}

function setGlbRuntimeMetrics(pkg, elapsedMs = runtimeStats.elapsedMs) {
  const loadedStates = glbTileStates.filter(state => state.loaded);
  const loadingStates = glbTileStates.filter(state => state.loading);
  const failedStates = glbTileStates.filter(state => state.failed);
  const loadedCount = loadedStates.length;
  const loadingCount = loadingStates.length;
  const failedCount = failedStates.length;
  runtimeStats = {
    ...runtimeStats,
    package: pkg,
    meshCount: loadedStates.reduce((total, state) => total + state.meshCount, 0),
    renderBatchCount: loadedStates.reduce((total, state) => total + state.renderBatchCount, 0),
    pickProxyCount: 0,
    featureCount: loadedStates.reduce((total, state) => total + state.featureCount, 0),
    tileCount: loadedCount,
    loadedTileCount: loadedCount,
    loadingTileCount: loadingCount,
    failedTileCount: failedCount,
    totalTileCount: glbTileStates.length,
    triangleCount: loadedStates.reduce((total, state) => total + state.triangleCount, 0),
    elapsedMs,
    streamingMode: glbStreamingMode(pkg),
    completeness: glbCompletenessText(pkg, loadedCount, loadingCount, failedCount),
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

function indexPackageObjects(pkg) {
  objectIndex = new Map();
  for (const obj of pkg.objects || []) {
    if (obj.stable_id) objectIndex.set(obj.stable_id, obj);
    if (obj.source_object_id) objectIndex.set(obj.source_object_id, obj);
  }
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
  applyPixelRatio(runtimeStats.pixelRatio, runtimeStats.qualityMode);
  renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
  camera.aspect = Math.max(1, rect.width) / Math.max(1, rect.height);
  camera.updateProjectionMatrix();
}

function beginInteraction() {
  isInteracting = true;
  if (restoreQualityTimer) {
    window.clearTimeout(restoreQualityTimer);
    restoreQualityTimer = null;
  }
  applyPixelRatio(interactionPixelRatio, 'adaptive-interaction');
  renderMetrics();
}

function endInteraction() {
  isInteracting = false;
  if (restoreQualityTimer) window.clearTimeout(restoreQualityTimer);
  restoreQualityTimer = window.setTimeout(() => {
    const restoredRatio = lowFpsSamples >= 2 ? Math.max(minPixelRatio, interactionPixelRatio) : maxIdlePixelRatio;
    applyPixelRatio(restoredRatio, lowFpsSamples >= 2 ? 'adaptive-fps-limited' : 'adaptive-idle');
    renderMetrics();
  }, 450);
}

function updateAdaptiveQuality(fps) {
  if (isInteracting) return;
  if (fps > 0 && fps < 28) {
    lowFpsSamples += 1;
    highFpsSamples = 0;
    if (lowFpsSamples >= 2 && runtimeStats.pixelRatio > minPixelRatio) {
      applyPixelRatio(runtimeStats.pixelRatio - 0.25, 'adaptive-fps-downshift');
    }
    return;
  }

  if (fps >= 50) {
    highFpsSamples += 1;
    if (highFpsSamples >= 4 && lowFpsSamples > 0) {
      lowFpsSamples = Math.max(0, lowFpsSamples - 1);
    }
    if (highFpsSamples >= 6 && runtimeStats.pixelRatio < maxIdlePixelRatio) {
      applyPixelRatio(runtimeStats.pixelRatio + 0.25, 'adaptive-fps-upshift');
      highFpsSamples = 0;
    }
  }
}

function frameScene(boundsOverride = null) {
  packageBounds = boundsOverride instanceof THREE.Box3 ? boundsOverride.clone() : new THREE.Box3().setFromObject(root);
  if (packageBounds.isEmpty()) {
    camera.position.set(8, 8, 8);
    controls.target.set(0, 0, 0);
    controls.minDistance = 0.2;
    controls.maxDistance = 500;
    controls.update();
    return;
  }

  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  packageBounds.getSize(size);
  packageBounds.getCenter(center);
  const radius = Math.max(size.x, size.y, size.z, 1);
  camera.position.set(center.x + radius * 1.4, center.y + radius * 1.0, center.z + radius * 1.4);
  controls.minDistance = Math.max(radius * 0.02, 0.25);
  controls.maxDistance = Math.max(radius * 25, 100);
  camera.near = Math.max(controls.minDistance / 100, 0.01);
  camera.far = Math.max(controls.maxDistance * 4, 1000);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function sourceBoundsHalfExtents(rawBounds, scaleToM = 1.0) {
  if (!rawBounds) return new THREE.Vector3(1, 1, 1);
  const scale = Number(scaleToM || 1);
  const halfX = Math.max(Math.abs(Number(rawBounds.max_x || 0) - Number(rawBounds.min_x || 0)) * scale / 2, 0.001);
  const halfY = Math.max(Math.abs(Number(rawBounds.max_z || 0) - Number(rawBounds.min_z || 0)) * scale / 2, 0.001);
  const halfZ = Math.max(Math.abs(Number(rawBounds.max_y || 0) - Number(rawBounds.min_y || 0)) * scale / 2, 0.001);
  return new THREE.Vector3(halfX, halfY, halfZ);
}

function approximatePackageBounds(pkg) {
  const scaleToM = pkg.metadata?.unit_metadata?.render_coordinate_scale_to_m || 1;
  const half = sourceBoundsHalfExtents(pkg.bounds || {}, scaleToM);
  return new THREE.Box3(half.clone().multiplyScalar(-1), half);
}

function tileCenterForState(tile) {
  const origin = Array.isArray(tile.rtc_origin) ? tile.rtc_origin : glbPackageOrigin;
  return new THREE.Vector3(
    Number(origin[0] || 0) - Number(glbPackageOrigin[0] || 0),
    Number(origin[1] || 0) - Number(glbPackageOrigin[1] || 0),
    Number(origin[2] || 0) - Number(glbPackageOrigin[2] || 0),
  );
}

function tileRadiusForState(pkg, tile) {
  const scaleToM = pkg.metadata?.unit_metadata?.render_coordinate_scale_to_m || 1;
  return sourceBoundsHalfExtents(tile.bounds || pkg.bounds || {}, scaleToM).length();
}

function disposeObject3D(object) {
  object.traverse(node => {
    if (node.geometry) node.geometry.dispose();
    if (node.material) {
      if (Array.isArray(node.material)) {
        node.material.forEach(material => material.dispose?.());
      } else {
        node.material.dispose?.();
      }
    }
  });
}

function prepareGlbTileStates(pkg) {
  glbPackageOrigin = Array.isArray(pkg.metadata?.rtc_origin_render_xyz)
    ? pkg.metadata.rtc_origin_render_xyz
    : [0, 0, 0];
  glbTileStates = (pkg.tiles || []).map(tile => {
    const center = tileCenterForState(tile);
    return {
      tile,
      key: tile.tile_id || String(tile.id),
      center,
      radius: tileRadiusForState(pkg, tile),
      loaded: false,
      loading: false,
      failed: false,
      loadAttempts: 0,
      lastError: '',
      group: null,
      meshCount: 0,
      renderBatchCount: 0,
      triangleCount: 0,
      featureCount: 0,
      lastVisibleAt: 0,
      lastActiveAt: 0,
    };
  });
}

function glbFrustum() {
  camera.updateMatrixWorld();
  const matrix = new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  return new THREE.Frustum().setFromProjectionMatrix(matrix);
}

function activeTileStates(pkg) {
  if (shouldUseReviewMode(pkg)) return glbTileStates;

  const frustum = glbFrustum();
  const target = controls.target || new THREE.Vector3();
  const now = performance.now();
  const scored = glbTileStates.map(state => {
    const visible = frustum.intersectsSphere(new THREE.Sphere(state.center, state.radius));
    if (visible) state.lastVisibleAt = now;
    return {
      state,
      visible,
      distance: state.center.distanceTo(target),
    };
  });

  const visibleStates = scored
    .filter(item => item.visible)
    .sort((a, b) => a.distance - b.distance)
    .map(item => item.state);
  const active = visibleStates.length
    ? visibleStates.slice(0, MAX_LOADED_GLB_TILES)
    : scored.sort((a, b) => a.distance - b.distance).slice(0, 1).map(item => item.state);
  active.forEach(state => {
    state.lastActiveAt = now;
  });
  return active;
}

async function loadGlbTileState(state, pkg) {
  if (state.loaded || state.loading || state.failed) return;
  state.loading = true;
  state.loadAttempts += 1;
  state.lastError = '';
  setGlbRuntimeMetrics(pkg);
  const tile = state.tile;
  const blobUrl = tile.blob_url || tile.url;
  if (!blobUrl) {
    state.failed = true;
    state.lastError = 'missing blob URL';
    state.loading = false;
    setGlbRuntimeMetrics(pkg);
    return;
  }

  try {
    if (tile.metadata_url) {
      try {
        const sidecarResponse = await fetch(tile.metadata_url);
        if (sidecarResponse.ok) {
          const sidecar = await sidecarResponse.json();
          const objectFeatures = Array.isArray(sidecar.object_features) ? sidecar.object_features : [];
          state.featureCount = objectFeatures.length;
          for (const feature of objectFeatures) {
            const featureId = Number(feature.feature_id);
            if (!Number.isFinite(featureId)) continue;
            const objectSummary = objectIndex.get(feature.stable_id) || objectIndex.get(feature.source_object_id);
            featureIndex.set(featureId, {
              ...feature,
              objectSummary: objectSummary || null,
            });
          }
        }
      } catch (error) {
        // Sidecar metrics are useful, but GLB rendering should not depend on them.
      }
    }

    const gltf = await gltfLoader.loadAsync(blobUrl);
    const tileRoot = gltf.scene || new THREE.Group();
    tileRoot.position.copy(state.center);
    tileRoot.userData.tileKey = state.key;
    let meshCount = 0;
    let renderBatchCount = 0;
    let triangleCount = 0;
    tileRoot.traverse(node => {
      if (!node.isMesh) return;
      meshCount += 1;
      renderBatchCount += 1;
      node.userData = {
        ...(node.userData || {}),
        packageFormat: 'GLB',
        tileKey: state.key,
      };
      selectableMeshes.push(node);
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
    state.group = tileRoot;
    state.meshCount = meshCount;
    state.renderBatchCount = renderBatchCount;
    state.triangleCount = triangleCount;
    state.loaded = true;
    state.failed = false;
    packageBounds.union(new THREE.Box3().setFromObject(tileRoot));
  } catch (error) {
    state.lastError = error.message || 'unknown error';
    if (state.loadAttempts >= MAX_GLB_TILE_LOAD_ATTEMPTS) {
      state.failed = true;
      setStatus(`GLB tile ${state.key} failed after ${state.loadAttempts} attempt(s): ${state.lastError}`);
    } else {
      setStatus(`Unable to load GLB tile ${state.key}; retry ${state.loadAttempts}/${MAX_GLB_TILE_LOAD_ATTEMPTS}: ${state.lastError}`);
    }
  } finally {
    state.loading = false;
    setGlbRuntimeMetrics(pkg);
  }
}

function unloadGlbTileState(state, pkg) {
  if (!state.loaded || !state.group) return;
  root.remove(state.group);
  disposeObject3D(state.group);
  selectableMeshes = selectableMeshes.filter(mesh => mesh.userData?.tileKey !== state.key);
  state.group = null;
  state.loaded = false;
  state.meshCount = 0;
  state.renderBatchCount = 0;
  state.triangleCount = 0;
  setGlbRuntimeMetrics(pkg);
}

function unloadOverflowGlbTiles(active, pkg) {
  if (shouldUseReviewMode(pkg)) return;
  const loadedStates = glbTileStates.filter(state => state.loaded);
  if (loadedStates.length <= MAX_RETAINED_GLB_TILES) return;

  const activeKeys = new Set(active.map(state => state.key));
  const now = performance.now();
  const candidates = loadedStates
    .filter(state => !activeKeys.has(state.key) && now - (state.lastActiveAt || 0) >= TILE_UNLOAD_GRACE_MS)
    .sort((a, b) => (a.lastActiveAt || 0) - (b.lastActiveAt || 0));

  for (const state of candidates) {
    if (glbTileStates.filter(item => item.loaded).length <= MAX_RETAINED_GLB_TILES) break;
    unloadGlbTileState(state, pkg);
  }
}

async function updateGlbTileStreaming(pkg, force = false) {
  if (!glbTileStates.length || isStreamingUpdateRunning) return;
  const now = performance.now();
  if (!force && now - lastStreamingUpdateAt < TILE_STREAM_INTERVAL_MS) return;
  lastStreamingUpdateAt = now;
  isStreamingUpdateRunning = true;
  try {
    const active = activeTileStates(pkg);
    const activeKeys = new Set(active.map(state => state.key));
    unloadOverflowGlbTiles(active, pkg);
    const candidates = glbTileStates.filter(state => (
      activeKeys.has(state.key)
      && !state.loaded
      && !state.loading
      && !state.failed
      && state.loadAttempts < MAX_GLB_TILE_LOAD_ATTEMPTS
    ));
    const loadBatchSize = shouldUseReviewMode(pkg) ? candidates.length : TILE_LOAD_BATCH_SIZE;
    for (const state of candidates.slice(0, loadBatchSize)) {
      await loadGlbTileState(state, pkg);
    }
    const loadedCount = glbTileStates.filter(state => state.loaded).length;
    const loadingCount = glbTileStates.filter(state => state.loading).length;
    const failedCount = glbTileStates.filter(state => state.failed).length;
    if (shouldUseReviewMode(pkg) && loadedCount === glbTileStates.length && loadingCount === 0 && failedCount === 0 && !pkg.__plant3dReviewFramed) {
      pkg.__plant3dReviewFramed = true;
      frameScene();
    }
    setStatus(`${glbCompletenessText(pkg, loadedCount, loadingCount, failedCount)} Feature-ID picking enabled; BVH acceleration deferred.`);
  } finally {
    isStreamingUpdateRunning = false;
  }
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
  indexPackageObjects(pkg);
  featureIndex = new Map();

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
  indexPackageObjects(pkg);
  featureIndex = new Map();
  selectableMeshes = [];
  prepareGlbTileStates(pkg);
  const approximateBounds = approximatePackageBounds(pkg);
  frameScene(approximateBounds);
  const elapsedMs = Math.round(performance.now() - started);
  setGlbRuntimeMetrics(pkg, elapsedMs);
  setStatus(`Prepared GLB tile stream with ${glbTileStates.length} tile(s) in ${elapsedMs} ms. Loading visible tiles...`);
  await updateGlbTileStreaming(pkg, true);
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

function featureIdFromHit(hit) {
  const geometry = hit.object?.geometry;
  if (!geometry || !Number.isInteger(hit.faceIndex)) return null;
  const featureAttribute = geometry.getAttribute('_FEATURE_ID_0') || geometry.getAttribute('_feature_id_0');
  if (!featureAttribute) return null;

  const firstVertex = hit.faceIndex * 3;
  const vertexIndex = geometry.index ? geometry.index.getX(firstVertex) : firstVertex;
  const featureId = featureAttribute.getX(vertexIndex);
  return Number.isFinite(featureId) ? Math.round(featureId) : null;
}

async function showGlbFeatureSelection(hit) {
  clearSelection();
  const featureId = featureIdFromHit(hit);
  if (!featureId || !featureIndex.has(featureId)) {
    if (selectionEl) selectionEl.textContent = 'No feature metadata was found for this GLB face.';
    return;
  }

  const feature = featureIndex.get(featureId);
  const objectSummary = feature.objectSummary;
  const baseRows = [
    `<p class="kv"><span>Feature ID</span><strong>${featureId}</strong></p>`,
    `<p class="kv"><span>Stable ID</span><strong>${escapeHtml(feature.stable_id || '')}</strong></p>`,
    `<p class="kv"><span>Type</span><strong>${escapeHtml(feature.object_type || objectSummary?.object_type || '')}</strong></p>`,
    `<p class="kv"><span>Source Object</span><strong>${escapeHtml(feature.source_object_id || objectSummary?.source_object_id || '')}</strong></p>`,
  ];
  if (!selectionEl) return;
  selectionEl.innerHTML = baseRows.join('') + '<p class="meta">Loading indexed metadata...</p>';

  if (!objectSummary?.url) {
    selectionEl.innerHTML = baseRows.join('') + '<p class="meta">Feature ID is present, but no indexed object URL is available.</p>';
    return;
  }

  try {
    const metadataStarted = performance.now();
    const response = await fetch(objectSummary.url);
    if (!response.ok) throw new Error(`Metadata request failed: ${response.status}`);
    const data = await response.json();
    runtimeStats.metadataLatencyMs = Math.round(performance.now() - metadataStarted);
    renderMetrics();
    selectionEl.innerHTML = [
      `<p class="kv"><span>Feature ID</span><strong>${featureId}</strong></p>`,
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
  if (hits[0].object?.userData?.packageFormat === 'GLB') {
    showGlbFeatureSelection(hits[0]);
    return;
  }
  showSelection(hits[0].object);
}

function animate() {
  const now = performance.now();
  runtimeStats.frameMs = Number((now - lastFrameAt).toFixed(1));
  lastFrameAt = now;
  controls.update();
  if (runtimeStats.package?.package_format === 'GLB') {
    updateGlbTileStreaming(runtimeStats.package);
  }
  renderer.render(scene, camera);
  runtimeStats.drawCalls = renderer.info.render.calls;
  runtimeStats.renderTriangles = renderer.info.render.triangles;
  runtimeStats.geometryCount = renderer.info.memory.geometries;
  runtimeStats.textureCount = renderer.info.memory.textures;
  runtimeStats.browserHeapMb = getBrowserHeapMb();
  framesSinceFpsSample += 1;
  if (now - lastFpsSampleAt >= 1000) {
    runtimeStats.fps = Math.round((framesSinceFpsSample * 1000) / (now - lastFpsSampleAt));
    framesSinceFpsSample = 0;
    lastFpsSampleAt = now;
    updateAdaptiveQuality(runtimeStats.fps);
    renderMetrics();
  }
  requestAnimationFrame(animate);
}

window.addEventListener('resize', resize);
controls.addEventListener('start', beginInteraction);
controls.addEventListener('end', endInteraction);
if (resetBtn) resetBtn.addEventListener('click', () => frameScene());
renderer.domElement.addEventListener('click', pick);
resize();
animate();

loadPackage().catch(error => {
  setStatus(error.message || 'Unable to load package.');
});
