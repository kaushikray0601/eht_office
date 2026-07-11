import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { manhattanSegmentPoints, routeProfile, suggestManhattanRoute, validateRoute } from './routing_core.js';

const viewer = document.getElementById('viewer');
const statusEl = document.getElementById('viewerStatus');
const resetBtn = document.getElementById('resetViewBtn');
const fitSelectionBtn = document.getElementById('fitSelectionBtn');
const clearSelectionBtn = document.getElementById('clearSelectionBtn');
const measureToggleBtn = document.getElementById('measureToggleBtn');
const vertexSnapToggleBtn = document.getElementById('vertexSnapToggleBtn');
const scaleToggleBtn = document.getElementById('scaleToggleBtn');
const scaleHud = document.getElementById('scaleHud');
const measurementHud = document.getElementById('measurementHud');
const measurementStatus = document.getElementById('measurementStatus');
const planeDistanceBtn = document.getElementById('planeDistanceBtn');
const viewerContextMenu = document.getElementById('viewerContextMenu');
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
const ehtRouteHud = document.getElementById('ehtRouteHud');
const ehtFinishRouteBtn = document.getElementById('ehtFinishRouteBtn');
const ehtCancelRouteBtn = document.getElementById('ehtCancelRouteBtn');
const ehtUndoGuideBtn = document.getElementById('ehtUndoGuideBtn');
const ehtDeleteGuideBtn = document.getElementById('ehtDeleteGuideBtn');
const ehtResetRouteBtn = document.getElementById('ehtResetRouteBtn');
const ehtOrthogonalRouteBtn = document.getElementById('ehtOrthogonalRouteBtn');
const ehtSelectedRouteControls = document.getElementById('ehtSelectedRouteControls');
const ehtEditSelectedRouteBtn = document.getElementById('ehtEditSelectedRouteBtn');
const ehtSaveLayerBtn = document.getElementById('ehtSaveLayerBtn');
const ehtUndoBtn = document.querySelector('.eht-undo-btn');
const ehtRedoBtn = document.querySelector('.eht-redo-btn');
const ehtDraftList = document.getElementById('ehtDraftList');
const plotPlanInput = document.getElementById('plotPlanInput');
const plotPlanVisibleToggle = document.getElementById('plotPlanVisibleToggle');
const plotPlanOpacity = document.getElementById('plotPlanOpacity');
const plotPlanClearBtn = document.getElementById('plotPlanClearBtn');
const plotPlanStatus = document.getElementById('plotPlanStatus');
const viewerLayerList = document.getElementById('viewerLayerList');
const viewerLayerStatus = document.getElementById('viewerLayerStatus');
const showAllLayersBtn = document.getElementById('showAllLayersBtn');
const hideOverlayLayersBtn = document.getElementById('hideOverlayLayersBtn');
const quickSelectBtn = document.getElementById('quickSelectBtn');
const quickOrbitBtn = document.getElementById('quickOrbitBtn');
const quickPanBtn = document.getElementById('quickPanBtn');
const quickTopBtn = document.getElementById('quickTopBtn');
const quickFrontBtn = document.getElementById('quickFrontBtn');
const quickSideBtn = document.getElementById('quickSideBtn');
const quickFitBtn = document.getElementById('quickFitBtn');
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
controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;

scene.add(new THREE.HemisphereLight(0xffffff, 0xb8c4d0, 1.8));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
keyLight.position.set(20, 35, 25);
scene.add(keyLight);

const root = new THREE.Group();
scene.add(root);

let packageBounds = new THREE.Box3();
let glbPackageOrigin = [0, 0, 0];
const viewerLayers = new Map();
const viewerInteractions = new Map();
let activeViewerInteractionId = '';
let viewerLayerControlRenderQueued = false;

function queueViewerLayerControlRender() {
  if (viewerLayerControlRenderQueued) return;
  viewerLayerControlRenderQueued = true;
  window.setTimeout(() => {
    viewerLayerControlRenderQueued = false;
    renderViewerLayerControls();
  }, 0);
}

function registerViewerLayer(config) {
  const group = config.group || (config.createGroup ? new THREE.Group() : null);
  const layer = {
    id: config.id,
    owner: config.owner || 'plant3d',
    kind: config.kind || 'overlay',
    label: config.label || config.id,
    group,
    getObjects: config.getObjects || (() => (group ? [group] : [])),
    getElements: config.getElements || (() => []),
    setVisible: config.setVisible || null,
    hiddenInControls: Boolean(config.hiddenInControls),
    visible: config.visible !== false,
  };
  viewerLayers.set(layer.id, layer);
  if (layer.group) {
    layer.group.userData.plant3dLayerId = layer.id;
    layer.group.visible = layer.visible;
    if (!layer.group.parent) scene.add(layer.group);
  }
  queueViewerLayerControlRender();
  return layer;
}

function updateViewerLayer(id, patch) {
  const layer = viewerLayers.get(id);
  if (!layer) return null;
  Object.assign(layer, patch);
  queueViewerLayerControlRender();
  return layer;
}

function isViewerLayerVisible(layer) {
  if (!layer) return false;
  if (typeof layer.isVisible === 'function') return Boolean(layer.isVisible());
  if (layer.group) return Boolean(layer.group.visible);
  const objects = layer.getObjects?.() || [];
  if (objects.length) return objects.some(object => object?.visible !== false);
  return Boolean(layer.visible);
}

function isViewerLayerIdVisible(id) {
  return isViewerLayerVisible(viewerLayers.get(id));
}

function activeCoordinateTransform() {
  const pkg = runtimeStats?.package || {};
  return pkg.coordinate_transform || pkg.metadata?.coordinate_transform || {};
}

function activeRenderOrigin() {
  const transform = activeCoordinateTransform();
  return Array.isArray(transform.rtc_origin_render_xyz)
    ? transform.rtc_origin_render_xyz
    : glbPackageOrigin;
}

function activeCoordinateScaleToM() {
  const transform = activeCoordinateTransform();
  const metadata = runtimeStats?.package?.metadata || {};
  return Number(transform.scale_to_m || metadata.render_coordinate_scale_to_m || metadata.unit_metadata?.render_coordinate_scale_to_m || 1) || 1;
}

function sourcePointToRenderPoint(sourcePoint) {
  const origin = activeRenderOrigin();
  const scaleToM = activeCoordinateScaleToM();
  return new THREE.Vector3(
    Number(sourcePoint.x || 0) * scaleToM - Number(origin[0] || 0),
    Number(sourcePoint.z || 0) * scaleToM - Number(origin[1] || 0),
    Number(sourcePoint.y || 0) * scaleToM - Number(origin[2] || 0),
  );
}

function renderPointToSourcePoint(renderPoint) {
  const origin = activeRenderOrigin();
  const scaleToM = activeCoordinateScaleToM();
  const renderWorldX = Number(renderPoint.x || 0) + Number(origin[0] || 0);
  const renderWorldY = Number(renderPoint.y || 0) + Number(origin[1] || 0);
  const renderWorldZ = Number(renderPoint.z || 0) + Number(origin[2] || 0);
  return {
    x: renderWorldX / scaleToM,
    y: renderWorldZ / scaleToM,
    z: renderWorldY / scaleToM,
    coordinate_frame: 'source_xyz_m',
  };
}

function rayFromViewerEvent(event) {
  updatePointerFromViewerEvent(event);
  return raycaster.ray.clone();
}

function pointOnSourceElevationFromViewerEvent(event, sourceElevationM) {
  const origin = activeRenderOrigin();
  const scaleToM = activeCoordinateScaleToM();
  const renderElevation = Number(sourceElevationM || 0) * scaleToM - Number(origin[1] || 0);
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -renderElevation);
  const point = new THREE.Vector3();
  const ray = rayFromViewerEvent(event);
  return ray.intersectPlane(plane, point) ? point : null;
}

function raycastObjectsFromViewerEvent(event, objects, recursive = false) {
  const ray = rayFromViewerEvent(event);
  if (!ray || !Array.isArray(objects) || !objects.length) return [];
  return raycaster.intersectObjects(objects, recursive);
}

function currentSourceElevationM() {
  return renderPointToSourcePoint(controls.target).z;
}

function sourcePointFromBounds(bounds) {
  if (!bounds || Object.keys(bounds).length === 0) return null;
  const minX = Number(bounds.min_x);
  const maxX = Number(bounds.max_x);
  const minY = Number(bounds.min_y);
  const maxY = Number(bounds.max_y);
  const minZ = Number(bounds.min_z);
  const maxZ = Number(bounds.max_z);
  if (![minX, maxX, minY, maxY, minZ, maxZ].every(Number.isFinite)) return null;
  return {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2,
    z: (minZ + maxZ) / 2,
    coordinate_frame: 'source_xyz_m',
  };
}

function modelAnchorFromObjectSummary(obj, sourcePoint = null, featureId = null) {
  if (!obj) return null;
  const summary = obj.selection_summary || {};
  return {
    owner_module: 'plant3d',
    anchor_kind: 'model_object',
    render_package_id: runtimeStats.package?.id || null,
    source_model_id: runtimeStats.package?.source_model_id || null,
    model_object_id: obj.id || null,
    stable_id: obj.stable_id || summary.stable_id || '',
    source_object_id: obj.source_object_id || summary.source_object_id || '',
    object_type: obj.object_type || summary.object_type || '',
    label: objectDisplayLabel(obj),
    bounds: obj.bounds || {},
    source_point_m: sourcePoint || sourcePointFromBounds(obj.bounds),
    feature_id: Number.isFinite(Number(featureId)) ? Number(featureId) : null,
  };
}

function getSelectedModelAnchor() {
  if (!isViewerLayerIdVisible('model')) return null;
  if (Number.isFinite(selectedGlbFeatureId)) {
    const feature = featureIndex.get(selectedGlbFeatureId);
    if (feature?.objectSummary) {
      return modelAnchorFromObjectSummary(
        feature.objectSummary,
        selectedModelAnchorSourcePoint || sourcePointFromBounds(feature.objectSummary.bounds),
        selectedGlbFeatureId,
      );
    }
  }
  if (selectedMesh?.userData?.objectId) {
    const obj = objectById.get(Number(selectedMesh.userData.objectId)) || objectById.get(String(selectedMesh.userData.objectId));
    if (obj) return modelAnchorFromObjectSummary(obj, selectedModelAnchorSourcePoint || sourcePointFromBounds(obj.bounds));
  }
  if (hierarchySelectedObjectId !== null && hierarchySelectedObjectId !== undefined) {
    const obj = objectById.get(Number(hierarchySelectedObjectId)) || objectById.get(String(hierarchySelectedObjectId));
    if (obj) return modelAnchorFromObjectSummary(obj);
  }
  if (selectedHighlight) {
    const bounds = new THREE.Box3().setFromObject(selectedHighlight);
    if (!bounds.isEmpty()) {
      const center = new THREE.Vector3();
      bounds.getCenter(center);
      const sourcePoint = renderPointToSourcePoint(center);
      return {
        owner_module: 'plant3d',
        anchor_kind: 'model_selection_point',
        render_package_id: runtimeStats.package?.id || null,
        source_model_id: runtimeStats.package?.source_model_id || null,
        model_object_id: null,
        stable_id: selectedMesh?.userData?.stableId || '',
        source_object_id: '',
        object_type: selectedMesh?.userData?.ifcClass || '',
        label: selectedMesh?.userData?.name || selectedMesh?.userData?.stableId || 'Selected model object',
        bounds: {},
        source_point_m: selectedModelAnchorSourcePoint || sourcePoint,
        feature_id: Number.isFinite(Number(selectedGlbFeatureId)) ? Number(selectedGlbFeatureId) : null,
      };
    }
  }
  return null;
}

function resetCanvasCursor() {
  renderer.domElement.style.cursor = measureModeActive ? 'crosshair' : navigationMode === 'pan' ? 'grab' : '';
}

function deactivateActiveViewerInteraction(options = {}) {
  const interactionId = activeViewerInteractionId;
  if (!interactionId) return false;
  const interaction = viewerInteractions.get(interactionId);
  activeViewerInteractionId = '';
  if (interaction?.onDeactivate) interaction.onDeactivate(options);
  resetCanvasCursor();
  return true;
}

function registerViewerInteraction(config) {
  if (!config?.id) return null;
  viewerInteractions.set(config.id, config);
  return {
    activate: () => {
      if (activeViewerInteractionId && activeViewerInteractionId !== config.id) {
        deactivateActiveViewerInteraction({ reason: 'replaced' });
      }
      if (measureModeActive) setMeasureMode(false);
      if (activeEhtTool) setActiveEhtTool('');
      movingDraftId = '';
      activeViewerInteractionId = config.id;
      renderer.domElement.style.cursor = config.cursor || 'crosshair';
    },
    deactivate: () => {
      if (activeViewerInteractionId === config.id) {
        deactivateActiveViewerInteraction({ reason: 'extension' });
      }
    },
    isActive: () => activeViewerInteractionId === config.id,
  };
}

function dispatchViewerInteractionClick(event) {
  const interaction = viewerInteractions.get(activeViewerInteractionId);
  if (!interaction?.onCanvasClick) return false;
  if (shouldIgnoreViewerCommitClick()) {
    if (interaction.onNavigationClick) interaction.onNavigationClick(event);
    return true;
  }
  return interaction.onCanvasClick(event) !== false;
}

function cancelActiveViewerInteraction() {
  const interaction = viewerInteractions.get(activeViewerInteractionId);
  if (!interaction) return false;
  if (interaction.onCancel) interaction.onCancel();
  activeViewerInteractionId = '';
  resetCanvasCursor();
  return true;
}

function publishViewerPackageLoaded(pkg) {
  if (!window.plant3dViewerRuntime) return;
  window.dispatchEvent(new CustomEvent('plant3dviewer:package-loaded', {
    detail: {
      package: runtimeStats.package || pkg,
      runtime: window.plant3dViewerRuntime,
    },
  }));
}

function publishViewerExtensionHost() {
  window.plant3dViewerRuntime = {
    THREE,
    scene,
    camera,
    controls,
    renderer,
    canvas: renderer.domElement,
    raycaster,
    getPackage: () => runtimeStats.package,
    getPackageBounds: () => packageBounds.clone(),
    currentSourceElevationM,
    renderNow: () => renderer.render(scene, camera),
    worldUnitsForScreenPixels,
    sourcePointToRenderPoint,
    renderPointToSourcePoint,
    getSelectedModelAnchor,
    pointOnSourceElevationFromViewerEvent,
    rayFromViewerEvent,
    raycastObjectsFromViewerEvent,
    registerInteraction: registerViewerInteraction,
    deactivateActiveInteraction: deactivateActiveViewerInteraction,
  };
  window.dispatchEvent(new CustomEvent('plant3dviewer:layers-ready', {
    detail: window.plant3dViewerLayers,
  }));
  window.dispatchEvent(new CustomEvent('plant3dviewer:runtime-ready', {
    detail: window.plant3dViewerRuntime,
  }));
}

function syncViewerLayerVisibility(id, visible) {
  const layer = viewerLayers.get(id);
  if (layer) layer.visible = Boolean(visible);
}

function setViewerLayerVisible(id, visible, { renderControls = true } = {}) {
  const layer = viewerLayers.get(id);
  if (!layer) return;
  const nextVisible = Boolean(visible);
  layer.visible = nextVisible;
  if (typeof layer.setVisible === 'function') {
    layer.setVisible(nextVisible);
  } else if (layer.group) {
    layer.group.visible = nextVisible;
  } else {
    (layer.getObjects?.() || []).forEach(object => {
      if (object) object.visible = nextVisible;
    });
  }
  if (!nextVisible && id === 'measurement') {
    measureModeActive = false;
    if (measureToggleBtn) {
      measureToggleBtn.textContent = 'Measure';
      measureToggleBtn.setAttribute('aria-pressed', 'false');
      measureToggleBtn.classList.remove('p3d-button-primary');
    }
    renderer.domElement.style.cursor = navigationMode === 'pan' ? 'grab' : '';
  }
  if (!nextVisible && id === 'eht-draft') {
    setActiveEhtTool('');
    movingDraftId = '';
  }
  if (renderControls) renderViewerLayerControls();
}

