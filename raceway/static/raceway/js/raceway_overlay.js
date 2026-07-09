const RACEWAY_LAYER_ID = 'raceway-overlay';
const RACEWAY_INTERACTION_ID = 'raceway-centerline-authoring';

const catalog = [
  {
    id: 'LADDER-HDG',
    label: 'Ladder HDG',
    sizes: [
      { id: 'LADDER-HDG-300x100', label: '300 x 100 mm', widthMm: 300, depthMm: 100 },
      { id: 'LADDER-HDG-450x100', label: '450 x 100 mm', widthMm: 450, depthMm: 100 },
      { id: 'LADDER-HDG-600x150', label: '600 x 150 mm', widthMm: 600, depthMm: 150 },
    ],
  },
  {
    id: 'PERF-HDG',
    label: 'Perforated HDG',
    sizes: [
      { id: 'PERF-HDG-150x50', label: '150 x 50 mm', widthMm: 150, depthMm: 50 },
      { id: 'PERF-HDG-300x75', label: '300 x 75 mm', widthMm: 300, depthMm: 75 },
      { id: 'PERF-HDG-450x100', label: '450 x 100 mm', widthMm: 450, depthMm: 100 },
    ],
  },
];

const services = [
  { id: 'power', label: 'Power', color: 0x2563eb },
  { id: 'control', label: 'Control', color: 0x0f766e },
  { id: 'instrument', label: 'Instrument', color: 0xca8a04 },
  { id: 'telecom', label: 'Telecom', color: 0x7c3aed },
];

const state = {
  runs: [],
  activeRunId: '',
  selectedNodeIndex: -1,
  mode: 'idle',
  familyId: catalog[0].id,
  sizeId: catalog[0].sizes[0].id,
  serviceClass: services[0].id,
  elevationM: 0,
  elevationInitialized: false,
};

let layer = null;
let runtime = null;
let interaction = null;
let panel = null;
let statusEl = null;
let summaryEl = null;
let runListEl = null;
let nodeListEl = null;
let inspectorEl = null;
let bootstrapAttempts = 0;

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

function activeFamily() {
  return catalog.find(family => family.id === state.familyId) || catalog[0];
}

function activeSize() {
  const family = activeFamily();
  return family.sizes.find(size => size.id === state.sizeId) || family.sizes[0];
}

function serviceFor(id = state.serviceClass) {
  return services.find(service => service.id === id) || services[0];
}

function activeRun() {
  return state.runs.find(run => run.id === state.activeRunId) || null;
}

