import os

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import SimpleTestCase
from django.urls import reverse
from playwright.sync_api import sync_playwright

from telemetry.models import SuggestionEvent

from .models import RacewayFamily, RacewayLayer
from .tests import (
    assign_project,
    create_family,
    create_nodes,
    create_project,
    create_run,
    create_size,
    create_source_and_package,
)


REAL_VIEWER_READY_TIMEOUT_MS = 45000


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
                          constructor() { this.attributes = {}; this.userData = {}; }
                          setFromPoints(points) { this.points = points; return this; }
                          setAttribute(name, attribute) { this.attributes[name] = attribute; return this; }
                          computeVertexNormals() {}
                          computeBoundingSphere() {}
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
                        window.__racewayFrameRequests = [];
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
                        window.__racewayOpenedUrls = [];
                        window.open = (url) => {
                          window.__racewayOpenedUrls.push(String(url));
                          return null;
                        };
                        window.fetch = async (url, options = {}) => {
                          const method = options.method || 'GET';
                          const body = options.body ? JSON.parse(options.body) : null;
                          window.__racewayFetchLog.push({ url: String(url), method, body });
                          if (String(url).startsWith('/raceway/catalog/')) {
                            return { ok: true, status: 200, json: async () => catalogPayload };
                          }
                          if (String(url).startsWith('/telemetry/events/') && method === 'POST') {
                            return { ok: false, status: 503, json: async () => ({ error: 'Telemetry unavailable in smoke test.' }) };
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
                                  key: node.key || `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
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
                          if (String(url).startsWith('/raceway/runs/501/') && method === 'PATCH') {
                            return {
                              ok: true,
                              status: 200,
                              json: async () => ({
                                run: { id: 501, key: 'run-key', nodes_url: '/raceway/runs/501/nodes/' },
                              }),
                            };
                          }
                          if (String(url).startsWith('/raceway/layers/91/graph/') && method === 'GET') {
                            return {
                              ok: true,
                              status: 200,
                              json: async () => ({
                                layer: { id: 91, project_id: 'RWY-BROWSER' },
                                graph: {
                                  tolerance_m: 0.01,
                                  nodes: [],
                                  edges: [],
                                  warnings: [],
                                },
                              }),
                            };
                          }
                          if (String(url).startsWith('/raceway/layers/91/schedule/') && method === 'GET') {
                            return {
                              ok: true,
                              status: 200,
                              json: async () => ({
                                layer: { id: 91, project_id: 'RWY-BROWSER' },
                                schedule: {
                                  generated_at: '2026-07-12T00:00:00+00:00',
                                  project_id: 'RWY-BROWSER',
                                  layer_id: 91,
                                  layer_name: 'Raceway Draft',
                                  graph_warnings: { total: 0, by_code: {}, near_miss_endpoint: 0, unconnected_crossing: 0, zero_length_segment: 0 },
                                  warning_summary: { total: 1, by_code: { 'raceway.warning.model_clash_aabb': 1 }, by_severity: { warning: 1 }, warning: 1, info: 0, error: 0 },
                                  warnings: [
                                    {
                                      code: 'raceway.warning.model_clash_aabb',
                                      severity: 'warning',
                                      message: 'Raceway segment envelope overlaps a Plant3D object bounds box.',
                                      run_key: 'run-key',
                                      run_tag: 'RWY-001',
                                      node_keys: [
                                        '00000000-0000-4000-8000-000000000001',
                                        '00000000-0000-4000-8000-000000000002',
                                      ],
                                      segment_index: 1,
                                      values: { object_label: 'B-001' },
                                    },
                                  ],
                                  assumptions: [
                                    { code: 'raceway.schedule.traceability', message: 'Use durable UUID keys.' },
                                    { code: 'raceway.schedule.standard_length_piece_estimate', message: 'Piece estimate assumption.' },
                                  ],
                                  runs: [],
                                  segments: [],
                                  fitting_placeholders: {
                                    plan_bends: [],
                                    risers: [],
                                    counts: { plan_bend_total: 2, riser_total: 1, plan_bends: {}, risers: {} },
                                  },
                                  groups: [
                                    {
                                      family_code: 'LADDER-HDG',
                                      size_label: '300 x 100 mm',
                                      service_class: 'power',
                                      run_count: 1,
                                      segment_count: 3,
                                      length_m: 12.5,
                                      horizontal_length_m: 10.5,
                                      riser_length_m: 2,
                                      plan_bend_count: 2,
                                      riser_count: 1,
                                      support_placeholders: 6,
                                      standard_length_mm: 3000,
                                      piece_count_estimate: 5,
                                      offcut_m_estimate: 2.5,
                                      known_weight_kg: 0,
                                      has_unknown_weight: true,
                                    },
                                  ],
                                  totals: {
                                    run_count: 1,
                                    segment_count: 3,
                                    length_m: 12.5,
                                    horizontal_length_m: 10.5,
                                    riser_length_m: 2,
                                    plan_bend_count: 2,
                                    riser_count: 1,
                                    support_placeholders: 6,
                                    piece_count_estimate: 5,
                                    offcut_m_estimate: 2.5,
                                    known_weight_kg: 0,
                                    has_unknown_weight: true,
                                  },
                                },
                              }),
                            };
                          }
                          if (String(url).startsWith('/raceway/layers/91/fittings/') && method === 'GET') {
                            return {
                              ok: true,
                              status: 200,
                              json: async () => ({
                                layer: { id: 91, project_id: 'RWY-BROWSER' },
                                fittings: {
                                  generated_at: '2026-07-12T00:00:00+00:00',
                                  project_id: 'RWY-BROWSER',
                                  layer_id: 91,
                                  projection: 'raceway.fittings.v0',
                                  status: 'derived_placeholder',
                                  counts: {
                                    total: 4,
                                    synthetic_proxy_total: 3,
                                    by_kind: { plan_bend: 2, riser: 1, reducer_candidate: 1, tee: 0, cross: 0 },
                                    by_category: { plan_bend_46_90: 2, riser_up: 1, width_reducer: 1 },
                                    requires_catalogue_validation: 4,
                                    requires_face_alignment: 2,
                                  },
                                  graph_summary: {
                                    node_count: 3,
                                    edge_count: 2,
                                    branch_node_count: 0,
                                    junction_node_count: 1,
                                    warning_count: 0,
                                  },
                                  assumptions: [
                                    { code: 'raceway.fittings.route_as_truth', message: 'Route is truth.' },
                                    { code: 'raceway.fittings.face_alignment_deferred', message: 'Face alignment deferred.' },
                                  ],
                                  items: [],
                                },
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
                          modelAnchorFromViewerEvent: event => window.__racewayUseModelAnchor ? ({
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
                          }) : null,
                          currentSourceElevationM: () => 1.0,
                          pointOnSourceElevationFromViewerEvent: (event, elevation) => new Vector3(event.clientX / 10, elevation, event.clientY / 10),
                          renderPointToSourcePoint: point => ({ x: point.x, y: point.z, z: point.y, coordinate_frame: 'source_xyz_m' }),
                          sourcePointToRenderPoint: point => new Vector3(point.x, point.z, point.y),
                          frameSourcePoints: (points, options = {}) => {
                            window.__racewayFrameRequests.push({ points, options });
                            return true;
                          },
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
                        window.__racewayUseModelAnchor = true;
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
                self.assertIn("Ctrl+Z", page.get_attribute('[data-raceway-action="undo"]', "title"))
                self.assertIn("Ctrl+Shift+Z", page.get_attribute('[data-raceway-action="redo"]', "title"))
                self.assertIn("Ctrl+S", page.get_attribute('[data-raceway-action="save"]', "title"))
                self.assertIn("J", page.get_attribute('[data-raceway-action="connect-node"]', "title"))
                self.assertIn("G", page.get_attribute('[data-raceway-action="refresh-graph"]', "title"))
                self.assertIn("B", page.get_attribute('[data-raceway-action="refresh-schedule"]', "title"))
                self.assertIn("T", page.get_attribute('[data-raceway-action="refresh-fittings"]', "title"))
                self.assertIn("Shift+B", page.get_attribute('[data-raceway-action="open-schedule-csv"]', "title"))
                self.assertIn("Shift+V", page.get_attribute('[data-raceway-action="toggle-surfaces"]', "title"))
                self.assertTrue(
                    page.evaluate(
                        """() => {
                          const children = Array.from(document.querySelector('#racewayToolSection').children);
                          return children.indexOf(document.querySelector('#racewayInspector'))
                            < children.indexOf(document.querySelector('#racewaySummary'));
                        }"""
                    )
                )
                self.assertIn("O", page.get_attribute("#racewayOrthoInput", "title"))
                self.assertIn("Enter", page.get_attribute('[data-raceway-action="add-segment"]', "title"))
                self.assertIn("Shift+X", page.get_attribute('[data-raceway-action="split-segment"]', "title"))

                page.evaluate("() => { window.__racewayUseModelAnchor = false; }")
                page.click('[data-raceway-action="start"]')
                page.check("#racewayOrthoInput")
                page.click("#viewerCanvas", position={"x": 100, "y": 100})
                page.click("#viewerCanvas", position={"x": 180, "y": 130})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 2")
                ortho_nodes = page.evaluate(
                    """() => window.racewayViewerOverlay.getRuns()[0].nodes.map(node => ({
                      x: node.x,
                      y: node.y,
                      z: node.z,
                      anchor: node.anchor?.stable_id || '',
                    }))"""
                )
                self.assertEqual([node["anchor"] for node in ortho_nodes], ["", ""])
                same_x = round(ortho_nodes[1]["x"], 3) == round(ortho_nodes[0]["x"], 3)
                same_y = round(ortho_nodes[1]["y"], 3) == round(ortho_nodes[0]["y"], 3)
                self.assertTrue(same_x or same_y, ortho_nodes)
                self.assertFalse(same_x and same_y, ortho_nodes)
                page.evaluate("() => window.racewayViewerOverlay.flushTelemetry()")
                page.wait_for_function("() => window.__racewayFetchLog.some((entry) => entry.url.includes('/telemetry/events/'))")
                telemetry_events = page.evaluate(
                    """() => window.__racewayFetchLog
                      .filter((entry) => entry.url.includes('/telemetry/events/'))
                      .flatMap((entry) => entry.body?.events || [])
                    """
                )
                self.assertIn("raceway.ortho.axis_lock", {event["suggestion_code"] for event in telemetry_events})
                self.assertTrue(any(event["suggestion_code"].startswith("raceway.warning.") for event in telemetry_events))
                self.assertFalse(any("run_id" in event.get("context", {}) for event in telemetry_events))
                self.assertFalse(any("node_id" in event.get("context", {}) for event in telemetry_events))
                page.select_option("#racewaySegmentDirectionSelect", "plus_y")
                page.fill("#racewaySegmentLengthInput", "4")
                page.press("#racewaySegmentLengthInput", "Enter")
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                typed_nodes = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0].nodes")
                self.assertEqual(round(typed_nodes[2]["x"], 3), round(typed_nodes[1]["x"], 3))
                self.assertEqual(round(typed_nodes[2]["y"] - typed_nodes[1]["y"], 3), 4)
                page.click('[data-raceway-action="select-node"][data-node-index="2"]')
                self.assertFalse(page.eval_on_selector('[data-raceway-action="connect-node"]', "el => el.disabled"))
                page.click('[data-raceway-action="connect-node"]')
                page.dispatch_event(
                    "#viewerCanvas",
                    "click",
                    {"clientX": typed_nodes[0]["x"] * 10, "clientY": typed_nodes[0]["y"] * 10},
                )
                page.wait_for_function(
                    """() => {
                      const nodes = window.racewayViewerOverlay.getRuns()[0]?.nodes || [];
                      if (nodes.length !== 3) return false;
                      return Math.round(nodes[2].x * 1000) === Math.round(nodes[0].x * 1000)
                        && Math.round(nodes[2].y * 1000) === Math.round(nodes[0].y * 1000)
                        && Math.round(nodes[2].z * 1000) === Math.round(nodes[0].z * 1000);
                    }"""
                )
                self.assertIn("connected", page.text_content("#racewayToolStatus"))
                page.evaluate("() => { window.racewayViewerOverlay.setRuns([]); window.__racewayUseModelAnchor = true; }")

                page.click('[data-raceway-action="start"]')
                page.click("#viewerCanvas", position={"x": 120, "y": 90})
                page.click("#viewerCanvas", position={"x": 220, "y": 130})
                page.click("#viewerCanvas", position={"x": 320, "y": 90})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                page.keyboard.press("Control+Z")
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 2")
                page.keyboard.press("Control+Shift+Z")
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
                self.assertIn("solid-3-plane-proxy", preview_kinds)
                self.assertIn("rung", preview_kinds)
                self.assertIn("plan-bend-proxy", preview_kinds)
                self.assertIn("riser-proxy", preview_kinds)
                self.assertIn("accessory-side-rail", preview_kinds)
                self.assertIn("accessory-lower-edge", preview_kinds)
                self.assertIn("accessory-cross-member", preview_kinds)
                self.assertIn("node-handle", preview_kinds)
                self.assertIn("node-hit-target", preview_kinds)
                snap_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.getMeasurementSnapObjects()
                        .map((child) => ({
                          kind: child.userData?.racewayPreviewKind,
                          snap: Boolean(child.userData?.measurementSnapTarget),
                        }))
                    """
                )
                self.assertIn("side-rail", {item["kind"] for item in snap_kinds})
                self.assertIn("lower-edge", {item["kind"] for item in snap_kinds})
                self.assertIn("depth-tick", {item["kind"] for item in snap_kinds})
                self.assertIn("rung", {item["kind"] for item in snap_kinds})
                self.assertIn("accessory-side-rail", {item["kind"] for item in snap_kinds})
                self.assertIn("accessory-lower-edge", {item["kind"] for item in snap_kinds})
                self.assertIn("accessory-cross-member", {item["kind"] for item in snap_kinds})
                self.assertNotIn("node-handle", {item["kind"] for item in snap_kinds})
                self.assertTrue(all(item["snap"] for item in snap_kinds))
                page.evaluate(
                    """() => {
                    window.__racewaySavedRunsForDirectVertical = window.racewayViewerOverlay.getRuns();
                    window.racewayViewerOverlay.setRuns([{
                      id: 'direct-vertical-riser',
                      tag: 'RWY-DIRECT-VERTICAL',
                      familyId: '10',
                      sizeId: '11',
                      familyCode: 'B-001',
                      familyKind: 'ladder',
                      widthMm: 300,
                      depthMm: 100,
                      serviceClass: 'power',
                      elevationM: 1,
                      orientation: { schema: 'raceway.orientation.v0', preset: 'open_up', quarter_turns: 0, label: 'Open Up' },
                      metadata: {},
                      nodes: [
                        { x: 12, y: 8, z: 1, coordinate_frame: 'source_xyz_m' },
                        { x: 12, y: 8, z: 4, coordinate_frame: 'source_xyz_m' },
                      ],
                    }]);
                    }"""
                )
                direct_riser_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.group.children
                        .flatMap((runGroup) => runGroup.children.map((child) => child.userData?.racewayPreviewKind))
                        .filter(Boolean)
                    """
                )
                self.assertIn("riser-proxy", direct_riser_kinds)
                self.assertIn("accessory-side-rail", direct_riser_kinds)
                self.assertIn("accessory-lower-edge", direct_riser_kinds)
                self.assertIn("accessory-cross-member", direct_riser_kinds)
                page.evaluate("() => window.racewayViewerOverlay.setRuns(window.__racewaySavedRunsForDirectVertical || [])")
                solid_proxy = page.evaluate(
                    """() => {
                        const proxy = window.racewayViewerOverlay.layer.group.children
                          .flatMap((runGroup) => runGroup.children)
                          .find((child) => child.userData?.racewayPreviewKind === 'solid-3-plane-proxy');
                        return {
                          faceCount: proxy?.userData?.faceCount || 0,
                          positionCount: proxy?.geometry?.userData?.positionCount || 0,
                          colorCount: proxy?.geometry?.attributes?.color?.count || 0,
                          vertexColors: Boolean(proxy?.material?.config?.vertexColors),
                          hasShadeVariation: (() => {
                            const values = Array.from(proxy?.geometry?.attributes?.color?.array || []);
                            return new Set(values.map(value => value.toFixed(4))).size > 2;
                          })(),
                        };
                    }"""
                )
                self.assertGreaterEqual(solid_proxy["faceCount"], 3)
                self.assertEqual(solid_proxy["positionCount"], solid_proxy["faceCount"] * 6)
                self.assertEqual(solid_proxy["colorCount"], solid_proxy["positionCount"])
                self.assertTrue(solid_proxy["vertexColors"])
                self.assertTrue(solid_proxy["hasShadeVariation"])
                depth_tick_points = page.evaluate(
                    """() => {
                        const tick = window.racewayViewerOverlay.layer.group.children
                          .flatMap((runGroup) => runGroup.children)
                          .find((child) => child.userData?.racewayPreviewKind === 'depth-tick');
                        return tick.geometry.points.map((point) => ({ x: point.x, y: point.y, z: point.z }));
                    }"""
                )
                self.assertGreater(depth_tick_points[1]["y"], depth_tick_points[0]["y"])
                page.click('[data-raceway-action="toggle-surfaces"]')
                page.wait_for_function("() => document.querySelector('#racewaySurfaceToggleBtn')?.textContent === 'Wire Only'")
                wire_preview_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.group.children
                        .flatMap((runGroup) => runGroup.children.map((child) => child.userData?.racewayPreviewKind))
                        .filter(Boolean)
                    """
                )
                self.assertNotIn("solid-3-plane-proxy", wire_preview_kinds)
                self.assertIn("side-rail", wire_preview_kinds)
                self.assertIn("rung", wire_preview_kinds)
                self.assertIn("wire view", page.text_content("#racewaySummary"))
                page.keyboard.press("Shift+V")
                page.wait_for_function("() => document.querySelector('#racewaySurfaceToggleBtn')?.textContent === 'Surface On'")
                self.assertIn("surface view", page.text_content("#racewaySummary"))

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
                page.wait_for_function(
                    "() => window.__racewayFetchLog.some((entry) => entry.url.includes('/graph/') && entry.method === 'GET')"
                )
                self.assertIn("Graph: no warnings", page.text_content("#racewayGraphWarnings"))
                page.click('[data-raceway-action="refresh-schedule"]')
                page.wait_for_function(
                    "() => window.__racewayFetchLog.some((entry) => entry.url.includes('/schedule/') && entry.method === 'GET')"
                )
                schedule_summary = page.text_content("#racewayScheduleSummary")
                self.assertIn("Schedule", schedule_summary)
                self.assertIn("12.500 m", schedule_summary)
                self.assertIn("5 piece", schedule_summary)
                self.assertIn("2.500 m offcut", schedule_summary)
                self.assertIn("validation notice", schedule_summary)
                self.assertIn("B-001", schedule_summary)
                self.assertEqual(page.text_content("#racewayWarningBadge"), "1")
                schedule_fetches_before = page.evaluate(
                    "() => window.__racewayFetchLog.filter((entry) => entry.url.includes('/schedule/') && entry.method === 'GET').length"
                )
                page.click("#viewerCanvas", position={"x": 30, "y": 30})
                page.keyboard.press("B")
                page.wait_for_function(
                    "(before) => window.__racewayFetchLog.filter((entry) => entry.url.includes('/schedule/') && entry.method === 'GET').length > before",
                    arg=schedule_fetches_before,
                )
                self.assertIn("Raceway schedule refreshed", page.text_content("#racewayToolStatus"))
                page.click('[data-raceway-action="refresh-fittings"]')
                page.wait_for_function(
                    "() => window.__racewayFetchLog.some((entry) => entry.url.includes('/fittings/') && entry.method === 'GET')"
                )
                fitting_summary = page.text_content("#racewayFittingSummary")
                self.assertIn("Fittings", fitting_summary)
                self.assertIn("4 item", fitting_summary)
                self.assertIn("3 synthetic proxy", fitting_summary)
                self.assertIn("1 reducer candidate", fitting_summary)
                self.assertIn("2 need face alignment", fitting_summary)
                fitting_fetches_before = page.evaluate(
                    "() => window.__racewayFetchLog.filter((entry) => entry.url.includes('/fittings/') && entry.method === 'GET').length"
                )
                page.click("#viewerCanvas", position={"x": 32, "y": 32})
                page.keyboard.press("T")
                page.wait_for_function(
                    "(before) => window.__racewayFetchLog.filter((entry) => entry.url.includes('/fittings/') && entry.method === 'GET').length > before",
                    arg=fitting_fetches_before,
                )
                self.assertIn("Raceway fittings refreshed", page.text_content("#racewayToolStatus"))
                page.select_option("#racewayOrientationSelect", "roll_right")
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.orientation?.preset === 'roll_right'"
                )
                self.assertIn("orientation set to Roll Right", page.text_content("#racewayToolStatus"))
                page.keyboard.press("Control+Z")
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.orientation?.preset === 'open_up'"
                )
                page.keyboard.press("Control+Shift+Z")
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.orientation?.preset === 'roll_right'"
                )
                node_puts_before = page.evaluate(
                    "() => window.__racewayFetchLog.filter((entry) => entry.url.includes('/nodes/') && entry.method === 'PUT').length"
                )
                page.click("#viewerCanvas", position={"x": 35, "y": 35})
                page.keyboard.press("Control+S")
                page.wait_for_function(
                    "(before) => window.__racewayFetchLog.filter((entry) => entry.url.includes('/nodes/') && entry.method === 'PUT').length > before",
                    arg=node_puts_before,
                )
                self.assertIn("saved to server", page.text_content("#racewayToolStatus"))
                saved_run = page.evaluate(
                    """() => [...window.__racewayFetchLog]
                        .reverse()
                        .find((entry) => entry.url.includes('/raceway/runs/501/') && entry.method === 'PATCH').body
                    """
                )
                self.assertEqual(saved_run["metadata"]["orientation"]["schema"], "raceway.orientation.v0")
                self.assertEqual(saved_run["metadata"]["orientation"]["preset"], "roll_right")
                self.assertEqual(saved_run["metadata"]["orientation"]["quarter_turns"], 1)
                latest_saved_nodes = page.evaluate(
                    """() => [...window.__racewayFetchLog]
                        .reverse()
                        .find((entry) => entry.url.includes('/nodes/') && entry.method === 'PUT').body.nodes
                    """
                )
                self.assertEqual(
                    [node.get("key") for node in latest_saved_nodes],
                    [
                        "00000000-0000-4000-8000-000000000001",
                        "00000000-0000-4000-8000-000000000002",
                        "00000000-0000-4000-8000-000000000003",
                    ],
                )
                page.wait_for_function(
                    "() => document.querySelector('#racewaySegmentList [data-raceway-action=\"select-segment\"][data-segment-index=\"1\"]')"
                )
                self.assertIn("S1", page.text_content("#racewaySegmentList"))
                page.click('[data-raceway-action="select-segment"][data-segment-index="1"]')
                self.assertIn("segment S1 selected", page.text_content("#racewayToolStatus"))
                self.assertEqual(page.locator("#racewaySegmentOrientationSelect").count(), 0)
                self.assertIn("Run default", page.text_content("#racewayOrientationSelect"))
                page.select_option("#racewayOrientationSelect", "open_down")
                page.wait_for_function(
                    """() => window.racewayViewerOverlay.getRuns()[0]
                      ?.segmentOrientationOverrides?.[
                        '00000000-0000-4000-8000-000000000001::00000000-0000-4000-8000-000000000002'
                      ]?.orientation?.preset === 'open_down'
                    """
                )
                self.assertIn("segment S1 orientation set to Open Down", page.text_content("#racewayToolStatus"))
                self.assertIn("Open Down | segment", page.text_content("#racewaySegmentList"))
                page.select_option("#racewayOrientationSelect", "__run_default__")
                page.wait_for_function(
                    """() => !window.racewayViewerOverlay.getRuns()[0]
                      ?.segmentOrientationOverrides?.[
                        '00000000-0000-4000-8000-000000000001::00000000-0000-4000-8000-000000000002'
                      ]
                    """
                )
                selected_segment_preview_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.group.children
                        .flatMap((runGroup) => runGroup.children.map((child) => child.userData?.racewayPreviewKind))
                        .filter(Boolean)
                    """
                )
                self.assertIn("selected-segment-highlight", selected_segment_preview_kinds)
                page.click('[data-raceway-action="select-warning"][data-warning-index="0"]')
                page.wait_for_function(
                    "() => document.querySelector('#racewayToolStatus')?.textContent.includes('selected from raceway.warning.model_clash_aabb')"
                )
                warning_selection_state = page.evaluate(
                    """() => ({
                      nodeActive: document.querySelector('[data-raceway-action="select-node"][data-node-index="1"]')?.classList.contains('raceway-row-active') || false,
                      segmentActive: document.querySelector('[data-raceway-action="select-segment"][data-segment-index="1"]')?.classList.contains('raceway-row-active') || false,
                    })"""
                )
                self.assertTrue(
                    warning_selection_state["nodeActive"] or warning_selection_state["segmentActive"],
                    warning_selection_state,
                )
                page.wait_for_function("() => window.__racewayFrameRequests.length === 1")
                self.assertIn("selected from raceway.warning.model_clash_aabb", page.text_content("#racewayToolStatus"))
                self.assertIn("framed in viewer", page.text_content("#racewayToolStatus"))
                frame_request = page.evaluate("() => window.__racewayFrameRequests[0]")
                self.assertEqual(len(frame_request["points"]), 2)
                self.assertEqual(frame_request["options"]["minRadiusM"], 1.5)
                warning_preview_kinds = page.evaluate(
                    """() => window.racewayViewerOverlay.layer.group.children
                        .flatMap((runGroup) => runGroup.children.map((child) => child.userData?.racewayPreviewKind))
                        .filter(Boolean)
                    """
                )
                self.assertIn("warning-segment-highlight", warning_preview_kinds)
                self.assertEqual(page.input_value("#racewayOrientationSelect"), "__run_default__")
                page.fill("#racewaySegmentFaceOffsetInput", "0.200")
                page.wait_for_function(
                    """() => Math.abs((window.racewayViewerOverlay.getRuns()[0]
                      ?.segmentFaceOffsetOverrides?.[
                        '00000000-0000-4000-8000-000000000001::00000000-0000-4000-8000-000000000002'
                      ]?.face_offset_m || 0) - 0.2) < 0.0001
                    """
                )
                self.assertIn("offset 0.200 m", page.text_content("#racewaySegmentList"))
                self.assertEqual(page.input_value("#racewayOrientationSelect"), "__run_default__")
                page.fill("#racewaySegmentSplitInput", "40")
                page.click('[data-raceway-action="split-segment"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 4")
                split_state = page.evaluate(
                    """() => {
                      const run = window.racewayViewerOverlay.getRuns()[0] || {};
                      return {
                        nodeCount: (run.nodes || []).length,
                        selectedRows: Array.from(document.querySelectorAll('[data-raceway-action="select-node"]'))
                          .filter((row) => row.classList.contains('raceway-row-active'))
                          .map((row) => row.dataset.nodeIndex),
                        faceOffsets: Object.values(run.segmentFaceOffsetOverrides || {})
                          .map((override) => override.face_offset_m || 0),
                        status: document.querySelector('#racewayToolStatus')?.textContent || '',
                      };
                    }"""
                )
                self.assertEqual(split_state["nodeCount"], 4)
                self.assertEqual(split_state["selectedRows"], ["1"])
                self.assertEqual(
                    sum(1 for offset in split_state["faceOffsets"] if abs(offset - 0.2) < 0.0001),
                    2,
                    split_state,
                )
                self.assertIn("split at 40%", split_state["status"])
                page.click('[data-raceway-action="delete-node"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                merge_state = page.evaluate(
                    """() => {
                      const run = window.racewayViewerOverlay.getRuns()[0] || {};
                      return {
                        faceOffsets: Object.values(run.segmentFaceOffsetOverrides || {})
                          .map((override) => override.face_offset_m || 0),
                        status: document.querySelector('#racewayToolStatus')?.textContent || '',
                      };
                    }"""
                )
                self.assertEqual(
                    sum(1 for offset in merge_state["faceOffsets"] if abs(offset - 0.2) < 0.0001),
                    1,
                    merge_state,
                )
                self.assertIn("Matching segment intent carried", merge_state["status"])
                page.click('[data-raceway-action="open-schedule-csv"]')
                self.assertEqual(
                    page.evaluate("() => window.__racewayOpenedUrls.at(-1)"),
                    "/raceway/layers/91/schedule.csv",
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
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 2")
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
        if not RacewayFamily.objects.exists():
            ladder = create_family("BROWSER-LADDER-HDG")
            create_size(family=ladder, width_mm=300, depth_mm=100)
            tray = create_family("BROWSER-TRAY-HDG")
            tray.kind = "tray"
            tray.save(update_fields=["kind"])
            create_size(family=tray, width_mm=300, depth_mm=75)

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
                page.wait_for_selector("#racewayToolSection", timeout=REAL_VIEWER_READY_TIMEOUT_MS)
                page.wait_for_selector("#viewer canvas", timeout=REAL_VIEWER_READY_TIMEOUT_MS)
                page.wait_for_function(
                    "() => window.plant3dViewerRuntime?.getPackage?.()?.project_id === 'RWY-REAL-BROWSER'",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#racewayFamilySelect option').length >= 2",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )

                page.click('[data-raceway-action="start"]')
                canvas = page.locator("#viewer canvas")
                canvas.click(position={"x": 360, "y": 280})
                canvas.click(position={"x": 470, "y": 310})
                canvas.click(position={"x": 580, "y": 280})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 3")
                page.click('[data-raceway-action="finish"]')
                page.click('[data-raceway-action="select-segment"][data-segment-index="1"]')
                page.select_option("#racewayOrientationSelect", "open_down")
                page.wait_for_function(
                    "() => Object.values(window.racewayViewerOverlay.getRuns()[0]?.segmentOrientationOverrides || {})"
                    ".some((override) => override.orientation?.preset === 'open_down')"
                )
                page.fill("#racewaySegmentFaceOffsetInput", "0.250")
                page.wait_for_function(
                    "() => Object.values(window.racewayViewerOverlay.getRuns()[0]?.segmentFaceOffsetOverrides || {})"
                    ".some((override) => Math.abs((override.face_offset_m || 0) - 0.25) < 0.0001)"
                )
                page.fill("#racewaySegmentSplitInput", "25")
                page.click('[data-raceway-action="split-segment"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 4")
                page.click('[data-raceway-action="save"]')
                page.wait_for_function(
                    "() => document.querySelector('#racewayToolStatus')?.textContent.includes('saved to server')",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )
                post_save_state = page.evaluate(
                    """() => {
                      const run = window.racewayViewerOverlay.getRuns()[0] || {};
                      return {
                        nodes: (run.nodes || []).map((node) => node.key || ''),
                        overrides: run.segmentOrientationOverrides || {},
                        faceOffsets: run.segmentFaceOffsetOverrides || {},
                        metadata: run.metadata || {},
                        status: document.querySelector('#racewayToolStatus')?.textContent || '',
                      };
                    }"""
                )
                self.assertEqual(len(post_save_state["nodes"]), 4)
                self.assertTrue(
                    any(
                        override.get("orientation", {}).get("preset") == "open_down"
                        for override in post_save_state["overrides"].values()
                    ),
                    post_save_state,
                )
                self.assertGreaterEqual(
                    sum(
                        1
                        for override in post_save_state["overrides"].values()
                        if override.get("orientation", {}).get("preset") == "open_down"
                    ),
                    2,
                    post_save_state,
                )
                self.assertTrue(
                    any(
                        abs(override.get("face_offset_m", 0) - 0.25) < 0.0001
                        for override in post_save_state["faceOffsets"].values()
                    ),
                    post_save_state,
                )

                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector("#racewayToolSection", timeout=REAL_VIEWER_READY_TIMEOUT_MS)
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 4",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )
                restored = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0]")
                self.assertEqual(restored["tag"], "RWY-001")
                self.assertEqual(len(restored["nodes"]), 4)
                self.assertTrue(restored["serverRunId"])
                self.assertIn(
                    "open_down",
                    {
                        override["orientation"]["preset"]
                        for override in restored.get("segmentOrientationOverrides", {}).values()
                    },
                )
                self.assertTrue(
                    any(
                        abs(override.get("face_offset_m", 0) - 0.25) < 0.0001
                        for override in restored.get("segmentFaceOffsetOverrides", {}).values()
                    ),
                    restored.get("segmentFaceOffsetOverrides", {}),
                )

                severe_messages = [
                    message for message in console_messages
                    if message.startswith("error:") and "favicon" not in message.lower()
                ]
                self.assertEqual(severe_messages, [])
            finally:
                browser.close()

    def test_real_viewer_applies_reducer_edge_match_offsets(self):
        layer = RacewayLayer.objects.create(
            project_id=self.project.proj_id,
            source_model_id=self.source.pk,
            render_package_id=self.package.pk,
            name="Reducer edge-match test layer",
        )
        family = create_family("REAL-REDUCER-LADDER")
        small = create_size(family=family, width_mm=300, depth_mm=100)
        large = create_size(family=family, width_mm=600, depth_mm=100)
        small_run = create_run(layer=layer, family=family, size=small)
        small_run.tag = "RWY-SMALL"
        small_run.source_model_id = self.source.pk
        small_run.render_package_id = self.package.pk
        small_run.save()
        large_run = create_run(layer=layer, family=family, size=large)
        large_run.tag = "RWY-LARGE"
        large_run.source_model_id = self.source.pk
        large_run.render_package_id = self.package.pk
        large_run.save()
        create_nodes(small_run, [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0)])
        create_nodes(large_run, [(3.0, 0.0, 0.0), (6.0, 0.0, 0.0)])

        console_messages = []
        telemetry_flushed = False
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
                page.wait_for_selector("#racewayToolSection", timeout=REAL_VIEWER_READY_TIMEOUT_MS)
                page.wait_for_function(
                    "() => window.racewayViewerOverlay.getRuns().length === 2",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )

                page.click('[data-raceway-action="apply-reducer-offsets"]')
                page.wait_for_function(
                    """() => {
                      const run = window.racewayViewerOverlay.getRuns()
                        .find((item) => item.tag === 'RWY-SMALL');
                      return Object.values(run?.segmentFaceOffsetOverrides || {})
                        .some((override) => Math.abs((override.face_offset_m || 0) - 0.15) < 0.0001);
                    }""",
                    timeout=REAL_VIEWER_READY_TIMEOUT_MS,
                )
                status = page.locator("#racewayToolStatus").inner_text()
                self.assertIn("Applied reducer edge-match offsets", status)
                page.evaluate("() => window.racewayViewerOverlay.flushTelemetry()")
                telemetry_flushed = True

                severe_messages = [
                    message for message in console_messages
                    if message.startswith("error:") and "favicon" not in message.lower()
                ]
                self.assertEqual(severe_messages, [])
            finally:
                browser.close()
        self.assertTrue(telemetry_flushed)
        event = SuggestionEvent.objects.filter(
            suggestion_code="raceway.reducer.edge_match_offset",
            action=SuggestionEvent.ACTION_ACCEPTED,
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.context["run_tag"], "RWY-SMALL")
        self.assertAlmostEqual(event.context["suggested_face_offset_m"], 0.15)
        self.assertEqual(event.action_detail["source"], "apply_edge_match_command")
