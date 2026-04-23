import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const sceneDataEl = document.getElementById('scene-data');
const container = document.getElementById('viewer');
const propsContent = document.getElementById('props-content');
const pageBody = document.body;
const navPanelToggleBtn = document.getElementById('navpanel-toggle');
const navPanelReopenBtn = document.getElementById('navpanel-reopen');
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
const mouse = new THREE.Vector2();
const selectableMeshes = [];
const manuallyHiddenItems = new Set();
const contextLabels = [];
const leafRepresentatives = new Map();
let hierarchySearchMatches = new Set();

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
                <label class="flex items-center text-xs font-medium text-gray-700 p-1 rounded hover:bg-black/5 transition cursor-pointer">
                    <input type="checkbox" class="file-toggle mr-2 h-3.5 w-3.5 text-blue-500 rounded border-gray-300 focus:ring-0" checked data-file="${escapeHtml(file)}">
                    <span class="truncate" title="${escapeHtml(file)}">${escapeHtml(file)}</span>
                </label>
                <div class="hierarchy-file-children pl-5 mt-1 border-l border-gray-100 space-y-1 py-1">
        `;

        groups.forEach(groupEntry => {
            const isIfcGroup = groupEntry.sourceFormat === "IFC";
            const sortedItems = groupEntry.items.sort((a, b) => a.leafLabel.localeCompare(b.leafLabel));

            if (isIfcGroup) {
                html += `
                    <div class="hierarchy-group" data-group-key="${escapeHtml(groupEntry.groupKey)}" data-file="${escapeHtml(file)}">
                        <label class="flex items-center text-gray-600 hover:text-gray-900 transition cursor-pointer text-[11px] font-medium tracking-wide">
                            <input type="checkbox" class="group-toggle mr-2 h-3 w-3 text-gray-500 rounded border-gray-200 focus:ring-0" checked data-file="${escapeHtml(file)}" data-group-key="${escapeHtml(groupEntry.groupKey)}">
                            <span class="truncate" title="${escapeHtml(groupEntry.group)}">${escapeHtml(groupEntry.group)}</span>
                        </label>
                        <div class="pl-4 mt-1 border-l border-gray-100 space-y-1">
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

    if (hierarchySearchStatus) {
        if (!query) {
            hierarchySearchStatus.textContent = 'Search the current hierarchy';
        } else {
            hierarchySearchStatus.textContent = hierarchySearchMatches.size
                ? `${hierarchySearchMatches.size} match${hierarchySearchMatches.size === 1 ? '' : 'es'}`
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
    const minimumRadius = hasVisibleIfcGeometry ? 0.5 : 10;
    const radius = Math.max(sphere.radius, minimumRadius);
    
    // Dynamically adjust Grid and Axes to match the viewed content box
    scene.remove(gridHelper);
    scene.remove(axesHelper);
    
    const maxDim = radius * 2;
    const gridDim = Math.max(maxDim * 1.5, 10);
    gridHelper = new THREE.GridHelper(gridDim, 30, 0x888888, 0xb0b0b0);
    gridHelper.position.y = box.min.y;
    gridHelper.position.x = center.x;
    gridHelper.position.z = center.z;
    scene.add(gridHelper);
    
    const axesSize = Math.max(maxDim * 0.5, 5);
    axesHelper = new THREE.AxesHelper(axesSize);
    axesHelper.position.copy(gridHelper.position);
    scene.add(axesHelper);
    syncGroundPlaneToGrid();

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
    const rect = renderer.domElement.getBoundingClientRect();

    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    // Ignore hidden objects during raycast
    const hits = raycaster.intersectObjects(selectableMeshes.filter(m => m.visible && m.parent), false);

    if (!hits.length) {
        clearHighlight();
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
    selectedGroup = selectGroup;
    applyHighlight(selectGroup);
    renderProperties(item);
});

renderer.domElement.addEventListener("dblclick", (event) => {
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
