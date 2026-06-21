import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const sceneDataEl = document.getElementById('scene-data');
const container = document.getElementById('viewer');
const propsContent = document.getElementById('props-content');
const pageBody = document.body;
const navPanelToggleBtn = document.getElementById('navpanel-toggle');
const navPanelReopenBtn = document.getElementById('navpanel-reopen');
const sidePanelToggleBtn = document.getElementById('sidepanel-toggle');
const sidePanelReopenBtn = document.getElementById('sidepanel-reopen');
const toggleAllHierarchy = document.getElementById('toggleAllHierarchy');
const hierarchySelectionCount = document.getElementById('hierarchySelectionCount');
const hContent = document.getElementById("hierarchy-content");
const hierarchySearchInput = document.getElementById('hierarchySearchInput');
const hierarchySearchStatus = document.getElementById('hierarchySearchStatus');
const searchFocusBtn = document.getElementById('searchFocusBtn');
const searchIsolateBtn = document.getElementById('searchIsolateBtn');
const searchClearBtn = document.getElementById('searchClearBtn');
const richSymbolToggle = document.getElementById('toggleRichSymbols');
const contextLabelToggle = document.getElementById('toggleContextLabels');
const ifcOpacityWrap = document.getElementById('ifcOpacityWrap');
const ifcOpacitySlider = document.getElementById('ifcOpacitySlider');
const ifcOpacityValue = document.getElementById('ifcOpacityValue');
const ifcClassFilterWrap = document.getElementById('ifcClassFilterWrap');
const ifcClassFilters = document.getElementById('ifcClassFilters');
const attributeSettingsBtn = document.getElementById('attributeSettingsBtn');
const attributeSettingsModal = document.getElementById('attributeSettingsModal');
const attributeSettingsCloseBtn = document.getElementById('attributeSettingsCloseBtn');
const attributeSettingsSaveBtn = document.getElementById('attributeSettingsSaveBtn');
const attributeSettingsResetBtn = document.getElementById('attributeSettingsResetBtn');
const attributeSettingsRows = document.getElementById('attributeSettingsRows');
const attributeSettingsEmpty = document.getElementById('attributeSettingsEmpty');
const attributeSettingsStatus = document.getElementById('attributeSettingsStatus');
const scaleToggleBtn = document.getElementById('scaleToggleBtn');
const measureToggleBtn = document.getElementById('measureToggleBtn');
const viewerUnitBadge = document.getElementById('viewerUnitBadge');
const measurementHud = document.getElementById('measurementHud');
const measurementStatus = document.getElementById('measurementStatus');
const ehtToolPalette = document.getElementById('ehtToolPalette');
const ehtToolStatus = document.getElementById('ehtToolStatus');
const ehtPaletteToggleBtn = document.getElementById('ehtPaletteToggleBtn');
const ehtSelectToolBtn = document.getElementById('ehtSelectToolBtn');
const ehtSaveLayerBtn = document.getElementById('ehtSaveLayerBtn');
const ehtRouteControls = document.getElementById('ehtRouteControls');
const ehtFinishRouteBtn = document.getElementById('ehtFinishRouteBtn');
const ehtCancelRouteBtn = document.getElementById('ehtCancelRouteBtn');

if (!sceneDataEl) throw new Error("scene-data script tag not found");
if (!container) throw new Error("viewer container not found");

const sceneData = JSON.parse(sceneDataEl.textContent);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf3f4f6);

const camera = new THREE.PerspectiveCamera(
    60,
    container.clientWidth / container.clientHeight,
    0.1,
    10000
);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.domElement.style.display = 'block';
renderer.domElement.style.width = '100%';
renderer.domElement.style.height = '100%';
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = true;
controls.enableRotate = true;
controls.enableZoom = true;
controls.screenSpacePanning = true;
controls.zoomToCursor = true;
controls.rotateSpeed = 0.8;
controls.zoomSpeed = 1.2;
controls.panSpeed = 0.8;
controls.mouseButtons = {
    LEFT: THREE.MOUSE.ROTATE,
    MIDDLE: THREE.MOUSE.DOLLY,
    RIGHT: THREE.MOUSE.PAN
};

scene.add(new THREE.AmbientLight(0xffffff, 0.9));

const dir1 = new THREE.DirectionalLight(0xffffff, 0.7);
dir1.position.set(100, 120, 80);
scene.add(dir1);

const dir2 = new THREE.DirectionalLight(0xffffff, 0.35);
dir2.position.set(-80, 60, -50);
scene.add(dir2);

let gridHelper = new THREE.GridHelper(300, 30, 0x888888, 0xb0b0b0);
scene.add(gridHelper);

let axesHelper = new THREE.AxesHelper(80);
scene.add(axesHelper);
let ground = null;

const modelGroup = new THREE.Group();
scene.add(modelGroup);

const raycaster = new THREE.Raycaster();
raycaster.params.Line = { threshold: 0.08 };
const mouse = new THREE.Vector2();
const selectableMeshes = [];
const ehtSelectableMeshes = [];
const manuallyHiddenItems = new Set();
const contextLabels = [];
const gridScaleLabels = [];
const measurementObjects = [];
const measurementPreviewObjects = [];
const ehtRoutePreviewObjects = [];
const ehtPlacementPreviewObjects = [];
let measurementSnapCandidates = [];
const MEASURE_INACTIVE_BUTTON_CLASSES = ['bg-white', 'hover:bg-slate-50', 'text-slate-700', 'border-slate-200'];
const MEASURE_ACTIVE_BUTTON_CLASSES = ['bg-amber-500', 'hover:bg-amber-400', 'text-slate-950', 'border-amber-500'];
const leafRepresentatives = new Map();
let hierarchySearchMatches = new Set();
let attributeLabelMap = {};
let attributeMappings = [];
let visibleAttributeKeys = [];
let showGridScaleLabels = true;
let lastGridScaleState = null;
let measureModeActive = false;
let measurementPoints = [];
let hoveredSnapKey = "";
let ehtElements = [];
let ehtObjects = [];
const visibleEhtTypes = new Set();
const hiddenEhtUids = new Set();
const knownEhtTypes = new Set();
const collapsedEhtTypes = new Set();
let activeEhtTool = "";
let pendingEhtRoutePoints = [];
let selectedEhtElementUid = "";
let ehtLayerDirty = false;
let pendingEhtGeometryEdit = null;
let selectedEhtObjects = [];
let hoveredEhtPlacementKey = "";
let routeStartElementUid = "";

let selectedGroup = null;

function vecFromArray(a) {
    return new THREE.Vector3(a[0], a[1], a[2]);
}

function getItemProperties(item) {
    return item.properties || {};
}

function getSourceFormat(item) {
    return String(getItemProperties(item).source_format || "").toUpperCase();
}

function getHierarchyFile(item) {
    return getItemProperties(item).filename || "Unknown File";
}

function getHierarchyPipe(item) {
    const props = getItemProperties(item);
    return (
        props.pipeline_ref
        || props.spool_ref
        || props.hierarchy_group
        || props.storey_name
        || props.ifc_class
        || "Unknown Group"
    );
}

function getHierarchyGroup(item) {
    return getHierarchyPipe(item);
}

function getHierarchyGroupKey(item) {
    return `${getHierarchyFile(item)}___${getHierarchyGroup(item)}`;
}

function getHierarchyLeafLabel(item) {
    const props = getItemProperties(item);
    if (getSourceFormat(item) === "IFC") {
        return (
            props.component_ref
            || props.name
            || props.global_id
            || props.tag
            || `${props.ifc_class || item.kind || "IFC Object"} ${props.uid ?? item.uid ?? ""}`.trim()
        );
    }
    return getHierarchyGroup(item);
}

function getHierarchyLeafKey(item) {
    if (getSourceFormat(item) !== "IFC") {
        return getHierarchyGroupKey(item);
    }
    const props = getItemProperties(item);
    return `${getHierarchyGroupKey(item)}___${props.global_id || props.uid || props.component_ref || props.name || item.kind || "object"}`;
}

function getHierarchySearchText(item) {
    const props = getItemProperties(item);
    const materials = (props.materials || [])
        .map((entry) => `${entry.code || ""} ${entry.description || ""}`.trim())
        .join(" ");
    const spatialPath = Array.isArray(props.spatial_path) ? props.spatial_path.join(" ") : "";
    return [
        getHierarchyFile(item),
        getHierarchyGroup(item),
        getHierarchyLeafLabel(item),
        props.component_ref,
        props.name,
        props.global_id,
        props.ifc_class,
        props.tag,
        props.pipeline_ref,
        props.spool_ref,
        props.support_code,
        props.inline_code,
        props.description,
        props.object_type,
        props.predefined_type,
        materials,
        spatialPath,
    ].join(" ").toLowerCase();
}

function getItemVisibilityKey(item) {
    const props = getItemProperties(item);
    return `${getHierarchyFile(item)}___${props.uid ?? "no-uid"}___${props.record_id ?? item.kind ?? "item"}`;
}

function getAttributeMappingUrl() {
    return attributeSettingsBtn ? attributeSettingsBtn.dataset.mappingUrl || "" : "";
}

function isPcfAttributeKey(key) {
    return /^ATTRIBUTE\d+$/i.test(String(key || "").trim());
}

function attributeSort(a, b) {
    const aNum = parseInt(String(a).replace(/\D+/g, ""), 10);
    const bNum = parseInt(String(b).replace(/\D+/g, ""), 10);
    if (Number.isFinite(aNum) && Number.isFinite(bNum) && aNum !== bNum) {
        return aNum - bNum;
    }
    return String(a).localeCompare(String(b));
}

function sceneItems() {
    return [
        ...(sceneData.pipes || []),
        ...(sceneData.fittings || []),
        ...(sceneData.welds || []),
        ...(sceneData.supports || []),
        ...(sceneData.markers || []),
        ...(sceneData.meshes || []),
    ];
}

