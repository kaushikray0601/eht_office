import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const sceneDataEl = document.getElementById('scene-data');
const container = document.getElementById('viewer');
const propsContent = document.getElementById('props-content');

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

const modelGroup = new THREE.Group();
scene.add(modelGroup);

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const selectableMeshes = [];

let selectedGroup = null;

function vecFromArray(a) {
    return new THREE.Vector3(a[0], a[1], a[2]);
}

function registerSelectable(mesh, item, selectGroup) {
    mesh.userData.item = item;
    mesh.userData.selectGroup = selectGroup;
    selectableMeshes.push(mesh);
}

function addCylinderBetweenPoints(startArr, endArr, radius, color, item, selectGroup) {
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
        registerSelectable(s, item, selectGroup);
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
    registerSelectable(cylinder, item, selectGroup);
    selectGroup.push(cylinder);
    return cylinder;
}

function addSphere(pointArr, color, radius, item, selectGroup) {
    const geometry = new THREE.SphereGeometry(radius, 14, 14);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    modelGroup.add(mesh);
    registerSelectable(mesh, item, selectGroup);
    selectGroup.push(mesh);
    return mesh;
}

function addCube(pointArr, color, size, item, selectGroup) {
    const geometry = new THREE.BoxGeometry(size, size, size);
    const material = new THREE.MeshStandardMaterial({ color });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(vecFromArray(pointArr));
    modelGroup.add(mesh);
    registerSelectable(mesh, item, selectGroup);
    selectGroup.push(mesh);
    return mesh;
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
    markerRad: baseRadius * 2.5
};

function addPipe(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, sizes.pipeRad, 0x555555, item, selectGroup);
}

function addFitting(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, sizes.fittingRad, 0x2563eb, item, selectGroup);

    const midpoint = [(item.start[0] + item.end[0]) / 2, (item.start[1] + item.end[1]) / 2, (item.start[2] + item.end[2]) / 2];
    addSphere(midpoint, 0x2563eb, sizes.fittingGlandRad, item, selectGroup);
}

function addWeld(item) {
    const selectGroup = [];
    addSphere(item.point, 0xdc2626, sizes.weldRad, item, selectGroup);
}

function addSupport(item) {
    const selectGroup = [];
    addCube(item.point, 0x16a34a, sizes.supportSize, item, selectGroup);
}

function addMarker(item) {
    const selectGroup = [];
    addSphere(item.point, 0xea580c, sizes.markerRad, item, selectGroup);
}

(sceneData.pipes || []).forEach(addPipe);
(sceneData.fittings || []).forEach(addFitting);
(sceneData.welds || []).forEach(addWeld);
(sceneData.supports || []).forEach(addSupport);
(sceneData.markers || []).forEach(addMarker);

// ----------- HIERARCHY TREE GENERATION -----------
const hierarchy = {}; 
selectableMeshes.forEach(mesh => {
    const p = mesh.userData.item.properties || {};
    const file = p.filename || "Unknown File";
    const pipe = p.pipeline_ref || p.spool_ref || "Unknown Line";
    
    if (!hierarchy[file]) hierarchy[file] = {};
    if (!hierarchy[file][pipe]) hierarchy[file][pipe] = [];
    hierarchy[file][pipe].push(mesh);
});

