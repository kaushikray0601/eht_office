from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from eht.models import SLDTopologyEdit
from eht.tests import make_rich_sld_project_snapshot


class SldBrowserSmokeTests(StaticLiveServerTestCase):
    """Opt-in browser smoke tests for the interactive SLD workspace."""

    project_id = 'p-browser-sld'

    def setUp(self):
        super().setUp()
        make_rich_sld_project_snapshot(self.project_id, ['LINE-001', 'LINE-002', 'LINE-003'])

    def test_sld_topology_modes_get_live_browser_state(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                console_messages = []
                page.on('console', lambda message: console_messages.append(f'{message.type}: {message.text}'))

                page.goto(f'{self.live_server_url}/base/', wait_until='domcontentloaded')
                page.select_option('#id_proj_id', self.project_id)
                page.click('#sld-tab')

                root = page.locator('#sld-diagram-shell')
                root.wait_for(state='visible', timeout=15000)
                page.wait_for_function(
                    """() => {
                        const root = document.querySelector('#sld-diagram-shell');
                        return !!(root && root.__sldState && root.dataset.rendering === 'false');
                    }""",
                    timeout=30000,
                )

                state = page.evaluate(
                    """() => {
                        const root = document.querySelector('#sld-diagram-shell');
                        return {
                            rendering: root.dataset.rendering || '',
                            hasState: !!root.__sldState,
                            nodeCount: root.__sldState ? root.__sldState.payload.nodes.length : 0,
                            edgeCount: root.__sldState ? root.__sldState.payload.edges.length : 0,
                            scriptUrls: Array.from(document.scripts)
                                .map((script) => script.src)
                                .filter((src) => src.includes('sld_workspace.js')),
                        };
                    }"""
                )
                self.assertTrue(state['hasState'])
                self.assertEqual(state['rendering'], 'false')
                self.assertGreater(state['nodeCount'], 0)
                self.assertGreater(state['edgeCount'], 0)
                self.assertTrue(any('sld-r3-hit-targets' in src for src in state['scriptUrls']))

                mode_expectations = [
                    ('#sld-combine-mode', 'combineMode'),
                    ('#sld-split-mode', 'splitMode'),
                    ('#sld-downstream-jb-mode', 'downstreamJbMode'),
                    ('#sld-attach-jb-mode', 'attachJbMode'),
                ]
                for selector, state_key in mode_expectations:
                    page.click(selector)
                    page.wait_for_function(
                        f"""() => {{
                            const root = document.querySelector('#sld-diagram-shell');
                            return !!(root && root.__sldState && root.__sldState.{state_key});
                        }}""",
                        timeout=5000,
                    )
                    self.assertTrue(page.evaluate(
                        f"""() => document.querySelector('#sld-diagram-shell').__sldState.{state_key}"""
                    ))

                severe_messages = [
                    message for message in console_messages
                    if message.startswith('error:') and 'favicon' not in message.lower()
                ]
                self.assertEqual(severe_messages, [])

            finally:
                browser.close()

    def test_sld_topology_preview_works_from_rendered_cell_clicks(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                console_messages = []
                responses = []
                page.on('console', lambda message: console_messages.append(f'{message.type}: {message.text}'))
                page.on(
                    'response',
                    lambda response: responses.append((response.url, response.status))
                    if '/sld/topology/' in response.url else None,
                )

                self._open_sld_workspace(page)
                ids = page.evaluate(
                    """() => {
                        const state = document.querySelector('#sld-diagram-shell').__sldState;
                        const nodes = state.payload.nodes;
                        const byType = (type) => nodes
                            .filter((node) => node.component_type === type)
                            .map((node) => node.component_id);
                        const firstJb = byType('JB3PH')[0];
                        const downstreamChildren = (state.outgoingBySource[firstJb] || [])
                            .map((edge) => edge.to_component_id);
                        return {
                            mcbs: byType('MCB'),
                            jbs: byType('JB3PH'),
                            downstreamChildren,
                        };
                    }"""
                )

                page.click('#sld-combine-mode')
                self._click_component(page, ids['mcbs'][0])
                self._click_component(page, ids['mcbs'][1])
                self._wait_for_preview(page, 'combinePreview')

                page.click('#sld-split-mode')
                self._click_component(page, ids['mcbs'][0])
                self._wait_for_preview(page, 'splitPreview')

                page.click('#sld-downstream-jb-mode')
                self._click_component(page, ids['jbs'][0])
                self._click_component(page, ids['downstreamChildren'][0])
                self._click_component(page, ids['downstreamChildren'][1])
                self._wait_for_preview(page, 'downstreamJbPreview')

                page.click('#sld-attach-jb-mode')
                self._click_component(page, ids['mcbs'][2])
                self._click_component(page, ids['jbs'][0])
                self._wait_for_preview(page, 'attachJbPreview')

                failed_responses = [
                    (url, status) for url, status in responses
                    if status >= 400
                ]
                self.assertEqual(failed_responses, [])
                severe_messages = [
                    message for message in console_messages
                    if message.startswith('error:') and 'favicon' not in message.lower()
                ]
                self.assertEqual(severe_messages, [])

            finally:
                browser.close()

    def test_sld_topology_apply_works_from_rendered_cell_clicks(self):
        workflows = [
            ('combine', self._exercise_combine_workflow),
            ('split', self._exercise_split_workflow),
            ('downstream', self._exercise_downstream_workflow),
            ('attach', self._exercise_attach_workflow),
        ]
        project_ids = {workflow_name: f'pbsld-{workflow_name[:4]}' for workflow_name, _exercise in workflows}
        for workflow_name, _exercise in workflows:
            make_rich_sld_project_snapshot(
                project_ids[workflow_name],
                ['LINE-001', 'LINE-002', 'LINE-003'],
            )

        failed_response_summary = {}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                for workflow_name, exercise in workflows:
                    with self.subTest(workflow=workflow_name):
                        project_id = project_ids[workflow_name]
                        responses = []
                        page.on(
                            'response',
                            lambda response: responses.append((response.url, response.status))
                            if '/sld/topology/' in response.url else None,
                        )
                        self._open_sld_workspace(page, project_id=project_id)
                        exercise(page)
                        page.click('#sld-combine-apply')
                        self._wait_for_topology_edit_render(page)
                        failed_responses = [
                            (url, status) for url, status in responses
                            if status >= 400
                        ]
                        failed_response_summary[workflow_name] = failed_responses
            finally:
                browser.close()

        self.assertEqual(failed_response_summary, {name: [] for name, _exercise in workflows})
        for workflow_name, _exercise in workflows:
            self.assertEqual(
                SLDTopologyEdit.objects.filter(
                    project__proj_id=project_ids[workflow_name],
                    status='applied',
                ).count(),
                1,
            )

    def _open_sld_workspace(self, page, project_id=None):
        project_id = project_id or self.project_id
        page.goto(f'{self.live_server_url}/base/', wait_until='domcontentloaded')
        page.select_option('#id_proj_id', project_id)
        page.click('#sld-tab')
        root = page.locator('#sld-diagram-shell')
        root.wait_for(state='visible', timeout=15000)
        page.wait_for_function(
            """() => {
                const root = document.querySelector('#sld-diagram-shell');
                return !!(root && root.__sldState && root.dataset.rendering === 'false');
            }""",
            timeout=30000,
        )

    def _collect_topology_ids(self, page):
        return page.evaluate(
            """() => {
                const state = document.querySelector('#sld-diagram-shell').__sldState;
                const nodes = state.payload.nodes;
                const byType = (type) => nodes
                    .filter((node) => node.component_type === type)
                    .map((node) => node.component_id);
                const firstJb = byType('JB3PH')[0];
                const downstreamChildren = (state.outgoingBySource[firstJb] || [])
                    .map((edge) => edge.to_component_id);
                return {
                    mcbs: byType('MCB'),
                    jbs: byType('JB3PH'),
                    downstreamChildren,
                };
            }"""
        )

    def _exercise_combine_workflow(self, page):
        ids = self._collect_topology_ids(page)
        page.click('#sld-combine-mode')
        self._click_component(page, ids['mcbs'][0])
        self._click_component(page, ids['mcbs'][1])
        self._wait_for_preview(page, 'combinePreview')

    def _exercise_split_workflow(self, page):
        ids = self._collect_topology_ids(page)
        page.click('#sld-split-mode')
        self._click_component(page, ids['mcbs'][0])
        self._wait_for_preview(page, 'splitPreview')

    def _exercise_downstream_workflow(self, page):
        ids = self._collect_topology_ids(page)
        page.click('#sld-downstream-jb-mode')
        self._click_component(page, ids['jbs'][0])
        self._click_component(page, ids['downstreamChildren'][0])
        self._click_component(page, ids['downstreamChildren'][1])
        self._wait_for_preview(page, 'downstreamJbPreview')

    def _exercise_attach_workflow(self, page):
        ids = self._collect_topology_ids(page)
        page.click('#sld-attach-jb-mode')
        self._click_component(page, ids['mcbs'][2])
        self._click_component(page, ids['jbs'][0])
        self._wait_for_preview(page, 'attachJbPreview')

    def _click_component(self, page, component_id):
        box = page.evaluate(
            """(componentId) => {
                const root = document.querySelector('#sld-diagram-shell');
                const state = root && root.__sldState;
                const element = state && state.elementByComponentId[componentId];
                const view = element && state.paper.findViewByModel(element);
                let rect = view && view.el.getBoundingClientRect();
                if (!rect) {
                    return null;
                }
                if (rect.top < 0 || rect.bottom > window.innerHeight || rect.left < 0 || rect.right > window.innerWidth) {
                    window.scrollBy({
                        left: rect.left - (window.innerWidth / 2) + (rect.width / 2),
                        top: rect.top - (window.innerHeight / 2) + (rect.height / 2),
                        behavior: 'instant',
                    });
                    rect = view.el.getBoundingClientRect();
                }
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                const hit = document.elementFromPoint(x, y);
                return {
                    x,
                    y,
                    width: rect.width,
                    height: rect.height,
                    hitTag: hit ? hit.tagName : '',
                    hitClass: hit ? hit.getAttribute('class') || '' : '',
                    hitModelId: hit && hit.closest ? (hit.closest('[model-id]') || {}).getAttribute('model-id') || '' : '',
                    viewModelId: view.el.getAttribute('model-id') || '',
                };
            }""",
            component_id,
        )
        self.assertIsNotNone(box, f'Component {component_id} is not rendered on the active SLD page.')
        self.assertEqual(
            box['hitModelId'],
            box['viewModelId'],
            f'Click target for {component_id} is not the rendered component: {box}',
        )
        page.mouse.click(box['x'], box['y'])

    def _wait_for_preview(self, page, preview_key):
        try:
            page.wait_for_function(
                f"""(previewKey) => {{
                    const root = document.querySelector('#sld-diagram-shell');
                    const state = root && root.__sldState;
                    return !!(
                        state
                        && state.topologyPreviewStatus === 'ready'
                        && state[previewKey]
                        && state[previewKey].ok
                        && !document.querySelector('#sld-combine-apply').disabled
                    );
                }}""",
                arg=preview_key,
                timeout=7000,
            )
        except PlaywrightTimeoutError as exc:
            state = page.evaluate(
                """(previewKey) => {
                    const root = document.querySelector('#sld-diagram-shell');
                    const state = root && root.__sldState;
                    if (!state) {
                        return {hasState: false};
                    }
                    return {
                        hasState: true,
                        mode: {
                            combine: state.combineMode,
                            split: state.splitMode,
                            downstream: state.downstreamJbMode,
                            attach: state.attachJbMode,
                        },
                        combineSelectionIds: Array.from(state.combineSelectionIds || []),
                        splitSelectionIds: Array.from(state.splitSelectionIds || []),
                        downstreamJbParentId: state.downstreamJbParentId,
                        downstreamJbSelectionIds: Array.from(state.downstreamJbSelectionIds || []),
                        attachSourceId: state.attachSourceId,
                        attachTargetJbId: state.attachTargetJbId,
                        topologyPreviewStatus: state.topologyPreviewStatus,
                        topologyPreviewError: state.topologyPreviewError,
                        preview: state[previewKey] || null,
                        applyDisabled: document.querySelector('#sld-combine-apply').disabled,
                    };
                }""",
                preview_key,
            )
            raise AssertionError(f'SLD preview {preview_key} did not become ready. State: {state}') from exc

    def _wait_for_topology_edit_render(self, page):
        page.wait_for_function(
            """() => {
                const root = document.querySelector('#sld-diagram-shell');
                return !!(
                    root
                    && root.dataset.rendering === 'false'
                    && root.__sldState
                    && root.__sldState.hasTopologyEdit
                );
            }""",
            timeout=30000,
        )
