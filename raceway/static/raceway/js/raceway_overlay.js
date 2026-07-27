const RACEWAY_LAYER_ID = 'raceway-overlay';
const RACEWAY_INTERACTION_ID = 'raceway-centerline-authoring';
const CATALOG_URL = '/raceway/catalog/';
const TELEMETRY_EVENTS_URL = '/telemetry/events/';
const EXPECTED_FITTING_PROJECTION = 'raceway.fittings.v0';
const SOURCE_COORDINATE_FRAME = 'source_xyz_m';
const HISTORY_LIMIT = 80;
const NODE_HANDLE_SCREEN_PX = 5;
const NODE_HANDLE_SELECTED_SCREEN_PX = 6;
const NODE_HIT_TARGET_SCREEN_PX = 18;
const PROXY_FACE_OPACITY = 0.14;
const PROXY_FACE_SELECTED_OPACITY = 0.24;
const PROXY_BOTTOM_SHADE = 1.12;
const PROXY_SIDE_SHADE = 0.72;
const ACCESSORY_RADIUS_MIN_M = 0.05;
const ACCESSORY_RADIUS_MAX_M = 5;
const ACCESSORY_DEFAULT_RADIUS_M = 0.6;
const ACCESSORY_CURVE_SEGMENTS = 8;
const TELEMETRY_FLUSH_DELAY_MS = 750;
const TELEMETRY_MAX_BATCH_SIZE = 50;
const RACEWAY_MEASUREMENT_SNAP_KINDS = new Set([
  'side-rail',
  'lower-edge',
  'depth-tick',
  'rung',
  'tray-cross-member',
  'accessory-side-rail',
  'accessory-lower-edge',
  'accessory-cross-member',
  'reducer-side-rail',
  'reducer-lower-edge',
  'reducer-cross-member',
  'branch-side-rail',
  'branch-lower-edge',
  'branch-cross-member',
]);
const ORIENTATION_SCHEMA = 'raceway.orientation.v0';
const SEGMENT_ORIENTATION_SCHEMA = 'raceway.segment_orientation.v0';
const SEGMENT_FACE_OFFSET_SCHEMA = 'raceway.segment_face_offset.v0';
const SEGMENT_ORIENTATION_INHERIT = '__run_default__';
const SEGMENT_FACE_OFFSET_EPSILON_M = 0.0005;
const SEGMENT_FACE_OFFSET_LIMIT_M = 5;
const DEFAULT_REDUCER_HANDEDNESS = 'left_edge';
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

const reducerHandednessOptions = [
  { id: 'left_edge', label: 'Left Edge' },
  { id: 'right_edge', label: 'Right Edge' },
  { id: 'centerline', label: 'Centerline' },
];

const state = {
  runs: [],
  activeRunId: '',
  selectedNodeIndex: -1,
  selectedSegmentIndex: -1,
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
  loadedServerRunIds: [],
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
  segmentSplitPercent: 50,
  accessoryRadiusM: ACCESSORY_DEFAULT_RADIUS_M,
  reducerHandedness: DEFAULT_REDUCER_HANDEDNESS,
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
  'apply-reducer-offsets': 'Apply reducer edge-match offset suggestions',
  'open-warning-details': 'Open raceway warning details',
  'open-schedule-csv': 'Download raceway schedule CSV',
  'delete-run': 'Delete active run',
  'add-segment': 'Add typed segment from the last node',
  'split-segment': 'Split selected segment into two editable segments',
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
  'apply-reducer-offsets': 'Shift+T',
  'open-warning-details': 'Shift+W',
  'open-schedule-csv': 'Shift+B',
  'delete-run': 'Shift+Del',
  'add-segment': 'Enter in segment fields',
  'split-segment': 'Shift+X',
  'toggle-ortho': 'O',
  'toggle-surfaces': 'Shift+V',
};

let layer = null;
let runtime = null;
let interaction = null;
let panel = null;
let statusEl = null;
let commandHintEl = null;
let summaryEl = null;
let graphWarningsEl = null;
let scheduleSummaryEl = null;
let fittingSummaryEl = null;
let warningBadgeEl = null;
let runListEl = null;
let nodeListEl = null;
let segmentListEl = null;
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

function segmentPairKey(startNode, endNode) {
  const startKey = String(startNode?.key || '');
  const endKey = String(endNode?.key || '');
  return startKey && endKey ? `${startKey}::${endKey}` : '';
}

function normalizedSegmentOrientationOverride(rawOverride) {
  if (!rawOverride || typeof rawOverride !== 'object') return null;
  const startNodeKey = String(rawOverride.start_node_key || rawOverride.startNodeKey || '').trim();
  const endNodeKey = String(rawOverride.end_node_key || rawOverride.endNodeKey || '').trim();
  const preset = orientationPresets.find(item => item.id === String(rawOverride.preset || rawOverride.orientation?.preset || '').trim());
  if (!startNodeKey || !endNodeKey || !preset) return null;
  return {
    key: `${startNodeKey}::${endNodeKey}`,
    start_node_key: startNodeKey,
    end_node_key: endNodeKey,
    orientation: normalizedOrientation(preset.id),
  };
}

function ensureSegmentOrientationOverrides(run) {
  if (!run) return {};
  if (run.segmentOrientationOverrides && typeof run.segmentOrientationOverrides === 'object') {
    const metadataOverrides = run.metadata?.segment_orientation?.overrides;
    if (Object.keys(run.segmentOrientationOverrides).length || !Array.isArray(metadataOverrides) || !metadataOverrides.length) {
      return run.segmentOrientationOverrides;
    }
  }
  const overrides = {};
  const rawOverrides = run.metadata?.segment_orientation?.overrides || run.segmentOrientation?.overrides || [];
  if (Array.isArray(rawOverrides)) {
    rawOverrides.forEach(rawOverride => {
      const override = normalizedSegmentOrientationOverride(rawOverride);
      if (override) overrides[override.key] = override;
    });
  }
  run.segmentOrientationOverrides = overrides;
  return overrides;
}

function segmentOrientationOverrideFor(run, segmentKey) {
  const overrides = ensureSegmentOrientationOverrides(run);
  return overrides[String(segmentKey || '')] || null;
}

function segmentOrientationFor(run, segmentKey) {
  return segmentOrientationOverrideFor(run, segmentKey)?.orientation || runOrientation(run);
}

function segmentIntentStatusFor(run, segmentKey) {
  return segmentHasIntentOverride(run, segmentKey) ? 'segment_override' : 'run_default';
}

function segmentOrientationPayloadFromOverrides(run, overrides) {
  const items = [];
  (run?.nodes || []).forEach((node, index) => {
    if (index < 1) return;
    const key = segmentPairKey(run.nodes[index - 1], node);
    const override = overrides[key];
    if (!key || !override) return;
    items.push({
      start_node_key: override.start_node_key,
      end_node_key: override.end_node_key,
      preset: override.orientation.preset,
      quarter_turns: override.orientation.quarter_turns,
      label: override.orientation.label,
    });
  });
  return {
    schema: SEGMENT_ORIENTATION_SCHEMA,
    overrides: items,
  };
}

function segmentOrientationPayload(run) {
  return segmentOrientationPayloadFromOverrides(run, ensureSegmentOrientationOverrides(run));
}

function normalizedFaceOffsetM(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.min(Math.max(parsed, -SEGMENT_FACE_OFFSET_LIMIT_M), SEGMENT_FACE_OFFSET_LIMIT_M);
}

function normalizedSegmentSplitPercent(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 50;
  return Math.min(Math.max(parsed, 1), 99);
}

function normalizedAccessoryRadiusM(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return ACCESSORY_DEFAULT_RADIUS_M;
  return Math.min(Math.max(parsed, ACCESSORY_RADIUS_MIN_M), ACCESSORY_RADIUS_MAX_M);
}

function normalizedReducerHandedness(value) {
  const id = String(value || '').trim();
  return reducerHandednessOptions.some(option => option.id === id) ? id : DEFAULT_REDUCER_HANDEDNESS;
}

