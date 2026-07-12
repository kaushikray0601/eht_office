const RACEWAY_LAYER_ID = 'raceway-overlay';
const RACEWAY_INTERACTION_ID = 'raceway-centerline-authoring';
const CATALOG_URL = '/raceway/catalog/';
const TELEMETRY_EVENTS_URL = '/telemetry/events/';
const SOURCE_COORDINATE_FRAME = 'source_xyz_m';
const HISTORY_LIMIT = 80;
const NODE_HANDLE_SCREEN_PX = 5;
const NODE_HANDLE_SELECTED_SCREEN_PX = 6;
const NODE_HIT_TARGET_SCREEN_PX = 18;
const PROXY_FACE_OPACITY = 0.14;
const PROXY_FACE_SELECTED_OPACITY = 0.24;
const PROXY_BOTTOM_SHADE = 1.12;
const PROXY_SIDE_SHADE = 0.72;
const TELEMETRY_FLUSH_DELAY_MS = 750;
const TELEMETRY_MAX_BATCH_SIZE = 50;
const RACEWAY_MEASUREMENT_SNAP_KINDS = new Set([
  'side-rail',
  'lower-edge',
  'depth-tick',
  'rung',
  'tray-cross-member',
]);
const ORIENTATION_SCHEMA = 'raceway.orientation.v0';
const orientationPresets = [
  { id: 'open_up', label: 'Open Up', quarterTurns: 0 },
  { id: 'roll_right', label: 'Roll Right', quarterTurns: 1 },
  { id: 'open_down', label: 'Open Down', quarterTurns: 2 },
  { id: 'roll_left', label: 'Roll Left', quarterTurns: 3 },
];
const DEFAULT_ORIENTATION_PRESET = orientationPresets[0].id;
const TELEMETRY_FORBIDDEN_ID_KEYS = new Set([
  'id',
  'pk',
  'layer_id',
  'run_id',
  'node_id',
  'edge_id',
  'family_id',
  'size_id',
  'source_model_id',
  'render_package_id',
  'model_object_id',
]);
const TELEMETRY_CLIENT = (() => {
  try {
    const src = document.currentScript?.getAttribute?.('src') || '';
    const version = new URL(src, window.location.href).searchParams.get('v') || '';
    return version ? `raceway-overlay@${version}` : 'raceway-overlay';
  } catch (_error) {
    return 'raceway-overlay';
  }
})();

let catalog = [];

const services = [
  { id: 'power', label: 'Power', color: 0x2563eb },
  { id: 'control', label: 'Control', color: 0x0f766e },
  { id: 'instrument', label: 'Instrument', color: 0xca8a04 },
  { id: 'telecom', label: 'Telecom', color: 0x7c3aed },
];

const segmentDirections = [
  { id: 'plus_x', label: '+X East', dx: 1, dy: 0, dz: 0 },
  { id: 'minus_x', label: '-X West', dx: -1, dy: 0, dz: 0 },
  { id: 'plus_y', label: '+Y North', dx: 0, dy: 1, dz: 0 },
  { id: 'minus_y', label: '-Y South', dx: 0, dy: -1, dz: 0 },
  { id: 'plus_z', label: '+EL Up', dx: 0, dy: 0, dz: 1 },
  { id: 'minus_z', label: '-EL Down', dx: 0, dy: 0, dz: -1 },
];

const state = {
  runs: [],
  activeRunId: '',
  selectedNodeIndex: -1,
  mode: 'idle',
  familyId: '',
  sizeId: '',
  serviceClass: services[0].id,
  elevationM: 0,
  elevationInitialized: false,
  catalogLoaded: false,
  persistenceLoaded: false,
  persistenceLoading: false,
  persistenceReady: false,
  contextKey: '',
  layerId: null,
  layerUrl: '',
  runsUrl: '',
  graphProjection: null,
  graphLoaded: false,
  graphLoading: false,
  graphError: '',
  scheduleProjection: null,
  scheduleLoaded: false,
  scheduleLoading: false,
  scheduleError: '',
  fittingProjection: null,
  fittingsLoaded: false,
  fittingsLoading: false,
  fittingsError: '',
  undoStack: [],
  redoStack: [],
  orthoMode: false,
  showProxyFaces: true,
  orientationPreset: DEFAULT_ORIENTATION_PRESET,
  segmentDirection: segmentDirections[0].id,
  segmentLengthM: 6,
  connectSource: null,
  warningFocus: null,
};

const actionLabels = {
  start: 'Start raceway draw',
  'continue-run': 'Continue active run',
  finish: 'Finish active run',
  undo: 'Undo last raceway edit',
  redo: 'Redo last undone raceway edit',
  cancel: 'Cancel active raceway command',
  'select-node-mode': 'Select node on canvas',
  'move-node': 'Move selected node',
  'delete-node': 'Delete selected node',
  'connect-node': 'Connect selected endpoint to an existing raceway node',
  'anchor-node': 'Anchor selected node to selected plant object',
  'clear-anchor': 'Clear selected node anchor',
  save: 'Save draft raceways',
  reload: 'Reload saved raceways',
  'refresh-graph': 'Refresh raceway graph warnings',
  'refresh-schedule': 'Refresh raceway schedule totals',
  'refresh-fittings': 'Refresh fitting placeholders',
  'open-schedule-csv': 'Download raceway schedule CSV',
  'delete-run': 'Delete active run',
  'add-segment': 'Add typed segment from the last node',
  'toggle-ortho': 'Toggle orthogonal drawing assist',
  'toggle-surfaces': 'Toggle shaded raceway faces',
};

const actionShortcuts = {
  start: 'S',
  'continue-run': 'C',
  finish: 'F',
  undo: 'Ctrl+Z',
  redo: 'Ctrl+Shift+Z / Ctrl+Y',
  cancel: 'Esc',
  'select-node-mode': 'N',
  'move-node': 'M',
  'delete-node': 'Del',
  'connect-node': 'J',
  'anchor-node': 'A',
  'clear-anchor': 'Shift+A',
  save: 'Ctrl+S',
  reload: 'R',
  'refresh-graph': 'G',
  'refresh-schedule': 'B',
  'refresh-fittings': 'T',
  'open-schedule-csv': 'Shift+B',
  'delete-run': 'Shift+Del',
  'add-segment': 'Enter in segment fields',
  'toggle-ortho': 'O',
  'toggle-surfaces': 'Shift+V',
};

let layer = null;
let runtime = null;
let interaction = null;
let panel = null;
let statusEl = null;
let summaryEl = null;
let graphWarningsEl = null;
let scheduleSummaryEl = null;
let fittingSummaryEl = null;
let warningBadgeEl = null;
let runListEl = null;
let nodeListEl = null;
let inspectorEl = null;
let bootstrapAttempts = 0;
let persistenceBootstrapQueued = false;
let catalogLoadPromise = null;
let telemetryQueue = [];
let telemetryFlushTimer = null;
const telemetryShownSignatures = new Set();
const telemetryLifecycleKeys = new Map();

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatM(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : '0.000';
}

function sameId(left, right) {
  return String(left ?? '') === String(right ?? '');
}

function activeFamily() {
  return catalog.find(family => sameId(family.id, state.familyId)) || catalog[0] || null;
}

function activeSize() {
  const family = activeFamily();
  if (!family) return null;
  return family.sizes.find(size => sameId(size.id, state.sizeId)) || family.sizes[0] || null;
}

function serviceFor(id = state.serviceClass) {
  return services.find(service => service.id === id) || services[0];
}

function orientationPresetFor(id) {
  return orientationPresets.find(preset => preset.id === id) || orientationPresets[0];
}

function normalizedOrientation(value = DEFAULT_ORIENTATION_PRESET) {
  const preset = orientationPresetFor(typeof value === 'object' ? value?.preset : value);
  return {
    schema: ORIENTATION_SCHEMA,
    preset: preset.id,
    quarter_turns: preset.quarterTurns,
    label: preset.label,
  };
}

function runOrientation(run) {
  return normalizedOrientation(run?.orientation || run?.metadata?.orientation || state.orientationPreset);
}

function orientationLabel(run) {
  return runOrientation(run).label;
}

function activeRun() {
  return state.runs.find(run => run.id === state.activeRunId) || null;
}

function markRunDirty(run = activeRun()) {
  if (run) run.dirty = true;
}

function hasUnsavedLocalChanges() {
  return state.runs.some(run => !run.serverRunId || run.dirty);
}

function runPersistenceLabel(run) {
  if (!run?.serverRunId) return 'unsaved';
  return run.dirty ? 'unsaved changes' : 'saved';
}

