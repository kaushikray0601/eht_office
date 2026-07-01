import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const viewer = document.getElementById('viewer');
const statusEl = document.getElementById('viewerStatus');
const resetBtn = document.getElementById('resetViewBtn');
const fitSelectionBtn = document.getElementById('fitSelectionBtn');
const clearSelectionBtn = document.getElementById('clearSelectionBtn');
const metricsEl = document.getElementById('runtimeMetrics');
const selectionEl = document.getElementById('selectionPanel');
const hierarchyContent = document.getElementById('hierarchy-content');
const hierarchySelectionCount = document.getElementById('hierarchySelectionCount');
const hierarchySearchInput = document.getElementById('hierarchySearchInput');
const hierarchySearchStatus = document.getElementById('hierarchySearchStatus');
const searchFocusBtn = document.getElementById('searchFocusBtn');
const searchIsolateBtn = document.getElementById('searchIsolateBtn');
const searchClearBtn = document.getElementById('searchClearBtn');
const ehtToolPalette = document.getElementById('ehtToolPalette');
const ehtToolStatus = document.getElementById('ehtToolStatus');
const ehtPaletteToggleBtn = document.getElementById('ehtPaletteToggleBtn');
const ehtSelectToolBtn = document.getElementById('ehtSelectToolBtn');
const ehtRouteControls = document.getElementById('ehtRouteControls');
const ehtFinishRouteBtn = document.getElementById('ehtFinishRouteBtn');
const ehtCancelRouteBtn = document.getElementById('ehtCancelRouteBtn');
const ehtSaveLayerBtn = document.getElementById('ehtSaveLayerBtn');
const ehtUndoBtn = document.querySelector('.eht-undo-btn');
const ehtDraftList = document.getElementById('ehtDraftList');
const DRAFT_PARAMETER_FIELDS = [
  { key: 'label', label: 'Label', type: 'text' },
  { key: 'width_m', label: 'Width m', type: 'number', step: '0.05' },
  { key: 'height_m', label: 'Height m', type: 'number', step: '0.05' },
  { key: 'depth_m', label: 'Depth m', type: 'number', step: '0.05' },
  { key: 'weight_kg', label: 'Weight kg', type: 'number', step: '0.1' },
  { key: 'voltage_v', label: 'Voltage V', type: 'number', step: '1' },
  { key: 'power_w', label: 'Power W', type: 'number', step: '1' },
  { key: 'circuit_ref', label: 'Circuit ref', type: 'text' },
  { key: 'cable_type', label: 'Cable type', type: 'text' },
];

const devicePixelRatio = window.devicePixelRatio || 1;
const maxIdlePixelRatio = Math.max(0.75, Math.min(devicePixelRatio, 1.5));
const interactionPixelRatio = Math.max(0.75, Math.min(maxIdlePixelRatio, 1.0));
const minPixelRatio = Math.min(interactionPixelRatio, 0.75);