function selectedNode() {
  const run = activeRun();
  return run && state.selectedNodeIndex >= 0 ? run.nodes[state.selectedNodeIndex] || null : null;
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
    });
  }
  return registry.register({
    id: RACEWAY_LAYER_ID,
    owner: 'raceway',
    kind: 'consumer-overlay',
    label: 'Raceway',
    createGroup: true,
    getElements: () => state.runs,
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
}

function bootstrap() {
  registerRacewayOverlay();
  ensurePanel();
  if (!hostReady()) return false;
  ensureElevationDefault();
  ensureInteraction();
  renderRaceway();
  renderPanel();
  if (window.racewayViewerOverlay) window.racewayViewerOverlay.layer = layer;
  return true;
}

function ensureInteraction() {
  if (interaction || !runtime?.registerInteraction) return;
  interaction = runtime.registerInteraction({
    id: RACEWAY_INTERACTION_ID,
    cursor: 'crosshair',
    onCanvasClick: event => {
      if (state.mode === 'draw') {
        addNodeFromEvent(event);
        return true;
      }
      if (state.mode === 'move') {
        moveSelectedNodeFromEvent(event);
        return true;
      }
      return false;
    },
    onCancel: () => {
      state.mode = 'idle';
      setStatus('Raceway command cancelled.');
      renderPanel();
    },
  });
}

function activateCanvasMode(mode) {
  state.mode = mode;
  interaction?.activate?.();
}

function deactivateCanvasMode() {
  state.mode = 'idle';
  interaction?.deactivate?.();
}

function makeRun() {
  const family = activeFamily();
  const size = activeSize();
  return {
    id: `raceway-draft-${Date.now()}-${state.runs.length + 1}`,
    tag: `RWY-${String(state.runs.length + 1).padStart(3, '0')}`,
    familyId: family.id,
    familyLabel: family.label,
    sizeId: size.id,
    sizeLabel: size.label,
    widthMm: size.widthMm,
    depthMm: size.depthMm,
    serviceClass: state.serviceClass,
    elevationM: Number(state.elevationM) || 0,
    nodes: [],
  };
}

function sourcePointFromEvent(event) {
  if (!runtime?.pointOnSourceElevationFromViewerEvent) return null;
  const renderPoint = runtime.pointOnSourceElevationFromViewerEvent(event, Number(state.elevationM) || 0);
  if (!renderPoint) return null;
  const sourcePoint = runtime.renderPointToSourcePoint(renderPoint);
  return {
    x: Number(sourcePoint.x) || 0,
    y: Number(sourcePoint.y) || 0,
    z: Number(state.elevationM) || 0,
    coordinate_frame: 'source_xyz_m',
  };
}

function nodeDistance(a, b) {
  if (!a || !b) return 0;
  const dx = Number(b.x || 0) - Number(a.x || 0);
  const dy = Number(b.y || 0) - Number(a.y || 0);
  const dz = Number(b.z || 0) - Number(a.z || 0);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function runLength(run) {
  return run.nodes.reduce((total, node, index) => total + nodeDistance(run.nodes[index - 1], node), 0);
}

function runWarnings(run) {
  const warnings = [];
  run.nodes.forEach((node, index) => {
    if (index > 0 && nodeDistance(run.nodes[index - 1], node) < 0.05) warnings.push(`Short segment ${index}`);
    if (Math.abs(Number(node.z || 0) - Number(run.elevationM || 0)) > 0.001) warnings.push(`Node ${index + 1} off plane`);
  });
  return warnings;
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

function renderRaceway() {
  if (!hostReady()) return;
  clearLayerGroup();
  const THREE = runtime.THREE;
  state.runs.forEach(run => {
    const color = serviceFor(run.serviceClass).color;
    const group = new THREE.Group();
    const points = run.nodes.map(renderSourcePoint).filter(Boolean);
    if (points.length > 1) {
      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({ color, depthTest: false }),
      ));
    }
    run.nodes.forEach((node, index) => {
      const renderPoint = renderSourcePoint(node);
      if (!renderPoint) return;
      const selected = run.id === state.activeRunId && index === state.selectedNodeIndex;
      const radius = runtime.worldUnitsForScreenPixels?.(renderPoint, 7, 0.04, 0.22) || 0.12;
      const handle = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 16, 16),
        new THREE.MeshBasicMaterial({ color: selected ? 0xf97316 : color, depthTest: false }),
      );
      handle.position.copy(renderPoint);
      group.add(handle);
    });
    layer.group.add(group);
  });
  window.plant3dViewerLayers?.update?.(RACEWAY_LAYER_ID, { getElements: () => state.runs });
  runtime.renderNow?.();
}

function beginRun() {
  if (!hostReady()) {
    setStatus('Viewer is still preparing raceway tools.');
    return;
  }
  ensureElevationDefault();
  const run = makeRun();
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
  deactivateCanvasMode();
  setStatus(`${run.tag}: ${run.nodes.length} nodes, ${formatM(runLength(run))} m`);
  renderPanel();
}