function viewerLayerSummary() {
  return Array.from(viewerLayers.values()).map(layer => {
    const objects = layer.getObjects?.() || [];
    const elements = layer.getElements?.() || [];
    return {
      id: layer.id,
      owner: layer.owner,
      kind: layer.kind,
      label: layer.label,
      visible: isViewerLayerVisible(layer),
      objectCount: objects.filter(Boolean).length,
      elementCount: elements.filter(Boolean).length,
    };
  });
}

window.plant3dViewerLayers = {
  summary: viewerLayerSummary,
  ids: () => Array.from(viewerLayers.keys()),
  register: registerViewerLayer,
  update: updateViewerLayer,
  setVisible: setViewerLayerVisible,
  isVisible: isViewerLayerIdVisible,
};

const ehtDraftGroup = new THREE.Group();
scene.add(ehtDraftGroup);
const pendingRouteGroup = new THREE.Group();
scene.add(pendingRouteGroup);
const measurementGroup = new THREE.Group();
scene.add(measurementGroup);

let gridHelper = new THREE.GridHelper(20, 20, 0x7f8ea3, 0xcbd5e1);
gridHelper.material.opacity = 0.45;
gridHelper.material.transparent = true;
scene.add(gridHelper);
let axesHelper = new THREE.AxesHelper(5);
scene.add(axesHelper);

registerViewerLayer({
  id: 'model',
  owner: 'plant3d',
  kind: 'model',
  label: 'Plant model',
  group: root,
  getObjects: () => selectableMeshes,
  setVisible: visible => {
    root.visible = Boolean(visible);
    if (!visible && Number.isFinite(selectedGlbFeatureId)) {
      clearSelection({ keepDraft: true });
      if (selectionEl) selectionEl.textContent = 'Model layer hidden.';
    }
  },
});
registerViewerLayer({
  id: 'measurement',
  owner: 'plant3d',
  kind: 'tool-overlay',
  label: 'Measurement',
  group: measurementGroup,
  getElements: () => measurementPoints,
});
registerViewerLayer({
  id: 'reference-grid',
  owner: 'plant3d',
  kind: 'reference',
  label: 'Grid and axes',
  getObjects: () => [gridHelper, axesHelper].filter(Boolean),
  setVisible: visible => setGridScaleVisible(visible, { syncLayer: false, renderControls: false }),
});
registerViewerLayer({
  id: 'reference-plot-plan',
  owner: 'plant3d',
  kind: 'reference',
  label: '2D plot plan',
  getObjects: () => plotPlanMesh ? [plotPlanMesh] : [],
  setVisible: visible => {
    if (plotPlanVisibleToggle) plotPlanVisibleToggle.checked = Boolean(visible);
    updatePlotPlanVisibility({ syncLayer: false, renderControls: false });
  },
});
registerViewerLayer({
  id: 'eht-draft',
  owner: 'eht',
  kind: 'consumer-draft-overlay',
  label: 'EHT draft tools',
  group: ehtDraftGroup,
  getElements: () => ehtDraftElements,
  setVisible: visible => {
    ehtDraftGroup.visible = Boolean(visible);
    applyDraftVisibility();
    if (!visible && selectedDraftElement()) {
      clearSelection();
      if (selectionEl) selectionEl.textContent = 'EHT draft layer hidden.';
    }
  },
});
registerViewerLayer({
  id: 'eht-route-preview',
  owner: 'eht',
  kind: 'consumer-draft-preview',
  label: 'EHT route preview',
  group: pendingRouteGroup,
  getElements: () => pendingRoutePoints,
  hiddenInControls: true,
});

let objectIndex = new Map();
let objectById = new Map();
let featureIndex = new Map();
let featureSpanIndex = new Map();
let selectableMeshes = [];
let hiddenGlbFeatureIds = new Set();
let packageObjectRows = [];
let hierarchySearchMatches = new Set();
let selectedMesh = null;
let selectedHighlight = null;
let selectedGlbFeatureId = null;
let selectedModelAnchorSourcePoint = null;
let hierarchySelectedObjectId = null;
let activeEhtTool = '';
let pendingRoutePoints = [];
let pendingRouteAnchors = [];
let pendingRouteGuidePoints = [];
let routeWorkflowState = 'idle';
let routeSourceAnchor = null;
let routeDestinationAnchor = null;
let editingRouteId = '';
let draggingRouteGuideIndex = -1;
let routeGuideDragPlane = null;
let routeGuideDragStartPoint = null;
let selectedRouteGuideIndex = -1;
let routeHudCollapsed = false;
let routeOrthogonalEdit = false;
let ehtDraftElements = [];
let selectedDraftId = '';
let movingDraftId = '';
let draftUndoStack = [];
let draftRedoStack = [];
let routeUndoStack = [];
let routeRedoStack = [];
let restoringDraftHistory = false;
let showGridScale = true;
let measureModeActive = false;
let vertexSnapEnabled = true;
let navigationMode = 'orbit';
let measurementPoints = [];
let measurementLine = null;
let pointerDownState = null;
let suppressNextViewerClick = false;
let currentGridLayout = { size: 20, step: 1, divisions: 20 };
let plotPlanMesh = null;
let plotPlanObjectUrl = '';
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
  color: 0x2563eb,
  wireframe: false,
  depthTest: true,
  depthWrite: false,
  transparent: true,
  opacity: 0.36,
  side: THREE.DoubleSide,
  polygonOffset: true,
  polygonOffsetFactor: -2,
  polygonOffsetUnits: -2,
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

function layerCountText(layer) {
  const elementCount = (layer.getElements?.() || []).filter(Boolean).length;
  const objectCount = (layer.getObjects?.() || []).filter(Boolean).length;
  if (elementCount) return `${elementCount}`;
  if (objectCount) return `${objectCount}`;
  return '';
}

function hiddenStateSummary() {
  const hiddenLayers = Array.from(viewerLayers.values())
    .filter(layer => !layer.hiddenInControls && !isViewerLayerVisible(layer));
  const parts = [];
  if (hiddenLayers.length) parts.push(`${hiddenLayers.length} layer${hiddenLayers.length === 1 ? '' : 's'} off`);
  if (hiddenGlbFeatureIds.size) parts.push(`${hiddenGlbFeatureIds.size} model hidden`);
  const hiddenDraftCount = ehtDraftElements.filter(element => !isDraftElementVisible(element)).length;
  if (hiddenDraftCount) parts.push(`${hiddenDraftCount} EHT hidden`);
  return parts;
}

function updateViewerLayerStatus(message = '') {
  if (!viewerLayerStatus) return;
  const hiddenParts = hiddenStateSummary();
  const badges = hiddenParts.map(part => `<span class="p3d-state-badge p3d-state-warning">${escapeHtml(part)}</span>`).join('');
  const base = message || 'Layer visibility is viewer-session only.';
  viewerLayerStatus.innerHTML = `${badges}${badges ? '<br>' : ''}${escapeHtml(base)}`;
}

function renderViewerLayerControls() {
  if (!viewerLayerList) return;
  const layers = Array.from(viewerLayers.values()).filter(layer => !layer.hiddenInControls);
  viewerLayerList.innerHTML = layers.map(layer => `
    <label class="p3d-layer-row ${isViewerLayerVisible(layer) ? '' : 'p3d-layer-off'}" data-layer-id="${escapeHtml(layer.id)}">
      <input type="checkbox" class="viewer-layer-toggle" data-layer-id="${escapeHtml(layer.id)}" ${isViewerLayerVisible(layer) ? 'checked' : ''}>
      <span>
        <span class="p3d-layer-name">${escapeHtml(layer.label)}</span>
        <span class="p3d-layer-meta">${escapeHtml(layer.owner)} / ${escapeHtml(layer.kind)}</span>
      </span>
      <span class="p3d-layer-count">${escapeHtml(layerCountText(layer))}</span>
    </label>
  `).join('');
  viewerLayerList.querySelectorAll('.viewer-layer-toggle').forEach(toggle => {
    toggle.addEventListener('change', () => {
      setViewerLayerVisible(toggle.dataset.layerId, toggle.checked);
      updateViewerLayerStatus();
    });
  });
  updateViewerLayerStatus();
}

function showAllViewerLayers() {
  Array.from(viewerLayers.values())
    .filter(layer => !layer.hiddenInControls)
    .forEach(layer => setViewerLayerVisible(layer.id, true, { renderControls: false }));
  hiddenGlbFeatureIds.clear();
  hiddenEhtDraftIds.clear();
  hiddenEhtTypes.clear();
  refreshFeatureVisibilityMasks();
  applyDraftVisibility();
  renderDraftList();
  renderViewerLayerControls();
  updateViewerLayerStatus('All viewer layers and hidden session items are visible.');
  setStatus('All viewer layers and hidden session items are visible.');
}

function hideOverlayViewerLayers() {
  Array.from(viewerLayers.values())
    .filter(layer => !layer.hiddenInControls && layer.id !== 'model')
    .forEach(layer => setViewerLayerVisible(layer.id, false, { renderControls: false }));
  renderViewerLayerControls();
  updateViewerLayerStatus('Overlays hidden. Plant model remains visible.');
  setStatus('Overlays hidden. Plant model remains visible.');
}

function formatDimension(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  if (Math.abs(number) >= 100) return number.toFixed(1);
  if (Math.abs(number) >= 10) return number.toFixed(2);
  return number.toFixed(3);
}

function formatSceneLength(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  const abs = Math.abs(number);
  if (abs < 1) return `${number.toFixed(3)} m`;
  if (abs < 10) return `${number.toFixed(2)} m`;
  if (abs < 100) return `${number.toFixed(1)} m`;
  return `${number.toFixed(0)} m`;
}

function formatMm(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  return `${Math.round(number * 1000)} mm`;
}

function niceGridStepForExtent(extent, targetTicks = 16) {
  const rawStep = Math.max(Number(extent || 0) / targetTicks, 0.001);
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalized = rawStep / magnitude;
  const multiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return multiplier * magnitude;
}

