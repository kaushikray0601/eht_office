import os

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import SimpleTestCase
from django.urls import reverse
from playwright.sync_api import sync_playwright

from .tests import assign_project, create_project, create_source_and_package


class RacewayBrowserSmokeTests(SimpleTestCase):
    def test_raceway_authoring_uses_viewer_interaction_contract(self):
        script_path = os.path.join(
            os.path.dirname(__file__),
            "static",
            "raceway",
            "js",
            "raceway_overlay.js",
        )
        console_messages = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1000, "height": 700})
                page.on("console", lambda message: console_messages.append(f"{message.type}: {message.text}"))
                page.set_content(
                    """
                    <!doctype html>
                    <html>
                    <head></head>
                    <body>
                      <details open>
                        <summary>Reference Layers</summary>
                        <div id="viewerLayerList"></div>
                      </details>
                      <div id="viewerCanvas" style="width:600px;height:360px;background:#eef2f7;"></div>
                      <script>
                        class Vector3 {
                          constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
                          copy(other) { this.x = other.x; this.y = other.y; this.z = other.z; return this; }
                        }
                        class Group {
                          constructor() { this.children = []; this.userData = {}; this.visible = true; }
                          add(child) { this.children.push(child); child.parent = this; }
                          traverse(callback) { callback(this); this.children.forEach(child => child.traverse ? child.traverse(callback) : callback(child)); }
                        }
                        class BufferGeometry {
                          setFromPoints(points) { this.points = points; return this; }
                          dispose() {}
                        }
                        class LineBasicMaterial { constructor(config) { this.config = config; } dispose() {} }
                        class MeshBasicMaterial { constructor(config) { this.config = config; } dispose() {} }
                        class SphereGeometry { constructor(radius) { this.radius = radius; } dispose() {} }
                        class Line {
                          constructor(geometry, material) { this.geometry = geometry; this.material = material; this.position = new Vector3(); this.userData = {}; }
                          traverse(callback) { callback(this); }
                        }
                        class Mesh {
                          constructor(geometry, material) { this.geometry = geometry; this.material = material; this.position = new Vector3(); this.userData = {}; }
                          traverse(callback) { callback(this); }
                        }

                        const layers = new Map();
                        ['model', 'measurement', 'reference-grid', 'plot-plan', 'eht-draft'].forEach(id => {
                          layers.set(id, { id, group: new Group(), getElements: () => [] });
                        });
                        window.plant3dViewerLayers = {
                          ids: () => Array.from(layers.keys()),
                          register: config => {
                            const layer = { ...config, group: config.createGroup ? new Group() : null };
                            layers.set(config.id, layer);
                            return layer;
                          },
                          update: (id, patch) => {
                            const layer = layers.get(id);
                            if (!layer) return null;
                            Object.assign(layer, patch);
                            return layer;
                          },
                          isVisible: id => layers.get(id)?.group?.visible !== false,
                        };

                        const canvas = document.getElementById('viewerCanvas');
                        let activeInteraction = null;
                        window.__racewayRenderCount = 0;
                        const catalogPayload = {
                          families: [
                            {
                              id: 1,
                              code: 'LADDER-HDG',
                              name: 'Ladder HDG',
                              kind: 'ladder',
                              material: 'HDG steel',
                              standard_basis: 'IEC 61537',
                              is_validated: false,
                              sizes: [
                                { id: 11, code: 'LADDER-HDG-300x100', label: '300 x 100 mm', width_mm: 300, depth_mm: 100, is_active: true },
                                { id: 12, code: 'LADDER-HDG-450x100', label: '450 x 100 mm', width_mm: 450, depth_mm: 100, is_active: true },
                                { id: 13, code: 'LADDER-HDG-600x150', label: '600 x 150 mm', width_mm: 600, depth_mm: 150, is_active: true },
                              ],
                            },
                            {
                              id: 2,
                              code: 'PERF-HDG',
                              name: 'Perforated HDG',
                              kind: 'perforated_tray',
                              material: 'HDG steel',
                              standard_basis: 'IEC 61537',
                              is_validated: false,
                              sizes: [
                                { id: 21, code: 'PERF-HDG-150x50', label: '150 x 50 mm', width_mm: 150, depth_mm: 50, is_active: true },
                              ],
                            },
                          ],
                        };
                        window.__racewayFetchLog = [];
                        window.fetch = async (url, options = {}) => {
                          const method = options.method || 'GET';
                          const body = options.body ? JSON.parse(options.body) : null;
                          window.__racewayFetchLog.push({ url: String(url), method, body });
                          if (String(url).startsWith('/raceway/catalog/')) {
                            return { ok: true, status: 200, json: async () => catalogPayload };
                          }
                          if (String(url).startsWith('/raceway/projects/RWY-BROWSER/layers/') && method === 'GET') {
                            return { ok: true, status: 200, json: async () => ({ layers: [] }) };
                          }
                          if (String(url).startsWith('/raceway/projects/RWY-BROWSER/layers/') && method === 'POST') {
                            return {
                              ok: true,
                              status: 201,
                              json: async () => ({ layer: { id: 91, url: '/raceway/layers/91/', runs_url: '/raceway/layers/91/runs/' } }),
                            };
                          }
                          if (String(url).startsWith('/raceway/layers/91/runs/') && method === 'POST') {
                            return {
                              ok: true,
                              status: 201,
                              json: async () => ({
                                run: { id: 501, key: 'run-key', nodes_url: '/raceway/runs/501/nodes/' },
                              }),
                            };
                          }
                          if (String(url).startsWith('/raceway/runs/501/nodes/') && method === 'PUT') {
                            return {
                              ok: true,
                              status: 200,
                              json: async () => ({
                                nodes: body.nodes.map((node, index) => ({
                                  id: 900 + index,
                                  key: `node-${index}`,
                                  sequence: node.sequence,
                                  source_x_m: node.source_x_m,
                                  source_y_m: node.source_y_m,
                                  source_z_m: node.source_z_m,
                                  metadata: {},
                                  anchor: node.anchor || {},
                                })),
                              }),
                            };
                          }
                          if (String(url).startsWith('/raceway/runs/501/') && method === 'DELETE') {
                            return { ok: true, status: 200, json: async () => ({ status: 'deleted', run_id: 501 }) };
                          }
                          return { ok: false, status: 404, json: async () => ({ error: 'Unexpected fetch in smoke test.' }) };
                        };

                        window.plant3dViewerRuntime = {
                          THREE: { Vector3, Group, BufferGeometry, LineBasicMaterial, MeshBasicMaterial, SphereGeometry, Line, Mesh },
                          canvas,
                          getPackage: () => ({ id: 77, project_id: 'RWY-BROWSER', source_model_id: 55, metadata: {} }),
                          getSelectedModelAnchor: () => ({
                            owner_module: 'plant3d',
                            anchor_kind: 'model_object',
                            render_package_id: 77,
                            source_model_id: 55,
                            model_object_id: 44,
                            stable_id: 'ifc:pump-001',
                            source_object_id: 'Pump-001',
                            object_type: 'IfcPump',
                            label: 'P-001',
                            bounds: { min_x: 40, max_x: 50, min_y: 55, max_y: 59, min_z: 0, max_z: 3 },
                            source_point_m: { x: 45, y: 57, z: 1.5, coordinate_frame: 'source_xyz_m' },
                            feature_id: null,
                          }),
                          modelAnchorFromViewerEvent: event => ({
                            owner_module: 'plant3d',
                            anchor_kind: 'model_object',
                            render_package_id: 77,
                            source_model_id: 55,
                            model_object_id: 44,
                            stable_id: 'ifc:steel-001',
                            source_object_id: 'Steel-001',
                            object_type: 'IfcBeam',
                            label: 'ST-001',
                            bounds: { min_x: 10, max_x: 40, min_y: 8, max_y: 20, min_z: 1, max_z: 3 },
                            source_point_m: {
                              x: event.clientX / 10,
                              y: event.clientY / 10,
                              z: event.clientX >= 300 ? 2.5 : event.clientX >= 200 ? 1.5 : 1.0,
                              coordinate_frame: 'source_xyz_m',
                            },
                            feature_id: 88,
                          }),
                          currentSourceElevationM: () => 1.0,
                          pointOnSourceElevationFromViewerEvent: (event, elevation) => new Vector3(event.clientX / 10, elevation, event.clientY / 10),
                          renderPointToSourcePoint: point => ({ x: point.x, y: point.z, z: point.y, coordinate_frame: 'source_xyz_m' }),
                          sourcePointToRenderPoint: point => new Vector3(point.x, point.z, point.y),
                          raycastObjectsFromViewerEvent: (event, objects) => objects
                            .map(object => {
                              const dx = object.position.x - (event.clientX / 10);
                              const dz = object.position.z - (event.clientY / 10);
                              const distance = Math.sqrt((dx * dx) + (dz * dz));
                              const radius = object.geometry?.radius || 0.2;
                              return distance <= Math.max(radius, 0.25) ? { object, distance } : null;
                            })
                            .filter(Boolean)
                            .sort((left, right) => left.distance - right.distance),
                          worldUnitsForScreenPixels: () => 0.1,
                          renderNow: () => { window.__racewayRenderCount += 1; },
                          registerInteraction: config => ({
                            activate: () => { activeInteraction = config; },
                            deactivate: () => { if (activeInteraction === config) activeInteraction = null; },
                            isActive: () => activeInteraction === config,
                          }),
                        };
                        let pointerStart = null;
                        let suppressNextInteractionClick = false;
                        window.__racewayCanvasClickCount = 0;
                        canvas.addEventListener('pointerdown', event => {
                          pointerStart = { x: event.clientX, y: event.clientY };
                          suppressNextInteractionClick = false;
                        });
                        canvas.addEventListener('pointermove', event => {
                          if (!pointerStart) return;
                          const dx = event.clientX - pointerStart.x;
                          const dy = event.clientY - pointerStart.y;
                          if ((dx * dx) + (dy * dy) > 36) suppressNextInteractionClick = true;
                        });
                        canvas.addEventListener('pointerup', () => { pointerStart = null; });
                        canvas.addEventListener('click', event => {
                          window.__racewayCanvasClickCount += 1;
                          if (suppressNextInteractionClick) {
                            suppressNextInteractionClick = false;
                            activeInteraction?.onNavigationClick?.(event);
                            return;
                          }
                          if (activeInteraction?.onCanvasClick) activeInteraction.onCanvasClick(event);
                        });
                      </script>
                    </body>
                    </html>
                    """,
                    wait_until="domcontentloaded",
                )

                page.add_script_tag(path=script_path)
                page.wait_for_selector("#racewayToolSection", timeout=5000)
                page.wait_for_function("() => window.plant3dViewerLayers.ids().includes('raceway-overlay')")
                page.wait_for_function("() => document.querySelector('#racewaySizeSelect option[value=\"12\"]')")
                layer_ids = page.evaluate("() => window.plant3dViewerLayers.ids()")
                self.assertIn("model", layer_ids)
                self.assertIn("measurement", layer_ids)
                self.assertIn("eht-draft", layer_ids)
                self.assertIn("raceway-overlay", layer_ids)
                self.assertTrue(page.eval_on_selector('[data-raceway-action="finish"]', "el => el.disabled"))
                self.assertTrue(page.eval_on_selector('[data-raceway-action="save"]', "el => el.disabled"))
                page.click('[data-raceway-action="start"]')
                page.click("#viewerCanvas", position={"x": 120, "y": 90})
                page.click("#viewerCanvas", position={"x": 220, "y": 130})
                page.click("#viewerCanvas", position={"x": 320, "y": 90})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes[1]?.anchor?.stable_id === 'ifc:steel-001'")
                auto_anchored_nodes = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0].nodes.map(node => ({ z: node.z, anchor: node.anchor?.stable_id || '' }))")
                self.assertEqual([node["anchor"] for node in auto_anchored_nodes], ["ifc:steel-001", "ifc:steel-001", "ifc:steel-001"])
                self.assertGreater(round(auto_anchored_nodes[2]["z"], 3), round(auto_anchored_nodes[0]["z"], 3))
                page.dispatch_event("#viewerCanvas", "pointerdown", {"clientX": 160, "clientY": 120})
                page.dispatch_event("#viewerCanvas", "pointermove", {"clientX": 260, "clientY": 180})
                page.dispatch_event("#viewerCanvas", "pointerup", {"clientX": 260, "clientY": 180})
                page.dispatch_event("#viewerCanvas", "click", {"clientX": 260, "clientY": 180})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                self.assertIn("navigation gesture ignored", page.text_content("#racewayToolStatus"))
                preview_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.group.children
                        .flatMap((runGroup) => runGroup.children.map((child) => child.userData?.racewayPreviewKind))
                        .filter(Boolean)
                    """
                )
                self.assertIn("side-rail", preview_kinds)
                self.assertIn("rung", preview_kinds)
                self.assertIn("bend-placeholder", preview_kinds)
                self.assertIn("node-handle", preview_kinds)
                self.assertIn("node-hit-target", preview_kinds)
                self.assertIn("riser-placeholder", preview_kinds)
                depth_tick_points = page.evaluate(
                    """() => {
                        const tick = window.racewayViewerOverlay.layer.group.children
                          .flatMap((runGroup) => runGroup.children)
                          .find((child) => child.userData?.racewayPreviewKind === 'depth-tick');
                        return tick.geometry.points.map((point) => ({ x: point.x, y: point.y, z: point.z }));
                    }"""
                )
                self.assertGreater(depth_tick_points[1]["y"], depth_tick_points[0]["y"])

                page.click('[data-raceway-action="select-node"][data-node-index="1"]')
                page.click('[data-raceway-action="anchor-node"]')
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.nodes[1]?.anchor?.stable_id === 'ifc:pump-001'"
                )

                page.click('[data-raceway-action="finish"]')
                page.click('[data-raceway-action="save"]')
                page.wait_for_function(
                    "() => window.__racewayFetchLog.some((entry) => entry.url.includes('/nodes/') && entry.method === 'PUT')"
                )
                saved_nodes = page.evaluate(
                    "() => window.__racewayFetchLog.find((entry) => entry.url.includes('/nodes/') && entry.method === 'PUT').body.nodes"
                )
                self.assertEqual(len(saved_nodes), 3)
                self.assertEqual(saved_nodes[0]["node_kind"], "endpoint")
                self.assertEqual(saved_nodes[1]["node_kind"], "bend")
                self.assertEqual(saved_nodes[1]["anchor"]["stable_id"], "ifc:pump-001")
                self.assertEqual(saved_nodes[1]["anchor"]["owner_module"], "raceway")
                self.assertNotIn("feature_id", saved_nodes[1]["anchor"])
                self.assertEqual(round(saved_nodes[1]["source_z_m"], 3), 1.5)

                page.select_option("#racewaySizeSelect", "12")
                page.select_option("#racewayServiceSelect", "control")
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.widthMm === 450 && window.racewayViewerOverlay.getRuns()[0]?.serviceClass === 'control'"
                )
                page.wait_for_function("() => document.querySelector('#racewaySummary')?.textContent.includes('unsaved changes')")

                page.click('[data-raceway-action="undo"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 2")

                node_before_move = page.evaluate("() => ({ ...window.racewayViewerOverlay.getRuns()[0].nodes[0] })")
                page.click('[data-raceway-action="select-node-mode"]')
                page.dispatch_event(
                    "#viewerCanvas",
                    "click",
                    {"clientX": node_before_move["x"] * 10, "clientY": node_before_move["y"] * 10},
                )
                page.wait_for_timeout(100)
                selection_diagnostic = page.evaluate(
                    """() => ({
                        status: document.querySelector('#racewayToolStatus')?.textContent || '',
                        clickCount: window.__racewayCanvasClickCount,
                        nodeRows: Array.from(document.querySelectorAll('[data-raceway-action="select-node"]')).map(row => ({
                          index: row.dataset.nodeIndex,
                          active: row.classList.contains('raceway-row-active'),
                        })),
                    })"""
                )
                self.assertIn("node 1 selected", selection_diagnostic["status"], selection_diagnostic)
                page.click('[data-raceway-action="move-node"]')
                page.click("#viewerCanvas", position={"x": 320, "y": 170})
                moved_node = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0].nodes[0]")
                self.assertNotEqual(round(moved_node["x"], 3), round(node_before_move["x"], 3))
                self.assertGreater(round(moved_node["z"], 3), round(node_before_move["z"], 3))

                page.click('[data-raceway-action="delete-node"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 1")
                page.on("dialog", lambda dialog: dialog.accept())
                page.click('[data-raceway-action="delete-run"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns().length === 0")

                severe_messages = [
                    message for message in console_messages
                    if message.startswith("error:")
                ]
                self.assertEqual(severe_messages, [])
            finally:
                browser.close()


class RacewayRealViewerBrowserSmokeTests(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(username="raceway-real-browser", password="pw")
        self.project = create_project("RWY-REAL-BROWSER")
        assign_project(self.user, self.project)
        self.source, self.package = create_source_and_package(self.project.proj_id)
        self.client.force_login(self.user)

    def add_client_cookies(self, context):
        for cookie in self.client.cookies.values():
            context.add_cookies([
                {
                    "name": cookie.key,
                    "value": cookie.value,
                    "url": self.live_server_url,
                }
            ])

    def test_real_viewer_draw_save_and_reload_raceway_run(self):
        console_messages = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                context = browser.new_context(viewport={"width": 1280, "height": 850})
                self.add_client_cookies(context)
                page = context.new_page()
                page.on("console", lambda message: console_messages.append(f"{message.type}: {message.text}"))
                page.goto(
                    f"{self.live_server_url}{reverse('plant3d_package_viewer', args=[self.package.pk])}",
                    wait_until="domcontentloaded",
                )
                page.wait_for_selector("#racewayToolSection", timeout=15000)
                page.wait_for_selector("#viewer canvas", timeout=15000)
                page.wait_for_function(
                    "() => window.plant3dViewerRuntime?.getPackage?.()?.project_id === 'RWY-REAL-BROWSER'",
                    timeout=15000,
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#racewayFamilySelect option').length >= 2",
                    timeout=15000,
                )

                page.click('[data-raceway-action="start"]')
                canvas = page.locator("#viewer canvas")
                canvas.click(position={"x": 360, "y": 280})
                canvas.click(position={"x": 470, "y": 310})
                canvas.click(position={"x": 580, "y": 280})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                page.click('[data-raceway-action="finish"]')
                page.click('[data-raceway-action="save"]')
                page.wait_for_function(
                    "() => document.querySelector('#racewayToolStatus')?.textContent.includes('saved to server')",
                    timeout=15000,
                )

                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector("#racewayToolSection", timeout=15000)
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3",
                    timeout=15000,
                )
                restored = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0]")
                self.assertEqual(restored["tag"], "RWY-001")
                self.assertEqual(len(restored["nodes"]), 3)
                self.assertTrue(restored["serverRunId"])

                severe_messages = [
                    message for message in console_messages
                    if message.startswith("error:") and "favicon" not in message.lower()
                ]
                self.assertEqual(severe_messages, [])
            finally:
                browser.close()