function clonePlain(value) {
  if (typeof structuredClone === 'function') return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

function captureHistorySnapshot() {
  return {
    runs: clonePlain(state.runs),
    activeRunId: state.activeRunId,
    selectedNodeIndex: state.selectedNodeIndex,
    mode: state.mode,
    familyId: state.familyId,
    sizeId: state.sizeId,
    serviceClass: state.serviceClass,
    elevationM: state.elevationM,
    elevationInitialized: state.elevationInitialized,
    orientationPreset: state.orientationPreset,
  };
}

function restoreHistorySnapshot(snapshot) {
  state.connectSource = null;
  state.runs = clonePlain(snapshot.runs || []);
  state.activeRunId = snapshot.activeRunId || state.runs[0]?.id || '';
  if (!state.runs.some(run => run.id === state.activeRunId)) {
    state.activeRunId = state.runs[0]?.id || '';
  }
  state.selectedNodeIndex = Number(snapshot.selectedNodeIndex);
  if (!Number.isInteger(state.selectedNodeIndex)) state.selectedNodeIndex = -1;
  const run = activeRun();
  if (!run || state.selectedNodeIndex >= run.nodes.length) {
    state.selectedNodeIndex = run?.nodes.length ? run.nodes.length - 1 : -1;
  }
  state.familyId = snapshot.familyId || state.familyId;
  state.sizeId = snapshot.sizeId || state.sizeId;
  state.serviceClass = snapshot.serviceClass || state.serviceClass;
  state.elevationM = Number(snapshot.elevationM) || 0;
  state.elevationInitialized = Boolean(snapshot.elevationInitialized);
  state.orientationPreset = orientationPresetFor(snapshot.orientationPreset).id;
  state.mode = snapshot.mode || 'idle';
  if (!run || state.mode === 'idle') {
    state.mode = 'idle';
    interaction?.deactivate?.();
  } else {
    interaction?.activate?.();
  }
  renderRaceway();
  renderPanel({ forceInspector: true });
}

function pushUndo(label = 'Raceway edit') {
  state.undoStack.push({ label, snapshot: captureHistorySnapshot() });
  if (state.undoStack.length > HISTORY_LIMIT) state.undoStack.shift();
  state.redoStack = [];
}

function clearHistory() {
  state.undoStack = [];
  state.redoStack = [];
}

function undoRacewayEdit() {
  const entry = state.undoStack.pop();
  if (!entry) {
    setStatus('Nothing to undo.');
    renderPanel();
    return;
  }
  state.redoStack.push({ label: entry.label, snapshot: captureHistorySnapshot() });
  restoreHistorySnapshot(entry.snapshot);
  setStatus(`${entry.label} undone.`);
  renderPanel({ forceInspector: true });
}

function redoRacewayEdit() {
  const entry = state.redoStack.pop();
  if (!entry) {
    setStatus('Nothing to redo.');
    renderPanel();
    return;
  }
  state.undoStack.push({ label: entry.label, snapshot: captureHistorySnapshot() });
  restoreHistorySnapshot(entry.snapshot);
  setStatus(`${entry.label} redone.`);
  renderPanel({ forceInspector: true });
}

function actionTooltip(action, disabledReason = '') {
  const label = disabledReason || actionLabels[action] || 'Raceway command';
  const shortcut = actionShortcuts[action];
  return shortcut ? `${label}. Shortcut: ${shortcut}.` : label;
}

function segmentDirectionById(id = state.segmentDirection) {
  return segmentDirections.find(direction => direction.id === id) || segmentDirections[0];
}

function clearGraphProjection() {
  state.graphProjection = null;
  state.graphLoaded = false;
  state.graphLoading = false;
  state.graphError = '';
}

function clearScheduleProjection() {
  state.scheduleProjection = null;
  state.scheduleLoaded = false;
  state.scheduleLoading = false;
  state.scheduleError = '';
}

function clearFittingProjection() {
  state.fittingProjection = null;
  state.fittingsLoaded = false;
  state.fittingsLoading = false;
  state.fittingsError = '';
}

function graphWarnings() {
  const warnings = state.graphProjection?.warnings;
  return Array.isArray(warnings) ? warnings : [];
}

function scheduleWarnings() {
  const warnings = state.scheduleProjection?.warnings;
  return Array.isArray(warnings) ? warnings : [];
}

function allSizes() {
  return catalog.flatMap(family => family.sizes.map(size => ({ ...size, family })));
}

function catalogFamilyById(id) {
  return catalog.find(family => sameId(family.id, id)) || null;
}

function catalogSizeById(id) {
  const match = allSizes().find(item => sameId(item.id, id));
  return match ? { ...match, family: match.family } : null;
}

function normalizeFamily(rawFamily) {
  const sizes = Array.isArray(rawFamily.sizes) ? rawFamily.sizes : [];
  return {
    id: String(rawFamily.id || ''),
    code: String(rawFamily.code || ''),
    label: String(rawFamily.name || rawFamily.code || 'Raceway'),
    kind: String(rawFamily.kind || ''),
    material: String(rawFamily.material || ''),
    standardBasis: String(rawFamily.standard_basis || ''),
    isValidated: Boolean(rawFamily.is_validated),
    sizes: sizes
      .filter(size => size && size.is_active !== false)
      .map(size => ({
        id: String(size.id || ''),
        code: String(size.code || ''),
        label: String(size.label || `${size.width_mm} x ${size.depth_mm} mm`),
        widthMm: Number(size.width_mm) || 0,
        depthMm: Number(size.depth_mm) || 0,
      }))
      .filter(size => size.id && size.widthMm > 0 && size.depthMm > 0),
  };
}

function initializeCatalogSelection() {
  if (!catalog.length) {
    state.familyId = '';
    state.sizeId = '';
    return;
  }
  if (!catalogFamilyById(state.familyId)) state.familyId = catalog[0].id;
  if (!activeSize()) state.sizeId = activeFamily()?.sizes[0]?.id || '';
}

function selectedNode() {
  const run = activeRun();
  return run && state.selectedNodeIndex >= 0 ? run.nodes[state.selectedNodeIndex] || null : null;
}

function selectedNodeIsEndpoint(run = activeRun()) {
  if (!run || state.selectedNodeIndex < 0 || !run.nodes[state.selectedNodeIndex]) return false;
  return state.selectedNodeIndex === 0 || state.selectedNodeIndex === run.nodes.length - 1;
}

function canConnectSelectedEndpoint(run = activeRun()) {
  const totalNodes = state.runs.reduce((count, item) => count + (item.nodes?.length || 0), 0);
  return selectedNodeIsEndpoint(run) && totalNodes > 1;
}

function runByKey(runKey) {
  const key = String(runKey || '');
  if (!key) return null;
  return state.runs.find(run => String(run.key || '') === key) || null;
}

function warningTargetRun(warning) {
  return runByKey(warning?.run_key || warning?.runKey || '');
}

function warningTargetNodeIndex(run, warning) {
  if (!run) return -1;
  const nodeKeys = Array.isArray(warning?.node_keys) ? warning.node_keys.map(String) : [];
  for (let index = run.nodes.length - 1; index >= 0; index -= 1) {
    if (nodeKeys.includes(String(run.nodes[index]?.key || ''))) return index;
  }
  const segmentIndex = Number(warning?.segment_index);
  if (Number.isInteger(segmentIndex) && segmentIndex >= 0 && run.nodes.length) {
    return Math.min(Math.max(segmentIndex, 0), run.nodes.length - 1);
  }
  return -1;
}

function nodeSourcePoint(node) {
  const x = Number(node?.x);
  const y = Number(node?.y);
  const z = Number(node?.z);
  if (![x, y, z].every(Number.isFinite)) return null;
  return { x, y, z, coordinate_frame: SOURCE_COORDINATE_FRAME };
}

function warningTargetSourcePoints(run, warning) {
  if (!run) return [];
  const segmentIndex = Number(warning?.segment_index);
  if (Number.isInteger(segmentIndex) && segmentIndex > 0 && segmentIndex < run.nodes.length) {
    return [
      nodeSourcePoint(run.nodes[segmentIndex - 1]),
      nodeSourcePoint(run.nodes[segmentIndex]),
    ].filter(Boolean);
  }
  const sourcePoint = warning?.source_point_m || warning?.sourcePointM || null;
  if (sourcePoint) {
    const x = Number(sourcePoint.x);
    const y = Number(sourcePoint.y);
    const z = Number(sourcePoint.z);
    if ([x, y, z].every(Number.isFinite)) {
      return [{ x, y, z, coordinate_frame: SOURCE_COORDINATE_FRAME }];
    }
  }
  const nodeIndex = warningTargetNodeIndex(run, warning);
  return nodeIndex >= 0 ? [nodeSourcePoint(run.nodes[nodeIndex])].filter(Boolean) : [];
}

function warningFramePaddingM(run) {
  const trayWidthM = Math.max(Number(run?.widthMm) || 0, Number(run?.depthMm) || 0) / 1000;
  return Math.max(trayWidthM, 0.5);
}

function focusScheduleWarningTarget(warning, run) {
  if (!runtime?.frameSourcePoints) return false;
  const sourcePoints = warningTargetSourcePoints(run, warning);
  if (!sourcePoints.length) return false;
  return runtime.frameSourcePoints(sourcePoints, {
    paddingM: warningFramePaddingM(run),
    minRadiusM: 1.5,
  }) === true;
}

function highlightedSegment(run, segmentIndex) {
  const focus = state.warningFocus;
  return Boolean(focus && focus.runId === run.id && Number(focus.segmentIndex) === Number(segmentIndex));
}

function racewayMeasurementSnapObjects() {
  const objects = [];
  layer?.group?.traverse?.(object => {
    if (!object || object.visible === false) return;
    const kind = object.userData?.racewayPreviewKind || '';
    if (RACEWAY_MEASUREMENT_SNAP_KINDS.has(kind)) objects.push(object);
  });
  return objects;
}

function ensureElevationDefault() {
  if (state.elevationInitialized) return;
  const currentElevation = runtime?.currentSourceElevationM?.();
  if (Number.isFinite(currentElevation)) {
    state.elevationM = currentElevation;
  }
  state.elevationInitialized = true;
}

function registerRacewayOverlay() {
  const registry = window.plant3dViewerLayers;
  if (!registry?.register) return null;
  if (registry.ids?.().includes(RACEWAY_LAYER_ID)) {
    return registry.update?.(RACEWAY_LAYER_ID, {
      getElements: () => state.runs,
      getMeasurementSnapObjects: racewayMeasurementSnapObjects,
      screenScaledObjects: true,
    });
  }
  return registry.register({
    id: RACEWAY_LAYER_ID,
    owner: 'raceway',
    kind: 'consumer-overlay',
    label: 'Raceway',
    createGroup: true,
    getElements: () => state.runs,
    getMeasurementSnapObjects: racewayMeasurementSnapObjects,
    screenScaledObjects: true,
  });
}

function hostReady() {
  runtime = window.plant3dViewerRuntime || runtime;
  layer = registerRacewayOverlay() || layer;
  return Boolean(runtime?.THREE && runtime?.registerInteraction && layer?.group);
}

function scheduleBootstrap() {
  bootstrapAttempts += 1;
  if (bootstrap()) return;
  if (bootstrapAttempts < 80) window.setTimeout(scheduleBootstrap, 100);
  if (bootstrapAttempts === 80) {
    console.warn('Raceway overlay could not attach to the Plant3D viewer host.');
  }
}

function bootstrap() {
  registerRacewayOverlay();
  ensurePanel();
  if (!hostReady()) return false;
  ensureElevationDefault();
  ensureInteraction();
  renderRaceway();
  renderPanel();
  schedulePersistenceBootstrap();
  if (window.racewayViewerOverlay) window.racewayViewerOverlay.layer = layer;
  return true;
}

function ensureInteraction() {
  if (interaction || !runtime?.registerInteraction) return;
  interaction = runtime.registerInteraction({
    id: RACEWAY_INTERACTION_ID,
    cursor: 'crosshair',
    onCanvasClick: event => {
      if (state.mode === 'connect') {
        connectSelectedNodeFromEvent(event);
        return true;
      }
      if (state.mode === 'draw') {
        if (selectRacewayNodeFromEvent(event)) return true;
        addNodeFromEvent(event);
        return true;
      }
      if (state.mode === 'move') {
        if (selectRacewayNodeFromEvent(event)) return true;
        moveSelectedNodeFromEvent(event);
        return true;
      }
      if (state.mode === 'select') {
        return selectRacewayNodeFromEvent(event);
      }
      return false;
    },
    onNavigationClick: () => {
      if (state.mode !== 'idle') {
        const run = activeRun();
        if (state.mode === 'draw' && run) {
          setStatus(`${run.tag}: navigation gesture ignored; continue with a clean click from node ${run.nodes.length || 1}.`);
        } else {
          setStatus('Navigation gesture ignored. Click without dragging to place or select raceway nodes.');
        }
      }
    },
    onCancel: () => {
      state.mode = 'idle';
      setStatus('Raceway command cancelled.');
      renderPanel();
    },
    onDeactivate: () => {
      if (state.mode !== 'idle') {
        state.mode = 'idle';
        setStatus('Raceway command paused by another viewer tool.');
        renderPanel();
      }
    },
  });
}

function activateCanvasMode(mode) {
  state.mode = mode;
  if (mode !== 'connect') state.connectSource = null;
  interaction?.activate?.();
}

function deactivateCanvasMode() {
  state.connectSource = null;
  state.mode = 'idle';
  interaction?.deactivate?.();
}

function activateNodeSelectionMode(run = activeRun()) {
  if (!run) {
    deactivateCanvasMode();
    return;
  }
  activateCanvasMode('select');
}

function makeRun() {
  const family = activeFamily();
  const size = activeSize();
  if (!family || !size) return null;
  return {
    id: `raceway-draft-${Date.now()}-${state.runs.length + 1}`,
    tag: `RWY-${String(state.runs.length + 1).padStart(3, '0')}`,
    familyId: family.id,
    familyCode: family.code,
    familyKind: family.kind,
    familyLabel: family.label,
    sizeId: size.id,
    sizeCode: size.code,
    sizeLabel: size.label,
    widthMm: size.widthMm,
    depthMm: size.depthMm,
    serviceClass: state.serviceClass,
    elevationM: Number(state.elevationM) || 0,
    orientation: normalizedOrientation(state.orientationPreset),
    nodes: [],
    dirty: true,
  };
}

function applyPaletteToActiveRun(options = {}) {
  const run = activeRun();
  if (!run) return;
  const family = activeFamily();
  const size = activeSize();
  if (!family || !size) return;
  const nextElevation = Number(state.elevationM) || 0;
  const previousElevation = Number(run.elevationM) || 0;
  run.familyId = family.id;
  run.familyCode = family.code;
  run.familyKind = family.kind;
  run.familyLabel = family.label;
  run.sizeId = size.id;
  run.sizeCode = size.code;
  run.sizeLabel = size.label;
  run.widthMm = size.widthMm;
  run.depthMm = size.depthMm;
  run.serviceClass = state.serviceClass;
  if (options.shiftElevation) {
    const delta = nextElevation - previousElevation;
    run.nodes.forEach(node => {
      node.z = Number(node.z || 0) + delta;
    });
  }
  run.elevationM = nextElevation;
  markRunDirty(run);
}

function syncPaletteFromRun(run) {
  if (!run) return;
  state.familyId = run.familyId || state.familyId;
  if (!catalogFamilyById(state.familyId)) state.familyId = catalog[0]?.id || '';
  state.sizeId = run.sizeId || state.sizeId;
  if (!activeSize()) state.sizeId = activeFamily()?.sizes[0]?.id || '';
  state.serviceClass = run.serviceClass || state.serviceClass;
  state.elevationM = Number(run.elevationM) || 0;
  state.elevationInitialized = true;
  state.orientationPreset = runOrientation(run).preset;
}

function sourcePointFromEvent(event) {
  const anchor = runtime?.modelAnchorFromViewerEvent?.(event) || null;
  const modelPoint = pointFromModelAnchor(anchor);
  if (modelPoint) return modelPoint;
  if (!runtime?.pointOnSourceElevationFromViewerEvent) return null;
  const renderPoint = runtime.pointOnSourceElevationFromViewerEvent(event, Number(state.elevationM) || 0);
  if (!renderPoint) return null;
  const sourcePoint = runtime.renderPointToSourcePoint(renderPoint);
  return {
    x: Number(sourcePoint.x) || 0,
    y: Number(sourcePoint.y) || 0,
    z: Number(state.elevationM) || 0,
    coordinate_frame: SOURCE_COORDINATE_FRAME,
  };
}

function orthoAdjustedPoint(run, point) {
  if (!state.orthoMode || !run?.nodes?.length || !point) {
    return { point, adjusted: false };
  }
  if (point.anchor && Object.keys(point.anchor).length) {
    return { point, adjusted: false };
  }
  const previous = run.nodes[run.nodes.length - 1];
  const dx = Number(point.x || 0) - Number(previous.x || 0);
  const dy = Number(point.y || 0) - Number(previous.y || 0);
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
    return { point, adjusted: false };
  }
  const adjusted = { ...point };
  if (Math.abs(dx) >= Math.abs(dy)) {
    adjusted.y = Number(previous.y) || 0;
  } else {
    adjusted.x = Number(previous.x) || 0;
  }
  return { point: adjusted, adjusted: true };
}

function adoptWorkingElevationFromPoint(run, point) {
  const elevation = Number(point?.z);
  if (!Number.isFinite(elevation)) return;
  state.elevationM = elevation;
  state.elevationInitialized = true;
  if (run) run.elevationM = elevation;
}

function selectedModelAnchor() {
  return runtime?.getSelectedModelAnchor?.() || null;
}

function anchorLabel(anchor) {
  return anchor?.label || anchor?.stable_id || anchor?.source_object_id || '';
}

function compactObject(object) {
  return Object.fromEntries(
    Object.entries(object)
      .filter(([_key, value]) => value !== null && value !== undefined && value !== ''),
  );
}

function normalizedAnchorSourcePoint(sourcePoint) {
  if (!sourcePoint || typeof sourcePoint !== 'object') return null;
  const x = Number(sourcePoint.x);
  const y = Number(sourcePoint.y);
  const z = Number(sourcePoint.z);
  if (![x, y, z].every(Number.isFinite)) return null;
  return { x, y, z, coordinate_frame: SOURCE_COORDINATE_FRAME };
}

function sanitizeAnchorForPersistence(anchor) {
  if (!anchor || typeof anchor !== 'object') return {};
  if (!Object.keys(anchor).length) return {};
  const sourcePoint = normalizedAnchorSourcePoint(anchor.source_point_m);
  const cleaned = compactObject({
    owner_module: 'raceway',
    anchor_kind: anchor.anchor_kind || 'model_object',
    render_package_id: anchor.render_package_id,
    source_model_id: anchor.source_model_id,
    model_object_id: anchor.model_object_id,
    stable_id: anchor.stable_id || anchor.model_object_stable_id,
    source_object_id: anchor.source_object_id,
    object_type: anchor.object_type,
    label: anchor.label,
    bounds: anchor.bounds && typeof anchor.bounds === 'object' ? anchor.bounds : undefined,
    source_point_m: sourcePoint || undefined,
  });
  return cleaned.anchor_kind ? cleaned : {};
}

function pointFromModelAnchor(anchor) {
  const persistedAnchor = sanitizeAnchorForPersistence(anchor);
  const sourcePoint = persistedAnchor.source_point_m || null;
  if (!sourcePoint) return null;
  const z = Number(sourcePoint.z);
  return {
    x: Number(sourcePoint.x) || 0,
    y: Number(sourcePoint.y) || 0,
    z: Number.isFinite(z) ? z : Number(state.elevationM) || 0,
    coordinate_frame: SOURCE_COORDINATE_FRAME,
    anchor: persistedAnchor,
  };
}

function attachSelectedModelToNode() {
  const run = activeRun();
  if (!run) {
    setStatus('Start or select a raceway run before anchoring to the plant model.');
    return;
  }
  const anchor = selectedModelAnchor();
  if (!anchor) {
    setStatus('Select a Plant3D model object first, then anchor the raceway node.');
    return;
  }
  const point = pointFromModelAnchor(anchor);
  if (!point) {
    setStatus('Selected model object has no usable source-coordinate anchor.');
    return;
  }
  pushUndo('Anchor node');
  adoptWorkingElevationFromPoint(run, point);
  if (state.selectedNodeIndex >= 0 && run.nodes[state.selectedNodeIndex]) {
    run.nodes[state.selectedNodeIndex] = point;
  } else {
    run.nodes.push(point);
    state.selectedNodeIndex = run.nodes.length - 1;
  }
  markRunDirty(run);
  setStatus(`${run.tag}: node ${state.selectedNodeIndex + 1} anchored to ${anchorLabel(anchor)}.`);
  renderRaceway();
  renderPanel();
}

function clearSelectedNodeAnchor() {
  const node = selectedNode();
  if (!node?.anchor) {
    setStatus('Selected node has no plant model anchor.');
    return;
  }
  pushUndo('Clear node anchor');
  node.anchor = {};
  markRunDirty();
  setStatus('Plant model anchor cleared from selected node.');
  renderPanel();
}

