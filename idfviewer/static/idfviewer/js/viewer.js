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

scene.add(new THREE.GridHelper(300, 30, 0x888888, 0xb0b0b0));
scene.add(new THREE.AxesHelper(80));

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

function addPipe(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, 0.7, 0x555555, item, selectGroup);
}

function addFitting(item) {
    const selectGroup = [];
    addCylinderBetweenPoints(item.start, item.end, 1.0, 0x2563eb, item, selectGroup);

    const midpoint = [
        (item.start[0] + item.end[0]) / 2,
        (item.start[1] + item.end[1]) / 2,
        (item.start[2] + item.end[2]) / 2,
    ];
    addSphere(midpoint, 0x2563eb, 1.5, item, selectGroup);
}

function addWeld(item) {
    const selectGroup = [];
    addSphere(item.point, 0xdc2626, 1.5, item, selectGroup);
}

function addSupport(item) {
    const selectGroup = [];
    addCube(item.point, 0x16a34a, 3.2, item, selectGroup);
}

function addMarker(item) {
    const selectGroup = [];
    addSphere(item.point, 0xea580c, 1.8, item, selectGroup);
}

(sceneData.pipes || []).forEach(addPipe);
(sceneData.fittings || []).forEach(addFitting);
(sceneData.welds || []).forEach(addWeld);
(sceneData.supports || []).forEach(addSupport);
(sceneData.markers || []).forEach(addMarker);

function fitCameraToObject(object) {
    const box = new THREE.Box3().setFromObject(object);

    if (box.isEmpty()) {
        camera.position.set(120, 120, 120);
        controls.target.set(0, 0, 0);
        controls.update();
        return;
    }

    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const center = sphere.center.clone();
    const radius = Math.max(sphere.radius, 10);

    const offset = new THREE.Vector3(1.4, 1.0, 1.2).normalize().multiplyScalar(radius * 2.8);

    camera.position.copy(center.clone().add(offset));
    camera.near = Math.max(radius / 100, 0.1);
    camera.far = radius * 100;
    camera.updateProjectionMatrix();
    camera.lookAt(center);

    controls.target.copy(center);
    controls.minDistance = radius * 0.25;
    controls.maxDistance = radius * 25;
    controls.update();
}

fitCameraToObject(modelGroup);

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

    let materialsHtml = "<div>No materials listed.</div>";
    if (p.materials && p.materials.length) {
        const nonEmpty = p.materials.filter(m => (m.code || m.description));
        if (nonEmpty.length) {
            materialsHtml = `
                <table>
                    <thead>
                        <tr><th>Code</th><th>Description</th></tr>
                    </thead>
                    <tbody>
                        ${nonEmpty.map(m => `
                            <tr>
                                <td>${escapeHtml(m.code)}</td>
                                <td>${escapeHtml(m.description)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        }
    }

    const notesHtml = (p.notes && p.notes.length)
        ? `<ul>${p.notes.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>`
        : "<div>No notes.</div>";

    const rawCoords = p.raw_point
        ? `Point: ${escapeHtml(JSON.stringify(p.raw_point))}`
        : `Start: ${escapeHtml(JSON.stringify(p.raw_start || []))}<br>End: ${escapeHtml(JSON.stringify(p.raw_end || []))}`;

    propsContent.innerHTML = `
        <div class="section"><span class="label">Kind:</span> ${escapeHtml(p.kind || "")}</div>
        <div class="section"><span class="label">Record ID:</span> ${escapeHtml(p.record_id || "")}</div>
        <div class="section"><span class="label">Inline code:</span> ${escapeHtml(p.inline_code || "")}</div>
        <div class="section"><span class="label">Component ref:</span> ${escapeHtml(p.component_ref || "")}</div>
        <div class="section"><span class="label">Pipeline ref:</span> ${escapeHtml(p.pipeline_ref || "")}</div>
        <div class="section"><span class="label">Support code:</span> ${escapeHtml(p.support_code || "")}</div>
        <div class="section">
            <div class="label">Notes:</div>
            ${notesHtml}
        </div>
        <div class="section">
            <div class="label">Materials:</div>
            ${materialsHtml}
        </div>
        <div class="section">
            <div class="label">Raw coordinates:</div>
            <pre>${rawCoords}</pre>
        </div>
        <div class="section">
            <div class="label">Raw metadata:</div>
            <pre>${escapeHtml(JSON.stringify(p.raw_meta || {}, null, 2))}</pre>
        </div>
    `;
}

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
            mesh.material.emissive.setHex(0xffff00);
        }
    });
}

renderer.domElement.addEventListener("click", (event) => {
    const rect = renderer.domElement.getBoundingClientRect();

    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(selectableMeshes, false);

    if (!hits.length) {
        clearHighlight();
        propsContent.innerHTML = "Click any pipe, fitting, weld, support, or marker.";
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