function gridLayoutForExtent(extent) {
  const paddedExtent = Math.max(Number(extent || 0) * 1.35, 10);
  const step = niceGridStepForExtent(paddedExtent);
  const divisions = Math.max(2, Math.min(100, Math.ceil(paddedExtent / step)));
  const evenDivisions = divisions % 2 === 0 ? divisions : divisions + 1;
  return {
    size: step * evenDivisions,
    step,
    divisions: evenDivisions,
  };
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

function draftSnapshot() {
  return {
    elements: serializeDraftElements(),
    hidden_types: Array.from(hiddenEhtTypes),
    hidden_ids: Array.from(hiddenEhtDraftIds),
    selected_id: selectedDraftId,
  };
}

function pushDraftHistory() {
  if (restoringDraftHistory) return;
  draftUndoStack.push(draftSnapshot());
  if (draftUndoStack.length > 80) draftUndoStack.shift();
  draftRedoStack = [];
  updateUndoState();
}

function clearDraftObjects() {
  for (const element of ehtDraftElements) {
    element.object3d?.parent?.remove(element.object3d);
    disposeObject3D(element.object3d);
  }
  ehtDraftElements = [];
  hiddenEhtDraftIds.clear();
  hiddenEhtTypes.clear();
  selectedDraftId = '';
  movingDraftId = '';
}

function restoreDraftSnapshot(snapshot) {
  restoringDraftHistory = true;
  clearDraftSelectionVisual();
  clearDraftObjects();
  hiddenEhtTypes = new Set(snapshot?.hidden_types || []);
  hiddenEhtDraftIds = new Set(snapshot?.hidden_ids || []);
  const restored = (snapshot?.elements || []).map(restoreDraftElement).filter(Boolean);
  const selected = restored.find(element => element.id === snapshot?.selected_id) || null;
  selectedDraftId = selected ? selected.id : '';
  applyDraftVisibility();
  renderDraftList();
  if (selected) {
    setDraftElementSelectedVisual(selected, true);
    renderDraftSelectionPanel(selected);
  } else if (selectionEl) {
    selectionEl.textContent = 'Click an object in the viewer.';
  }
  renderViewerLayerControls();
  updateUndoState();
  restoringDraftHistory = false;
}

function undoDraftChange() {
  if (!draftUndoStack.length) {
    setEhtStatus('No draft action to undo.');
    return false;
  }
  draftRedoStack.push(draftSnapshot());
  restoreDraftSnapshot(draftUndoStack.pop());
  setEhtStatus('Draft action undone.');
  return true;
}

function redoDraftChange() {
  if (!draftRedoStack.length) {
    setEhtStatus('No draft action to redo.');
    return false;
  }
  draftUndoStack.push(draftSnapshot());
  restoreDraftSnapshot(draftRedoStack.pop());
  setEhtStatus('Draft action redone.');
  return true;
}

function cloneRouteAnchor(anchor) {
  if (!anchor) return null;
  return {
    element: anchor.element,
    point: anchor.point?.clone ? anchor.point.clone() : null,
    entryFace: anchor.entryFace || '',
    distance: Number(anchor.distance) || 0,
  };
}

function routeEditSnapshot() {
  return {
    workflow_state: routeWorkflowState,
    source_anchor: cloneRouteAnchor(routeSourceAnchor),
    destination_anchor: cloneRouteAnchor(routeDestinationAnchor),
    editing_route_id: editingRouteId,
    selected_guide_index: selectedRouteGuideIndex,
    route_orthogonal_edit: routeOrthogonalEdit,
    guide_points: pendingRouteGuidePoints.map(point => point.clone()),
    anchors: pendingRouteAnchors.map(cloneRouteAnchor),
  };
}

function restoreRouteEditSnapshot(snapshot) {
  if (!snapshot) return;
  routeWorkflowState = snapshot.workflow_state || 'idle';
  routeSourceAnchor = cloneRouteAnchor(snapshot.source_anchor);
  routeDestinationAnchor = cloneRouteAnchor(snapshot.destination_anchor);
  editingRouteId = snapshot.editing_route_id || '';
  selectedRouteGuideIndex = Number.isInteger(snapshot.selected_guide_index) ? snapshot.selected_guide_index : -1;
  routeOrthogonalEdit = Boolean(snapshot.route_orthogonal_edit);
  pendingRouteGuidePoints = (snapshot.guide_points || []).map(point => point.clone());
  pendingRouteAnchors = (snapshot.anchors || []).map(cloneRouteAnchor);
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  updateUndoState();
}

function pushRouteHistory() {
  if (routeWorkflowState !== 'edit_route') return;
  routeUndoStack.push(routeEditSnapshot());
  if (routeUndoStack.length > 80) routeUndoStack.shift();
  routeRedoStack = [];
  updateUndoState();
}

function undoRouteChange() {
  if (routeWorkflowState !== 'edit_route' || !routeUndoStack.length) return false;
  routeRedoStack.push(routeEditSnapshot());
  restoreRouteEditSnapshot(routeUndoStack.pop());
  setEhtStatus(`Route edit undone. ${routeWorkflowStatus()}`);
  return true;
}

function redoRouteChange() {
  if (routeWorkflowState !== 'edit_route' || !routeRedoStack.length) return false;
  routeUndoStack.push(routeEditSnapshot());
  restoreRouteEditSnapshot(routeRedoStack.pop());
  setEhtStatus(`Route edit redone. ${routeWorkflowStatus()}`);
  return true;
}

function clearRouteHistory() {
  routeUndoStack = [];
  routeRedoStack = [];
}

function updateOrthogonalRouteButton() {
  if (!ehtOrthogonalRouteBtn) return;
  ehtOrthogonalRouteBtn.classList.toggle('p3d-button-primary', !routeOrthogonalEdit);
  ehtOrthogonalRouteBtn.textContent = routeOrthogonalEdit ? 'Ortho Assist' : 'Centerline';
  ehtOrthogonalRouteBtn.title = routeOrthogonalEdit
    ? 'Optional assist: route is regenerated as Manhattan/orthogonal segments through guide points.'
    : 'Default drafting mode: route is drawn directly through clicked centerline points in order.';
}

function resetRouteWorkflow({ clearPreview = true } = {}) {
  routeWorkflowState = 'idle';
  routeSourceAnchor = null;
  routeDestinationAnchor = null;
  editingRouteId = '';
  draggingRouteGuideIndex = -1;
  routeGuideDragPlane = null;
  routeGuideDragStartPoint = null;
  selectedRouteGuideIndex = -1;
  controls.enabled = true;
  pendingRoutePoints = [];
  pendingRouteAnchors = [];
  pendingRouteGuidePoints = [];
  clearRouteHistory();
  if (clearPreview) clearPendingRoutePreview();
}

function routeWorkflowStatus(def = activeEhtTool ? ehtDef(activeEhtTool) : null) {
  const label = def?.label || 'Cable route';
  if (routeWorkflowState === 'select_source') {
    return `${label}: select the source component first.`;
  }
  if (routeWorkflowState === 'select_destination') {
    return `${label}: source ${draftAnchorLabel(routeSourceAnchor)} selected. Select destination component.`;
  }
  if (routeWorkflowState === 'edit_route') {
    const validation = routeValidationForPoints(pendingRoutePoints, routeSourceAnchor, routeDestinationAnchor);
    const warningText = validation.warnings.length ? ` ${validation.warnings.length} warning(s): ${routeWarningSummary(validation.warnings)}` : ' No route warnings.';
    const editMode = routeOrthogonalEdit
      ? 'Ortho Assist is on: route is Manhattan/orthogonal through guides.'
      : 'Centerline mode: click path points in order; Finish Route converts the centerline to cable geometry.';
    return `${label}: ${draftAnchorLabel(routeSourceAnchor)} -> ${draftAnchorLabel(routeDestinationAnchor)} | ${Math.max(pendingRouteGuidePoints.length - 2, 0)} guide point(s), ${formatDimension(validation.diagnostics.length_m)} m.${warningText} ${editMode} Drag guides to adjust; Delete removes the selected intermediate guide.`;
  }
  return def ? `${label}: select a source component.` : 'Select a tool, then click the model.';
}

function beginRouteWorkflow(def) {
  resetRouteWorkflow();
  routeWorkflowState = 'select_source';
  setEhtStatus(routeWorkflowStatus(def));
}

function setActiveEhtTool(tool) {
  activeEhtTool = tool || '';
  if (activeEhtTool) deactivateActiveViewerInteraction({ reason: 'eht-tool' });
  if (activeEhtTool && measureModeActive) setMeasureMode(false);
  if (activeEhtTool) movingDraftId = '';
  if (activeEhtTool) setViewerLayerVisible('eht-draft', true, { renderControls: false });
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
  if (def?.kind === 'route') {
    beginRouteWorkflow(def);
  } else {
    resetRouteWorkflow();
    setEhtStatus(def ? `${def.label}: click the model to place an element.` : 'Select a tool, then click the model.');
  }
}

function updateUndoState() {
  const routeEditing = routeWorkflowState === 'edit_route';
  if (ehtRedoBtn) ehtRedoBtn.disabled = routeEditing ? routeRedoStack.length === 0 : draftRedoStack.length === 0;
  if (ehtUndoBtn) ehtUndoBtn.disabled = routeEditing ? routeUndoStack.length === 0 : draftUndoStack.length === 0;
  if (ehtEditSelectedRouteBtn) {
    const routeSelected = selectedDraftElement()?.kind === 'route';
    ehtEditSelectedRouteBtn.disabled = !routeSelected;
  }
  if (ehtSelectedRouteControls) {
    ehtSelectedRouteControls.classList.toggle('p3d-hidden', selectedDraftElement()?.kind !== 'route');
  }
  if (ehtDeleteGuideBtn) {
    ehtDeleteGuideBtn.disabled = routeWorkflowState !== 'edit_route' || selectedRouteGuideIndex <= 0 || selectedRouteGuideIndex >= pendingRouteGuidePoints.length - 1;
  }
  updateOrthogonalRouteButton();
  renderRouteHud();
}

function selectedDraftElement() {
  return selectedDraftId ? ehtDraftElements.find(element => element.id === selectedDraftId) || null : null;
}

function isConnectableDraftElement(element) {
  return element?.kind === 'point' && !['pipe_strap'].includes(element.type);
}

function connectionPointForDraftElement(element, targetPoint = null) {
  if (!element?.object3d) return null;
  const bounds = new THREE.Box3().setFromObject(element.object3d);
  if (bounds.isEmpty()) return element.object3d.position.clone();
  const center = new THREE.Vector3();
  bounds.getCenter(center);
  if (!targetPoint) return center;
  const candidates = [];
  const addCandidate = (point, label) => candidates.push({ point, label });
  const clampedX = THREE.MathUtils.clamp(targetPoint.x, bounds.min.x, bounds.max.x);
  const clampedY = THREE.MathUtils.clamp(targetPoint.y, bounds.min.y, bounds.max.y);
  const clampedZ = THREE.MathUtils.clamp(targetPoint.z, bounds.min.z, bounds.max.z);
  if (['distribution_board', 'isolator'].includes(element.type)) {
    addCandidate(new THREE.Vector3(clampedX, bounds.min.y, center.z), 'bottom');
    addCandidate(new THREE.Vector3(clampedX, bounds.max.y, center.z), 'top');
  } else if (element.type === 'junction_box') {
    addCandidate(new THREE.Vector3(bounds.min.x, clampedY, center.z), 'left');
    addCandidate(new THREE.Vector3(bounds.max.x, clampedY, center.z), 'right');
    addCandidate(new THREE.Vector3(clampedX, bounds.min.y, center.z), 'bottom');
    addCandidate(new THREE.Vector3(clampedX, bounds.max.y, center.z), 'top');
  } else {
    addCandidate(center, 'center');
  }
  candidates.sort((a, b) => a.point.distanceToSquared(targetPoint) - b.point.distanceToSquared(targetPoint));
  const best = candidates[0] || { point: center, label: 'center' };
  return { point: best.point, label: best.label };
}

function nearestConnectableDraftAnchor(point) {
  const candidates = ehtDraftElements
    .filter(isConnectableDraftElement)
    .filter(isDraftElementVisible)
    .map(element => {
      const connection = connectionPointForDraftElement(element, point);
      const connectionPoint = connection?.point || element.object3d.position.clone();
      return {
        element,
        point: connectionPoint,
        entryFace: connection?.label || 'center',
        distance: connectionPoint.distanceTo(point),
      };
    })
    .sort((a, b) => a.distance - b.distance);
  const best = candidates[0] || null;
  if (!best) return null;
  const threshold = Math.max(worldUnitsForScreenPixels(point, 34, 0.25, 1.5), 0.35);
  return best.distance <= threshold ? best : null;
}

function connectableAnchorFromViewerEvent(event) {
  updatePointerFromViewerEvent(event);
  const connectableObjects = ehtDraftElements
    .filter(isConnectableDraftElement)
    .filter(isDraftElementVisible)
    .map(element => element.object3d)
    .filter(Boolean);
  const hits = connectableObjects.length ? raycaster.intersectObjects(connectableObjects, true) : [];
  if (hits.length) {
    const element = draftElementFromObject(hits[0].object);
    if (isConnectableDraftElement(element)) {
      const connection = connectionPointForDraftElement(element, hits[0].point);
      return {
        element,
        point: (connection?.point || hits[0].point).clone(),
        entryFace: connection?.label || 'center',
        distance: 0,
      };
    }
  }
  return nearestConnectableDraftAnchor(pointFromViewerEvent(event));
}

function draftAnchorLabel(anchor) {
  if (!anchor?.element) return '';
  return `${draftLabel(anchor.element)} ${anchor.entryFace || ''}`.trim();
}

function routeValidationForPoints(points, startAnchor = null, endAnchor = null) {
  return validateRoute((points || []).map(point => (
    point instanceof THREE.Vector3 ? { x: point.x, y: point.y, z: point.z } : point
  )), {
    sourceId: startAnchor?.element?.id || '',
    destinationId: endAnchor?.element?.id || '',
    minSegmentLengthM: 0.1,
    maxBendCount: 24,
  });
}

function routeWarningSummary(warnings = [], maxCount = 2) {
  if (!warnings.length) return 'No route warnings.';
  const shown = warnings.slice(0, maxCount).map(warning => warning.message).join(' ');
  const hidden = warnings.length > maxCount ? ` +${warnings.length - maxCount} more.` : '';
  return `${shown}${hidden}`;
}

function routeWarningBadgesHtml(warnings = []) {
  if (!warnings.length) return '<span class="p3d-state-badge">No route warnings</span>';
  return warnings.map(warning => `
    <span class="p3d-state-badge p3d-route-warning-${escapeHtml(warning.severity || 'warn')}" title="${escapeHtml(warning.message)}">
      ${escapeHtml((warning.severity || 'warn').toUpperCase())}: ${escapeHtml(warning.code || 'route')}
    </span>
  `).join('');
}

function routeProfileForPoints(points, startAnchor = null, endAnchor = null) {
  return routeProfile((points || []).map(point => (
    point instanceof THREE.Vector3 ? { x: point.x, y: point.y, z: point.z } : point
  )), {
    sourceId: startAnchor?.element?.id || '',
    destinationId: endAnchor?.element?.id || '',
    minSegmentLengthM: 0.1,
    maxBendCount: 24,
    routeMode: routeOrthogonalEdit ? 'manual_manhattan' : 'manual_direct',
    substrate: 'free_space',
  });
}

function routeProfileForElement(element) {
  if (!element || element.kind !== 'route') return null;
  return routeProfile(element.points || [], {
    sourceId: element.parameters?.source_anchor?.draft_id || '',
    destinationId: element.parameters?.destination_anchor?.draft_id || '',
    minSegmentLengthM: 0.1,
    maxBendCount: 24,
    routeMode: element.parameters?.route_method || 'manual_manhattan',
    substrate: element.parameters?.route_substrate || 'free_space',
  });
}

function routeHudHtml(title, sourceLabel, destinationLabel, profile, guideCount = null) {
  const diagnostics = profile?.diagnostics || {};
  const counts = profile?.warning_counts || {};
  const totalWarnings = counts.total || 0;
  const statusClass = counts.block ? 'p3d-route-warning-block' : counts.warn ? 'p3d-route-warning-warn' : 'p3d-route-warning-info';
  return `
    <div class="p3d-route-hud-title">
      <span>${escapeHtml(title)}</span>
      <span class="p3d-route-hud-title-actions">
        <span class="p3d-state-badge ${statusClass}">${totalWarnings ? `${totalWarnings} warning${totalWarnings === 1 ? '' : 's'}` : 'Ready'}</span>
        <button id="ehtRouteHudToggle" type="button" title="${routeHudCollapsed ? 'Expand route summary' : 'Collapse route summary'}">${routeHudCollapsed ? '+' : '-'}</button>
      </span>
    </div>
    ${routeHudCollapsed ? '' : `
      <div class="p3d-route-hud-grid">
        <div class="kv"><span>Source</span><strong>${escapeHtml(sourceLabel || '-')}</strong></div>
        <div class="kv"><span>Destination</span><strong>${escapeHtml(destinationLabel || '-')}</strong></div>
        <div class="kv"><span>Length</span><strong>${formatDimension(diagnostics.length_m || 0)} m</strong></div>
        <div class="kv"><span>Segments / Bends</span><strong>${diagnostics.segment_count || 0} / ${diagnostics.bend_count || 0}</strong></div>
        <div class="kv"><span>Guide Points</span><strong>${guideCount === null ? '-' : guideCount}</strong></div>
        <div class="kv"><span>Substrate</span><strong>${escapeHtml(profile?.substrate || 'free_space')}</strong></div>
      </div>
      <p class="p3d-route-hud-note">${escapeHtml(profile?.next_action || 'Select a route tool to begin.')}</p>
    `}
  `;
}

function renderRouteHud() {
  if (!ehtRouteHud) return;
  let html = '';
  if (routeWorkflowState === 'edit_route') {
    const profile = routeProfileForPoints(pendingRoutePoints, routeSourceAnchor, routeDestinationAnchor);
    html = routeHudHtml(
      editingRouteId ? 'Editing Route' : 'Route Preview',
      draftAnchorLabel(routeSourceAnchor),
      draftAnchorLabel(routeDestinationAnchor),
      profile,
      Math.max(pendingRouteGuidePoints.length - 2, 0),
    );
  } else {
    const selectedRoute = selectedDraftElement();
    if (selectedRoute?.kind === 'route') {
      const profile = routeProfileForElement(selectedRoute);
      html = routeHudHtml(
        'Selected Route',
        selectedRoute.parameters?.from_ref,
        selectedRoute.parameters?.to_ref,
        profile,
        selectedRoute.parameters?.guide_point_count ?? null,
      );
    }
  }
  ehtRouteHud.innerHTML = html;
  ehtRouteHud.classList.toggle('p3d-hidden', !html);
}

function serializePoint(point) {
  return point instanceof THREE.Vector3 ? [point.x, point.y, point.z] : point;
}

function routeAnchorMetadata(anchor) {
  if (!anchor?.element) return {};
  return {
    draft_id: anchor.element.id,
    entry_face: anchor.entryFace || '',
    label: draftAnchorLabel(anchor),
  };
}

function pointFromSerialized(value) {
  if (!Array.isArray(value) || value.length < 3) return null;
  const point = new THREE.Vector3(Number(value[0]), Number(value[1]), Number(value[2]));
  return [point.x, point.y, point.z].every(Number.isFinite) ? point : null;
}

function routeGuidePointsFromElement(element) {
  const savedGuides = Array.isArray(element?.parameters?.route_guide_points)
    ? element.parameters.route_guide_points
    : element?.points || [];
  const guides = savedGuides.map(pointFromSerialized).filter(Boolean);
  return guides.length >= 2 ? guides : (element?.points || []).map(pointFromSerialized).filter(Boolean);
}

function routeAnchorFromMetadata(metadata, fallbackPoint = null) {
  const draftId = metadata?.draft_id;
  const element = draftId ? ehtDraftElements.find(item => item.id === draftId) : null;
  if (!element || !isConnectableDraftElement(element)) return null;
  const fallback = fallbackPoint || element.object3d?.position || null;
  const connection = connectionPointForDraftElement(element, fallback);
  return {
    element,
    point: (connection?.point || fallback || new THREE.Vector3()).clone(),
    entryFace: metadata?.entry_face || connection?.label || 'center',
    distance: 0,
  };
}

function routeMetadataPatch(startAnchor, endAnchor) {
  const validation = routeValidationForPoints(pendingRoutePoints, startAnchor, endAnchor);
  return {
    from_ref: draftAnchorLabel(startAnchor),
    to_ref: draftAnchorLabel(endAnchor),
    route_method: routeOrthogonalEdit ? 'manhattan_guide' : 'direct_guide',
    guide_point_count: pendingRouteGuidePoints.length,
    route_guide_points: pendingRouteGuidePoints.map(serializePoint),
    route_diagnostics: validation.diagnostics,
    route_warnings: validation.warnings,
    source_anchor: routeAnchorMetadata(startAnchor),
    destination_anchor: routeAnchorMetadata(endAnchor),
  };
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

function draftOriginVector(element) {
  if (Array.isArray(element?.points?.[0])) return new THREE.Vector3(...element.points[0]);
  if (element?.object3d) return element.object3d.position.clone();
  return new THREE.Vector3();
}

function coordinateInputHtml(axis, name, value, extraAttrs = '') {
  return `
    <label class="p3d-coordinate-axis">
      <span>${escapeHtml(axis.toUpperCase())}</span>
      <input name="${escapeHtml(name)}" type="number" step="0.01" value="${escapeHtml(formatDimension(value))}" ${extraAttrs}>
    </label>
  `;
}

function coordinateRowHtml(label, controlsHtml) {
  return `
    <div class="p3d-coordinate-row">
      <span class="p3d-coordinate-label">${escapeHtml(label)}</span>
      <div class="p3d-coordinate-controls">${controlsHtml}</div>
    </div>
  `;
}

function draftPositionRows(element) {
  if (element?.kind === 'route') {
    return (element.points || []).map((point, index) => {
      const vector = Array.isArray(point) ? new THREE.Vector3(...point) : new THREE.Vector3();
      const controls = [
        coordinateInputHtml('x', `route_node_${index}_x`, vector.x, `data-route-node-index="${index}" data-route-node-axis="x"`),
        coordinateInputHtml('y', `route_node_${index}_y`, vector.y, `data-route-node-index="${index}" data-route-node-axis="y"`),
        coordinateInputHtml('z', `route_node_${index}_z`, vector.z, `data-route-node-index="${index}" data-route-node-axis="z"`),
      ].join('');
      return `
        <fieldset class="p3d-route-node-fieldset">
          <legend>N${index + 1}</legend>
          ${coordinateRowHtml('XYZ', controls)}
        </fieldset>
      `;
    }).join('');
  }
  const origin = draftOriginVector(element);
  const controls = [
    coordinateInputHtml('x', 'position_x', origin.x),
    coordinateInputHtml('y', 'position_y', origin.y),
    coordinateInputHtml('z', 'position_z', origin.z),
  ].join('');
  return coordinateRowHtml('Position', controls);
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

function selectedItemBounds() {
  const draftElement = selectedDraftElement();
  if (isViewerLayerIdVisible('eht-draft') && draftElement?.object3d) {
    return new THREE.Box3().setFromObject(draftElement.object3d);
  }
  if (isViewerLayerIdVisible('model') && selectedHighlight) {
    return new THREE.Box3().setFromObject(selectedHighlight);
  }
  return null;
}

function planeDistanceSummary(bounds = selectedItemBounds()) {
  if (!bounds || bounds.isEmpty() || !gridHelper) return null;
  const planeY = Number(gridHelper.position.y || 0);
  const bottom = bounds.min.y - planeY;
  const top = bounds.max.y - planeY;
  const center = ((bounds.min.y + bounds.max.y) / 2) - planeY;
  return { planeY, bottom, top, center };
}

function planeDistanceHtml(bounds = selectedItemBounds()) {
  const summary = planeDistanceSummary(bounds);
  if (!summary) return '';
  return [
    kvRow('Plane Δ bottom', formatSceneLength(summary.bottom)),
    kvRow('Plane Δ top', formatSceneLength(summary.top)),
    kvRow('Plane Δ center', formatSceneLength(summary.center)),
  ].join('');
}

function draftRouteValidationHtml(element) {
  if (!element || element.kind !== 'route') return '';
  const validation = validateRoute(element.points || [], {
    sourceId: element.parameters?.source_anchor?.draft_id || '',
    destinationId: element.parameters?.destination_anchor?.draft_id || '',
    minSegmentLengthM: 0.1,
    maxBendCount: 24,
  });
  const diagnostics = validation.diagnostics || {};
  const warnings = validation.warnings || [];
  return `
    <div class="p3d-route-validation">
      <div class="kv"><span>Route Diagnostics</span><strong>${formatDimension(diagnostics.length_m || 0)} m | ${diagnostics.segment_count || 0} segments | ${diagnostics.bend_count || 0} bends</strong></div>
      <div class="p3d-route-warning-list">${routeWarningBadgesHtml(warnings)}</div>
      ${warnings.length ? `<p class="meta">${escapeHtml(routeWarningSummary(warnings, 3))}</p>` : ''}
    </div>
  `;
}

function reportPlaneDistanceForSelection() {
  const summary = planeDistanceSummary();
  if (!summary) {
    setMeasurementHudVisible(true);
    setMeasurementStatus('Select a model object or EHT draft item first.');
    return false;
  }
  setMeasurementHudVisible(true);
  setMeasurementStatus(
    `Grid plane EL ${formatSceneLength(summary.planeY)} | bottom ${formatSceneLength(summary.bottom)}, top ${formatSceneLength(summary.top)}, center ${formatSceneLength(summary.center)}.`,
  );
  return true;
}

function rememberPointerDown(event) {
  pointerDownState = {
    x: event.clientX,
    y: event.clientY,
  };
  suppressNextViewerClick = false;
}

function trackPointerMove(event) {
  if (!pointerDownState) return;
  const dx = event.clientX - pointerDownState.x;
  const dy = event.clientY - pointerDownState.y;
  if ((dx * dx) + (dy * dy) > 36) suppressNextViewerClick = true;
}

function forgetPointerDown() {
  pointerDownState = null;
}

function shouldIgnoreViewerCommitClick() {
  if (!suppressNextViewerClick && !isInteracting) return false;
  suppressNextViewerClick = false;
  return true;
}

function shouldIgnoreToolPlacementClick() {
  if (!shouldIgnoreViewerCommitClick()) return false;
  setEhtStatus('Navigation gesture ignored for placement. Click without dragging to place the selected tool.');
  return true;
}

function pendingRouteGuideHandles() {
  const handles = [];
  pendingRouteGroup.traverse(node => {
    if (node.userData?.routeGuideHandle) handles.push(node);
  });
  return handles;
}

function pickPendingRouteGuideHandle(event) {
  if (routeWorkflowState !== 'edit_route' || pendingRouteGuidePoints.length <= 2) return null;
  updatePointerFromViewerEvent(event);
  const hits = raycaster.intersectObjects(pendingRouteGuideHandles(), false);
  const hit = hits.find(item => item.object?.userData?.draggableRouteGuide);
  if (!hit) return null;
  const index = Number(hit.object.userData.routeGuideIndex);
  return Number.isInteger(index) && index > 0 && index < pendingRouteGuidePoints.length - 1 ? index : null;
}

function routeGuidePointFromDragEvent(event) {
  updatePointerFromViewerEvent(event);
  const point = new THREE.Vector3();
  if (routeGuideDragPlane && raycaster.ray.intersectPlane(routeGuideDragPlane, point)) {
    return point;
  }
  return pointFromViewerEvent(event);
}

function orthogonalGuideDragPoint(point, event) {
  if (!point || !routeOrthogonalEdit || event.shiftKey || !routeGuideDragStartPoint) return point;
  const constrained = point.clone();
  const dx = Math.abs(constrained.x - routeGuideDragStartPoint.x);
  const dz = Math.abs(constrained.z - routeGuideDragStartPoint.z);
  if (dx >= dz) {
    constrained.z = routeGuideDragStartPoint.z;
  } else {
    constrained.x = routeGuideDragStartPoint.x;
  }
  constrained.y = routeGuideDragStartPoint.y;
  return constrained;
}

function beginRouteGuideDrag(event) {
  const guideIndex = pickPendingRouteGuideHandle(event);
  if (guideIndex === null) return false;
  pushRouteHistory();
  draggingRouteGuideIndex = guideIndex;
  selectedRouteGuideIndex = guideIndex;
  const guidePoint = pendingRouteGuidePoints[guideIndex];
  routeGuideDragStartPoint = guidePoint.clone();
  routeGuideDragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -guidePoint.y);
  suppressNextViewerClick = true;
  controls.enabled = false;
  renderer.domElement.style.cursor = 'grabbing';
  setEhtStatus(`Dragging guide G${guideIndex}. ${routeOrthogonalEdit ? 'Ortho Assist is on; hold Shift for temporary free planar drag.' : 'Centerline mode is on; drag freely on the current elevation plane.'} Release to keep the route preview.`);
  event.preventDefault();
  event.stopPropagation();
  return true;
}

function updateRouteGuideDrag(event) {
  if (draggingRouteGuideIndex < 0) return false;
  const nextPoint = orthogonalGuideDragPoint(routeGuidePointFromDragEvent(event), event);
  if (nextPoint) {
    pendingRouteGuidePoints[draggingRouteGuideIndex] = nextPoint.clone();
    refreshPendingRouteFromGuidePoints();
    updatePendingRoutePreview();
  }
  suppressNextViewerClick = true;
  event.preventDefault();
  event.stopPropagation();
  return true;
}

function finishRouteGuideDrag() {
  if (draggingRouteGuideIndex < 0) return false;
  const guideIndex = draggingRouteGuideIndex;
  draggingRouteGuideIndex = -1;
  selectedRouteGuideIndex = guideIndex;
  routeGuideDragPlane = null;
  routeGuideDragStartPoint = null;
  controls.enabled = true;
  renderer.domElement.style.cursor = measureModeActive ? 'crosshair' : navigationMode === 'pan' ? 'grab' : '';
  setEhtStatus(`Guide G${guideIndex} moved. ${routeWorkflowStatus()}`);
  updatePendingRoutePreview();
  updateUndoState();
  return true;
}

function selectRouteGuide(index) {
  if (routeWorkflowState !== 'edit_route') return false;
  if (!Number.isInteger(index) || index <= 0 || index >= pendingRouteGuidePoints.length - 1) return false;
  selectedRouteGuideIndex = index;
  updatePendingRoutePreview();
  updateUndoState();
  setEhtStatus(`Guide G${index} selected. Press Delete or use Delete Guide to remove it.`);
  return true;
}

function deleteSelectedRouteGuide() {
  if (routeWorkflowState !== 'edit_route' || selectedRouteGuideIndex <= 0 || selectedRouteGuideIndex >= pendingRouteGuidePoints.length - 1) {
    setEhtStatus('Select an intermediate route guide first. Source and destination cannot be deleted.');
    return false;
  }
  const deletedIndex = selectedRouteGuideIndex;
  pushRouteHistory();
  pendingRouteGuidePoints.splice(selectedRouteGuideIndex, 1);
  pendingRouteAnchors.splice(selectedRouteGuideIndex, 1);
  selectedRouteGuideIndex = Math.min(deletedIndex, pendingRouteGuidePoints.length - 2);
  if (selectedRouteGuideIndex <= 0) selectedRouteGuideIndex = -1;
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  updateUndoState();
  setEhtStatus(`Guide G${deletedIndex} deleted. Adjacent route sections reconnected.`);
  return true;
}

function handleViewerPointerDown(event) {
  rememberPointerDown(event);
  beginRouteGuideDrag(event);
}

function handleViewerPointerMove(event) {
  if (updateRouteGuideDrag(event)) return;
  trackPointerMove(event);
}

function handleViewerPointerUp() {
  finishRouteGuideDrag();
  forgetPointerDown();
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
  replaceRouteVisualChildren(element.object3d, (element.points || []).map(point => new THREE.Vector3(...point)), ehtDef(element.type), false, element.type);
  if (selectedDraftId === element.id) setDraftElementSelectedVisual(element, true);
}

function setDraftElementOrigin(element, point) {
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
}

function rememberDraftMaterialState(material) {
  if (!material || material.userData?.draftOriginalMaterial) return;
  material.userData = {
    ...(material.userData || {}),
    draftOriginalMaterial: {
      color: material.color?.getHex?.(),
      emissive: material.emissive?.getHex?.(),
      opacity: material.opacity,
      transparent: material.transparent,
    },
  };
}

function setDraftElementSelectedVisual(element, selected) {
  if (!element?.object3d) return;
  element.object3d.traverse(node => {
    if (!node.isMesh || node.isSprite || node.userData?.routeNodeLabel) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    materials.filter(Boolean).forEach(material => {
      rememberDraftMaterialState(material);
      const original = material.userData?.draftOriginalMaterial || {};
      if (selected) {
        material.color?.set?.(0x2563eb);
        material.emissive?.set?.(0x1d4ed8);
        if (material.emissiveIntensity !== undefined) material.emissiveIntensity = 0.25;
      } else {
        if (original.color !== undefined) material.color?.setHex?.(original.color);
        if (original.emissive !== undefined) material.emissive?.setHex?.(original.emissive);
        if (material.emissiveIntensity !== undefined) material.emissiveIntensity = 0;
        if (original.opacity !== undefined) material.opacity = original.opacity;
        if (original.transparent !== undefined) material.transparent = original.transparent;
      }
      material.needsUpdate = true;
    });
  });
}

function clearDraftSelectionVisual() {
  const current = selectedDraftElement();
  if (current) setDraftElementSelectedVisual(current, false);
}

function updateRouteNodeCoordinate(element, index, axis, value) {
  if (!element || element.kind !== 'route') return false;
  const point = element.points?.[index];
  const nextValue = Number(value);
  if (!Array.isArray(point) || !Number.isFinite(nextValue)) return false;
  const axisIndex = { x: 0, y: 1, z: 2 }[axis];
  if (axisIndex === undefined) return false;
  point[axisIndex] = nextValue;
  rebuildRouteGeometry(element);
  return true;
}

function liveUpdateDraftPositionFromInput(input) {
  const form = input?.form;
  const element = ehtDraftElements.find(item => item.id === form?.dataset?.draftId);
  if (!element) return;
  draftRedoStack = [];
  if (input.dataset.routeNodeIndex !== undefined) {
    const updated = updateRouteNodeCoordinate(
      element,
      Number(input.dataset.routeNodeIndex),
      input.dataset.routeNodeAxis,
      input.value,
    );
    if (updated) setEhtStatus(`${draftLabel(element)} route node updated. Save Draft Local to retain after refresh.`);
  } else {
    const x = Number(form.elements.position_x?.value);
    const y = Number(form.elements.position_y?.value);
    const z = Number(form.elements.position_z?.value);
    if ([x, y, z].every(Number.isFinite)) {
      setDraftElementOrigin(element, new THREE.Vector3(x, y, z));
      setEhtStatus(`${draftLabel(element)} position updated. Save Draft Local to retain after refresh.`);
    }
  }
  renderDraftList();
  renderViewerLayerControls();
}

function selectDraftElement(element, { frame = false } = {}) {
  if (!element) return;
  clearDraftSelectionVisual();
  clearSelection({ keepDraft: true });
  selectedDraftId = element.id;
  movingDraftId = movingDraftId === element.id ? movingDraftId : '';
  setDraftElementSelectedVisual(element, true);
  setSelectionActionsEnabled(true);
  renderDraftSelectionPanel(element);
  if (frame) {
    const bounds = new THREE.Box3().setFromObject(element.object3d);
    frameBounds(bounds);
  }
  refreshRouteNodeLabelVisibility();
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
    kvRow('Visibility', isDraftElementVisible(element) ? 'Visible' : 'Hidden'),
    kvRow('Points', element.points.length),
    element.kind === 'route' ? kvRow('Route Length', `${formatDimension(draftLength(element))} m`) : kvRow('Position', draftPositionText(element)),
    planeDistanceHtml(new THREE.Box3().setFromObject(element.object3d)),
    draftRouteValidationHtml(element),
    `<form id="ehtParameterForm" class="p3d-form" data-draft-id="${escapeHtml(element.id)}">`,
    draftPositionRows(element),
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
  pushDraftHistory();
  const x = Number(form.elements.position_x?.value);
  const y = Number(form.elements.position_y?.value);
  const z = Number(form.elements.position_z?.value);
  if ([x, y, z].every(Number.isFinite)) {
    setDraftElementOrigin(element, new THREE.Vector3(x, y, z));
  }
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

function routeReferencesDraftElement(routeElement, draftId) {
  if (!routeElement || routeElement.kind !== 'route' || !draftId) return false;
  return (
    routeElement.parameters?.source_anchor?.draft_id === draftId
    || routeElement.parameters?.destination_anchor?.draft_id === draftId
  );
}

function disposeDraftElement(element) {
  if (!element) return;
  hiddenEhtDraftIds.delete(element.id);
  element.object3d.parent?.remove(element.object3d);
  disposeObject3D(element.object3d);
}

function deleteDraftElement(element, { recordHistory = true } = {}) {
  if (!element) return;
  const label = draftLabel(element);
  const cascadeRoutes = element.kind === 'point'
    ? ehtDraftElements.filter(item => routeReferencesDraftElement(item, element.id))
    : [];
  const deleteIds = new Set([element.id, ...cascadeRoutes.map(item => item.id)]);
  if (recordHistory) pushDraftHistory();
  for (const item of ehtDraftElements.filter(candidate => deleteIds.has(candidate.id))) {
    disposeDraftElement(item);
  }
  ehtDraftElements = ehtDraftElements.filter(item => !deleteIds.has(item.id));
  if (deleteIds.has(selectedDraftId)) selectedDraftId = '';
  if (deleteIds.has(movingDraftId)) movingDraftId = '';
  if (
    routeSourceAnchor?.element?.id && deleteIds.has(routeSourceAnchor.element.id)
    || routeDestinationAnchor?.element?.id && deleteIds.has(routeDestinationAnchor.element.id)
    || editingRouteId && deleteIds.has(editingRouteId)
  ) {
    resetRouteWorkflow();
  }
  clearSelection();
  if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
  renderDraftList();
  updateUndoState();
  setEhtStatus(cascadeRoutes.length
    ? `${label} deleted with ${cascadeRoutes.length} associated cable route${cascadeRoutes.length === 1 ? '' : 's'}.`
    : `${label} deleted.`);
}

function setDraftElementHidden(element, hidden) {
  if (!element) return;
  if (hidden) {
    hiddenEhtDraftIds.add(element.id);
  } else {
    hiddenEhtDraftIds.delete(element.id);
    hiddenEhtTypes.delete(element.type);
  }
  applyDraftVisibility();
  renderDraftList();
  renderViewerLayerControls();
}

function toggleSelectedDraftVisibility() {
  const element = selectedDraftElement();
  if (!element) return false;
  const hide = isDraftElementVisible(element);
  setDraftElementHidden(element, hide);
  setEhtStatus(`${draftLabel(element)} ${hide ? 'hidden' : 'visible'} in this viewer session.`);
  renderDraftSelectionPanel(element);
  return true;
}

function hideSelectedGlbFeature() {
  if (!Number.isFinite(selectedGlbFeatureId)) return;
  hiddenGlbFeatureIds.add(selectedGlbFeatureId);
  refreshFeatureVisibilityMasks();
  clearSelection({ keepDraft: true });
  if (selectionEl) {
    selectionEl.innerHTML = [
      '<p class="meta">Selected model object hidden in this viewer session.</p>',
      modelVisibilityActionsHtml(),
    ].join('');
  }
  setStatus(`${hiddenGlbFeatureIds.size} model object${hiddenGlbFeatureIds.size === 1 ? '' : 's'} hidden in this viewer session.`);
  renderViewerLayerControls();
}

function unhideAllGlbFeatures() {
  if (!hiddenGlbFeatureIds.size) return;
  hiddenGlbFeatureIds.clear();
  refreshFeatureVisibilityMasks();
  if (selectionEl) selectionEl.textContent = 'All hidden model objects are visible again.';
  setStatus('All hidden model objects are visible again.');
  renderViewerLayerControls();
}

function hasHiddenDraftElements() {
  return hiddenEhtDraftIds.size > 0 || hiddenEhtTypes.size > 0;
}

function unhideAllViewerItems() {
  const hadModelHidden = hiddenGlbFeatureIds.size > 0;
  const hadDraftHidden = hasHiddenDraftElements();
  if (hadModelHidden) {
    hiddenGlbFeatureIds.clear();
    refreshFeatureVisibilityMasks();
  }
  if (hadDraftHidden) {
    hiddenEhtDraftIds.clear();
    hiddenEhtTypes.clear();
    applyDraftVisibility();
    renderDraftList();
  }
  if (hadModelHidden || hadDraftHidden) {
    if (selectionEl) selectionEl.textContent = 'All hidden viewer items are visible again.';
    setStatus('All hidden viewer items are visible again.');
    renderViewerLayerControls();
  }
}

function toggleModelVisibilityShortcut() {
  if (selectedDraftElement()) return toggleSelectedDraftVisibility();
  if (Number.isFinite(selectedGlbFeatureId)) {
    hideSelectedGlbFeature();
    return true;
  }
  if (hiddenGlbFeatureIds.size || hasHiddenDraftElements()) {
    unhideAllViewerItems();
    return true;
  }
  return false;
}

function moveDraftElementTo(element, point) {
  if (!element || !point) return;
  pushDraftHistory();
  setDraftElementOrigin(element, point);
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
  if (!isViewerLayerIdVisible('eht-draft')) return null;
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

function setScaleHud(text) {
  if (scaleHud) scaleHud.textContent = text;
}

function setGridScaleVisible(visible, { syncLayer = true, renderControls = true } = {}) {
  showGridScale = Boolean(visible);
  if (gridHelper) gridHelper.visible = showGridScale;
  if (axesHelper) axesHelper.visible = showGridScale;
  if (scaleHud) scaleHud.classList.toggle('p3d-hidden', !showGridScale);
  if (scaleToggleBtn) {
    scaleToggleBtn.textContent = showGridScale ? 'Grid On' : 'Grid Off';
    scaleToggleBtn.setAttribute('aria-pressed', showGridScale ? 'true' : 'false');
    scaleToggleBtn.classList.toggle('p3d-button-primary', showGridScale);
  }
  if (syncLayer) syncViewerLayerVisibility('reference-grid', showGridScale);
  if (renderControls) renderViewerLayerControls();
}

function disposeSceneHelper(helper) {
  if (!helper) return;
  scene.remove(helper);
  helper.geometry?.dispose?.();
  if (Array.isArray(helper.material)) {
    helper.material.forEach(material => material.dispose?.());
  } else {
    helper.material?.dispose?.();
  }
}

function updateReferenceGrid(bounds) {
  if (!(bounds instanceof THREE.Box3) || bounds.isEmpty()) return;
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  bounds.getSize(size);
  bounds.getCenter(center);
  const maxDim = Math.max(size.x, size.z, size.y, 1);
  const layout = gridLayoutForExtent(maxDim);
  currentGridLayout = layout;
  disposeSceneHelper(gridHelper);
  disposeSceneHelper(axesHelper);
  gridHelper = new THREE.GridHelper(layout.size, layout.divisions, 0x7f8ea3, 0xcbd5e1);
  gridHelper.material.opacity = 0.45;
  gridHelper.material.transparent = true;
  gridHelper.position.set(center.x, bounds.min.y, center.z);
  gridHelper.visible = showGridScale;
  scene.add(gridHelper);
  axesHelper = new THREE.AxesHelper(Math.max(layout.size * 0.18, 1));
  axesHelper.position.copy(gridHelper.position);
  axesHelper.visible = showGridScale;
  scene.add(axesHelper);
  setScaleHud(`Grid ${formatSceneLength(layout.step)} | X red, Y green, Z blue`);
  setGridScaleVisible(showGridScale);
  updatePlotPlanPlacement();
}

function setPlotPlanStatus(message) {
  if (plotPlanStatus) plotPlanStatus.textContent = message;
}

function plotPlanOpacityValue() {
  const opacity = Number(plotPlanOpacity?.value || 0.45);
  return Number.isFinite(opacity) ? THREE.MathUtils.clamp(opacity, 0.1, 1) : 0.45;
}

function updatePlotPlanVisibility({ syncLayer = true, renderControls = true } = {}) {
  const visible = Boolean(plotPlanVisibleToggle?.checked ?? true);
  if (plotPlanMesh) plotPlanMesh.visible = visible;
  if (plotPlanMesh?.material) {
    plotPlanMesh.material.opacity = plotPlanOpacityValue();
    plotPlanMesh.material.needsUpdate = true;
  }
  if (syncLayer) syncViewerLayerVisibility('reference-plot-plan', visible);
  if (renderControls) renderViewerLayerControls();
}

function updatePlotPlanPlacement() {
  if (!plotPlanMesh || !gridHelper) return;
  const image = plotPlanMesh.material?.map?.image;
  const aspect = image?.width && image?.height ? image.width / image.height : 1;
  const maxSize = Math.max(currentGridLayout.size || 20, 1);
  const width = aspect >= 1 ? maxSize : maxSize * aspect;
  const height = aspect >= 1 ? maxSize / aspect : maxSize;
  plotPlanMesh.geometry?.dispose?.();
  plotPlanMesh.geometry = new THREE.PlaneGeometry(width, height);
  plotPlanMesh.rotation.set(-Math.PI / 2, 0, 0);
  plotPlanMesh.position.set(gridHelper.position.x, gridHelper.position.y + 0.01, gridHelper.position.z);
  plotPlanMesh.renderOrder = -1;
  updatePlotPlanVisibility();
}

function clearPlotPlan() {
  if (plotPlanMesh) {
    scene.remove(plotPlanMesh);
    plotPlanMesh.geometry?.dispose?.();
    plotPlanMesh.material?.map?.dispose?.();
    plotPlanMesh.material?.dispose?.();
    plotPlanMesh = null;
  }
  if (plotPlanObjectUrl) {
    URL.revokeObjectURL(plotPlanObjectUrl);
    plotPlanObjectUrl = '';
  }
  if (plotPlanInput) plotPlanInput.value = '';
  syncViewerLayerVisibility('reference-plot-plan', false);
  renderViewerLayerControls();
  setPlotPlanStatus('Local image only; not saved yet.');
}

function loadPlotPlanFile(file) {
  if (!file) return;
  clearPlotPlan();
  plotPlanObjectUrl = URL.createObjectURL(file);
  setPlotPlanStatus(`Loading ${file.name}...`);
  new THREE.TextureLoader().load(
    plotPlanObjectUrl,
    texture => {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.needsUpdate = true;
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        opacity: plotPlanOpacityValue(),
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      plotPlanMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), material);
      plotPlanMesh.name = 'Local 2D plot plan overlay';
      scene.add(plotPlanMesh);
      updatePlotPlanPlacement();
      setPlotPlanStatus(`${file.name} fitted to helper grid. Local only; not saved yet.`);
    },
    undefined,
    () => {
      clearPlotPlan();
      setPlotPlanStatus('Unable to load plot plan image.');
    },
  );
}

function clearMeasurementGraphics() {
  while (measurementGroup.children.length) {
    const child = measurementGroup.children.pop();
    child.parent = null;
    disposeObject3D(child);
  }
  measurementLine = null;
}

function setMeasurementHudVisible(visible) {
  if (measurementHud) measurementHud.classList.toggle('p3d-hidden', !visible);
}

function setMeasurementStatus(text) {
  if (measurementStatus) measurementStatus.textContent = text;
}

function setVertexSnapEnabled(enabled) {
  vertexSnapEnabled = Boolean(enabled);
  if (vertexSnapToggleBtn) {
    vertexSnapToggleBtn.textContent = vertexSnapEnabled ? 'Snap Vertex On' : 'Snap Vertex Off';
    vertexSnapToggleBtn.setAttribute('aria-pressed', vertexSnapEnabled ? 'true' : 'false');
    vertexSnapToggleBtn.classList.toggle('p3d-button-primary', vertexSnapEnabled);
  }
}

function nearestFaceVertex(hit) {
  if (!vertexSnapEnabled || !hit?.object?.geometry || !Number.isInteger(hit.faceIndex)) return null;
  const geometry = hit.object.geometry;
  const positions = geometry.getAttribute?.('position');
  if (!positions) return null;
  const faceVertexIndices = [0, 1, 2].map(offset => {
    const rawIndex = hit.faceIndex * 3 + offset;
    return geometry.index ? geometry.index.getX(rawIndex) : rawIndex;
  });
  let best = null;
  let bestDistance = Infinity;
  const candidate = new THREE.Vector3();
  for (const vertexIndex of faceVertexIndices) {
    candidate.fromBufferAttribute(positions, vertexIndex);
    hit.object.localToWorld(candidate);
    const distance = candidate.distanceToSquared(hit.point);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = candidate.clone();
    }
  }
  return best;
}

function selectedMeasurementSnapObjects() {
  const draftElement = selectedDraftElement();
  if (isViewerLayerIdVisible('eht-draft') && draftElement?.object3d) return [draftElement.object3d];
  if (isViewerLayerIdVisible('model') && selectedHighlight) return [selectedHighlight];
  return [];
}

function measurementPointFromViewerEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  if (vertexSnapEnabled) {
    const snapTargets = selectedMeasurementSnapObjects();
    if (snapTargets.length) {
      const selectedHits = raycaster.intersectObjects(snapTargets, true);
      if (selectedHits.length) {
        return nearestFaceVertex(selectedHits[0]) || selectedHits[0].point.clone();
      }
      setMeasurementStatus('Snap Vertex On: click on the selected component, or turn snap off for free measurement.');
      return null;
    } else {
      setMeasurementStatus('Snap Vertex On: select a component first, or turn snap off for free measurement.');
      return null;
    }
  }
  const canPickModel = isViewerLayerIdVisible('model') && selectableMeshes.length;
  const hit = firstVisibleGlbHit(canPickModel ? raycaster.intersectObjects(selectableMeshes, false) : []);
  if (hit) return hit.point.clone();
  return pointFromViewerEvent(event);
}