function nodeDistance(a, b) {
  if (!a || !b) return 0;
  const dx = Number(b.x || 0) - Number(a.x || 0);
  const dy = Number(b.y || 0) - Number(a.y || 0);
  const dz = Number(b.z || 0) - Number(a.z || 0);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function routeTurnStats(run) {
  const stats = { bends: 0, risers: 0 };
  const nodes = run?.nodes || [];
  for (let index = 1; index < nodes.length; index += 1) {
    const previous = nodes[index - 1];
    const node = nodes[index];
    if (Math.abs(Number(node.z || 0) - Number(previous.z || 0)) > 0.001) stats.risers += 1;
  }
  for (let index = 1; index < nodes.length - 1; index += 1) {
    const a = nodes[index - 1];
    const b = nodes[index];
    const c = nodes[index + 1];
    const inX = Number(b.x || 0) - Number(a.x || 0);
    const inY = Number(b.y || 0) - Number(a.y || 0);
    const outX = Number(c.x || 0) - Number(b.x || 0);
    const outY = Number(c.y || 0) - Number(b.y || 0);
    const inPlan = Math.sqrt((inX * inX) + (inY * inY));
    const outPlan = Math.sqrt((outX * outX) + (outY * outY));
    if (inPlan < 0.05 || outPlan < 0.05) continue;
    const cosine = ((inX * outX) + (inY * outY)) / (inPlan * outPlan);
    if (cosine < 0.996) stats.bends += 1;
  }
  return stats;
}

function bendCount(run) {
  return routeTurnStats(run).bends;
}

function riserCount(run) {
  return routeTurnStats(run).risers;
}

function runLength(run) {
  return run.nodes.reduce((total, node, index) => total + nodeDistance(run.nodes[index - 1], node), 0);
}

function runWarnings(run) {
  const warnings = [];
  if (!run) return warnings;
  if (run.nodes.length > 0 && run.nodes.length < 2) {
    warnings.push({
      code: 'raceway.warning.too_few_nodes',
      severity: 'warning',
      message: 'Add at least two nodes before saving this raceway run.',
    });
  }
  if (!run.familyId || !run.sizeId || !run.serviceClass) {
    warnings.push({
      code: 'raceway.warning.missing_catalog_or_service',
      severity: 'warning',
      message: 'Select family, size, and service before saving this raceway run.',
    });
  }
  run.nodes.forEach((node, index) => {
    if (index > 0 && nodeDistance(run.nodes[index - 1], node) < 0.05) {
      warnings.push({
        code: 'raceway.warning.short_segment',
        severity: 'warning',
        message: `Segment ${index} is shorter than 0.050 m; review whether adjacent nodes should be merged.`,
        nodeIndices: [index - 1, index],
      });
    }
  });
  return warnings;
}

function warningTelemetrySignature(warning) {
  return [
    warning?.code || 'raceway.warning',
    warning?.run_key || warning?.runTag || warning?.run_tag || '',
    Array.isArray(warning?.node_keys) ? warning.node_keys.join(',') : '',
    warning?.node_key || warning?.endpoint_node_key || '',
    Array.isArray(warning?.edge_keys) ? warning.edge_keys.join(',') : '',
    warning?.segment_index ?? '',
    warning?.message || '',
  ].join('|');
}

function recordWarningTelemetry(warnings, action = 'shown', options = {}) {
  const items = Array.isArray(warnings) ? warnings : [];
  items.forEach(warning => {
    const suggestionCode = warning?.code || 'raceway.warning';
    const signature = `warning:${warningTelemetrySignature(warning)}`;
    if (action === 'shown' && telemetryShownSignatures.has(signature)) return;
    if (action === 'shown') telemetryShownSignatures.add(signature);
    queueTelemetryEvent({
      key: telemetryLifecycleKey(signature),
      suggestionCode,
      action,
      context: warning,
      actionDetail: options.actionDetail || {},
    });
  });
}

function recordVisibleWarningTelemetry(action = 'shown', options = {}) {
  const run = activeRun();
  const localWarnings = runWarnings(run).map(warning => ({
    ...warning,
    run_key: run?.key || warning.run_key || '',
    run_tag: run?.tag || warning.run_tag || '',
  }));
  recordWarningTelemetry([...localWarnings, ...graphWarnings(), ...scheduleWarnings()], action, options);
}

function recordOrthoTelemetry(run, previousPoint, rawPoint, adjustedPoint) {
  if (!run || !previousPoint || !rawPoint || !adjustedPoint) return;
  const lockedAxis = Math.abs(Number(rawPoint.x || 0) - Number(adjustedPoint.x || 0)) > 0.001 ? 'x' : 'y';
  queueTelemetryEvent({
    suggestionCode: 'raceway.ortho.axis_lock',
    action: 'shown',
    context: {
      run_key: run.key || '',
      run_tag: run.tag || '',
      segment_index: Math.max(run.nodes.length - 1, 0),
      previous_point_m: {
        x: Number(previousPoint.x) || 0,
        y: Number(previousPoint.y) || 0,
        z: Number(previousPoint.z) || 0,
      },
      raw_point_m: {
        x: Number(rawPoint.x) || 0,
        y: Number(rawPoint.y) || 0,
        z: Number(rawPoint.z) || 0,
      },
      adjusted_point_m: {
        x: Number(adjustedPoint.x) || 0,
        y: Number(adjustedPoint.y) || 0,
        z: Number(adjustedPoint.z) || 0,
      },
    },
    actionDetail: { locked_axis: lockedAxis },
  });
}

function clearLayerGroup() {
  if (!layer?.group) return;
  while (layer.group.children.length) {
    const child = layer.group.children.pop();
    child.traverse?.(node => {
      node.geometry?.dispose?.();
      if (Array.isArray(node.material)) {
        node.material.forEach(material => material.dispose?.());
      } else {
        node.material?.dispose?.();
      }
    });
  }
}

function renderSourcePoint(point) {
  return runtime?.sourcePointToRenderPoint?.(point) || null;
}

function isLadderRun(run) {
  return run.familyKind === 'ladder' || String(run.familyCode || '').startsWith('LADDER');
}

function runWidthM(run) {
  return Math.max((Number(run.widthMm) || 300) / 1000, 0.05);
}

function runDepthM(run) {
  return Math.max((Number(run.depthMm) || 50) / 1000, 0.025);
}

function addSourceLine(group, sourcePoints, material, previewKind) {
  const renderPoints = sourcePoints.map(renderSourcePoint).filter(Boolean);
  if (renderPoints.length < 2) return null;
  const line = new runtime.THREE.Line(
    new runtime.THREE.BufferGeometry().setFromPoints(renderPoints),
    material,
  );
  line.userData.racewayPreviewKind = previewKind;
  if (RACEWAY_MEASUREMENT_SNAP_KINDS.has(previewKind)) {
    line.userData.measurementSnapTarget = true;
  }
  group.add(line);
  return line;
}

function previewMaterial(color, opacity = 1) {
  return new runtime.THREE.LineBasicMaterial({
    color,
    depthTest: false,
    transparent: opacity < 1,
    opacity,
  });
}

function proxyFaceMaterial(color, selected) {
  return new runtime.THREE.MeshBasicMaterial({
    color: 0xffffff,
    depthTest: true,
    depthWrite: false,
    transparent: true,
    opacity: selected ? PROXY_FACE_SELECTED_OPACITY : PROXY_FACE_OPACITY,
    side: runtime.THREE.DoubleSide,
    vertexColors: true,
  });
}

function updateRacewayScreenScale(object) {
  const config = object?.userData?.screenScale;
  if (!config || !runtime?.worldUnitsForScreenPixels) return;
  const worldSize = runtime.worldUnitsForScreenPixels(
    object.position,
    config.pixels,
    config.min,
    config.max,
  );
  object.scale?.setScalar?.(worldSize);
}

function bufferAttribute(values, itemSize = 3) {
  const array = new Float32Array(values);
  if (runtime.THREE.Float32BufferAttribute) {
    return new runtime.THREE.Float32BufferAttribute(array, itemSize);
  }
  if (runtime.THREE.BufferAttribute) {
    return new runtime.THREE.BufferAttribute(array, itemSize);
  }
  return { array, itemSize, count: values.length / itemSize };
}

function positionAttribute(values) {
  return bufferAttribute(values, 3);
}

function setGeometryPositions(geometry, positions, colors = []) {
  const attribute = positionAttribute(positions);
  if (geometry.setAttribute) {
    geometry.setAttribute('position', attribute);
  } else {
    geometry.attributes = { ...(geometry.attributes || {}), position: attribute };
  }
  if (colors.length === positions.length) {
    const colorAttribute = bufferAttribute(colors, 3);
    if (geometry.setAttribute) {
      geometry.setAttribute('color', colorAttribute);
    } else {
      geometry.attributes = { ...(geometry.attributes || {}), color: colorAttribute };
    }
  }
  geometry.userData = { ...(geometry.userData || {}), positionCount: positions.length / 3 };
  geometry.computeVertexNormals?.();
  geometry.computeBoundingSphere?.();
  return geometry;
}

function clampColorUnit(value) {
  return Math.min(Math.max(Number(value) || 0, 0), 1);
}

function colorFloats(color, shade = 1) {
  const base = Number(color) || 0;
  return [
    clampColorUnit(((base >> 16) & 255) / 255 * shade),
    clampColorUnit(((base >> 8) & 255) / 255 * shade),
    clampColorUnit((base & 255) / 255 * shade),
  ];
}

function proxyFaceColors(color, selected) {
  const baseColor = selected ? 0xf97316 : color;
  return {
    bottom: colorFloats(baseColor, PROXY_BOTTOM_SHADE),
    side: colorFloats(baseColor, PROXY_SIDE_SHADE),
  };
}

function pushRenderVertex(positions, colors, sourcePoint, vertexColor = null) {
  const point = renderSourcePoint(sourcePoint);
  if (!point) return false;
  positions.push(Number(point.x) || 0, Number(point.y) || 0, Number(point.z) || 0);
  if (vertexColor) colors.push(vertexColor[0], vertexColor[1], vertexColor[2]);
  return true;
}

function addProxyQuad(positions, colors, a, b, c, d, vertexColor = null) {
  const before = positions.length;
  const colorBefore = colors.length;
  if (
    !pushRenderVertex(positions, colors, a, vertexColor)
    || !pushRenderVertex(positions, colors, b, vertexColor)
    || !pushRenderVertex(positions, colors, c, vertexColor)
    || !pushRenderVertex(positions, colors, a, vertexColor)
    || !pushRenderVertex(positions, colors, c, vertexColor)
    || !pushRenderVertex(positions, colors, d, vertexColor)
  ) {
    positions.length = before;
    colors.length = colorBefore;
  }
}

function segmentPlanBasis(start, end) {
  const dx = Number(end.x || 0) - Number(start.x || 0);
  const dy = Number(end.y || 0) - Number(start.y || 0);
  const dz = Number(end.z || 0) - Number(start.z || 0);
  const length = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (length < 0.001) {
    return { length: 0, tx: 1, ty: 0, tz: 0, nx: 0, ny: 1, nz: 0, dx: 0, dy: 0, dz: 1 };
  }
  const planLength = Math.sqrt(dx * dx + dy * dy);
  let nx = 0;
  let ny = 1;
  if (planLength >= 0.001) {
    nx = -dy / planLength;
    ny = dx / planLength;
  }
  const tx = dx / length;
  const ty = dy / length;
  const tz = dz / length;
  let depthX = (ty * 0) - (tz * ny);
  let depthY = (tz * nx) - (tx * 0);
  let depthZ = (tx * ny) - (ty * nx);
  let depthLength = Math.sqrt((depthX * depthX) + (depthY * depthY) + (depthZ * depthZ));
  if (depthLength < 0.001) {
    depthX = 0;
    depthY = 0;
    depthZ = 1;
    depthLength = 1;
  }
  depthX /= depthLength;
  depthY /= depthLength;
  depthZ /= depthLength;
  if (depthZ < -0.001) {
    depthX *= -1;
    depthY *= -1;
    depthZ *= -1;
  }
  return {
    length,
    tx,
    ty,
    tz,
    nx,
    ny,
    nz: 0,
    dx: depthX,
    dy: depthY,
    dz: depthZ,
  };
}

function rollBasisAroundTangent(basis, quarterTurns = 0) {
  const turns = ((Number(quarterTurns) || 0) % 4 + 4) % 4;
  if (!turns) return basis;
  const angle = turns * Math.PI / 2;
  const cos = Math.round(Math.cos(angle));
  const sin = Math.round(Math.sin(angle));
  return {
    ...basis,
    nx: (basis.nx * cos) + (basis.dx * sin),
    ny: (basis.ny * cos) + (basis.dy * sin),
    nz: (basis.nz * cos) + (basis.dz * sin),
    dx: (basis.dx * cos) - (basis.nx * sin),
    dy: (basis.dy * cos) - (basis.ny * sin),
    dz: (basis.dz * cos) - (basis.nz * sin),
  };
}

function orientedSegmentBasis(run, start, end) {
  const basis = segmentPlanBasis(start, end);
  return rollBasisAroundTangent(basis, runOrientation(run).quarter_turns);
}

function sourcePointAlongSegment(start, basis, distanceM) {
  return {
    x: Number(start.x || 0) + basis.tx * distanceM,
    y: Number(start.y || 0) + basis.ty * distanceM,
    z: Number(start.z || 0) + basis.tz * distanceM,
  };
}

function sourceFrameOffsetPoint(point, basis, lateralOffsetM = 0, depthOffsetM = 0) {
  return {
    x: Number(point.x || 0) + (basis.nx * lateralOffsetM) + (basis.dx * depthOffsetM),
    y: Number(point.y || 0) + (basis.ny * lateralOffsetM) + (basis.dy * depthOffsetM),
    z: Number(point.z || 0) + (basis.nz * lateralOffsetM) + (basis.dz * depthOffsetM),
  };
}

function segmentCornerPoints(run, start, end) {
  const basis = orientedSegmentBasis(run, start, end);
  if (basis.length < 0.001) return null;
  const halfWidth = runWidthM(run) / 2;
  const depth = runDepthM(run);
  const leftStartBottom = sourceFrameOffsetPoint(start, basis, halfWidth, 0);
  const leftEndBottom = sourceFrameOffsetPoint(end, basis, halfWidth, 0);
  const rightStartBottom = sourceFrameOffsetPoint(start, basis, -halfWidth, 0);
  const rightEndBottom = sourceFrameOffsetPoint(end, basis, -halfWidth, 0);
  const leftStartTop = sourceFrameOffsetPoint(start, basis, halfWidth, depth);
  const leftEndTop = sourceFrameOffsetPoint(end, basis, halfWidth, depth);
  const rightStartTop = sourceFrameOffsetPoint(start, basis, -halfWidth, depth);
  const rightEndTop = sourceFrameOffsetPoint(end, basis, -halfWidth, depth);
  return {
    basis,
    leftStartBottom,
    leftEndBottom,
    rightStartBottom,
    rightEndBottom,
    leftStartTop,
    leftEndTop,
    rightStartTop,
    rightEndTop,
  };
}

function addSegmentProxyFaces(positions, colors, run, start, end, faceColors) {
  const corners = segmentCornerPoints(run, start, end);
  if (!corners) return;
  addProxyQuad(positions, colors, corners.leftStartBottom, corners.rightStartBottom, corners.rightEndBottom, corners.leftEndBottom, faceColors.bottom);
  addProxyQuad(positions, colors, corners.leftStartBottom, corners.leftEndBottom, corners.leftEndTop, corners.leftStartTop, faceColors.side);
  addProxyQuad(positions, colors, corners.rightStartBottom, corners.rightStartTop, corners.rightEndTop, corners.rightEndBottom, faceColors.side);
}

function addRunProxyFaceMesh(group, run, color, selected) {
  const positions = [];
  const colors = [];
  const faceColors = proxyFaceColors(color, selected);
  for (let index = 1; index < run.nodes.length; index += 1) {
    addSegmentProxyFaces(positions, colors, run, run.nodes[index - 1], run.nodes[index], faceColors);
  }
  if (positions.length < 18) return null;
  const geometry = setGeometryPositions(new runtime.THREE.BufferGeometry(), positions, colors);
  const mesh = new runtime.THREE.Mesh(geometry, proxyFaceMaterial(color, selected));
  mesh.userData.racewayPreviewKind = 'solid-3-plane-proxy';
  mesh.userData.racewayRunId = run.id;
  mesh.userData.faceCount = positions.length / 18;
  mesh.renderOrder = 18;
  group.add(mesh);
  return mesh;
}

function addSegmentPreview(group, run, start, end, material, detailMaterial) {
  const corners = segmentCornerPoints(run, start, end);
  if (!corners) return;
  const { basis } = corners;
  const halfWidth = runWidthM(run) / 2;

  addSourceLine(group, [corners.leftStartTop, corners.leftEndTop], material, 'side-rail');
  addSourceLine(group, [corners.rightStartTop, corners.rightEndTop], material, 'side-rail');
  addSourceLine(group, [corners.leftStartBottom, corners.leftEndBottom], detailMaterial, 'lower-edge');
  addSourceLine(group, [corners.rightStartBottom, corners.rightEndBottom], detailMaterial, 'lower-edge');
  addSourceLine(group, [corners.leftStartBottom, corners.leftStartTop], detailMaterial, 'depth-tick');
  addSourceLine(group, [corners.rightStartBottom, corners.rightStartTop], detailMaterial, 'depth-tick');
  addSourceLine(group, [corners.leftEndBottom, corners.leftEndTop], detailMaterial, 'depth-tick');
  addSourceLine(group, [corners.rightEndBottom, corners.rightEndTop], detailMaterial, 'depth-tick');

  const spacing = isLadderRun(run) ? 0.75 : 1.2;
  const maxCrossMembers = isLadderRun(run) ? 16 : 10;
  const memberCount = Math.min(Math.max(Math.floor(basis.length / spacing), 1), maxCrossMembers);
  for (let index = 0; index <= memberCount; index += 1) {
    const distance = (basis.length * index) / memberCount;
    const center = sourcePointAlongSegment(start, basis, distance);
    const leftBottom = sourceFrameOffsetPoint(center, basis, halfWidth, 0);
    const rightBottom = sourceFrameOffsetPoint(center, basis, -halfWidth, 0);
    addSourceLine(group, [leftBottom, rightBottom], detailMaterial, isLadderRun(run) ? 'rung' : 'tray-cross-member');
  }
}

function addBendPlaceholder(group, run, node, material) {
  const size = Math.max(Math.min(runWidthM(run) * 0.35, 0.35), 0.08);
  const diamond = [
    { x: node.x, y: Number(node.y || 0) + size, z: node.z },
    { x: Number(node.x || 0) + size, y: node.y, z: node.z },
    { x: node.x, y: Number(node.y || 0) - size, z: node.z },
    { x: Number(node.x || 0) - size, y: node.y, z: node.z },
    { x: node.x, y: Number(node.y || 0) + size, z: node.z },
  ];
  addSourceLine(group, diamond, material, 'bend-placeholder');
}

function addRiserPlaceholder(group, run, start, end, material) {
  const dz = Number(end.z || 0) - Number(start.z || 0);
  if (Math.abs(dz) < 0.001) return;
  const midpoint = {
    x: (Number(start.x || 0) + Number(end.x || 0)) / 2,
    y: (Number(start.y || 0) + Number(end.y || 0)) / 2,
    z: (Number(start.z || 0) + Number(end.z || 0)) / 2,
  };
  const markerHalf = Math.max(Math.min(runWidthM(run) * 0.25, 0.25), 0.06);
  addSourceLine(group, [
    { x: midpoint.x - markerHalf, y: midpoint.y, z: midpoint.z },
    { x: midpoint.x + markerHalf, y: midpoint.y, z: midpoint.z },
  ], material, 'riser-placeholder');
  addSourceLine(group, [
    { x: midpoint.x, y: midpoint.y - markerHalf, z: midpoint.z },
    { x: midpoint.x, y: midpoint.y + markerHalf, z: midpoint.z },
  ], material, 'riser-placeholder');
}

function addWarningSegmentHighlight(group, run, start, end) {
  const material = previewMaterial(0xdc2626, 1);
  const line = addSourceLine(group, [start, end], material, 'warning-segment-highlight');
  if (line) {
    line.userData.racewayRunId = run.id;
    line.renderOrder = 42;
  }
  addBendPlaceholder(group, run, start, material);
  addBendPlaceholder(group, run, end, material);
}

function addNodeHandle(group, run, node, index, color) {
  const renderPoint = renderSourcePoint(node);
  if (!renderPoint) return;
  const selected = run.id === state.activeRunId && index === state.selectedNodeIndex;
  const handle = new runtime.THREE.Mesh(
    new runtime.THREE.SphereGeometry(1, 16, 16),
    new runtime.THREE.MeshBasicMaterial({ color: selected ? 0xf97316 : color, depthTest: false }),
  );
  handle.position.copy(renderPoint);
  handle.userData.racewayPreviewKind = 'node-handle';
  handle.userData.racewayRunId = run.id;
  handle.userData.racewayNodeIndex = index;
  handle.userData.screenScale = {
    kind: 'marker',
    pixels: selected ? NODE_HANDLE_SELECTED_SCREEN_PX : NODE_HANDLE_SCREEN_PX,
    min: 0.012,
    max: 0.075,
  };
  updateRacewayScreenScale(handle);
  handle.renderOrder = 32;
  group.add(handle);

  const hitTarget = new runtime.THREE.Mesh(
    new runtime.THREE.SphereGeometry(1, 12, 12),
    new runtime.THREE.MeshBasicMaterial({
      color,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      opacity: 0,
    }),
  );
  hitTarget.position.copy(renderPoint);
  hitTarget.userData.racewayPreviewKind = 'node-hit-target';
  hitTarget.userData.racewayRunId = run.id;
  hitTarget.userData.racewayNodeIndex = index;
  hitTarget.userData.screenScale = {
    kind: 'marker',
    pixels: NODE_HIT_TARGET_SCREEN_PX,
    min: 0.045,
    max: 0.18,
  };
  updateRacewayScreenScale(hitTarget);
  group.add(hitTarget);
}

function racewayNodeHitTargets() {
  const targets = [];
  layer?.group?.traverse?.(node => {
    if (node.userData?.racewayPreviewKind === 'node-hit-target' || node.userData?.racewayPreviewKind === 'node-handle') {
      targets.push(node);
    }
  });
  return targets;
}

function pickRacewayNodeFromEvent(event) {
  if (!runtime?.raycastObjectsFromViewerEvent) return nearestRacewayNodeFromEvent(event);
  const hits = runtime.raycastObjectsFromViewerEvent(event, racewayNodeHitTargets(), false) || [];
  const hit = hits.find(item => item.object?.userData?.racewayRunId && Number.isInteger(item.object.userData.racewayNodeIndex));
  if (!hit) return nearestRacewayNodeFromEvent(event);
  return {
    runId: hit.object.userData.racewayRunId,
    nodeIndex: hit.object.userData.racewayNodeIndex,
  };
}

function nearestRacewayNodeFromEvent(event) {
  if (!runtime?.pointOnSourceElevationFromViewerEvent) return null;
  let best = null;
  state.runs.forEach(run => {
    run.nodes.forEach((node, nodeIndex) => {
      const nodePoint = renderSourcePoint(node);
      const eventPoint = runtime.pointOnSourceElevationFromViewerEvent(event, Number(node.z) || 0);
      if (!nodePoint || !eventPoint) return;
      const dx = Number(nodePoint.x || 0) - Number(eventPoint.x || 0);
      const dy = Number(nodePoint.y || 0) - Number(eventPoint.y || 0);
      const dz = Number(nodePoint.z || 0) - Number(eventPoint.z || 0);
      const distanceSq = (dx * dx) + (dy * dy) + (dz * dz);
      const radius = Math.max(runtime.worldUnitsForScreenPixels?.(nodePoint, 22, 0.1, 0.55) || 0, 0.3);
      if (distanceSq <= radius * radius && (!best || distanceSq < best.distanceSq)) {
        best = { runId: run.id, nodeIndex, distanceSq };
      }
    });
  });
  return best;
}

function selectRacewayNodeFromEvent(event) {
  const picked = pickRacewayNodeFromEvent(event);
  if (!picked) return false;
  const run = state.runs.find(item => item.id === picked.runId);
  if (!run || !run.nodes[picked.nodeIndex]) return false;
  state.activeRunId = run.id;
  state.selectedNodeIndex = picked.nodeIndex;
  syncPaletteFromRun(run);
  activateNodeSelectionMode(run);
  setStatus(`${run.tag}: node ${picked.nodeIndex + 1} selected.`);
  renderRaceway();
  renderPanel();
  return true;
}

function beginConnectNode() {
  const run = activeRun();
  if (!run || !selectedNode()) {
    setStatus('Select an endpoint node before connecting it.');
    return;
  }
  if (!selectedNodeIsEndpoint(run)) {
    setStatus('Connect Node works on the first or last node of a run. Split-and-tee support comes later.');
    return;
  }
  if (!canConnectSelectedEndpoint(run)) {
    setStatus('Add another raceway node before connecting this endpoint.');
    return;
  }
  state.connectSource = { runId: run.id, nodeIndex: state.selectedNodeIndex };
  activateCanvasMode('connect');
  setStatus(`${run.tag}: click an existing raceway node to connect endpoint N${state.selectedNodeIndex + 1}.`);
  renderPanel();
}

function runById(runId) {
  return state.runs.find(run => run.id === runId) || null;
}

function connectedNodeCopy(sourceNode, targetNode) {
  return {
    serverNodeId: sourceNode?.serverNodeId,
    key: sourceNode?.key || '',
    x: Number(targetNode.x) || 0,
    y: Number(targetNode.y) || 0,
    z: Number(targetNode.z) || 0,
    coordinate_frame: SOURCE_COORDINATE_FRAME,
    anchor: sanitizeAnchorForPersistence(targetNode.anchor || {}),
  };
}

function connectSelectedNodeFromEvent(event) {
  const source = state.connectSource || { runId: state.activeRunId, nodeIndex: state.selectedNodeIndex };
  const sourceRun = runById(source.runId);
  const sourceNode = sourceRun?.nodes?.[source.nodeIndex] || null;
  if (!sourceRun || !sourceNode) {
    state.connectSource = null;
    setStatus('Connection source node is no longer available.');
    renderPanel();
    return;
  }
  state.activeRunId = sourceRun.id;
  state.selectedNodeIndex = source.nodeIndex;
  if (!selectedNodeIsEndpoint(sourceRun)) {
    setStatus('Connect Node works on the first or last node of a run.');
    renderPanel();
    return;
  }
  const target = pickRacewayNodeFromEvent(event);
  if (!target) {
    setStatus(`${sourceRun.tag}: click an existing raceway node handle to connect this endpoint.`);
    return;
  }
  if (target.runId === source.runId && target.nodeIndex === source.nodeIndex) {
    setStatus('Select a different raceway node as the connection target.');
    return;
  }
  const targetRun = runById(target.runId);
  const targetNode = targetRun?.nodes?.[target.nodeIndex] || null;
  if (!targetRun || !targetNode) {
    setStatus('Connection target node is no longer available.');
    return;
  }
  pushUndo('Connect node');
  sourceRun.nodes[source.nodeIndex] = connectedNodeCopy(sourceNode, targetNode);
  state.activeRunId = sourceRun.id;
  state.selectedNodeIndex = source.nodeIndex;
  adoptWorkingElevationFromPoint(sourceRun, targetNode);
  markRunDirty(sourceRun);
  state.connectSource = null;
  activateNodeSelectionMode(sourceRun);
  setStatus(`${sourceRun.tag}: endpoint N${source.nodeIndex + 1} connected to ${targetRun.tag} N${target.nodeIndex + 1}. Save and refresh graph to confirm.`);
  renderRaceway();
  renderPanel({ forceInspector: true });
}

function renderTrayPreview(group, run, color) {
  const selected = run.id === state.activeRunId;
  const material = previewMaterial(selected ? 0xf97316 : color, selected ? 1 : 0.92);
  const detailMaterial = previewMaterial(color, 0.62);
  const guideMaterial = previewMaterial(0x475569, selected ? 0.7 : 0.35);
  if (state.showProxyFaces) addRunProxyFaceMesh(group, run, color, selected);
  const points = run.nodes.map(renderSourcePoint).filter(Boolean);
  if (points.length > 1) {
    const guide = new runtime.THREE.Line(
      new runtime.THREE.BufferGeometry().setFromPoints(points),
      guideMaterial,
    );
    guide.userData.racewayPreviewKind = 'centerline-guide';
    group.add(guide);
  }
  for (let index = 1; index < run.nodes.length; index += 1) {
    addSegmentPreview(group, run, run.nodes[index - 1], run.nodes[index], material, detailMaterial);
    addRiserPlaceholder(group, run, run.nodes[index - 1], run.nodes[index], previewMaterial(0xbe123c, selected ? 0.95 : 0.65));
    if (highlightedSegment(run, index)) {
      addWarningSegmentHighlight(group, run, run.nodes[index - 1], run.nodes[index]);
    }
  }
  for (let index = 1; index < run.nodes.length - 1; index += 1) {
    addBendPlaceholder(group, run, run.nodes[index], previewMaterial(0xf97316, selected ? 0.95 : 0.65));
  }
}

function renderRaceway() {
  if (!hostReady()) return;
  clearLayerGroup();
  state.runs.forEach(run => {
    const color = serviceFor(run.serviceClass).color;
    const group = new runtime.THREE.Group();
    group.userData.racewayPreviewKind = isLadderRun(run) ? 'ladder-proxy' : 'tray-proxy';
    renderTrayPreview(group, run, color);
    run.nodes.forEach((node, index) => addNodeHandle(group, run, node, index, color));
    layer.group.add(group);
  });
  window.plant3dViewerLayers?.update?.(RACEWAY_LAYER_ID, {
    getElements: () => state.runs,
    getMeasurementSnapObjects: racewayMeasurementSnapObjects,
  });
  runtime.renderNow?.();
}

function beginRun() {
  if (!hostReady()) {
    setStatus('Viewer is still preparing raceway tools.');
    return;
  }
  ensureElevationDefault();
  const run = makeRun();
  if (!run) {
    setStatus(state.catalogLoaded ? 'No active raceway catalogue size is available.' : 'Raceway catalogue is still loading.');
    schedulePersistenceBootstrap();
    renderPanel();
    return;
  }
  pushUndo('Start raceway run');
  state.runs.push(run);
  state.activeRunId = run.id;
  state.selectedNodeIndex = -1;
  activateCanvasMode('draw');
  setStatus(`${run.tag}: click centerline nodes at EL +${formatM(run.elevationM)}`);
  renderRaceway();
  renderPanel();
}

function finishRun() {
  const run = activeRun();
  if (!run) return;
  if (run.nodes.length < 2) {
    setStatus('Add at least two nodes before finish.');
    return;
  }
  activateNodeSelectionMode(run);
  setStatus(`${run.tag}: ${run.nodes.length} nodes, ${formatM(runLength(run))} m. Click a node handle to select it.`);
  renderPanel();
}

function continueRun() {
  const run = activeRun();
  if (!run) {
    setStatus('Select a raceway run before continuing.');
    return;
  }
  state.selectedNodeIndex = run.nodes.length - 1;
  activateCanvasMode('draw');
  setStatus(`${run.tag}: continue from node ${run.nodes.length || 1}. Click structure or the working plane to append.`);
  renderRaceway();
  renderPanel();
}

function addTypedSegment() {
  const run = activeRun();
  const start = run?.nodes?.at(-1) || null;
  const length = Number(state.segmentLengthM);
  const direction = segmentDirectionById();
  if (!run || !start) {
    setStatus('Add or select a raceway run with at least one node before typed segment entry.');
    return;
  }
  if (!Number.isFinite(length) || length <= 0) {
    setStatus('Enter a positive segment length.');
    renderPanel();
    return;
  }
  const point = {
    x: Number(start.x || 0) + direction.dx * length,
    y: Number(start.y || 0) + direction.dy * length,
    z: Number(start.z || 0) + direction.dz * length,
    coordinate_frame: SOURCE_COORDINATE_FRAME,
  };
  pushUndo('Add typed segment');
  run.nodes.push(point);
  state.selectedNodeIndex = run.nodes.length - 1;
  adoptWorkingElevationFromPoint(run, point);
  markRunDirty(run);
  activateCanvasMode('draw');
  setStatus(`${run.tag}: ${formatM(length)} m typed segment added ${direction.label}.`);
  renderRaceway();
  renderPanel();
}

function cancelRun() {
  const run = activeRun();
  if (run && state.mode === 'draw' && run.nodes.length === 0) {
    pushUndo('Cancel empty raceway run');
    state.runs = state.runs.filter(item => item.id !== run.id);
    state.activeRunId = state.runs.at(-1)?.id || '';
  }
  deactivateCanvasMode();
  state.selectedNodeIndex = -1;
  setStatus('Raceway command cancelled.');
  renderRaceway();
  renderPanel();
}

function addNodeFromEvent(event) {
  const run = activeRun();
  const rawPoint = sourcePointFromEvent(event);
  const { point, adjusted } = orthoAdjustedPoint(run, rawPoint);
  if (!run || !point) {
    setStatus('No point found on the active elevation.');
    return;
  }
  pushUndo('Add node');
  const previousPoint = run.nodes.at(-1) || null;
  run.nodes.push(point);
  state.selectedNodeIndex = run.nodes.length - 1;
  adoptWorkingElevationFromPoint(run, point);
  markRunDirty(run);
  if (adjusted) recordOrthoTelemetry(run, previousPoint, rawPoint, point);
  const anchor = anchorLabel(point.anchor);
  setStatus(anchor
    ? `${run.tag}: node ${run.nodes.length} added at EL +${formatM(point.z)} and anchored to ${anchor}.`
    : `${run.tag}: node ${run.nodes.length} added at EL +${formatM(point.z)}${adjusted ? ' with ortho lock.' : '.'}`);
  renderRaceway();
  renderPanel();
}

function deleteSelectedNode() {
  const run = activeRun();
  if (!run || state.selectedNodeIndex < 0) return;
  pushUndo('Delete node');
  run.nodes.splice(state.selectedNodeIndex, 1);
  state.selectedNodeIndex = Math.min(state.selectedNodeIndex, run.nodes.length - 1);
  markRunDirty(run);
  if (run.nodes.length) {
    activateNodeSelectionMode(run);
  } else {
    deactivateCanvasMode();
  }
  setStatus(`${run.tag}: node deleted.`);
  renderRaceway();
  renderPanel();
}

function moveSelectedNodeFromEvent(event) {
  const run = activeRun();
  const point = sourcePointFromEvent(event);
  if (!run || state.selectedNodeIndex < 0 || !point) return;
  pushUndo('Move node');
  run.nodes[state.selectedNodeIndex] = point;
  adoptWorkingElevationFromPoint(run, point);
  markRunDirty(run);
  activateNodeSelectionMode(run);
  const anchor = anchorLabel(point.anchor);
  setStatus(anchor
    ? `${run.tag}: node ${state.selectedNodeIndex + 1} moved to EL +${formatM(point.z)} and anchored to ${anchor}.`
    : `${run.tag}: node ${state.selectedNodeIndex + 1} moved to EL +${formatM(point.z)}.`);
  renderRaceway();
  renderPanel();
}

function csrfToken() {
  try {
    return document.cookie
      .split(';')
      .map(part => part.trim())
      .find(part => part.startsWith('csrftoken='))
      ?.slice('csrftoken='.length) || '';
  } catch (_error) {
    return '';
  }
}

function apiHeaders(method) {
  const headers = { Accept: 'application/json' };
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRFToken'] = csrfToken();
  }
  return headers;
}