function cancelRun() {
  const run = activeRun();
  if (run && state.mode === 'draw' && run.nodes.length === 0) {
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
  const point = sourcePointFromEvent(event);
  if (!run || !point) {
    setStatus('No point found on the active elevation.');
    return;
  }
  run.nodes.push(point);
  state.selectedNodeIndex = run.nodes.length - 1;
  setStatus(`${run.tag}: node ${run.nodes.length} added.`);
  renderRaceway();
  renderPanel();
}

function undoNode() {
  const run = activeRun();
  if (!run?.nodes.length) return;
  run.nodes.pop();
  state.selectedNodeIndex = Math.min(state.selectedNodeIndex, run.nodes.length - 1);
  setStatus(`${run.tag}: last node removed.`);
  renderRaceway();
  renderPanel();
}

function deleteSelectedNode() {
  const run = activeRun();
  if (!run || state.selectedNodeIndex < 0) return;
  run.nodes.splice(state.selectedNodeIndex, 1);
  state.selectedNodeIndex = Math.min(state.selectedNodeIndex, run.nodes.length - 1);
  deactivateCanvasMode();
  setStatus(`${run.tag}: node deleted.`);
  renderRaceway();
  renderPanel();
}

function moveSelectedNodeFromEvent(event) {
  const run = activeRun();
  const point = sourcePointFromEvent(event);
  if (!run || state.selectedNodeIndex < 0 || !point) return;
  run.nodes[state.selectedNodeIndex] = point;
  deactivateCanvasMode();
  setStatus(`${run.tag}: node ${state.selectedNodeIndex + 1} moved.`);
  renderRaceway();
  renderPanel();
}

function setStatus(message) {
  if (statusEl) statusEl.textContent = message;
}

function injectStyles() {
  if (document.getElementById('racewayViewerStyles')) return;
  const style = document.createElement('style');
  style.id = 'racewayViewerStyles';
  style.textContent = `
    .raceway-tool-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .raceway-tool-grid label, .raceway-node-editor label { display: grid; gap: 4px; color: #475569; font-size: 11px; font-weight: 700; }
    .raceway-tool-grid select, .raceway-tool-grid input, .raceway-node-editor input { width: 100%; min-width: 0; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 6px; color: #0f172a; font-size: 12px; }
    .raceway-status { margin: 8px 0; color: #475569; font-size: 12px; line-height: 1.35; }
    .raceway-run-list, .raceway-node-list { display: grid; gap: 6px; margin-top: 8px; }
    .raceway-row { width: 100%; justify-content: space-between; text-align: left; }
    .raceway-row-active { border-color: #2563eb; color: #1d4ed8; }
    .raceway-node-editor { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
  `;
  document.head.appendChild(style);
}

function familyOptionsHtml() {
  return catalog.map(family => `<option value="${escapeHtml(family.id)}"${family.id === state.familyId ? ' selected' : ''}>${escapeHtml(family.label)}</option>`).join('');
}

function sizeOptionsHtml() {
  return activeFamily().sizes.map(size => `<option value="${escapeHtml(size.id)}"${size.id === state.sizeId ? ' selected' : ''}>${escapeHtml(size.label)}</option>`).join('');
}

function serviceOptionsHtml() {
  return services.map(service => `<option value="${escapeHtml(service.id)}"${service.id === state.serviceClass ? ' selected' : ''}>${escapeHtml(service.label)}</option>`).join('');
}

function runRowsHtml() {
  if (!state.runs.length) return '<div class="meta">No raceway drafts</div>';
  return state.runs.map(run => `
    <button type="button" class="raceway-row ${run.id === state.activeRunId ? 'raceway-row-active' : ''}" data-raceway-action="select-run" data-run-id="${escapeHtml(run.id)}">
      <strong>${escapeHtml(run.tag)}</strong><br>
      ${escapeHtml(run.familyLabel)} ${escapeHtml(run.sizeLabel)}<br>
      ${escapeHtml(serviceFor(run.serviceClass).label)} | ${run.nodes.length} nodes | ${formatM(runLength(run))} m
    </button>
  `).join('');
}

function nodeRowsHtml() {
  const run = activeRun();
  if (!run?.nodes.length) return '<div class="meta">No nodes</div>';
  return run.nodes.map((node, index) => `
    <button type="button" class="raceway-row ${index === state.selectedNodeIndex ? 'raceway-row-active' : ''}" data-raceway-action="select-node" data-node-index="${index}">
      N${index + 1} X ${formatM(node.x)} Y ${formatM(node.y)} EL ${formatM(node.z)}
    </button>
  `).join('');
}

function inspectorHtml() {
  const node = selectedNode();
  if (!node) return '<div class="meta">Select a node</div>';
  return `
    <div class="raceway-node-editor">
      <label>X m<input type="number" step="0.001" value="${formatM(node.x)}" data-raceway-node-axis="x"></label>
      <label>Y m<input type="number" step="0.001" value="${formatM(node.y)}" data-raceway-node-axis="y"></label>
      <label>EL m<input type="number" step="0.001" value="${formatM(node.z)}" data-raceway-node-axis="z"></label>
    </div>
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
    <summary>Raceway Draft</summary>
    <div id="racewayToolStatus" class="raceway-status">Ready</div>
    <div class="raceway-tool-grid">
      <label>Family<select id="racewayFamilySelect">${familyOptionsHtml()}</select></label>
      <label>Size<select id="racewaySizeSelect">${sizeOptionsHtml()}</select></label>
      <label>Service<select id="racewayServiceSelect">${serviceOptionsHtml()}</select></label>
      <label>EL m<input id="racewayElevationInput" type="number" step="0.001" value="${formatM(state.elevationM)}"></label>
    </div>
    <div class="p3d-toolbar" style="margin-top: 10px;">
      <button type="button" class="p3d-button-primary" data-raceway-action="start">Start</button>
      <button type="button" data-raceway-action="finish">Finish</button>
      <button type="button" data-raceway-action="undo">Undo Node</button>
      <button type="button" data-raceway-action="cancel">Cancel</button>
    </div>
    <div class="p3d-toolbar" style="margin-top: 8px;">
      <button type="button" data-raceway-action="move-node">Move Node</button>
      <button type="button" data-raceway-action="delete-node">Delete Node</button>
    </div>
    <div id="racewaySummary" class="meta" style="margin-top: 8px;"></div>
    <div id="racewayRunList" class="raceway-run-list"></div>
    <div id="racewayNodeList" class="raceway-node-list"></div>
    <div id="racewayInspector"></div>
  `;
  layerPanel.parentNode.insertBefore(panel, layerPanel);
  statusEl = panel.querySelector('#racewayToolStatus');
  summaryEl = panel.querySelector('#racewaySummary');
  runListEl = panel.querySelector('#racewayRunList');
  nodeListEl = panel.querySelector('#racewayNodeList');
  inspectorEl = panel.querySelector('#racewayInspector');
  panel.addEventListener('click', handlePanelClick);
  panel.addEventListener('change', handlePanelChange);
  panel.addEventListener('input', handlePanelInput);
  return panel;
}

function renderPanel() {
  if (!panel) return;
  const run = activeRun();
  if (panel.querySelector('#racewayElevationInput') !== document.activeElement) {
    panel.querySelector('#racewayElevationInput').value = formatM(state.elevationM);
  }
  if (summaryEl) {
    const warnings = run ? runWarnings(run).length : 0;
    summaryEl.textContent = run
      ? `${run.tag} | EL +${formatM(run.elevationM)} | ${formatM(runLength(run))} m | ${warnings} warning(s)`
      : 'No active run';
  }
  if (runListEl) runListEl.innerHTML = runRowsHtml();
  if (nodeListEl) nodeListEl.innerHTML = nodeRowsHtml();
  if (inspectorEl && !inspectorEl.contains(document.activeElement)) inspectorEl.innerHTML = inspectorHtml();
}

function handlePanelClick(event) {
  const button = event.target.closest?.('[data-raceway-action]');
  if (!button) return;
  const action = button.dataset.racewayAction;
  if (action === 'start') beginRun();
  if (action === 'finish') finishRun();
  if (action === 'undo') undoNode();
  if (action === 'cancel') cancelRun();
  if (action === 'delete-node') deleteSelectedNode();
  if (action === 'move-node') {
    if (selectedNode()) {
      activateCanvasMode('move');
      setStatus('Move Node: click the replacement point.');
    } else {
      setStatus('Select a node before move.');
    }
  }
  if (action === 'select-run') {
    state.activeRunId = button.dataset.runId || '';
    state.selectedNodeIndex = -1;
    deactivateCanvasMode();
    renderRaceway();
    renderPanel();
  }
  if (action === 'select-node') {
    state.selectedNodeIndex = Number(button.dataset.nodeIndex);
    deactivateCanvasMode();
    renderRaceway();
    renderPanel();
  }
}

function handlePanelChange(event) {
  const target = event.target;
  if (target.id === 'racewayFamilySelect') {
    state.familyId = target.value;
    state.sizeId = activeFamily().sizes[0].id;
    panel.querySelector('#racewaySizeSelect').innerHTML = sizeOptionsHtml();
  }
  if (target.id === 'racewaySizeSelect') state.sizeId = target.value;
  if (target.id === 'racewayServiceSelect') state.serviceClass = target.value;
  if (target.id === 'racewayElevationInput') {
    state.elevationM = Number(target.value) || 0;
    state.elevationInitialized = true;
  }
}

function handlePanelInput(event) {
  const axis = event.target.dataset?.racewayNodeAxis;
  if (!axis) return;
  const node = selectedNode();
  if (!node) return;
  const value = Number(event.target.value);
  if (!Number.isFinite(value)) return;
  node[axis] = value;
  if (axis === 'z') {
    const run = activeRun();
    if (run) run.elevationM = value;
  }
  renderRaceway();
}

window.addEventListener('plant3dviewer:layers-ready', scheduleBootstrap);
window.addEventListener('plant3dviewer:runtime-ready', scheduleBootstrap);
window.addEventListener('DOMContentLoaded', scheduleBootstrap);
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
    deactivateCanvasMode();
    renderRaceway();
    renderPanel();
  },
};