const hContent = document.getElementById("hierarchy-content");
if (hContent) {
    let html = "";
    Object.keys(hierarchy).forEach(file => {
        html += `
        <div class="mb-2">
            <label class="flex items-center text-xs font-medium text-gray-700 p-1 rounded hover:bg-black/5 transition cursor-pointer">
                <input type="checkbox" class="file-toggle mr-2 h-3.5 w-3.5 text-blue-500 rounded border-gray-300 focus:ring-0" checked data-file="${escapeHtml(file)}"> 
                <span class="truncate" title="${escapeHtml(file)}">${escapeHtml(file)}</span>
            </label>
            <div class="pl-5 mt-1 border-l border-gray-100 space-y-1 py-1">
        `;
        Object.keys(hierarchy[file]).forEach(pipe => {
            html += `
            <label class="flex items-center text-gray-500 hover:text-gray-800 transition cursor-pointer text-[11px] font-normal tracking-wide">
                <input type="checkbox" class="pipe-toggle mr-2 h-3 w-3 text-gray-400 rounded border-gray-200 focus:ring-0" checked data-file="${escapeHtml(file)}" data-pipe="${escapeHtml(pipe)}"> 
                <span class="truncate" title="${escapeHtml(pipe)}">${escapeHtml(pipe)}</span>
            </label>
            `;
        });
        html += `</div></div>`;
    });
    hContent.innerHTML = html || "<span class='text-gray-400'>No hierarchy data found.</span>";

    function updateVisibility() {
        const activePipes = new Set();
        document.querySelectorAll('.pipe-toggle:checked').forEach(cb => {
            activePipes.add(cb.dataset.file + "___" + cb.dataset.pipe);
        });
        
        selectableMeshes.forEach(mesh => {
            const p = mesh.userData.item.properties || {};
            const file = p.filename || "Unknown File";
            const pipe = p.pipeline_ref || p.spool_ref || "Unknown Line";
            const key = file + "___" + pipe;
            mesh.visible = activePipes.has(key);
        });
        
        fitCameraToObject(modelGroup);
    }

    document.querySelectorAll('.file-toggle').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const file = e.target.dataset.file;
            document.querySelectorAll(`.pipe-toggle[data-file="${file}"]`).forEach(pcb => {
                pcb.checked = isChecked;
            });
            updateVisibility();
        });
    });

    document.querySelectorAll('.pipe-toggle').forEach(cb => {
        cb.addEventListener('change', updateVisibility);
    });
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
    const radius = Math.max(sphere.radius, 10);
    
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
    selectedGroup.forEach(mesh => mesh.visible = false);
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
        modelGroup.traverse(node => {
            if (node.isMesh) node.visible = true;
        });
        btnShowHidden.classList.add('hidden');
        fitCameraToObject(modelGroup);
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

function renderProperties(item) {
    const p = item.properties || {};
    const activeFilters = Array.from(document.querySelectorAll('.prop-filter'))
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    let html = `
        <div class="prop-row"><span class="prop-key">Kind</span><span class="prop-val">${escapeHtml(p.kind || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Record ID</span><span class="prop-val">${escapeHtml(p.record_id || "")}</span></div>
        <div class="prop-row"><span class="prop-key">File Source</span><span class="prop-val">${escapeHtml(p.filename || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Inline code</span><span class="prop-val">${escapeHtml(p.inline_code || "")}</span></div>
        <div class="prop-row"><span class="prop-key">Component ref</span><span class="prop-val">${escapeHtml(p.component_ref || "")}</span></div>
    `;

    if (activeFilters.includes("pipeline_ref")) {
        html += `<div class="prop-row"><span class="prop-key">Pipeline System</span><span class="prop-val font-semibold text-blue-700">${escapeHtml(p.pipeline_ref || p.spool_ref || "Unknown")}</span></div>`;
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

    const notesHtml = (p.notes && p.notes.length)
        ? `<ul class="list-disc pl-4 text-xs text-red-600 space-y-1">${p.notes.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>`
        : "<span class='text-gray-400 italic'>No notes.</span>";
    html += `<div class="prop-row"><span class="prop-key mb-1">Notes & Warnings</span><div class="prop-val">${notesHtml}</div></div>`;

    if (activeFilters.includes("raw_coords")) {
        const rawCoords = p.raw_point
            ? `Point: ${escapeHtml(JSON.stringify(p.raw_point))}`
            : `Start: ${escapeHtml(JSON.stringify(p.raw_start || []))}\nEnd: ${escapeHtml(JSON.stringify(p.raw_end || []))}`;
        html += `<div class="prop-row"><span class="prop-key mb-1">Raw Coordinates</span><pre class="prop-val bg-gray-100 p-2 rounded text-xs overflow-x-auto border">${rawCoords}</pre></div>`;
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
                <p>Click on any pipe, fitting, weld, support, or marker to view its details.</p>
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
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -2; // Send ground slightly down so z-fighting doesn't happen with 0-origin pipes
scene.add(ground);

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