function worldUnitsForScreenPixels(point, pixels, minValue = 0.004, maxValue = 0.12) {
  const distance = camera.position.distanceTo(point || controls.target);
  const viewportHeight = Math.max(renderer.domElement.clientHeight || 1, 1);
  const visibleHeight = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * Math.max(distance, 0.001);
  return THREE.MathUtils.clamp((visibleHeight / viewportHeight) * pixels, minValue, maxValue);
}

function updateMeasurementGraphicScale(object) {
  if (!object?.userData?.screenScale) return;
  const config = object.userData.screenScale;
  const worldSize = worldUnitsForScreenPixels(
    object.position,
    config.pixels,
    config.min,
    config.max,
  );
  if (config.kind === 'sprite') {
    object.scale.set(worldSize * (config.aspect || 1), worldSize, 1);
  } else {
    object.scale.setScalar(worldSize);
  }
}

function updateMeasurementGraphicsScale() {
  measurementGroup.children.forEach(updateMeasurementGraphicScale);
  ehtDraftGroup.traverse(updateMeasurementGraphicScale);
  pendingRouteGroup.traverse(updateMeasurementGraphicScale);
}

function createMeasurementMarker(point) {
  const geometry = new THREE.SphereGeometry(1, 16, 16);
  const material = new THREE.MeshBasicMaterial({ color: 0xf97316, depthTest: false });
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(point);
  marker.userData.screenScale = { kind: 'marker', pixels: 5, min: 0.004, max: 0.08 };
  updateMeasurementGraphicScale(marker);
  marker.renderOrder = 30;
  measurementGroup.add(marker);
}