let EHT_ELEMENT_DEFS = {
    distribution_board: {
        label: "Distribution Board",
        geometry_type: "point",
        color: 0x7c3aed,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "board_ref", label: "Board Ref", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "voltage", label: "Voltage", type: "text" },
            { key: "length_m", label: "Length m", type: "number", default: "0.80" },
            { key: "width_m", label: "Width m", type: "number", default: "0.25" },
            { key: "height_m", label: "Height m", type: "number", default: "1.00" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    junction_box: {
        label: "Junction Box",
        geometry_type: "point",
        color: 0x2563eb,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "source_board", label: "Source Board", type: "text" },
            { key: "length_m", label: "Length m", type: "number", default: "0.35" },
            { key: "width_m", label: "Width m", type: "number", default: "0.16" },
            { key: "height_m", label: "Height m", type: "number", default: "0.30" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    isolator: {
        label: "Isolator",
        geometry_type: "point",
        color: 0x0f766e,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "isolator_type", label: "Isolator Type", type: "text" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    tracer_sr: {
        label: "SR Tracer",
        geometry_type: "polyline",
        color: 0xf59e0b,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "tracer_family", label: "Tracer Family", type: "select", options: ["SR"], default: "SR" },
            { key: "tracer_type", label: "Tracer Type", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "watts_per_m", label: "W/m", type: "number" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    tracer_mi: {
        label: "MI Tracer",
        geometry_type: "polyline",
        color: 0xea580c,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "tracer_family", label: "Tracer Family", type: "select", options: ["MI"], default: "MI" },
            { key: "tracer_type", label: "Tracer Type", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "watts_per_m", label: "W/m", type: "number" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    rtd: {
        label: "RTD",
        geometry_type: "point",
        color: 0xdc2626,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "setpoint_c", label: "Setpoint C", type: "number" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    cold_cable: {
        label: "Cold Cable",
        geometry_type: "polyline",
        color: 0x0284c7,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "from", label: "From", type: "text" },
            { key: "to", label: "To", type: "text" },
            { key: "cable_type", label: "Cable Type", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    end_termination: {
        label: "End Termination",
        geometry_type: "point",
        color: 0xbe123c,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "circuit", label: "Circuit", type: "text" },
            { key: "termination_type", label: "Termination Type", type: "text" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
    pipe_strap: {
        label: "Pipe Strap",
        geometry_type: "point",
        color: 0x65a30d,
        fields: [
            { key: "tag", label: "Tag", type: "text" },
            { key: "strap_type", label: "Strap Type", type: "text" },
            { key: "spacing_m", label: "Spacing m", type: "number" },
            { key: "note", label: "Construction Note", type: "textarea" },
        ],
    },
};

function getEhtDef(elementType) {
    return EHT_ELEMENT_DEFS[elementType] || EHT_ELEMENT_DEFS.junction_box;
}

function normalizeEhtDefinition(def) {
    const normalized = { ...def };
    normalized.geometry_type = normalized.geometry_type || normalized.geometryType || "point";
    if (typeof normalized.color === "string") {
        normalized.color = parseInt(normalized.color.replace("#", ""), 16);
    }
    normalized.fields = Array.isArray(normalized.fields) ? normalized.fields : [];
    return normalized;
}

function applyEhtToolDefinitions(definitions) {
    if (!definitions || typeof definitions !== "object") return;
    EHT_ELEMENT_DEFS = Object.fromEntries(
        Object.entries(definitions).map(([key, def]) => [key, normalizeEhtDefinition(def)])
    );
}

function getEhtOverlayUrl() {
    return container ? container.dataset.ehtUrl || "" : "";
}

function getSceneAttributeDictionary() {
    const found = new Map();
    sceneItems().forEach(item => {
        const props = getItemProperties(item);
        const metadata = props.pipeline_metadata || {};
        Object.entries(metadata).forEach(([key, value]) => {
            if (!isPcfAttributeKey(key)) return;
            if (!found.has(key)) {
                found.set(key, {
                    key,
                    sampleValue: Array.isArray(value) ? value.join(" | ") : value,
                    count: 0,
                });
            }
            found.get(key).count += 1;
        });
    });
    return Array.from(found.values()).sort((a, b) => attributeSort(a.key, b.key));
}

function getAttributeSettingsDictionary() {
    const byKey = new Map(getSceneAttributeDictionary().map(row => [row.key, row]));
    attributeMappings.forEach(mapping => {
        const key = String(mapping.attribute_key || "").trim().toUpperCase();
        if (!key || byKey.has(key)) return;
        byKey.set(key, {
            key,
            sampleValue: "",
            count: 0,
        });
    });
    return Array.from(byKey.values()).sort((a, b) => attributeSort(a.key, b.key));
}

function displayNameForAttribute(key) {
    const label = String(attributeLabelMap[key] || "").trim();
    return label || key;
}

function rebuildAttributeLabelMap() {
    attributeLabelMap = {};
    attributeMappings.forEach(mapping => {
        const key = String(mapping.attribute_key || "").trim().toUpperCase();
        const label = String(mapping.display_name || "").trim();
        if (key && label) {
            attributeLabelMap[key] = label;
        }
    });
}

function getDisplayPipelineAttributes(properties) {
    const metadata = properties.pipeline_metadata || {};
    return Object.entries(metadata)
        .filter(([key, value]) => isPcfAttributeKey(key) && value !== "" && value !== null && value !== undefined)
        .sort(([a], [b]) => attributeSort(a, b))
        .map(([key, value]) => ({
            key,
            label: displayNameForAttribute(key),
            value: Array.isArray(value) ? value.join(" | ") : String(value),
            isNamed: Boolean(String(attributeLabelMap[key] || "").trim()),
        }));
}

function getAvailablePipelineAttributes(properties) {
    const detected = getDisplayPipelineAttributes(properties);
    const detectedByKey = new Map(detected.map(row => [row.key, row]));
    const ordered = [];
    const seen = new Set();

    attributeMappings.forEach(mapping => {
        const key = String(mapping.attribute_key || "").trim().toUpperCase();
        if (!key || seen.has(key) || !detectedByKey.has(key)) return;
        ordered.push(detectedByKey.get(key));
        seen.add(key);
    });

    detected.forEach(row => {
        if (!seen.has(row.key)) {
            ordered.push(row);
            seen.add(row.key);
        }
    });

    return ordered;
}

function normalizeVisibleAttributeKeys(availableAttributes) {
    const availableKeys = availableAttributes.map(row => row.key);
    visibleAttributeKeys = visibleAttributeKeys.filter(key => availableKeys.includes(key));
    if (!visibleAttributeKeys.length && availableKeys.length) {
        visibleAttributeKeys = [availableKeys[0]];
    }
}

function addVisibleAttributeKey(availableAttributes) {
    const next = availableAttributes.find(row => !visibleAttributeKeys.includes(row.key));
    if (next) {
        visibleAttributeKeys.push(next.key);
    }
}

async function loadProjectAttributeMappings() {
    const url = getAttributeMappingUrl();
    if (!url) return;

    try {
        const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Unable to load project attribute names.");
        }
        attributeMappings = Array.isArray(payload.mappings) ? payload.mappings : [];
        rebuildAttributeLabelMap();
        rerenderSelectedProperties();
    } catch (error) {
        console.error("[idfviewer] Attribute mapping load failed", error);
        if (attributeSettingsStatus) {
            attributeSettingsStatus.textContent = error.message || "Unable to load names";
        }
    }
}

function setNavPanelCollapsed(collapsed) {
    pageBody.classList.toggle('nav-collapsed', collapsed);
    if (navPanelToggleBtn) {
        navPanelToggleBtn.textContent = collapsed ? "Show" : "Hide";
    }
    setTimeout(() => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }, 230);
}

function refreshViewerSize() {
    setTimeout(() => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }, 230);
}

function setSidePanelCollapsed(collapsed) {
    pageBody.classList.toggle('sidepanel-collapsed', collapsed);
    if (sidePanelToggleBtn) {
        sidePanelToggleBtn.textContent = collapsed ? "Show" : "Hide";
    }
    refreshViewerSize();
}

function setGridScaleVisible(visible) {
    showGridScaleLabels = visible;
    if (scaleToggleBtn) {
        scaleToggleBtn.textContent = visible ? "Grid On" : "Grid Off";
        scaleToggleBtn.setAttribute('aria-pressed', visible ? 'true' : 'false');
    }
    if (gridHelper) gridHelper.visible = visible;
    if (axesHelper) axesHelper.visible = visible;
    if (!visible) {
        clearGridScaleLabels();
        return;
    }
    if (lastGridScaleState) {
        updateGridScaleLabels(
            lastGridScaleState.center,
            lastGridScaleState.gridDim,
            lastGridScaleState.baseY,
            lastGridScaleState.gridStep,
        );
    }
}

function registerSelectable(mesh, item, selectGroup, { richSymbol = false } = {}) {
    mesh.userData.item = item;
    mesh.userData.selectGroup = selectGroup;
    mesh.userData.groupKey = getHierarchyGroupKey(item);
    mesh.userData.leafKey = getHierarchyLeafKey(item);
    mesh.userData.leafLabel = getHierarchyLeafLabel(item);
    mesh.userData.visibilityKey = getItemVisibilityKey(item);
    mesh.userData.isRichSymbol = richSymbol;
    mesh.userData.ifcClass = getItemProperties(item).ifc_class || "";
    selectableMeshes.push(mesh);

    const existing = leafRepresentatives.get(mesh.userData.leafKey);
    if (!existing || (existing.userData.isRichSymbol && !richSymbol)) {
        leafRepresentatives.set(mesh.userData.leafKey, mesh);
    }
}

function addCylinderBetweenPoints(startArr, endArr, radius, color, item, selectGroup, { richSymbol = false } = {}) {
    const start = vecFromArray(startArr);
    const end = vecFromArray(endArr);

    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();

    if (length < 0.0001) {
        const g = new THREE.SphereGeometry(radius * 1.2, 10, 10);
        const m = new THREE.MeshStandardMaterial({ color });
        const s = new THREE.Mesh(g, m);
        s.position.copy(start);
        modelGroup.add(s);
        registerSelectable(s, item, selectGroup, { richSymbol });
        selectGroup.push(s);
        return s;
    }

    const geometry = new THREE.CylinderGeometry(radius, radius, length, 10);
    const material = new THREE.MeshStandardMaterial({ color });
    const cylinder = new THREE.Mesh(geometry, material);

    const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    cylinder.position.copy(midpoint);

    const yAxis = new THREE.Vector3(0, 1, 0);
    cylinder.quaternion.setFromUnitVectors(
        yAxis,
        direction.clone().normalize()
    );

    modelGroup.add(cylinder);
    registerSelectable(cylinder, item, selectGroup, { richSymbol });
    selectGroup.push(cylinder);
    return cylinder;
}

function addSphere(pointArr, color, radius, item, selectGroup, { richSymbol = false } = {}) {
    const geometry = new THREE.SphereGeometry(radius, 14, 14);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    modelGroup.add(mesh);
    registerSelectable(mesh, item, selectGroup, { richSymbol });
    selectGroup.push(mesh);
    return mesh;
}

function addCube(pointArr, color, size, item, selectGroup, { richSymbol = false } = {}) {
    const geometry = new THREE.BoxGeometry(size, size, size);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    modelGroup.add(mesh);
    registerSelectable(mesh, item, selectGroup, { richSymbol });
    selectGroup.push(mesh);
    return mesh;
}

function addStandaloneMesh(mesh, item, selectGroup, { richSymbol = false, selectable = true } = {}) {
    modelGroup.add(mesh);
    if (selectable) {
        registerSelectable(mesh, item, selectGroup, { richSymbol });
        selectGroup.push(mesh);
    }
    return mesh;
}

function orientObjectToDirection(object, direction) {
    const safeDirection = direction && direction.lengthSq() > 0.000001
        ? direction.clone().normalize()
        : new THREE.Vector3(1, 0, 0);
    const yAxis = new THREE.Vector3(0, 1, 0);
    object.quaternion.setFromUnitVectors(yAxis, safeDirection);
}

function getSegmentDirection(startArr, endArr) {
    return vecFromArray(endArr).sub(vecFromArray(startArr)).normalize();
}

function pointAlongSegment(startArr, endArr, t) {
    return [
        startArr[0] + (endArr[0] - startArr[0]) * t,
        startArr[1] + (endArr[1] - startArr[1]) * t,
        startArr[2] + (endArr[2] - startArr[2]) * t,
    ];
}

function midpointOfSegment(startArr, endArr) {
    return pointAlongSegment(startArr, endArr, 0.5);
}

const segmentSources = [...(sceneData.pipes || []), ...(sceneData.fittings || [])]
    .filter(item => item.start && item.end)
    .map(item => {
        const start = vecFromArray(item.start);
        const end = vecFromArray(item.end);
        const delta = new THREE.Vector3().subVectors(end, start);
        return {
            start,
            end,
            direction: delta.lengthSq() > 0.000001 ? delta.normalize() : new THREE.Vector3(1, 0, 0),
        };
    });

function findNearestDirection(pointArr) {
    if (!segmentSources.length) return new THREE.Vector3(1, 0, 0);
    const point = vecFromArray(pointArr);
    let bestDistance = Infinity;
    let bestDirection = segmentSources[0].direction.clone();

    segmentSources.forEach(source => {
        const segment = new THREE.Vector3().subVectors(source.end, source.start);
        const lengthSq = segment.lengthSq();
        if (lengthSq < 0.000001) return;
        const t = THREE.MathUtils.clamp(
            new THREE.Vector3().subVectors(point, source.start).dot(segment) / lengthSq,
            0,
            1
        );
        const closestPoint = source.start.clone().add(segment.multiplyScalar(t));
        const distanceSq = point.distanceToSquared(closestPoint);
        if (distanceSq < bestDistance) {
            bestDistance = distanceSq;
            bestDirection = source.direction.clone();
        }
    });

    return bestDirection;
}

function getItemDirection(item) {
    if (item.start && item.end) {
        return getSegmentDirection(item.start, item.end);
    }
    if (item.point) {
        return findNearestDirection(item.point);
    }
    return new THREE.Vector3(1, 0, 0);
}

function getHorizontalPerpendicular(direction) {
    const side = new THREE.Vector3(-direction.z, 0, direction.x);
    if (side.lengthSq() < 0.000001) {
        return new THREE.Vector3(0, 0, 1);
    }
    return side.normalize();
}

function addOrientedCylinderAt(pointArr, direction, radius, length, color, item, selectGroup, options = {}) {
    const geometry = new THREE.CylinderGeometry(radius, radius, length, 12);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    orientObjectToDirection(mesh, direction);
    return addStandaloneMesh(mesh, item, selectGroup, options);
}

function addOrientedConeAt(pointArr, direction, radius, length, color, item, selectGroup, options = {}) {
    const geometry = new THREE.ConeGeometry(radius, length, 14);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    orientObjectToDirection(mesh, direction);
    return addStandaloneMesh(mesh, item, selectGroup, options);
}

function addOrientedBoxAt(pointArr, direction, width, height, depth, color, item, selectGroup, options = {}) {
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    orientObjectToDirection(mesh, direction);
    return addStandaloneMesh(mesh, item, selectGroup, options);
}

function addOctahedronAt(pointArr, color, size, item, selectGroup, options = {}) {
    const geometry = new THREE.OctahedronGeometry(size);
    const material = new THREE.MeshStandardMaterial({ color, flatShading: true });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    return addStandaloneMesh(mesh, item, selectGroup, options);
}

function safeRenderEnhancement(name, item, fn) {
    try {
        fn();
    } catch (error) {
        console.error(`[idfviewer] ${name} enhancement failed`, item, error);
    }
}

// Calculate dynamic geometry sizing to prevent support cubes swallowing pipelines when scaling varies drastically
let pipeLengths = [];
(sceneData.pipes || []).forEach(p => {
    const dx = p.end[0] - p.start[0], dy = p.end[1] - p.start[1], dz = p.end[2] - p.start[2];
    const len = Math.sqrt(dx*dx + dy*dy + dz*dz);
    if (len > 0.0001) pipeLengths.push(len);
});
(sceneData.fittings || []).forEach(p => {
    const dx = p.end[0] - p.start[0], dy = p.end[1] - p.start[1], dz = p.end[2] - p.start[2];
    const len = Math.sqrt(dx*dx + dy*dy + dz*dz);
    if (len > 0.0001) pipeLengths.push(len);
});

pipeLengths.sort((a,b) => a - b);
const medianLength = pipeLengths.length > 0 ? pipeLengths[Math.floor(pipeLengths.length / 2)] : 25;
let baseRadius = medianLength * 0.03; 
if (baseRadius === 0) baseRadius = 0.7; // Fallback

const sizes = {
    pipeRad: baseRadius,
    fittingRad: baseRadius * 1.4,
    fittingGlandRad: baseRadius * 2.1,
    weldRad: baseRadius * 2.1,
    supportSize: baseRadius * 4.5,
    supportStem: baseRadius * 4.2,
    supportPlate: baseRadius * 7.5,
    supportFrameWidth: baseRadius * 6.5,
    markerRad: baseRadius * 2.5,
    arrowShaft: baseRadius * 0.8,
    arrowLength: baseRadius * 9,
    labelLift: baseRadius * 7,
    labelScale: baseRadius * 10
};

function clampLabelText(text, maxChars = 30) {
    const normalized = (text || "").replace(/\s+/g, " ").trim();
    if (!normalized) return "";
    return normalized.length > maxChars ? normalized.slice(0, maxChars - 1) + "…" : normalized;
}

function getContextLabelText(item) {
    const props = getItemProperties(item);
    if (getSourceFormat(item) === "IFC") return "";
    if (props.notes && props.notes.length) return clampLabelText(props.notes[0], 34);
    if (item.kind === "Support") return clampLabelText(props.support_code || props.inline_code, 22);
    if (item.kind === "Marker") return clampLabelText(props.inline_code || props.component_ref, 16);
    if (props.kind === "Valve" || props.kind === "Flange") return clampLabelText(props.component_ref, 22);
    return "";
}

function createTextSprite(text, tone = {}) {
    const label = clampLabelText(text);
    if (!label) return null;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    const fontSize = 34;
    const paddingX = 22;
    const paddingY = 12;
    ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
    const textWidth = Math.ceil(ctx.measureText(label).width);
    canvas.width = textWidth + paddingX * 2;
    canvas.height = fontSize + paddingY * 2;

    ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
    ctx.fillStyle = tone.background || 'rgba(255,255,255,0.92)';
    ctx.strokeStyle = tone.border || 'rgba(148,163,184,0.65)';
    ctx.lineWidth = 2;

    const radius = 12;
    const x = 1;
    const y = 1;
    const width = canvas.width - 2;
    const height = canvas.height - 2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = tone.text || '#1e293b';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, paddingX, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        depthWrite: false,
        depthTest: true,
    });
    const sprite = new THREE.Sprite(material);
    const aspect = canvas.width / canvas.height;
    sprite.scale.set(sizes.labelScale * aspect, sizes.labelScale, 1);
    return sprite;
}

function addContextLabel(item, pointArr, text, tone = {}) {
    const sprite = createTextSprite(text, tone);
    if (!sprite) return;
    sprite.position.copy(vecFromArray(pointArr)).add(new THREE.Vector3(0, sizes.labelLift, 0));
    sprite.userData.leafKey = getHierarchyLeafKey(item);
    sprite.userData.visibilityKey = getItemVisibilityKey(item);
    modelGroup.add(sprite);
    contextLabels.push(sprite);
}

function createScaleLabelSprite(text, { accent = false, labelHeight = 0.5 } = {}) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const fontSize = 24;
    const paddingX = 12;
    const paddingY = 7;
    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    const width = Math.ceil(ctx.measureText(text).width + paddingX * 2);
    const height = fontSize + paddingY * 2;
    canvas.width = Math.max(width, 56);
    canvas.height = height;

    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    ctx.textBaseline = 'middle';
    ctx.fillStyle = accent ? 'rgba(15, 23, 42, 0.86)' : 'rgba(255, 255, 255, 0.86)';
    ctx.strokeStyle = accent ? 'rgba(15, 23, 42, 0.24)' : 'rgba(148, 163, 184, 0.45)';
    ctx.lineWidth = 2;

    const radius = 8;
    const x = 1;
    const y = 1;
    const rectWidth = canvas.width - 2;
    const rectHeight = canvas.height - 2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + rectWidth - radius, y);
    ctx.quadraticCurveTo(x + rectWidth, y, x + rectWidth, y + radius);
    ctx.lineTo(x + rectWidth, y + rectHeight - radius);
    ctx.quadraticCurveTo(x + rectWidth, y + rectHeight, x + rectWidth - radius, y + rectHeight);
    ctx.lineTo(x + radius, y + rectHeight);
    ctx.quadraticCurveTo(x, y + rectHeight, x, y + rectHeight - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = accent ? '#ffffff' : '#334155';
    ctx.fillText(text, paddingX, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        depthTest: false,
        depthWrite: false,
    });
    const sprite = new THREE.Sprite(material);
    const aspect = canvas.width / canvas.height;
    const safeLabelHeight = Math.max(Number(labelHeight || 0.5), 0.2);
    sprite.scale.set(safeLabelHeight * aspect, safeLabelHeight, 1);
    sprite.renderOrder = 8;
    return sprite;
}

function clearGridScaleLabels() {
    while (gridScaleLabels.length) {
        const label = gridScaleLabels.pop();
        scene.remove(label);
        if (label.material && label.material.map) {
            label.material.map.dispose();
        }
        if (label.material) {
            label.material.dispose();
        }
    }
}

function niceGridStepForExtent(extent, targetTicks = 10) {
    const rawStep = Math.max(extent / targetTicks, 0.001);
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const normalized = rawStep / magnitude;
    const multiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return multiplier * magnitude;
}

function gridLayoutForExtent(extent) {
    const sourceFormat = String((sceneData.stats || {}).source_format || "").toUpperCase();
    const isPipelineSource = sourceFormat === "PCF" || sourceFormat === "IDF";
    const minimumGridSize = isPipelineSource ? 30 : 0.1;
    const reviewMultiplier = isPipelineSource ? 4 : 1.5;
    const targetTicks = isPipelineSource ? 30 : 16;
    const paddedExtent = Math.max(extent * reviewMultiplier, minimumGridSize);
    const step = niceGridStepForExtent(paddedExtent, targetTicks);
    const divisions = Math.max(2, Math.min(80, Math.ceil(paddedExtent / step)));
    const evenDivisions = divisions % 2 === 0 ? divisions : divisions + 1;
    return {
        size: step * evenDivisions,
        step,
        divisions: evenDivisions,
    };
}

function displayDistance(value) {
    const unit = (sceneData.stats || {}).display_unit || 'm';
    const absValue = Math.abs(value);
    let decimals = 0;
    if (absValue < 1) {
        decimals = 3;
    } else if (absValue < 10) {
        decimals = 2;
    } else if (absValue < 100) {
        decimals = 1;
    }
    return `${value.toFixed(decimals)} ${unit}`;
}

function sceneCoordinateStats() {
    const stats = sceneData.stats || {};
    return {
        coordinateUnit: stats.coordinate_unit || "unknown",
        scaleToM: Number(stats.coordinate_scale_to_m || stats.scale_factor || 1),
        displayUnit: stats.display_unit || "m",
        confidence: stats.unit_confidence || "unknown",
        sourceFormat: stats.source_format || "Scene",
    };
}

function formatSceneLength(value) {
    return displayDistance(value);
}

function formatCompactNumber(value, maxDecimals = 6) {
    if (!Number.isFinite(value)) return "";
    return Number(value.toFixed(maxDecimals)).toString();
}

function updateUnitBadge(gridStep = null) {
    if (!viewerUnitBadge) return;
    const unitStats = sceneCoordinateStats();
    const confidenceTone = unitStats.confidence === "declared"
        ? "text-emerald-700"
        : unitStats.confidence === "fallback" || unitStats.confidence === "mixed_or_missing"
            ? "text-amber-700"
            : "text-slate-600";
    const scaleText = Number.isFinite(unitStats.scaleToM)
        ? `${formatCompactNumber(unitStats.scaleToM)} m per ${unitStats.coordinateUnit}`
        : "scale unknown";
    const gridText = gridStep ? `Grid step ${formatSceneLength(gridStep)}` : "Grid step pending";
    viewerUnitBadge.innerHTML = `
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span class="font-semibold text-slate-800">${escapeHtml(unitStats.sourceFormat)}</span>
            <span>${escapeHtml(unitStats.coordinateUnit)} -> ${escapeHtml(unitStats.displayUnit)}</span>
            <span class="${confidenceTone}">${escapeHtml(unitStats.confidence)}</span>
        </div>
        <div class="mt-1 text-[10px] text-slate-500">${escapeHtml(scaleText)} | ${escapeHtml(gridText)}</div>
    `;
}

function addGridScaleLabel(text, x, y, z, options = {}) {
    const label = createScaleLabelSprite(text, options);
    if (!label) return;
    label.position.set(x, y, z);
    gridScaleLabels.push(label);
    scene.add(label);
}

function updateGridScaleLabels(center, gridDim, baseY, gridStep = null) {
    lastGridScaleState = {
        center: center.clone ? center.clone() : new THREE.Vector3(center.x, center.y, center.z),
        gridDim,
        baseY,
        gridStep,
    };
    updateUnitBadge(gridStep || niceGridStepForExtent(gridDim));
    clearGridScaleLabels();
}

function disposeThreeObject(object) {
    if (!object) return;
    scene.remove(object);
    modelGroup.remove(object);
    if (object.geometry) {
        object.geometry.dispose();
    }
    if (object.material) {
        if (Array.isArray(object.material)) {
            object.material.forEach(material => {
                if (material.map) material.map.dispose();
                material.dispose();
            });
        } else {
            if (object.material.map) object.material.map.dispose();
            object.material.dispose();
        }
    }
}

function clearMeasurementGraphics() {
    while (measurementObjects.length) {
        disposeThreeObject(measurementObjects.pop());
    }
}

function clearMeasurementPreview() {
    hoveredSnapKey = "";
    while (measurementPreviewObjects.length) {
        disposeThreeObject(measurementPreviewObjects.pop());
    }
}

function setMeasurementStatus(html) {
    if (!measurementStatus) return;
    measurementStatus.innerHTML = html;
}

function setMeasurementHudVisible(visible) {
    if (!measurementHud) return;
    measurementHud.classList.toggle('hidden', !visible);
}

function measurementPointLabel(item, role) {
    const props = getItemProperties(item);
    const ref = props.component_ref || props.pipeline_ref || props.support_code || props.inline_code || props.uid || item.kind || "Point";
    return `${ref} ${role}`.trim();
}

function addMeasurementSnapCandidate(item, pointArr, role) {
    if (!Array.isArray(pointArr) || pointArr.length < 3) return;
    const position = vecFromArray(pointArr);
    if (!Number.isFinite(position.x) || !Number.isFinite(position.y) || !Number.isFinite(position.z)) return;
    measurementSnapCandidates.push({
        item,
        role,
        position,
        leafKey: getHierarchyLeafKey(item),
        visibilityKey: getItemVisibilityKey(item),
        label: measurementPointLabel(item, role),
    });
}

function rebuildMeasurementSnapCandidates() {
    measurementSnapCandidates = [];
    [...(sceneData.pipes || []), ...(sceneData.fittings || [])].forEach(item => {
        addMeasurementSnapCandidate(item, item.start, "start");
        addMeasurementSnapCandidate(item, item.end, "end");
    });
    [...(sceneData.welds || []), ...(sceneData.supports || []), ...(sceneData.markers || [])].forEach(item => {
        addMeasurementSnapCandidate(item, item.point, "point");
    });
}

function isSnapCandidateVisible(candidate) {
    if (manuallyHiddenItems.has(candidate.visibilityKey)) return false;
    const representative = leafRepresentatives.get(candidate.leafKey);
    return !representative || Boolean(representative.visible && representative.parent);
}

function findSnapCandidateFromEvent(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    const projected = new THREE.Vector3();
    let best = null;
    const snapThresholdPx = 30;

    measurementSnapCandidates.forEach(candidate => {
        if (!isSnapCandidateVisible(candidate)) return;
        projected.copy(candidate.position).project(camera);
        if (projected.z < -1 || projected.z > 1) return;
        const screenX = (projected.x * 0.5 + 0.5) * rect.width;
        const screenY = (-projected.y * 0.5 + 0.5) * rect.height;
        const distancePx = Math.hypot(pointerX - screenX, pointerY - screenY);
        if (distancePx <= snapThresholdPx && (!best || distancePx < best.distancePx)) {
            best = { ...candidate, distancePx };
        }
    });

    return best;
}

function snapCandidateKey(candidate) {
    if (!candidate) return "";
    const p = candidate.position;
    return `${candidate.visibilityKey}|${candidate.role}|${p.x.toFixed(5)}|${p.y.toFixed(5)}|${p.z.toFixed(5)}`;
}

function addMeasurementPreviewMarker(candidate) {
    const outerRadius = THREE.MathUtils.clamp(sizes.pipeRad * 3.2, 0.012, 0.06);
    const innerRadius = THREE.MathUtils.clamp(outerRadius * 0.2, 0.003, 0.012);
    const geometry = new THREE.TorusGeometry(outerRadius, innerRadius, 18, 36);
    const material = new THREE.MeshBasicMaterial({
        color: 0xfb923c,
        transparent: true,
        opacity: 0.82,
        depthTest: false,
    });
    const marker = new THREE.Mesh(geometry, material);
    marker.position.copy(candidate.position);
    marker.lookAt(camera.position);
    marker.renderOrder = 24;
    scene.add(marker);
    measurementPreviewObjects.push(marker);
}

function addMeasurementPreviewLabel(candidate) {
    const label = createMeasurementLabelSprite(
        `Snap: ${candidate.label}`,
        THREE.MathUtils.clamp(sizes.labelScale * 0.055, 0.075, 0.14)
    );
    if (!label) return;
    const lift = THREE.MathUtils.clamp(sizes.labelLift * 0.16, 0.08, 0.24);
    label.position.copy(candidate.position).add(new THREE.Vector3(0, lift, 0));
    label.material.opacity = 0.78;
    label.renderOrder = 25;
    scene.add(label);
    measurementPreviewObjects.push(label);
}

function renderMeasurementPreview(candidate) {
    const nextKey = snapCandidateKey(candidate);
    if (nextKey === hoveredSnapKey) return;
    clearMeasurementPreview();
    if (!candidate) return;
    hoveredSnapKey = nextKey;
    addMeasurementPreviewMarker(candidate);
    addMeasurementPreviewLabel(candidate);
}

function updateMeasurementPreview(event) {
    if (!measureModeActive) {
        clearMeasurementPreview();
        return;
    }
    renderMeasurementPreview(findSnapCandidateFromEvent(event));
}

function addMeasurementMarker(point) {
    const radius = THREE.MathUtils.clamp(sizes.pipeRad * 2.4, 0.008, 0.045);
    const geometry = new THREE.SphereGeometry(radius, 18, 18);
    const material = new THREE.MeshBasicMaterial({
        color: 0xf97316,
        depthTest: false,
    });
    const marker = new THREE.Mesh(geometry, material);
    marker.position.copy(point);
    marker.renderOrder = 20;
    scene.add(marker);
    measurementObjects.push(marker);
}

function addMeasurementLine(start, end) {
    const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
    const material = new THREE.LineBasicMaterial({
        color: 0xf97316,
        depthTest: false,
        linewidth: 2,
    });
    const line = new THREE.Line(geometry, material);
    line.renderOrder = 19;
    scene.add(line);
    measurementObjects.push(line);
}

function createMeasurementLabelSprite(text, labelHeight) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const fontSize = 20;
    const paddingX = 10;
    const paddingY = 5;
    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    const width = Math.ceil(ctx.measureText(text).width + paddingX * 2);
    canvas.width = Math.max(width, 50);
    canvas.height = fontSize + paddingY * 2;

    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(255, 247, 237, 0.84)';
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.38)';
    ctx.lineWidth = 1.5;

    const radius = 7;
    const x = 1;
    const y = 1;
    const rectWidth = canvas.width - 2;
    const rectHeight = canvas.height - 2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + rectWidth - radius, y);
    ctx.quadraticCurveTo(x + rectWidth, y, x + rectWidth, y + radius);
    ctx.lineTo(x + rectWidth, y + rectHeight - radius);
    ctx.quadraticCurveTo(x + rectWidth, y + rectHeight, x + rectWidth - radius, y + rectHeight);
    ctx.lineTo(x + radius, y + rectHeight);
    ctx.quadraticCurveTo(x, y + rectHeight, x, y + rectHeight - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#9a3412';
    ctx.fillText(text, paddingX, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.9,
        depthTest: false,
        depthWrite: false,
    });
    const sprite = new THREE.Sprite(material);
    const aspect = canvas.width / canvas.height;
    const safeLabelHeight = Math.max(Number(labelHeight || 0.12), 0.08);
    sprite.scale.set(safeLabelHeight * aspect, safeLabelHeight, 1);
    sprite.renderOrder = 21;
    return sprite;
}