const renderer = new THREE.WebGLRenderer({
  antialias: true,
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
const ehtDraftGroup = new THREE.Group();
scene.add(ehtDraftGroup);

let packageBounds = new THREE.Box3();
let objectIndex = new Map();
let objectById = new Map();
let featureIndex = new Map();
let featureSpanIndex = new Map();
let selectableMeshes = [];
let packageObjectRows = [];
let hierarchySearchMatches = new Set();
let selectedMesh = null;
let selectedHighlight = null;
let hierarchySelectedObjectId = null;
let activeEhtTool = '';
let pendingRoutePoints = [];
let ehtDraftElements = [];
let selectedDraftId = '';
let movingDraftId = '';
let hiddenEhtDraftIds = new Set();
let hiddenEhtTypes = new Set();
let collapsedEhtTypes = new Set();
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
  antialiasing: 'MSAA',
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
const EHT_TOOL_DEFS = {
  distribution_board: { label: 'Distribution Board', kind: 'point', color: 0x7c3aed, defaults: { width_m: 0.8, height_m: 1.8, depth_m: 0.35, weight_kg: 120, voltage_v: 415, power_w: 0, circuit_ref: '', cable_type: '' } },
  junction_box: { label: 'Junction Box', kind: 'point', color: 0x2563eb, defaults: { width_m: 0.45, height_m: 0.45, depth_m: 0.25, weight_kg: 12, voltage_v: 230, power_w: 0, circuit_ref: '', cable_type: '' } },
  isolator: { label: 'Isolator', kind: 'point', color: 0x0f766e, defaults: { width_m: 0.35, height_m: 0.45, depth_m: 0.22, weight_kg: 8, voltage_v: 415, power_w: 0, circuit_ref: '', cable_type: '' } },
  rtd: { label: 'RTD', kind: 'point', color: 0xdc2626, defaults: { width_m: 0.18, height_m: 0.18, depth_m: 0.12, weight_kg: 1, voltage_v: 24, power_w: 0, circuit_ref: '', cable_type: '' } },
  end_termination: { label: 'End Termination', kind: 'point', color: 0xbe123c, defaults: { width_m: 0.25, height_m: 0.25, depth_m: 0.15, weight_kg: 2, voltage_v: 230, power_w: 0, circuit_ref: '', cable_type: '' } },
  pipe_strap: { label: 'Pipe Strap', kind: 'point', color: 0x65a30d, defaults: { width_m: 0.15, height_m: 0.08, depth_m: 0.08, weight_kg: 0.2, voltage_v: '', power_w: '', circuit_ref: '', cable_type: '' } },
  tracer_sr: { label: 'SR Tracer', kind: 'route', color: 0xf59e0b, defaults: { width_m: '', height_m: '', depth_m: '', weight_kg: '', voltage_v: 230, power_w: 30, circuit_ref: '', cable_type: 'SR' } },
  tracer_mi: { label: 'MI Tracer', kind: 'route', color: 0xea580c, defaults: { width_m: '', height_m: '', depth_m: '', weight_kg: '', voltage_v: 230, power_w: 60, circuit_ref: '', cable_type: 'MI' } },
  cold_cable: { label: 'Cold Cable', kind: 'route', color: 0x0284c7, defaults: { width_m: '', height_m: '', depth_m: '', weight_kg: '', voltage_v: 230, power_w: 0, circuit_ref: '', cable_type: 'Cold cable' } },
};
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

function kvRow(label, value) {
  if (value === null || value === undefined || value === '') return '';
  return `<p class="kv"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></p>`;
}

function formatDimension(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  if (Math.abs(number) >= 100) return number.toFixed(1);
  if (Math.abs(number) >= 10) return number.toFixed(2);
  return number.toFixed(3);
}

function dimensionsText(summary) {
  const dimensions = summary?.dimensions || {};
  const unit = summary?.dimension_unit || 'm';
  const x = formatDimension(dimensions.x);
  const y = formatDimension(dimensions.y);
  const z = formatDimension(dimensions.z);
  if (!x && !y && !z) return '';
  return `X ${x || '-'} ${unit}, Y ${y || '-'} ${unit}, Z ${z || '-'} ${unit}`;
}

function metadataDetails(data) {
  const metadata = data?.metadata || {};
  const bounds = data?.bounds || {};
  const hasMetadata = Object.keys(metadata).length > 0;
  const hasBounds = Object.keys(bounds).length > 0;
  if (!hasMetadata && !hasBounds) return '';
  return [
    '<details>',
    '<summary>Raw metadata</summary>',
    hasBounds ? `<p class="kv"><span>Bounds</span><strong>${escapeHtml(JSON.stringify(bounds))}</strong></p>` : '',
    hasMetadata ? `<p class="kv"><span>Metadata</span><strong>${escapeHtml(JSON.stringify(metadata))}</strong></p>` : '',
    '</details>',
  ].join('');
}

function objectDisplayLabel(obj) {
  const summary = obj?.selection_summary || {};
  return summary.display_label || obj?.tag || obj?.line_id || obj?.source_object_id || obj?.stable_id || `Object ${obj?.id || ''}`.trim();
}

function objectGroupLabel(obj) {
  const summary = obj?.selection_summary || {};
  return summary.hierarchy_group || obj?.object_type || 'Ungrouped';
}

function objectSearchText(obj) {
  const summary = obj?.selection_summary || {};
  return [
    objectDisplayLabel(obj),
    obj?.object_type,
    obj?.tag,
    obj?.line_id,
    obj?.stable_id,
    obj?.source_object_id,
    summary.name,
    summary.hierarchy_group,
    Array.isArray(summary.spatial_path) ? summary.spatial_path.join(' ') : '',
  ].join(' ').toLowerCase();
}

function collapseButton(label, expanded = true) {
  return `<button type="button" class="p3d-tree-collapse" aria-label="${escapeHtml(label)}">${expanded ? '▾' : '▸'}</button>`;
}

function renderHierarchy(pkg) {
  packageObjectRows = Array.isArray(pkg.objects) ? pkg.objects : [];
  if (!hierarchyContent) return;
  if (!packageObjectRows.length) {
    hierarchyContent.innerHTML = '<div class="meta">No indexed objects found.</div>';
    renderDraftList();
    return;
  }

  const byGroup = new Map();
  for (const obj of packageObjectRows) {
    const group = objectGroupLabel(obj);
    if (!byGroup.has(group)) byGroup.set(group, []);
    byGroup.get(group).push(obj);
  }

  const sourceLabel = pkg.source_display_name || `Source ${pkg.source_model_id || ''}`.trim() || 'Source Model';
  const groups = Array.from(byGroup.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  hierarchyContent.innerHTML = `
    <div class="p3d-tree-node hierarchy-file" data-file="${escapeHtml(sourceLabel)}">
      <div class="p3d-tree-row">
        ${collapseButton(`Collapse ${sourceLabel}`)}
        <span class="p3d-tree-label" title="${escapeHtml(sourceLabel)}">${escapeHtml(sourceLabel)}</span>
        <span class="p3d-tree-count">${packageObjectRows.length}</span>
      </div>
      <div class="p3d-tree-children">
        ${groups.map(([group, objects]) => {
          const sorted = objects.slice().sort((a, b) => objectDisplayLabel(a).localeCompare(objectDisplayLabel(b)));
          return `
            <div class="p3d-tree-node hierarchy-group" data-file="${escapeHtml(sourceLabel)}" data-group="${escapeHtml(group)}">
              <div class="p3d-tree-row">
                ${collapseButton(`Collapse ${group}`)}
                <span class="p3d-tree-label" title="${escapeHtml(group)}">${escapeHtml(group)}</span>
                <span class="p3d-tree-count">${sorted.length}</span>
              </div>
              <div class="p3d-tree-children">
                ${sorted.map(obj => `
                  <button type="button" class="p3d-tree-leaf hierarchy-leaf-row" data-object-id="${escapeHtml(obj.id)}" data-file="${escapeHtml(sourceLabel)}" data-group="${escapeHtml(group)}" data-search-text="${escapeHtml(objectSearchText(obj))}" title="${escapeHtml(objectDisplayLabel(obj))}">
                    <span class="p3d-tree-label">${escapeHtml(objectDisplayLabel(obj))}</span>
                  </button>
                `).join('')}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
  bindHierarchyEvents();
  updateHierarchyCounters();
  renderDraftList();
}

function updateHierarchyCounters() {
  const leafRows = Array.from(document.querySelectorAll('.hierarchy-leaf-row'));
  const visibleCount = leafRows.filter(row => !row.classList.contains('p3d-tree-hidden')).length;
  if (hierarchySelectionCount) {
    hierarchySelectionCount.textContent = leafRows.length ? `${visibleCount}/${leafRows.length} listed` : 'No assets';
  }
}

function currentHierarchyQuery() {
  return hierarchySearchInput ? hierarchySearchInput.value.trim().toLowerCase() : '';
}

function applyHierarchySearch() {
  const query = currentHierarchyQuery();
  let matchCount = 0;
  hierarchySearchMatches = new Set();
  document.querySelectorAll('.hierarchy-leaf-row').forEach(row => {
    const visible = !query || String(row.dataset.searchText || '').includes(query);
    row.classList.toggle('p3d-tree-hidden', !visible);
    if (visible && query) {
      matchCount += 1;
      hierarchySearchMatches.add(row.dataset.objectId);
    }
  });
  document.querySelectorAll('.hierarchy-group').forEach(group => {
    const hasVisibleLeaves = Array.from(group.querySelectorAll('.hierarchy-leaf-row')).some(row => !row.classList.contains('p3d-tree-hidden'));
    group.classList.toggle('p3d-tree-hidden', !hasVisibleLeaves);
  });
  document.querySelectorAll('.hierarchy-file').forEach(file => {
    const hasVisibleLeaves = Array.from(file.querySelectorAll('.hierarchy-leaf-row')).some(row => !row.classList.contains('p3d-tree-hidden'));
    file.classList.toggle('p3d-tree-hidden', !hasVisibleLeaves);
  });
  document.querySelectorAll('.eht-hierarchy-row').forEach(row => {
    const visible = !query || String(row.dataset.searchText || '').includes(query);
    row.classList.toggle('p3d-tree-hidden', !visible);
    if (visible && query) matchCount += 1;
  });
  document.querySelectorAll('.eht-type-group').forEach(group => {
    const hasVisibleLeaves = Array.from(group.querySelectorAll('.eht-hierarchy-row')).some(row => !row.classList.contains('p3d-tree-hidden'));
    group.classList.toggle('p3d-tree-hidden', !hasVisibleLeaves);
  });
  if (hierarchySearchStatus) {
    hierarchySearchStatus.textContent = query ? `${matchCount} match${matchCount === 1 ? '' : 'es'}` : 'Search the current hierarchy';
  }
  updateHierarchyCounters();
}

function sourceBoundsToRenderBox(bounds) {
  if (!bounds || Object.keys(bounds).length === 0) return null;
  const origin = Array.isArray(glbPackageOrigin) ? glbPackageOrigin : [0, 0, 0];
  const minX = Number(bounds.min_x);
  const maxX = Number(bounds.max_x);
  const minY = Number(bounds.min_y);
  const maxY = Number(bounds.max_y);
  const minZ = Number(bounds.min_z);
  const maxZ = Number(bounds.max_z);
  if (![minX, maxX, minY, maxY, minZ, maxZ].every(Number.isFinite)) return null;
  const min = new THREE.Vector3(minX - origin[0], minZ - origin[1], minY - origin[2]);
  const max = new THREE.Vector3(maxX - origin[0], maxZ - origin[1], maxY - origin[2]);
  return new THREE.Box3().setFromPoints([min, max]);
}

async function showObjectMetadataFromSummary(obj, featureId = null) {
  if (!selectionEl || !obj) return;
  hierarchySelectedObjectId = obj.id;
  selectionEl.innerHTML = selectionDetailsHtml({ ...obj, selection_summary: obj.selection_summary || {} }, featureId);
  if (!obj.url) return;
  try {
    const metadataStarted = performance.now();
    const response = await fetch(obj.url);
    if (!response.ok) throw new Error(`Metadata request failed: ${response.status}`);
    const data = await response.json();
    runtimeStats.metadataLatencyMs = Math.round(performance.now() - metadataStarted);
    renderMetrics();
    selectionEl.innerHTML = selectionDetailsHtml(data, featureId);
  } catch (error) {
    selectionEl.innerHTML += `<p class="meta">${escapeHtml(error.message || 'Unable to load metadata.')}</p>`;
  }
}

function focusObjectFromHierarchy(objectId, { filterList = false } = {}) {
  const obj = objectById.get(Number(objectId)) || objectById.get(String(objectId));
  if (!obj) return;
  if (filterList && hierarchySearchInput) {
    hierarchySearchInput.value = objectDisplayLabel(obj);
    applyHierarchySearch();
  }
  clearSelection();
  const bounds = sourceBoundsToRenderBox(obj.bounds);
  if (bounds && !bounds.isEmpty()) frameBounds(bounds);
  showObjectMetadataFromSummary(obj);
}

function firstHierarchyMatch() {
  const query = currentHierarchyQuery();
  if (!query) return null;
  return Array.from(document.querySelectorAll('.hierarchy-leaf-row'))
    .find(row => !row.classList.contains('p3d-tree-hidden'));
}

function bindHierarchyEvents() {
  document.querySelectorAll('.p3d-tree-collapse').forEach(button => {
    button.addEventListener('click', event => {
      event.preventDefault();
      const node = button.closest('.p3d-tree-node');
      const children = node?.querySelector('.p3d-tree-children');
      if (!children) return;
      const collapsed = children.classList.toggle('p3d-tree-hidden');
      button.textContent = collapsed ? '▸' : '▾';
    });
  });
  document.querySelectorAll('.hierarchy-leaf-row').forEach(row => {
    row.addEventListener('click', event => {
      event.preventDefault();
      focusObjectFromHierarchy(row.dataset.objectId, { filterList: false });
    });
    row.addEventListener('dblclick', () => focusObjectFromHierarchy(row.dataset.objectId, { filterList: true }));
  });
  applyHierarchySearch();
}

function ehtDef(tool) {
  return EHT_TOOL_DEFS[tool] || EHT_TOOL_DEFS.junction_box;
}

function setEhtStatus(message) {
  if (ehtToolStatus) ehtToolStatus.textContent = message;
}

function setActiveEhtTool(tool) {
  activeEhtTool = tool || '';
  if (activeEhtTool) movingDraftId = '';
  document.querySelectorAll('.eht-tool-btn').forEach(button => {
    button.classList.toggle('p3d-tool-active', button.dataset.ehtTool === activeEhtTool);
  });
  if (ehtSelectToolBtn) {
    ehtSelectToolBtn.classList.toggle('p3d-button-primary', !activeEhtTool);
  }
  const def = activeEhtTool ? ehtDef(activeEhtTool) : null;
  if (ehtRouteControls) {
    ehtRouteControls.classList.toggle('p3d-hidden', !def || def.kind !== 'route');
  }
  pendingRoutePoints = [];
  setEhtStatus(def ? `${def.label}: click the model to place ${def.kind === 'route' ? 'route points' : 'an element'}.` : 'Select a tool, then click the model.');
}

function updateUndoState() {
  if (ehtUndoBtn) ehtUndoBtn.disabled = ehtDraftElements.length === 0;
}

function selectedDraftElement() {
  return selectedDraftId ? ehtDraftElements.find(element => element.id === selectedDraftId) || null : null;
}

function draftDefaults(type, sequence) {
  const def = ehtDef(type);
  return {
    label: `${def.label} ${sequence}`,
    ...(def.defaults || {}),
  };
}

function numericOrBlank(value) {
  if (value === '' || value === null || value === undefined) return '';
  const number = Number(value);
  return Number.isFinite(number) ? number : '';
}

function draftParamValue(params, key) {
  return params && Object.prototype.hasOwnProperty.call(params, key) ? params[key] : '';
}

function draftParameterRows(element) {
  const params = element.parameters || {};
  return DRAFT_PARAMETER_FIELDS.map(field => {
    const value = draftParamValue(params, field.key);
    const attrs = [
      `name="${escapeHtml(field.key)}"`,
      `type="${escapeHtml(field.type)}"`,
      `value="${escapeHtml(value)}"`,
      field.step ? `step="${escapeHtml(field.step)}"` : '',
    ].filter(Boolean).join(' ');
    return `
      <label class="p3d-form-row">
        <span>${escapeHtml(field.label)}</span>
        <input ${attrs}>
      </label>
    `;
  }).join('');
}

function draftPositionText(element) {
  const point = element.points?.[0] || [];
  if (!point.length) return '';
  return point.map(value => formatDimension(value)).join(', ');
}

function draftLength(element) {
  if (!Array.isArray(element.points) || element.points.length < 2) return 0;
  let total = 0;
  for (let index = 1; index < element.points.length; index += 1) {
    const previous = new THREE.Vector3(...element.points[index - 1]);
    const current = new THREE.Vector3(...element.points[index]);
    total += previous.distanceTo(current);
  }
  return total;
}

function applyPointDimensions(element) {
  if (!element || element.kind !== 'point' || !element.object3d) return;
  const params = element.parameters || {};
  const base = 0.45;
  const width = Math.max(Number(params.width_m) || base, 0.05);
  const height = Math.max(Number(params.height_m) || base, 0.05);
  const depth = Math.max(Number(params.depth_m) || base, 0.05);
  element.object3d.scale.set(width / base, height / base, depth / base);
  element.object3d.updateMatrixWorld(true);
}

function rebuildRouteGeometry(element) {
  if (!element || element.kind !== 'route' || !element.object3d) return;
  const points = (element.points || []).map(point => new THREE.Vector3(...point));
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  element.object3d.geometry?.dispose?.();
  element.object3d.geometry = geometry;
  element.object3d.computeLineDistances?.();
}

function selectDraftElement(element, { frame = false } = {}) {
  if (!element) return;
  clearSelection({ keepDraft: true });
  selectedDraftId = element.id;
  movingDraftId = movingDraftId === element.id ? movingDraftId : '';
  setSelectionActionsEnabled(true);
  renderDraftSelectionPanel(element);
  if (frame) {
    const bounds = new THREE.Box3().setFromObject(element.object3d);
    frameBounds(bounds);
  }
  renderDraftList();
}

function renderDraftSelectionPanel(element = selectedDraftElement()) {
  if (!selectionEl || !element) return;
  const def = ehtDef(element.type);
  const isMoving = movingDraftId === element.id;
  selectionEl.innerHTML = [
    kvRow('Draft EHT Element', draftLabel(element)),
    kvRow('Type', def.label),
    kvRow('Mode', element.kind),
    kvRow('Points', element.points.length),
    element.kind === 'route' ? kvRow('Route Length', `${formatDimension(draftLength(element))} m`) : kvRow('Position', draftPositionText(element)),
    `<form id="ehtParameterForm" class="p3d-form" data-draft-id="${escapeHtml(element.id)}">`,
    draftParameterRows(element),
    '<div class="p3d-toolbar p3d-form-actions">',
    '<button type="submit" class="p3d-button-primary">Apply Parameters</button>',
    `<button type="button" id="ehtMoveSelectedBtn" class="${isMoving ? 'p3d-button-primary' : ''}">${isMoving ? 'Click New Position' : 'Move'}</button>`,
    '<button type="button" id="ehtDeleteSelectedBtn">Delete</button>',
    '</div>',
    '</form>',
    '<p class="meta">Draft overlay only; persistence is a later EHT layer pass.</p>',
  ].join('');
}

function updateDraftParametersFromForm(form) {
  const element = ehtDraftElements.find(item => item.id === form?.dataset?.draftId);
  if (!element) return;
  const next = { ...(element.parameters || {}) };
  for (const field of DRAFT_PARAMETER_FIELDS) {
    const input = form.elements[field.key];
    if (!input) continue;
    next[field.key] = field.type === 'number' ? numericOrBlank(input.value) : input.value.trim();
  }
  element.parameters = next;
  applyPointDimensions(element);
  renderDraftList();
  renderDraftSelectionPanel(element);
  setEhtStatus(`${draftLabel(element)} parameters updated. Draft is not persisted yet.`);
}

function deleteDraftElement(element) {
  if (!element) return;
  ehtDraftElements = ehtDraftElements.filter(item => item.id !== element.id);
  hiddenEhtDraftIds.delete(element.id);
  element.object3d.parent?.remove(element.object3d);
  disposeObject3D(element.object3d);
  if (selectedDraftId === element.id) selectedDraftId = '';
  if (movingDraftId === element.id) movingDraftId = '';
  clearSelection();
  if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
  renderDraftList();
  setEhtStatus(`${draftLabel(element)} deleted.`);
}

function moveDraftElementTo(element, point) {
  if (!element || !point) return;
  const nextPoint = point.clone();
  if (element.kind === 'point') {
    element.object3d.position.copy(nextPoint);
    element.points = [nextPoint.toArray()];
  } else if (element.kind === 'route' && element.points.length) {
    const first = new THREE.Vector3(...element.points[0]);
    const delta = nextPoint.sub(first);
    element.points = element.points.map(existing => new THREE.Vector3(...existing).add(delta).toArray());
    rebuildRouteGeometry(element);
  }
  movingDraftId = '';
  selectDraftElement(element);
  setEhtStatus(`${draftLabel(element)} moved. Draft is not persisted yet.`);
}

function draftElementFromObject(object) {
  let cursor = object;
  while (cursor) {
    if (cursor.userData?.ehtDraftId) {
      return ehtDraftElements.find(item => item.id === cursor.userData.ehtDraftId) || null;
    }
    cursor = cursor.parent;
  }
  return null;
}

function pickDraftElement() {
  const draftObjects = ehtDraftElements
    .filter(isDraftElementVisible)
    .map(element => element.object3d)
    .filter(Boolean);
  if (!draftObjects.length) return null;
  const previousThreshold = raycaster.params.Line?.threshold;
  if (raycaster.params.Line) raycaster.params.Line.threshold = 0.25;
  const hits = raycaster.intersectObjects(draftObjects, true);
  if (raycaster.params.Line) raycaster.params.Line.threshold = previousThreshold ?? 1;
  if (!hits.length) return null;
  return draftElementFromObject(hits[0].object);
}

function pointFromViewerEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = selectableMeshes.length ? raycaster.intersectObjects(selectableMeshes, false) : [];
  if (hits.length) return hits[0].point.clone();

  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -controls.target.y);
  const point = new THREE.Vector3();
  if (raycaster.ray.intersectPlane(plane, point)) return point;
  return controls.target.clone();
}

function createDraftPointMesh(position, def) {
  const geometry = new THREE.BoxGeometry(0.45, 0.45, 0.45);
  const material = new THREE.MeshStandardMaterial({
    color: def.color,
    roughness: 0.6,
    metalness: 0.0,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(position);
  return mesh;
}

function createDraftRouteObject(points, def) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color: def.color, linewidth: 2 });
  const line = new THREE.Line(geometry, material);
  return line;
}