function createMeasurementLine(start, end) {
  const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
  const material = new THREE.LineBasicMaterial({ color: 0xf97316, linewidth: 2, depthTest: false });
  const line = new THREE.Line(geometry, material);
  line.renderOrder = 29;
  measurementGroup.add(line);
  measurementLine = line;
}

function createCanvasLabelSprite(text, position, options = {}) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  if (!context) return null;
  const fontSize = options.fontSize || 22;
  const paddingX = options.paddingX || 12;
  const paddingY = options.paddingY || 6;
  context.font = `700 ${fontSize}px Inter, Arial, sans-serif`;
  canvas.width = Math.max(Math.ceil(context.measureText(text).width + paddingX * 2), options.minWidth || 90);
  canvas.height = fontSize + paddingY * 2;
  context.font = `700 ${fontSize}px Inter, Arial, sans-serif`;
  context.textBaseline = 'middle';
  context.fillStyle = options.fillStyle || 'rgba(255, 247, 237, 0.92)';
  context.strokeStyle = options.strokeStyle || 'rgba(249, 115, 22, 0.45)';
  context.lineWidth = 2;
  context.fillRect(1, 1, canvas.width - 2, canvas.height - 2);
  context.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
  context.fillStyle = options.textStyle || '#9a3412';
  context.fillText(text, paddingX, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  const aspect = canvas.width / canvas.height;
  sprite.position.copy(position);
  sprite.userData.screenScale = {
    kind: 'sprite',
    pixels: options.pixels || 28,
    min: options.minScale || 0.12,
    max: options.maxScale || 0.65,
    aspect,
  };
  updateMeasurementGraphicScale(sprite);
  sprite.renderOrder = options.renderOrder || 31;
  return sprite;
}

