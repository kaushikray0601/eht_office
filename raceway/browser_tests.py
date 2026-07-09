import os

from django.test import SimpleTestCase
from playwright.sync_api import sync_playwright


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
                        window.plant3dViewerRuntime = {
                          THREE: { Vector3, Group, BufferGeometry, LineBasicMaterial, MeshBasicMaterial, SphereGeometry, Line, Mesh },
                          canvas,
                          currentSourceElevationM: () => 106.5,
                          pointOnSourceElevationFromViewerEvent: (event, elevation) => new Vector3(event.clientX / 10, elevation, event.clientY / 10),
                          renderPointToSourcePoint: point => ({ x: point.x, y: point.z, z: point.y, coordinate_frame: 'source_xyz_m' }),
                          sourcePointToRenderPoint: point => new Vector3(point.x, point.z, point.y),
                          worldUnitsForScreenPixels: () => 0.1,
                          renderNow: () => { window.__racewayRenderCount += 1; },
                          registerInteraction: config => ({
                            activate: () => { activeInteraction = config; },
                            deactivate: () => { if (activeInteraction === config) activeInteraction = null; },
                            isActive: () => activeInteraction === config,
                          }),
                        };
                        canvas.addEventListener('click', event => {
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
                layer_ids = page.evaluate("() => window.plant3dViewerLayers.ids()")
                self.assertIn("model", layer_ids)
                self.assertIn("measurement", layer_ids)
                self.assertIn("eht-draft", layer_ids)
                self.assertIn("raceway-overlay", layer_ids)
                page.click('[data-raceway-action="start"]')
                page.click("#viewerCanvas", position={"x": 120, "y": 90})
                page.click("#viewerCanvas", position={"x": 220, "y": 130})
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 2")

                page.click('[data-raceway-action="undo"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 1")

                page.click('[data-raceway-action="select-node"][data-node-index="0"]')
                page.click('[data-raceway-action="move-node"]')
                page.click("#viewerCanvas", position={"x": 320, "y": 170})
                moved_node = page.evaluate("() => window.racewayViewerOverlay.getRuns()[0].nodes[0]")
                self.assertGreater(moved_node["x"], 0)
                self.assertEqual(round(moved_node["z"], 3), 106.5)

                page.click('[data-raceway-action="delete-node"]')
                page.wait_for_function("() => window.racewayViewerOverlay.getRuns()[0]?.nodes.length === 0")

                severe_messages = [
                    message for message in console_messages
                    if message.startswith("error:")
                ]
                self.assertEqual(severe_messages, [])
            finally:
                browser.close()