function draftLabel(element) {
  const def = ehtDef(element.type);
  return element.parameters?.label || `${def.label} ${element.sequence}`;
}

function draftSearchText(element) {
  return [
    draftLabel(element),
    ehtDef(element.type).label,
    element.type,
    element.kind,
    element.parameters?.circuit_ref,
    element.parameters?.cable_type,
  ].join(' ').toLowerCase();
}

function isDraftElementVisible(element) {
  return !hiddenEhtTypes.has(element.type) && !hiddenEhtDraftIds.has(element.id);
}

function applyDraftVisibility() {
  for (const element of ehtDraftElements) {
    element.object3d.visible = isDraftElementVisible(element);
  }
}

function syncEhtTypeState(type) {
  const elements = ehtDraftElements.filter(element => element.type === type);
  const visibleCount = elements.filter(isDraftElementVisible).length;
  const toggle = document.querySelector(`.eht-type-toggle[data-eht-type="${type}"]`);
  if (!toggle) return;
  toggle.checked = elements.length > 0 && visibleCount === elements.length;
  toggle.indeterminate = visibleCount > 0 && visibleCount < elements.length;
}

function renderDraftList() {
  if (!ehtDraftList) return;
  if (!ehtDraftElements.length) {
    ehtDraftList.innerHTML = '<div class="meta">No EHT draft elements yet.</div>';
    updateUndoState();
    return;
  }
  const byType = new Map();
  for (const element of ehtDraftElements) {
    if (!byType.has(element.type)) byType.set(element.type, []);
    byType.get(element.type).push(element);
  }
  const types = Array.from(byType.keys()).sort((a, b) => ehtDef(a).label.localeCompare(ehtDef(b).label));
  ehtDraftList.innerHTML = types.map(type => {
    const def = ehtDef(type);
    const elements = byType.get(type).slice().sort((a, b) => draftLabel(a).localeCompare(draftLabel(b)));
    const collapsed = collapsedEhtTypes.has(type);
    const allVisible = elements.every(isDraftElementVisible);
    const someVisible = elements.some(isDraftElementVisible);
    return `
      <div class="p3d-tree-node eht-type-group" data-eht-type="${escapeHtml(type)}">
        <div class="p3d-tree-row">
          <button type="button" class="eht-type-collapse-toggle" data-eht-type="${escapeHtml(type)}" aria-label="${collapsed ? 'Expand' : 'Collapse'} ${escapeHtml(def.label)}">${collapsed ? '▸' : '▾'}</button>
          <input type="checkbox" class="eht-type-toggle" data-eht-type="${escapeHtml(type)}" ${allVisible ? 'checked' : ''} ${someVisible && !allVisible ? 'data-indeterminate="true"' : ''}>
          <span class="p3d-tree-label" title="${escapeHtml(def.label)}">${escapeHtml(def.label)}</span>
          <span class="p3d-tree-count">${elements.length}</span>
        </div>
        <div class="p3d-tree-children ${collapsed ? 'p3d-tree-hidden' : ''}">
          ${elements.map(element => `
            <div class="p3d-tree-leaf eht-hierarchy-row ${selectedDraftId === element.id ? 'p3d-draft-selected' : ''}" data-draft-id="${escapeHtml(element.id)}" data-eht-type="${escapeHtml(type)}" data-search-text="${escapeHtml(draftSearchText(element))}">
              <input type="checkbox" class="eht-element-toggle" data-draft-id="${escapeHtml(element.id)}" ${isDraftElementVisible(element) ? 'checked' : ''}>
              <button type="button" class="eht-select-row" data-draft-id="${escapeHtml(element.id)}" title="${escapeHtml(draftLabel(element))}">${escapeHtml(draftLabel(element))}</button>
              <span class="p3d-tree-count">${escapeHtml(element.kind)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }).join('');
  ehtDraftList.querySelectorAll('.eht-type-toggle[data-indeterminate="true"]').forEach(toggle => {
    toggle.indeterminate = true;
  });
  ehtDraftList.querySelectorAll('.eht-type-collapse-toggle').forEach(button => {
    button.addEventListener('click', () => {
      const type = button.dataset.ehtType;
      if (collapsedEhtTypes.has(type)) {
        collapsedEhtTypes.delete(type);
      } else {
        collapsedEhtTypes.add(type);
      }
      renderDraftList();
    });
  });
  ehtDraftList.querySelectorAll('.eht-type-toggle').forEach(toggle => {
    toggle.addEventListener('change', () => {
      const type = toggle.dataset.ehtType;
      if (toggle.checked) {
        hiddenEhtTypes.delete(type);
        ehtDraftElements.filter(element => element.type === type).forEach(element => hiddenEhtDraftIds.delete(element.id));
      } else {
        hiddenEhtTypes.add(type);
      }
      applyDraftVisibility();
      renderDraftList();
    });
  });
  ehtDraftList.querySelectorAll('.eht-element-toggle').forEach(toggle => {
    toggle.addEventListener('change', () => {
      const element = ehtDraftElements.find(item => item.id === toggle.dataset.draftId);
      if (!element) return;
      if (toggle.checked) {
        hiddenEhtDraftIds.delete(element.id);
        hiddenEhtTypes.delete(element.type);
      } else {
        hiddenEhtDraftIds.add(element.id);
      }
      applyDraftVisibility();
      syncEhtTypeState(element.type);
      renderDraftList();
    });
  });
  ehtDraftList.querySelectorAll('.eht-select-row').forEach(row => {
    row.addEventListener('click', () => {
      const element = ehtDraftElements.find(item => item.id === row.dataset.draftId);
      if (!element) return;
      selectDraftElement(element, { frame: true });
    });
  });
  applyDraftVisibility();
  if (currentHierarchyQuery()) applyHierarchySearch();
  updateUndoState();
}

function addDraftElement(type, kind, points, object3d) {
  const sequence = ehtDraftElements.length + 1;
  const element = {
    id: `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type,
    kind,
    sequence,
    points: points.map(point => point.toArray()),
    parameters: draftDefaults(type, sequence),
    object3d,
  };
  object3d.userData.ehtDraftId = element.id;
  ehtDraftGroup.add(object3d);
  hiddenEhtTypes.delete(type);
  hiddenEhtDraftIds.delete(element.id);
  ehtDraftElements.push(element);
  selectedDraftId = element.id;
  applyPointDimensions(element);
  renderDraftList();
  renderDraftSelectionPanel(element);
  setSelectionActionsEnabled(true);
  setEhtStatus(`${draftLabel(element)} added. Draft is not persisted yet.`);
  return element;
}

function placeEhtPoint(type, point) {
  const def = ehtDef(type);
  const mesh = createDraftPointMesh(point, def);
  addDraftElement(type, 'point', [point], mesh);
}

function finishEhtRoute() {
  if (!activeEhtTool || pendingRoutePoints.length < 2) {
    setEhtStatus('Pick at least two route points before finishing.');
    return;
  }
  const def = ehtDef(activeEhtTool);
  const line = createDraftRouteObject(pendingRoutePoints, def);
  addDraftElement(activeEhtTool, 'route', pendingRoutePoints, line);
  pendingRoutePoints = [];
}

function cancelEhtRoute() {
  pendingRoutePoints = [];
  setEhtStatus(activeEhtTool ? `${ehtDef(activeEhtTool).label}: route cancelled.` : 'Route cancelled.');
}

function handleEhtToolClick(event) {
  if (movingDraftId) {
    const element = ehtDraftElements.find(item => item.id === movingDraftId);
    if (element) {
      moveDraftElementTo(element, pointFromViewerEvent(event));
      return true;
    }
    movingDraftId = '';
  }
  if (!activeEhtTool) return false;
  const def = ehtDef(activeEhtTool);
  const point = pointFromViewerEvent(event);
  if (def.kind === 'route') {
    pendingRoutePoints.push(point);
    setEhtStatus(`${def.label}: ${pendingRoutePoints.length} point(s) picked. Use Finish Route when complete.`);
    return true;
  }
  placeEhtPoint(activeEhtTool, point);
  return true;
}

function undoLastDraftElement() {
  const element = ehtDraftElements.pop();
  if (!element) return;
  element.object3d.parent?.remove(element.object3d);
  disposeObject3D(element.object3d);
  hiddenEhtDraftIds.delete(element.id);
  if (movingDraftId === element.id) movingDraftId = '';
  selectedDraftId = '';
  renderDraftList();
  setEhtStatus('Last draft element removed.');
}

function bindEhtTools() {
  document.querySelectorAll('.eht-tool-btn').forEach(button => {
    button.addEventListener('click', () => setActiveEhtTool(button.dataset.ehtTool || ''));
  });
  if (ehtSelectToolBtn) ehtSelectToolBtn.addEventListener('click', () => setActiveEhtTool(''));
  if (ehtPaletteToggleBtn && ehtToolPalette) {
    ehtPaletteToggleBtn.addEventListener('click', () => {
      const collapsed = !ehtToolPalette.classList.contains('palette-collapsed');
      ehtToolPalette.classList.toggle('palette-collapsed', collapsed);
      ehtPaletteToggleBtn.textContent = collapsed ? 'Show' : 'Hide';
    });
  }
  if (ehtFinishRouteBtn) ehtFinishRouteBtn.addEventListener('click', finishEhtRoute);
  if (ehtCancelRouteBtn) ehtCancelRouteBtn.addEventListener('click', cancelEhtRoute);
  if (ehtUndoBtn) ehtUndoBtn.addEventListener('click', undoLastDraftElement);
  if (ehtSaveLayerBtn) {
    ehtSaveLayerBtn.addEventListener('click', () => {
      setEhtStatus('Draft save is not wired yet. Next pass will add backend EHT layer persistence.');
    });
  }
  renderDraftList();
}

if (selectionEl) {
  selectionEl.addEventListener('submit', event => {
    if (event.target?.id !== 'ehtParameterForm') return;
    event.preventDefault();
    updateDraftParametersFromForm(event.target);
  });
  selectionEl.addEventListener('click', event => {
    const moveButton = event.target.closest?.('#ehtMoveSelectedBtn');
    if (moveButton) {
      const element = selectedDraftElement();
      if (!element) return;
      movingDraftId = movingDraftId === element.id ? '' : element.id;
      setActiveEhtTool('');
      renderDraftSelectionPanel(element);
      setEhtStatus(movingDraftId ? `${draftLabel(element)} move mode: click a new model position.` : `${draftLabel(element)} move cancelled.`);
      return;
    }
    const deleteButton = event.target.closest?.('#ehtDeleteSelectedBtn');
    if (deleteButton) {
      const element = selectedDraftElement();
      if (element) deleteDraftElement(element);
    }
  });
}

function selectionDetailsHtml(data, featureId = null) {
  const summary = data?.selection_summary || {};
  const spatialPath = Array.isArray(summary.spatial_path) ? summary.spatial_path.join(' / ') : '';
  return [
    kvRow('Feature ID', featureId),
    kvRow('Label', summary.display_label || data?.tag || data?.source_object_id || data?.stable_id),
    kvRow('Type', summary.object_type || data?.object_type),
    kvRow('Tag', summary.tag || data?.tag),
    kvRow('Name', summary.name),
    kvRow('Line ID', summary.line_id || data?.line_id),
    kvRow('Source Extents', dimensionsText(summary)),
    kvRow('Spatial Path', spatialPath),
    kvRow('Group', summary.hierarchy_group),
    kvRow('Stable ID', summary.stable_id || data?.stable_id),
    kvRow('Source Object', summary.source_object_id || data?.source_object_id),
    metadataDetails(data),
  ].join('');
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
    `<p class="kv"><span>Antialiasing</span><strong>${escapeHtml(runtimeStats.antialiasing || 'unknown')}</strong></p>`,
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
  objectById = new Map();
  for (const obj of pkg.objects || []) {
    if (obj.stable_id) objectIndex.set(obj.stable_id, obj);
    if (obj.source_object_id) objectIndex.set(obj.source_object_id, obj);
    if (obj.id !== undefined && obj.id !== null) {
      objectById.set(Number(obj.id), obj);
      objectById.set(String(obj.id), obj);
    }
  }
  renderHierarchy(pkg);
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
  if (runtimeStats.package && shouldUseReviewMode(runtimeStats.package)) {
    applyPixelRatio(maxIdlePixelRatio, 'review-fidelity');
  } else {
    applyPixelRatio(interactionPixelRatio, 'adaptive-interaction');
  }
  renderMetrics();
}

function endInteraction() {
  isInteracting = false;
  if (restoreQualityTimer) window.clearTimeout(restoreQualityTimer);
  restoreQualityTimer = window.setTimeout(() => {
    if (runtimeStats.package && shouldUseReviewMode(runtimeStats.package) && lowFpsSamples < 2) {
      applyPixelRatio(maxIdlePixelRatio, 'review-fidelity');
    } else {
      const restoredRatio = lowFpsSamples >= 2 ? Math.max(minPixelRatio, interactionPixelRatio) : maxIdlePixelRatio;
      applyPixelRatio(restoredRatio, lowFpsSamples >= 2 ? 'adaptive-fps-limited' : 'adaptive-idle');
    }
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

function frameBounds(bounds) {
  if (!(bounds instanceof THREE.Box3) || bounds.isEmpty()) return;
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  bounds.getSize(size);
  bounds.getCenter(center);
  const radius = Math.max(size.length() * 0.5, 0.5);
  const fovRadians = THREE.MathUtils.degToRad(camera.fov);
  const distance = Math.max(radius / Math.tan(fovRadians / 2), radius * 2.0);
  const direction = new THREE.Vector3().subVectors(camera.position, controls.target);
  if (direction.lengthSq() < 0.0001) direction.set(1, 0.8, 1);
  direction.normalize();
  camera.position.copy(center).add(direction.multiplyScalar(distance * 1.25));
  controls.target.copy(center);
  controls.minDistance = Math.max(radius * 0.02, 0.05);
  controls.maxDistance = Math.max(radius * 80, controls.minDistance * 10, 100);
  camera.near = Math.max(controls.minDistance / 100, 0.005);
  camera.far = Math.max(controls.maxDistance * 4, 1000);
  camera.updateProjectionMatrix();
  controls.update();
}

function setSelectionActionsEnabled(enabled) {
  if (fitSelectionBtn) fitSelectionBtn.disabled = !enabled;
  if (clearSelectionBtn) clearSelectionBtn.disabled = !enabled;
}

function fitSelectedObject() {
  const draftElement = selectedDraftElement();
  if (draftElement) {
    const bounds = new THREE.Box3().setFromObject(draftElement.object3d);
    frameBounds(bounds);
    return;
  }
  if (!selectedHighlight) return;
  const bounds = new THREE.Box3().setFromObject(selectedHighlight);
  frameBounds(bounds);
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

function tuneLoadedGlbMaterial(material) {
  if (!material) return;
  if (Array.isArray(material)) {
    material.forEach(item => tuneLoadedGlbMaterial(item));
    return;
  }
  if (typeof material.metalness === 'number') material.metalness = 0.0;
  if (typeof material.roughness === 'number') material.roughness = Math.max(material.roughness, 0.9);
  if (typeof material.envMapIntensity === 'number') material.envMapIntensity = 0.0;
  material.needsUpdate = true;
}

function disposeObject3D(object) {
  object.traverse(node => {
    if (node.geometry) node.geometry.dispose();
    if (node.material && !node.userData?.isSelectionHighlight) {
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
          const objectSpans = Array.isArray(sidecar.object_spans) ? sidecar.object_spans : [];
          for (const span of objectSpans) {
            const featureId = Number(span.feature_id);
            if (!Number.isFinite(featureId)) continue;
            featureSpanIndex.set(featureId, {
              firstIndex: Number(span.first_index),
              indexCount: Number(span.index_count),
              vertexOffset: Number(span.vertex_offset),
              vertexCount: Number(span.vertex_count),
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
      tuneLoadedGlbMaterial(node.material);
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
  if (selectedMesh?.userData?.tileKey === state.key) {
    clearSelection();
    if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
  }
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
  featureSpanIndex = new Map();
  selectableMeshes = [];
  prepareGlbTileStates(pkg);
  const approximateBounds = approximatePackageBounds(pkg);
  frameScene(approximateBounds);
  const elapsedMs = Math.round(performance.now() - started);
  setGlbRuntimeMetrics(pkg, elapsedMs);
  setStatus(`Prepared GLB tile stream with ${glbTileStates.length} tile(s) in ${elapsedMs} ms. Loading visible tiles...`);
  await updateGlbTileStreaming(pkg, true);
}

function clearSelection({ keepDraft = false } = {}) {
  if (selectedHighlight) {
    selectedHighlight.parent?.remove(selectedHighlight);
    selectedHighlight.geometry?.dispose?.();
    selectedHighlight = null;
  }
  selectedMesh = null;
  if (!keepDraft) {
    selectedDraftId = '';
    movingDraftId = '';
    renderDraftList();
  }
  setSelectionActionsEnabled(false);
}

async function showSelection(mesh) {
  clearSelection();
  selectedMesh = mesh;
  selectedHighlight = new THREE.Mesh(mesh.geometry.clone(), highlightMaterial);
  selectedHighlight.userData.isSelectionHighlight = true;
  selectedHighlight.renderOrder = 10;
  selectedHighlight.frustumCulled = false;
  root.add(selectedHighlight);
  setSelectionActionsEnabled(true);

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
    selectionEl.innerHTML = selectionDetailsHtml(data);
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

function vertexIndexForGeometryIndex(geometry, geometryIndex) {
  return geometry.index ? geometry.index.getX(geometryIndex) : geometryIndex;
}

function appendTriangleVertex(highlightPositions, positions, vertexIndex) {
  highlightPositions.push(
    positions.getX(vertexIndex),
    positions.getY(vertexIndex),
    positions.getZ(vertexIndex),
  );
}

function highlightGeometryFromSpan(sourceGeometry, positions, featureAttribute, featureId) {
  const span = featureSpanIndex.get(featureId);
  if (!span) return null;

  const firstIndex = Math.trunc(span.firstIndex);
  const indexCount = Math.trunc(span.indexCount);
  const sourceCount = sourceGeometry.index ? sourceGeometry.index.count : positions.count;
  if (!Number.isInteger(firstIndex) || !Number.isInteger(indexCount) || firstIndex < 0 || indexCount < 3) return null;
  if (firstIndex + indexCount > sourceCount) return null;

  const triangleIndexCount = indexCount - (indexCount % 3);
  if (triangleIndexCount < 3) return null;

  const highlightPositions = [];
  for (let cursor = firstIndex; cursor < firstIndex + triangleIndexCount; cursor += 1) {
    const vertexIndex = vertexIndexForGeometryIndex(sourceGeometry, cursor);
    if (Math.round(featureAttribute.getX(vertexIndex)) !== featureId) {
      return null;
    }
    appendTriangleVertex(highlightPositions, positions, vertexIndex);
  }

  if (!highlightPositions.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(highlightPositions, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function highlightGeometryForFeature(hit, featureId) {
  const sourceGeometry = hit.object?.geometry;
  const positions = sourceGeometry?.getAttribute?.('position');
  const featureAttribute = sourceGeometry?.getAttribute?.('_FEATURE_ID_0') || sourceGeometry?.getAttribute?.('_feature_id_0');
  if (!sourceGeometry || !positions || !featureAttribute) return null;

  const spanGeometry = highlightGeometryFromSpan(sourceGeometry, positions, featureAttribute, featureId);
  if (spanGeometry) return spanGeometry;

  const indices = sourceGeometry.index;
  const triangleCount = indices ? Math.floor(indices.count / 3) : Math.floor(positions.count / 3);
  const highlightPositions = [];
  for (let triangle = 0; triangle < triangleCount; triangle += 1) {
    const triangleIndices = [0, 1, 2].map(offset => {
      const rawIndex = triangle * 3 + offset;
      return vertexIndexForGeometryIndex(sourceGeometry, rawIndex);
    });
    const includesFeature = triangleIndices.some(index => Math.round(featureAttribute.getX(index)) === featureId);
    if (!includesFeature) continue;
    for (const index of triangleIndices) {
      appendTriangleVertex(highlightPositions, positions, index);
    }
  }

  if (!highlightPositions.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(highlightPositions, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function showGlbFeatureHighlight(hit, featureId) {
  const geometry = highlightGeometryForFeature(hit, featureId);
  if (!geometry) return;
  selectedMesh = hit.object;
  selectedHighlight = new THREE.Mesh(geometry, highlightMaterial);
  selectedHighlight.userData.isSelectionHighlight = true;
  selectedHighlight.renderOrder = 10;
  selectedHighlight.frustumCulled = false;
  hit.object.add(selectedHighlight);
  setSelectionActionsEnabled(true);
}

async function showGlbFeatureSelection(hit) {
  clearSelection();
  const featureId = featureIdFromHit(hit);
  if (!featureId || !featureIndex.has(featureId)) {
    if (selectionEl) selectionEl.textContent = 'No feature metadata was found for this GLB face.';
    return;
  }

  showGlbFeatureHighlight(hit, featureId);
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
    selectionEl.innerHTML = selectionDetailsHtml(data, featureId);
  } catch (error) {
    selectionEl.innerHTML = baseRows.join('') + `<p class="meta">${escapeHtml(error.message || 'Unable to load metadata.')}</p>`;
  }
}

function pick(event) {
  if (handleEhtToolClick(event)) {
    return;
  }
  const pickStarted = performance.now();
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const draftElement = pickDraftElement();
  if (draftElement) {
    runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
    renderMetrics();
    selectDraftElement(draftElement);
    return;
  }
  if (!selectableMeshes.length) {
    runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
    renderMetrics();
    if (selectionEl) selectionEl.textContent = 'Object picking is not available for this package format yet.';
    return;
  }
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
if (hierarchySearchInput) hierarchySearchInput.addEventListener('input', applyHierarchySearch);
if (searchFocusBtn) {
  searchFocusBtn.addEventListener('click', () => {
    const match = firstHierarchyMatch();
    if (match) focusObjectFromHierarchy(match.dataset.objectId, { filterList: false });
  });
}
if (searchIsolateBtn) {
  searchIsolateBtn.addEventListener('click', () => {
    const match = firstHierarchyMatch();
    if (match) focusObjectFromHierarchy(match.dataset.objectId, { filterList: true });
  });
}
if (searchClearBtn) {
  searchClearBtn.addEventListener('click', () => {
    if (hierarchySearchInput) hierarchySearchInput.value = '';
    applyHierarchySearch();
  });
}
if (resetBtn) resetBtn.addEventListener('click', () => frameScene());
if (fitSelectionBtn) fitSelectionBtn.addEventListener('click', fitSelectedObject);
if (clearSelectionBtn) {
  clearSelectionBtn.addEventListener('click', () => {
    clearSelection();
    if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
  });
}
renderer.domElement.addEventListener('click', pick);
bindEhtTools();
window.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    clearSelection();
    if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
  }
});
resize();
animate();

loadPackage().catch(error => {
  setStatus(error.message || 'Unable to load package.');
});