function createMeasurementLabel(text, position) {
  const sprite = createCanvasLabelSprite(text, position);
  if (sprite) measurementGroup.add(sprite);
}

function renderMeasurement() {
  clearMeasurementGraphics();
  measurementPoints.forEach(point => createMeasurementMarker(point));
  if (measurementPoints.length === 0) {
    setMeasurementStatus('Pick the first point.');
    return;
  }
  if (measurementPoints.length === 1) {
    setMeasurementStatus('First point picked. Pick the second point.');
    return;
  }
  const [start, end] = measurementPoints;
  const distance = start.distanceTo(end);
  createMeasurementLine(start, end);
  const midpoint = start.clone().add(end).multiplyScalar(0.5);
  midpoint.y += Math.max(distance * 0.04, 0.15);
  createMeasurementLabel(formatSceneLength(distance), midpoint);
  setMeasurementStatus(`${formatSceneLength(distance)} (${formatMm(distance)}). Pick again to start a new measurement.`);
}

function addMeasurementPoint(point) {
  if (!point) return;
  if (measurementPoints.length >= 2) measurementPoints = [];
  measurementPoints.push(point.clone());
  renderMeasurement();
  renderViewerLayerControls();
}

function setMeasureMode(active) {
  measureModeActive = Boolean(active);
  if (measureModeActive) {
    deactivateActiveViewerInteraction({ reason: 'measurement' });
    setActiveEhtTool('');
    movingDraftId = '';
    setViewerLayerVisible('measurement', true, { renderControls: false });
  }
  if (measureToggleBtn) {
    measureToggleBtn.textContent = measureModeActive ? 'Measuring' : 'Measure';
    measureToggleBtn.setAttribute('aria-pressed', measureModeActive ? 'true' : 'false');
    measureToggleBtn.classList.toggle('p3d-button-primary', measureModeActive);
  }
  renderer.domElement.style.cursor = measureModeActive ? 'crosshair' : navigationMode === 'pan' ? 'grab' : '';
  setMeasurementHudVisible(measureModeActive || measurementPoints.length > 0);
  if (measureModeActive && measurementPoints.length === 0) setMeasurementStatus('Pick the first point.');
}

function setNavigationMode(mode) {
  navigationMode = mode === 'pan' ? 'pan' : 'orbit';
  controls.mouseButtons.LEFT = navigationMode === 'pan' ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
  controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
  controls.mouseButtons.RIGHT = navigationMode === 'pan' ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN;
  renderer.domElement.style.cursor = measureModeActive ? 'crosshair' : navigationMode === 'pan' ? 'grab' : '';
  [quickOrbitBtn, quickPanBtn].forEach(button => button?.classList.remove('p3d-button-primary'));
  if (navigationMode === 'pan') quickPanBtn?.classList.add('p3d-button-primary');
  if (navigationMode === 'orbit') quickOrbitBtn?.classList.add('p3d-button-primary');
}

function frameFromDirection(direction) {
  const bounds = selectedDraftElement()
    ? new THREE.Box3().setFromObject(selectedDraftElement().object3d)
    : selectedHighlight
      ? new THREE.Box3().setFromObject(selectedHighlight)
      : packageBounds;
  if (!(bounds instanceof THREE.Box3) || bounds.isEmpty()) return;
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  bounds.getSize(size);
  bounds.getCenter(center);
  const radius = Math.max(size.length() * 0.5, 1);
  const viewDirection = direction.clone().normalize();
  camera.position.copy(center).add(viewDirection.multiplyScalar(radius * 2.6));
  controls.target.copy(center);
  camera.near = Math.max(radius / 500, 0.01);
  camera.far = Math.max(radius * 25, 1000);
  camera.updateProjectionMatrix();
  controls.update();
}

function quickSelectMode() {
  setMeasureMode(false);
  setActiveEhtTool('');
  movingDraftId = '';
  setNavigationMode('orbit');
}

function pointFromViewerEvent(event) {
  return pointAndNormalFromViewerEvent(event).point;
}

function pointAndNormalFromViewerEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const canPickModel = isViewerLayerIdVisible('model') && selectableMeshes.length;
  const hit = firstVisibleGlbHit(canPickModel ? raycaster.intersectObjects(selectableMeshes, false) : []);
  if (hit) {
    let normal = null;
    if (hit.face?.normal && hit.object) {
      normal = hit.face.normal.clone().transformDirection(hit.object.matrixWorld).normalize();
    }
    return { point: hit.point.clone(), normal, hit };
  }

  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -controls.target.y);
  const point = new THREE.Vector3();
  if (raycaster.ray.intersectPlane(plane, point)) return { point, normal: new THREE.Vector3(0, 1, 0), hit: null };
  return { point: controls.target.clone(), normal: null, hit: null };
}

function pointDevicePlacementFromViewerEvent(event, type) {
  const { point, normal } = pointAndNormalFromViewerEvent(event);
  const def = ehtDef(type);
  const defaults = def.defaults || {};
  if (normal) {
    const visibleNormal = normal.clone().normalize();
    const cameraSide = camera.position.clone().sub(point).normalize();
    if (visibleNormal.dot(cameraSide) < 0) visibleNormal.negate();
    const width = Math.max(Number(defaults.width_m) || 0.45, 0.05);
    const height = Math.max(Number(defaults.height_m) || 0.45, 0.05);
    const depth = Math.max(Number(defaults.depth_m) || 0.25, 0.05);
    const halfExtent = (
      Math.abs(visibleNormal.x) * width
      + Math.abs(visibleNormal.y) * height
      + Math.abs(visibleNormal.z) * depth
    ) / 2;
    return point.clone().add(visibleNormal.multiplyScalar(halfExtent));
  }
  return point;
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
  const group = new THREE.Group();
  replaceRouteVisualChildren(group, points, def, false, activeEhtTool);
  return group;
}

function cableRadiusForTool(typeOrDef, preview = false) {
  const type = typeof typeOrDef === 'string' ? typeOrDef : '';
  const base = type === 'cold_cable' ? 0.045 : type === 'tracer_mi' ? 0.035 : 0.03;
  return preview ? base * 0.75 : base;
}

function routeMaterial(def, preview = false) {
  return new THREE.MeshStandardMaterial({
    color: def.color,
    roughness: 0.55,
    metalness: 0.0,
    transparent: preview,
    opacity: preview ? 0.65 : 1,
  });
}

function routePointMarker(point, def, preview = false) {
  const geometry = new THREE.SphereGeometry(preview ? 0.08 : 0.1, 12, 12);
  const material = new THREE.MeshBasicMaterial({
    color: def.color,
    transparent: preview,
    opacity: preview ? 0.8 : 1,
    depthTest: false,
  });
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(point);
  marker.renderOrder = preview ? 26 : 10;
  return marker;
}

function routeNodeLabel(point, index, preview = false) {
  const position = point.clone();
  position.y += preview ? 0.16 : 0.22;
  const sprite = createCanvasLabelSprite(`N${index + 1}`, position, {
    fontSize: 18,
    paddingX: 8,
    paddingY: 4,
    fillStyle: preview ? 'rgba(239, 246, 255, 0.84)' : 'rgba(236, 253, 245, 0.92)',
    strokeStyle: preview ? 'rgba(37, 99, 235, 0.45)' : 'rgba(15, 118, 110, 0.45)',
    textStyle: preview ? '#1d4ed8' : '#0f766e',
    pixels: preview ? 20 : 22,
    minScale: 0.08,
    maxScale: 0.42,
    minWidth: 30,
    renderOrder: preview ? 27 : 12,
  });
  if (sprite) sprite.userData.routeNodeLabel = index + 1;
  if (sprite) sprite.visible = false;
  return sprite;
}

function manhattanRouteThroughGuides(guides) {
  const cleanGuides = (guides || []).filter(point => point instanceof THREE.Vector3);
  return suggestManhattanRoute(cleanGuides.map(point => ({ x: point.x, y: point.y, z: point.z })))
    .map(point => new THREE.Vector3(point.x, point.y, point.z));
}

function directRouteThroughGuides(guides) {
  return (guides || [])
    .filter(point => point instanceof THREE.Vector3)
    .map(point => point.clone());
}

function refreshPendingRouteFromGuidePoints() {
  pendingRoutePoints = routeOrthogonalEdit
    ? manhattanRouteThroughGuides(pendingRouteGuidePoints)
    : directRouteThroughGuides(pendingRouteGuidePoints);
}

function routeGuideHandle(point, index, total) {
  const isEndpoint = index === 0 || index === total - 1;
  const isSelected = index === selectedRouteGuideIndex;
  const geometry = new THREE.SphereGeometry(isEndpoint ? 0.105 : 0.145, 16, 16);
  const material = new THREE.MeshBasicMaterial({
    color: isSelected ? 0x2563eb : isEndpoint ? 0x0f766e : 0xf97316,
    transparent: true,
    opacity: isSelected ? 1 : isEndpoint ? 0.72 : 0.95,
    depthTest: false,
  });
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(point);
  marker.renderOrder = 34;
  marker.userData.routeGuideHandle = true;
  marker.userData.routeGuideIndex = index;
  marker.userData.draggableRouteGuide = !isEndpoint;
  return marker;
}

function renderPendingRouteGuideHandles() {
  if (routeWorkflowState !== 'edit_route' || !pendingRouteGuidePoints.length) return;
  pendingRouteGuidePoints.forEach((point, index) => {
    pendingRouteGroup.add(routeGuideHandle(point, index, pendingRouteGuidePoints.length));
  });
}

function routeNodeLabelShouldBeVisible(node) {
  let cursor = node;
  while (cursor) {
    if (cursor === pendingRouteGroup) return pendingRoutePoints.length > 0;
    if (cursor.userData?.ehtDraftId) return cursor.userData.ehtDraftId === selectedDraftId;
    cursor = cursor.parent;
  }
  return false;
}

function refreshRouteNodeLabelVisibility() {
  [ehtDraftGroup, pendingRouteGroup].forEach(group => {
    group.traverse(node => {
      if (node.userData?.routeNodeLabel) node.visible = routeNodeLabelShouldBeVisible(node);
    });
  });
}

function replaceRouteVisualChildren(group, points, def, preview = false, type = '') {
  while (group.children.length) {
    const child = group.children.pop();
    child.parent = null;
    disposeObject3D(child);
  }
  const routePoints = (points || []).filter(point => point instanceof THREE.Vector3);
  routePoints.forEach((point, index) => {
    const marker = routePointMarker(point, def, preview);
    marker.userData.routeNodeIndex = index;
    group.add(marker);
    const label = routeNodeLabel(point, index, preview);
    if (label) group.add(label);
  });
  refreshRouteNodeLabelVisibility();
  if (routePoints.length < 2) return;
  const curve = new THREE.CatmullRomCurve3(routePoints, false, 'catmullrom', 0.05);
  const radius = cableRadiusForTool(type, preview);
  const segments = Math.max(routePoints.length * 12, 16);
  const geometry = new THREE.TubeGeometry(curve, segments, radius, 8, false);
  const mesh = new THREE.Mesh(geometry, routeMaterial(def, preview));
  mesh.renderOrder = preview ? 25 : 8;
  group.add(mesh);
}

function clearPendingRoutePreview() {
  while (pendingRouteGroup.children.length) {
    const child = pendingRouteGroup.children.pop();
    child.parent = null;
    disposeObject3D(child);
  }
}

function updatePendingRoutePreview() {
  clearPendingRoutePreview();
  if (!activeEhtTool || pendingRoutePoints.length === 0) {
    refreshRouteNodeLabelVisibility();
    renderRouteHud();
    return;
  }
  const def = ehtDef(activeEhtTool);
  replaceRouteVisualChildren(pendingRouteGroup, pendingRoutePoints, def, true, activeEhtTool);
  renderPendingRouteGuideHandles();
  refreshRouteNodeLabelVisibility();
  renderRouteHud();
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
    element.object3d.visible = isViewerLayerIdVisible('eht-draft') && isDraftElementVisible(element);
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
    renderViewerLayerControls();
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
          <button type="button" class="eht-type-collapse-toggle" data-eht-type="${escapeHtml(type)}" aria-label="${collapsed ? 'Expand' : 'Collapse'} ${escapeHtml(def.label)}">${collapsed ? '+' : '-'}</button>
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
              <button type="button" class="eht-delete-row" data-draft-id="${escapeHtml(element.id)}" aria-label="Delete ${escapeHtml(draftLabel(element))}">Delete</button>
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
  ehtDraftList.querySelectorAll('.eht-delete-row').forEach(button => {
    button.addEventListener('click', event => {
      event.stopPropagation();
      const element = ehtDraftElements.find(item => item.id === button.dataset.draftId);
      if (element) deleteDraftElement(element);
    });
  });
  applyDraftVisibility();
  if (currentHierarchyQuery()) applyHierarchySearch();
  updateUndoState();
  renderViewerLayerControls();
}

function addDraftElement(type, kind, points, object3d, parameterPatch = {}, { recordHistory = true } = {}) {
  if (recordHistory) pushDraftHistory();
  const sequence = ehtDraftElements.length + 1;
  const element = {
    id: `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type,
    kind,
    sequence,
    points: points.map(point => point.toArray()),
    parameters: { ...draftDefaults(type, sequence), ...parameterPatch },
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

function draftStorageKey() {
  return `plant3d:eht-draft:${viewer.dataset.packageUrl || window.location.pathname}`;
}

function serializeDraftElements() {
  return ehtDraftElements.map(element => ({
    id: element.id,
    type: element.type,
    kind: element.kind,
    sequence: element.sequence,
    points: element.points,
    parameters: element.parameters || {},
    hidden: hiddenEhtDraftIds.has(element.id),
  }));
}

function saveDraftLayerToLocalStorage() {
  try {
    window.localStorage.setItem(draftStorageKey(), JSON.stringify({
      saved_at: new Date().toISOString(),
      elements: serializeDraftElements(),
    }));
    setEhtStatus(`${ehtDraftElements.length} draft element${ehtDraftElements.length === 1 ? '' : 's'} saved locally in this browser.`);
  } catch (error) {
    setEhtStatus(error.message || 'Unable to save draft locally.');
  }
}

function restoreDraftElement(saved) {
  const def = EHT_TOOL_DEFS[saved.type];
  if (!def || !Array.isArray(saved.points) || !saved.points.length) return null;
  const points = saved.points
    .map(point => Array.isArray(point) ? new THREE.Vector3(Number(point[0]), Number(point[1]), Number(point[2])) : null)
    .filter(point => point && [point.x, point.y, point.z].every(Number.isFinite));
  if (!points.length) return null;
  const object3d = saved.kind === 'route'
    ? createDraftRouteObject(points, def)
    : createDraftPointMesh(points[0], def);
  const element = {
    id: saved.id || `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type: saved.type,
    kind: saved.kind === 'route' ? 'route' : 'point',
    sequence: Number(saved.sequence) || ehtDraftElements.length + 1,
    points: points.map(point => point.toArray()),
    parameters: { ...draftDefaults(saved.type, Number(saved.sequence) || ehtDraftElements.length + 1), ...(saved.parameters || {}) },
    object3d,
  };
  object3d.userData.ehtDraftId = element.id;
  ehtDraftGroup.add(object3d);
  if (saved.hidden) hiddenEhtDraftIds.add(element.id);
  applyPointDimensions(element);
  ehtDraftElements.push(element);
  return element;
}

function restoreDraftLayerFromLocalStorage() {
  let saved = null;
  try {
    const raw = window.localStorage.getItem(draftStorageKey());
    if (!raw) return;
    saved = JSON.parse(raw);
  } catch (error) {
    setEhtStatus('Unable to read local draft.');
    return;
  }
  const elements = Array.isArray(saved?.elements) ? saved.elements : [];
  const restored = elements.map(restoreDraftElement).filter(Boolean);
  if (!restored.length) return;
  selectedDraftId = '';
  renderDraftList();
  applyDraftVisibility();
  setEhtStatus(`${restored.length} local draft element${restored.length === 1 ? '' : 's'} restored from this browser.`);
}