function addMeasurementLabel(start, end, text) {
    const label = createMeasurementLabelSprite(text, THREE.MathUtils.clamp(sizes.labelScale * 0.08, 0.08, 0.18));
    if (!label) return;
    const midpoint = start.clone().add(end).multiplyScalar(0.5);
    const lift = THREE.MathUtils.clamp(sizes.labelLift * 0.18, 0.08, 0.28);
    label.position.copy(midpoint).add(new THREE.Vector3(0, lift, 0));
    label.renderOrder = 21;
    scene.add(label);
    measurementObjects.push(label);
}

function ehtStatus(message) {
    if (ehtToolStatus) {
        ehtToolStatus.textContent = message;
    }
}

function markEhtLayerDirty() {
    ehtLayerDirty = true;
    if (ehtSaveLayerBtn) {
        ehtSaveLayerBtn.textContent = "Save EHT Layer *";
        ehtSaveLayerBtn.classList.add('bg-amber-600', 'hover:bg-amber-500');
        ehtSaveLayerBtn.classList.remove('bg-slate-800', 'hover:bg-slate-700');
    }
}

function markEhtLayerClean() {
    ehtLayerDirty = false;
    if (ehtSaveLayerBtn) {
        ehtSaveLayerBtn.textContent = "Save EHT Layer";
        ehtSaveLayerBtn.classList.remove('bg-amber-600', 'hover:bg-amber-500');
        ehtSaveLayerBtn.classList.add('bg-slate-800', 'hover:bg-slate-700');
    }
}

function clearEhtRoutePreview() {
    while (ehtRoutePreviewObjects.length) {
        disposeThreeObject(ehtRoutePreviewObjects.pop());
    }
}

function clearEhtPlacementPreview() {
    hoveredEhtPlacementKey = "";
    while (ehtPlacementPreviewObjects.length) {
        disposeThreeObject(ehtPlacementPreviewObjects.pop());
    }
}

function ehtPlacementPreviewKey(candidate) {
    if (!candidate || !candidate.point) return "";
    return [
        activeEhtTool || "edit",
        pendingEhtGeometryEdit ? `${pendingEhtGeometryEdit.action}:${pendingEhtGeometryEdit.vertexIndex}` : "place",
        pendingEhtRoutePoints.length,
        candidate.snapLabel || "grid",
        candidate.point.x.toFixed(4),
        candidate.point.y.toFixed(4),
        candidate.point.z.toFixed(4),
    ].join("|");
}

function getEhtPlacementCandidateFromEvent(event) {
    const snapped = findSnapCandidateFromEvent(event);
    if (snapped) {
        return {
            point: snapped.position.clone(),
            snapLabel: snapped.label,
            snapped: true,
        };
    }

    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const planeY = gridHelper ? gridHelper.position.y : 0;
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -planeY);
    const point = new THREE.Vector3();
    if (!raycaster.ray.intersectPlane(plane, point)) return null;
    return { point, snapLabel: "Grid point", snapped: false };
}

function addEhtPlacementPreviewMarker(candidate) {
    const def = activeEhtToolDef();
    const color = def ? def.color : 0xf59e0b;
    const radius = THREE.MathUtils.clamp(sizes.pipeRad * 2.2, 0.008, 0.045);
    const geometry = new THREE.SphereGeometry(radius, 18, 18);
    const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: candidate.snapped ? 0.95 : 0.58,
        depthTest: false,
    });
    const marker = new THREE.Mesh(geometry, material);
    marker.position.copy(candidate.point);
    marker.renderOrder = 26;
    scene.add(marker);
    ehtPlacementPreviewObjects.push(marker);
}

function addEhtPlacementPreviewLine(candidate) {
    if (!pendingEhtRoutePoints.length) return;
    const def = activeEhtToolDef();
    if (!def || def.geometry_type !== "polyline") return;
    const last = pendingEhtRoutePoints[pendingEhtRoutePoints.length - 1];
    const geometry = new THREE.BufferGeometry().setFromPoints([last, candidate.point]);
    const material = new THREE.LineBasicMaterial({
        color: def.color,
        transparent: true,
        opacity: 0.42,
        depthTest: false,
    });
    const line = new THREE.Line(geometry, material);
    line.renderOrder = 24;
    scene.add(line);
    ehtPlacementPreviewObjects.push(line);
}

function addEhtPlacementPreviewLabel(candidate) {
    const def = activeEhtToolDef();
    const baseLabel = candidate.snapped ? `Snap: ${candidate.snapLabel}` : "Grid point";
    const nextLength = pendingEhtRoutePoints.length
        ? pendingEhtRoutePoints[pendingEhtRoutePoints.length - 1].distanceTo(candidate.point)
        : 0;
    const sourceElement = findEhtElement(routeStartElementUid);
    const target = sourceElement
        ? findNearestEhtElementToPoint(candidate.point, { excludeUid: sourceElement.element_uid, maxDistance: THREE.MathUtils.clamp(sizes.pipeRad * 28, 0.12, 1.2) })
        : null;
    const routeText = def && def.geometry_type === "polyline" && pendingEhtRoutePoints.length
        ? ` | leg ${formatSceneLength(nextLength)}`
        : "";
    const targetText = target ? ` | target ${getEhtElementLabel(target.element)}` : "";
    const label = createMeasurementLabelSprite(
        `${baseLabel}${routeText}${targetText}`,
        THREE.MathUtils.clamp(sizes.labelScale * 0.055, 0.075, 0.14)
    );
    if (!label) return;
    const lift = THREE.MathUtils.clamp(sizes.labelLift * 0.16, 0.08, 0.24);
    label.position.copy(candidate.point).add(new THREE.Vector3(0, lift, 0));
    label.material.opacity = 0.76;
    label.renderOrder = 27;
    scene.add(label);
    ehtPlacementPreviewObjects.push(label);
}