async function apiFetch(url, options = {}) {
  const method = options.method || 'GET';
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    method,
    headers: {
      ...apiHeaders(method),
      ...(options.headers || {}),
    },
    body: options.body && typeof options.body !== 'string' ? JSON.stringify(options.body) : options.body,
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) {
    const message = payload.error || `Raceway request failed (${response.status}).`;
    const details = payload.errors ? ` ${JSON.stringify(payload.errors)}` : '';
    throw new Error(`${message}${details}`);
  }
  return payload;
}

function telemetryUuid() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, char => {
    const value = Math.floor(Math.random() * 16);
    const digit = char === 'x' ? value : ((value & 0x3) | 0x8);
    return digit.toString(16);
  });
}

function telemetryLifecycleKey(signature) {
  if (!telemetryLifecycleKeys.has(signature)) {
    telemetryLifecycleKeys.set(signature, telemetryUuid());
  }
  return telemetryLifecycleKeys.get(signature);
}

function telemetrySafeJson(value) {
  if (Array.isArray(value)) return value.map(item => telemetrySafeJson(item));
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => !TELEMETRY_FORBIDDEN_ID_KEYS.has(String(key)))
        .map(([key, item]) => [key, telemetrySafeJson(item)]),
    );
  }
  return value;
}

function scheduleTelemetryFlush() {
  if (telemetryFlushTimer) return;
  telemetryFlushTimer = window.setTimeout(() => {
    telemetryFlushTimer = null;
    flushTelemetryEvents();
  }, TELEMETRY_FLUSH_DELAY_MS);
}