function placeEhtPoint(type, point) {
  const def = ehtDef(type);
  const mesh = createDraftPointMesh(point, def);
  addDraftElement(type, 'point', [point], mesh);
}

function finishEhtRoute() {
  refreshPendingRouteFromGuidePoints();
  if (!activeEhtTool || routeWorkflowState !== 'edit_route' || pendingRoutePoints.length < 2) {
    setEhtStatus(routeWorkflowState === 'select_source' || routeWorkflowState === 'select_destination'
      ? routeWorkflowStatus()
      : 'Select source and destination components before finishing a route.');
    return;
  }
  const startAnchor = routeSourceAnchor || pendingRouteAnchors[0] || null;
  const endAnchor = routeDestinationAnchor || pendingRouteAnchors[pendingRouteAnchors.length - 1] || null;
  if (!startAnchor || !endAnchor) {
    setEhtStatus('Cable route must have source and destination components before Finish Route.');
    return;
  }
  if (startAnchor.element?.id && startAnchor.element.id === endAnchor.element?.id) {
    setEhtStatus('Cable route must end on a different EHT component.');
    return;
  }
  const def = ehtDef(activeEhtTool);
  const metadata = routeMetadataPatch(startAnchor, endAnchor);
  const editingElement = editingRouteId ? ehtDraftElements.find(item => item.id === editingRouteId) : null;
  if (editingElement?.kind === 'route') {
    pushDraftHistory();
    editingElement.points = pendingRoutePoints.map(point => point.toArray());
    editingElement.parameters = { ...(editingElement.parameters || {}), ...metadata };
    rebuildRouteGeometry(editingElement);
    selectDraftElement(editingElement);
    setEhtStatus(`${draftLabel(editingElement)} updated from ${draftAnchorLabel(startAnchor)} to ${draftAnchorLabel(endAnchor)}. Save Draft Local to retain after refresh.`);
  } else {
    const line = createDraftRouteObject(pendingRoutePoints, def);
    addDraftElement(activeEhtTool, 'route', pendingRoutePoints, line, metadata);
    setEhtStatus(`${def.label}: connected from ${draftAnchorLabel(startAnchor)} to ${draftAnchorLabel(endAnchor)}. Save Draft Local to retain after refresh.`);
  }
  resetRouteWorkflow();
}

function cancelEhtRoute() {
  resetRouteWorkflow();
  setEhtStatus(activeEhtTool ? `${ehtDef(activeEhtTool).label}: route cancelled.` : 'Route cancelled.');
}

function setRouteSourceAnchor(anchor) {
  routeSourceAnchor = anchor;
  routeDestinationAnchor = null;
  routeWorkflowState = 'select_destination';
  pendingRouteGuidePoints = [anchor.point.clone()];
  selectedRouteGuideIndex = -1;
  refreshPendingRouteFromGuidePoints();
  pendingRouteAnchors = [anchor];
  updatePendingRoutePreview();
  setEhtStatus(routeWorkflowStatus());
}

function setRouteDestinationAnchor(anchor) {
  if (routeSourceAnchor?.element?.id && anchor?.element?.id === routeSourceAnchor.element.id) {
    setEhtStatus('Destination must be a different EHT component.');
    return;
  }
  routeDestinationAnchor = anchor;
  routeWorkflowState = 'edit_route';
  routeOrthogonalEdit = false;
  pendingRouteGuidePoints = [routeSourceAnchor.point.clone(), anchor.point.clone()];
  selectedRouteGuideIndex = -1;
  refreshPendingRouteFromGuidePoints();
  pendingRouteAnchors = [routeSourceAnchor, anchor];
  updatePendingRoutePreview();
  setEhtStatus(routeWorkflowStatus());
}

function centerlineGuideInsertIndex() {
  if (pendingRouteGuidePoints.length <= 1) return pendingRouteGuidePoints.length;
  if (selectedRouteGuideIndex > 0 && selectedRouteGuideIndex < pendingRouteGuidePoints.length - 1) {
    return selectedRouteGuideIndex + 1;
  }
  return pendingRouteGuidePoints.length - 1;
}

function distancePointToSegmentSquared(point, start, end) {
  const segment = end.clone().sub(start);
  const lengthSq = segment.lengthSq();
  if (lengthSq <= 0.000001) return point.distanceToSquared(start);
  const t = THREE.MathUtils.clamp(point.clone().sub(start).dot(segment) / lengthSq, 0, 1);
  const projection = start.clone().add(segment.multiplyScalar(t));
  return point.distanceToSquared(projection);
}

function routeGuideInsertIndex(point) {
  if (pendingRouteGuidePoints.length <= 2) return Math.max(pendingRouteGuidePoints.length - 1, 1);
  let bestIndex = Math.max(pendingRouteGuidePoints.length - 1, 1);
  let bestDistance = Infinity;
  for (let index = 1; index < pendingRouteGuidePoints.length; index += 1) {
    const segmentPoints = manhattanSegmentPoints(pendingRouteGuidePoints[index - 1], pendingRouteGuidePoints[index], { axisOrder: ['x', 'z', 'y'] });
    for (let segmentIndex = 1; segmentIndex < segmentPoints.length; segmentIndex += 1) {
      const distance = distancePointToSegmentSquared(
        point,
        new THREE.Vector3(segmentPoints[segmentIndex - 1].x, segmentPoints[segmentIndex - 1].y, segmentPoints[segmentIndex - 1].z),
        new THREE.Vector3(segmentPoints[segmentIndex].x, segmentPoints[segmentIndex].y, segmentPoints[segmentIndex].z),
      );
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = index;
      }
    }
  }
  return bestIndex;
}

function addRouteGuidePoint(point) {
  if (!routeSourceAnchor || !routeDestinationAnchor) {
    setEhtStatus(routeWorkflowStatus());
    return;
  }
  const insertAt = routeOrthogonalEdit ? routeGuideInsertIndex(point) : centerlineGuideInsertIndex();
  pushRouteHistory();
  pendingRouteGuidePoints.splice(insertAt, 0, point.clone());
  pendingRouteAnchors.splice(insertAt, 0, null);
  selectedRouteGuideIndex = insertAt;
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  setEhtStatus(routeWorkflowStatus());
}

function undoLastRouteGuidePoint() {
  if (routeWorkflowState !== 'edit_route' || pendingRouteGuidePoints.length <= 2) {
    setEhtStatus('No guide point to undo.');
    return;
  }
  pushRouteHistory();
  pendingRouteGuidePoints.splice(pendingRouteGuidePoints.length - 2, 1);
  pendingRouteAnchors.splice(Math.max(pendingRouteAnchors.length - 2, 1), 1);
  selectedRouteGuideIndex = -1;
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  setEhtStatus(routeWorkflowStatus());
}

function resetRouteGuidePath() {
  if (!routeSourceAnchor || !routeDestinationAnchor) {
    setEhtStatus(routeWorkflowStatus());
    return;
  }
  pushRouteHistory();
  pendingRouteGuidePoints = [routeSourceAnchor.point.clone(), routeDestinationAnchor.point.clone()];
  pendingRouteAnchors = [routeSourceAnchor, routeDestinationAnchor];
  selectedRouteGuideIndex = -1;
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  setEhtStatus(routeOrthogonalEdit
    ? 'Guide path reset to direct Ortho Assist route.'
    : 'Centerline reset. Click path points in order, then Finish Route.');
}

function editDraftRoute(element = selectedDraftElement()) {
  if (!element || element.kind !== 'route') return false;
  const guides = routeGuidePointsFromElement(element);
  if (guides.length < 2) {
    setEhtStatus('Unable to edit this route: no route points found.');
    return false;
  }
  const sourceAnchor = routeAnchorFromMetadata(element.parameters?.source_anchor, guides[0]);
  const destinationAnchor = routeAnchorFromMetadata(element.parameters?.destination_anchor, guides[guides.length - 1]);
  if (!sourceAnchor || !destinationAnchor) {
    setEhtStatus('Unable to edit this route: source or destination component is missing. Recreate the route.');
    return false;
  }
  setActiveEhtTool(element.type);
  editingRouteId = element.id;
  routeWorkflowState = 'edit_route';
  routeSourceAnchor = sourceAnchor;
  routeDestinationAnchor = destinationAnchor;
  routeOrthogonalEdit = element.parameters?.route_method !== 'direct_guide';
  pendingRouteGuidePoints = guides.map(point => point.clone());
  pendingRouteGuidePoints[0] = sourceAnchor.point.clone();
  pendingRouteGuidePoints[pendingRouteGuidePoints.length - 1] = destinationAnchor.point.clone();
  pendingRouteAnchors = pendingRouteGuidePoints.map(() => null);
  pendingRouteAnchors[0] = sourceAnchor;
  pendingRouteAnchors[pendingRouteAnchors.length - 1] = destinationAnchor;
  refreshPendingRouteFromGuidePoints();
  updatePendingRoutePreview();
  setEhtStatus(`Editing ${draftLabel(element)}. Click rough path points, Undo Guide, Reset Path, then Finish Route.`);
  return true;
}

function handleRouteWorkflowClick(event, def) {
  if (routeWorkflowState === 'select_source') {
    const anchor = connectableAnchorFromViewerEvent(event);
    if (!anchor) {
      setEhtStatus(`${def.label}: select a source EHT component first.`);
      return true;
    }
    setRouteSourceAnchor(anchor);
    return true;
  }
  if (routeWorkflowState === 'select_destination') {
    const anchor = connectableAnchorFromViewerEvent(event);
    if (!anchor) {
      setEhtStatus(`${def.label}: select a destination EHT component.`);
      return true;
    }
    setRouteDestinationAnchor(anchor);
    return true;
  }
  if (routeWorkflowState === 'edit_route') {
    addRouteGuidePoint(pointFromViewerEvent(event));
    return true;
  }
  beginRouteWorkflow(def);
  return true;
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
  if (def.kind === 'route') {
    return handleRouteWorkflowClick(event, def);
  }
  const point = pointDevicePlacementFromViewerEvent(event, activeEhtTool);
  placeEhtPoint(activeEhtTool, point);
  return true;
}

function undoLastDraftElement() {
  if (!ehtDraftElements.length) return;
  pushDraftHistory();
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
  if (ehtUndoGuideBtn) ehtUndoGuideBtn.addEventListener('click', undoLastRouteGuidePoint);
  if (ehtDeleteGuideBtn) ehtDeleteGuideBtn.addEventListener('click', deleteSelectedRouteGuide);
  if (ehtResetRouteBtn) ehtResetRouteBtn.addEventListener('click', resetRouteGuidePath);
  if (ehtOrthogonalRouteBtn) {
    ehtOrthogonalRouteBtn.addEventListener('click', () => {
      if (routeWorkflowState === 'edit_route') pushRouteHistory();
      routeOrthogonalEdit = !routeOrthogonalEdit;
      if (routeWorkflowState === 'edit_route') {
        refreshPendingRouteFromGuidePoints();
        updatePendingRoutePreview();
      }
      updateOrthogonalRouteButton();
      setEhtStatus(routeWorkflowState === 'edit_route'
        ? routeWorkflowStatus()
        : `Route drafting mode set to ${routeOrthogonalEdit ? 'Ortho Assist' : 'Centerline'}.`);
    });
  }
  if (ehtCancelRouteBtn) ehtCancelRouteBtn.addEventListener('click', cancelEhtRoute);
  if (ehtEditSelectedRouteBtn) ehtEditSelectedRouteBtn.addEventListener('click', () => editDraftRoute());
  if (ehtUndoBtn) ehtUndoBtn.addEventListener('click', () => {
    if (!undoRouteChange()) undoDraftChange();
  });
  if (ehtRedoBtn) ehtRedoBtn.addEventListener('click', () => {
    if (!redoRouteChange()) redoDraftChange();
  });
  if (ehtSaveLayerBtn) {
    ehtSaveLayerBtn.addEventListener('click', saveDraftLayerToLocalStorage);
  }
  if (ehtRouteHud) {
    ehtRouteHud.addEventListener('click', event => {
      if (!event.target.closest?.('#ehtRouteHudToggle')) return;
      routeHudCollapsed = !routeHudCollapsed;
      renderRouteHud();
    });
  }
  renderDraftList();
  updateOrthogonalRouteButton();
}