function addEhtConnectionTargetPreview(candidate) {
    const sourceElement = findEhtElement(routeStartElementUid);
    if (!sourceElement || !pendingEhtRoutePoints.length) return;
    const target = findNearestEhtElementToPoint(candidate.point, {
        excludeUid: sourceElement.element_uid,
        maxDistance: THREE.MathUtils.clamp(sizes.pipeRad * 28, 0.12, 1.2),
    });
    if (!target) return;

    const anchor = getEhtElementAnchorPoint(target.element);
    if (!anchor) return;
    const radius = THREE.MathUtils.clamp(sizes.pipeRad * 5.2, 0.04, 0.12);
    const geometry = new THREE.RingGeometry(radius * 0.7, radius, 28);
    const material = new THREE.MeshBasicMaterial({
        color: 0x22c55e,
        transparent: true,
        opacity: 0.72,
        depthTest: false,
        side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(geometry, material);
    ring.position.copy(anchor);
    ring.lookAt(camera.position);
    ring.renderOrder = 28;
    scene.add(ring);
    ehtPlacementPreviewObjects.push(ring);

    const label = createEhtLabelSprite(
        `Target: ${getEhtElementLabel(target.element)}`,
        THREE.MathUtils.clamp(sizes.labelScale * 0.045, 0.055, 0.095)
    );
    if (!label) return;
    const lift = THREE.MathUtils.clamp(sizes.labelLift * 0.2, 0.08, 0.24);
    label.position.copy(anchor).add(new THREE.Vector3(0, lift, 0));
    label.material.opacity = 0.82;
    label.renderOrder = 29;
    scene.add(label);
    ehtPlacementPreviewObjects.push(label);
}

function renderEhtPlacementPreview(candidate) {
    const key = ehtPlacementPreviewKey(candidate);
    if (key === hoveredEhtPlacementKey) return;
    clearEhtPlacementPreview();
    if (!candidate) return;
    hoveredEhtPlacementKey = key;
    addEhtPlacementPreviewLine(candidate);
    addEhtPlacementPreviewMarker(candidate);
    addEhtPlacementPreviewLabel(candidate);
    addEhtConnectionTargetPreview(candidate);
}

function updateEhtPlacementPreview(event) {
    if (measureModeActive || (!activeEhtTool && !pendingEhtGeometryEdit)) {
        clearEhtPlacementPreview();
        return;
    }
    renderEhtPlacementPreview(getEhtPlacementCandidateFromEvent(event));
}

function renderEhtRoutePreview() {
    clearEhtRoutePreview();
    const def = activeEhtToolDef();
    if (!def || def.geometry_type !== "polyline" || !pendingEhtRoutePoints.length) {
        return;
    }

    pendingEhtRoutePoints.forEach(point => {
        const geometry = new THREE.SphereGeometry(THREE.MathUtils.clamp(sizes.pipeRad * 1.8, 0.006, 0.035), 14, 14);
        const material = new THREE.MeshBasicMaterial({ color: def.color, depthTest: false });
        const marker = new THREE.Mesh(geometry, material);
        marker.position.copy(point);
        marker.renderOrder = 22;
        scene.add(marker);
        ehtRoutePreviewObjects.push(marker);
    });

    if (pendingEhtRoutePoints.length < 2) return;
    const geometry = new THREE.BufferGeometry().setFromPoints(pendingEhtRoutePoints);
    const material = new THREE.LineBasicMaterial({
        color: def.color,
        transparent: true,
        opacity: 0.72,
        depthTest: false,
    });
    const line = new THREE.Line(geometry, material);
    line.renderOrder = 21;
    scene.add(line);
    ehtRoutePreviewObjects.push(line);
}

function setEhtRouteControlsVisible(visible) {
    if (ehtRouteControls) {
        ehtRouteControls.classList.toggle('hidden', !visible);
    }
}

function cancelPendingEhtRoute({ updateStatus = true } = {}) {
    pendingEhtRoutePoints = [];
    routeStartElementUid = "";
    clearEhtRoutePreview();
    clearEhtPlacementPreview();
    setEhtRouteControlsVisible(false);
    if (updateStatus) {
        const def = activeEhtToolDef();
        ehtStatus(def ? `${def.label}: click to start route.` : "Select or edit EHT elements.");
    }
}

function routePreviewLength() {
    if (pendingEhtRoutePoints.length < 2) return 0;
    return pendingEhtRoutePoints.reduce((total, point, index) => {
        if (index === 0) return total;
        return total + point.distanceTo(pendingEhtRoutePoints[index - 1]);
    }, 0);
}

function pointsRouteLength(points) {
    if (!Array.isArray(points) || points.length < 2) return 0;
    return points.reduce((total, point, index) => {
        if (index === 0) return total;
        const current = point instanceof THREE.Vector3 ? point : vecFromArray(point);
        const previous = points[index - 1] instanceof THREE.Vector3 ? points[index - 1] : vecFromArray(points[index - 1]);
        return total + current.distanceTo(previous);
    }, 0);
}

function activeEhtToolDef() {
    return activeEhtTool ? getEhtDef(activeEhtTool) : null;
}

function setActiveEhtTool(tool) {
    if (tool && measureModeActive) {
        setMeasureMode(false);
    }
    if (tool && pendingEhtGeometryEdit) {
        cancelPendingEhtGeometryEdit({ updateStatus: false });
    }
    activeEhtTool = tool || "";
    cancelPendingEhtRoute({ updateStatus: false });
    clearEhtPlacementPreview();
    document.querySelectorAll('.eht-tool-btn').forEach(button => {
        const isActive = button.dataset.ehtTool === activeEhtTool;
        button.classList.toggle('ring-2', isActive);
        button.classList.toggle('ring-slate-900', isActive);
    });
    if (ehtSelectToolBtn) {
        ehtSelectToolBtn.classList.toggle('bg-slate-900', !activeEhtTool);
        ehtSelectToolBtn.classList.toggle('text-white', !activeEhtTool);
        ehtSelectToolBtn.classList.toggle('bg-white', Boolean(activeEhtTool));
        ehtSelectToolBtn.classList.toggle('text-slate-700', Boolean(activeEhtTool));
    }
    const def = activeEhtToolDef();
    ehtStatus(def ? `${def.label}: click to ${def.geometry_type === "polyline" ? "start route" : "place"}.` : "Select or edit EHT elements.");
}

function nextEhtUid() {
    if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
    }
    return `eht-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function defaultEhtMetadata(elementType) {
    return Object.fromEntries(
        getEhtDef(elementType).fields.map(field => [field.key, String(field.default || "")])
    );
}

function createEhtElement(elementType, points) {
    const def = getEhtDef(elementType);
    const count = ehtElements.filter(element => element.element_type === elementType).length + 1;
    const geometry = {
        type: def.geometry_type,
        points: points.map(point => [point.x, point.y, point.z]),
    };
    if (def.geometry_type === "polyline") {
        geometry.length_m = Number(pointsRouteLength(points).toFixed(4));
        geometry.segment_count = Math.max(points.length - 1, 0);
        geometry.point_count = points.length;
    }
    return {
        element_uid: nextEhtUid(),
        element_type: elementType,
        label: `${def.label} ${count}`,
        geometry,
        metadata: defaultEhtMetadata(elementType),
    };
}

function updateEhtGeometryMetrics(element) {
    const geometry = element.geometry || {};
    const points = geometry.points || [];
    geometry.point_count = points.length;
    if (geometry.type === "polyline") {
        geometry.length_m = Number(pointsRouteLength(points).toFixed(4));
        geometry.segment_count = Math.max(points.length - 1, 0);
    } else {
        geometry.length_m = 0;
        geometry.segment_count = 0;
    }
    element.geometry = geometry;
}

function formatCoordinateInput(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "0";
    return numeric.toFixed(4).replace(/\.?0+$/, "");
}

function getPointElementCoordinate(element) {
    const points = ((element || {}).geometry || {}).points || [];
    return points.length ? [...points[0]] : [0, 0, 0];
}

function setPointElementCoordinate(element, pointArray) {
    const geometry = element.geometry || {};
    geometry.points = [[
        Number(pointArray[0]) || 0,
        Number(pointArray[1]) || 0,
        Number(pointArray[2]) || 0,
    ]];
    element.geometry = geometry;
    updateEhtGeometryMetrics(element);
    markEhtLayerDirty();
    renderEhtElements();
    renderEhtProperties(element);
}

function applyPointCoordinateInputs(element) {
    const x = Number.parseFloat(document.getElementById('ehtCoordX')?.value || "0");
    const y = Number.parseFloat(document.getElementById('ehtCoordY')?.value || "0");
    const z = Number.parseFloat(document.getElementById('ehtCoordZ')?.value || "0");
    if (![x, y, z].every(Number.isFinite)) {
        ehtStatus("Enter valid X, Y, and Z coordinates.");
        return;
    }
    setPointElementCoordinate(element, [x, y, z]);
    ehtStatus(`${getEhtElementLabel(element)} coordinate updated. Save EHT Layer when ready.`);
}

function nudgePointElement(element, axis, direction) {
    const step = Number.parseFloat(document.getElementById('ehtNudgeStep')?.value || "0.05");
    const safeStep = Number.isFinite(step) && step > 0 ? step : 0.05;
    const point = getPointElementCoordinate(element);
    const axisIndex = { x: 0, y: 1, z: 2 }[axis];
    if (axisIndex === undefined) return;
    point[axisIndex] = Number(point[axisIndex] || 0) + safeStep * direction;
    setPointElementCoordinate(element, point);
    ehtStatus(`${getEhtElementLabel(element)} nudged ${axis.toUpperCase()} ${direction > 0 ? "+" : "-"}${safeStep}. Save EHT Layer when ready.`);
}

function getEhtElementAnchorPoint(element) {
    const points = ((element || {}).geometry || {}).points || [];
    return points.length ? vecFromArray(points[0]) : null;
}

function findNearestEhtElementToPoint(point, { excludeUid = "", maxDistance = null } = {}) {
    if (!point) return null;
    const limit = Number.isFinite(maxDistance)
        ? maxDistance
        : THREE.MathUtils.clamp(sizes.pipeRad * 16, 0.08, 0.65);
    let best = null;
    let bestDistance = Infinity;
    ehtElements.forEach(element => {
        if (excludeUid && element.element_uid === excludeUid) return;
        const anchor = getEhtElementAnchorPoint(element);
        if (!anchor) return;
        const distance = anchor.distanceTo(point);
        if (distance <= limit && distance < bestDistance) {
            best = element;
            bestDistance = distance;
        }
    });
    return best ? { element: best, distance: bestDistance } : null;
}

function startEhtRouteFromElement(element, tool) {
    const point = getEhtElementAnchorPoint(element);
    const def = getEhtDef(tool);
    if (!point || !def || def.geometry_type !== "polyline") return;
    setActiveEhtTool(tool);
    routeStartElementUid = element.element_uid;
    pendingEhtRoutePoints = [point];
    renderEhtRoutePreview();
    setEhtRouteControlsVisible(true);
    ehtStatus(`${def.label}: started from ${getEhtElementLabel(element)}. Pick the next route point.`);
}

function applyRouteConnectionMetadata(element, points, sourceElement) {
    if (!element || !sourceElement) return;
    const metadata = { ...(element.metadata || {}) };
    const sourceLabel = getEhtElementLabel(sourceElement);
    metadata.from_element_uid = sourceElement.element_uid;
    metadata.from_element_type = sourceElement.element_type;
    if (Object.prototype.hasOwnProperty.call(metadata, "from")) {
        metadata.from = sourceLabel;
    }

    const lastPoint = points.length ? points[points.length - 1] : null;
    const target = findNearestEhtElementToPoint(lastPoint, {
        excludeUid: sourceElement.element_uid,
        maxDistance: THREE.MathUtils.clamp(sizes.pipeRad * 28, 0.12, 1.2),
    });
    if (target) {
        metadata.to_element_uid = target.element.element_uid;
        metadata.to_element_type = target.element.element_type;
        if (Object.prototype.hasOwnProperty.call(metadata, "to")) {
            metadata.to = getEhtElementLabel(target.element);
        }
    }
    element.metadata = metadata;
}

function cancelPendingEhtGeometryEdit({ updateStatus = true } = {}) {
    pendingEhtGeometryEdit = null;
    clearEhtPlacementPreview();
    if (updateStatus) {
        ehtStatus("Geometry edit cancelled.");
    }
}

function startEhtGeometryEdit(element, action, vertexIndex = 0) {
    setActiveEhtTool("");
    if (measureModeActive) setMeasureMode(false);
    pendingEhtGeometryEdit = {
        elementUid: element.element_uid,
        action,
        vertexIndex: Number(vertexIndex) || 0,
    };
    const actionLabel = action === "move_element"
        ? "pick the new element position"
        : action === "move_vertex"
            ? `pick the new position for route point ${pendingEhtGeometryEdit.vertexIndex + 1}`
            : `pick the new point to insert after route point ${pendingEhtGeometryEdit.vertexIndex + 1}`;
    ehtStatus(`${element.label || getEhtDef(element.element_type).label}: ${actionLabel}.`);
}

function applyEhtGeometryEditAtPoint(point) {
    if (!pendingEhtGeometryEdit) return false;
    const element = findEhtElement(pendingEhtGeometryEdit.elementUid);
    if (!element) {
        cancelPendingEhtGeometryEdit();
        return true;
    }

    const geometry = element.geometry || {};
    const points = Array.isArray(geometry.points) ? [...geometry.points] : [];
    const pointArray = [point.x, point.y, point.z];
    const vertexIndex = THREE.MathUtils.clamp(pendingEhtGeometryEdit.vertexIndex, 0, Math.max(points.length - 1, 0));

    if (pendingEhtGeometryEdit.action === "move_element") {
        geometry.points = [pointArray];
    } else if (pendingEhtGeometryEdit.action === "move_vertex") {
        if (!points.length) return true;
        points[vertexIndex] = pointArray;
        geometry.points = points;
    } else if (pendingEhtGeometryEdit.action === "add_vertex_after") {
        points.splice(vertexIndex + 1, 0, pointArray);
        geometry.points = points;
    }

    element.geometry = geometry;
    updateEhtGeometryMetrics(element);
    pendingEhtGeometryEdit = null;
    clearEhtPlacementPreview();
    markEhtLayerDirty();
    renderEhtElements();
    renderEhtProperties(element);
    ehtStatus(`${element.label || getEhtDef(element.element_type).label} geometry updated. Save EHT Layer when ready.`);
    return true;
}

function clearEhtObjects() {
    clearEhtHighlight();
    ehtSelectableMeshes.length = 0;
    while (ehtObjects.length) {
        disposeThreeObject(ehtObjects.pop());
    }
}

function registerEhtObject(object, element) {
    object.userData.ehtElementUid = element.element_uid;
    object.userData.ehtElement = element;
    ehtObjects.push(object);
    if (object.isMesh || object.isLine) {
        ehtSelectableMeshes.push(object);
    }
    return object;
}

function createEhtLabelSprite(text, labelHeight) {
    const label = clampLabelText(text, 36);
    if (!label) return null;

    const pixelRatio = 2;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const fontSize = 18;
    const paddingX = 10;
    const paddingY = 5;
    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    const logicalWidth = Math.max(Math.ceil(ctx.measureText(label).width + paddingX * 2), 54);
    const logicalHeight = fontSize + paddingY * 2;
    canvas.width = logicalWidth * pixelRatio;
    canvas.height = logicalHeight * pixelRatio;
    canvas.style.width = `${logicalWidth}px`;
    canvas.style.height = `${logicalHeight}px`;
    ctx.scale(pixelRatio, pixelRatio);

    ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(255,255,255,0.58)';
    ctx.strokeStyle = 'rgba(100,116,139,0.28)';
    ctx.lineWidth = 1;

    const radius = 6;
    const x = 0.5;
    const y = 0.5;
    const rectWidth = logicalWidth - 1;
    const rectHeight = logicalHeight - 1;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + rectWidth - radius, y);
    ctx.quadraticCurveTo(x + rectWidth, y, x + rectWidth, y + radius);
    ctx.lineTo(x + rectWidth, y + rectHeight - radius);
    ctx.quadraticCurveTo(x + rectWidth, y + rectHeight, x + rectWidth - radius, y + rectHeight);
    ctx.lineTo(x + radius, y + rectHeight);
    ctx.quadraticCurveTo(x, y + rectHeight, x, y + rectHeight - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#334155';
    ctx.fillText(label, paddingX, logicalHeight / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.72,
        depthTest: true,
        depthWrite: false,
    });
    const sprite = new THREE.Sprite(material);
    const aspect = logicalWidth / logicalHeight;
    const safeHeight = THREE.MathUtils.clamp(Number(labelHeight || 0.06), 0.04, 0.09);
    sprite.scale.set(safeHeight * aspect, safeHeight, 1);
    sprite.renderOrder = 18;
    return sprite;
}

function addEhtLabel(element, anchor) {
    const label = createEhtLabelSprite(
        element.label || getEhtDef(element.element_type).label,
        THREE.MathUtils.clamp(sizes.labelScale * 0.04, 0.045, 0.085)
    );
    if (!label) return;
    const lift = THREE.MathUtils.clamp(sizes.labelLift * 0.13, 0.06, 0.18);
    label.position.copy(anchor).add(new THREE.Vector3(0, lift, 0));
    label.material.opacity = 0.68;
    label.renderOrder = 18;
    scene.add(label);
    registerEhtObject(label, element);
}

function renderEhtPoint(element, point) {
    const def = getEhtDef(element.element_type);
    const size = THREE.MathUtils.clamp(sizes.pipeRad * 5.5, 0.04, 0.14);
    let geometry;
    if (element.element_type === "distribution_board" || element.element_type === "junction_box") {
        const dimensions = getEhtCuboidDimensions(element);
        geometry = new THREE.BoxGeometry(dimensions.length, dimensions.height, dimensions.width);
    } else if (element.element_type === "isolator") {
        geometry = new THREE.OctahedronGeometry(size * 0.75);
    } else if (element.element_type === "end_termination") {
        geometry = new THREE.ConeGeometry(size * 0.55, size * 1.3, 18);
    } else if (element.element_type === "pipe_strap") {
        geometry = new THREE.TorusGeometry(size * 0.6, size * 0.12, 12, 30);
    } else {
        geometry = new THREE.SphereGeometry(size * 0.55, 18, 18);
    }
    const material = new THREE.MeshStandardMaterial({
        color: def.color,
        roughness: 0.55,
        metalness: 0.05,
    });
    const mesh = new THREE.Mesh(geometry, material);
    if (element.element_type === "distribution_board" || element.element_type === "junction_box") {
        const dimensions = getEhtCuboidDimensions(element);
        mesh.position.set(
            point.x + dimensions.length / 2,
            point.y + dimensions.height / 2,
            point.z + dimensions.width / 2,
        );
    } else {
        mesh.position.copy(point);
    }
    mesh.renderOrder = 16;
    scene.add(mesh);
    registerEhtObject(mesh, element);
    if (element.element_type === "distribution_board" || element.element_type === "junction_box") {
        const dimensions = getEhtCuboidDimensions(element);
        addEhtLabel(element, new THREE.Vector3(point.x + dimensions.length / 2, point.y + dimensions.height, point.z + dimensions.width / 2));
    } else {
        addEhtLabel(element, point);
    }
}

function renderEhtPolyline(element, points) {
    const def = getEhtDef(element.element_type);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({
        color: def.color,
        depthTest: false,
        linewidth: 2,
    });
    const line = new THREE.Line(geometry, material);
    line.renderOrder = 15;
    scene.add(line);
    registerEhtObject(line, element);

    points.forEach(point => {
        const markerGeometry = new THREE.SphereGeometry(THREE.MathUtils.clamp(sizes.pipeRad * 1.8, 0.006, 0.035), 14, 14);
        const markerMaterial = new THREE.MeshBasicMaterial({ color: def.color, depthTest: false });
        const marker = new THREE.Mesh(markerGeometry, markerMaterial);
        marker.position.copy(point);
        marker.renderOrder = 16;
        scene.add(marker);
        registerEhtObject(marker, element);
    });

    const midpoint = points[0].clone().add(points[points.length - 1]).multiplyScalar(0.5);
    addEhtLabel(element, midpoint);
}

function renderEhtElements() {
    clearEhtObjects();
    const availableTypes = new Set(ehtElements.map(element => element.element_type));
    Array.from(knownEhtTypes).forEach(type => {
        if (!availableTypes.has(type)) {
            knownEhtTypes.delete(type);
            visibleEhtTypes.delete(type);
            collapsedEhtTypes.delete(type);
        }
    });
    availableTypes.forEach(type => {
        if (!knownEhtTypes.has(type)) {
            knownEhtTypes.add(type);
            visibleEhtTypes.add(type);
        }
    });
    ehtElements.forEach(element => {
        const points = ((element.geometry || {}).points || []).map(point => vecFromArray(point));
        if (!points.length) return;
        if ((element.geometry || {}).type === "polyline") {
            renderEhtPolyline(element, points);
        } else {
            renderEhtPoint(element, points[0]);
        }
    });
    applyEhtVisibility();
    buildEhtHierarchySection();
    const selected = findEhtElement(selectedEhtElementUid);
    if (selected) {
        applyEhtHighlight(selected);
    }
}

function findEhtElement(uid) {
    return ehtElements.find(element => element.element_uid === uid) || null;
}

function getEhtObjectsForElement(element) {
    if (!element) return [];
    return ehtObjects.filter(object => object.userData.ehtElementUid === element.element_uid);
}

function clearEhtHighlight() {
    selectedEhtObjects.forEach(object => {
        if (object.material) {
            if (object.material.emissive) {
                object.material.emissive.setHex(0x000000);
            }
            if (object.userData.originalColor !== undefined && object.material.color) {
                object.material.color.setHex(object.userData.originalColor);
                object.userData.originalColor = undefined;
            }
            if (object.userData.originalScale) {
                object.scale.copy(object.userData.originalScale);
                object.userData.originalScale = null;
            }
            if (object.userData.originalOpacity !== undefined) {
                object.material.opacity = object.userData.originalOpacity;
                object.material.transparent = object.userData.originalTransparent;
                object.userData.originalOpacity = undefined;
                object.userData.originalTransparent = undefined;
            }
        }
    });
    selectedEhtObjects = [];
}

function applyEhtHighlight(element) {
    clearEhtHighlight();
    selectedEhtObjects = getEhtObjectsForElement(element).filter(object => object.visible && object.parent);
    selectedEhtObjects.forEach(object => {
        if (!object.userData.originalScale) {
            object.userData.originalScale = object.scale.clone();
        }
        if (object.isMesh) {
            object.scale.copy(object.userData.originalScale).multiplyScalar(1.35);
        }
        if (object.material) {
            if (object.material.emissive) {
                object.material.emissive.setHex(0xffb020);
            } else {
                if (object.material.color && object.userData.originalColor === undefined) {
                    object.userData.originalColor = object.material.color.getHex();
                    object.material.color.setHex(0xffb020);
                }
                object.userData.originalOpacity = object.material.opacity;
                object.userData.originalTransparent = object.material.transparent;
                object.material.transparent = true;
                object.material.opacity = Math.min(1, (object.material.opacity || 1) + 0.2);
            }
        }
    });
}

function focusOnEhtElement(element) {
    const objects = getEhtObjectsForElement(element).filter(object => object.visible && object.parent);
    if (!objects.length) return;
    const box = new THREE.Box3();
    box.makeEmpty();
    objects.forEach(object => {
        const objectBox = new THREE.Box3().setFromObject(object);
        box.union(objectBox);
    });
    if (box.isEmpty()) return;
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);
    const radius = Math.max(size.length() * 0.5, 0.5);
    const offset = new THREE.Vector3(1.4, 1.0, 1.2).normalize().multiplyScalar(radius * 5);
    camera.position.copy(center.clone().add(offset));
    camera.near = 0.05;
    camera.far = Math.max(camera.far, radius * 100, 1000);
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.update();
}

function getEhtTypeLabel(elementType) {
    return getEhtDef(elementType).label || elementType;
}

function getEhtElementLabel(element) {
    return element.label || getEhtTypeLabel(element.element_type);
}

function parsePositiveNumber(value, fallback, { min = 0.02, max = 5 } = {}) {
    const parsed = Number.parseFloat(String(value ?? "").replace(/,/g, ""));
    if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
    return THREE.MathUtils.clamp(parsed, min, max);
}

function getEhtCuboidDimensions(element) {
    const metadata = (element || {}).metadata || {};
    const defaults = element.element_type === "distribution_board"
        ? { length: 0.8, width: 0.25, height: 1.0 }
        : { length: 0.35, width: 0.16, height: 0.3 };
    return {
        length: parsePositiveNumber(metadata.length_m, defaults.length, { min: 0.04, max: 6 }),
        width: parsePositiveNumber(metadata.width_m, defaults.width, { min: 0.03, max: 3 }),
        height: parsePositiveNumber(metadata.height_m, defaults.height, { min: 0.04, max: 4 }),
    };
}

function getEhtSearchText(element) {
    const metadataText = Object.values(element.metadata || {}).join(" ");
    return [
        getEhtTypeLabel(element.element_type),
        element.label,
        element.element_uid,
        metadataText,
    ].join(" ").toLowerCase();
}

function isEhtElementVisible(element) {
    const typeVisible = knownEhtTypes.size === 0 || visibleEhtTypes.has(element.element_type);
    return typeVisible && !hiddenEhtUids.has(element.element_uid);
}

function areAllEhtElementsVisible() {
    return ehtElements.length > 0 && ehtElements.every(element => isEhtElementVisible(element));
}

function applyEhtVisibility() {
    ehtObjects.forEach(object => {
        const element = object.userData.ehtElement;
        object.visible = element ? isEhtElementVisible(element) : true;
    });
}

function renderEhtProperties(element) {
    if (!propsContent || !element) return;
    selectedEhtElementUid = element.element_uid;
    clearHighlight();
    selectedGroup = null;
    applyEhtHighlight(element);
    const def = getEhtDef(element.element_type);
    const metadata = element.metadata || {};
    const geometry = element.geometry || {};
    const pointCoordinate = geometry.type !== "polyline" ? getPointElementCoordinate(element) : null;
    const coordinateLabel = element.element_type === "distribution_board" || element.element_type === "junction_box"
        ? "Front-left-lower Coordinate"
        : "Anchor Coordinate";
    const schemaKeys = new Set(def.fields.map(field => field.key));
    const extraFields = Object.keys(metadata)
        .filter(key => !schemaKeys.has(key))
        .map(key => ({ key, label: key.replace(/_/g, " "), type: "textarea" }));
    const rows = [...def.fields, ...extraFields];
    propsContent.innerHTML = `
        <div class="rounded-lg border border-amber-200 bg-amber-50/70 p-4 shadow-sm">
            <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">EHT Design Element</div>
            <div class="mt-2 text-sm font-semibold text-slate-900">${escapeHtml(def.label)}</div>
            ${geometry.type === "polyline" ? `
                <div class="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                    <div class="rounded border border-amber-100 bg-white/75 px-2 py-1.5">
                        <div class="text-[9px] font-semibold uppercase tracking-wide text-slate-400">Route Length</div>
                        <div class="mt-0.5 font-semibold text-slate-800">${escapeHtml(formatSceneLength(Number(geometry.length_m || pointsRouteLength(geometry.points || []))))}</div>
                    </div>
                    <div class="rounded border border-amber-100 bg-white/75 px-2 py-1.5">
                        <div class="text-[9px] font-semibold uppercase tracking-wide text-slate-400">Segments</div>
                        <div class="mt-0.5 font-semibold text-slate-800">${escapeHtml(geometry.segment_count || Math.max((geometry.points || []).length - 1, 0))}</div>
                    </div>
                </div>
                <div class="mt-3 rounded border border-amber-100 bg-white/70 p-3">
                    <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Route Geometry</div>
                    <select id="ehtRoutePointSelect" class="mt-2 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[11px] text-slate-800 outline-none focus:border-slate-400">
                        ${(geometry.points || []).map((point, index) => `
                            <option value="${index}">Point ${index + 1}</option>
                        `).join("")}
                    </select>
                    <div class="mt-2 grid grid-cols-3 gap-1.5">
                        <button id="ehtMoveVertexBtn" type="button" class="rounded border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-medium text-slate-700 shadow-sm hover:bg-slate-50">Move</button>
                        <button id="ehtAddVertexBtn" type="button" class="rounded border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-medium text-slate-700 shadow-sm hover:bg-slate-50">Add After</button>
                        <button id="ehtDeleteVertexBtn" type="button" class="rounded border border-red-200 bg-white px-2 py-1.5 text-[10px] font-medium text-red-700 shadow-sm hover:bg-red-50">Delete</button>
                    </div>
                </div>
            ` : `
                <div class="mt-3 rounded border border-amber-100 bg-white/70 p-3">
                    <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Geometry</div>
                    <button id="ehtMoveElementBtn" type="button" class="mt-2 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[11px] font-medium text-slate-700 shadow-sm hover:bg-slate-50">Move Element</button>
                    <div class="mt-3 border-t border-amber-100 pt-3">
                        <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">${coordinateLabel}</div>
                        <div class="mt-2 grid grid-cols-3 gap-1.5">
                            <label class="block">
                                <span class="text-[9px] font-semibold uppercase text-slate-400">X</span>
                                <input id="ehtCoordX" type="number" step="0.001" class="mt-1 w-full rounded border border-slate-200 bg-white px-1.5 py-1 text-[11px] text-slate-800 outline-none focus:border-slate-400" value="${escapeHtml(formatCoordinateInput(pointCoordinate[0]))}">
                            </label>
                            <label class="block">
                                <span class="text-[9px] font-semibold uppercase text-slate-400">Y</span>
                                <input id="ehtCoordY" type="number" step="0.001" class="mt-1 w-full rounded border border-slate-200 bg-white px-1.5 py-1 text-[11px] text-slate-800 outline-none focus:border-slate-400" value="${escapeHtml(formatCoordinateInput(pointCoordinate[1]))}">
                            </label>
                            <label class="block">
                                <span class="text-[9px] font-semibold uppercase text-slate-400">Z</span>
                                <input id="ehtCoordZ" type="number" step="0.001" class="mt-1 w-full rounded border border-slate-200 bg-white px-1.5 py-1 text-[11px] text-slate-800 outline-none focus:border-slate-400" value="${escapeHtml(formatCoordinateInput(pointCoordinate[2]))}">
                            </label>
                        </div>
                        <button id="ehtApplyCoordBtn" type="button" class="mt-2 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[10px] font-medium text-slate-700 shadow-sm hover:bg-slate-50">Apply Coordinate</button>
                        <div class="mt-3 grid grid-cols-[1fr_2fr] gap-2">
                            <label class="block">
                                <span class="text-[9px] font-semibold uppercase text-slate-400">Step</span>
                                <input id="ehtNudgeStep" type="number" min="0.001" step="0.001" class="mt-1 w-full rounded border border-slate-200 bg-white px-1.5 py-1 text-[11px] text-slate-800 outline-none focus:border-slate-400" value="0.05">
                            </label>
                            <div class="grid grid-cols-3 gap-1">
                                ${["x", "y", "z"].map(axis => `
                                    <div class="grid grid-cols-2 gap-0.5">
                                        <button type="button" class="eht-nudge-btn rounded border border-slate-200 bg-white px-1 py-1 text-[10px] font-medium text-slate-600 shadow-sm hover:bg-slate-50" data-axis="${axis}" data-direction="-1">${axis.toUpperCase()}-</button>
                                        <button type="button" class="eht-nudge-btn rounded border border-slate-200 bg-white px-1 py-1 text-[10px] font-medium text-slate-600 shadow-sm hover:bg-slate-50" data-axis="${axis}" data-direction="1">${axis.toUpperCase()}+</button>
                                    </div>
                                `).join("")}
                            </div>
                        </div>
                    </div>
                </div>
            `}
            ${geometry.type !== "polyline" ? `
                <div class="mt-3 rounded border border-sky-100 bg-white/70 p-3">
                    <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Start Route From Here</div>
                    <div class="mt-2 grid grid-cols-3 gap-1.5">
                        <button type="button" class="eht-start-route-btn rounded border border-sky-200 bg-sky-50 px-2 py-1.5 text-[10px] font-medium text-sky-800 shadow-sm hover:bg-sky-100" data-route-tool="cold_cable">Cold Cable</button>
                        <button type="button" class="eht-start-route-btn rounded border border-amber-200 bg-amber-50 px-2 py-1.5 text-[10px] font-medium text-amber-900 shadow-sm hover:bg-amber-100" data-route-tool="tracer_sr">SR</button>
                        <button type="button" class="eht-start-route-btn rounded border border-orange-200 bg-orange-50 px-2 py-1.5 text-[10px] font-medium text-orange-900 shadow-sm hover:bg-orange-100" data-route-tool="tracer_mi">MI</button>
                    </div>
                </div>
            ` : ""}
            <div class="mt-4 space-y-3">
                <label class="block">
                    <span class="prop-key">Label</span>
                    <input id="ehtEditLabel" class="mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800 outline-none focus:border-slate-400" value="${escapeHtml(element.label || "")}">
                </label>
                ${rows.map(field => {
                    const value = metadata[field.key] || "";
                    const maxLengthAttr = field.max_length ? `maxlength="${Number(field.max_length)}"` : "";
                    if (field.type === "select") {
                        return `
                            <label class="block">
                                <span class="prop-key">${escapeHtml(field.label || field.key)}</span>
                                <select class="eht-metadata-input mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800 outline-none focus:border-slate-400" data-key="${escapeHtml(field.key)}">
                                    ${(field.options || []).map(option => `
                                        <option value="${escapeHtml(option)}" ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>
                                    `).join("")}
                                </select>
                            </label>
                        `;
                    }
                    if (field.type === "number") {
                        return `
                            <label class="block">
                                <span class="prop-key">${escapeHtml(field.label || field.key)}</span>
                                <input type="number" class="eht-metadata-input mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800 outline-none focus:border-slate-400" data-key="${escapeHtml(field.key)}" value="${escapeHtml(value)}" ${maxLengthAttr}>
                            </label>
                        `;
                    }
                    return `
                    <label class="block">
                        <span class="prop-key">${escapeHtml(field.label || field.key)}</span>
                        <textarea class="eht-metadata-input mt-1 w-full rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800 outline-none focus:border-slate-400" data-key="${escapeHtml(field.key)}" rows="${field.type === "textarea" ? 3 : 1}" ${maxLengthAttr}>${escapeHtml(value)}</textarea>
                    </label>
                    `;
                }).join("")}
            </div>
            <div class="mt-4 flex gap-2">
                <button id="ehtApplyEditBtn" type="button" class="flex-1 rounded bg-slate-800 px-3 py-2 text-[11px] font-medium text-white shadow-sm hover:bg-slate-700">Apply</button>
                <button id="ehtFocusElementBtn" type="button" class="rounded border border-slate-200 bg-white px-3 py-2 text-[11px] font-medium text-slate-700 shadow-sm hover:bg-slate-50">Focus</button>
                <button id="ehtDeleteElementBtn" type="button" class="rounded border border-red-200 bg-white px-3 py-2 text-[11px] font-medium text-red-700 shadow-sm hover:bg-red-50">Delete</button>
            </div>
            <div class="mt-3 text-[10px] leading-relaxed text-slate-500">Use Save EHT Layer to persist changes.</div>
        </div>
    `;

    document.getElementById('ehtApplyEditBtn').addEventListener('click', () => {
        element.label = document.getElementById('ehtEditLabel').value.trim();
        element.metadata = {};
        document.querySelectorAll('.eht-metadata-input').forEach(input => {
            element.metadata[input.dataset.key] = input.value.trim();
        });
        markEhtLayerDirty();
        renderEhtElements();
        renderEhtProperties(element);
    });
    document.getElementById('ehtFocusElementBtn').addEventListener('click', () => {
        focusOnEhtElement(element);
    });
    document.getElementById('ehtDeleteElementBtn').addEventListener('click', () => {
        deleteEhtElement(element, { confirmDelete: true });
    });

    const moveElementBtn = document.getElementById('ehtMoveElementBtn');
    if (moveElementBtn) {
        moveElementBtn.addEventListener('click', () => {
            startEhtGeometryEdit(element, 'move_element', 0);
        });
    }

    const applyCoordBtn = document.getElementById('ehtApplyCoordBtn');
    if (applyCoordBtn) {
        applyCoordBtn.addEventListener('click', () => {
            applyPointCoordinateInputs(element);
        });
    }

    document.querySelectorAll('.eht-nudge-btn').forEach(button => {
        button.addEventListener('click', () => {
            nudgePointElement(element, button.dataset.axis, Number(button.dataset.direction || 1));
        });
    });

    document.querySelectorAll('.eht-start-route-btn').forEach(button => {
        button.addEventListener('click', () => {
            startEhtRouteFromElement(element, button.dataset.routeTool || "cold_cable");
        });
    });

    const routePointSelect = document.getElementById('ehtRoutePointSelect');
    const moveVertexBtn = document.getElementById('ehtMoveVertexBtn');
    const addVertexBtn = document.getElementById('ehtAddVertexBtn');
    const deleteVertexBtn = document.getElementById('ehtDeleteVertexBtn');
    if (moveVertexBtn && routePointSelect) {
        moveVertexBtn.addEventListener('click', () => {
            startEhtGeometryEdit(element, 'move_vertex', parseInt(routePointSelect.value || "0", 10));
        });
    }
    if (addVertexBtn && routePointSelect) {
        addVertexBtn.addEventListener('click', () => {
            startEhtGeometryEdit(element, 'add_vertex_after', parseInt(routePointSelect.value || "0", 10));
        });
    }
    if (deleteVertexBtn && routePointSelect) {
        deleteVertexBtn.addEventListener('click', () => {
            const geometry = element.geometry || {};
            const points = Array.isArray(geometry.points) ? [...geometry.points] : [];
            if (points.length <= 2) {
                ehtStatus("A route must keep at least two points.");
                return;
            }
            points.splice(parseInt(routePointSelect.value || "0", 10), 1);
            geometry.points = points;
            element.geometry = geometry;
            updateEhtGeometryMetrics(element);
            markEhtLayerDirty();
            renderEhtElements();
            renderEhtProperties(element);
            ehtStatus(`${element.label || def.label} route point deleted. Save EHT Layer when ready.`);
        });
    }
}

function selectEhtElement(element) {
    clearHighlight();
    selectedGroup = null;
    selectedEhtElementUid = element.element_uid;
    applyEhtHighlight(element);
    renderEhtProperties(element);
}

function isTextEntryTarget(target) {
    if (!target) return false;
    const tagName = String(target.tagName || "").toLowerCase();
    return tagName === "input" || tagName === "textarea" || tagName === "select" || Boolean(target.isContentEditable);
}

function findEhtHitFromEvent(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(ehtSelectableMeshes.filter(object => object.visible && object.parent), false);
    return hits.length ? findEhtElement(hits[0].object.userData.ehtElementUid) : null;
}

function pointFromEhtPlacementEvent(event) {
    const candidate = getEhtPlacementCandidateFromEvent(event);
    return candidate ? candidate.point.clone() : null;
}

function handleEhtPlacementClick(event) {
    const def = activeEhtToolDef();
    if (!def) return false;
    const point = pointFromEhtPlacementEvent(event);
    if (!point) {
        ehtStatus("No placement point found.");
        return true;
    }

    if (def.geometry_type === "polyline") {
        pendingEhtRoutePoints.push(point);
        clearEhtPlacementPreview();
        renderEhtRoutePreview();
        setEhtRouteControlsVisible(true);
        const routeLength = routePreviewLength();
        const lengthText = pendingEhtRoutePoints.length > 1 ? ` Current length ${formatSceneLength(routeLength)}.` : "";
        ehtStatus(`${def.label}: ${pendingEhtRoutePoints.length} point(s). Add more points or finish route.${lengthText}`);
        return true;
    }

    const element = createEhtElement(activeEhtTool, [point]);
    clearEhtPlacementPreview();
    ehtElements.push(element);
    markEhtLayerDirty();
    renderEhtElements();
    renderEhtProperties(element);
    ehtStatus(`${def.label} placed. Save EHT Layer when ready.`);
    return true;
}

function finishPendingEhtRoute() {
    const def = activeEhtToolDef();
    if (!def || def.geometry_type !== "polyline") return;
    if (pendingEhtRoutePoints.length < 2) {
        ehtStatus(`${def.label}: add at least two points before finishing.`);
        return;
    }
    const routePoints = [...pendingEhtRoutePoints];
    const sourceElement = findEhtElement(routeStartElementUid);
    const element = createEhtElement(activeEhtTool, routePoints);
    applyRouteConnectionMetadata(element, routePoints, sourceElement);
    ehtElements.push(element);
    clearEhtPlacementPreview();
    cancelPendingEhtRoute({ updateStatus: false });
    markEhtLayerDirty();
    renderEhtElements();
    renderEhtProperties(element);
    ehtStatus(`${def.label} route placed. Save EHT Layer when ready.`);
}

async function loadEhtLayer() {
    const url = getEhtOverlayUrl();
    if (!url) return;
    try {
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Unable to load EHT layer.");
        }
        applyEhtToolDefinitions(payload.tool_definitions);
        ehtElements = Array.isArray(payload.elements) ? payload.elements : [];
        renderEhtElements();
        markEhtLayerClean();
        ehtStatus(ehtElements.length ? `${ehtElements.length} EHT element(s) loaded.` : "Select a tool, then click the model.");
    } catch (error) {
        ehtStatus(error.message || "Unable to load EHT layer.");
    }
}

async function saveEhtLayer({ successMessage = null, quiet = false } = {}) {
    const url = getEhtOverlayUrl();
    if (!url) return false;
    if (ehtSaveLayerBtn) {
        ehtSaveLayerBtn.disabled = true;
        if (!quiet) {
            ehtSaveLayerBtn.textContent = "Saving...";
        }
    }
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookieValue('csrftoken'),
            },
            body: JSON.stringify({ elements: ehtElements }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Unable to save EHT layer.");
        }
        applyEhtToolDefinitions(payload.tool_definitions);
        ehtElements = Array.isArray(payload.elements) ? payload.elements : ehtElements;
        renderEhtElements();
        markEhtLayerClean();
        ehtStatus(successMessage || `${ehtElements.length} EHT element(s) saved.`);
        if (selectedEhtElementUid) {
            const selected = findEhtElement(selectedEhtElementUid);
            if (selected) renderEhtProperties(selected);
        }
        return true;
    } catch (error) {
        ehtStatus(error.message || "Unable to save EHT layer.");
        markEhtLayerDirty();
        return false;
    } finally {
        if (ehtSaveLayerBtn) {
            ehtSaveLayerBtn.disabled = false;
        }
    }
}

async function deleteEhtElement(element, { confirmDelete = true } = {}) {
    if (!element) return false;
    const label = getEhtElementLabel(element);
    if (confirmDelete && !window.confirm(`Delete ${label} from the EHT layer? This will be saved immediately.`)) {
        return false;
    }

    const previousElements = ehtElements;
    ehtElements = ehtElements.filter(row => row.element_uid !== element.element_uid);
    selectedEhtElementUid = "";
    clearEhtHighlight();
    markEhtLayerDirty();
    renderEhtElements();
    if (propsContent) {
        propsContent.innerHTML = `<div class="text-center text-slate-400 mt-12 text-[12px]">Deleting EHT element...</div>`;
    }
    ehtStatus(`Deleting ${label}...`);

    const saved = await saveEhtLayer({
        successMessage: `${label} deleted from the EHT layer.`,
        quiet: true,
    });
    if (!saved) {
        ehtElements = previousElements;
        renderEhtElements();
        const restored = findEhtElement(element.element_uid);
        if (restored) renderEhtProperties(restored);
        ehtStatus(`Delete failed. ${label} was restored in the viewer.`);
        return false;
    }
    if (propsContent) {
        propsContent.innerHTML = `<div class="text-center text-slate-400 mt-12 text-[12px]">EHT element deleted.</div>`;
    }
    return true;
}

function parseExpectedLengthMeters(item) {
    const props = getItemProperties(item);
    const rawLength = String(props.cut_piece_length || "").trim();
    if (!rawLength) return null;
    const numeric = Number.parseFloat(rawLength.replace(/,/g, ""));
    if (!Number.isFinite(numeric)) return null;
    const unitStats = sceneCoordinateStats();
    return numeric * unitStats.scaleToM;
}

function measurementMismatch(pointA, pointB, measuredLength) {
    if (!pointA || !pointB || pointA.item !== pointB.item) return null;
    const roles = new Set([pointA.role, pointB.role]);
    if (!(roles.has("start") && roles.has("end"))) return null;
    const expectedLength = parseExpectedLengthMeters(pointA.item);
    if (!Number.isFinite(expectedLength) || expectedLength <= 0) return null;
    const delta = measuredLength - expectedLength;
    const tolerance = Math.max(0.005, expectedLength * 0.005);
    return {
        expectedLength,
        delta,
        tolerance,
        isMismatch: Math.abs(delta) > tolerance,
    };
}

function renderMeasurementResult() {
    clearMeasurementGraphics();
    measurementPoints.forEach(point => addMeasurementMarker(point.position));

    if (measurementPoints.length === 0) {
        setMeasurementStatus("Pick the first snap point.");
        return;
    }
    if (measurementPoints.length === 1) {
        setMeasurementStatus(`
            First point: <span class="font-semibold text-slate-900">${escapeHtml(measurementPoints[0].label)}</span><br>
            Pick the second snap point.
        `);
        return;
    }

    const [pointA, pointB] = measurementPoints;
    const measuredLength = pointA.position.distanceTo(pointB.position);
    addMeasurementLine(pointA.position, pointB.position);
    addMeasurementLabel(pointA.position, pointB.position, formatSceneLength(measuredLength));

    const mismatch = measurementMismatch(pointA, pointB, measuredLength);
    let mismatchHtml = `<div class="mt-2 text-slate-500">No file length parameter is available for this picked pair yet.</div>`;
    if (mismatch) {
        mismatchHtml = mismatch.isMismatch
            ? `<div class="mt-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-amber-800">Suspected mismatch: expected ${escapeHtml(formatSceneLength(mismatch.expectedLength))}, delta ${escapeHtml(formatSceneLength(mismatch.delta))}.</div>`
            : `<div class="mt-2 rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-800">Matches file length within ${escapeHtml(formatSceneLength(mismatch.tolerance))} tolerance.</div>`;
    }

    setMeasurementStatus(`
        <div><span class="font-semibold text-slate-900">${escapeHtml(formatSceneLength(measuredLength))}</span></div>
        <div class="mt-1 text-slate-500">${escapeHtml(pointA.label)} -> ${escapeHtml(pointB.label)}</div>
        ${mismatchHtml}
        <div class="mt-2 text-slate-400">Pick another point to start a new measurement.</div>
    `);
}

function handleMeasurementClick(event) {
    const snapped = findSnapCandidateFromEvent(event);
    if (!snapped) {
        setMeasurementStatus("No snap point nearby. Move closer to an endpoint, weld, support, or marker.");
        return;
    }

    clearMeasurementPreview();

    if (measurementPoints.length >= 2) {
        measurementPoints = [];
    }

    measurementPoints.push(snapped);
    renderMeasurementResult();
}

function setMeasureMode(active) {
    if (active && activeEhtTool) {
        setActiveEhtTool("");
    }
    measureModeActive = active;
    if (measureToggleBtn) {
        measureToggleBtn.textContent = active ? "Measuring" : "Measure";
        measureToggleBtn.setAttribute('aria-pressed', active ? 'true' : 'false');
        const removeClasses = active ? MEASURE_INACTIVE_BUTTON_CLASSES : MEASURE_ACTIVE_BUTTON_CLASSES;
        const addClasses = active ? MEASURE_ACTIVE_BUTTON_CLASSES : MEASURE_INACTIVE_BUTTON_CLASSES;
        measureToggleBtn.classList.remove(...removeClasses);
        measureToggleBtn.classList.add(...addClasses);
    }
    controls.enableRotate = !active;
    renderer.domElement.style.cursor = active ? "crosshair" : "";
    setMeasurementHudVisible(active || measurementPoints.length > 0);
    if (!active) {
        clearMeasurementPreview();
    }
    if (active && measurementPoints.length === 0) {
        setMeasurementStatus("Pick the first snap point.");
    }
}

function addFittingAccent(item, selectGroup) {
    const recordId = item.record_id !== undefined
        ? item.record_id
        : (item.properties ? item.properties.record_id : undefined);
    const direction = getItemDirection(item);
    const midpoint = midpointOfSegment(item.start, item.end);

    if (recordId === 130) {
        addOctahedronAt(midpoint, 0x0f766e, sizes.fittingGlandRad * 0.85, item, selectGroup, { richSymbol: true });
        addOrientedBoxAt(
            [midpoint[0], midpoint[1] + sizes.fittingGlandRad * 1.15, midpoint[2]],
            getHorizontalPerpendicular(direction),
            sizes.fittingRad * 0.45,
            sizes.fittingGlandRad * 1.8,
            sizes.fittingRad * 0.45,
            0x134e4a,
            item,
            selectGroup,
            { richSymbol: true }
        );
        return;
    }

    if (recordId === 105 || recordId === 107) {
        addOrientedCylinderAt(
            pointAlongSegment(item.start, item.end, 0.38),
            direction,
            sizes.fittingGlandRad * 0.7,
            sizes.fittingRad * 1.4,
            0x1d4ed8,
            item,
            selectGroup,
            { richSymbol: true }
        );
        addOrientedCylinderAt(
            pointAlongSegment(item.start, item.end, 0.62),
            direction,
            sizes.fittingGlandRad * 0.7,
            sizes.fittingRad * 1.4,
            0x1d4ed8,
            item,
            selectGroup,
            { richSymbol: true }
        );
        return;
    }

    if (recordId === 110) {
        addOrientedCylinderAt(
            midpoint,
            direction,
            sizes.fittingGlandRad * 0.68,
            sizes.fittingRad * 0.55,
            0xf59e0b,
            item,
            selectGroup,
            { richSymbol: true }
        );
        return;
    }

    if (recordId === 115) {
        addCube(midpoint, 0x92400e, sizes.fittingGlandRad * 1.2, item, selectGroup, { richSymbol: true });
        return;
    }
}

function addFlowMarkerSymbol(item, selectGroup) {
    const direction = getItemDirection(item);
    const anchor = vecFromArray(item.point);
    const shaftLength = sizes.arrowLength * 0.6;
    const shaftCenter = anchor.clone().add(direction.clone().multiplyScalar(shaftLength * 0.2));
    const coneCenter = anchor.clone().add(direction.clone().multiplyScalar(shaftLength * 0.75));

    addOrientedCylinderAt(
        [shaftCenter.x, shaftCenter.y, shaftCenter.z],
        direction,
        sizes.arrowShaft,
        shaftLength,
        0xf97316,
        item,
        selectGroup,
        { richSymbol: true }
    );
    addOrientedConeAt(
        [coneCenter.x, coneCenter.y, coneCenter.z],
        direction,
        sizes.markerRad * 1.3,
        sizes.arrowLength * 0.32,
        0xfb923c,
        item,
        selectGroup,
        { richSymbol: true }
    );
}

function addFloorSupportSymbol(item, selectGroup) {
    const direction = getItemDirection(item);
    const anchor = vecFromArray(item.point);
    const platePoint = anchor.clone().add(new THREE.Vector3(0, -sizes.supportStem * 0.45, 0));

    addOrientedCylinderAt(
        [anchor.x, anchor.y - sizes.supportStem * 0.2, anchor.z],
        new THREE.Vector3(0, 1, 0),
        sizes.arrowShaft * 0.85,
        sizes.supportStem * 0.7,
        0x15803d,
        item,
        selectGroup,
        { richSymbol: true }
    );
    addOrientedBoxAt(
        [platePoint.x, platePoint.y, platePoint.z],
        new THREE.Vector3(0, 1, 0),
        sizes.supportPlate,
        sizes.arrowShaft * 1.6,
        sizes.supportPlate * 0.78,
        0x166534,
        item,
        selectGroup,
        { richSymbol: true }
    );
    addOrientedBoxAt(
        [anchor.x, anchor.y - sizes.supportStem * 0.05, anchor.z],
        direction,
        sizes.arrowShaft * 1.2,
        sizes.supportFrameWidth,
        sizes.arrowShaft * 1.2,
        0x22c55e,
        item,
        selectGroup,
        { richSymbol: true }
    );
}

function addNozzleSupportSymbol(item, selectGroup) {
    const direction = getItemDirection(item);
    const side = getHorizontalPerpendicular(direction);
    const anchor = vecFromArray(item.point);
    const halfWidth = sizes.supportFrameWidth * 0.34;
    const topY = anchor.y + sizes.supportStem * 0.26;
    const lowerY = anchor.y - sizes.supportStem * 0.34;

    addOrientedCylinderAt(
        [anchor.x + side.x * halfWidth, (topY + lowerY) / 2, anchor.z + side.z * halfWidth],
        new THREE.Vector3(0, 1, 0),
        sizes.arrowShaft * 0.72,
        topY - lowerY,
        0x15803d,
        item,
        selectGroup,
        { richSymbol: true }
    );
    addOrientedCylinderAt(
        [anchor.x - side.x * halfWidth, (topY + lowerY) / 2, anchor.z - side.z * halfWidth],
        new THREE.Vector3(0, 1, 0),
        sizes.arrowShaft * 0.72,
        topY - lowerY,
        0x15803d,
        item,
        selectGroup,
        { richSymbol: true }
    );
    addOrientedBoxAt(
        [anchor.x, topY, anchor.z],
        side,
        sizes.arrowShaft * 1.1,
        sizes.supportFrameWidth,
        sizes.arrowShaft * 1.1,
        0x22c55e,
        item,
        selectGroup,
        { richSymbol: true }
    );
}

function getCheckedLeafKeys() {
    const leafToggles = hContent ? Array.from(document.querySelectorAll('.leaf-toggle')) : [];
    if (!leafToggles.length) return null;
    return new Set(leafToggles.filter(cb => cb.checked).map(cb => cb.dataset.leafKey));
}

function getActiveIfcClasses() {
    const filters = Array.from(document.querySelectorAll('.ifc-class-filter'));
    if (!filters.length) return null;
    return new Set(filters.filter(cb => cb.checked).map(cb => cb.value));
}

function applyIfcOpacity() {
    const opacity = ifcOpacitySlider ? parseFloat(ifcOpacitySlider.value) : 1.0;
    if (ifcOpacityValue) {
        ifcOpacityValue.textContent = opacity.toFixed(2);
    }

    selectableMeshes.forEach(mesh => {
        if (!mesh.userData || !mesh.userData.item || getSourceFormat(mesh.userData.item) !== "IFC") return;
        if (!mesh.material) return;
        mesh.material.transparent = opacity < 0.999;
        mesh.material.opacity = opacity;
        mesh.material.needsUpdate = true;
    });
}

function applySceneVisibility({ refit = false } = {}) {
    const activeLeafKeys = getCheckedLeafKeys();
    const activeIfcClasses = getActiveIfcClasses();

    selectableMeshes.forEach(mesh => {
        const leafVisible = activeLeafKeys ? activeLeafKeys.has(mesh.userData.leafKey) : true;
        const itemVisible = !manuallyHiddenItems.has(mesh.userData.visibilityKey);
        const richVisible = mesh.userData.isRichSymbol
            ? (richSymbolToggle ? richSymbolToggle.checked : true)
            : true;
        const classVisible = mesh.userData.ifcClass
            ? (!activeIfcClasses || activeIfcClasses.has(mesh.userData.ifcClass))
            : true;
        mesh.visible = leafVisible && itemVisible && richVisible && classVisible;
    });

    contextLabels.forEach(sprite => {
        const leafVisible = activeLeafKeys ? activeLeafKeys.has(sprite.userData.leafKey) : true;
        const itemVisible = !manuallyHiddenItems.has(sprite.userData.visibilityKey);
        const labelVisible = contextLabelToggle ? contextLabelToggle.checked : true;
        sprite.visible = leafVisible && itemVisible && labelVisible;
    });

    applyIfcOpacity();

    if (refit) {
        fitCameraToObject(modelGroup);
    }
}

function addPipe(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, sizes.pipeRad, 0x555555, item, selectGroup);
}

function addFitting(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, sizes.fittingRad, 0x2563eb, item, selectGroup);
    addSphere(midpointOfSegment(item.start, item.end), 0x2563eb, sizes.fittingGlandRad, item, selectGroup);
    safeRenderEnhancement("fitting", item, () => addFittingAccent(item, selectGroup));

    const labelText = getContextLabelText(item);
    if (labelText) {
        safeRenderEnhancement("fitting-label", item, () => {
            addContextLabel(item, midpointOfSegment(item.start, item.end), labelText, {
                background: 'rgba(219, 234, 254, 0.94)',
                border: 'rgba(59, 130, 246, 0.45)',
                text: '#1d4ed8',
            });
        });
    }
}

function addWeld(item) {
    const selectGroup = [];
    addSphere(item.point, 0xdc2626, sizes.weldRad, item, selectGroup);
}

function addSupport(item) {
    const selectGroup = [];
    addCube(item.point, 0x16a34a, sizes.supportSize, item, selectGroup);
    const supportCode = (getItemProperties(item).inline_code || "").toUpperCase();
    if (supportCode === "FLOR") {
        safeRenderEnhancement("support-floor", item, () => addFloorSupportSymbol(item, selectGroup));
    } else if (supportCode.startsWith("NCU")) {
        safeRenderEnhancement("support-nozzle", item, () => addNozzleSupportSymbol(item, selectGroup));
    } else {
        safeRenderEnhancement("support-generic", item, () => {
            addOrientedBoxAt(
                [item.point[0], item.point[1] - sizes.supportStem * 0.22, item.point[2]],
                new THREE.Vector3(0, 1, 0),
                sizes.supportPlate * 0.85,
                sizes.arrowShaft * 1.2,
                sizes.supportPlate * 0.55,
                0x166534,
                item,
                selectGroup,
                { richSymbol: true }
            );
        });
    }

    const labelText = getContextLabelText(item);
    if (labelText) {
        safeRenderEnhancement("support-label", item, () => {
            addContextLabel(item, item.point, labelText, {
                background: 'rgba(240, 253, 244, 0.94)',
                border: 'rgba(34, 197, 94, 0.42)',
                text: '#166534',
            });
        });
    }
}

function addMarker(item) {
    const selectGroup = [];
    addSphere(item.point, 0xea580c, sizes.markerRad, item, selectGroup);
    const markerCode = (getItemProperties(item).inline_code || "").toUpperCase();
    if (markerCode === "FLOW") {
        safeRenderEnhancement("marker-flow", item, () => addFlowMarkerSymbol(item, selectGroup));
    }

    const labelText = getContextLabelText(item);
    if (labelText) {
        safeRenderEnhancement("marker-label", item, () => {
            addContextLabel(item, item.point, labelText, {
                background: 'rgba(255, 247, 237, 0.96)',
                border: 'rgba(249, 115, 22, 0.38)',
                text: '#c2410c',
            });
        });
    }
}

function addIfcMesh(item) {
    const meshData = item.mesh || {};
    const positions = Array.isArray(meshData.positions) ? meshData.positions : [];
    const indices = Array.isArray(meshData.indices) ? meshData.indices : [];
    if (!positions.length || !indices.length) return;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    const colorArray = Array.isArray(meshData.color) && meshData.color.length >= 3
        ? meshData.color
        : [0.45, 0.55, 0.72];
    const color = new THREE.Color(colorArray[0], colorArray[1], colorArray[2]);
    const material = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.72,
        metalness: 0.08,
        side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = false;
    mesh.receiveShadow = false;

    const selectGroup = [];
    addStandaloneMesh(mesh, item, selectGroup);
}

(sceneData.pipes || []).forEach(addPipe);
(sceneData.fittings || []).forEach(addFitting);
(sceneData.welds || []).forEach(addWeld);
(sceneData.supports || []).forEach(addSupport);
(sceneData.markers || []).forEach(addMarker);
(sceneData.meshes || []).forEach(addIfcMesh);
rebuildMeasurementSnapCandidates();

function buildIfcClassFilterUI() {
    if (!ifcClassFilters || !ifcClassFilterWrap) return;

    const classCounts = new Map();
    leafRepresentatives.forEach(mesh => {
        const ifcClass = mesh.userData.ifcClass;
        if (!ifcClass) return;
        classCounts.set(ifcClass, (classCounts.get(ifcClass) || 0) + 1);
    });

    const sorted = Array.from(classCounts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    if (!sorted.length) {
        ifcClassFilterWrap.classList.add('hidden');
        if (ifcOpacityWrap) ifcOpacityWrap.classList.add('hidden');
        return;
    }

    ifcClassFilterWrap.classList.remove('hidden');
    if (ifcOpacityWrap) ifcOpacityWrap.classList.remove('hidden');
    ifcClassFilters.innerHTML = sorted.map(([className, count]) => `
        <label class="flex items-center justify-between gap-2 cursor-pointer hover:text-slate-900 transition">
            <span class="flex items-center gap-2">
                <input type="checkbox" class="ifc-class-filter rounded border-slate-300 text-slate-700 focus:ring-0" value="${escapeHtml(className)}" checked>
                <span>${escapeHtml(className)}</span>
            </span>
            <span class="text-[10px] text-slate-400">${count}</span>
        </label>
    `).join("");

    document.querySelectorAll('.ifc-class-filter').forEach(cb => {
        cb.addEventListener('change', () => {
            applySceneVisibility({ refit: true });
        });
    });
}

function buildHierarchyTree() {
    if (!hContent) return;

    const hierarchy = {};
    leafRepresentatives.forEach(mesh => {
        const item = mesh.userData.item;
        const file = getHierarchyFile(item);
        const group = getHierarchyGroup(item);
        const groupKey = getHierarchyGroupKey(item);
        const leafKey = getHierarchyLeafKey(item);
        const leafLabel = getHierarchyLeafLabel(item);
        const sourceFormat = getSourceFormat(item);

        if (!hierarchy[file]) hierarchy[file] = { groups: {} };
        if (!hierarchy[file].groups[groupKey]) {
            hierarchy[file].groups[groupKey] = {
                group,
                groupKey,
                sourceFormat,
                items: [],
            };
        }

        hierarchy[file].groups[groupKey].items.push({
            leafKey,
            leafLabel,
            searchText: getHierarchySearchText(item),
        });
    });

    const sortedFiles = Object.keys(hierarchy).sort((a, b) => a.localeCompare(b));
    let html = "";

    sortedFiles.forEach(file => {
        const fileEntry = hierarchy[file];
        const groups = Object.values(fileEntry.groups).sort((a, b) => a.group.localeCompare(b.group));
        html += `
            <div class="hierarchy-file mb-2" data-file="${escapeHtml(file)}">
                <div class="flex items-center gap-1 text-xs font-medium text-gray-700 p-1 rounded hover:bg-black/5 transition">
                    <button type="button" class="file-collapse-toggle flex h-5 w-5 shrink-0 items-center justify-center rounded border border-slate-200 bg-white text-[10px] text-slate-500 shadow-sm transition hover:bg-slate-50" data-file="${escapeHtml(file)}" aria-label="Collapse file">▾</button>
                    <label class="flex min-w-0 flex-1 items-center cursor-pointer">
                        <input type="checkbox" class="file-toggle mr-2 h-3.5 w-3.5 text-blue-500 rounded border-gray-300 focus:ring-0" checked data-file="${escapeHtml(file)}">
                        <span class="truncate" title="${escapeHtml(file)}">${escapeHtml(file)}</span>
                    </label>
                </div>
                <div class="hierarchy-file-children pl-5 mt-1 border-l border-gray-100 space-y-1 py-1">
        `;

        groups.forEach(groupEntry => {
            const isIfcGroup = groupEntry.sourceFormat === "IFC";
            const sortedItems = groupEntry.items.sort((a, b) => a.leafLabel.localeCompare(b.leafLabel));

            if (isIfcGroup) {
                html += `
                    <div class="hierarchy-group" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-file="${escapeHtml(file)}">
                        <div class="flex items-center gap-1 text-gray-600 hover:text-gray-900 transition text-[11px] font-medium tracking-wide">
                            <button type="button" class="group-collapse-toggle flex h-4 w-4 shrink-0 items-center justify-center rounded border border-slate-200 bg-white text-[9px] text-slate-500 shadow-sm transition hover:bg-slate-50" data-group-key="${escapeHtml(groupEntry.groupKey)}" aria-label="Collapse group">▾</button>
                            <label class="flex min-w-0 flex-1 items-center cursor-pointer">
                                <input type="checkbox" class="group-toggle mr-2 h-3 w-3 text-gray-500 rounded border-gray-200 focus:ring-0" checked data-file="${escapeHtml(file)}" data-group-key="${escapeHtml(groupEntry.groupKey)}">
                                <span class="truncate" title="${escapeHtml(groupEntry.group)}">${escapeHtml(groupEntry.group)}</span>
                            </label>
                        </div>
                        <div class="hierarchy-group-children pl-4 mt-1 border-l border-gray-100 space-y-1">
                            ${sortedItems.map(entry => `
                                <label class="hierarchy-leaf-row flex items-center text-gray-500 hover:text-gray-800 transition cursor-pointer text-[11px] font-normal tracking-wide" data-leaf-key="${escapeHtml(entry.leafKey)}" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-file="${escapeHtml(file)}" data-search-text="${escapeHtml(entry.searchText)}">
                                    <input type="checkbox" class="leaf-toggle mr-2 h-3 w-3 text-gray-400 rounded border-gray-200 focus:ring-0" checked data-file="${escapeHtml(file)}" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-leaf-key="${escapeHtml(entry.leafKey)}">
                                    <span class="truncate" title="${escapeHtml(entry.leafLabel)}">${escapeHtml(entry.leafLabel)}</span>
                                </label>
                            `).join("")}
                        </div>
                    </div>
                `;
            } else {
                const entry = sortedItems[0];
                html += `
                    <label class="hierarchy-leaf-row flex items-center text-gray-500 hover:text-gray-800 transition cursor-pointer text-[11px] font-normal tracking-wide" data-leaf-key="${escapeHtml(entry.leafKey)}" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-file="${escapeHtml(file)}" data-search-text="${escapeHtml(entry.searchText)}">
                        <input type="checkbox" class="leaf-toggle mr-2 h-3 w-3 text-gray-400 rounded border-gray-200 focus:ring-0" checked data-file="${escapeHtml(file)}" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-leaf-key="${escapeHtml(entry.leafKey)}">
                        <span class="truncate" title="${escapeHtml(entry.leafLabel)}">${escapeHtml(entry.leafLabel)}</span>
                    </label>
                `;
            }
        });

        html += `</div></div>`;
    });

    hContent.innerHTML = html || "<span class='text-gray-400'>No hierarchy data found.</span>";
    buildEhtHierarchySection();
}

function buildEhtHierarchySection() {
    if (!hContent) return;
    const existing = document.getElementById('ehtHierarchySection');
    if (existing) existing.remove();
    if (!ehtElements.length) return;

    const byType = new Map();
    ehtElements.forEach(element => {
        if (!byType.has(element.element_type)) {
            byType.set(element.element_type, []);
        }
        byType.get(element.element_type).push(element);
    });

    const sortedTypes = Array.from(byType.keys()).sort((a, b) => getEhtTypeLabel(a).localeCompare(getEhtTypeLabel(b)));
    const allVisible = areAllEhtElementsVisible();
    const section = document.createElement('div');
    section.id = 'ehtHierarchySection';
    section.className = 'mt-4 border-t border-slate-200 pt-4';
    section.innerHTML = `
        <div class="mb-3 flex items-center justify-between gap-2 px-1">
            <div>
                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">EHT Overlay</div>
                <div class="mt-0.5 text-[10px] text-slate-500">${ehtElements.length} element${ehtElements.length === 1 ? "" : "s"}</div>
            </div>
            <button id="ehtShowAllBtn" type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-[10px] font-medium text-slate-600 shadow-sm hover:bg-slate-50">${allVisible ? "Hide All" : "Show All"}</button>
        </div>
        <div class="space-y-2">
            ${sortedTypes.map(type => {
                const elements = byType.get(type).sort((a, b) => getEhtElementLabel(a).localeCompare(getEhtElementLabel(b)));
                const typeVisible = visibleEhtTypes.has(type);
                const typeCollapsed = collapsedEhtTypes.has(type);
                return `
                    <div class="eht-type-group rounded border border-amber-100 bg-amber-50/35 p-2" data-eht-type="${escapeHtml(type)}">
                        <div class="flex items-center justify-between gap-2 text-[11px] font-semibold text-slate-700">
                            <span class="flex min-w-0 flex-1 items-center gap-2">
                                <button type="button" class="eht-type-collapse-toggle flex h-4 w-4 shrink-0 items-center justify-center rounded border border-amber-200 bg-white text-[10px] text-amber-700 shadow-sm transition hover:bg-amber-50" data-eht-type="${escapeHtml(type)}" aria-label="${typeCollapsed ? "Expand EHT type" : "Collapse EHT type"}">${typeCollapsed ? "+" : "-"}</button>
                                <label class="flex min-w-0 flex-1 items-center gap-2">
                                <input type="checkbox" class="eht-type-toggle rounded border-slate-300 text-amber-600 focus:ring-0" data-eht-type="${escapeHtml(type)}" ${typeVisible ? "checked" : ""}>
                                <span class="truncate" title="${escapeHtml(getEhtTypeLabel(type))}">${escapeHtml(getEhtTypeLabel(type))}</span>
                                </label>
                            </span>
                            <span class="text-[10px] text-slate-400">${elements.length}</span>
                        </div>
                        <div class="eht-type-children mt-2 space-y-1 pl-5 ${typeCollapsed ? "hidden" : ""}">
                            ${elements.map(element => {
                                const elementVisible = isEhtElementVisible(element);
                                return `
                                    <div class="eht-hierarchy-row flex items-center gap-2 rounded px-1.5 py-1 text-[11px] text-slate-600 transition hover:bg-white/70" data-eht-uid="${escapeHtml(element.element_uid)}" data-search-text="${escapeHtml(getEhtSearchText(element))}">
                                        <input type="checkbox" class="eht-element-toggle h-3 w-3 rounded border-slate-300 text-amber-600 focus:ring-0" data-eht-uid="${escapeHtml(element.element_uid)}" ${elementVisible ? "checked" : ""}>
                                        <button type="button" class="eht-select-row min-w-0 flex-1 truncate text-left" data-eht-uid="${escapeHtml(element.element_uid)}" title="${escapeHtml(getEhtElementLabel(element))}">
                                            ${escapeHtml(getEhtElementLabel(element))}
                                        </button>
                                    </div>
                                `;
                            }).join("")}
                        </div>
                    </div>
                `;
            }).join("")}
        </div>
    `;
    hContent.appendChild(section);

    const showAllBtn = document.getElementById('ehtShowAllBtn');
    if (showAllBtn) {
        showAllBtn.addEventListener('click', () => {
            if (areAllEhtElementsVisible()) {
                hiddenEhtUids.clear();
                visibleEhtTypes.clear();
                ehtElements.forEach(element => hiddenEhtUids.add(element.element_uid));
            } else {
                hiddenEhtUids.clear();
                visibleEhtTypes.clear();
                ehtElements.forEach(element => visibleEhtTypes.add(element.element_type));
            }
            applyEhtVisibility();
            buildEhtHierarchySection();
        });
    }

    section.querySelectorAll('.eht-type-collapse-toggle').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const type = button.dataset.ehtType;
            if (collapsedEhtTypes.has(type)) {
                collapsedEhtTypes.delete(type);
            } else {
                collapsedEhtTypes.add(type);
            }
            buildEhtHierarchySection();
        });
    });

    section.querySelectorAll('.eht-type-toggle').forEach(toggle => {
        toggle.addEventListener('change', () => {
            const type = toggle.dataset.ehtType;
            if (toggle.checked) {
                visibleEhtTypes.add(type);
                ehtElements
                    .filter(element => element.element_type === type)
                    .forEach(element => hiddenEhtUids.delete(element.element_uid));
            } else {
                visibleEhtTypes.delete(type);
            }
            applyEhtVisibility();
            buildEhtHierarchySection();
        });
    });

    section.querySelectorAll('.eht-element-toggle').forEach(toggle => {
        toggle.addEventListener('change', () => {
            if (toggle.checked) {
                hiddenEhtUids.delete(toggle.dataset.ehtUid);
                const element = findEhtElement(toggle.dataset.ehtUid);
                if (element) visibleEhtTypes.add(element.element_type);
            } else {
                hiddenEhtUids.add(toggle.dataset.ehtUid);
            }
            applyEhtVisibility();
            buildEhtHierarchySection();
        });
    });

    section.querySelectorAll('.eht-select-row').forEach(button => {
        button.addEventListener('click', () => {
            const element = findEhtElement(button.dataset.ehtUid);
            if (element) selectEhtElement(element);
        });
    });

    if (getCurrentSearchQuery()) {
        applyHierarchySearchFilter();
    }
}

function syncGroupToggleStates() {
    document.querySelectorAll('.group-toggle').forEach(groupToggle => {
        const leafToggles = Array.from(document.querySelectorAll('.leaf-toggle')).filter(cb => cb.dataset.groupKey === groupToggle.dataset.groupKey);
        const checkedCount = leafToggles.filter(cb => cb.checked).length;
        groupToggle.checked = leafToggles.length > 0 && checkedCount === leafToggles.length;
        groupToggle.indeterminate = checkedCount > 0 && checkedCount < leafToggles.length;
    });
}

function syncFileToggleStates() {
    document.querySelectorAll('.file-toggle').forEach(fileToggle => {
        const leafToggles = Array.from(document.querySelectorAll('.leaf-toggle')).filter(cb => cb.dataset.file === fileToggle.dataset.file);
        const checkedCount = leafToggles.filter(cb => cb.checked).length;
        fileToggle.checked = leafToggles.length > 0 && checkedCount === leafToggles.length;
        fileToggle.indeterminate = checkedCount > 0 && checkedCount < leafToggles.length;
    });
}

function syncMasterHierarchyToggle() {
    if (!toggleAllHierarchy) return;
    const leafToggles = Array.from(document.querySelectorAll('.leaf-toggle'));
    const checkedCount = leafToggles.filter(cb => cb.checked).length;
    toggleAllHierarchy.checked = leafToggles.length > 0 && checkedCount === leafToggles.length;
    toggleAllHierarchy.indeterminate = checkedCount > 0 && checkedCount < leafToggles.length;
    if (hierarchySelectionCount) {
        hierarchySelectionCount.textContent = leafToggles.length
            ? `${checkedCount}/${leafToggles.length} assets visible`
            : "No Assets";
    }
}

function getCurrentSearchQuery() {
    return hierarchySearchInput ? hierarchySearchInput.value.trim().toLowerCase() : "";
}

function findMatchingLeafKeys(query) {
    if (!query) {
        return new Set(Array.from(leafRepresentatives.keys()));
    }
    const matches = new Set();
    document.querySelectorAll('.hierarchy-leaf-row').forEach(row => {
        const haystack = String(row.dataset.searchText || "").toLowerCase();
        if (haystack.includes(query)) {
            matches.add(row.dataset.leafKey);
        }
    });
    return matches;
}

function applyHierarchySearchFilter() {
    const query = getCurrentSearchQuery();
    hierarchySearchMatches = findMatchingLeafKeys(query);

    document.querySelectorAll('.hierarchy-leaf-row').forEach(row => {
        const visible = !query || hierarchySearchMatches.has(row.dataset.leafKey);
        row.classList.toggle('hidden', !visible);
    });

    document.querySelectorAll('.hierarchy-group').forEach(groupRow => {
        const visibleChildren = Array.from(groupRow.querySelectorAll('.hierarchy-leaf-row')).some(row => !row.classList.contains('hidden'));
        groupRow.classList.toggle('hidden', !visibleChildren);
    });

    document.querySelectorAll('.hierarchy-file').forEach(fileRow => {
        const visibleChildren = Array.from(fileRow.querySelectorAll('.hierarchy-leaf-row')).some(row => !row.classList.contains('hidden'));
        fileRow.classList.toggle('hidden', !visibleChildren);
    });

    document.querySelectorAll('.eht-hierarchy-row').forEach(row => {
        const haystack = String(row.dataset.searchText || "").toLowerCase();
        const visible = !query || haystack.includes(query);
        row.classList.toggle('hidden', !visible);
    });

    document.querySelectorAll('.eht-type-group').forEach(groupRow => {
        const visibleChildren = Array.from(groupRow.querySelectorAll('.eht-hierarchy-row')).some(row => !row.classList.contains('hidden'));
        groupRow.classList.toggle('hidden', !visibleChildren);
    });

    const ehtSection = document.getElementById('ehtHierarchySection');
    if (ehtSection && query) {
        const visibleChildren = Array.from(ehtSection.querySelectorAll('.eht-hierarchy-row')).some(row => !row.classList.contains('hidden'));
        ehtSection.classList.toggle('hidden', !visibleChildren);
    } else if (ehtSection) {
        ehtSection.classList.remove('hidden');
    }

    if (hierarchySearchStatus) {
        const ehtMatchCount = query
            ? Array.from(document.querySelectorAll('.eht-hierarchy-row')).filter(row => !row.classList.contains('hidden')).length
            : 0;
        const totalMatches = hierarchySearchMatches.size + ehtMatchCount;
        if (!query) {
            hierarchySearchStatus.textContent = 'Search the current hierarchy';
        } else {
            hierarchySearchStatus.textContent = totalMatches
                ? `${totalMatches} match${totalMatches === 1 ? '' : 'es'}`
                : 'No matches found';
        }
    }
}

function updateHierarchyState({ refit = false } = {}) {
    syncGroupToggleStates();
    syncFileToggleStates();
    syncMasterHierarchyToggle();
    applyHierarchySearchFilter();
    applySceneVisibility({ refit });
}

function selectLeafKey(leafKey, { isolate = false, refit = true } = {}) {
    const mesh = leafRepresentatives.get(leafKey);
    if (!mesh) return false;

    if (isolate) {
        document.querySelectorAll('.leaf-toggle').forEach(cb => {
            cb.checked = cb.dataset.leafKey === leafKey;
        });
        updateHierarchyState({ refit: false });
    }

    clearHighlight();
    clearEhtHighlight();
    selectedEhtElementUid = "";
    selectedGroup = mesh.userData.selectGroup || [mesh];
    applyHighlight(selectedGroup);
    renderProperties(mesh.userData.item);
    if (refit) {
        focusOnSelection();
    }
    return true;
}

function focusSearchMatches({ isolate = false } = {}) {
    const query = getCurrentSearchQuery();
    if (!query) {
        if (hierarchySearchStatus) {
            hierarchySearchStatus.textContent = 'Type a search term first';
        }
        return;
    }
    const matches = findMatchingLeafKeys(query);
    if (!matches.size) {
        if (hierarchySearchStatus) {
            hierarchySearchStatus.textContent = 'No matches found';
        }
        return;
    }

    if (isolate) {
        document.querySelectorAll('.leaf-toggle').forEach(cb => {
            cb.checked = matches.has(cb.dataset.leafKey);
        });
        updateHierarchyState({ refit: true });
    }

    const firstMatch = Array.from(matches)[0];
    selectLeafKey(firstMatch, { isolate: false, refit: true });
}

buildHierarchyTree();
buildIfcClassFilterUI();

if (hContent) {
    document.querySelectorAll('.file-toggle').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const file = e.target.dataset.file;
            document.querySelectorAll('.leaf-toggle').forEach(leafToggle => {
                if (leafToggle.dataset.file === file) leafToggle.checked = isChecked;
            });
            updateHierarchyState({ refit: true });
        });
    });

    document.querySelectorAll('.group-toggle').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const groupKey = e.target.dataset.groupKey;
            document.querySelectorAll('.leaf-toggle').forEach(leafToggle => {
                if (leafToggle.dataset.groupKey === groupKey) leafToggle.checked = isChecked;
            });
            updateHierarchyState({ refit: true });
        });
    });

    document.querySelectorAll('.leaf-toggle').forEach(cb => {
        cb.addEventListener('change', () => updateHierarchyState({ refit: true }));
    });

    document.querySelectorAll('.file-collapse-toggle').forEach(btn => {
        btn.addEventListener('click', event => {
            event.stopPropagation();
            const fileRow = btn.closest('.hierarchy-file');
            const children = fileRow ? fileRow.querySelector('.hierarchy-file-children') : null;
            if (!children) return;
            const collapsed = children.classList.toggle('hidden');
            btn.textContent = collapsed ? '▸' : '▾';
            btn.setAttribute('aria-label', collapsed ? 'Expand file' : 'Collapse file');
        });
    });

    document.querySelectorAll('.group-collapse-toggle').forEach(btn => {
        btn.addEventListener('click', event => {
            event.stopPropagation();
            const groupRow = btn.closest('.hierarchy-group');
            const children = groupRow ? groupRow.querySelector('.hierarchy-group-children') : null;
            if (!children) return;
            const collapsed = children.classList.toggle('hidden');
            btn.textContent = collapsed ? '▸' : '▾';
            btn.setAttribute('aria-label', collapsed ? 'Expand group' : 'Collapse group');
        });
    });

    document.querySelectorAll('.hierarchy-leaf-row').forEach(row => {
        row.addEventListener('click', (event) => {
            if (event.target && event.target.tagName === 'INPUT') return;
            selectLeafKey(row.dataset.leafKey, { refit: false });
        });
        row.addEventListener('dblclick', () => {
            selectLeafKey(row.dataset.leafKey, { refit: true });
        });
    });

    if (toggleAllHierarchy) {
        toggleAllHierarchy.addEventListener('change', (event) => {
            const isChecked = event.target.checked;
            document.querySelectorAll('.leaf-toggle').forEach(cb => {
                cb.checked = isChecked;
            });
            updateHierarchyState({ refit: true });
        });
    }

    if (hierarchySearchInput) {
        hierarchySearchInput.addEventListener('input', () => {
            applyHierarchySearchFilter();
        });
    }

    if (searchFocusBtn) {
        searchFocusBtn.addEventListener('click', () => focusSearchMatches({ isolate: false }));
    }

    if (searchIsolateBtn) {
        searchIsolateBtn.addEventListener('click', () => focusSearchMatches({ isolate: true }));
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            if (hierarchySearchInput) hierarchySearchInput.value = '';
            applyHierarchySearchFilter();
            document.querySelectorAll('.leaf-toggle').forEach(cb => {
                cb.checked = true;
            });
            updateHierarchyState({ refit: true });
        });
    }

    updateHierarchyState({ refit: false });
}

// -------------------------------------------------
// Thickness Slider UI binding
const thicknessSlider = document.getElementById('thicknessSlider');
if (thicknessSlider) {
    thicknessSlider.addEventListener('input', function(e) {
        const val = parseFloat(e.target.value);
        const tf = document.getElementById('thicknessValue');
        if (tf) tf.textContent = val.toFixed(1) + 'x';
        
        modelGroup.children.forEach(mesh => {
            if (!mesh.geometry) return;
            if (mesh.userData && mesh.userData.item && getSourceFormat(mesh.userData.item) === "IFC") return;
            // Cylinder Y is the length, X & Z are the radius.
            if (mesh.geometry.type === 'CylinderGeometry') {
                mesh.scale.set(val, 1, val);
            } else {
                mesh.scale.set(val, val, val);
            }
        });
    });
}
// -------------------------------------------------

function fitCameraToObject(object) {
    const box = new THREE.Box3();
    box.makeEmpty();
    
    // Only fit to visible objects
    object.traverse(node => {
        if (node.isMesh && node.visible) {
            if (!node.geometry.boundingBox) node.geometry.computeBoundingBox();
            const nodeBox = new THREE.Box3().copy(node.geometry.boundingBox).applyMatrix4(node.matrixWorld);
            box.union(nodeBox);
        }
    });

    if (box.isEmpty()) {
        clearGridScaleLabels();
        camera.position.set(120, 120, 120);
        controls.target.set(0, 0, 0);
        controls.update();
        return;
    }

    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const center = sphere.center.clone();
    const hasVisibleIfcGeometry = selectableMeshes.some(mesh =>
        mesh.visible
        && mesh.userData
        && mesh.userData.item
        && getSourceFormat(mesh.userData.item) === "IFC"
    );
    const actualRadius = Math.max(sphere.radius, 0.05);
    const minimumCameraRadius = hasVisibleIfcGeometry ? 0.5 : 2;
    const radius = Math.max(actualRadius, minimumCameraRadius);
    
    // Dynamically adjust Grid and Axes to match the viewed content box
    scene.remove(gridHelper);
    scene.remove(axesHelper);
    
    const maxDim = actualRadius * 2;
    const gridLayout = gridLayoutForExtent(maxDim);
    const gridDim = gridLayout.size;
    gridHelper = new THREE.GridHelper(gridDim, gridLayout.divisions, 0x888888, 0xb0b0b0);
    gridHelper.position.y = box.min.y;
    gridHelper.position.x = center.x;
    gridHelper.position.z = center.z;
    gridHelper.visible = showGridScaleLabels;
    scene.add(gridHelper);
    
    const axesSize = Math.max(maxDim * 0.5, 5);
    axesHelper = new THREE.AxesHelper(axesSize);
    axesHelper.position.copy(gridHelper.position);
    axesHelper.visible = showGridScaleLabels;
    scene.add(axesHelper);
    syncGroundPlaneToGrid();
    updateGridScaleLabels(center, gridDim, gridHelper.position.y, gridLayout.step);

    const offset = new THREE.Vector3(1.4, 1.0, 1.2).normalize().multiplyScalar(radius * 2.8);

    camera.position.copy(center.clone().add(offset));
    // Set near/far robustly to handle massive geographical plants
    camera.near = 0.1;
    camera.far = Math.max(radius * 50, 500000);
    camera.updateProjectionMatrix();
    camera.lookAt(center);

    controls.target.copy(center);
    controls.maxDistance = camera.far * 0.9;
    controls.minDistance = 0.1; 
    controls.update();
}

// Initial fit for modelGroup
fitCameraToObject(modelGroup);

function focusOnSelection() {
    if (!selectedGroup || selectedGroup.length === 0) return;
    const box = new THREE.Box3();
    box.makeEmpty();
    selectedGroup.forEach(mesh => {
        if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
        const nodeBox = new THREE.Box3().copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
        box.union(nodeBox);
    });
    
    if (box.isEmpty()) return;
    
    const center = new THREE.Vector3();
    box.getCenter(center);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const r = Math.max(sphere.radius, 2);

    const direction = new THREE.Vector3().subVectors(camera.position, controls.target).normalize();
    if (direction.length() < 0.1) direction.set(0, 1, 1).normalize();
    const desiredPos = center.clone().add(direction.multiplyScalar(r * 4));
    
    camera.position.copy(desiredPos);
    controls.target.copy(center);
    controls.update();
}

function hideSelection() {
    if (!selectedGroup) return;
    selectedGroup.forEach(mesh => manuallyHiddenItems.add(mesh.userData.visibilityKey));
    applySceneVisibility({ refit: false });
    clearHighlight();
    propsContent.innerHTML = `
        <div class="text-center mt-10">
            <div class="inline-block p-4 rounded-full bg-red-100 text-red-600 mb-3 border border-red-200">
                <svg class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path></svg>
            </div>
            <p class="text-gray-700 font-semibold mb-2">Component Hidden</p>
            <p class="text-xs text-gray-400 mb-4 px-2">Hiding outliers helps the viewer establish a better bounding scale for clusters.</p>
            <button id="btnRefit" class="text-xs font-bold shadow bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded transition">Recalibrate Scene Camera</button>
        </div>
    `;
    
    document.getElementById('btnRefit').addEventListener('click', () => {
        fitCameraToObject(modelGroup);
    });
    
    const btnShowHidden = document.getElementById('btnShowHidden');
    if(btnShowHidden) btnShowHidden.classList.remove('hidden');
}

const btnShowHidden = document.getElementById('btnShowHidden');
if(btnShowHidden) {
    btnShowHidden.addEventListener('click', () => {
        manuallyHiddenItems.clear();
        applySceneVisibility({ refit: false });
        btnShowHidden.classList.add('hidden');
        fitCameraToObject(modelGroup);
    });
}

if (richSymbolToggle) {
    richSymbolToggle.addEventListener('change', () => {
        applySceneVisibility({ refit: false });
    });
}

if (contextLabelToggle) {
    contextLabelToggle.addEventListener('change', () => {
        applySceneVisibility({ refit: false });
    });
}

if (ifcOpacitySlider) {
    ifcOpacitySlider.addEventListener('input', () => {
        applyIfcOpacity();
    });
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderAttributeSettingsRows() {
    if (!attributeSettingsRows) return;
    const attributes = getAttributeSettingsDictionary();

    if (attributeSettingsEmpty) {
        attributeSettingsEmpty.classList.toggle('hidden', attributes.length > 0);
    }

    attributeSettingsRows.innerHTML = attributes.map(attr => {
        const label = attributeLabelMap[attr.key] || "";
        const sample = attr.sampleValue === undefined || attr.sampleValue === null ? "" : String(attr.sampleValue);
        return `
            <div class="grid gap-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[140px_1fr_1fr] md:items-center">
                <div>
                    <div class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">PCF Key</div>
                    <div class="mt-1 font-mono text-[12px] font-semibold text-slate-800">${escapeHtml(attr.key)}</div>
                    <div class="mt-1 text-[10px] text-slate-400">${attr.count} component${attr.count === 1 ? "" : "s"}</div>
                </div>
                <div>
                    <div class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Sample Value</div>
                    <div class="mt-1 truncate rounded border border-slate-100 bg-slate-50 px-2 py-1.5 text-[12px] text-slate-700" title="${escapeHtml(sample)}">${escapeHtml(sample || "Blank")}</div>
                </div>
                <label class="block">
                    <span class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Display Name</span>
                    <input type="text" class="attribute-name-input mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-[12px] text-slate-800 shadow-sm outline-none transition focus:border-slate-500" data-attribute-key="${escapeHtml(attr.key)}" value="${escapeHtml(label)}" placeholder="e.g. Line ID, Fluid, Design Temp">
                </label>
            </div>
        `;
    }).join("");

    if (attributeSettingsStatus) {
        attributeSettingsStatus.textContent = attributes.length
            ? `${attributes.length} attribute key${attributes.length === 1 ? "" : "s"} detected`
            : "";
    }
}

function openAttributeSettings() {
    if (!attributeSettingsModal) return;
    renderAttributeSettingsRows();
    attributeSettingsModal.classList.remove('hidden');
    attributeSettingsModal.classList.add('flex');
}

function closeAttributeSettings() {
    if (!attributeSettingsModal) return;
    attributeSettingsModal.classList.add('hidden');
    attributeSettingsModal.classList.remove('flex');
}

function rerenderSelectedProperties() {
    if (selectedGroup && selectedGroup.length > 0 && selectedGroup[0].userData.item) {
        renderProperties(selectedGroup[0].userData.item);
    }
}

if (attributeSettingsBtn) {
    attributeSettingsBtn.addEventListener('click', openAttributeSettings);
}

if (attributeSettingsCloseBtn) {
    attributeSettingsCloseBtn.addEventListener('click', closeAttributeSettings);
}

if (attributeSettingsModal) {
    attributeSettingsModal.addEventListener('click', event => {
        if (event.target === attributeSettingsModal) {
            closeAttributeSettings();
        }
    });
}

if (attributeSettingsSaveBtn) {
    attributeSettingsSaveBtn.addEventListener('click', async () => {
        const nextMappings = [];
        document.querySelectorAll('.attribute-name-input').forEach(input => {
            const key = input.dataset.attributeKey;
            const value = input.value.trim();
            if (key && value) {
                nextMappings.push({
                    attribute_key: key,
                    display_name: value,
                });
            }
        });

        const url = getAttributeMappingUrl();
        if (!url) return;
        const originalLabel = attributeSettingsSaveBtn.textContent;
        attributeSettingsSaveBtn.disabled = true;
        attributeSettingsSaveBtn.textContent = "Saving...";
        if (attributeSettingsStatus) {
            attributeSettingsStatus.textContent = "";
        }

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookieValue("csrftoken"),
                },
                body: JSON.stringify({ mappings: nextMappings }),
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "Unable to save attribute names.");
            }
            attributeMappings = Array.isArray(payload.mappings) ? payload.mappings : [];
            rebuildAttributeLabelMap();
            renderAttributeSettingsRows();
        } catch (error) {
            if (attributeSettingsStatus) {
                attributeSettingsStatus.textContent = error.message || "Unable to save";
            }
            return;
        } finally {
            attributeSettingsSaveBtn.disabled = false;
            attributeSettingsSaveBtn.textContent = originalLabel;
        }

        if (attributeSettingsStatus) {
            attributeSettingsStatus.textContent = "Saved";
        }
        rerenderSelectedProperties();
    });
}

if (attributeSettingsResetBtn) {
    attributeSettingsResetBtn.addEventListener('click', async () => {
        const url = getAttributeMappingUrl();
        if (!url) return;
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookieValue("csrftoken"),
                },
                body: JSON.stringify({ mappings: [] }),
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "Unable to clear attribute names.");
            }
            attributeMappings = [];
            rebuildAttributeLabelMap();
            renderAttributeSettingsRows();
            rerenderSelectedProperties();
            if (attributeSettingsStatus) {
                attributeSettingsStatus.textContent = "Cleared";
            }
        } catch (error) {
            if (attributeSettingsStatus) {
                attributeSettingsStatus.textContent = error.message || "Unable to clear";
            }
        }
    });
}

loadProjectAttributeMappings();
loadEhtLayer();

function getCookieValue(name) {
    const cookieValue = document.cookie
        .split(';')
        .map((cookie) => cookie.trim())
        .find((cookie) => cookie.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
}

function renderProperties(item) {
    const p = item.properties || {};
    const activeFilters = Array.from(document.querySelectorAll('.prop-filter'))
        .filter(cb => cb.checked)
        .map(cb => cb.value);
    const sourceFormat = String(p.source_format || "IDF").toUpperCase();
    const hierarchyLabel = sourceFormat === "IFC" ? "Spatial Group" : "Pipeline System";
    const hierarchyValue = p.pipeline_ref || p.spool_ref || p.hierarchy_group || p.ifc_class || "Unknown";

    let html = `
        <div class="prop-row"><span class="prop-key">Source Format</span><span class="prop-val">${escapeHtml(p.source_format || "IDF")}</span></div>
        <div class="prop-row"><span class="prop-key">Source Record</span><span class="prop-val">${escapeHtml(p.source_record || p.record_id || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Kind</span><span class="prop-val">${escapeHtml(p.kind || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Record ID</span><span class="prop-val">${escapeHtml(p.record_id || "")}</span></div>
        <div class="prop-row"><span class="prop-key">File Source</span><span class="prop-val">${escapeHtml(p.filename || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Inline code</span><span class="prop-val">${escapeHtml(p.inline_code || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Component ref</span><span class="prop-val">${escapeHtml(p.component_ref || "")}</span></div>
    `;

    if (activeFilters.includes("pipeline_ref")) {
        html += `<div class="prop-row"><span class="prop-key">${escapeHtml(hierarchyLabel)}</span><span class="prop-val font-semibold text-blue-700">${escapeHtml(hierarchyValue)}</span></div>`;
    }
    const availableAttributes = getAvailablePipelineAttributes(p);
    normalizeVisibleAttributeKeys(availableAttributes);
    const attributeByKey = new Map(availableAttributes.map(row => [row.key, row]));
    const selectedAttributes = visibleAttributeKeys
        .map(key => attributeByKey.get(key))
        .filter(Boolean);
    if (availableAttributes.length) {
        html += `
            <div class="prop-row">
                <div class="mb-2 flex items-center justify-between gap-2">
                    <span class="prop-key">Project Attributes</span>
                    <button id="btnAddProjectAttribute" type="button" class="flex h-6 w-6 items-center justify-center rounded border border-slate-200 bg-white text-[13px] font-semibold text-slate-600 shadow-sm transition hover:bg-slate-50" title="Add another project attribute">+</button>
                </div>
                <div class="space-y-2">
                    ${selectedAttributes.map((row, index) => `
                        <div class="rounded-md border border-slate-200 bg-white p-2">
                            <select class="project-attribute-select w-full rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-[11px] font-semibold text-slate-700 outline-none transition focus:border-slate-400" data-index="${index}">
                                ${availableAttributes.map(option => `
                                    <option value="${escapeHtml(option.key)}" ${option.key === row.key ? "selected" : ""}>
                                        ${escapeHtml(option.label)}${option.isNamed ? ` (${escapeHtml(option.key)})` : ""}
                                    </option>
                                `).join("")}
                            </select>
                            <div class="mt-2 text-[12px] leading-relaxed text-slate-800">
                                ${escapeHtml(row.value)}
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }
    if (sourceFormat === "IFC") {
        html += `<div class="prop-row"><span class="prop-key">IFC Class</span><span class="prop-val">${escapeHtml(p.ifc_class || "")}</span></div>`;
        html += `<div class="prop-row"><span class="prop-key">Global ID</span><span class="prop-val">${escapeHtml(p.global_id || "")}</span></div>`;
        if (p.name) {
            html += `<div class="prop-row"><span class="prop-key">Name</span><span class="prop-val">${escapeHtml(p.name)}</span></div>`;
        }
        if (p.object_type) {
            html += `<div class="prop-row"><span class="prop-key">Object Type</span><span class="prop-val">${escapeHtml(p.object_type)}</span></div>`;
        }
        if (p.predefined_type) {
            html += `<div class="prop-row"><span class="prop-key">Predefined Type</span><span class="prop-val">${escapeHtml(p.predefined_type)}</span></div>`;
        }
        if (p.tag) {
            html += `<div class="prop-row"><span class="prop-key">Tag</span><span class="prop-val">${escapeHtml(p.tag)}</span></div>`;
        }
        if (p.spatial_path && p.spatial_path.length) {
            html += `<div class="prop-row"><span class="prop-key">Spatial Path</span><span class="prop-val">${escapeHtml(p.spatial_path.join(" > "))}</span></div>`;
        }
    }
    if (p.piping_spec) {
        html += `<div class="prop-row"><span class="prop-key">Piping Spec</span><span class="prop-val">${escapeHtml(p.piping_spec)}</span></div>`;
    }
    if (p.tracing_spec || p.tracing_on) {
        html += `<div class="prop-row"><span class="prop-key">Tracing</span><span class="prop-val">${escapeHtml(p.tracing_spec || "Specified")} ${p.tracing_on ? "<span class='text-emerald-700 font-semibold'>(ON)</span>" : ""}</span></div>`;
    }
    if (p.item_code) {
        html += `<div class="prop-row"><span class="prop-key">Item Code</span><span class="prop-val">${escapeHtml(p.item_code)}</span></div>`;
    }
    if (p.description) {
        html += `<div class="prop-row"><span class="prop-key">Description</span><span class="prop-val">${escapeHtml(p.description)}</span></div>`;
    }
    if (p.connection_reference) {
        html += `<div class="prop-row"><span class="prop-key">Connection Ref</span><span class="prop-val">${escapeHtml(p.connection_reference)}</span></div>`;
    }
    if (p.support_type || p.support_direction || p.support_name) {
        html += `<div class="prop-row"><span class="prop-key">Support Detail</span><span class="prop-val">${escapeHtml([p.support_type, p.support_direction, p.support_name].filter(Boolean).join(" | "))}</span></div>`;
    }
    if (p.flow_value) {
        html += `<div class="prop-row"><span class="prop-key">Flow Value</span><span class="prop-val">${escapeHtml(p.flow_value)}</span></div>`;
    }
    if (activeFilters.includes("support_code")) {
        html += `<div class="prop-row"><span class="prop-key">Support Code</span><span class="prop-val">${escapeHtml(p.support_code || "N/A")}</span></div>`;
    }
    if (activeFilters.includes("insulation_spec")) {
        html += `<div class="prop-row"><span class="prop-key">Insulation Spec</span><span class="prop-val">${escapeHtml(p.insulation_spec || "None")}</span></div>`;
    }
    if (activeFilters.includes("instrument_tag")) {
        html += `<div class="prop-row"><span class="prop-key">Instrument Tag</span><span class="prop-val">${escapeHtml(p.instrument_tag || "None")}</span></div>`;
    }

    if (activeFilters.includes("materials")) {
        let materialsHtml = "<span class='text-gray-400 italic'>No materials listed</span>";
        if (p.materials && p.materials.length) {
            const nonEmpty = p.materials.filter(m => (m.code || m.description));
            if (nonEmpty.length) {
                materialsHtml = `
                    <div class="mt-1 bg-white border rounded-md overflow-hidden">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-gray-100 text-gray-600">
                                <tr><th class="px-2 py-1 border-b">Code</th><th class="px-2 py-1 border-b">Description</th></tr>
                            </thead>
                            <tbody>
                                ${nonEmpty.map(m => `
                                    <tr class="border-b last:border-0 hover:bg-gray-50">
                                        <td class="px-2 py-1 whitespace-nowrap text-blue-600">${escapeHtml(m.code)}</td>
                                        <td class="px-2 py-1">${escapeHtml(m.description)}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                `;
            }
        }
        html += `<div class="prop-row"><span class="prop-key mb-1">Materials</span><div class="prop-val">${materialsHtml}</div></div>`;
    }

    if (sourceFormat === "IFC" && p.property_sets && Object.keys(p.property_sets).length) {
        const propertySetHtml = Object.entries(p.property_sets).map(([name, values]) => `
            <div class="mb-3 rounded border border-slate-200 bg-white/90">
                <div class="border-b border-slate-200 px-2 py-1 text-[11px] font-semibold text-slate-700">${escapeHtml(name)}</div>
                <div class="px-2 py-2 text-[11px] space-y-1">
                    ${Object.entries(values || {}).map(([key, value]) => `
                        <div><span class="font-medium text-slate-500">${escapeHtml(key)}:</span> <span class="text-slate-800">${escapeHtml(value)}</span></div>
                    `).join("")}
                </div>
            </div>
        `).join("");
        html += `<div class="prop-row"><span class="prop-key mb-1">Property Sets</span><div class="prop-val">${propertySetHtml}</div></div>`;
    }

    if (sourceFormat === "IFC" && p.quantities && Object.keys(p.quantities).length) {
        const quantityHtml = Object.entries(p.quantities).map(([name, values]) => `
            <div class="mb-3 rounded border border-slate-200 bg-white/90">
                <div class="border-b border-slate-200 px-2 py-1 text-[11px] font-semibold text-slate-700">${escapeHtml(name)}</div>
                <div class="px-2 py-2 text-[11px] space-y-1">
                    ${Object.entries(values || {}).map(([key, value]) => `
                        <div><span class="font-medium text-slate-500">${escapeHtml(key)}:</span> <span class="text-slate-800">${escapeHtml(value)}</span></div>
                    `).join("")}
                </div>
            </div>
        `).join("");
        html += `<div class="prop-row"><span class="prop-key mb-1">Quantities</span><div class="prop-val">${quantityHtml}</div></div>`;
    }

    const notesHtml = (p.notes && p.notes.length)
        ? `<ul class="list-disc pl-4 text-xs text-red-600 space-y-1">${p.notes.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>`
        : "<span class='text-gray-400 italic'>No notes.</span>";
    html += `<div class="prop-row"><span class="prop-key mb-1">Notes & Warnings</span><div class="prop-val">${notesHtml}</div></div>`;

    if (activeFilters.includes("raw_coords")) {
        const rawCoords = sourceFormat === "IFC"
            ? `Bounds: ${escapeHtml(JSON.stringify(p.raw_bounds || {}))}`
            : p.raw_point
            ? `Point: ${escapeHtml(JSON.stringify(p.raw_point))}`
            : `Start: ${escapeHtml(JSON.stringify(p.raw_start || []))}\nEnd: ${escapeHtml(JSON.stringify(p.raw_end || []))}`;
        const extraCoords = [
            p.centre_point ? `Centre: ${escapeHtml(JSON.stringify(p.centre_point))}` : "",
            p.branch1_point ? `Branch1: ${escapeHtml(JSON.stringify(p.branch1_point))}` : "",
        ].filter(Boolean).join("\n");
        html += `<div class="prop-row"><span class="prop-key mb-1">Raw Coordinates</span><pre class="prop-val bg-gray-100 p-2 rounded text-xs overflow-x-auto border">${rawCoords}</pre></div>`;
        if (extraCoords) {
            html += `<div class="prop-row"><span class="prop-key mb-1">Extra Geometry</span><pre class="prop-val bg-gray-100 p-2 rounded text-xs overflow-x-auto border">${extraCoords}</pre></div>`;
        }
    }

    if (activeFilters.includes("unmapped")) {
        html += `<div class="prop-row"><span class="prop-key mb-1">Unmapped Metadata</span><pre class="prop-val bg-red-50 text-red-800 p-2 rounded text-xs overflow-x-auto border border-red-200">${escapeHtml(JSON.stringify(p.unmapped_meta || {}, null, 2))}</pre></div>`;
    }

    // UX enhancements: Adding focus and hide buttons to bottom of properties panel
    html += `
        <div class="mt-6 flex space-x-2 pb-6">
            <button id="btnFocusSel" title="Double-click item in 3D viewer to shortcut" class="flex-1 bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 font-medium py-1.5 px-2 rounded shadow-sm text-[11px] transition">Focus Camera</button>
            <button id="btnHideSel" class="flex-1 bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 font-medium py-1.5 px-2 rounded shadow-sm text-[11px] transition">Hide Object</button>
        </div>
    `;

    propsContent.innerHTML = html;
    
    document.getElementById("btnFocusSel").addEventListener("click", focusOnSelection);
    document.getElementById("btnHideSel").addEventListener("click", hideSelection);
    document.querySelectorAll('.project-attribute-select').forEach(select => {
        select.addEventListener('change', () => {
            const index = parseInt(select.dataset.index || "0", 10);
            visibleAttributeKeys[index] = select.value;
            renderProperties(item);
        });
    });
    const addAttributeBtn = document.getElementById("btnAddProjectAttribute");
    if (addAttributeBtn) {
        addAttributeBtn.addEventListener('click', () => {
            addVisibleAttributeKey(getAvailablePipelineAttributes(p));
            renderProperties(item);
        });
    }
}

// Re-render properties if filters change and an item is selected
document.querySelectorAll('.prop-filter').forEach(cb => {
    cb.addEventListener('change', () => {
        if (selectedGroup && selectedGroup.length > 0 && selectedGroup[0].userData.item) {
            renderProperties(selectedGroup[0].userData.item);
        }
    });
});

function clearHighlight() {
    if (!selectedGroup) return;

    selectedGroup.forEach(mesh => {
        if (mesh.material && mesh.material.emissive) {
            mesh.material.emissive.setHex(0x000000);
        }
    });

    selectedGroup = null;
}

function applyHighlight(selectGroup) {
    selectGroup.forEach(mesh => {
        if (mesh.material && mesh.material.emissive) {
            mesh.material.emissive.setHex(0x10b981); // Tailwind emerald-500
        }
    });
}

renderer.domElement.addEventListener("click", (event) => {
    if (measureModeActive) {
        event.preventDefault();
        event.stopPropagation();
        handleMeasurementClick(event);
        return;
    }

    if (pendingEhtGeometryEdit) {
        event.preventDefault();
        event.stopPropagation();
        const point = pointFromEhtPlacementEvent(event);
        if (point) {
            applyEhtGeometryEditAtPoint(point);
        } else {
            ehtStatus("No edit point found.");
        }
        return;
    }

    if (activeEhtTool) {
        event.preventDefault();
        event.stopPropagation();
        handleEhtPlacementClick(event);
        return;
    }

    const ehtHit = findEhtHitFromEvent(event);
    if (ehtHit) {
        event.preventDefault();
        event.stopPropagation();
        selectEhtElement(ehtHit);
        return;
    }

    const rect = renderer.domElement.getBoundingClientRect();

    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    // Ignore hidden objects during raycast
    const hits = raycaster.intersectObjects(selectableMeshes.filter(m => m.visible && m.parent), false);

    if (!hits.length) {
        clearHighlight();
        clearEhtHighlight();
        selectedEhtElementUid = "";
        propsContent.innerHTML = `
            <div class="text-center text-gray-400 mt-10">
                <svg class="mx-auto h-12 w-12 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                </svg>
                <p>Click on any rendered object to view its details.</p>
            </div>
        `;
        return;
    }

    const picked = hits[0].object;
    const item = picked.userData.item;
    const selectGroup = picked.userData.selectGroup || [picked];

    clearHighlight();
    clearEhtHighlight();
    selectedEhtElementUid = "";
    selectedGroup = selectGroup;
    applyHighlight(selectGroup);
    renderProperties(item);
});

renderer.domElement.addEventListener("pointermove", (event) => {
    updateMeasurementPreview(event);
    updateEhtPlacementPreview(event);
});

renderer.domElement.addEventListener("pointerleave", () => {
    clearMeasurementPreview();
    clearEhtPlacementPreview();
});

renderer.domElement.addEventListener("dblclick", (event) => {
    if (activeEhtTool && pendingEhtRoutePoints.length >= 2) {
        event.preventDefault();
        event.stopPropagation();
        finishPendingEhtRoute();
        return;
    }
    if (selectedGroup && selectedGroup.length) {
        focusOnSelection();
    }
});

// Add a solid ground plane
const groundGeo = new THREE.PlaneGeometry(2000, 2000);
const groundMat = new THREE.MeshStandardMaterial({ 
    color: 0xcccccc, 
    depthWrite: true, 
    opacity: 0.8, 
    transparent: true 
});
ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.visible = false;
scene.add(ground);

function syncGroundPlaneToGrid() {
    if (!ground) return;
    ground.position.y = gridHelper.position.y - 0.05;
}

syncGroundPlaneToGrid();

// ----------- PLOT PLAN MAP GENERATION -----------
let currentMapTexture = null;
const plotInput = document.getElementById('plotPlanInput');
if (plotInput) {
    plotInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(event) {
            const imgObj = new Image();
            imgObj.src = event.target.result;
            imgObj.onload = () => {
                document.getElementById('plotPlanControls').classList.remove('hidden');
                
                currentMapTexture = new THREE.Texture(imgObj);
                currentMapTexture.needsUpdate = true;
                currentMapTexture.minFilter = THREE.LinearFilter;
                currentMapTexture.magFilter = THREE.LinearFilter;
                
                groundMat.map = currentMapTexture;
                groundMat.color.setHex(0xffffff); // remove base color mapping to show pure texture
                groundMat.opacity = 1.0;
                groundMat.needsUpdate = true;
                ground.visible = true;
                syncGroundPlaneToGrid();
                
                // Align map roughly with the active camera focus
                if (controls.target) {
                    document.getElementById('ppOffsetX').value = Math.round(controls.target.x);
                    document.getElementById('ppOffsetZ').value = Math.round(controls.target.z);
                }
                updatePlotPlan();
            }
        };
        reader.readAsDataURL(file);
    });
}

function updatePlotPlan() {
    if(!currentMapTexture) return;
    
    const scale = parseFloat(document.getElementById('ppScale').value);
    const ox = parseFloat(document.getElementById('ppOffsetX').value);
    const oz = parseFloat(document.getElementById('ppOffsetZ').value);
    
    document.getElementById('scaleVal').innerText = scale.toFixed(2);
    document.getElementById('offsetXVal').innerText = ox;
    document.getElementById('offsetZVal').innerText = oz;
    
    ground.scale.set(scale, scale, 1);
    ground.position.x = ox;
    ground.position.z = oz;
}

if (navPanelToggleBtn) {
    navPanelToggleBtn.addEventListener('click', () => {
        setNavPanelCollapsed(true);
    });
}

if (navPanelReopenBtn) {
    navPanelReopenBtn.addEventListener('click', () => {
        setNavPanelCollapsed(false);
    });
}

if (sidePanelToggleBtn) {
    sidePanelToggleBtn.addEventListener('click', () => {
        setSidePanelCollapsed(true);
    });
}

if (sidePanelReopenBtn) {
    sidePanelReopenBtn.addEventListener('click', () => {
        setSidePanelCollapsed(false);
    });
}

if (scaleToggleBtn) {
    scaleToggleBtn.addEventListener('click', () => {
        setGridScaleVisible(!showGridScaleLabels);
    });
}

if (measureToggleBtn) {
    measureToggleBtn.addEventListener('click', () => {
        setMeasureMode(!measureModeActive);
    });
}

document.querySelectorAll('.eht-tool-btn').forEach(button => {
    button.addEventListener('click', () => {
        setActiveEhtTool(button.dataset.ehtTool || "");
    });
});

if (ehtSelectToolBtn) {
    ehtSelectToolBtn.addEventListener('click', () => {
        setActiveEhtTool("");
    });
}

if (ehtPaletteToggleBtn && ehtToolPalette) {
    ehtPaletteToggleBtn.addEventListener('click', () => {
        const collapsed = !ehtToolPalette.classList.contains('palette-collapsed');
        ehtToolPalette.classList.toggle('palette-collapsed', collapsed);
        ehtPaletteToggleBtn.textContent = collapsed ? "Show" : "Hide";
        ehtPaletteToggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    });
}

if (ehtSaveLayerBtn) {
    ehtSaveLayerBtn.addEventListener('click', () => {
        saveEhtLayer();
    });
}

if (ehtFinishRouteBtn) {
    ehtFinishRouteBtn.addEventListener('click', () => {
        finishPendingEhtRoute();
    });
}

if (ehtCancelRouteBtn) {
    ehtCancelRouteBtn.addEventListener('click', () => {
        cancelPendingEhtRoute();
    });
}

function handleGlobalKeyDown(event) {
    const isDeleteKey = event.key === 'Delete' || event.key === 'Backspace' || event.code === 'Delete' || event.code === 'Backspace';
    if (isDeleteKey && selectedEhtElementUid && !isTextEntryTarget(event.target)) {
        const selected = findEhtElement(selectedEhtElementUid);
        if (selected) {
            event.preventDefault();
            event.stopPropagation();
            deleteEhtElement(selected, { confirmDelete: true });
            return;
        }
    }
    if (event.key === 'Escape' && measureModeActive) {
        measurementPoints = [];
        clearMeasurementPreview();
        clearMeasurementGraphics();
        setMeasureMode(false);
    }
    if (event.key === 'Escape' && activeEhtTool) {
        if (pendingEhtRoutePoints.length) {
            cancelPendingEhtRoute();
        } else {
            setActiveEhtTool("");
        }
        clearEhtPlacementPreview();
    }
    if (event.key === 'Escape' && pendingEhtGeometryEdit) {
        cancelPendingEhtGeometryEdit();
    }
    if ((event.key === 'Enter' || event.key === ' ') && activeEhtTool && pendingEhtRoutePoints.length >= 2) {
        event.preventDefault();
        finishPendingEhtRoute();
    }
}

document.addEventListener('keydown', handleGlobalKeyDown, true);

if (document.getElementById('ppScale')) {
    document.getElementById('ppScale').addEventListener('input', updatePlotPlan);
    document.getElementById('ppOffsetX').addEventListener('input', updatePlotPlan);
    document.getElementById('ppOffsetZ').addEventListener('input', updatePlotPlan);

    document.getElementById('btnCenterMap').addEventListener('click', () => {
        document.getElementById('ppOffsetX').value = Math.round(controls.target.x);
        document.getElementById('ppOffsetZ').value = Math.round(controls.target.z);
        updatePlotPlan();
    });
}
// -------------------------------------------------

const nearestIfcInput = document.getElementById('nearestIfcInput');
const nearestStructureBtn = document.getElementById('runNearestStructureBtn');
const nearestStructureStatus = document.getElementById('nearestStructureStatus');
const nearestStructureResults = document.getElementById('nearestStructureResults');

function findLeafKeyForPipelineLine(lineKey, lineLabel) {
    for (const [leafKey, mesh] of leafRepresentatives.entries()) {
        const props = getItemProperties(mesh.userData.item);
        const candidateLineKey = String(props.pipeline_ref || props.spool_ref || "").trim();
        const candidateLabel = getHierarchyLeafLabel(mesh.userData.item);
        if ((lineKey && candidateLineKey === lineKey) || (lineLabel && candidateLabel === lineLabel)) {
            return leafKey;
        }
    }
    return "";
}

function renderNearestStructureResults(payload) {
    if (!nearestStructureResults) return;

    const rows = payload.results || [];
    const summary = payload.summary || {};
    if (!rows.length) {
        nearestStructureResults.classList.add('hidden');
        if (nearestStructureStatus) {
            nearestStructureStatus.textContent = summary.warning || 'No nearest-structure matches were produced from the uploaded IFC files.';
        }
        return;
    }

    if (nearestStructureStatus) {
        const baseSummary = `Analyzed ${summary.line_count || 0} pipeline lines against ${summary.ifc_object_count || 0} IFC objects from ${payload.ifc_source_label || 'the uploaded IFC files'}.`;
        nearestStructureStatus.textContent = summary.warning ? `${baseSummary} ${summary.warning}` : baseSummary;
    }

    nearestStructureResults.classList.remove('hidden');
    nearestStructureResults.innerHTML = `
        <div class="border-b border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Ranked By Nearest Approximate Distance
        </div>
        ${summary.warning ? `
            <div class="border-b border-amber-200 bg-amber-50 px-3 py-2 text-[10px] leading-relaxed text-amber-800">
                ${escapeHtml(summary.warning)}
            </div>
        ` : ''}
        <div class="divide-y divide-slate-100">
            ${rows.map((row) => {
                const distanceClass = row.distance_m <= 0.5
                    ? 'text-emerald-700'
                    : row.distance_m <= 2.0
                        ? 'text-amber-700'
                        : 'text-slate-700';
                const title = row.component_ref || row.name || row.ifc_class;
                return `
                    <button type="button" class="nearest-result-row w-full px-3 py-3 text-[11px] text-left hover:bg-slate-50 transition" data-line-key="${escapeHtml(row.line_key || '')}" data-line-label="${escapeHtml(row.line_label || '')}">
                        <div class="flex items-start justify-between gap-3">
                            <div class="min-w-0">
                                <div class="font-semibold text-slate-800 truncate" title="${escapeHtml(row.line_label)}">${escapeHtml(row.line_label)}</div>
                                <div class="mt-1 truncate text-slate-500" title="${escapeHtml(title)}">${escapeHtml(title)}</div>
                            </div>
                            <div class="text-right">
                                <div class="font-semibold ${distanceClass}">${escapeHtml(row.distance_m.toFixed(3))} m</div>
                                <div class="text-[10px] text-slate-400">${escapeHtml(Math.round(row.distance_mm))} mm</div>
                            </div>
                        </div>
                        <div class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-slate-500">
                            <div><span class="font-medium text-slate-600">IFC Class:</span> ${escapeHtml(row.ifc_class || '')}</div>
                            <div><span class="font-medium text-slate-600">Storey:</span> ${escapeHtml(row.storey_name || 'Unknown')}</div>
                            <div><span class="font-medium text-slate-600">Ref:</span> ${escapeHtml(row.component_ref || 'N/A')}</div>
                            <div><span class="font-medium text-slate-600">File:</span> ${escapeHtml(row.ifc_file || '')}</div>
                        </div>
                    </button>
                `;
            }).join('')}
        </div>
    `;

    nearestStructureResults.querySelectorAll('.nearest-result-row').forEach((button) => {
        button.addEventListener('click', () => {
            const leafKey = findLeafKeyForPipelineLine(button.dataset.lineKey, button.dataset.lineLabel);
            if (leafKey) {
                selectLeafKey(leafKey, { isolate: true, refit: true });
            } else if (nearestStructureStatus) {
                nearestStructureStatus.textContent = `The report found ${button.dataset.lineLabel}, but that line is not currently available in the visible hierarchy.`;
            }
        });
    });
}

if (nearestStructureBtn) {
    const activeSceneFormat = String((sceneData.stats || {}).source_format || '').toUpperCase();
    if (activeSceneFormat === 'IFC') {
        nearestStructureBtn.disabled = true;
        nearestStructureBtn.classList.add('opacity-50', 'cursor-not-allowed');
        if (nearestStructureStatus) {
            nearestStructureStatus.textContent = 'Open an IDF or PCF pipeline scene first, then compare it against IFC reference files here.';
        }
    } else {
        nearestStructureBtn.addEventListener('click', async () => {
            if (!nearestIfcInput || !nearestIfcInput.files || !nearestIfcInput.files.length) {
                if (nearestStructureStatus) {
                    nearestStructureStatus.textContent = 'Choose one or more IFC files before running the nearest-structure analysis.';
                }
                return;
            }

            const originalLabel = nearestStructureBtn.textContent;
            nearestStructureBtn.disabled = true;
            nearestStructureBtn.textContent = 'Analyzing...';
            if (nearestStructureStatus) {
                nearestStructureStatus.textContent = 'Parsing IFC reference files and comparing them against the active pipeline scene...';
            }

            const formData = new FormData();
            formData.append('scene', JSON.stringify(sceneData));
            Array.from(nearestIfcInput.files).forEach((file) => {
                formData.append('ifc_files', file);
            });

            try {
                const response = await fetch(nearestStructureBtn.dataset.analyzeUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookieValue('csrftoken'),
                    },
                    body: formData,
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || 'Unable to analyze the nearest structure for the current scene.');
                }
                renderNearestStructureResults(payload);
            } catch (error) {
                nearestStructureResults.classList.add('hidden');
                if (nearestStructureStatus) {
                    nearestStructureStatus.textContent = error.message || 'Unable to analyze the nearest structure for the current scene.';
                }
            } finally {
                nearestStructureBtn.disabled = false;
                nearestStructureBtn.textContent = originalLabel;
            }
        });
    }
}

window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

animate();