function queueTelemetryEvent({ key = '', suggestionCode, action = 'shown', context = {}, actionDetail = {} }) {
  const packageInfo = packageContext();
  if (!packageInfo?.projectId || !suggestionCode) return;
  telemetryQueue.push({
    key: key || telemetryUuid(),
    project_id: packageInfo.projectId,
    owner_module: 'raceway',
    suggestion_code: suggestionCode,
    action,
    context: telemetrySafeJson(context),
    action_detail: telemetrySafeJson(actionDetail),
    client: TELEMETRY_CLIENT,
  });
  scheduleTelemetryFlush();
}

async function flushTelemetryEvents(options = {}) {
  if (telemetryFlushTimer) {
    window.clearTimeout(telemetryFlushTimer);
    telemetryFlushTimer = null;
  }
  if (!telemetryQueue.length) return null;
  const batch = telemetryQueue.splice(0, TELEMETRY_MAX_BATCH_SIZE);
  try {
    const response = await fetch(TELEMETRY_EVENTS_URL, {
      credentials: 'same-origin',
      method: 'POST',
      keepalive: Boolean(options.keepalive),
      headers: apiHeaders('POST'),
      body: JSON.stringify({ events: batch }),
    });
    if (!response.ok) throw new Error(`Telemetry request failed (${response.status}).`);
  } catch (error) {
    console.warn('Raceway telemetry was not recorded.', error?.message || error);
  } finally {
    if (telemetryQueue.length) scheduleTelemetryFlush();
  }
  return null;
}

function packageContext() {
  const pkg = runtime?.getPackage?.() || null;
  const projectId = String(pkg?.project_id || pkg?.metadata?.project_id || '').trim();
  const sourceModelId = Number(pkg?.source_model_id);
  const renderPackageId = Number(pkg?.id);
  if (!projectId) return null;
  return {
    projectId,
    sourceModelId: Number.isFinite(sourceModelId) && sourceModelId > 0 ? sourceModelId : null,
    renderPackageId: Number.isFinite(renderPackageId) && renderPackageId > 0 ? renderPackageId : null,
  };
}

function contextKey(context) {
  return `${context.projectId}:${context.sourceModelId || ''}:${context.renderPackageId || ''}`;
}

function urlWithQuery(path, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') query.set(key, value);
  });
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

async function loadCatalog() {
  if (state.catalogLoaded) return;
  if (catalogLoadPromise) {
    await catalogLoadPromise;
    return;
  }
  catalogLoadPromise = apiFetch(CATALOG_URL)
    .then(payload => {
      catalog = (Array.isArray(payload.families) ? payload.families : [])
        .map(normalizeFamily)
        .filter(family => family.id && family.sizes.length);
      state.catalogLoaded = true;
      initializeCatalogSelection();
    })
    .finally(() => {
      catalogLoadPromise = null;
    });
  await catalogLoadPromise;
}

function layerCollectionUrl(context) {
  return urlWithQuery(`/raceway/projects/${encodeURIComponent(context.projectId)}/layers/`, {
    source_model_id: context.sourceModelId,
    render_package_id: context.renderPackageId,
  });
}

function layerGraphUrl() {
  return state.layerId ? `/raceway/layers/${encodeURIComponent(state.layerId)}/graph/` : '';
}

function layerScheduleUrl() {
  return state.layerId ? `/raceway/layers/${encodeURIComponent(state.layerId)}/schedule/` : '';
}

function layerFittingsUrl() {
  return state.layerId ? `/raceway/layers/${encodeURIComponent(state.layerId)}/fittings/` : '';
}

function layerScheduleCsvUrl() {
  return state.layerId ? `/raceway/layers/${encodeURIComponent(state.layerId)}/schedule.csv` : '';
}

async function loadGraphProjection(options = {}) {
  const url = layerGraphUrl();
  if (!url) {
    clearGraphProjection();
    renderPanel();
    return null;
  }
  state.graphLoading = true;
  state.graphError = '';
  renderPanel();
  try {
    const payload = await apiFetch(url);
    state.graphProjection = payload.graph || null;
    state.graphLoaded = true;
    recordWarningTelemetry(graphWarnings(), 'shown');
    if (!options.quiet) {
      const count = graphWarnings().length;
      setStatus(count ? `Raceway graph refreshed with ${count} warning(s).` : 'Raceway graph refreshed with no warnings.');
    }
    return state.graphProjection;
  } catch (error) {
    state.graphProjection = null;
    state.graphLoaded = false;
    state.graphError = error.message || 'Unable to refresh raceway graph.';
    if (!options.quiet) setStatus(state.graphError);
    return null;
  } finally {
    state.graphLoading = false;
    renderPanel();
  }
}

async function loadScheduleProjection(options = {}) {
  const url = layerScheduleUrl();
  if (!url) {
    clearScheduleProjection();
    renderPanel();
    return null;
  }
  state.scheduleLoading = true;
  state.scheduleError = '';
  renderPanel();
  try {
    const payload = await apiFetch(url);
    state.scheduleProjection = payload.schedule || null;
    state.scheduleLoaded = true;
    recordWarningTelemetry(scheduleWarnings(), 'shown');
    if (!options.quiet) {
      const totals = state.scheduleProjection?.totals || {};
      setStatus(`Raceway schedule refreshed: ${formatM(totals.length_m)} m, ${totals.piece_count_estimate || 0} piece(s).`);
    }
    return state.scheduleProjection;
  } catch (error) {
    state.scheduleProjection = null;
    state.scheduleLoaded = false;
    state.scheduleError = error.message || 'Unable to refresh raceway schedule.';
    if (!options.quiet) setStatus(state.scheduleError);
    return null;
  } finally {
    state.scheduleLoading = false;
    renderPanel();
  }
}

async function loadFittingProjection(options = {}) {
  const url = layerFittingsUrl();
  if (!url) {
    clearFittingProjection();
    renderPanel();
    return null;
  }
  state.fittingsLoading = true;
  state.fittingsError = '';
  renderPanel();
  try {
    const payload = await apiFetch(url);
    state.fittingProjection = payload.fittings || null;
    state.fittingsLoaded = true;
    if (!options.quiet) {
      const counts = state.fittingProjection?.counts || {};
      const byKind = counts.by_kind || {};
      setStatus(
        `Raceway fittings refreshed: ${counts.total || 0} placeholder(s), `
        + `${byKind.reducer_candidate || 0} reducer candidate(s).`
      );
    }
    return state.fittingProjection;
  } catch (error) {
    state.fittingProjection = null;
    state.fittingsLoaded = false;
    state.fittingsError = error.message || 'Unable to refresh raceway fittings.';
    if (!options.quiet) setStatus(state.fittingsError);
    return null;
  } finally {
    state.fittingsLoading = false;
    renderPanel();
  }
}

function openScheduleCsv() {
  const url = layerScheduleCsvUrl();
  if (!url) {
    setStatus('Save a raceway layer before downloading the schedule CSV.');
    return;
  }
  window.open?.(url, '_blank', 'noopener');
  setStatus('Raceway schedule CSV download opened.');
}

function runFromServer(payload) {
  const serverFamily = payload.family || {};
  const serverSize = payload.size || {};
  const metadata = payload.metadata || {};
  const family = catalogFamilyById(payload.family_id);
  const sizeMatch = catalogSizeById(payload.size_id);
  const familyForSize = sizeMatch?.family || family;
  const size = sizeMatch || {};
  return {
    id: `raceway-run-${payload.id}`,
    serverRunId: payload.id,
    key: payload.key || '',
    tag: payload.tag || `RWY-${payload.id}`,
    familyId: String(payload.family_id || ''),
    familyCode: serverFamily.code || familyForSize?.code || family?.code || '',
    familyKind: serverFamily.kind || familyForSize?.kind || family?.kind || '',
    familyLabel: serverFamily.name || familyForSize?.label || family?.label || 'Raceway',
    sizeId: String(payload.size_id || ''),
    sizeCode: size.code || `${serverFamily.code || ''}-${serverSize.width_mm || ''}x${serverSize.depth_mm || ''}`,
    sizeLabel: serverSize.label || size.label || 'Catalogue size',
    widthMm: Number(serverSize.width_mm) || Number(size.widthMm) || 300,
    depthMm: Number(serverSize.depth_mm) || Number(size.depthMm) || 100,
    serviceClass: payload.service_class || services[0].id,
    elevationM: Number(payload.elevation_m) || 0,
    metadata,
    orientation: normalizedOrientation(metadata.orientation),
    nodes: (Array.isArray(payload.nodes) ? payload.nodes : [])
      .slice()
      .sort((left, right) => Number(left.sequence) - Number(right.sequence))
      .map(node => ({
        serverNodeId: node.id,
        key: node.key || '',
        x: Number(node.source_x_m) || 0,
        y: Number(node.source_y_m) || 0,
        z: Number(node.source_z_m) || 0,
        coordinate_frame: SOURCE_COORDINATE_FRAME,
        anchor: sanitizeAnchorForPersistence(node.anchor || {}),
      })),
    dirty: false,
  };
}

async function loadSavedRaceways({ force = false } = {}) {
  const context = packageContext();
  if (!context) {
    setStatus('Raceway persistence is waiting for package context.');
    return;
  }
  const key = contextKey(context);
  if (state.persistenceLoaded && state.contextKey === key && !force) return;
  state.persistenceLoading = true;
  renderPanel();
  try {
    await loadCatalog();
    const layerPayload = await apiFetch(layerCollectionUrl(context));
    const layers = Array.isArray(layerPayload.layers) ? layerPayload.layers : [];
    const layerMatch = layers.find(item => item.status === 'draft') || layers[0] || null;
    state.contextKey = key;
    state.layerId = layerMatch?.id || null;
    state.layerUrl = layerMatch?.url || '';
    state.runsUrl = layerMatch?.runs_url || '';
    state.persistenceLoaded = true;
    state.persistenceReady = true;
    if (!layerMatch) {
      clearGraphProjection();
      clearScheduleProjection();
      clearFittingProjection();
      if (force || !state.runs.length) {
        state.runs = [];
        state.activeRunId = '';
        state.selectedNodeIndex = -1;
        clearHistory();
        renderRaceway();
      }
      setStatus('No saved raceway runs for this package yet.');
      return;
    }
    const runPayload = await apiFetch(urlWithQuery(layerMatch.runs_url, { include_nodes: 1 }));
    state.runs = (Array.isArray(runPayload.runs) ? runPayload.runs : []).map(runFromServer);
    state.activeRunId = state.runs[0]?.id || '';
    state.selectedNodeIndex = -1;
    clearHistory();
    syncPaletteFromRun(activeRun());
    renderRaceway();
    await loadGraphProjection({ quiet: true });
    if (state.scheduleLoaded) await loadScheduleProjection({ quiet: true });
    if (state.fittingsLoaded) await loadFittingProjection({ quiet: true });
    setStatus(state.runs.length ? `${state.runs.length} saved raceway run(s) loaded.` : 'Raceway layer loaded with no runs.');
  } catch (error) {
    state.persistenceReady = false;
    setStatus(error.message || 'Unable to load saved raceway runs.');
  } finally {
    state.persistenceLoading = false;
    renderPanel();
  }
}

function confirmDiscardLocalChanges(actionLabel) {
  if (!hasUnsavedLocalChanges()) return true;
  const message = `${actionLabel} will discard unsaved local Raceway changes. Continue?`;
  return window.confirm?.(message) !== false;
}

async function reloadSavedRaceways() {
  if (!confirmDiscardLocalChanges('Reload Saved')) {
    setStatus('Reload cancelled; unsaved raceway changes were kept.');
    return;
  }
  await loadSavedRaceways({ force: true });
}