function normalizedSegmentFaceOffsetOverride(rawOverride) {
  if (!rawOverride || typeof rawOverride !== 'object') return null;
  const startNodeKey = String(rawOverride.start_node_key || rawOverride.startNodeKey || '').trim();
  const endNodeKey = String(rawOverride.end_node_key || rawOverride.endNodeKey || '').trim();
  const faceOffsetM = normalizedFaceOffsetM(rawOverride.face_offset_m ?? rawOverride.faceOffsetM);
  if (!startNodeKey || !endNodeKey || Math.abs(faceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) return null;
  return {
    key: `${startNodeKey}::${endNodeKey}`,
    start_node_key: startNodeKey,
    end_node_key: endNodeKey,
    face_offset_m: faceOffsetM,
  };
}

function ensureSegmentFaceOffsetOverrides(run) {
  if (!run) return {};
  if (run.segmentFaceOffsetOverrides && typeof run.segmentFaceOffsetOverrides === 'object') {
    const metadataOverrides = run.metadata?.segment_face_offset?.overrides;
    if (Object.keys(run.segmentFaceOffsetOverrides).length || !Array.isArray(metadataOverrides) || !metadataOverrides.length) {
      return run.segmentFaceOffsetOverrides;
    }
  }
  const overrides = {};
  const rawOverrides = run.metadata?.segment_face_offset?.overrides || run.segmentFaceOffset?.overrides || [];
  if (Array.isArray(rawOverrides)) {
    rawOverrides.forEach(rawOverride => {
      const override = normalizedSegmentFaceOffsetOverride(rawOverride);
      if (override) overrides[override.key] = override;
    });
  }
  run.segmentFaceOffsetOverrides = overrides;
  return overrides;
}

function segmentFaceOffsetOverrideFor(run, segmentKey) {
  const overrides = ensureSegmentFaceOffsetOverrides(run);
  return overrides[String(segmentKey || '')] || null;
}

function segmentFaceOffsetFor(run, segmentKey) {
  return segmentFaceOffsetOverrideFor(run, segmentKey)?.face_offset_m || 0;
}

function segmentHasIntentOverride(run, segmentKey) {
  return Boolean(segmentOrientationOverrideFor(run, segmentKey))
    || Math.abs(segmentFaceOffsetFor(run, segmentKey)) >= SEGMENT_FACE_OFFSET_EPSILON_M;
}

function segmentFaceOffsetPayloadFromOverrides(run, overrides) {
  const items = [];
  (run?.nodes || []).forEach((node, index) => {
    if (index < 1) return;
    const key = segmentPairKey(run.nodes[index - 1], node);
    const override = overrides[key];
    if (!key || !override || Math.abs(Number(override.face_offset_m) || 0) < SEGMENT_FACE_OFFSET_EPSILON_M) return;
    items.push({
      start_node_key: override.start_node_key,
      end_node_key: override.end_node_key,
      face_offset_m: Number(override.face_offset_m) || 0,
    });
  });
  return {
    schema: SEGMENT_FACE_OFFSET_SCHEMA,
    overrides: items,
  };
}

function segmentFaceOffsetPayload(run) {
  return segmentFaceOffsetPayloadFromOverrides(run, ensureSegmentFaceOffsetOverrides(run));
}

function segmentIntentSnapshot(run) {
  const intents = new Map();
  runSegments(run).forEach(segment => {
    const orientationPreset = segmentOrientationOverrideFor(run, segment.key)?.orientation?.preset || '';
    const faceOffsetM = segmentFaceOffsetFor(run, segment.key);
    if (!orientationPreset && Math.abs(faceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) return;
    intents.set(Number(segment.segmentIndex), {
      orientationPreset,
      effectiveOrientationPreset: segment.orientation?.preset || runOrientation(run).preset,
      faceOffsetM,
    });
  });
  return intents;
}

function assignSegmentOrientationOverride(overrides, segment, presetId) {
  const preset = orientationPresets.find(item => item.id === String(presetId || ''));
  if (!preset || !segment?.key) return false;
  overrides[segment.key] = {
    key: segment.key,
    start_node_key: String(segment.startNode?.key || ''),
    end_node_key: String(segment.endNode?.key || ''),
    orientation: normalizedOrientation(preset.id),
  };
  return true;
}

function assignSegmentFaceOffsetOverride(overrides, segment, faceOffsetM) {
  const offsetM = normalizedFaceOffsetM(faceOffsetM);
  if (!segment?.key || Math.abs(offsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) return false;
  overrides[segment.key] = {
    key: segment.key,
    start_node_key: String(segment.startNode?.key || ''),
    end_node_key: String(segment.endNode?.key || ''),
    face_offset_m: offsetM,
  };
  return true;
}

function rewriteSegmentIntentOverrides(run, intentBySegmentIndex) {
  const orientationOverrides = {};
  const faceOffsetOverrides = {};
  runSegments(run).forEach(segment => {
    const intent = intentBySegmentIndex.get(Number(segment.segmentIndex));
    if (!intent) return;
    if (intent.orientationPreset) {
      assignSegmentOrientationOverride(orientationOverrides, segment, intent.orientationPreset);
    }
    assignSegmentFaceOffsetOverride(faceOffsetOverrides, segment, intent.faceOffsetM);
  });
  run.segmentOrientationOverrides = orientationOverrides;
  run.segmentFaceOffsetOverrides = faceOffsetOverrides;
  run.metadata = {
    ...(run.metadata || {}),
    segment_orientation: segmentOrientationPayloadFromOverrides(run, orientationOverrides),
    segment_face_offset: segmentFaceOffsetPayloadFromOverrides(run, faceOffsetOverrides),
  };
}

function cloneSegmentIntent(intent) {
  return intent
    ? {
        orientationPreset: intent.orientationPreset || '',
        effectiveOrientationPreset: intent.effectiveOrientationPreset || intent.orientationPreset || '',
        faceOffsetM: normalizedFaceOffsetM(intent.faceOffsetM),
      }
    : null;
}

function mergedSegmentIntent(leftIntent, rightIntent, runDefaultOrientationPreset = DEFAULT_ORIENTATION_PRESET) {
  const left = cloneSegmentIntent(leftIntent) || { orientationPreset: '', faceOffsetM: 0 };
  const right = cloneSegmentIntent(rightIntent) || { orientationPreset: '', faceOffsetM: 0 };
  const merged = {};
  let conflict = false;
  if (left.orientationPreset || right.orientationPreset) {
    if (left.orientationPreset && left.orientationPreset === right.orientationPreset) {
      merged.orientationPreset = left.orientationPreset;
    } else {
      conflict = true;
    }
  }
  const leftHasOffset = Math.abs(left.faceOffsetM) >= SEGMENT_FACE_OFFSET_EPSILON_M;
  const rightHasOffset = Math.abs(right.faceOffsetM) >= SEGMENT_FACE_OFFSET_EPSILON_M;
  if (leftHasOffset || rightHasOffset) {
    const mergedOrientationPreset = merged.orientationPreset || runDefaultOrientationPreset || DEFAULT_ORIENTATION_PRESET;
    const offsetFrameSurvives = left.effectiveOrientationPreset === mergedOrientationPreset
      && right.effectiveOrientationPreset === mergedOrientationPreset;
    if (
      leftHasOffset
      && rightHasOffset
      && Math.abs(left.faceOffsetM - right.faceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M
      && offsetFrameSurvives
    ) {
      merged.faceOffsetM = left.faceOffsetM;
    } else {
      conflict = true;
    }
  }
  return {
    intent: Object.keys(merged).length ? merged : null,
    conflict,
  };
}

function segmentOrientationPresetByPreviousIndex(run, oldSegments) {
  const previousByIndex = new Map(
    (oldSegments || [])
      .filter(segment => segment.intentStatus === 'segment_override')
      .map(segment => [Number(segment.segmentIndex), segment.orientation.preset]),
  );
  const oldSegmentsByKey = new Map((oldSegments || []).map(segment => [segment.key, segment]));
  Object.values(ensureSegmentOrientationOverrides(run)).forEach(override => {
    const draftMatch = String(override.key || '').match(/^draft:(\d+)$/);
    if (draftMatch) {
      previousByIndex.set(Number(draftMatch[1]), override.orientation?.preset);
      return;
    }
    const previousSegment = oldSegmentsByKey.get(String(override.key || ''));
    if (previousSegment) {
      previousByIndex.set(Number(previousSegment.segmentIndex), override.orientation?.preset);
    }
  });
  return previousByIndex;
}

function segmentFaceOffsetByPreviousIndex(run, oldSegments) {
  const previousByIndex = new Map(
    (oldSegments || [])
      .filter(segment => Math.abs(Number(segment.faceOffsetM) || 0) >= SEGMENT_FACE_OFFSET_EPSILON_M)
      .map(segment => [Number(segment.segmentIndex), Number(segment.faceOffsetM) || 0]),
  );
  const oldSegmentsByKey = new Map((oldSegments || []).map(segment => [segment.key, segment]));
  Object.values(ensureSegmentFaceOffsetOverrides(run)).forEach(override => {
    const draftMatch = String(override.key || '').match(/^draft:(\d+)$/);
    if (draftMatch) {
      previousByIndex.set(Number(draftMatch[1]), Number(override.face_offset_m) || 0);
      return;
    }
    const previousSegment = oldSegmentsByKey.get(String(override.key || ''));
    if (previousSegment) {
      previousByIndex.set(Number(previousSegment.segmentIndex), Number(override.face_offset_m) || 0);
    }
  });
  return previousByIndex;
}

function migrateDraftSegmentOrientationOverrides(run, oldSegments) {
  const previousByIndex = segmentOrientationPresetByPreviousIndex(run, oldSegments);
  const previousOverrides = ensureSegmentOrientationOverrides(run);
  const overrides = {};
  runSegments(run).forEach(segment => {
    const preset = previousOverrides[segment.key]?.orientation?.preset
      || previousByIndex.get(Number(segment.segmentIndex));
    const presetConfig = orientationPresets.find(item => item.id === preset);
    if (!presetConfig || segment.keyStatus !== 'saved') return;
    overrides[segment.key] = {
      key: segment.key,
      start_node_key: String(segment.startNode.key || ''),
      end_node_key: String(segment.endNode.key || ''),
      orientation: normalizedOrientation(presetConfig.id),
    };
  });
  run.segmentOrientationOverrides = overrides;
  run.metadata = {
    ...(run.metadata || {}),
    segment_orientation: segmentOrientationPayloadFromOverrides(run, overrides),
  };
}

function migrateDraftSegmentFaceOffsetOverrides(run, oldSegments) {
  const previousByIndex = segmentFaceOffsetByPreviousIndex(run, oldSegments);
  const previousOverrides = ensureSegmentFaceOffsetOverrides(run);
  const overrides = {};
  runSegments(run).forEach(segment => {
    const faceOffsetM = previousOverrides[segment.key]?.face_offset_m
      ?? previousByIndex.get(Number(segment.segmentIndex))
      ?? 0;
    if (Math.abs(faceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M || segment.keyStatus !== 'saved') return;
    overrides[segment.key] = {
      key: segment.key,
      start_node_key: String(segment.startNode.key || ''),
      end_node_key: String(segment.endNode.key || ''),
      face_offset_m: normalizedFaceOffsetM(faceOffsetM),
    };
  });
  run.segmentFaceOffsetOverrides = overrides;
  run.metadata = {
    ...(run.metadata || {}),
    segment_face_offset: segmentFaceOffsetPayloadFromOverrides(run, overrides),
  };
}

function segmentIntentPayloads(run) {
  return {
    segment_orientation: segmentOrientationPayload(run),
    segment_face_offset: segmentFaceOffsetPayload(run),
  };
}

function activeRun() {
  return state.runs.find(run => run.id === state.activeRunId) || null;
}

function markRunDirty(run = activeRun()) {
  if (run) run.dirty = true;
}

function hasUnsavedLocalChanges() {
  return state.runs.some(run => !run.serverRunId || run.dirty) || serverRunIdsRemovedFromDraft().length > 0;
}

function runHasUnsavedSavableChanges(run) {
  return Boolean(run && run.nodes?.length >= 2 && (!run.serverRunId || run.dirty));
}

function normalizedServerRunId(value) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
}

function serverRunIdsFromRuns(runs) {
  const ids = new Set();
  (runs || []).forEach(run => {
    const id = normalizedServerRunId(run?.serverRunId);
    if (id !== null) ids.add(id);
  });
  return Array.from(ids).sort((left, right) => left - right);
}

function rememberLoadedServerRuns(runs = state.runs, options = {}) {
  const ids = new Set(serverRunIdsFromRuns(runs));
  if (options.merge) {
    state.loadedServerRunIds.forEach(id => ids.add(id));
  }
  state.loadedServerRunIds = Array.from(ids).sort((left, right) => left - right);
}

function forgetLoadedServerRun(serverRunId) {
  const id = normalizedServerRunId(serverRunId);
  if (id === null) return;
  state.loadedServerRunIds = state.loadedServerRunIds.filter(loadedId => loadedId !== id);
}

function savableRunsForPersistence() {
  return state.runs.filter(run => run.nodes.length >= 2);
}

function serverRunIdsRemovedFromDraft(savableRuns = savableRunsForPersistence()) {
  const keptIds = new Set(serverRunIdsFromRuns(savableRuns));
  return state.loadedServerRunIds.filter(id => !keptIds.has(id));
}

function hasUnsavedSavableChanges() {
  return state.runs.some(runHasUnsavedSavableChanges) || serverRunIdsRemovedFromDraft().length > 0;
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
    selectedSegmentIndex: state.selectedSegmentIndex,
    mode: state.mode,
    familyId: state.familyId,
    sizeId: state.sizeId,
    serviceClass: state.serviceClass,
    elevationM: state.elevationM,
    elevationInitialized: state.elevationInitialized,
    orientationPreset: state.orientationPreset,
    segmentSplitPercent: state.segmentSplitPercent,
    accessoryRadiusM: state.accessoryRadiusM,
    reducerHandedness: state.reducerHandedness,
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
  state.selectedSegmentIndex = Number(snapshot.selectedSegmentIndex);
  if (!Number.isInteger(state.selectedSegmentIndex)) state.selectedSegmentIndex = -1;
  const run = activeRun();
  if (!run || state.selectedNodeIndex >= run.nodes.length) {
    state.selectedNodeIndex = run?.nodes.length ? run.nodes.length - 1 : -1;
  }
  if (!run || state.selectedSegmentIndex < 1 || state.selectedSegmentIndex >= run.nodes.length) {
    state.selectedSegmentIndex = -1;
  }
  state.familyId = snapshot.familyId || state.familyId;
  state.sizeId = snapshot.sizeId || state.sizeId;
  state.serviceClass = snapshot.serviceClass || state.serviceClass;
  state.elevationM = Number(snapshot.elevationM) || 0;
  state.elevationInitialized = Boolean(snapshot.elevationInitialized);
  state.orientationPreset = orientationPresetFor(snapshot.orientationPreset).id;
  state.segmentSplitPercent = normalizedSegmentSplitPercent(snapshot.segmentSplitPercent);
  state.accessoryRadiusM = normalizedAccessoryRadiusM(snapshot.accessoryRadiusM);
  state.reducerHandedness = normalizedReducerHandedness(snapshot.reducerHandedness);
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

function clearDerivedProjections() {
  clearGraphProjection();
  clearScheduleProjection();
  clearFittingProjection();
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

function warningSegmentIsFocused(run, segmentIndex) {
  const focus = state.warningFocus;
  return Boolean(focus && focus.runId === run.id && Number(focus.segmentIndex) === Number(segmentIndex));
}

function selectedSegmentIsFocused(run, segmentIndex) {
  return run.id === state.activeRunId && Number(segmentIndex) === Number(state.selectedSegmentIndex);
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
    metadata: {},
    segmentOrientationOverrides: {},
    segmentFaceOffsetOverrides: {},
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

function orthoAdjustedPoint(run, point, previousPoint = null) {
  if (!state.orthoMode || !run?.nodes?.length || !point) {
    return { point, adjusted: false };
  }
  if (point.anchor && Object.keys(point.anchor).length) {
    return { point, adjusted: false };
  }
  const previous = previousPoint || run.nodes[run.nodes.length - 1];
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

function continuationAnchor(run, { allowDefaultLast = true } = {}) {
  const nodes = run?.nodes || [];
  if (!nodes.length) return null;
  if (nodes.length > 1 && state.selectedNodeIndex === 0) {
    return { node: nodes[0], index: 0, mode: 'prepend' };
  }
  if (state.selectedNodeIndex === nodes.length - 1) {
    return { node: nodes[nodes.length - 1], index: nodes.length - 1, mode: 'append' };
  }
  if (state.selectedNodeIndex >= 0 && state.selectedNodeIndex < nodes.length) {
    return null;
  }
  return allowDefaultLast
    ? { node: nodes[nodes.length - 1], index: nodes.length - 1, mode: 'append' }
    : null;
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
  state.selectedSegmentIndex = -1;
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

function segmentIdentity(startNode, endNode, segmentIndex) {
  const startKey = String(startNode?.key || '');
  const endKey = String(endNode?.key || '');
  if (startKey && endKey) {
    return {
      key: `${startKey}::${endKey}`,
      status: 'saved',
      label: `${startKey.slice(0, 8)} -> ${endKey.slice(0, 8)}`,
    };
  }
  return {
    key: `draft:${segmentIndex}`,
    status: 'draft',
    label: 'draft identity until saved',
  };
}

function runSegments(run) {
  const nodes = run?.nodes || [];
  const segments = [];
  for (let index = 1; index < nodes.length; index += 1) {
    const startNode = nodes[index - 1];
    const endNode = nodes[index];
    const lengthM = nodeDistance(startNode, endNode);
    const dz = Number(endNode?.z || 0) - Number(startNode?.z || 0);
    const identity = segmentIdentity(startNode, endNode, index);
    const orientationOverride = segmentOrientationOverrideFor(run, identity.key);
    const orientation = orientationOverride?.orientation || runOrientation(run);
    const faceOffsetM = segmentFaceOffsetFor(run, identity.key);
    segments.push({
      segmentIndex: index,
      startNodeIndex: index - 1,
      endNodeIndex: index,
      startNode,
      endNode,
      lengthM,
      isRiser: Math.abs(dz) > 0.001,
      orientation,
      orientationOverride: Boolean(orientationOverride),
      faceOffsetM,
      faceOffsetOverride: Math.abs(faceOffsetM) >= SEGMENT_FACE_OFFSET_EPSILON_M,
      intentStatus: segmentIntentStatusFor(run, identity.key),
      key: identity.key,
      keyStatus: identity.status,
      keyLabel: identity.label,
    });
  }
  return segments;
}

function selectedSegment() {
  const run = activeRun();
  if (!run || state.selectedSegmentIndex < 1) return null;
  return runSegments(run).find(segment => segment.segmentIndex === state.selectedSegmentIndex) || null;
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

function reducerEdgeMatchTelemetrySignature(candidate, offset) {
  return [
    'reducer-edge-match',
    candidate?.fitting_key || '',
    candidate?.graph_node_key || '',
    offset?.run_key || '',
    offset?.segment_key || '',
  ].join('|');
}

function recordReducerEdgeMatchTelemetry(candidate, offset, action = 'shown', actionDetail = {}) {
  if (!candidate || !offset) return;
  const signature = reducerEdgeMatchTelemetrySignature(candidate, offset);
  if (action === 'shown' && telemetryShownSignatures.has(signature)) return;
  if (action === 'shown') telemetryShownSignatures.add(signature);
  queueTelemetryEvent({
    key: telemetryLifecycleKey(signature),
    suggestionCode: 'raceway.reducer.edge_match_offset',
    action,
    context: {
      fitting_key: candidate.fitting_key || '',
      category: candidate.category || '',
      graph_node_key: candidate.graph_node_key || '',
      graph_node_kind: candidate.graph_node_kind || '',
      source_point_m: candidate.source_point_m || {},
      recommended_handedness: candidate.face_alignment?.recommended_handedness || '',
      selected_handedness: state.reducerHandedness,
      current_status: candidate.face_alignment?.current_status || '',
      centerline_aligned: Boolean(candidate.face_alignment?.centerline_aligned),
      run_key: offset.run_key || '',
      run_tag: offset.run_tag || '',
      node_key: offset.node_key || '',
      segment_key: offset.segment_key || '',
      segment_index: offset.segment_index,
      width_mm: offset.width_mm,
      current_face_offset_m: offset.current_face_offset_m,
      suggested_face_offset_m: offset.suggested_face_offset_m,
      delta_face_offset_m: offset.delta_face_offset_m,
      max_recommended_offset_delta_m: candidate.face_alignment?.max_recommended_offset_delta_m,
    },
    actionDetail,
  });
}

function recordReducerEdgeMatchProjectionTelemetry(projection, action = 'shown') {
  reducerEdgeMatchCandidates(projection).forEach(candidate => {
    const alignmentSuggestion = reducerAlignmentSuggestion(candidate);
    (alignmentSuggestion.member_offsets || []).forEach(offset => {
      recordReducerEdgeMatchTelemetry(candidate, offset, action);
    });
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

function basisFromLateralReference(start, end, lateralReference) {
  const sx = Number(start?.x || 0);
  const sy = Number(start?.y || 0);
  const sz = Number(start?.z || 0);
  const dx = Number(end?.x || 0) - sx;
  const dy = Number(end?.y || 0) - sy;
  const dz = Number(end?.z || 0) - sz;
  const length = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (length < 0.001) return null;

  const tx = dx / length;
  const ty = dy / length;
  const tz = dz / length;
  const rawNx = Number(lateralReference?.x || 0);
  const rawNy = Number(lateralReference?.y || 0);
  const rawNz = Number(lateralReference?.z || 0);
  const dot = (rawNx * tx) + (rawNy * ty) + (rawNz * tz);
  let nx = rawNx - (dot * tx);
  let ny = rawNy - (dot * ty);
  let nz = rawNz - (dot * tz);
  let nLength = Math.sqrt((nx * nx) + (ny * ny) + (nz * nz));
  if (nLength < 0.001) return null;
  nx /= nLength;
  ny /= nLength;
  nz /= nLength;

  let depthX = (ty * nz) - (tz * ny);
  let depthY = (tz * nx) - (tx * nz);
  let depthZ = (tx * ny) - (ty * nx);
  let depthLength = Math.sqrt((depthX * depthX) + (depthY * depthY) + (depthZ * depthZ));
  if (depthLength < 0.001) return null;
  depthX /= depthLength;
  depthY /= depthLength;
  depthZ /= depthLength;
  return { length, tx, ty, tz, nx, ny, nz, dx: depthX, dy: depthY, dz: depthZ };
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

function orientedSegmentBasis(run, start, end, orientation = runOrientation(run)) {
  const basis = segmentPlanBasis(start, end);
  return rollBasisAroundTangent(basis, normalizedOrientation(orientation).quarter_turns);
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

function pointTowardPoint(from, to, distanceM) {
  const dx = Number(to?.x || 0) - Number(from?.x || 0);
  const dy = Number(to?.y || 0) - Number(from?.y || 0);
  const dz = Number(to?.z || 0) - Number(from?.z || 0);
  const length = Math.sqrt((dx * dx) + (dy * dy) + (dz * dz));
  if (length < 0.001) return { x: Number(from?.x || 0), y: Number(from?.y || 0), z: Number(from?.z || 0) };
  const distance = Math.min(Math.max(Number(distanceM) || 0, 0), length);
  return {
    x: Number(from?.x || 0) + (dx / length) * distance,
    y: Number(from?.y || 0) + (dy / length) * distance,
    z: Number(from?.z || 0) + (dz / length) * distance,
  };
}

function planBendInfoAtNode(run, nodeIndex) {
  const nodes = run?.nodes || [];
  if (nodeIndex < 1 || nodeIndex >= nodes.length - 1) return null;
  const previous = nodes[nodeIndex - 1];
  const node = nodes[nodeIndex];
  const next = nodes[nodeIndex + 1];
  const inX = Number(node.x || 0) - Number(previous.x || 0);
  const inY = Number(node.y || 0) - Number(previous.y || 0);
  const outX = Number(next.x || 0) - Number(node.x || 0);
  const outY = Number(next.y || 0) - Number(node.y || 0);
  const inPlan = Math.sqrt((inX * inX) + (inY * inY));
  const outPlan = Math.sqrt((outX * outX) + (outY * outY));
  if (inPlan < 0.05 || outPlan < 0.05) return null;
  const cosine = Math.min(Math.max(((inX * outX) + (inY * outY)) / (inPlan * outPlan), -1), 1);
  const angleDeg = Math.acos(cosine) * 180 / Math.PI;
  if (angleDeg < 5) return null;
  const radiusM = normalizedAccessoryRadiusM(state.accessoryRadiusM);
  const rawCutbackM = radiusM * Math.tan((angleDeg * Math.PI / 180) / 2);
  return {
    previous,
    node,
    next,
    angleDeg,
    radiusM,
    incomingCutbackM: Math.min(rawCutbackM, inPlan * 0.45),
    outgoingCutbackM: Math.min(rawCutbackM, outPlan * 0.45),
  };
}

function riserTurnInfoAtNode(run, nodeIndex) {
  const nodes = run?.nodes || [];
  if (nodeIndex < 1 || nodeIndex >= nodes.length - 1) return null;
  const previous = nodes[nodeIndex - 1];
  const node = nodes[nodeIndex];
  const next = nodes[nodeIndex + 1];
  const beforeDz = Number(node.z || 0) - Number(previous.z || 0);
  const afterDz = Number(next.z || 0) - Number(node.z || 0);
  const beforeIsRiser = Math.abs(beforeDz) > 0.001;
  const afterIsRiser = Math.abs(afterDz) > 0.001;
  if (beforeIsRiser === afterIsRiser) return null;
  const beforeLength = nodeDistance(previous, node);
  const afterLength = nodeDistance(node, next);
  if (beforeLength < 0.05 || afterLength < 0.05) return null;
  const radiusM = normalizedAccessoryRadiusM(state.accessoryRadiusM);
  return {
    previous,
    node,
    next,
    radiusM,
    incomingCutbackM: Math.min(radiusM, beforeLength * 0.45),
    outgoingCutbackM: Math.min(radiusM, afterLength * 0.45),
    incomingIsRiser: beforeIsRiser,
    outgoingIsRiser: afterIsRiser,
    category: (afterIsRiser ? afterDz : beforeDz) >= 0 ? 'riser-up' : 'riser-down',
  };
}

function fittingProjectionItems() {
  return Array.isArray(state.fittingProjection?.items) ? state.fittingProjection.items : [];
}

function reducerProxyItems() {
  return fittingProjectionItems().filter(item => (
    item?.kind === 'reducer_candidate'
    && item?.status === 'synthetic_proxy'
    && item?.geometry_recipe?.proxy_kind === 'reducer_taper'
  ));
}

function branchProxyItems() {
  return fittingProjectionItems().filter(item => (
    (item?.kind === 'tee' || item?.kind === 'cross')
    && item?.status === 'synthetic_proxy'
    && (item?.geometry_recipe?.proxy_kind === 'tee_node_proxy' || item?.geometry_recipe?.proxy_kind === 'cross_node_proxy')
  ));
}

function reducerTrimForSegmentNode(run, segment, nodeIndex) {
  if (!run || !segment || !state.fittingsLoaded) return 0;
  const nodeKey = String(run.nodes?.[nodeIndex]?.key || '');
  if (!nodeKey) return 0;
  let trimM = 0;
  reducerProxyItems().forEach(item => {
    const cutback = Number(item.geometry_recipe?.straight_proxy_cutback?.each_port_m);
    if (!Number.isFinite(cutback) || cutback <= 0) return;
    const port = (item.geometry_recipe?.ports || []).find(candidate => (
      String(candidate.run_key || '') === String(run.key || '')
      && String(candidate.segment_key || '') === String(segment.key || '')
      && String(candidate.node_key || '') === nodeKey
    ));
    if (port) trimM = Math.max(trimM, cutback);
  });
  return trimM;
}

function branchTrimForSegmentNode(run, segment, nodeIndex) {
  if (!run || !segment || !state.fittingsLoaded) return 0;
  const nodeKey = String(run.nodes?.[nodeIndex]?.key || '');
  if (!nodeKey) return 0;
  let trimM = 0;
  branchProxyItems().forEach(item => {
    const cutback = Number(item.geometry_recipe?.straight_proxy_cutback?.default_each_port_m);
    if (!Number.isFinite(cutback) || cutback <= 0) return;
    const port = (item.ports || []).find(candidate => (
      String(candidate.run_key || '') === String(run.key || '')
      && String(candidate.segment_key || '') === String(segment.key || '')
      && String(candidate.node_key || '') === nodeKey
    ));
    if (port) trimM = Math.max(trimM, cutback);
  });
  return trimM;
}

function nodeAccessoryTrimM(run, nodeIndex, side) {
  const planBend = planBendInfoAtNode(run, nodeIndex);
  const riserTurn = riserTurnInfoAtNode(run, nodeIndex);
  const segment = segmentNearNode(run, nodeIndex, side);
  const trimCandidates = [];
  if (planBend) trimCandidates.push(side === 'incoming' ? planBend.incomingCutbackM : planBend.outgoingCutbackM);
  if (riserTurn) trimCandidates.push(side === 'incoming' ? riserTurn.incomingCutbackM : riserTurn.outgoingCutbackM);
  trimCandidates.push(reducerTrimForSegmentNode(run, segment, nodeIndex));
  trimCandidates.push(branchTrimForSegmentNode(run, segment, nodeIndex));
  return Math.max(...trimCandidates, 0);
}

function segmentTrimmedEndpoints(run, segment) {
  const startTrim = nodeAccessoryTrimM(run, segment.startNodeIndex, 'outgoing');
  const endTrim = nodeAccessoryTrimM(run, segment.endNodeIndex, 'incoming');
  const basis = segmentPlanBasis(segment.startNode, segment.endNode);
  if (basis.length < 0.001) return { start: segment.startNode, end: segment.endNode };
  let trimStart = Math.min(startTrim, basis.length * 0.45);
  let trimEnd = Math.min(endTrim, basis.length * 0.45);
  if (trimStart + trimEnd > basis.length * 0.8) {
    const scale = (basis.length * 0.8) / (trimStart + trimEnd);
    trimStart *= scale;
    trimEnd *= scale;
  }
  const start = sourcePointAlongSegment(segment.startNode, basis, trimStart);
  const end = sourcePointAlongSegment(segment.startNode, basis, Math.max(basis.length - trimEnd, 0));
  return { start, end, trimStartM: trimStart, trimEndM: trimEnd };
}

function segmentCornerPoints(run, start, end, orientation = runOrientation(run), faceOffsetM = 0, basisOverride = null) {
  const basis = basisOverride || orientedSegmentBasis(run, start, end, orientation);
  if (basis.length < 0.001) return null;
  const halfWidth = runWidthM(run) / 2;
  const depth = runDepthM(run);
  const offset = normalizedFaceOffsetM(faceOffsetM);
  const leftStartBottom = sourceFrameOffsetPoint(start, basis, offset + halfWidth, 0);
  const leftEndBottom = sourceFrameOffsetPoint(end, basis, offset + halfWidth, 0);
  const rightStartBottom = sourceFrameOffsetPoint(start, basis, offset - halfWidth, 0);
  const rightEndBottom = sourceFrameOffsetPoint(end, basis, offset - halfWidth, 0);
  const leftStartTop = sourceFrameOffsetPoint(start, basis, offset + halfWidth, depth);
  const leftEndTop = sourceFrameOffsetPoint(end, basis, offset + halfWidth, depth);
  const rightStartTop = sourceFrameOffsetPoint(start, basis, offset - halfWidth, depth);
  const rightEndTop = sourceFrameOffsetPoint(end, basis, offset - halfWidth, depth);
  return {
    basis,
    faceOffsetM: offset,
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

function addSegmentProxyFaces(positions, colors, run, start, end, faceColors, orientation = runOrientation(run), faceOffsetM = 0, basisOverride = null) {
  const corners = segmentCornerPoints(run, start, end, orientation, faceOffsetM, basisOverride);
  if (!corners) return;
  addProxyQuad(positions, colors, corners.leftStartBottom, corners.rightStartBottom, corners.rightEndBottom, corners.leftEndBottom, faceColors.bottom);
  addProxyQuad(positions, colors, corners.leftStartBottom, corners.leftEndBottom, corners.leftEndTop, corners.leftStartTop, faceColors.side);
  addProxyQuad(positions, colors, corners.rightStartBottom, corners.rightStartTop, corners.rightEndTop, corners.rightEndBottom, faceColors.side);
}

function addRunProxyFaceMesh(group, run, color, selected) {
  const positions = [];
  const colors = [];
  const faceColors = proxyFaceColors(color, selected);
  runSegments(run).forEach(segment => {
    const trimmed = segmentTrimmedEndpoints(run, segment);
    const basis = segmentRenderBasis(run, segment, trimmed.start, trimmed.end);
    addSegmentProxyFaces(positions, colors, run, trimmed.start, trimmed.end, faceColors, segment.orientation, segment.faceOffsetM, basis);
  });
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

function addSegmentPreview(group, run, start, end, material, detailMaterial, bottomEdgeMaterial = detailMaterial, orientation = runOrientation(run), faceOffsetM = 0, basisOverride = null) {
  const corners = segmentCornerPoints(run, start, end, orientation, faceOffsetM, basisOverride);
  if (!corners) return;
  const { basis } = corners;
  const halfWidth = runWidthM(run) / 2;

  addSourceLine(group, [corners.leftStartTop, corners.leftEndTop], material, 'side-rail');
  addSourceLine(group, [corners.rightStartTop, corners.rightEndTop], material, 'side-rail');
  addSourceLine(group, [corners.leftStartBottom, corners.leftEndBottom], bottomEdgeMaterial, 'lower-edge');
  addSourceLine(group, [corners.rightStartBottom, corners.rightEndBottom], bottomEdgeMaterial, 'lower-edge');
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
    const leftBottom = sourceFrameOffsetPoint(center, basis, corners.faceOffsetM + halfWidth, 0);
    const rightBottom = sourceFrameOffsetPoint(center, basis, corners.faceOffsetM - halfWidth, 0);
    addSourceLine(group, [leftBottom, rightBottom], detailMaterial, isLadderRun(run) ? 'rung' : 'tray-cross-member');
  }
}

function quadraticBezierPoint(start, control, end, t) {
  const u = 1 - t;
  return {
    x: (u * u * Number(start.x || 0)) + (2 * u * t * Number(control.x || 0)) + (t * t * Number(end.x || 0)),
    y: (u * u * Number(start.y || 0)) + (2 * u * t * Number(control.y || 0)) + (t * t * Number(end.y || 0)),
    z: (u * u * Number(start.z || 0)) + (2 * u * t * Number(control.z || 0)) + (t * t * Number(end.z || 0)),
  };
}

function curveBasisAt(points, index, orientation, basisReference = null) {
  const previous = points[Math.max(index - 1, 0)];
  const next = points[Math.min(index + 1, points.length - 1)];
  if (basisReference) {
    const inherited = basisFromLateralReference(previous, next, {
      x: basisReference.nx,
      y: basisReference.ny,
      z: basisReference.nz,
    });
    if (inherited) return inherited;
  }
  const basis = segmentPlanBasis(previous, next);
  return rollBasisAroundTangent(basis, normalizedOrientation(orientation).quarter_turns);
}

function accessoryCurveCornerPoints(run, points, orientation = runOrientation(run), faceOffsetM = 0, basisReference = null) {
  if (!Array.isArray(points) || points.length < 2) return;
  const halfWidth = runWidthM(run) / 2;
  const depth = runDepthM(run);
  const offset = normalizedFaceOffsetM(faceOffsetM);
  const leftTop = [];
  const rightTop = [];
  const leftBottom = [];
  const rightBottom = [];
  points.forEach((point, index) => {
    const basis = curveBasisAt(points, index, orientation, basisReference);
    leftTop.push(sourceFrameOffsetPoint(point, basis, offset + halfWidth, depth));
    rightTop.push(sourceFrameOffsetPoint(point, basis, offset - halfWidth, depth));
    leftBottom.push(sourceFrameOffsetPoint(point, basis, offset + halfWidth, 0));
    rightBottom.push(sourceFrameOffsetPoint(point, basis, offset - halfWidth, 0));
  });
  return { leftTop, rightTop, leftBottom, rightBottom };
}

function addAccessoryCurveFaceMesh(group, curveCorners, color, selected, previewKind) {
  if (!curveCorners || !Array.isArray(curveCorners.leftBottom) || curveCorners.leftBottom.length < 2) return null;
  const positions = [];
  const colors = [];
  const faceColors = proxyFaceColors(color, selected);
  for (let index = 1; index < curveCorners.leftBottom.length; index += 1) {
    const previous = index - 1;
    addProxyQuad(
      positions,
      colors,
      curveCorners.leftBottom[previous],
      curveCorners.rightBottom[previous],
      curveCorners.rightBottom[index],
      curveCorners.leftBottom[index],
      faceColors.bottom,
    );
    addProxyQuad(
      positions,
      colors,
      curveCorners.leftBottom[previous],
      curveCorners.leftBottom[index],
      curveCorners.leftTop[index],
      curveCorners.leftTop[previous],
      faceColors.side,
    );
    addProxyQuad(
      positions,
      colors,
      curveCorners.rightBottom[previous],
      curveCorners.rightTop[previous],
      curveCorners.rightTop[index],
      curveCorners.rightBottom[index],
      faceColors.side,
    );
  }
  if (positions.length < 18) return null;
  const geometry = setGeometryPositions(new runtime.THREE.BufferGeometry(), positions, colors);
  const mesh = new runtime.THREE.Mesh(geometry, proxyFaceMaterial(color, selected));
  mesh.userData.racewayPreviewKind = previewKind;
  mesh.userData.faceCount = positions.length / 18;
  mesh.renderOrder = 20;
  group.add(mesh);
  return mesh;
}

function addAccessoryCurveRails(group, run, points, material, detailMaterial, kind, orientation = runOrientation(run), faceOffsetM = 0, options = {}) {
  const curveCorners = accessoryCurveCornerPoints(run, points, orientation, faceOffsetM, options.basisReference || null);
  if (!curveCorners) return;
  if (options.surfaceKind) {
    addAccessoryCurveFaceMesh(group, curveCorners, options.color || 0xbe123c, Boolean(options.selected), options.surfaceKind);
  }
  const { leftTop, rightTop, leftBottom, rightBottom } = curveCorners;
  addSourceLine(group, leftTop, material, 'accessory-side-rail');
  addSourceLine(group, rightTop, material, 'accessory-side-rail');
  addSourceLine(group, leftBottom, detailMaterial, 'accessory-lower-edge');
  addSourceLine(group, rightBottom, detailMaterial, 'accessory-lower-edge');
  const crossbarIndexes = [0, Math.floor((points.length - 1) / 2), points.length - 1];
  Array.from(new Set(crossbarIndexes)).forEach(index => {
    addSourceLine(group, [leftBottom[index], rightBottom[index]], detailMaterial, 'accessory-cross-member');
  });
  const guide = addSourceLine(group, points, material, kind);
  if (guide) guide.renderOrder = 26;
}

function bendCurvePoints(start, control, end) {
  const points = [];
  for (let index = 0; index <= ACCESSORY_CURVE_SEGMENTS; index += 1) {
    points.push(quadraticBezierPoint(start, control, end, index / ACCESSORY_CURVE_SEGMENTS));
  }
  return points;
}

function segmentNearNode(run, nodeIndex, side) {
  const segmentIndex = side === 'incoming' ? nodeIndex : nodeIndex + 1;
  return runSegments(run).find(segment => segment.segmentIndex === segmentIndex) || null;
}

function riserTurnReferenceSegment(run, nodeIndex, info) {
  const incoming = segmentNearNode(run, nodeIndex, 'incoming');
  const outgoing = segmentNearNode(run, nodeIndex, 'outgoing');
  if (info?.incomingIsRiser && outgoing && !outgoing.isRiser) return outgoing;
  if (info?.outgoingIsRiser && incoming && !incoming.isRiser) return incoming;
  return incoming || outgoing || null;
}

function riserSegmentReferenceSegment(run, segment) {
  if (!segment?.isRiser) return null;
  const segments = runSegments(run);
  const incoming = segments.find(candidate => candidate.segmentIndex === segment.segmentIndex - 1) || null;
  const outgoing = segments.find(candidate => candidate.segmentIndex === segment.segmentIndex + 1) || null;
  if (incoming && !incoming.isRiser) return incoming;
  if (outgoing && !outgoing.isRiser) return outgoing;
  return null;
}

function segmentRenderBasis(run, segment, start = segment?.startNode, end = segment?.endNode) {
  const orientation = segment?.orientation || runOrientation(run);
  if (segment?.isRiser && !segment.orientationOverride) {
    const referenceSegment = riserSegmentReferenceSegment(run, segment);
    if (referenceSegment) {
      const referenceBasis = orientedSegmentBasis(
        run,
        referenceSegment.startNode,
        referenceSegment.endNode,
        referenceSegment.orientation,
      );
      const inherited = basisFromLateralReference(start, end, {
        x: referenceBasis.nx,
        y: referenceBasis.ny,
        z: referenceBasis.nz,
      });
      if (inherited) return inherited;
    }
  }
  return orientedSegmentBasis(run, start, end, orientation);
}

function addPlanBendProxy(group, run, nodeIndex, material, detailMaterial) {
  const info = planBendInfoAtNode(run, nodeIndex);
  if (!info) return;
  const incomingPoint = pointTowardPoint(info.node, info.previous, info.incomingCutbackM);
  const outgoingPoint = pointTowardPoint(info.node, info.next, info.outgoingCutbackM);
  const segment = segmentNearNode(run, nodeIndex, 'incoming') || segmentNearNode(run, nodeIndex, 'outgoing');
  const points = bendCurvePoints(incomingPoint, info.node, outgoingPoint);
  addAccessoryCurveRails(
    group,
    run,
    points,
    material,
    detailMaterial,
    'plan-bend-proxy',
    segment?.orientation || runOrientation(run),
    segment?.faceOffsetM || 0,
  );
}

function addRiserTurnProxy(group, run, nodeIndex, material, detailMaterial) {
  const info = riserTurnInfoAtNode(run, nodeIndex);
  if (!info) return;
  const incomingPoint = pointTowardPoint(info.node, info.previous, info.incomingCutbackM);
  const outgoingPoint = pointTowardPoint(info.node, info.next, info.outgoingCutbackM);
  const segment = riserTurnReferenceSegment(run, nodeIndex, info);
  const basisReference = segment ? segmentRenderBasis(run, segment, segment.startNode, segment.endNode) : null;
  const points = bendCurvePoints(incomingPoint, info.node, outgoingPoint);
  addAccessoryCurveRails(
    group,
    run,
    points,
    material,
    detailMaterial,
    'riser-proxy',
    segment?.orientation || runOrientation(run),
    segment?.faceOffsetM || 0,
    {
      basisReference,
      surfaceKind: 'riser-bend-surface',
      color: 0xbe123c,
      selected: run.id === state.activeRunId,
    },
  );
}

function addRiserSegmentProxy(group, run, segment, material, detailMaterial) {
  const line = addSourceLine(group, [segment.startNode, segment.endNode], material, 'riser-proxy');
  if (line) line.renderOrder = 27;
  const basis = segmentRenderBasis(run, segment);
  const corners = segmentCornerPoints(run, segment.startNode, segment.endNode, segment.orientation, segment.faceOffsetM, basis);
  if (!corners) return;
  addSourceLine(group, [corners.leftStartTop, corners.leftEndTop], material, 'accessory-side-rail');
  addSourceLine(group, [corners.rightStartTop, corners.rightEndTop], material, 'accessory-side-rail');
  addSourceLine(group, [corners.leftStartBottom, corners.leftEndBottom], detailMaterial, 'accessory-lower-edge');
  addSourceLine(group, [corners.rightStartBottom, corners.rightEndBottom], detailMaterial, 'accessory-lower-edge');
  [
    [corners.leftStartBottom, corners.rightStartBottom],
    [
      {
        x: (Number(corners.leftStartBottom.x || 0) + Number(corners.leftEndBottom.x || 0)) / 2,
        y: (Number(corners.leftStartBottom.y || 0) + Number(corners.leftEndBottom.y || 0)) / 2,
        z: (Number(corners.leftStartBottom.z || 0) + Number(corners.leftEndBottom.z || 0)) / 2,
      },
      {
        x: (Number(corners.rightStartBottom.x || 0) + Number(corners.rightEndBottom.x || 0)) / 2,
        y: (Number(corners.rightStartBottom.y || 0) + Number(corners.rightEndBottom.y || 0)) / 2,
        z: (Number(corners.rightStartBottom.z || 0) + Number(corners.rightEndBottom.z || 0)) / 2,
      },
    ],
    [corners.leftEndBottom, corners.rightEndBottom],
  ].forEach(points => {
    addSourceLine(group, points, detailMaterial, 'accessory-cross-member');
  });
}

function reducerPortCrossSection(item, port) {
  const run = runByKey(port?.run_key);
  if (!run) return null;
  const segment = runSegments(run).find(candidate => candidate.key === String(port?.segment_key || ''));
  if (!segment) return null;
  const cutback = Number(item.geometry_recipe?.straight_proxy_cutback?.each_port_m) || 0;
  const center = item.source_point_m || item.geometry_recipe?.center_point_m || null;
  const awayNode = port.role_at_node === 'incoming_to_node' ? segment.startNode : segment.endNode;
  const tangentPoint = pointTowardPoint(center, awayNode, cutback);
  const basis = segmentRenderBasis(run, segment, segment.startNode, segment.endNode);
  if (!basis) return null;
  const halfWidth = Math.max(Number(port.width_mm || 0) / 1000, runWidthM(run)) / 2;
  const depth = Math.max(Number(port.depth_mm || 0) / 1000, runDepthM(run));
  const offset = normalizedFaceOffsetM(port.face_offset_m ?? segment.faceOffsetM);
  return {
    run,
    segment,
    tangentPoint,
    leftBottom: sourceFrameOffsetPoint(tangentPoint, basis, offset + halfWidth, 0),
    rightBottom: sourceFrameOffsetPoint(tangentPoint, basis, offset - halfWidth, 0),
    leftTop: sourceFrameOffsetPoint(tangentPoint, basis, offset + halfWidth, depth),
    rightTop: sourceFrameOffsetPoint(tangentPoint, basis, offset - halfWidth, depth),
  };
}

function addReducerTaperProxy(group, item) {
  const ports = (item.geometry_recipe?.ports || [])
    .map(port => reducerPortCrossSection(item, port))
    .filter(Boolean);
  if (ports.length !== 2) return;
  const selected = ports.some(port => port.run.id === state.activeRunId);
  const color = selected ? 0xf97316 : serviceFor(ports[0].run.serviceClass).color;
  const positions = [];
  const colors = [];
  const faceColors = proxyFaceColors(color, selected);
  const [first, second] = ports;
  addProxyQuad(positions, colors, first.leftBottom, first.rightBottom, second.rightBottom, second.leftBottom, faceColors.bottom);
  addProxyQuad(positions, colors, first.leftBottom, second.leftBottom, second.leftTop, first.leftTop, faceColors.side);
  addProxyQuad(positions, colors, first.rightBottom, first.rightTop, second.rightTop, second.rightBottom, faceColors.side);
  if (positions.length >= 18) {
    const mesh = new runtime.THREE.Mesh(
      setGeometryPositions(new runtime.THREE.BufferGeometry(), positions, colors),
      proxyFaceMaterial(color, selected),
    );
    mesh.userData.racewayPreviewKind = 'reducer-taper-surface';
    mesh.userData.fittingKey = item.fitting_key || '';
    mesh.userData.faceCount = positions.length / 18;
    mesh.renderOrder = 21;
    group.add(mesh);
  }
  const railMaterial = previewMaterial(0x16a34a, selected ? 0.95 : 0.72);
  const detailMaterial = previewMaterial(0x15803d, selected ? 0.85 : 0.56);
  addSourceLine(group, [first.leftTop, second.leftTop], railMaterial, 'reducer-side-rail');
  addSourceLine(group, [first.rightTop, second.rightTop], railMaterial, 'reducer-side-rail');
  addSourceLine(group, [first.leftBottom, second.leftBottom], detailMaterial, 'reducer-lower-edge');
  addSourceLine(group, [first.rightBottom, second.rightBottom], detailMaterial, 'reducer-lower-edge');
  addSourceLine(group, [first.leftBottom, first.rightBottom], detailMaterial, 'reducer-cross-member');
  addSourceLine(group, [second.leftBottom, second.rightBottom], detailMaterial, 'reducer-cross-member');
}

function branchPortCrossSection(point, basis, widthM, depthM, faceOffsetM = 0) {
  const halfWidth = Math.max(Number(widthM) || 0, 0.05) / 2;
  const depth = Math.max(Number(depthM) || 0, 0.025);
  const offset = normalizedFaceOffsetM(faceOffsetM);
  return {
    leftBottom: sourceFrameOffsetPoint(point, basis, offset + halfWidth, 0),
    rightBottom: sourceFrameOffsetPoint(point, basis, offset - halfWidth, 0),
    leftTop: sourceFrameOffsetPoint(point, basis, offset + halfWidth, depth),
    rightTop: sourceFrameOffsetPoint(point, basis, offset - halfWidth, depth),
  };
}

function branchPortStub(item, port) {
  const run = runByKey(port?.run_key);
  if (!run) return null;
  const segment = runSegments(run).find(candidate => candidate.key === String(port?.segment_key || ''));
  if (!segment) return null;
  const center = item.source_point_m || item.geometry_recipe?.center_point_m || null;
  if (!center) return null;
  const rawCutback = Number(item.geometry_recipe?.straight_proxy_cutback?.default_each_port_m) || ACCESSORY_DEFAULT_RADIUS_M;
  const cutback = Math.min(rawCutback, Math.max(segment.lengthM * 0.45, 0.05));
  const awayNode = port.role_at_node === 'incoming_to_node' ? segment.startNode : segment.endNode;
  const tangentPoint = pointTowardPoint(center, awayNode, cutback);
  const basis = segmentRenderBasis(run, segment, segment.startNode, segment.endNode);
  if (!basis) return null;
  const widthM = Math.max(Number(port.width_mm || 0) / 1000, runWidthM(run));
  const depthM = Math.max(Number(port.depth_mm || 0) / 1000, runDepthM(run));
  const faceOffsetM = normalizedFaceOffsetM(port.face_offset_m ?? segment.faceOffsetM);
  return {
    run,
    segment,
    port,
    centerPoint: center,
    tangentPoint,
    center: branchPortCrossSection(center, basis, widthM, depthM, faceOffsetM),
    tangent: branchPortCrossSection(tangentPoint, basis, widthM, depthM, faceOffsetM),
  };
}

function addBranchNodeProxy(group, item) {
  const stubs = (item.ports || [])
    .map(port => branchPortStub(item, port))
    .filter(Boolean);
  if (stubs.length < 3) return;
  const selected = stubs.some(stub => stub.run.id === state.activeRunId);
  const color = selected ? 0xf97316 : (item.kind === 'cross' ? 0x7c3aed : 0x0ea5e9);
  const positions = [];
  const colors = [];
  const faceColors = proxyFaceColors(color, selected);
  stubs.forEach(stub => {
    addProxyQuad(
      positions,
      colors,
      stub.center.leftBottom,
      stub.center.rightBottom,
      stub.tangent.rightBottom,
      stub.tangent.leftBottom,
      faceColors.bottom,
    );
    addProxyQuad(
      positions,
      colors,
      stub.center.leftBottom,
      stub.tangent.leftBottom,
      stub.tangent.leftTop,
      stub.center.leftTop,
      faceColors.side,
    );
    addProxyQuad(
      positions,
      colors,
      stub.center.rightBottom,
      stub.center.rightTop,
      stub.tangent.rightTop,
      stub.tangent.rightBottom,
      faceColors.side,
    );
  });
  if (positions.length >= 18) {
    const mesh = new runtime.THREE.Mesh(
      setGeometryPositions(new runtime.THREE.BufferGeometry(), positions, colors),
      proxyFaceMaterial(color, selected),
    );
    mesh.userData.racewayPreviewKind = item.kind === 'cross' ? 'cross-node-surface' : 'tee-node-surface';
    mesh.userData.fittingKey = item.fitting_key || '';
    mesh.userData.branchIntentStatus = item.branch_intent?.status || '';
    mesh.userData.faceCount = positions.length / 18;
    mesh.renderOrder = 22;
    group.add(mesh);
  }
  const railMaterial = previewMaterial(color, selected ? 0.95 : 0.72);
  const detailMaterial = previewMaterial(item.kind === 'cross' ? 0x5b21b6 : 0x0369a1, selected ? 0.85 : 0.58);
  stubs.forEach(stub => {
    addSourceLine(group, [stub.center.leftTop, stub.tangent.leftTop], railMaterial, 'branch-side-rail');
    addSourceLine(group, [stub.center.rightTop, stub.tangent.rightTop], railMaterial, 'branch-side-rail');
    addSourceLine(group, [stub.center.leftBottom, stub.tangent.leftBottom], detailMaterial, 'branch-lower-edge');
    addSourceLine(group, [stub.center.rightBottom, stub.tangent.rightBottom], detailMaterial, 'branch-lower-edge');
    addSourceLine(group, [stub.tangent.leftBottom, stub.tangent.rightBottom], detailMaterial, 'branch-cross-member');
  });
  const centerPairs = [];
  stubs.forEach(stub => {
    centerPairs.push([stub.center.leftBottom, stub.center.rightBottom]);
  });
  centerPairs.slice(0, 4).forEach(points => {
    addSourceLine(group, points, detailMaterial, 'branch-cross-member');
  });
}

function renderFittingProxyBodies() {
  const items = [...reducerProxyItems(), ...branchProxyItems()];
  if (!items.length) return;
  const group = new runtime.THREE.Group();
  group.userData.racewayPreviewKind = 'fitting-proxy-bodies';
  items.forEach(item => {
    if (item.kind === 'reducer_candidate') addReducerTaperProxy(group, item);
    if (item.kind === 'tee' || item.kind === 'cross') addBranchNodeProxy(group, item);
  });
  if (group.children.length) layer.group.add(group);
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

function addSelectedSegmentHighlight(group, run, start, end) {
  const material = previewMaterial(0x2563eb, 0.98);
  const line = addSourceLine(group, [start, end], material, 'selected-segment-highlight');
  if (line) {
    line.userData.racewayRunId = run.id;
    line.renderOrder = 40;
  }
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
  state.selectedSegmentIndex = -1;
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
  const bottomEdgeMaterial = previewMaterial(0x0891b2, selected ? 0.82 : 0.54);
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
  runSegments(run).forEach(segment => {
    const trimmed = segmentTrimmedEndpoints(run, segment);
    const basis = segmentRenderBasis(run, segment, trimmed.start, trimmed.end);
    addSegmentPreview(group, run, trimmed.start, trimmed.end, material, detailMaterial, bottomEdgeMaterial, segment.orientation, segment.faceOffsetM, basis);
    if (segment.isRiser) {
      addRiserSegmentProxy(group, run, segment, previewMaterial(0xbe123c, selected ? 0.95 : 0.65), detailMaterial);
    }
    if (warningSegmentIsFocused(run, segment.segmentIndex)) {
      addWarningSegmentHighlight(group, run, segment.startNode, segment.endNode);
    } else if (selectedSegmentIsFocused(run, segment.segmentIndex)) {
      addSelectedSegmentHighlight(group, run, segment.startNode, segment.endNode);
    }
  });
  for (let index = 1; index < run.nodes.length - 1; index += 1) {
    addPlanBendProxy(group, run, index, previewMaterial(0xf97316, selected ? 0.95 : 0.65), detailMaterial);
    addRiserTurnProxy(group, run, index, previewMaterial(0xbe123c, selected ? 0.95 : 0.65), detailMaterial);
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
  renderFittingProxyBodies();
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
  state.selectedSegmentIndex = -1;
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
  const anchor = continuationAnchor(run, { allowDefaultLast: true });
  if (!anchor) {
    setStatus(`${run.tag}: select the first or last node before continuing. Mid-run branch insertion comes with tee/split support.`);
    renderPanel();
    return;
  }
  state.selectedNodeIndex = anchor.index;
  state.selectedSegmentIndex = -1;
  activateCanvasMode('draw');
  setStatus(`${run.tag}: continue from node ${anchor.index + 1}. Click structure or the working plane to extend.`);
  renderRaceway();
  renderPanel();
}

function addTypedSegment() {
  const run = activeRun();
  const anchor = continuationAnchor(run, { allowDefaultLast: true });
  const start = anchor?.node || null;
  const length = Number(state.segmentLengthM);
  const direction = segmentDirectionById();
  if (!run || !start) {
    setStatus(anchor === null && run?.nodes?.length
      ? 'Select the first or last node before typed segment entry. Mid-run branch insertion comes later.'
      : 'Add or select a raceway run with at least one node before typed segment entry.');
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
  if (anchor.mode === 'prepend') {
    run.nodes.unshift(point);
    state.selectedNodeIndex = 0;
  } else {
    run.nodes.push(point);
    state.selectedNodeIndex = run.nodes.length - 1;
  }
  state.selectedSegmentIndex = -1;
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
  state.selectedSegmentIndex = -1;
  setStatus('Raceway command cancelled.');
  renderRaceway();
  renderPanel();
}

function addNodeFromEvent(event) {
  const run = activeRun();
  const rawPoint = sourcePointFromEvent(event);
  const endpoint = continuationAnchor(run, { allowDefaultLast: true });
  const { point, adjusted } = orthoAdjustedPoint(run, rawPoint, endpoint?.node || null);
  if (!run || !point) {
    setStatus('No point found on the active elevation.');
    return;
  }
  if (endpoint === null && run.nodes.length) {
    setStatus(`${run.tag}: select the first or last node before continuing. Mid-run branch insertion comes with tee/split support.`);
    return;
  }
  pushUndo('Add node');
  const previousPoint = endpoint?.node || null;
  if (endpoint?.mode === 'prepend') {
    run.nodes.unshift(point);
    state.selectedNodeIndex = 0;
  } else {
    run.nodes.push(point);
    state.selectedNodeIndex = run.nodes.length - 1;
  }
  state.selectedSegmentIndex = -1;
  adoptWorkingElevationFromPoint(run, point);
  markRunDirty(run);
  if (adjusted) recordOrthoTelemetry(run, previousPoint, rawPoint, point);
  const anchor = anchorLabel(point.anchor);
  setStatus(anchor
    ? `${run.tag}: node ${state.selectedNodeIndex + 1} added at EL +${formatM(point.z)} and anchored to ${anchor}.`
    : `${run.tag}: node ${state.selectedNodeIndex + 1} added at EL +${formatM(point.z)}${adjusted ? ' with ortho lock.' : '.'}`);
  renderRaceway();
  renderPanel();
}

function interpolatedRacewayNode(startNode, endNode, ratio) {
  const t = Math.min(Math.max(Number(ratio) || 0, 0), 1);
  return {
    x: Number(startNode?.x || 0) + (Number(endNode?.x || 0) - Number(startNode?.x || 0)) * t,
    y: Number(startNode?.y || 0) + (Number(endNode?.y || 0) - Number(startNode?.y || 0)) * t,
    z: Number(startNode?.z || 0) + (Number(endNode?.z || 0) - Number(startNode?.z || 0)) * t,
    coordinate_frame: SOURCE_COORDINATE_FRAME,
    anchor: {},
  };
}

function splitSelectedSegment() {
  const run = activeRun();
  const segment = selectedSegment();
  if (!run || !segment) {
    setStatus('Select a segment before splitting it.');
    renderPanel();
    return false;
  }
  const percent = normalizedSegmentSplitPercent(state.segmentSplitPercent);
  const ratio = percent / 100;
  const oldIntentByIndex = segmentIntentSnapshot(run);
  const splitIndex = Number(segment.segmentIndex);
  const remappedIntentByIndex = new Map();
  oldIntentByIndex.forEach((intent, oldIndex) => {
    const cloned = cloneSegmentIntent(intent);
    if (!cloned) return;
    if (oldIndex < splitIndex) {
      remappedIntentByIndex.set(oldIndex, cloned);
    } else if (oldIndex === splitIndex) {
      remappedIntentByIndex.set(splitIndex, cloneSegmentIntent(cloned));
      remappedIntentByIndex.set(splitIndex + 1, cloneSegmentIntent(cloned));
    } else {
      remappedIntentByIndex.set(oldIndex + 1, cloned);
    }
  });
  const insertedNode = interpolatedRacewayNode(segment.startNode, segment.endNode, ratio);
  pushUndo('Split segment');
  run.nodes.splice(segment.endNodeIndex, 0, insertedNode);
  rewriteSegmentIntentOverrides(run, remappedIntentByIndex);
  state.segmentSplitPercent = percent;
  state.selectedNodeIndex = segment.endNodeIndex;
  state.selectedSegmentIndex = -1;
  state.warningFocus = null;
  adoptWorkingElevationFromPoint(run, insertedNode);
  markRunDirty(run);
  clearDerivedProjections();
  activateNodeSelectionMode(run);
  setStatus(`${run.tag}: segment S${splitIndex} split at ${percent}% into two editable segments. Save Draft to lock node UUIDs.`);
  renderRaceway();
  renderPanel({ forceInspector: true });
  return true;
}

function deleteSelectedNode() {
  const run = activeRun();
  if (!run || state.selectedNodeIndex < 0) return;
  const deleteIndex = state.selectedNodeIndex;
  const lastNodeIndex = run.nodes.length - 1;
  const oldIntentByIndex = segmentIntentSnapshot(run);
  const remappedIntentByIndex = new Map();
  let mergedIntentResult = { intent: null, conflict: false };
  if (deleteIndex === 0) {
    oldIntentByIndex.forEach((intent, oldIndex) => {
      const cloned = cloneSegmentIntent(intent);
      if (cloned && oldIndex > 1) remappedIntentByIndex.set(oldIndex - 1, cloned);
    });
  } else if (deleteIndex === lastNodeIndex) {
    oldIntentByIndex.forEach((intent, oldIndex) => {
      const cloned = cloneSegmentIntent(intent);
      if (cloned && oldIndex < deleteIndex) remappedIntentByIndex.set(oldIndex, cloned);
    });
  } else {
    mergedIntentResult = mergedSegmentIntent(
      oldIntentByIndex.get(deleteIndex),
      oldIntentByIndex.get(deleteIndex + 1),
      runOrientation(run).preset,
    );
    oldIntentByIndex.forEach((intent, oldIndex) => {
      const cloned = cloneSegmentIntent(intent);
      if (!cloned) return;
      if (oldIndex < deleteIndex) remappedIntentByIndex.set(oldIndex, cloned);
      if (oldIndex > deleteIndex + 1) remappedIntentByIndex.set(oldIndex - 1, cloned);
    });
    if (mergedIntentResult.intent) {
      remappedIntentByIndex.set(deleteIndex, mergedIntentResult.intent);
    }
  }
  pushUndo('Delete node');
  run.nodes.splice(deleteIndex, 1);
  rewriteSegmentIntentOverrides(run, remappedIntentByIndex);
  state.selectedNodeIndex = Math.min(deleteIndex, run.nodes.length - 1);
  state.selectedSegmentIndex = -1;
  markRunDirty(run);
  clearDerivedProjections();
  if (run.nodes.length) {
    activateNodeSelectionMode(run);
  } else {
    deactivateCanvasMode();
  }
  const mergeNote = mergedIntentResult.conflict
    ? ' Conflicting segment orientation/offset intent was dropped at the merged segment.'
    : mergedIntentResult.intent
      ? ' Matching segment intent carried to the merged segment.'
      : '';
  setStatus(`${run.tag}: node N${deleteIndex + 1} deleted.${mergeNote}`);
  renderRaceway();
  renderPanel();
}

function moveSelectedNodeFromEvent(event) {
  const run = activeRun();
  const point = sourcePointFromEvent(event);
  if (!run || state.selectedNodeIndex < 0 || !point) return;
  pushUndo('Move node');
  run.nodes[state.selectedNodeIndex] = point;
  state.selectedSegmentIndex = -1;
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

function layerWarningDetailsUrl() {
  return state.layerId ? `/raceway/layers/${encodeURIComponent(state.layerId)}/warnings/` : '';
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
    validateFittingProjectionContract(state.fittingProjection);
    state.fittingsLoaded = true;
    if (!options.quiet) recordReducerEdgeMatchProjectionTelemetry(state.fittingProjection, 'shown');
    if (!options.quiet) {
      const counts = state.fittingProjection?.counts || {};
      const byKind = counts.by_kind || {};
      setStatus(
        `Raceway fittings refreshed: ${counts.total || 0} item(s), `
        + `${byKind.reducer_candidate || 0} reducer candidate(s), ${counts.reducer_proxy_total || 0} reducer proxy.`
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
    renderRaceway();
    renderPanel();
  }
}

function reducerEdgeMatchCandidates(projection = state.fittingProjection) {
  const items = Array.isArray(projection?.items) ? projection.items : [];
  return items.filter(item => {
    if (
      item?.kind !== 'reducer_candidate'
      || !item?.requires_face_alignment
      || item?.face_alignment?.basis !== 'one_edge_matching'
    ) {
      return false;
    }
    const suggestion = reducerAlignmentSuggestion(item);
    return Array.isArray(suggestion.member_offsets) && suggestion.member_offsets.length;
  });
}

function reducerAlignmentSuggestion(candidate, handedness = state.reducerHandedness) {
  const selectedHandedness = normalizedReducerHandedness(handedness);
  const suggestions = candidate?.face_alignment?.suggestions_by_handedness || {};
  if (suggestions[selectedHandedness]) return suggestions[selectedHandedness];
  return {
    handedness: candidate?.face_alignment?.recommended_handedness || DEFAULT_REDUCER_HANDEDNESS,
    member_offsets: candidate?.face_alignment?.recommended_offsets || [],
  };
}

function reducerTransitionCandidates(projection = state.fittingProjection) {
  const items = Array.isArray(projection?.items) ? projection.items : [];
  return items.filter(item => item?.kind === 'reducer_candidate');
}

function reducerCandidateExclusionReasons(candidate) {
  const reasons = [];
  if (candidate?.kind !== 'reducer_candidate') reasons.push('not_reducer_candidate');
  if (!candidate?.requires_face_alignment) reasons.push('face_alignment_not_required');
  if (candidate?.face_alignment?.basis !== 'one_edge_matching') reasons.push('basis_not_one_edge_matching');
  const suggestion = reducerAlignmentSuggestion(candidate);
  if (!Array.isArray(suggestion.member_offsets) || !suggestion.member_offsets.length) {
    reasons.push('no_member_offsets_for_selected_handedness');
  }
  return reasons;
}

function logReducerCandidateDiagnostics(projection = state.fittingProjection) {
  const candidates = reducerTransitionCandidates(projection);
  if (!candidates.length || reducerEdgeMatchCandidates(projection).length) return;
  console.warn('Raceway reducer candidates produced no edge-match action.', candidates.map(candidate => ({
    fitting_key: candidate?.fitting_key || '',
    category: candidate?.category || '',
    status: candidate?.status || '',
    face_alignment_status: candidate?.face_alignment?.status || '',
    current_status: candidate?.face_alignment?.current_status || '',
    exclusion_reasons: reducerCandidateExclusionReasons(candidate),
  })));
}

function validateFittingProjectionContract(projection) {
  if (!projection) {
    console.warn('Raceway fitting projection missing from response.');
    return;
  }
  if (projection.projection !== EXPECTED_FITTING_PROJECTION) {
    console.warn(
      `Raceway fitting projection version mismatch: expected ${EXPECTED_FITTING_PROJECTION}, received ${projection.projection}.`
    );
  }
  if (!Array.isArray(projection.items)) {
    console.warn('Raceway fitting projection contract warning: items must be an array.');
  }
  if (!projection.counts || typeof projection.counts !== 'object') {
    console.warn('Raceway fitting projection contract warning: counts must be an object.');
  }
  reducerTransitionCandidates(projection).forEach(candidate => {
    if (!candidate.fitting_key) console.warn('Raceway reducer candidate missing fitting_key.', candidate);
    if (!candidate.category) console.warn('Raceway reducer candidate missing category.', candidate);
    if (!candidate.status) console.warn('Raceway reducer candidate missing status.', candidate);
    if (!candidate.face_alignment || typeof candidate.face_alignment !== 'object') {
      console.warn('Raceway reducer candidate missing face_alignment object.', candidate);
    } else if (candidate.face_alignment.basis === 'one_edge_matching') {
      const options = candidate.face_alignment.options || [];
      const suggestions = candidate.face_alignment.suggestions_by_handedness || {};
      if (!Array.isArray(options) || !options.length) {
        console.warn('Raceway reducer candidate one-edge alignment missing options.', candidate);
      }
      if (candidate.requires_face_alignment && !Object.keys(suggestions).length) {
        console.warn('Raceway reducer candidate one-edge alignment missing handedness suggestions.', candidate);
      }
    }
  });
  logReducerCandidateDiagnostics(projection);
}

function reducerCategorySummary(candidates) {
  const counts = new Map();
  candidates.forEach(candidate => {
    const category = String(candidate?.category || 'unknown_transition');
    counts.set(category, (counts.get(category) || 0) + 1);
  });
  return Array.from(counts.entries())
    .map(([category, count]) => `${category.replace(/_/g, ' ')} x${count}`)
    .join(', ');
}

function reducerNoEdgeMatchActionMessage(projection = state.fittingProjection) {
  const candidates = reducerTransitionCandidates(projection);
  if (!candidates.length) {
    return 'No reducer or transition candidates were found. Save connected unequal trays, then refresh fittings.';
  }
  const resolved = candidates.filter(item => item?.face_alignment?.status === 'offsets_match_recommended_edge').length;
  const serviceTransitions = candidates.filter(item => item?.category === 'service_transition').length;
  const insufficientContext = candidates.filter(
    item => item?.face_alignment?.current_status === 'insufficient_segment_context'
  ).length;
  const parts = [
    `No reducer edge-offset changes are available for ${candidates.length} candidate(s)`,
  ];
  const categories = reducerCategorySummary(candidates);
  if (categories) parts.push(`categories: ${categories}`);
  if (resolved) parts.push(`${resolved} already edge-aligned`);
  if (serviceTransitions) parts.push(`${serviceTransitions} service transition(s) do not need edge matching`);
  if (insufficientContext) parts.push(`${insufficientContext} need adjacent segment context`);
  parts.push(
    'Reducer body v0 renders saved same-family unequal-width left-edge matches; family, service, and depth transitions remain catalogue-validation placeholders.'
  );
  return `${parts.join('. ')}.`;
}

function collectReducerEdgeOffsetSuggestions(projection = state.fittingProjection) {
  const suggestions = new Map();
  const conflicts = [];
  reducerEdgeMatchCandidates(projection).forEach(candidate => {
    const alignmentSuggestion = reducerAlignmentSuggestion(candidate);
    (alignmentSuggestion.member_offsets || []).forEach(offset => {
      const runKey = String(offset?.run_key || '').trim();
      const segmentKey = String(offset?.segment_key || '').trim();
      const rawSuggestedFaceOffsetM = Number(offset?.suggested_face_offset_m);
      if (!runKey || !segmentKey || !Number.isFinite(rawSuggestedFaceOffsetM)) return;
      const suggestedFaceOffsetM = normalizedFaceOffsetM(rawSuggestedFaceOffsetM);
      const key = `${runKey}::${segmentKey}`;
      const previous = suggestions.get(key);
      if (previous && Math.abs(previous.suggestedFaceOffsetM - suggestedFaceOffsetM) >= SEGMENT_FACE_OFFSET_EPSILON_M) {
        conflicts.push({ key, previous, candidate, offset });
        return;
      }
      suggestions.set(key, {
        runKey,
        segmentKey,
        runTag: offset.run_tag || '',
        suggestedFaceOffsetM,
        fittingKey: candidate.fitting_key || '',
        handedness: alignmentSuggestion.handedness || state.reducerHandedness,
        candidate,
        offset,
      });
    });
  });
  return { suggestions: Array.from(suggestions.values()), conflicts };
}

async function applyReducerEdgeMatchSuggestions() {
  if (hasUnsavedSavableChanges()) {
    setStatus('Save Draft before applying reducer edge-match suggestions; fitting suggestions use the last saved graph.');
    renderPanel();
    return false;
  }
  let projection = state.fittingProjection;
  if (!state.fittingsLoaded || !projection) {
    projection = await loadFittingProjection({ quiet: true });
  }
  if (!projection) {
    setStatus('Unable to load reducer edge-match suggestions.');
    return false;
  }
  const { suggestions, conflicts } = collectReducerEdgeOffsetSuggestions(projection);
  if (!suggestions.length) {
    setStatus(reducerNoEdgeMatchActionMessage(projection));
    renderPanel();
    return false;
  }
  const pending = [];
  const missing = [];
  suggestions.forEach(suggestion => {
    const run = state.runs.find(item => String(item.key || '') === suggestion.runKey);
    if (!run) {
      missing.push(suggestion);
      return;
    }
    const segment = runSegments(run).find(item => item.key === suggestion.segmentKey);
    if (!segment) {
      missing.push(suggestion);
      return;
    }
    if (Math.abs(segmentFaceOffsetFor(run, segment.key) - suggestion.suggestedFaceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) {
      return;
    }
    pending.push({
      run,
      segment,
      suggestion,
      previousFaceOffsetM: segmentFaceOffsetFor(run, segment.key),
    });
  });
  if (!pending.length) {
    const extra = conflicts.length ? ` ${conflicts.length} conflicting suggestion(s) were skipped.` : '';
    setStatus(`Reducer edge-match offsets already match the current draft.${extra}`);
    renderPanel();
    return false;
  }
  pushUndo('Apply reducer edge-match offsets');
  pending.forEach(({ run, segment, suggestion, previousFaceOffsetM }) => {
    const overrides = ensureSegmentFaceOffsetOverrides(run);
    if (Math.abs(suggestion.suggestedFaceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) {
      delete overrides[segment.key];
    } else {
      overrides[segment.key] = {
        key: segment.key,
        start_node_key: String(segment.startNode.key || ''),
        end_node_key: String(segment.endNode.key || ''),
        face_offset_m: suggestion.suggestedFaceOffsetM,
      };
    }
    run.metadata = {
      ...(run.metadata || {}),
      segment_face_offset: segmentFaceOffsetPayloadFromOverrides(run, overrides),
    };
    markRunDirty(run);
    recordReducerEdgeMatchTelemetry(suggestion.candidate, suggestion.offset, 'accepted', {
      previous_face_offset_m: previousFaceOffsetM,
      applied_face_offset_m: suggestion.suggestedFaceOffsetM,
      handedness: suggestion.handedness,
      source: 'apply_edge_match_command',
    });
  });
  const first = pending[0];
  state.activeRunId = first.run.id;
  state.selectedNodeIndex = -1;
  state.selectedSegmentIndex = first.segment.segmentIndex;
  syncPaletteFromRun(first.run);
  clearFittingProjection();
  renderRaceway();
  renderPanel({ forceInspector: true });
  const conflictText = conflicts.length ? ` ${conflicts.length} conflicting suggestion(s) skipped.` : '';
  const missingText = missing.length ? ` ${missing.length} suggestion(s) no longer matched loaded segments.` : '';
  const handednessText = state.reducerHandedness.replace('_', ' ');
  setStatus(
    `Applied reducer edge-match offsets (${handednessText}) to ${pending.length} segment(s). Save Draft to persist, then refresh fittings.${conflictText}${missingText}`
  );
  return true;
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

function openWarningDetails() {
  const url = layerWarningDetailsUrl();
  if (!url) {
    setStatus('Save a raceway layer before opening warning details.');
    return;
  }
  window.open?.(url, 'racewayWarningDetails', 'width=1180,height=820,noopener');
  setStatus('Raceway warning details opened.');
}

function runFromServer(payload) {
  const serverFamily = payload.family || {};
  const serverSize = payload.size || {};
  const metadata = payload.metadata || {};
  const family = catalogFamilyById(payload.family_id);
  const sizeMatch = catalogSizeById(payload.size_id);
  const familyForSize = sizeMatch?.family || family;
  const size = sizeMatch || {};
  const run = {
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
    segmentOrientationOverrides: {},
    segmentFaceOffsetOverrides: {},
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
  run.segmentOrientationOverrides = ensureSegmentOrientationOverrides(run);
  run.segmentFaceOffsetOverrides = ensureSegmentFaceOffsetOverrides(run);
  return run;
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
      state.loadedServerRunIds = [];
      if (force || !state.runs.length) {
        state.runs = [];
        state.activeRunId = '';
        state.selectedNodeIndex = -1;
        state.selectedSegmentIndex = -1;
        clearHistory();
        renderRaceway();
      }
      setStatus('No saved raceway runs for this package yet.');
      return;
    }
    const runPayload = await apiFetch(urlWithQuery(layerMatch.runs_url, { include_nodes: 1 }));
    state.runs = (Array.isArray(runPayload.runs) ? runPayload.runs : []).map(runFromServer);
    rememberLoadedServerRuns();
    state.activeRunId = state.runs[0]?.id || '';
    state.selectedNodeIndex = -1;
    state.selectedSegmentIndex = -1;
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
    forgetLoadedServerRun(run.serverRunId);
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
      ...segmentIntentPayloads(run),
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

async function deleteServerRunsRemovedFromDraft(savableRuns) {
  const runIdsToDelete = serverRunIdsRemovedFromDraft(savableRuns);
  const deletedIds = [];
  for (const serverRunId of runIdsToDelete) {
    await apiFetch(`/raceway/runs/${serverRunId}/`, { method: 'DELETE' });
    deletedIds.push(serverRunId);
  }
  if (!deletedIds.length) return 0;
  const deletedIdSet = new Set(deletedIds);
  state.runs = state.runs.filter(run => !deletedIdSet.has(normalizedServerRunId(run.serverRunId)));
  state.loadedServerRunIds = state.loadedServerRunIds.filter(serverRunId => !deletedIdSet.has(serverRunId));
  if (!state.runs.some(run => run.id === state.activeRunId)) {
    state.activeRunId = state.runs[0]?.id || '';
  }
  state.selectedNodeIndex = -1;
  state.selectedSegmentIndex = -1;
  syncPaletteFromRun(activeRun());
  return deletedIds.length;
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
    const savableRuns = savableRunsForPersistence();
    const pendingDeleteCount = serverRunIdsRemovedFromDraft(savableRuns).length;
    if (!savableRuns.length && !pendingDeleteCount) {
      setStatus('Add at least two nodes before saving a raceway run.');
      return;
    }
    const persistentLayer = await ensureLayer(context);
    const deletedCount = await deleteServerRunsRemovedFromDraft(savableRuns);
    let savedCount = 0;
    for (const run of savableRuns) {
      try {
        const method = run.serverRunId ? 'PATCH' : 'POST';
        const url = run.serverRunId ? `/raceway/runs/${run.serverRunId}/` : persistentLayer.runs_url;
        const preSaveSegments = runSegments(run);
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
        migrateDraftSegmentOrientationOverrides(run, preSaveSegments);
        migrateDraftSegmentFaceOffsetOverrides(run, preSaveSegments);
        const finalSegmentOrientation = segmentOrientationPayload(run);
        const finalSegmentFaceOffset = segmentFaceOffsetPayload(run);
        if (finalSegmentOrientation.overrides.length || finalSegmentFaceOffset.overrides.length) {
          const patchedRun = await apiFetch(`/raceway/runs/${run.serverRunId}/`, {
            method: 'PATCH',
            body: runPayload(run, context),
          });
          run.metadata = patchedRun.run?.metadata || run.metadata || {};
          run.orientation = normalizedOrientation(run.metadata.orientation);
          run.segmentOrientationOverrides = {};
          run.segmentFaceOffsetOverrides = {};
          ensureSegmentOrientationOverrides(run);
          ensureSegmentFaceOffsetOverrides(run);
        }
        run.dirty = false;
        savedCount += 1;
      } catch (error) {
        throw new Error(`${run.tag || 'Raceway run'}: ${error.message || 'Unable to save this run.'}`);
      }
    }
    state.persistenceLoaded = true;
    state.persistenceReady = true;
    state.contextKey = contextKey(context);
    rememberLoadedServerRuns();
    clearHistory();
    await loadGraphProjection({ quiet: true });
    if (state.scheduleLoaded) await loadScheduleProjection({ quiet: true });
    if (state.fittingsLoaded) await loadFittingProjection({ quiet: true });
    recordVisibleWarningTelemetry('unresolved_at_save', { actionDetail: { trigger: 'save' } });
    flushTelemetryEvents();
    const deleteText = deletedCount ? `; ${deletedCount} removed from server` : '';
    setStatus(`${savedCount} raceway run(s) saved to server${deleteText}.`);
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
    .raceway-command-hint { margin: -4px 0 8px; color: #92400e; font-size: 11px; line-height: 1.35; }
    .raceway-command-hint[hidden] { display: none; }
    .raceway-run-list, .raceway-node-list, .raceway-segment-list { display: grid; gap: 6px; margin-top: 8px; }
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
  const segment = selectedSegment();
  if (segment) return segmentOrientationOptionsHtml(segment);
  return orientationPresets.map(preset => `<option value="${escapeHtml(preset.id)}"${preset.id === state.orientationPreset ? ' selected' : ''}>${escapeHtml(preset.label)}</option>`).join('');
}

function orientationSelectValue() {
  const segment = selectedSegment();
  return segment?.orientationOverride
    ? segment.orientation.preset
    : (segment ? SEGMENT_ORIENTATION_INHERIT : state.orientationPreset);
}

function orientationSelectTitle() {
  const segment = selectedSegment();
  if (!segment) return 'Run orientation. Select a segment to edit one segment override from this control.';
  return `Segment S${segment.segmentIndex} orientation. Choose Run default to remove the segment override.`;
}

function segmentOrientationOptionsHtml(segment) {
  const run = activeRun();
  const selectedValue = segment?.orientationOverride
    ? segment.orientation.preset
    : SEGMENT_ORIENTATION_INHERIT;
  const runDefaultLabel = run ? `Run default (${orientationLabel(run)})` : 'Run default';
  return [
    `<option value="${SEGMENT_ORIENTATION_INHERIT}"${selectedValue === SEGMENT_ORIENTATION_INHERIT ? ' selected' : ''}>${escapeHtml(runDefaultLabel)}</option>`,
    ...orientationPresets.map(preset => `<option value="${escapeHtml(preset.id)}"${preset.id === selectedValue ? ' selected' : ''}>${escapeHtml(preset.label)}</option>`),
  ].join('');
}

function segmentDirectionOptionsHtml() {
  return segmentDirections.map(direction => `<option value="${escapeHtml(direction.id)}"${direction.id === state.segmentDirection ? ' selected' : ''}>${escapeHtml(direction.label)}</option>`).join('');
}

function reducerHandednessOptionsHtml() {
  return reducerHandednessOptions
    .map(option => `<option value="${escapeHtml(option.id)}"${option.id === state.reducerHandedness ? ' selected' : ''}>${escapeHtml(option.label)}</option>`)
    .join('');
}

function segmentIntentText(segment) {
  if (!segment) return '';
  const parts = [segment.orientationOverride ? 'segment orientation' : 'run orientation'];
  if (segment.faceOffsetOverride) parts.push(`offset ${formatM(segment.faceOffsetM)} m`);
  return parts.join(' | ');
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

function segmentRowsHtml() {
  const run = activeRun();
  const segments = runSegments(run);
  if (!segments.length) return '<div class="meta">No segments</div>';
  return segments.map(segment => {
    const kind = segment.isRiser ? 'riser' : 'straight';
    const identityText = segment.keyStatus === 'saved' ? 'stable key' : 'draft key';
    const title = `Select segment ${segment.segmentIndex}: ${segment.keyLabel}`;
    return `
      <button type="button" class="raceway-row ${segment.segmentIndex === state.selectedSegmentIndex ? 'raceway-row-active' : ''}" data-raceway-action="select-segment" data-segment-index="${segment.segmentIndex}" title="${escapeHtml(title)}">
        <strong>S${segment.segmentIndex}</strong> N${segment.startNodeIndex + 1}->N${segment.endNodeIndex + 1} | ${formatM(segment.lengthM)} m | ${kind}<br>
        ${escapeHtml(segment.orientation.label)} | ${escapeHtml(segmentIntentText(segment))} | ${identityText}
      </button>
    `;
  }).join('');
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
  if (warning?.code === 'raceway.warning.face_offset_step_at_node') {
    return warning.message || 'Adjacent raceway segments have different face offsets at a shared node.';
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
  const fittingCounts = schedule.fitting_placeholders?.counts || {};
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
      ${totals.plan_bend_count || 0} bend(s) | ${totals.riser_count || 0} riser(s) | ${fittingCounts.tee_total || 0} tee(s) | ${fittingCounts.cross_total || 0} cross(es)<br>
      ${totals.support_placeholders || 0} support placeholder(s) | ${fittingCounts.branch_accessory_unresolved_total || 0} branch fitting(s) projection-only
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
      ${counts.total || 0} item(s) | ${counts.synthetic_proxy_total || 0} synthetic proxy | ${byKind.plan_bend || 0} bend(s) | ${byKind.riser || 0} riser(s)<br>
      ${byKind.tee || 0} tee(s) | ${byKind.cross || 0} cross(es) | ${byKind.reducer_candidate || 0} reducer candidate(s) | ${counts.reducer_proxy_total || 0} reducer proxy<br>
      ${counts.requires_face_alignment || 0} need face alignment | ${counts.requires_catalogue_validation || 0} need catalogue validation | ${counts.non_standard_plan_bends || 0} non-standard bend(s)<br>
      ${counts.one_edge_alignment_candidates || 0} edge-match candidate(s) | ${counts.face_offset_steps || 0} offset step(s) | ${counts.face_alignment_resolved_by_offset || 0} offset-resolved<br>
      ${graph.junction_node_count || 0} junction node(s) | ${graph.branch_node_count || 0} branch node(s)
      ${categoryRows}
      ${(projection.assumptions || []).length ? `<div class="meta">${projection.assumptions.length} fitting assumption(s) in JSON output.</div>` : ''}
    </div>
  `;
}

function inspectorHtml() {
  const node = selectedNode();
  const segment = selectedSegment();
  if (!node && segment) {
    const kind = segment.isRiser ? 'riser' : 'straight';
    return `
      <div class="meta">
        Segment S${segment.segmentIndex}: N${segment.startNodeIndex + 1}->N${segment.endNodeIndex + 1}<br>
        ${formatM(segment.lengthM)} m | ${kind} | ${escapeHtml(segment.orientation.label)} | ${escapeHtml(segmentIntentText(segment))}<br>
        ${segment.keyStatus === 'saved' ? 'Stable identity from node UUID pair' : 'Draft identity; save once to lock node UUIDs'}
      </div>
      ${localWarningsHtml(activeRun())}
    `;
  }
  if (!node) return `<div class="meta">Select a node or segment</div>${localWarningsHtml(activeRun())}`;
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
    <div id="racewayCommandHint" class="raceway-command-hint" hidden></div>
    <div class="raceway-tool-grid">
      <label>Family<select id="racewayFamilySelect">${familyOptionsHtml()}</select></label>
      <label>Size<select id="racewaySizeSelect">${sizeOptionsHtml()}</select></label>
      <label>Service<select id="racewayServiceSelect">${serviceOptionsHtml()}</select></label>
      <label>Orientation<select id="racewayOrientationSelect" title="${escapeHtml(orientationSelectTitle())}">${orientationOptionsHtml()}</select></label>
      <label>EL m<input id="racewayElevationInput" type="number" step="0.001" value="${formatM(state.elevationM)}"></label>
    </div>
    <div class="raceway-aid-grid">
      <label class="raceway-check" title="${escapeHtml(actionTooltip('toggle-ortho'))}"><input id="racewayOrthoInput" type="checkbox" title="${escapeHtml(actionTooltip('toggle-ortho'))}"${state.orthoMode ? ' checked' : ''}> Ortho</label>
      <label>Direction<select id="racewaySegmentDirectionSelect">${segmentDirectionOptionsHtml()}</select></label>
      <label>Length m<input id="racewaySegmentLengthInput" type="number" min="0.001" step="0.001" value="${formatM(state.segmentLengthM)}"></label>
      <label>Offset m<input id="racewaySegmentFaceOffsetInput" type="number" step="0.001" value="0.000" title="Select a segment to shift its tray faces left/right from the route centerline."></label>
      <label>Split %<input id="racewaySegmentSplitInput" type="number" min="1" max="99" step="1" value="${state.segmentSplitPercent}" title="Select a segment and split it at this percentage from its start node."></label>
      <label>Radius m<input id="racewayAccessoryRadiusInput" type="number" min="${ACCESSORY_RADIUS_MIN_M}" max="${ACCESSORY_RADIUS_MAX_M}" step="0.050" value="${formatM(state.accessoryRadiusM)}" title="Synthetic bend/riser proxy radius. Catalogue or project preference can override later."></label>
      <label>Reducer side<select id="racewayReducerHandednessSelect" title="Edge used by Apply Edge Match for unequal-width reducer candidates. Left/right are relative to each segment direction.">${reducerHandednessOptionsHtml()}</select></label>
      <button type="button" data-raceway-action="add-segment" title="${escapeHtml(actionTooltip('add-segment'))}">Add Segment</button>
      <button type="button" data-raceway-action="split-segment" title="${escapeHtml(actionTooltip('split-segment'))}">Split Segment</button>
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
      <button type="button" data-raceway-action="apply-reducer-offsets" title="${escapeHtml(actionTooltip('apply-reducer-offsets'))}">Apply Edge Match</button>
      <button type="button" data-raceway-action="open-warning-details" title="${escapeHtml(actionTooltip('open-warning-details'))}">Warnings</button>
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
    <div id="racewaySegmentList" class="raceway-segment-list"></div>
  `;
  layerPanel.parentNode.insertBefore(panel, layerPanel);
  statusEl = panel.querySelector('#racewayToolStatus');
  commandHintEl = panel.querySelector('#racewayCommandHint');
  summaryEl = panel.querySelector('#racewaySummary');
  graphWarningsEl = panel.querySelector('#racewayGraphWarnings');
  scheduleSummaryEl = panel.querySelector('#racewayScheduleSummary');
  fittingSummaryEl = panel.querySelector('#racewayFittingSummary');
  warningBadgeEl = panel.querySelector('#racewayWarningBadge');
  runListEl = panel.querySelector('#racewayRunList');
  nodeListEl = panel.querySelector('#racewayNodeList');
  segmentListEl = panel.querySelector('#racewaySegmentList');
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
    button.dataset.disabledReason = disabled ? title : '';
    button.title = actionTooltip(action, disabled ? title : '');
  });
}

function setCommandHint(message = '') {
  if (!commandHintEl) return;
  commandHintEl.hidden = !message;
  commandHintEl.textContent = message;
}

function disabledActionHint(action, reason) {
  const label = actionLabels[action] || 'Raceway command';
  return reason ? `${label} unavailable: ${reason}` : '';
}

function commandState(disabled, reason = '') {
  return {
    disabled: Boolean(disabled),
    reason: disabled ? reason : '',
  };
}

function computeRacewayCommandStates(snapshot = {}) {
  const layerId = snapshot.layerId || null;
  const persistenceLoading = Boolean(snapshot.persistenceLoading);
  const fittingsLoading = Boolean(snapshot.fittingsLoading);
  const graphLoading = Boolean(snapshot.graphLoading);
  const scheduleLoading = Boolean(snapshot.scheduleLoading);
  const edgeMatchCandidateCount = Number(snapshot.edgeMatchCandidateCount || 0);
  const reducerCandidateCount = Number(snapshot.reducerCandidateCount || 0);
  const splitPercent = Number(snapshot.splitPercent || 0);
  const segmentLengthM = Number(snapshot.segmentLengthM || 0);
  const hasUnsavedSavableChanges = Boolean(snapshot.hasUnsavedSavableChanges);
  const fittingsLoaded = Boolean(snapshot.fittingsLoaded);
  const edgeMatchDisabled = persistenceLoading
    || fittingsLoading
    || !layerId
    || hasUnsavedSavableChanges
    || (fittingsLoaded && edgeMatchCandidateCount <= 0 && reducerCandidateCount <= 0);
  let edgeMatchReason = '';
  if (!layerId) edgeMatchReason = 'Save a raceway layer before applying reducer edge-match suggestions.';
  else if (persistenceLoading || fittingsLoading) edgeMatchReason = 'Raceway persistence or fittings are busy.';
  else if (hasUnsavedSavableChanges) edgeMatchReason = 'Save Draft before applying reducer suggestions from the saved fitting projection.';
  else if (fittingsLoaded && edgeMatchCandidateCount <= 0 && reducerCandidateCount <= 0) edgeMatchReason = 'Refresh fittings after creating unresolved unequal-size reducer candidates.';
  const states = {
    start: commandState(!(Number(snapshot.catalogCount || 0) > 0), 'Raceway catalogue is still loading.'),
    'continue-run': commandState(!snapshot.hasRun, 'Select a run before continuing it.'),
    finish: commandState(!snapshot.hasRun || Number(snapshot.runNodeCount || 0) < 2, 'Add at least two nodes before finishing.'),
    undo: commandState(!(Number(snapshot.undoCount || 0) > 0), 'Nothing to undo.'),
    redo: commandState(!(Number(snapshot.redoCount || 0) > 0), 'Nothing to redo.'),
    cancel: commandState(!snapshot.hasRun && snapshot.mode === 'idle', 'No active raceway command.'),
    'select-node-mode': commandState(!snapshot.hasRun, 'Select a run before selecting nodes on canvas.'),
    'move-node': commandState(!snapshot.hasNode, 'Select a node before moving it.'),
    'delete-node': commandState(!snapshot.hasNode, 'Select a node before deleting it.'),
    'connect-node': commandState(!snapshot.canConnectEndpoint, 'Select the first or last node of a run before connecting it.'),
    'anchor-node': commandState(!snapshot.hasRun, 'Start or select a run before anchoring.'),
    'clear-anchor': commandState(!snapshot.hasAnchoredNode, 'Select an anchored node first.'),
    save: commandState(
      persistenceLoading || (!Number(snapshot.savableRunCount || 0) && !Number(snapshot.pendingDraftDeleteCount || 0)),
      'Add at least one two-node run or remove a saved run before saving.'
    ),
    reload: commandState(persistenceLoading, persistenceLoading ? 'Raceway persistence is busy.' : ''),
    'refresh-graph': commandState(
      persistenceLoading || graphLoading || !layerId,
      layerId ? 'Raceway persistence or graph refresh is busy.' : 'Save a raceway layer before refreshing graph warnings.'
    ),
    'refresh-schedule': commandState(
      persistenceLoading || scheduleLoading || !layerId,
      layerId ? 'Raceway persistence or schedule refresh is busy.' : 'Save a raceway layer before refreshing the schedule.'
    ),
    'refresh-fittings': commandState(
      persistenceLoading || fittingsLoading || !layerId,
      layerId ? 'Raceway persistence or fittings refresh is busy.' : 'Save a raceway layer before refreshing fittings.'
    ),
    'apply-reducer-offsets': commandState(edgeMatchDisabled, edgeMatchReason),
    'open-warning-details': commandState(
      persistenceLoading || !layerId,
      layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before opening warning details.'
    ),
    'open-schedule-csv': commandState(
      persistenceLoading || !layerId,
      layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before downloading CSV.'
    ),
    'delete-run': commandState(persistenceLoading || !snapshot.hasRun, 'Select a run before deleting it.'),
    'add-segment': commandState(
      !Number(snapshot.runNodeCount || 0) || !(segmentLengthM > 0),
      'Add at least one node and enter a positive segment length.'
    ),
    'split-segment': commandState(
      !snapshot.hasSelectedSegment || splitPercent <= 0 || splitPercent >= 100,
      'Select a segment and enter a split percentage between 1 and 99.'
    ),
    'toggle-surfaces': commandState(false),
  };
  return states;
}

function updateActionStates(run) {
  const node = selectedNode();
  const savableRuns = savableRunsForPersistence();
  const pendingDraftDeleteCount = serverRunIdsRemovedFromDraft(savableRuns).length;
  const edgeMatchCandidateCount = reducerEdgeMatchCandidates().length;
  const reducerCandidateCount = reducerTransitionCandidates().length;
  const segment = selectedSegment();
  const commandStates = computeRacewayCommandStates({
    catalogCount: catalog.length,
    hasRun: Boolean(run),
    runNodeCount: run?.nodes?.length || 0,
    hasNode: Boolean(node),
    hasAnchoredNode: Boolean(node && anchorLabel(node.anchor)),
    canConnectEndpoint: canConnectSelectedEndpoint(run),
    mode: state.mode,
    undoCount: state.undoStack.length,
    redoCount: state.redoStack.length,
    savableRunCount: savableRuns.length,
    pendingDraftDeleteCount,
    persistenceLoading: state.persistenceLoading,
    graphLoading: state.graphLoading,
    scheduleLoading: state.scheduleLoading,
    fittingsLoading: state.fittingsLoading,
    fittingsLoaded: state.fittingsLoaded,
    layerId: state.layerId,
    hasUnsavedSavableChanges: hasUnsavedSavableChanges(),
    edgeMatchCandidateCount,
    reducerCandidateCount,
    hasSelectedSegment: Boolean(segment),
    splitPercent: normalizedSegmentSplitPercent(state.segmentSplitPercent),
    segmentLengthM: state.segmentLengthM,
  });
  Object.entries(commandStates).forEach(([action, status]) => {
    setActionState(action, status.disabled, status.reason);
  });
  const edgeMatchState = commandStates['apply-reducer-offsets'];
  setCommandHint(
    edgeMatchState?.disabled && edgeMatchState.reason
      ? disabledActionHint('apply-reducer-offsets', edgeMatchState.reason)
      : ''
  );
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
  const segmentFaceOffsetInput = panel.querySelector('#racewaySegmentFaceOffsetInput');
  const segmentSplitInput = panel.querySelector('#racewaySegmentSplitInput');
  const accessoryRadiusInput = panel.querySelector('#racewayAccessoryRadiusInput');
  const reducerHandednessSelect = panel.querySelector('#racewayReducerHandednessSelect');
  const segment = selectedSegment();
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
    orientationSelect.value = orientationSelectValue();
    orientationSelect.title = orientationSelectTitle();
  } else if (orientationSelect) {
    orientationSelect.title = orientationSelectTitle();
  }
  if (orthoInput && orthoInput !== document.activeElement) orthoInput.checked = Boolean(state.orthoMode);
  if (surfaceToggleBtn) {
    surfaceToggleBtn.textContent = state.showProxyFaces ? 'Surface On' : 'Wire Only';
    surfaceToggleBtn.setAttribute('aria-pressed', state.showProxyFaces ? 'true' : 'false');
  }
  if (segmentDirectionSelect && segmentDirectionSelect !== document.activeElement) segmentDirectionSelect.value = state.segmentDirection;
  if (segmentLengthInput && segmentLengthInput !== document.activeElement) segmentLengthInput.value = formatM(state.segmentLengthM);
  if (accessoryRadiusInput && accessoryRadiusInput !== document.activeElement) {
    accessoryRadiusInput.value = formatM(state.accessoryRadiusM);
  }
  if (reducerHandednessSelect && reducerHandednessSelect !== document.activeElement) {
    reducerHandednessSelect.value = state.reducerHandedness;
  }
  if (segmentSplitInput) {
    segmentSplitInput.disabled = !segment;
    segmentSplitInput.title = segment
      ? `Split segment S${segment.segmentIndex} at this percentage from N${segment.startNodeIndex + 1}.`
      : 'Select a segment before splitting it.';
    if (segmentSplitInput !== document.activeElement) {
      segmentSplitInput.value = String(normalizedSegmentSplitPercent(state.segmentSplitPercent));
    }
  }
  if (segmentFaceOffsetInput) {
    segmentFaceOffsetInput.disabled = !segment;
    segmentFaceOffsetInput.title = segment
      ? `Segment S${segment.segmentIndex} face offset in meters. Positive shifts toward the segment left edge; zero follows the centerline.`
      : 'Select a segment to edit its tray face offset.';
    if (segmentFaceOffsetInput !== document.activeElement) {
      segmentFaceOffsetInput.value = formatM(segment?.faceOffsetM || 0);
    }
  }
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
  if (segmentListEl) segmentListEl.innerHTML = segmentRowsHtml();
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
  state.selectedSegmentIndex = Number.isInteger(segmentIndex) ? segmentIndex : -1;
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

function selectSegment(index) {
  const run = activeRun();
  const segmentIndex = Number(index);
  const segment = runSegments(run).find(item => item.segmentIndex === segmentIndex);
  if (!run || !segment) {
    setStatus('Select an active run segment.');
    return false;
  }
  state.selectedSegmentIndex = segment.segmentIndex;
  state.selectedNodeIndex = -1;
  state.warningFocus = null;
  activateNodeSelectionMode(run);
  const identityText = segment.keyStatus === 'saved' ? 'stable segment identity' : 'draft segment identity until saved';
  setStatus(`${run.tag}: segment S${segment.segmentIndex} selected (${formatM(segment.lengthM)} m, ${segment.isRiser ? 'riser' : 'straight'}, ${identityText}).`);
  renderRaceway();
  renderPanel({ forceInspector: true });
  return true;
}

function changeSelectedSegmentOrientation(value) {
  const run = activeRun();
  const segment = selectedSegment();
  if (!run || !segment) {
    setStatus('Select a raceway segment before changing segment orientation.');
    return false;
  }
  const preset = value === SEGMENT_ORIENTATION_INHERIT
    ? null
    : orientationPresets.find(item => item.id === String(value || ''));
  if (value !== SEGMENT_ORIENTATION_INHERIT && !preset) {
    setStatus('Unsupported segment orientation preset.');
    return false;
  }
  const overrides = ensureSegmentOrientationOverrides(run);
  pushUndo('Change segment orientation');
  if (value === SEGMENT_ORIENTATION_INHERIT) {
    delete overrides[segment.key];
    setStatus(`${run.tag}: segment S${segment.segmentIndex} now follows the run orientation. Save Draft to persist.`);
  } else {
    const startNodeKey = String(segment.startNode.key || '');
    const endNodeKey = String(segment.endNode.key || '');
    overrides[segment.key] = {
      key: segment.key,
      start_node_key: startNodeKey,
      end_node_key: endNodeKey,
      orientation: normalizedOrientation(preset.id),
    };
    setStatus(`${run.tag}: segment S${segment.segmentIndex} orientation set to ${preset.label}. Save Draft to persist.`);
  }
  run.metadata = {
    ...(run.metadata || {}),
    segment_orientation: segmentOrientationPayloadFromOverrides(run, overrides),
  };
  markRunDirty(run);
  renderRaceway();
  renderPanel({ forceInspector: true });
  return true;
}

function changeSelectedSegmentFaceOffset(value, options = {}) {
  const run = activeRun();
  const segment = selectedSegment();
  if (!run || !segment) {
    setStatus('Select a raceway segment before changing face offset.');
    return false;
  }
  const faceOffsetM = normalizedFaceOffsetM(value);
  const overrides = ensureSegmentFaceOffsetOverrides(run);
  if (options.pushHistory !== false) pushUndo('Change segment face offset');
  if (Math.abs(faceOffsetM) < SEGMENT_FACE_OFFSET_EPSILON_M) {
    delete overrides[segment.key];
    setStatus(`${run.tag}: segment S${segment.segmentIndex} face offset cleared. Save Draft to persist.`);
  } else {
    overrides[segment.key] = {
      key: segment.key,
      start_node_key: String(segment.startNode.key || ''),
      end_node_key: String(segment.endNode.key || ''),
      face_offset_m: faceOffsetM,
    };
    setStatus(`${run.tag}: segment S${segment.segmentIndex} face offset set to ${formatM(faceOffsetM)} m. Save Draft to persist.`);
  }
  run.metadata = {
    ...(run.metadata || {}),
    segment_face_offset: segmentFaceOffsetPayloadFromOverrides(run, overrides),
  };
  markRunDirty(run);
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
  if (action === 'apply-reducer-offsets') applyReducerEdgeMatchSuggestions();
  if (action === 'open-warning-details') openWarningDetails();
  if (action === 'open-schedule-csv') openScheduleCsv();
  if (action === 'delete-run') deleteActiveRun();
  if (action === 'add-segment') addTypedSegment();
  if (action === 'split-segment') splitSelectedSegment();
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
    state.selectedSegmentIndex = -1;
    state.warningFocus = null;
    syncPaletteFromRun(activeRun());
    activateNodeSelectionMode(activeRun());
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-node') {
    state.selectedNodeIndex = Number(button?.dataset.nodeIndex);
    state.selectedSegmentIndex = -1;
    state.warningFocus = null;
    activateNodeSelectionMode(activeRun());
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-segment') {
    selectSegment(button?.dataset.segmentIndex);
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
    setStatus(button.dataset.disabledReason || button.title || 'Raceway command unavailable.');
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
    if (selectedSegment()) {
      changeSelectedSegmentOrientation(target.value);
      return;
    }
    const preset = orientationPresetFor(target.value);
    if (run) {
      pushUndo('Change raceway orientation');
      run.orientation = normalizedOrientation(preset.id);
      run.metadata = {
        ...(run.metadata || {}),
        orientation: run.orientation,
        segment_orientation: segmentOrientationPayload(run),
      };
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
  if (target.id === 'racewaySegmentSplitInput') {
    state.segmentSplitPercent = normalizedSegmentSplitPercent(target.value);
  }
  if (target.id === 'racewayAccessoryRadiusInput') {
    state.accessoryRadiusM = normalizedAccessoryRadiusM(target.value);
    setStatus(`Synthetic accessory proxy radius set to ${formatM(state.accessoryRadiusM)} m.`);
  }
  if (target.id === 'racewayReducerHandednessSelect') {
    state.reducerHandedness = normalizedReducerHandedness(target.value);
    const label = reducerHandednessOptions.find(option => option.id === state.reducerHandedness)?.label || 'Left Edge';
    setStatus(`Reducer edge-match side set to ${label}. Apply Edge Match uses this side for unresolved reducer candidates.`);
  }
  if (target.id === 'racewaySegmentFaceOffsetInput') {
    const value = Number(target.value);
    if (Number.isFinite(value)) changeSelectedSegmentFaceOffset(value, { pushHistory: false });
    return;
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
  if (event.target.id === 'racewaySegmentSplitInput') {
    state.segmentSplitPercent = normalizedSegmentSplitPercent(event.target.value);
    renderPanel();
    return;
  }
  if (event.target.id === 'racewayAccessoryRadiusInput') {
    state.accessoryRadiusM = normalizedAccessoryRadiusM(event.target.value);
    renderRaceway();
    renderPanel();
    return;
  }
  if (event.target.id === 'racewaySegmentFaceOffsetInput') {
    const value = Number(event.target.value);
    if (!Number.isFinite(value)) return;
    if (event.target.dataset.racewayHistoryArmed !== '1') {
      pushUndo('Edit segment face offset');
      event.target.dataset.racewayHistoryArmed = '1';
    }
    changeSelectedSegmentFaceOffset(value, { pushHistory: false });
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
  if (event.target.id === 'racewaySegmentFaceOffsetInput') {
    delete event.target.dataset.racewayHistoryArmed;
  }
  if (event.target.id === 'racewaySegmentSplitInput') {
    state.segmentSplitPercent = normalizedSegmentSplitPercent(event.target.value);
    event.target.value = String(state.segmentSplitPercent);
  }
  if (event.target.id === 'racewayAccessoryRadiusInput') {
    state.accessoryRadiusM = normalizedAccessoryRadiusM(event.target.value);
    event.target.value = formatM(state.accessoryRadiusM);
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
  if (key === 'w' && event.shiftKey) return 'open-warning-details';
  if (key === 'x' && event.shiftKey) return 'split-segment';
  if (key === 'r' && !event.shiftKey) return 'reload';
  if (key === 'g' && !event.shiftKey) return 'refresh-graph';
  if (key === 't') return event.shiftKey ? 'apply-reducer-offsets' : 'refresh-fittings';
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
    || action === 'apply-reducer-offsets'
    || action === 'open-warning-details'
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
    if (event.target.closest?.('#racewaySegmentSplitInput')) {
      event.preventDefault();
      triggerRacewayAction('split-segment');
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
    rememberLoadedServerRuns(state.runs, { merge: true });
    state.activeRunId = state.runs[0]?.id || '';
    state.selectedNodeIndex = -1;
    state.selectedSegmentIndex = -1;
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
  computeRacewayCommandStates,
};
