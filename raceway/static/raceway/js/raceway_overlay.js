const RACEWAY_LAYER_ID = 'raceway-overlay';

const state = {
  runs: [],
};

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

let layer = registerRacewayOverlay();

function ensureRacewayOverlay() {
  layer = registerRacewayOverlay();
  if (window.racewayViewerOverlay) {
    window.racewayViewerOverlay.layer = layer;
  }
}

window.addEventListener('plant3dviewer:layers-ready', ensureRacewayOverlay);
window.addEventListener('DOMContentLoaded', ensureRacewayOverlay);
window.setTimeout(ensureRacewayOverlay, 0);

window.racewayViewerOverlay = {
  layerId: RACEWAY_LAYER_ID,
  layer,
  getRuns: () => [...state.runs],
  setRuns: runs => {
    state.runs = Array.isArray(runs) ? [...runs] : [];
    window.plant3dViewerLayers?.update?.(RACEWAY_LAYER_ID, {
      getElements: () => state.runs,
    });
  },
};