if (selectionEl) {
  selectionEl.addEventListener('submit', event => {
    if (event.target?.id !== 'ehtParameterForm') return;
    event.preventDefault();
    updateDraftParametersFromForm(event.target);
  });
  selectionEl.addEventListener('input', event => {
    const input = event.target;
    if (!input?.closest?.('#ehtParameterForm')) return;
    if (
      ['position_x', 'position_y', 'position_z'].includes(input.name)
      || input.dataset.routeNodeIndex !== undefined
    ) {
      liveUpdateDraftPositionFromInput(input);
    }
  });
  selectionEl.addEventListener('change', event => {
    const input = event.target;
    if (!input?.closest?.('#ehtParameterForm')) return;
    if (
      ['position_x', 'position_y', 'position_z'].includes(input.name)
      || input.dataset.routeNodeIndex !== undefined
    ) {
      liveUpdateDraftPositionFromInput(input);
    }
  });
  selectionEl.addEventListener('click', event => {
    const editRouteButton = event.target.closest?.('#ehtEditRouteBtn');
    if (editRouteButton) {
      editDraftRoute();
      return;
    }
    const moveButton = event.target.closest?.('#ehtMoveSelectedBtn');
    if (moveButton) {
      const element = selectedDraftElement();
      if (!element) return;
      movingDraftId = movingDraftId === element.id ? '' : element.id;
      if (movingDraftId) deactivateActiveViewerInteraction({ reason: 'eht-move' });
      setActiveEhtTool('');
      renderDraftSelectionPanel(element);
      setEhtStatus(movingDraftId ? `${draftLabel(element)} move mode: click a new model position.` : `${draftLabel(element)} move cancelled.`);
      return;
    }
    const deleteButton = event.target.closest?.('#ehtDeleteSelectedBtn');
    if (deleteButton) {
      const element = selectedDraftElement();
      if (element) deleteDraftElement(element);
      return;
    }
    const hideSelectedButton = event.target.closest?.('#hideSelectedModelObjectBtn');
    if (hideSelectedButton) {
      hideSelectedGlbFeature();
      return;
    }
    const unhideAllButton = event.target.closest?.('#unhideAllModelObjectsBtn');
    if (unhideAllButton) {
      unhideAllGlbFeatures();
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
    planeDistanceHtml(),
    modelVisibilityActionsHtml(featureId),
    metadataDetails(data),
  ].join('');
}

function modelVisibilityActionsHtml(featureId = null) {
  if (!Number.isFinite(Number(featureId))) {
    return hiddenGlbFeatureIds.size
      ? `<div class="p3d-toolbar p3d-selection-actions"><button type="button" id="unhideAllModelObjectsBtn">Unhide All (${hiddenGlbFeatureIds.size})</button></div>`
      : '';
  }
  const isHidden = hiddenGlbFeatureIds.has(Number(featureId));
  return [
    '<div class="p3d-toolbar p3d-selection-actions">',
    `<button type="button" id="hideSelectedModelObjectBtn" class="${isHidden ? '' : 'p3d-button-quiet'}">${isHidden ? 'Hidden' : 'Hide Selected'}</button>`,
    hiddenGlbFeatureIds.size ? `<button type="button" id="unhideAllModelObjectsBtn">Unhide All (${hiddenGlbFeatureIds.size})</button>` : '',
    '</div>',
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
  updateReferenceGrid(packageBounds);

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
  if (!material.userData?.plant3dVisibilityMask) {
    material.userData = { ...(material.userData || {}), plant3dVisibilityMask: true };
    material.onBeforeCompile = shader => {
      shader.vertexShader = shader.vertexShader
        .replace(
          '#include <common>',
          '#include <common>\nattribute float plant3dHiddenFeature;\nvarying float vPlant3dHiddenFeature;',
        )
        .replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvPlant3dHiddenFeature = plant3dHiddenFeature;',
        );
      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          '#include <common>\nvarying float vPlant3dHiddenFeature;',
        )
        .replace(
          '#include <clipping_planes_fragment>',
          '#include <clipping_planes_fragment>\nif (vPlant3dHiddenFeature > 0.5) discard;',
        );
    };
    material.customProgramCacheKey = () => 'plant3d-feature-visibility-v1';
  }
  material.needsUpdate = true;
}

function featureAttributeForGeometry(geometry) {
  return geometry?.getAttribute?.('_FEATURE_ID_0') || geometry?.getAttribute?.('_feature_id_0') || null;
}

function ensureFeatureVisibilityAttribute(mesh) {
  const geometry = mesh?.geometry;
  const positions = geometry?.getAttribute?.('position');
  if (!geometry || !positions || geometry.getAttribute('plant3dHiddenFeature')) return;
  geometry.setAttribute('plant3dHiddenFeature', new THREE.Float32BufferAttribute(new Float32Array(positions.count), 1));
}

function updateFeatureVisibilityForMesh(mesh) {
  const geometry = mesh?.geometry;
  const hiddenAttribute = geometry?.getAttribute?.('plant3dHiddenFeature');
  const featureAttribute = featureAttributeForGeometry(geometry);
  if (!hiddenAttribute || !featureAttribute) return;
  for (let index = 0; index < hiddenAttribute.count; index += 1) {
    const featureId = Math.round(featureAttribute.getX(index));
    hiddenAttribute.setX(index, hiddenGlbFeatureIds.has(featureId) ? 1 : 0);
  }
  hiddenAttribute.needsUpdate = true;
}

function refreshFeatureVisibilityMasks() {
  selectableMeshes.forEach(updateFeatureVisibilityForMesh);
}

function featureIdFromHit(hit) {
  const geometry = hit.object?.geometry;
  if (!geometry || !Number.isInteger(hit.faceIndex)) return null;
  const featureAttribute = featureAttributeForGeometry(geometry);
  if (!featureAttribute) return null;

  const firstVertex = hit.faceIndex * 3;
  const vertexIndex = geometry.index ? geometry.index.getX(firstVertex) : firstVertex;
  const featureId = featureAttribute.getX(vertexIndex);
  return Number.isFinite(featureId) ? Math.round(featureId) : null;
}

function firstVisibleGlbHit(hits) {
  if (!isViewerLayerIdVisible('model')) return null;
  return (hits || []).find(hit => {
    const featureId = featureIdFromHit(hit);
    return !Number.isFinite(featureId) || !hiddenGlbFeatureIds.has(featureId);
  }) || null;
}

function disposeObject3D(object) {
  object.traverse(node => {
    if (node.geometry) node.geometry.dispose();
    if (node.material && !node.userData?.isSelectionHighlight) {
      if (Array.isArray(node.material)) {
        node.material.forEach(material => {
          material.map?.dispose?.();
          material.dispose?.();
        });
      } else {
        node.material.map?.dispose?.();
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
      ensureFeatureVisibilityAttribute(node);
      updateFeatureVisibilityForMesh(node);
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
    renderViewerLayerControls();
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
  } else {
    await loadJsonPackage(pkg, started);
  }
  publishViewerPackageLoaded(pkg);
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
  renderViewerLayerControls();
}

async function loadGlbPackage(pkg, started) {
  runtimeStats.renderMode = 'glb-sidecar';
  indexPackageObjects(pkg);
  featureIndex = new Map();
  featureSpanIndex = new Map();
  hiddenGlbFeatureIds = new Set();
  selectableMeshes = [];
  prepareGlbTileStates(pkg);
  const approximateBounds = approximatePackageBounds(pkg);
  frameScene(approximateBounds);
  const elapsedMs = Math.round(performance.now() - started);
  setGlbRuntimeMetrics(pkg, elapsedMs);
  setStatus(`Prepared GLB tile stream with ${glbTileStates.length} tile(s) in ${elapsedMs} ms. Loading visible tiles...`);
  await updateGlbTileStreaming(pkg, true);
  renderViewerLayerControls();
}

function clearSelection({ keepDraft = false } = {}) {
  if (selectedHighlight) {
    selectedHighlight.parent?.remove(selectedHighlight);
    selectedHighlight.geometry?.dispose?.();
    selectedHighlight = null;
  }
  selectedMesh = null;
  selectedGlbFeatureId = null;
  selectedModelAnchorSourcePoint = null;
  if (!keepDraft) {
    clearDraftSelectionVisual();
    selectedDraftId = '';
    movingDraftId = '';
    refreshRouteNodeLabelVisibility();
    renderDraftList();
  }
  setSelectionActionsEnabled(false);
}

async function showSelection(mesh, hit = null) {
  clearSelection();
  selectedMesh = mesh;
  selectedModelAnchorSourcePoint = hit?.point ? renderPointToSourcePoint(hit.point) : null;
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

  selectedGlbFeatureId = featureId;
  selectedModelAnchorSourcePoint = hit?.point ? renderPointToSourcePoint(hit.point) : null;
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

function updatePointerFromViewerEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
}

async function selectItemFromViewerEvent(event, { clearOnMiss = true } = {}) {
  const pickStarted = performance.now();
  updatePointerFromViewerEvent(event);
  const draftElement = pickDraftElement();
  if (draftElement) {
    runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
    renderMetrics();
    selectDraftElement(draftElement);
    return 'draft';
  }
  if (!selectableMeshes.length) {
    runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
    renderMetrics();
    if (clearOnMiss && selectionEl) selectionEl.textContent = 'Object picking is not available for this package format yet.';
    return '';
  }
  const hits = raycaster.intersectObjects(selectableMeshes, false);
  runtimeStats.pickLatencyMs = Math.round(performance.now() - pickStarted);
  renderMetrics();
  const hit = firstVisibleGlbHit(hits);
  if (!hit) {
    if (clearOnMiss) {
      clearSelection();
      if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
    }
    return '';
  }
  if (hit.object?.userData?.packageFormat === 'GLB') {
    await showGlbFeatureSelection(hit);
    return 'model';
  }
  await showSelection(hit.object, hit);
  return 'model';
}

function pick(event) {
  hideContextMenu();
  if (dispatchViewerInteractionClick(event)) {
    return;
  }
  if (measureModeActive) {
    if (suppressNextViewerClick) {
      suppressNextViewerClick = false;
      return;
    }
    addMeasurementPoint(measurementPointFromViewerEvent(event));
    return;
  }
  if ((activeEhtTool || movingDraftId) && shouldIgnoreToolPlacementClick()) {
    return;
  }
  if (handleEhtToolClick(event)) {
    return;
  }
  selectItemFromViewerEvent(event);
}

async function focusFromViewerDoubleClick(event) {
  if (activeEhtTool || movingDraftId || measureModeActive) return;
  const picked = await selectItemFromViewerEvent(event, { clearOnMiss: false });
  if (picked) fitSelectedObject();
}

function contextMenuButton(action) {
  return viewerContextMenu?.querySelector(`[data-context-action="${action}"]`);
}

function setContextActionEnabled(action, enabled) {
  const button = contextMenuButton(action);
  if (button) button.disabled = !enabled;
}

function updateContextMenuState() {
  const draftElement = selectedDraftElement();
  const hasDraftSelection = Boolean(draftElement);
  const hasModelSelection = Number.isFinite(selectedGlbFeatureId);
  const hasAnySelection = hasDraftSelection || hasModelSelection || Boolean(selectedHighlight);
  const hideButton = contextMenuButton('hide');
  const unhideButton = contextMenuButton('unhide');
  if (hideButton) {
    const label = hasDraftSelection && !isDraftElementVisible(draftElement) ? 'Unhide Selected' : 'Hide Selected';
    hideButton.firstChild.nodeValue = label;
  }
  if (unhideButton) {
    unhideButton.firstChild.nodeValue = `Unhide All${hiddenGlbFeatureIds.size || hasHiddenDraftElements() ? '' : ''}`;
  }
  setContextActionEnabled('fit', hasAnySelection);
  setContextActionEnabled('hide', hasDraftSelection || hasModelSelection);
  setContextActionEnabled('unhide', hiddenGlbFeatureIds.size > 0 || hasHiddenDraftElements());
  setContextActionEnabled('move-draft', hasDraftSelection);
  setContextActionEnabled('delete-draft', hasDraftSelection);
}

function hideContextMenu() {
  if (!viewerContextMenu) return;
  viewerContextMenu.classList.add('p3d-hidden');
}

function placeContextMenu(event) {
  if (!viewerContextMenu) return;
  updateContextMenuState();
  viewerContextMenu.classList.remove('p3d-hidden');
  const menuRect = viewerContextMenu.getBoundingClientRect();
  const left = Math.min(event.clientX, window.innerWidth - menuRect.width - 8);
  const top = Math.min(event.clientY, window.innerHeight - menuRect.height - 8);
  viewerContextMenu.style.left = `${Math.max(left, 8)}px`;
  viewerContextMenu.style.top = `${Math.max(top, 8)}px`;
}

async function showContextMenu(event) {
  event.preventDefault();
  event.stopPropagation();
  await selectItemFromViewerEvent(event, { clearOnMiss: false });
  placeContextMenu(event);
}

function moveSelectedDraftFromContext() {
  const element = selectedDraftElement();
  if (!element) return;
  movingDraftId = movingDraftId === element.id ? '' : element.id;
  setActiveEhtTool('');
  renderDraftSelectionPanel(element);
  setEhtStatus(movingDraftId ? `${draftLabel(element)} move mode: click a new model position.` : `${draftLabel(element)} move cancelled.`);
}

function executeContextAction(action) {
  hideContextMenu();
  if (action === 'orbit') {
    setNavigationMode('orbit');
  } else if (action === 'pan') {
    setNavigationMode('pan');
  } else if (action === 'fit') {
    fitSelectedObject();
  } else if (action === 'hide') {
    toggleModelVisibilityShortcut();
  } else if (action === 'unhide') {
    unhideAllViewerItems();
  } else if (action === 'move-draft') {
    moveSelectedDraftFromContext();
  } else if (action === 'delete-draft') {
    const element = selectedDraftElement();
    if (element) deleteDraftElement(element);
  }
}

function isTypingTarget(target) {
  const tagName = target?.tagName?.toLowerCase?.() || '';
  return target?.isContentEditable || ['input', 'textarea', 'select'].includes(tagName);
}

function handleViewerShortcut(event) {
  if (isTypingTarget(event.target)) return false;
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === 'z') {
    event.preventDefault();
    if (event.shiftKey) {
      if (!redoRouteChange()) redoDraftChange();
    } else if (!undoRouteChange()) {
      undoDraftChange();
    }
    return true;
  }
  if (event.ctrlKey && key === 'h') {
    event.preventDefault();
    toggleModelVisibilityShortcut();
    return true;
  }
  if (event.ctrlKey || event.metaKey || event.altKey) return false;
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (routeWorkflowState === 'edit_route' && selectedRouteGuideIndex > 0) {
      event.preventDefault();
      deleteSelectedRouteGuide();
      return true;
    }
    const element = selectedDraftElement();
    if (element) {
      event.preventDefault();
      deleteDraftElement(element);
      return true;
    }
    return false;
  }
  if (key === 'p') {
    setNavigationMode('pan');
    return true;
  } else if (key === 'o' || key === 'r') {
    setNavigationMode('orbit');
    return true;
  } else if (key === 'f') {
    fitSelectedObject();
    return true;
  }
  return false;
}

function animate() {
  const now = performance.now();
  runtimeStats.frameMs = Number((now - lastFrameAt).toFixed(1));
  lastFrameAt = now;
  controls.update();
  updateMeasurementGraphicsScale();
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
if (measureToggleBtn) {
  measureToggleBtn.addEventListener('click', () => setMeasureMode(!measureModeActive));
}
if (planeDistanceBtn) {
  planeDistanceBtn.addEventListener('click', reportPlaneDistanceForSelection);
}
if (scaleToggleBtn) {
  scaleToggleBtn.addEventListener('click', () => setGridScaleVisible(!showGridScale));
}
if (vertexSnapToggleBtn) {
  vertexSnapToggleBtn.addEventListener('click', () => setVertexSnapEnabled(!vertexSnapEnabled));
}
if (quickSelectBtn) quickSelectBtn.addEventListener('click', quickSelectMode);
if (quickOrbitBtn) quickOrbitBtn.addEventListener('click', () => setNavigationMode('orbit'));
if (quickPanBtn) quickPanBtn.addEventListener('click', () => setNavigationMode('pan'));
if (quickTopBtn) quickTopBtn.addEventListener('click', () => frameFromDirection(new THREE.Vector3(0, 1, 0)));
if (quickFrontBtn) quickFrontBtn.addEventListener('click', () => frameFromDirection(new THREE.Vector3(0, 0, 1)));
if (quickSideBtn) quickSideBtn.addEventListener('click', () => frameFromDirection(new THREE.Vector3(1, 0, 0)));
if (quickFitBtn) quickFitBtn.addEventListener('click', () => {
  if (!fitSelectionBtn?.disabled) {
    fitSelectedObject();
  } else {
    frameScene();
  }
});
if (plotPlanInput) {
  plotPlanInput.addEventListener('change', () => {
    const file = plotPlanInput.files?.[0];
    if (file) loadPlotPlanFile(file);
  });
}
if (plotPlanVisibleToggle) {
  plotPlanVisibleToggle.addEventListener('change', updatePlotPlanVisibility);
}
if (plotPlanOpacity) {
  plotPlanOpacity.addEventListener('input', updatePlotPlanVisibility);
}
if (plotPlanClearBtn) {
  plotPlanClearBtn.addEventListener('click', clearPlotPlan);
}
if (showAllLayersBtn) {
  showAllLayersBtn.addEventListener('click', showAllViewerLayers);
}
if (hideOverlayLayersBtn) {
  hideOverlayLayersBtn.addEventListener('click', hideOverlayViewerLayers);
}
renderer.domElement.addEventListener('click', pick);
renderer.domElement.addEventListener('dblclick', focusFromViewerDoubleClick);
renderer.domElement.addEventListener('pointerdown', handleViewerPointerDown);
renderer.domElement.addEventListener('pointermove', handleViewerPointerMove);
renderer.domElement.addEventListener('pointerup', handleViewerPointerUp);
renderer.domElement.addEventListener('pointercancel', handleViewerPointerUp);
renderer.domElement.addEventListener('contextmenu', showContextMenu);
if (viewerContextMenu) {
  viewerContextMenu.addEventListener('click', event => {
    const button = event.target.closest?.('[data-context-action]');
    if (!button || button.disabled) return;
    executeContextAction(button.dataset.contextAction);
  });
}
document.addEventListener('click', event => {
  if (!viewerContextMenu || viewerContextMenu.classList.contains('p3d-hidden')) return;
  if (!viewerContextMenu.contains(event.target)) hideContextMenu();
});
bindEhtTools();
restoreDraftLayerFromLocalStorage();
refreshRouteNodeLabelVisibility();
setGridScaleVisible(showGridScale);
setVertexSnapEnabled(vertexSnapEnabled);
setNavigationMode('orbit');
publishViewerExtensionHost();
window.addEventListener('keydown', event => {
  if (handleViewerShortcut(event)) return;
  if (event.key === 'Escape') {
    hideContextMenu();
    if (cancelActiveViewerInteraction()) {
      return;
    } else if (activeEhtTool || movingDraftId || pendingRoutePoints.length) {
      resetRouteWorkflow();
      movingDraftId = '';
      setActiveEhtTool('');
      setEhtStatus('Drawing tool cancelled.');
    } else if (measureModeActive) {
      measurementPoints = [];
      clearMeasurementGraphics();
      setMeasureMode(false);
      setMeasurementStatus('Pick the first point.');
    } else {
      clearSelection();
      if (selectionEl) selectionEl.textContent = 'Click an object in the viewer.';
    }
  }
});
resize();
animate();

loadPackage().catch(error => {
  setStatus(error.message || 'Unable to load package.');
});