function removeRunFromState(run) {
  const removedIndex = state.runs.findIndex(item => item.id === run.id);
  state.runs = state.runs.filter(item => item.id !== run.id);
  const nextRun = state.runs[Math.max(Math.min(removedIndex, state.runs.length - 1), 0)] || null;
  state.activeRunId = nextRun?.id || '';
  state.selectedNodeIndex = -1;
  syncPaletteFromRun(nextRun);
  if (nextRun) {
    activateNodeSelectionMode(nextRun);
  } else {
    deactivateCanvasMode();
  }
  renderRaceway();
  renderPanel();
}

async function deleteActiveRun() {
  const run = activeRun();
  if (!run) {
    setStatus('Select a raceway run before deleting.');
    return;
  }
  const label = run.tag || 'selected raceway run';
  const message = run.serverRunId
    ? `Delete ${label} from the server?`
    : `Discard unsaved ${label}?`;
  if (window.confirm?.(message) === false) {
    setStatus('Delete cancelled.');
    return;
  }
  if (!run.serverRunId) {
    pushUndo('Delete run');
    removeRunFromState(run);
    setStatus(`${label} discarded.`);
    return;
  }
  state.persistenceLoading = true;
  renderPanel();
  try {
    await apiFetch(`/raceway/runs/${run.serverRunId}/`, { method: 'DELETE' });
    removeRunFromState(run);
    await loadGraphProjection({ quiet: true });
    if (state.scheduleLoaded) await loadScheduleProjection({ quiet: true });
    if (state.fittingsLoaded) await loadFittingProjection({ quiet: true });
    setStatus(`${label} deleted.`);
  } catch (error) {
    setStatus(error.message || `Unable to delete ${label}.`);
  } finally {
    state.persistenceLoading = false;
    renderPanel();
  }
}

function schedulePersistenceBootstrap() {
  if (persistenceBootstrapQueued) return;
  persistenceBootstrapQueued = true;
  window.setTimeout(() => {
    persistenceBootstrapQueued = false;
    loadSavedRaceways();
  }, 0);
}

async function ensureLayer(context) {
  if (state.layerId && state.runsUrl) {
    return { id: state.layerId, runs_url: state.runsUrl };
  }
  const payload = await apiFetch(`/raceway/projects/${encodeURIComponent(context.projectId)}/layers/`, {
    method: 'POST',
    body: {
      name: 'Raceway Draft',
      description: 'Aboveground raceway draft from Plant3D viewer.',
      source_model_id: context.sourceModelId,
      render_package_id: context.renderPackageId,
      metadata: { owner_module: 'raceway', authoring_surface: 'plant3d_viewer' },
    },
  });
  state.layerId = payload.layer.id;
  state.layerUrl = payload.layer.url;
  state.runsUrl = payload.layer.runs_url;
  return payload.layer;
}

function runPayload(run, context) {
  return {
    tag: run.tag,
    family_id: Number(run.familyId),
    size_id: Number(run.sizeId),
    service_class: run.serviceClass,
    status: 'draft',
    elevation_m: Number(run.elevationM) || 0,
    source_model_id: context.sourceModelId,
    render_package_id: context.renderPackageId,
    metadata: {
      proxy_kind: isLadderRun(run) ? 'ladder' : 'tray',
      catalogue_family_code: run.familyCode || '',
      catalogue_size_code: run.sizeCode || '',
      orientation: runOrientation(run),
    },
  };
}

function nodePayloads(run) {
  return run.nodes.map((node, index) => {
    const payload = {
      sequence: index,
      node_kind: index === 0 || index === run.nodes.length - 1 ? 'endpoint' : 'bend',
      source_x_m: Number(node.x) || 0,
      source_y_m: Number(node.y) || 0,
      source_z_m: Number(node.z) || 0,
      anchor: sanitizeAnchorForPersistence(node.anchor || {}),
      metadata: {},
    };
    if (node.key) payload.key = node.key;
    return payload;
  });
}

function applySavedRunPayload(localRun, payload) {
  localRun.serverRunId = payload.id;
  localRun.key = payload.key || localRun.key || '';
  localRun.id = `raceway-run-${payload.id}`;
  state.activeRunId = localRun.id;
}

async function saveDrafts() {
  const context = packageContext();
  if (!context) {
    setStatus('Raceway save is waiting for package context.');
    return;
  }
  state.persistenceLoading = true;
  renderPanel();
  try {
    await loadCatalog();
    const savableRuns = state.runs.filter(run => run.nodes.length >= 2);
    if (!savableRuns.length) {
      setStatus('Add at least two nodes before saving a raceway run.');
      return;
    }
    const persistentLayer = await ensureLayer(context);
    let savedCount = 0;
    for (const run of savableRuns) {
      try {
        const method = run.serverRunId ? 'PATCH' : 'POST';
        const url = run.serverRunId ? `/raceway/runs/${run.serverRunId}/` : persistentLayer.runs_url;
        const savedRun = await apiFetch(url, {
          method,
          body: runPayload(run, context),
        });
        applySavedRunPayload(run, savedRun.run);
        const savedNodes = await apiFetch(savedRun.run.nodes_url, {
          method: 'PUT',
          body: { nodes: nodePayloads(run) },
        });
        run.nodes = savedNodes.nodes.map(node => ({
          serverNodeId: node.id,
          key: node.key || '',
          x: Number(node.source_x_m) || 0,
          y: Number(node.source_y_m) || 0,
          z: Number(node.source_z_m) || 0,
          coordinate_frame: SOURCE_COORDINATE_FRAME,
          anchor: sanitizeAnchorForPersistence(node.anchor || {}),
        }));
        run.dirty = false;
        savedCount += 1;
      } catch (error) {
        throw new Error(`${run.tag || 'Raceway run'}: ${error.message || 'Unable to save this run.'}`);
      }
    }
    state.persistenceLoaded = true;
    state.persistenceReady = true;
    state.contextKey = contextKey(context);
    clearHistory();
    await loadGraphProjection({ quiet: true });
    if (state.scheduleLoaded) await loadScheduleProjection({ quiet: true });
    if (state.fittingsLoaded) await loadFittingProjection({ quiet: true });
    recordVisibleWarningTelemetry('unresolved_at_save', { actionDetail: { trigger: 'save' } });
    flushTelemetryEvents();
    setStatus(`${savedCount} raceway run(s) saved to server.`);
    renderRaceway();
  } catch (error) {
    setStatus(error.message || 'Unable to save raceway drafts.');
  } finally {
    state.persistenceLoading = false;
    renderPanel();
  }
}

function setStatus(message) {
  if (statusEl) statusEl.textContent = message;
}

function injectStyles() {
  if (document.getElementById('racewayViewerStyles')) return;
  const style = document.createElement('style');
  style.id = 'racewayViewerStyles';
  style.textContent = `
    .raceway-tool-grid, .raceway-aid-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .raceway-tool-grid label, .raceway-aid-grid label, .raceway-node-editor label { display: grid; gap: 4px; color: #475569; font-size: 11px; font-weight: 700; }
    .raceway-tool-grid select, .raceway-tool-grid input, .raceway-aid-grid select, .raceway-aid-grid input, .raceway-node-editor input { width: 100%; min-width: 0; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 6px; color: #0f172a; font-size: 12px; }
    .raceway-aid-grid { align-items: end; margin-top: 8px; }
    .raceway-check { align-self: end; min-height: 28px; display: flex !important; align-items: center; gap: 6px !important; }
    .raceway-check input { width: auto !important; }
    .raceway-summary-row { display: inline-flex; align-items: center; gap: 8px; }
    .raceway-warning-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 20px; height: 18px; padding: 0 6px; border-radius: 999px; background: #fee2e2; color: #991b1b; font-size: 11px; font-weight: 800; line-height: 1; }
    .raceway-warning-badge[hidden] { display: none; }
    .raceway-status { margin: 8px 0; color: #475569; font-size: 12px; line-height: 1.35; }
    .raceway-status-busy { color: #1d4ed8; }
    .raceway-run-list, .raceway-node-list { display: grid; gap: 6px; margin-top: 8px; }
    .raceway-row { width: 100%; justify-content: space-between; text-align: left; }
    .raceway-row-active { border-color: #2563eb; color: #1d4ed8; }
    .raceway-graph-warnings { display: grid; gap: 5px; margin-top: 8px; }
    .raceway-graph-warning { border-left: 3px solid #ca8a04; padding-left: 7px; color: #713f12; font-size: 11px; line-height: 1.35; }
    .raceway-graph-ok { color: #166534; font-size: 11px; }
    .raceway-graph-error { color: #991b1b; font-size: 11px; }
    .raceway-schedule-summary { margin-top: 8px; color: #334155; font-size: 11px; line-height: 1.4; }
    .raceway-schedule-summary strong { color: #0f172a; }
    .raceway-schedule-row { display: flex; justify-content: space-between; gap: 8px; border-top: 1px solid #e2e8f0; padding-top: 4px; margin-top: 4px; }
    .raceway-schedule-warning { color: #92400e; }
    .raceway-warning-list { display: grid; gap: 5px; margin-top: 8px; }
    .raceway-validation-warning { border: 0; border-left: 3px solid #ca8a04; background: transparent; padding: 0 0 0 7px; color: #713f12; font: inherit; font-size: 11px; line-height: 1.35; text-align: left; }
    button.raceway-validation-warning { cursor: pointer; }
    button.raceway-validation-warning:hover { background: rgba(202, 138, 4, 0.08); }
    .raceway-warning-active { background: rgba(220, 38, 38, 0.1); border-left-color: #dc2626; color: #7f1d1d; }
    .raceway-warning-info { border-left-color: #2563eb; color: #1e3a8a; }
    #racewayToolSection button:disabled { cursor: not-allowed; opacity: 0.55; }
    .raceway-node-editor { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
  `;
  document.head.appendChild(style);
}

function familyOptionsHtml() {
  if (!catalog.length) return '<option value="">Loading...</option>';
  return catalog.map(family => `<option value="${escapeHtml(family.id)}"${family.id === state.familyId ? ' selected' : ''}>${escapeHtml(family.label)}</option>`).join('');
}

function sizeOptionsHtml() {
  const family = activeFamily();
  if (!family?.sizes?.length) return '<option value="">Loading...</option>';
  return family.sizes.map(size => `<option value="${escapeHtml(size.id)}"${size.id === state.sizeId ? ' selected' : ''}>${escapeHtml(size.label)}</option>`).join('');
}

function serviceOptionsHtml() {
  return services.map(service => `<option value="${escapeHtml(service.id)}"${service.id === state.serviceClass ? ' selected' : ''}>${escapeHtml(service.label)}</option>`).join('');
}

function orientationOptionsHtml() {
  return orientationPresets.map(preset => `<option value="${escapeHtml(preset.id)}"${preset.id === state.orientationPreset ? ' selected' : ''}>${escapeHtml(preset.label)}</option>`).join('');
}

function segmentDirectionOptionsHtml() {
  return segmentDirections.map(direction => `<option value="${escapeHtml(direction.id)}"${direction.id === state.segmentDirection ? ' selected' : ''}>${escapeHtml(direction.label)}</option>`).join('');
}

function runRowsHtml() {
  if (!state.runs.length) return '<div class="meta">No raceway drafts</div>';
  return state.runs.map(run => `
    <button type="button" class="raceway-row ${run.id === state.activeRunId ? 'raceway-row-active' : ''}" data-raceway-action="select-run" data-run-id="${escapeHtml(run.id)}" title="Select raceway run">
      <strong>${escapeHtml(run.tag)}</strong><br>
      ${escapeHtml(run.familyLabel)} ${escapeHtml(run.sizeLabel)}<br>
      ${escapeHtml(serviceFor(run.serviceClass).label)} | ${isLadderRun(run) ? 'ladder proxy' : 'tray proxy'} | ${escapeHtml(orientationLabel(run))}<br>
      ${run.nodes.length} nodes | ${bendCount(run)} bends | ${riserCount(run)} risers | ${formatM(runLength(run))} m | ${runPersistenceLabel(run)}
    </button>
  `).join('');
}

function nodeRowsHtml() {
  const run = activeRun();
  if (!run?.nodes.length) return '<div class="meta">No nodes</div>';
  return run.nodes.map((node, index) => `
    <button type="button" class="raceway-row ${index === state.selectedNodeIndex ? 'raceway-row-active' : ''}" data-raceway-action="select-node" data-node-index="${index}" title="Select node ${index + 1}">
      N${index + 1} X ${formatM(node.x)} Y ${formatM(node.y)} EL ${formatM(node.z)}
      ${anchorLabel(node.anchor) ? `<br>Anchor: ${escapeHtml(anchorLabel(node.anchor))}` : ''}
    </button>
  `).join('');
}

function warningClass(warning) {
  return warning?.severity === 'info' ? 'raceway-warning-info' : 'raceway-warning-warning';
}

function warningFocusClass(index) {
  return state.warningFocus?.warningIndex === index ? ' raceway-warning-active' : '';
}

function localWarningLabel(warning) {
  return warning?.message || warning?.code || 'Raceway warning.';
}

function validationWarningLabel(warning) {
  if (warning?.code === 'raceway.warning.short_segment') {
    return warning.message || 'Short raceway segment; review adjacent nodes.';
  }
  if (warning?.code === 'raceway.warning.excessive_bends') {
    return warning.message || 'High bend count; review constructability and cable pulling.';
  }
  if (warning?.code === 'raceway.warning.too_few_nodes') {
    return warning.message || 'Run has fewer than two nodes.';
  }
  if (warning?.code === 'raceway.warning.inactive_catalog_reference') {
    return warning.message || 'Run references inactive catalogue data.';
  }
  if (warning?.code === 'raceway.warning.unknown_coordinate_context') {
    return warning.message || 'Coordinate context is incomplete.';
  }
  if (warning?.code === 'raceway.warning.support_span_placeholder_basis') {
    return warning.message || 'Support quantities are placeholder basis only.';
  }
  if (warning?.code === 'raceway.warning.model_clash_aabb') {
    const label = warning?.values?.object_label || warning?.values?.object_stable_id || 'Plant3D object';
    return `Raceway rough envelope overlaps ${label}.`;
  }
  if (warning?.code === 'raceway.warning.model_clearance_aabb') {
    const label = warning?.values?.object_label || warning?.values?.object_stable_id || 'Plant3D object';
    return `Raceway rough envelope is close to ${label}.`;
  }
  return warning?.message || warning?.code || 'Raceway validation notice.';
}

function localWarningsHtml(run, nodeIndex = -1) {
  const warnings = runWarnings(run).filter(warning => (
    nodeIndex < 0 || !warning.nodeIndices || warning.nodeIndices.includes(nodeIndex)
  ));
  if (!warnings.length) return '';
  return `
    <div class="raceway-warning-list">
      ${warnings.slice(0, 4).map(warning => `
        <div class="raceway-validation-warning ${warningClass(warning)}">
          ${escapeHtml(localWarningLabel(warning))}
        </div>
      `).join('')}
      ${warnings.length > 4 ? `<div class="meta">+${warnings.length - 4} more warning(s)</div>` : ''}
    </div>
  `;
}

function scheduleWarningRowsHtml(schedule) {
  const warnings = Array.isArray(schedule?.warnings) ? schedule.warnings : [];
  if (!warnings.length) return '';
  return `
    <div class="raceway-warning-list">
      ${warnings.slice(0, 4).map((warning, index) => {
        const label = escapeHtml(validationWarningLabel(warning));
        const className = `raceway-validation-warning ${warningClass(warning)}${warningFocusClass(index)}`;
        if (!warningTargetRun(warning)) {
          return `<div class="${className}">${label}</div>`;
        }
        return `
          <button type="button" class="${className}" data-raceway-action="select-warning" data-warning-index="${index}" title="Select affected raceway segment">
            ${label}
          </button>
        `;
      }).join('')}
      ${warnings.length > 4 ? `<div class="meta">+${warnings.length - 4} more validation notice(s) in JSON/CSV</div>` : ''}
    </div>
  `;
}

function graphWarningLabel(warning) {
  const point = warning?.source_point_m || {};
  const location = Number.isFinite(Number(point.x))
    ? ` at X ${formatM(point.x)} Y ${formatM(point.y)} EL ${formatM(point.z)}`
    : '';
  if (warning?.code === 'raceway.graph.unconnected_crossing') {
    return `Unconnected crossing${location}. Use Connect Node only where this is an intended tee/junction.`;
  }
  if (warning?.code === 'raceway.graph.near_miss_endpoint') {
    const distance = Number.isFinite(Number(warning.distance_m)) ? ` (${formatM(warning.distance_m)} m gap)` : '';
    return `Near-miss endpoint${location}${distance}. Select the endpoint and use Connect Node if this should be connected.`;
  }
  if (warning?.code === 'raceway.graph.zero_length_segment') {
    return `Collapsed segment within graph tolerance${warning.node_key ? ` near ${warning.node_key}` : ''}.`;
  }
  return warning?.message || warning?.code || 'Raceway graph warning.';
}

function graphWarningsHtml() {
  if (state.graphLoading) return '<div class="meta">Refreshing graph...</div>';
  if (state.graphError) return `<div class="raceway-graph-error">${escapeHtml(state.graphError)}</div>`;
  if (!state.layerId) return '';
  if (!state.graphLoaded) return '<div class="meta">Graph not refreshed yet.</div>';
  const warnings = graphWarnings();
  if (!warnings.length) return '<div class="raceway-graph-ok">Graph: no warnings in saved raceways.</div>';
  return warnings.map(warning => `
    <div class="raceway-graph-warning">
      ${escapeHtml(graphWarningLabel(warning))}
    </div>
  `).join('');
}

function racewayNoticeBadgeCount() {
  const scheduleCount = scheduleWarnings().length;
  const graphCount = scheduleCount ? 0 : graphWarnings().length;
  const draftCount = state.runs.reduce((total, run) => {
    if (run.serverRunId && !run.dirty) return total;
    return total + runWarnings(run).length;
  }, 0);
  return scheduleCount + graphCount + draftCount;
}

function scheduleSummaryHtml() {
  if (state.scheduleLoading) return '<div class="meta">Refreshing schedule...</div>';
  if (state.scheduleError) return `<div class="raceway-graph-error">${escapeHtml(state.scheduleError)}</div>`;
  if (!state.scheduleLoaded || !state.scheduleProjection) return '';
  const schedule = state.scheduleProjection;
  const totals = schedule.totals || {};
  const warnings = schedule.warning_summary || schedule.graph_warnings || {};
  const assumptions = Array.isArray(schedule.assumptions) ? schedule.assumptions : [];
  const groups = Array.isArray(schedule.groups) ? schedule.groups : [];
  const warningText = warnings.total
    ? `${warnings.total} validation notice(s) affect this schedule`
      + (warnings.by_severity ? ` (${warnings.warning || 0} warning, ${warnings.info || 0} info).` : '.')
    : '';
  const groupRows = groups.slice(0, 3).map(group => `
    <div class="raceway-schedule-row">
      <span>${escapeHtml(group.family_code)} ${escapeHtml(group.size_label)} ${escapeHtml(group.service_class)}</span>
      <span>${formatM(group.length_m)} m | ${group.piece_count_estimate || 0} pcs</span>
    </div>
  `).join('');
  return `
    <div>
      <strong>Schedule</strong><br>
      ${totals.run_count || 0} run(s) | ${formatM(totals.length_m)} m | ${totals.piece_count_estimate || 0} piece(s) | ${formatM(totals.offcut_m_estimate)} m offcut<br>
      ${totals.plan_bend_count || 0} bend(s) | ${totals.riser_count || 0} riser(s) | ${totals.support_placeholders || 0} support placeholder(s)
      ${warningText ? `<br><span class="raceway-schedule-warning">${escapeHtml(warningText)}</span>` : ''}
      <br>${assumptions.length} assumption(s) included in JSON/CSV output.
      ${groupRows}
      ${groups.length > 3 ? `<div class="meta">+${groups.length - 3} more group(s)</div>` : ''}
      ${scheduleWarningRowsHtml(schedule)}
    </div>
  `;
}

function fittingSummaryHtml() {
  if (state.fittingsLoading) return '<div class="meta">Refreshing fittings...</div>';
  if (state.fittingsError) return `<div class="raceway-graph-error">${escapeHtml(state.fittingsError)}</div>`;
  if (!state.fittingsLoaded || !state.fittingProjection) return '';
  const projection = state.fittingProjection;
  const counts = projection.counts || {};
  const byKind = counts.by_kind || {};
  const byCategory = counts.by_category || {};
  const graph = projection.graph_summary || {};
  const categoryRows = Object.entries(byCategory).slice(0, 4).map(([category, count]) => `
    <div class="raceway-schedule-row">
      <span>${escapeHtml(category)}</span>
      <span>${count}</span>
    </div>
  `).join('');
  return `
    <div>
      <strong>Fittings</strong><br>
      ${counts.total || 0} placeholder(s) | ${byKind.plan_bend || 0} bend(s) | ${byKind.riser || 0} riser(s) | ${byKind.reducer_candidate || 0} reducer candidate(s)<br>
      ${counts.requires_face_alignment || 0} need face alignment | ${counts.requires_catalogue_validation || 0} need catalogue validation<br>
      ${graph.junction_node_count || 0} junction node(s) | ${graph.branch_node_count || 0} branch node(s)
      ${categoryRows}
      ${(projection.assumptions || []).length ? `<div class="meta">${projection.assumptions.length} fitting assumption(s) in JSON output.</div>` : ''}
    </div>
  `;
}

function inspectorHtml() {
  const node = selectedNode();
  if (!node) return `<div class="meta">Select a node</div>${localWarningsHtml(activeRun())}`;
  const anchor = anchorLabel(node.anchor);
  return `
    <div class="raceway-node-editor">
      <label>X m<input type="number" step="0.001" value="${formatM(node.x)}" data-raceway-node-axis="x"></label>
      <label>Y m<input type="number" step="0.001" value="${formatM(node.y)}" data-raceway-node-axis="y"></label>
      <label>EL m<input type="number" step="0.001" value="${formatM(node.z)}" data-raceway-node-axis="z"></label>
    </div>
    <div class="meta" style="margin-top: 6px;">${anchor ? `Anchor: ${escapeHtml(anchor)}` : 'No plant model anchor'}</div>
    ${localWarningsHtml(activeRun(), state.selectedNodeIndex)}
  `;
}

function ensurePanel() {
  if (panel) return panel;
  const layerPanel = document.getElementById('viewerLayerList')?.closest('details');
  if (!layerPanel) return null;
  injectStyles();
  panel = document.createElement('details');
  panel.id = 'racewayToolSection';
  panel.className = 'panel p3d-viewer-section';
  panel.open = true;
  panel.innerHTML = `
    <summary><span class="raceway-summary-row"><span>Raceway Draft</span><span id="racewayWarningBadge" class="raceway-warning-badge" hidden>0</span></span></summary>
    <div id="racewayToolStatus" class="raceway-status">Ready</div>
    <div class="raceway-tool-grid">
      <label>Family<select id="racewayFamilySelect">${familyOptionsHtml()}</select></label>
      <label>Size<select id="racewaySizeSelect">${sizeOptionsHtml()}</select></label>
      <label>Service<select id="racewayServiceSelect">${serviceOptionsHtml()}</select></label>
      <label>Orientation<select id="racewayOrientationSelect">${orientationOptionsHtml()}</select></label>
      <label>EL m<input id="racewayElevationInput" type="number" step="0.001" value="${formatM(state.elevationM)}"></label>
    </div>
    <div class="raceway-aid-grid">
      <label class="raceway-check" title="${escapeHtml(actionTooltip('toggle-ortho'))}"><input id="racewayOrthoInput" type="checkbox" title="${escapeHtml(actionTooltip('toggle-ortho'))}"${state.orthoMode ? ' checked' : ''}> Ortho</label>
      <label>Direction<select id="racewaySegmentDirectionSelect">${segmentDirectionOptionsHtml()}</select></label>
      <label>Length m<input id="racewaySegmentLengthInput" type="number" min="0.001" step="0.001" value="${formatM(state.segmentLengthM)}"></label>
      <button type="button" data-raceway-action="add-segment" title="${escapeHtml(actionTooltip('add-segment'))}">Add Segment</button>
      <button id="racewaySurfaceToggleBtn" type="button" data-raceway-action="toggle-surfaces" title="${escapeHtml(actionTooltip('toggle-surfaces'))}" aria-pressed="${state.showProxyFaces ? 'true' : 'false'}">${state.showProxyFaces ? 'Surface On' : 'Wire Only'}</button>
    </div>
    <div class="p3d-toolbar" style="margin-top: 10px;">
      <button type="button" class="p3d-button-primary" data-raceway-action="start" title="${escapeHtml(actionTooltip('start'))}">Start</button>
      <button type="button" data-raceway-action="continue-run" title="${escapeHtml(actionTooltip('continue-run'))}">Continue</button>
      <button type="button" data-raceway-action="finish" title="${escapeHtml(actionTooltip('finish'))}">Finish</button>
      <button type="button" data-raceway-action="undo" title="${escapeHtml(actionTooltip('undo'))}">Undo</button>
      <button type="button" data-raceway-action="redo" title="${escapeHtml(actionTooltip('redo'))}">Redo</button>
      <button type="button" data-raceway-action="cancel" title="${escapeHtml(actionTooltip('cancel'))}">Cancel</button>
    </div>
    <div class="p3d-toolbar" style="margin-top: 8px;">
      <button type="button" data-raceway-action="select-node-mode" title="${escapeHtml(actionTooltip('select-node-mode'))}">Select Node</button>
      <button type="button" data-raceway-action="move-node" title="${escapeHtml(actionTooltip('move-node'))}">Move Node</button>
      <button type="button" data-raceway-action="delete-node" title="${escapeHtml(actionTooltip('delete-node'))}">Delete Node</button>
      <button type="button" data-raceway-action="connect-node" title="${escapeHtml(actionTooltip('connect-node'))}">Connect Node</button>
    </div>
    <div class="p3d-toolbar" style="margin-top: 8px;">
      <button type="button" data-raceway-action="anchor-node" title="${escapeHtml(actionTooltip('anchor-node'))}">Anchor Node</button>
      <button type="button" data-raceway-action="clear-anchor" title="${escapeHtml(actionTooltip('clear-anchor'))}">Clear Anchor</button>
    </div>
    <div class="p3d-toolbar" style="margin-top: 8px;">
      <button type="button" data-raceway-action="save" title="${escapeHtml(actionTooltip('save'))}">Save Draft</button>
      <button type="button" data-raceway-action="reload" title="${escapeHtml(actionTooltip('reload'))}">Reload Saved</button>
      <button type="button" data-raceway-action="refresh-graph" title="${escapeHtml(actionTooltip('refresh-graph'))}">Refresh Graph</button>
      <button type="button" data-raceway-action="refresh-schedule" title="${escapeHtml(actionTooltip('refresh-schedule'))}">Refresh Schedule</button>
      <button type="button" data-raceway-action="refresh-fittings" title="${escapeHtml(actionTooltip('refresh-fittings'))}">Refresh Fittings</button>
      <button type="button" data-raceway-action="open-schedule-csv" title="${escapeHtml(actionTooltip('open-schedule-csv'))}">CSV</button>
      <button type="button" data-raceway-action="delete-run" title="${escapeHtml(actionTooltip('delete-run'))}">Delete Run</button>
    </div>
    <div id="racewayInspector"></div>
    <div id="racewaySummary" class="meta" style="margin-top: 8px;"></div>
    <div id="racewayGraphWarnings" class="raceway-graph-warnings"></div>
    <div id="racewayScheduleSummary" class="raceway-schedule-summary"></div>
    <div id="racewayFittingSummary" class="raceway-schedule-summary"></div>
    <div id="racewayRunList" class="raceway-run-list"></div>
    <div id="racewayNodeList" class="raceway-node-list"></div>
  `;
  layerPanel.parentNode.insertBefore(panel, layerPanel);
  statusEl = panel.querySelector('#racewayToolStatus');
  summaryEl = panel.querySelector('#racewaySummary');
  graphWarningsEl = panel.querySelector('#racewayGraphWarnings');
  scheduleSummaryEl = panel.querySelector('#racewayScheduleSummary');
  fittingSummaryEl = panel.querySelector('#racewayFittingSummary');
  warningBadgeEl = panel.querySelector('#racewayWarningBadge');
  runListEl = panel.querySelector('#racewayRunList');
  nodeListEl = panel.querySelector('#racewayNodeList');
  inspectorEl = panel.querySelector('#racewayInspector');
  panel.addEventListener('click', handlePanelClick);
  panel.addEventListener('change', handlePanelChange);
  panel.addEventListener('input', handlePanelInput);
  panel.addEventListener('focusout', handlePanelFocusOut);
  return panel;
}

function setActionState(action, disabled, title = '') {
  panel?.querySelectorAll(`[data-raceway-action="${action}"]`).forEach(button => {
    button.disabled = Boolean(disabled);
    button.title = actionTooltip(action, disabled ? title : '');
  });
}

function updateActionStates(run) {
  const node = selectedNode();
  setActionState('start', !catalog.length, 'Raceway catalogue is still loading.');
  setActionState('continue-run', !run, 'Select a run before continuing it.');
  setActionState('finish', !run || (run.nodes.length < 2), 'Add at least two nodes before finishing.');
  setActionState('undo', !state.undoStack.length, 'Nothing to undo.');
  setActionState('redo', !state.redoStack.length, 'Nothing to redo.');
  setActionState('cancel', !run && state.mode === 'idle', 'No active raceway command.');
  setActionState('select-node-mode', !run, 'Select a run before selecting nodes on canvas.');
  setActionState('move-node', !node, 'Select a node before moving it.');
  setActionState('delete-node', !node, 'Select a node before deleting it.');
  setActionState('connect-node', !canConnectSelectedEndpoint(run), 'Select the first or last node of a run before connecting it.');
  setActionState('anchor-node', !run, 'Start or select a run before anchoring.');
  setActionState('clear-anchor', !node || !anchorLabel(node.anchor), 'Select an anchored node first.');
  setActionState('save', state.persistenceLoading || !state.runs.some(item => item.nodes.length >= 2), 'Add at least one two-node run before saving.');
  setActionState('reload', state.persistenceLoading, state.persistenceLoading ? 'Raceway persistence is busy.' : '');
  setActionState('refresh-graph', state.persistenceLoading || state.graphLoading || !state.layerId, state.layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before refreshing graph warnings.');
  setActionState('refresh-schedule', state.persistenceLoading || state.scheduleLoading || !state.layerId, state.layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before refreshing the schedule.');
  setActionState('refresh-fittings', state.persistenceLoading || state.fittingsLoading || !state.layerId, state.layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before refreshing fittings.');
  setActionState('open-schedule-csv', state.persistenceLoading || !state.layerId, state.layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before downloading CSV.');
  setActionState('delete-run', state.persistenceLoading || !run, 'Select a run before deleting it.');
  setActionState('add-segment', !run?.nodes?.length || !(Number(state.segmentLengthM) > 0), 'Add at least one node and enter a positive segment length.');
  setActionState('toggle-surfaces', false);
}

function renderPanel(options = {}) {
  if (!panel) return;
  const run = activeRun();
  const familySelect = panel.querySelector('#racewayFamilySelect');
  const sizeSelect = panel.querySelector('#racewaySizeSelect');
  const serviceSelect = panel.querySelector('#racewayServiceSelect');
  const orientationSelect = panel.querySelector('#racewayOrientationSelect');
  const orthoInput = panel.querySelector('#racewayOrthoInput');
  const surfaceToggleBtn = panel.querySelector('#racewaySurfaceToggleBtn');
  const segmentDirectionSelect = panel.querySelector('#racewaySegmentDirectionSelect');
  const segmentLengthInput = panel.querySelector('#racewaySegmentLengthInput');
  if (statusEl) statusEl.classList.toggle('raceway-status-busy', state.persistenceLoading);
  if (familySelect && familySelect !== document.activeElement) {
    familySelect.innerHTML = familyOptionsHtml();
    familySelect.value = state.familyId;
  }
  if (sizeSelect && sizeSelect !== document.activeElement) {
    sizeSelect.innerHTML = sizeOptionsHtml();
    sizeSelect.value = state.sizeId;
  }
  if (serviceSelect && serviceSelect !== document.activeElement) serviceSelect.value = state.serviceClass;
  if (orientationSelect && orientationSelect !== document.activeElement) {
    orientationSelect.innerHTML = orientationOptionsHtml();
    orientationSelect.value = state.orientationPreset;
  }
  if (orthoInput && orthoInput !== document.activeElement) orthoInput.checked = Boolean(state.orthoMode);
  if (surfaceToggleBtn) {
    surfaceToggleBtn.textContent = state.showProxyFaces ? 'Surface On' : 'Wire Only';
    surfaceToggleBtn.setAttribute('aria-pressed', state.showProxyFaces ? 'true' : 'false');
  }
  if (segmentDirectionSelect && segmentDirectionSelect !== document.activeElement) segmentDirectionSelect.value = state.segmentDirection;
  if (segmentLengthInput && segmentLengthInput !== document.activeElement) segmentLengthInput.value = formatM(state.segmentLengthM);
  if (panel.querySelector('#racewayElevationInput') !== document.activeElement) {
    panel.querySelector('#racewayElevationInput').value = formatM(state.elevationM);
  }
  if (summaryEl) {
    const warnings = run ? runWarnings(run).length : 0;
    const graphWarningCount = graphWarnings().length;
    const visualMode = state.showProxyFaces ? 'surface view' : 'wire view';
    summaryEl.textContent = run
      ? `${run.tag} | ${isLadderRun(run) ? 'ladder proxy' : 'tray proxy'} | ${visualMode} | ${orientationLabel(run)} | work EL +${formatM(run.elevationM)} | ${bendCount(run)} bends | ${riserCount(run)} risers | ${formatM(runLength(run))} m | ${runPersistenceLabel(run)} | ${warnings} local warning(s) | ${graphWarningCount} graph warning(s)`
      : 'No active run';
  }
  if (graphWarningsEl) graphWarningsEl.innerHTML = graphWarningsHtml();
  if (scheduleSummaryEl) scheduleSummaryEl.innerHTML = scheduleSummaryHtml();
  if (fittingSummaryEl) fittingSummaryEl.innerHTML = fittingSummaryHtml();
  if (warningBadgeEl) {
    const noticeCount = racewayNoticeBadgeCount();
    warningBadgeEl.hidden = noticeCount <= 0;
    warningBadgeEl.textContent = noticeCount > 99 ? '99+' : String(noticeCount);
    warningBadgeEl.title = `${noticeCount} Raceway validation notice(s)`;
  }
  if (runListEl) runListEl.innerHTML = runRowsHtml();
  if (nodeListEl) nodeListEl.innerHTML = nodeRowsHtml();
  if (inspectorEl && (options.forceInspector || !inspectorEl.contains(document.activeElement))) inspectorEl.innerHTML = inspectorHtml();
  recordVisibleWarningTelemetry('shown');
  updateActionStates(run);
}

function selectScheduleWarning(index) {
  const warningIndex = Number(index);
  const warning = scheduleWarnings()[warningIndex];
  const run = warningTargetRun(warning);
  if (!warning || !run) {
    setStatus('This schedule warning is not tied to a saved raceway run.');
    return false;
  }
  const segmentIndex = Number(warning.segment_index);
  state.activeRunId = run.id;
  state.selectedNodeIndex = warningTargetNodeIndex(run, warning);
  state.warningFocus = {
    warningIndex,
    runId: run.id,
    segmentIndex: Number.isInteger(segmentIndex) ? segmentIndex : null,
    code: warning.code || '',
  };
  syncPaletteFromRun(run);
  activateNodeSelectionMode(run);
  const framed = focusScheduleWarningTarget(warning, run);
  setStatus(`${run.tag}: selected from ${warning.code || 'schedule warning'}${framed ? ' and framed in viewer' : ''}.`);
  renderRaceway();
  renderPanel({ forceInspector: true });
  return true;
}

function runPanelAction(action, button = null) {
  if (action === 'start') beginRun();
  if (action === 'continue-run') continueRun();
  if (action === 'finish') finishRun();
  if (action === 'undo') undoRacewayEdit();
  if (action === 'redo') redoRacewayEdit();
  if (action === 'cancel') cancelRun();
  if (action === 'delete-node') deleteSelectedNode();
  if (action === 'connect-node') beginConnectNode();
  if (action === 'anchor-node') attachSelectedModelToNode();
  if (action === 'clear-anchor') clearSelectedNodeAnchor();
  if (action === 'save') saveDrafts();
  if (action === 'reload') reloadSavedRaceways();
  if (action === 'refresh-graph') loadGraphProjection({ quiet: false });
  if (action === 'refresh-schedule') loadScheduleProjection({ quiet: false });
  if (action === 'refresh-fittings') loadFittingProjection({ quiet: false });
  if (action === 'open-schedule-csv') openScheduleCsv();
  if (action === 'delete-run') deleteActiveRun();
  if (action === 'add-segment') addTypedSegment();
  if (action === 'toggle-ortho') {
    state.orthoMode = !state.orthoMode;
    setStatus(`Ortho drawing assist ${state.orthoMode ? 'on' : 'off'}.`);
    renderPanel();
  }
  if (action === 'toggle-surfaces') {
    state.showProxyFaces = !state.showProxyFaces;
    setStatus(`Raceway shaded faces ${state.showProxyFaces ? 'on' : 'off'}; wire overlay remains active.`);
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-node-mode') {
    activateNodeSelectionMode(activeRun());
    setStatus('Select Node: click a raceway node handle.');
    renderPanel();
  }
  if (action === 'move-node') {
    if (selectedNode()) {
      activateCanvasMode('move');
      setStatus('Move Node: click the replacement point.');
    } else {
      setStatus('Select a node before move.');
    }
  }
  if (action === 'select-run') {
    state.activeRunId = button?.dataset.runId || '';
    state.selectedNodeIndex = -1;
    state.warningFocus = null;
    syncPaletteFromRun(activeRun());
    activateNodeSelectionMode(activeRun());
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-node') {
    state.selectedNodeIndex = Number(button?.dataset.nodeIndex);
    state.warningFocus = null;
    activateNodeSelectionMode(activeRun());
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-warning') {
    selectScheduleWarning(button?.dataset.warningIndex);
  }
  return true;
}

function triggerRacewayAction(action) {
  ensurePanel();
  updateActionStates(activeRun());
  const button = panel?.querySelector(`[data-raceway-action="${action}"]`);
  if (button?.disabled) {
    setStatus(button.title || 'Raceway command unavailable.');
    return false;
  }
  return runPanelAction(action, button);
}

function handlePanelClick(event) {
  const button = event.target.closest?.('[data-raceway-action]');
  if (!button) return;
  if (button.disabled) return;
  runPanelAction(button.dataset.racewayAction, button);
}

function handlePanelChange(event) {
  const target = event.target;
  const run = activeRun();
  if (target.id === 'racewayFamilySelect') {
    if (run) pushUndo('Change raceway family');
    state.familyId = target.value;
    state.sizeId = activeFamily()?.sizes[0]?.id || '';
    panel.querySelector('#racewaySizeSelect').innerHTML = sizeOptionsHtml();
    applyPaletteToActiveRun();
  }
  if (target.id === 'racewaySizeSelect') {
    if (run) pushUndo('Change raceway size');
    state.sizeId = target.value;
    applyPaletteToActiveRun();
  }
  if (target.id === 'racewayServiceSelect') {
    if (run) pushUndo('Change raceway service');
    state.serviceClass = target.value;
    applyPaletteToActiveRun();
  }
  if (target.id === 'racewayOrientationSelect') {
    const preset = orientationPresetFor(target.value);
    if (run) {
      pushUndo('Change raceway orientation');
      run.orientation = normalizedOrientation(preset.id);
      markRunDirty(run);
      setStatus(`${run.tag}: orientation set to ${preset.label}. Save Draft to persist.`);
    } else {
      setStatus(`Default raceway orientation set to ${preset.label}.`);
    }
    state.orientationPreset = preset.id;
  }
  if (target.id === 'racewayElevationInput') {
    if (run) pushUndo('Change raceway elevation');
    state.elevationM = Number(target.value) || 0;
    state.elevationInitialized = true;
    applyPaletteToActiveRun({ shiftElevation: true });
  }
  if (target.id === 'racewayOrthoInput') {
    state.orthoMode = Boolean(target.checked);
    setStatus(`Ortho drawing assist ${state.orthoMode ? 'on' : 'off'}.`);
  }
  if (target.id === 'racewaySegmentDirectionSelect') {
    state.segmentDirection = target.value;
  }
  if (target.id === 'racewaySegmentLengthInput') {
    const length = Number(target.value);
    if (Number.isFinite(length) && length > 0) state.segmentLengthM = length;
  }
  renderRaceway();
  renderPanel();
}

function handlePanelInput(event) {
  if (event.target.id === 'racewaySegmentLengthInput') {
    const length = Number(event.target.value);
    if (Number.isFinite(length) && length > 0) state.segmentLengthM = length;
    renderPanel();
    return;
  }
  const axis = event.target.dataset?.racewayNodeAxis;
  if (!axis) return;
  const node = selectedNode();
  if (!node) return;
  const value = Number(event.target.value);
  if (!Number.isFinite(value)) return;
  const run = activeRun();
  if (run && event.target.dataset.racewayHistoryArmed !== '1') {
    pushUndo('Edit node coordinate');
    event.target.dataset.racewayHistoryArmed = '1';
  }
  node[axis] = value;
  if (axis === 'z') {
    if (run) run.elevationM = value;
    state.elevationM = value;
    state.elevationInitialized = true;
  }
  markRunDirty(run);
  renderRaceway();
  renderPanel();
}

function handlePanelFocusOut(event) {
  if (event.target.dataset?.racewayNodeAxis) {
    delete event.target.dataset.racewayHistoryArmed;
  }
}

function isTypingTarget(target) {
  return Boolean(target?.closest?.('input, textarea, select, [contenteditable="true"]'));
}

function racewayShortcutActionForEvent(event, key) {
  if (event.ctrlKey || event.metaKey) {
    if (event.altKey) return '';
    if (key === 'z') return event.shiftKey ? 'redo' : 'undo';
    if (key === 'y') return 'redo';
    if (key === 's') return 'save';
    return '';
  }
  if (event.altKey) return '';
  if (key === 'escape') return 'cancel';
  if (key === 'delete' || key === 'backspace') return event.shiftKey ? 'delete-run' : 'delete-node';
  if (key === 's' && !event.shiftKey) return 'start';
  if (key === 'c' && !event.shiftKey) return 'continue-run';
  if (key === 'f' && !event.shiftKey) return 'finish';
  if (key === 'n' && !event.shiftKey) return 'select-node-mode';
  if (key === 'm' && !event.shiftKey) return 'move-node';
  if (key === 'j' && !event.shiftKey) return 'connect-node';
  if (key === 'o' && !event.shiftKey) return 'toggle-ortho';
  if (key === 'v' && event.shiftKey) return 'toggle-surfaces';
  if (key === 'a') return event.shiftKey ? 'clear-anchor' : 'anchor-node';
  if (key === 'b') return event.shiftKey ? 'open-schedule-csv' : 'refresh-schedule';
  if (key === 'r' && !event.shiftKey) return 'reload';
  if (key === 'g' && !event.shiftKey) return 'refresh-graph';
  if (key === 't' && !event.shiftKey) return 'refresh-fittings';
  return '';
}

function racewayShortcutAvailableForAction(action) {
  if (!panel?.open || !action) return false;
  if (panel.contains(document.activeElement)) return true;
  if (state.mode !== 'idle') return true;
  const run = activeRun();
  if (run) return true;
  if (action === 'start') return true;
  if (action === 'toggle-ortho' || action === 'toggle-surfaces' || action === 'reload') return true;
  if (action === 'save') return state.runs.some(item => item.nodes.length >= 2);
  if (action === 'undo') return state.undoStack.length > 0;
  if (action === 'redo') return state.redoStack.length > 0;
  if (
    action === 'refresh-graph'
    || action === 'refresh-schedule'
    || action === 'refresh-fittings'
    || action === 'open-schedule-csv'
  ) {
    return Boolean(state.layerId);
  }
  return false;
}

function handleRacewayKeyboardShortcut(event) {
  if (event.defaultPrevented) return;
  const key = String(event.key || '').toLowerCase();
  const ctrlLike = event.ctrlKey || event.metaKey;
  const typingOutsideRaceway = isTypingTarget(event.target) && !panel?.contains(event.target);
  if (ctrlLike) {
    const action = racewayShortcutActionForEvent(event, key);
    if (!action || typingOutsideRaceway || !racewayShortcutAvailableForAction(action)) return;
    event.preventDefault();
    triggerRacewayAction(action);
    return;
  }
  if (!ctrlLike && !event.altKey && key === 'enter' && panel?.contains(event.target)) {
    if (event.target.closest?.('#racewaySegmentLengthInput, #racewaySegmentDirectionSelect')) {
      event.preventDefault();
      triggerRacewayAction('add-segment');
      return;
    }
  }
  if (isTypingTarget(event.target)) return;
  if (event.altKey) return;
  const action = racewayShortcutActionForEvent(event, key);
  if (!racewayShortcutAvailableForAction(action)) return;
  event.preventDefault();
  triggerRacewayAction(action);
}

window.addEventListener('plant3dviewer:layers-ready', scheduleBootstrap);
window.addEventListener('plant3dviewer:runtime-ready', scheduleBootstrap);
window.addEventListener('plant3dviewer:package-loaded', schedulePersistenceBootstrap);
window.addEventListener('DOMContentLoaded', scheduleBootstrap);
window.addEventListener('beforeunload', () => { flushTelemetryEvents({ keepalive: true }); });
document.addEventListener('keydown', handleRacewayKeyboardShortcut);
window.setTimeout(scheduleBootstrap, 0);

window.racewayViewerOverlay = {
  layerId: RACEWAY_LAYER_ID,
  layer,
  getRuns: () => state.runs.map(run => ({ ...run, nodes: run.nodes.map(node => ({ ...node })) })),
  setRuns: runs => {
    state.runs = Array.isArray(runs)
      ? runs.map(run => ({ ...run, nodes: Array.isArray(run.nodes) ? run.nodes.map(node => ({ ...node })) : [] }))
      : [];
    state.activeRunId = state.runs[0]?.id || '';
    state.selectedNodeIndex = -1;
    syncPaletteFromRun(activeRun());
    clearHistory();
    clearGraphProjection();
    clearScheduleProjection();
    clearFittingProjection();
    deactivateCanvasMode();
    renderRaceway();
    renderPanel();
  },
  flushTelemetry: flushTelemetryEvents,
  telemetryQueueSize: () => telemetryQueue.length,
};
