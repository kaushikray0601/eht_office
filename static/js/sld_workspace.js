(function () {
    const UPSTREAM_COMPONENT_ORDER = ['MCB', 'Cable4C', 'Isolator3PH', 'JB3PH'];
    const DOWNSTREAM_COMPONENT_ORDER = ['Isolator1PH', 'Cable3C', 'JB1PH', 'Tracer', 'EndTermination'];
    const NODE_STYLE = {
        MCB: { width: 108, height: 56, fill: '#f3f7fb', stroke: '#1f3447' },
        Cable4C: { width: 128, height: 34, fill: '#fff9ef', stroke: '#7a5b2b' },
        Cable3C: { width: 118, height: 32, fill: '#fff9ef', stroke: '#7a5b2b' },
        Isolator3PH: { width: 84, height: 34, fill: '#edf6ff', stroke: '#31597f' },
        Isolator1PH: { width: 84, height: 34, fill: '#edf6ff', stroke: '#31597f' },
        JB3PH: { width: 96, height: 54, fill: '#f5f8fc', stroke: '#20394f' },
        JB1PH: { width: 78, height: 44, fill: '#f5f8fc', stroke: '#20394f' },
        Tracer: { width: 120, height: 26, fill: '#eefaf1', stroke: '#2f6c43' },
        EndTermination: { width: 28, height: 28, fill: '#243b53', stroke: '#1a2735' },
    };

    function getNodeStyle(componentType) {
        return NODE_STYLE[componentType] || { width: 100, height: 40, fill: '#f8fafc', stroke: '#1f3447' };
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getSldCsrfToken() {
        if (typeof window.getCSRFToken === 'function') {
            return window.getCSRFToken();
        }
        let csrfToken = null;
        document.cookie.split(';').forEach(function (cookie) {
            const parts = cookie.trim().split('=');
            if (parts[0] === 'csrftoken') {
                csrfToken = parts[1];
            }
        });
        return csrfToken;
    }

    function setSldMessage(root, title, message, showSpinner) {
        root.innerHTML = `
            <div class="sld-diagram-shell__inner">
                ${showSpinner ? '<div class="spinner-border spinner-border-sm text-secondary mb-2" role="status" aria-hidden="true"></div>' : ''}
                <div class="fw-semibold text-dark mb-2">${title}</div>
                <div class="text-muted small mb-0">${message}</div>
            </div>
        `;
    }

    function renderEmptyState(root, message) {
        setSldMessage(root, 'Unable to render SLD', message, false);
    }

    function formatNodeBody(node) {
        const metadata = node.metadata || {};
        if (node.component_type === 'MCB' && metadata.breaker_size) {
            return `${metadata.breaker_size}A MCB`;
        }
        if ((node.component_type === 'Cable4C' || node.component_type === 'Cable3C') && metadata.length_m) {
            return `${node.display_name}\n${metadata.length_m} m`;
        }
        if (node.component_type === 'Tracer') {
            return 'Heat Trace';
        }
        if (node.component_type === 'EndTermination') {
            return 'End';
        }
        return node.display_name || node.component_type;
    }

    function createLineLabel(lineId, x, y) {
        const label = new joint.shapes.standard.TextBlock();
        label.position(x, y);
        label.resize(160, 34);
        label.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
            },
            label: {
                text: `Line ID: ${lineId}`,
                fill: '#132f4c',
                fontSize: 18,
                fontWeight: 700,
                textAnchor: 'start',
                textVerticalAnchor: 'middle',
                x: 0,
                y: '50%',
            },
        });
        label.prop('sldMeta', { type: 'line-label', lineId: lineId });
        return label;
    }

    function createComponentElement(node, position) {
        const style = getNodeStyle(node.component_type);

        if (node.component_type === 'EndTermination') {
            const circle = new joint.shapes.standard.Circle();
            circle.position(position.x, position.y - style.height / 2);
            circle.resize(style.width, style.height);
            circle.attr({
                body: {
                    fill: style.fill,
                    stroke: style.stroke,
                    strokeWidth: 2,
                },
                label: {
                    text: '',
                },
            });
            circle.prop('sldMeta', { componentId: node.component_id, node: node });
            return circle;
        }

        const rectangle = new joint.shapes.standard.Rectangle();
        rectangle.position(position.x, position.y - style.height / 2);
        rectangle.resize(style.width, style.height);
        rectangle.attr({
            body: {
                fill: style.fill,
                stroke: style.stroke,
                strokeWidth: 1.8,
                rx: 10,
                ry: 10,
            },
            label: {
                text: `${node.display_tag}\n${formatNodeBody(node)}`,
                fill: '#17324d',
                fontSize: 12,
                fontWeight: 600,
                textVerticalAnchor: 'middle',
                textAnchor: 'middle',
            },
        });
        if (node.component_type === 'Tracer') {
            rectangle.attr('body/strokeDasharray', '6 4');
        }
        rectangle.prop('sldMeta', { componentId: node.component_id, node: node });
        return rectangle;
    }

    function createEndTerminationLabel(node, position) {
        const label = new joint.shapes.standard.TextBlock();
        label.position(position.x + 42, position.y - 16);
        label.resize(120, 32);
        label.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
            },
            label: {
                text: `${node.display_tag}\nEnd Termination`,
                fill: '#17324d',
                fontSize: 11,
                fontWeight: 600,
                textAnchor: 'start',
                textVerticalAnchor: 'middle',
                x: 0,
                y: '50%',
            },
        });
        label.prop('sldMeta', { type: 'end-label', componentId: node.component_id });
        return label;
    }

    function groupNodesByLine(payload) {
        return payload.line_groups.map(function (lineGroup) {
            const lineNodes = payload.nodes.filter(function (node) {
                return (node.line_ids || []).includes(lineGroup.line_id);
            });
            const branches = lineGroup.branch_indices.map(function (branchIndex) {
                const branchNodes = lineNodes.filter(function (node) {
                    return node.branch_index === branchIndex;
                });
                const circuits = Array.from(new Set(
                    branchNodes
                        .map(function (node) { return node.circuit_index; })
                        .filter(function (value) { return value !== null && value !== undefined; })
                )).sort(function (a, b) { return a - b; });

                return {
                    branchIndex: branchIndex,
                    nodes: branchNodes,
                    branchType: branchNodes.some(function (node) { return node.component_type === 'JB3PH'; }) ? '3phJB' : '1phJB',
                    circuits: circuits.length ? circuits : [1],
                };
            });
            return {
                lineId: lineGroup.line_id,
                branches: branches,
            };
        });
    }

    function buildAutoLayout(payload) {
        const lineGroups = groupNodesByLine(payload);
        const positions = {};
        const startX = 200;
        const componentGap = 44;
        const branchGap = 88;
        const circuitGap = 94;
        const lineGap = 96;
        let currentTop = 60;

        lineGroups.forEach(function (lineGroup) {
            lineGroup.branches.forEach(function (branch) {
                const rowYs = branch.circuits.map(function (_circuit, index) {
                    return currentTop + index * circuitGap + 38;
                });
                const branchMidY = rowYs.length === 1 ? rowYs[0] : (rowYs[0] + rowYs[rowYs.length - 1]) / 2;
                let cursorX = startX;

                UPSTREAM_COMPONENT_ORDER.forEach(function (componentType) {
                    const node = branch.nodes.find(function (item) {
                        return item.component_type === componentType && (item.circuit_index === null || item.circuit_index === undefined);
                    });
                    if (!node) {
                        return;
                    }
                    positions[node.component_id] = { x: cursorX, y: branchMidY };
                    cursorX += getNodeStyle(componentType).width + componentGap;
                });

                const downstreamStartX = cursorX + (branch.branchType === '3phJB' ? 18 : 0);
                branch.circuits.forEach(function (circuitIndex, circuitOffset) {
                    let rowCursorX = downstreamStartX;
                    const rowY = rowYs[circuitOffset];

                    DOWNSTREAM_COMPONENT_ORDER.forEach(function (componentType) {
                        const node = branch.nodes.find(function (item) {
                            return item.component_type === componentType && item.circuit_index === circuitIndex;
                        });
                        if (!node) {
                            return;
                        }
                        positions[node.component_id] = { x: rowCursorX, y: rowY };
                        rowCursorX += getNodeStyle(componentType).width + componentGap;
                    });
                });

                currentTop = rowYs[rowYs.length - 1] + branchGap;
            });
            currentTop += lineGap;
        });

        return positions;
    }

    function mergeSavedPositions(autoPositions, savedPositions) {
        const merged = Object.assign({}, autoPositions);
        Object.keys(savedPositions || {}).forEach(function (componentId) {
            if (!merged[componentId]) {
                return;
            }
            const coords = savedPositions[componentId];
            merged[componentId] = {
                x: Number(coords.x),
                y: Number(coords.y),
            };
        });
        return merged;
    }

    function computeLineLabelPositions(payload, positions) {
        const labelPositions = [];
        payload.line_groups.forEach(function (lineGroup) {
            const lineNodes = payload.nodes.filter(function (node) {
                return (node.line_ids || []).includes(lineGroup.line_id) && positions[node.component_id];
            });
            if (!lineNodes.length) {
                return;
            }
            const yValues = lineNodes.map(function (node) { return positions[node.component_id].y; });
            const minY = Math.min.apply(null, yValues);
            const maxY = Math.max.apply(null, yValues);
            labelPositions.push({
                lineId: lineGroup.line_id,
                x: 24,
                y: minY + ((maxY - minY) / 2) - 16,
            });
        });
        return labelPositions;
    }

    function computeCanvasSize(payload, positions) {
        let maxX = 860;
        let maxY = 320;
        payload.nodes.forEach(function (node) {
            const position = positions[node.component_id];
            if (!position) {
                return;
            }
            const style = getNodeStyle(node.component_type);
            maxX = Math.max(maxX, position.x + style.width + 180);
            maxY = Math.max(maxY, position.y + style.height + 120);
        });
        return {
            width: Math.max(1400, maxX),
            height: Math.max(360, maxY),
        };
    }

    function getEdgeKey(edge) {
        return [
            edge.from_component_id,
            edge.to_component_id,
            edge.branch_index || 0,
            edge.circuit_index === null || edge.circuit_index === undefined ? 'na' : edge.circuit_index,
        ].join('__');
    }

    function buildLinkVertices(sourceCell, targetCell) {
        const sourceCenterY = sourceCell.position().y + sourceCell.size().height / 2;
        const targetCenterY = targetCell.position().y + targetCell.size().height / 2;
        const sourceRightX = sourceCell.position().x + sourceCell.size().width;
        const targetLeftX = targetCell.position().x;

        if (Math.abs(sourceCenterY - targetCenterY) <= 8) {
            return [];
        }

        const branchX = Math.round((sourceRightX + targetLeftX) / 2);
        return [
            { x: branchX, y: sourceCenterY },
            { x: branchX, y: targetCenterY },
        ];
    }

    function createDiagramLink(edge, sourceCell, targetCell, sourceNode, targetNode) {
        const link = new joint.shapes.standard.Link();

        link.source({ id: sourceCell.id, anchor: { name: 'right' } });
        link.target({ id: targetCell.id, anchor: { name: 'left' } });
        link.attr({
            line: {
                stroke: '#1f3447',
                strokeWidth: 2,
                targetMarker: null,
                sourceMarker: null,
                pointerEvents: 'none',
            },
        });
        link.connector('rounded', { radius: 8 });
        link.vertices(buildLinkVertices(sourceCell, targetCell));

        link.prop('sldMeta', {
            edge: edge,
            sourceNode: sourceNode,
            targetNode: targetNode,
        });
        return link;
    }

    function applyDefaultElementStyle(element) {
        const meta = element.prop('sldMeta') || {};
        const node = meta.node;
        if (!node) {
            return;
        }
        const style = getNodeStyle(node.component_type);
        if (node.component_type === 'EndTermination') {
            element.attr({
                body: {
                    fill: style.fill,
                    stroke: style.stroke,
                    strokeWidth: 2,
                    opacity: 1,
                },
            });
            return;
        }
        element.attr({
            body: {
                fill: style.fill,
                stroke: style.stroke,
                strokeWidth: 1.8,
                opacity: 1,
            },
            label: {
                fill: '#17324d',
            },
        });
    }

    function applyMutedElementStyle(element) {
        const meta = element.prop('sldMeta') || {};
        const node = meta.node;
        if (!node) {
            return;
        }
        if (node.component_type === 'EndTermination') {
            element.attr({
                body: {
                    opacity: 0.25,
                },
            });
            return;
        }
        element.attr({
            body: {
                opacity: 0.2,
            },
            label: {
                fill: '#829ab1',
            },
        });
    }

    function applyPathElementStyle(element, isSelected) {
        const meta = element.prop('sldMeta') || {};
        const node = meta.node;
        if (!node) {
            return;
        }
        const style = getNodeStyle(node.component_type);
        const stroke = isSelected ? '#c05621' : '#2f6c43';
        const fill = isSelected ? '#fff1e6' : style.fill;
        if (node.component_type === 'EndTermination') {
            element.attr({
                body: {
                    fill: isSelected ? '#c05621' : '#2f6c43',
                    stroke: stroke,
                    strokeWidth: isSelected ? 3 : 2.5,
                    opacity: 1,
                },
            });
            return;
        }
        element.attr({
            body: {
                fill: fill,
                stroke: stroke,
                strokeWidth: isSelected ? 3 : 2.4,
                opacity: 1,
            },
            label: {
                fill: '#102a43',
            },
        });
    }

    function applyDefaultLinkStyle(link) {
        link.attr({
            line: {
                stroke: '#1f3447',
                strokeWidth: 2,
                opacity: 1,
            },
        });
    }

    function applyMutedLinkStyle(link) {
        link.attr({
            line: {
                opacity: 0.15,
            },
        });
    }

    function applyPathLinkStyle(link, isAdjacent) {
        link.attr({
            line: {
                stroke: isAdjacent ? '#c05621' : '#2f6c43',
                strokeWidth: isAdjacent ? 3.4 : 2.8,
                opacity: 1,
            },
        });
    }

    function updateSavedCountBadge(root, savedCount) {
        const panel = root.closest('.sld-panel');
        const badge = panel ? panel.querySelector('.sld-saved-count-badge') : null;
        if (badge) {
            badge.textContent = `Saved Nodes: ${savedCount}`;
        }
    }

    function setDirtyState(root, isDirty, hasSavedLayout) {
        const panel = root.closest('.sld-panel');
        const saveButton = panel ? panel.querySelector('#sld-save-layout') : null;
        const resetButton = panel ? panel.querySelector('#sld-reset-layout') : null;
        if (saveButton) {
            saveButton.disabled = !isDirty;
        }
        if (resetButton) {
            resetButton.disabled = !isDirty && !hasSavedLayout;
        }
        if (root.__sldState) {
            root.__sldState.isDirty = isDirty;
            root.__sldState.hasSavedLayout = hasSavedLayout;
        }
    }

    function getSelectionSummaryContainer(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-selection-summary') : null;
    }

    function getInspectorDetailsContainer(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-inspector-details') : null;
    }

    function buildInspectorRows(node, relatedNodeCount, adjacentEdgeCount) {
        const metadata = node.metadata || {};
        const rows = [
            ['Tag', node.display_tag || '-'],
            ['Component', node.display_name || node.component_type],
            ['Type', node.component_type],
            ['Line IDs', (node.line_ids || []).join(', ') || '-'],
            ['Branch', node.branch_index !== null && node.branch_index !== undefined ? node.branch_index : '-'],
            ['Circuit', node.circuit_index !== null && node.circuit_index !== undefined ? node.circuit_index : '-'],
            ['Path Nodes', relatedNodeCount],
            ['Path Links', adjacentEdgeCount],
        ];
        Object.keys(metadata).sort().forEach(function (key) {
            const value = metadata[key];
            if (value === null || value === undefined || value === '') {
                return;
            }
            rows.push([key.replace(/_/g, ' '), Array.isArray(value) ? value.join(', ') : value]);
        });
        return rows;
    }

    function renderInspector(root, node, relatedNodeCount, adjacentEdgeCount) {
        const summary = getSelectionSummaryContainer(root);
        const details = getInspectorDetailsContainer(root);
        if (!summary || !details) {
            return;
        }
        if (!node) {
            summary.textContent = 'Select a component in the diagram to inspect its details and highlight the connected path.';
            details.innerHTML = '';
            return;
        }
        summary.innerHTML = `Selected <strong>${escapeHtml(node.display_tag || node.component_type)}</strong>. Connected path highlighting is limited to the current rendered graph.`;
        details.innerHTML = buildInspectorRows(node, relatedNodeCount, adjacentEdgeCount).map(function (row) {
            return `<dt>${escapeHtml(row[0])}</dt><dd>${escapeHtml(row[1])}</dd>`;
        }).join('');
    }

    function collectComponentPositions(state) {
        const positions = {};
        Object.keys(state.elementByComponentId).forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            const position = element.position();
            const size = element.size();
            positions[componentId] = {
                x: position.x,
                y: position.y + size.height / 2,
            };
        });
        return positions;
    }

    function updateLinkGeometry(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }

        Object.keys(state.linkByEdgeKey).forEach(function (edgeKey) {
            const linkEntry = state.linkByEdgeKey[edgeKey];
            const sourceCell = state.elementByComponentId[linkEntry.edge.from_component_id];
            const targetCell = state.elementByComponentId[linkEntry.edge.to_component_id];
            if (!sourceCell || !targetCell) {
                return;
            }

            linkEntry.link.source({ id: sourceCell.id, anchor: { name: 'right' } });
            linkEntry.link.target({ id: targetCell.id, anchor: { name: 'left' } });
            linkEntry.link.vertices(buildLinkVertices(sourceCell, targetCell));
        });
    }

    function refreshDynamicLabels(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }

        Object.keys(state.endLabelByComponentId).forEach(function (componentId) {
            const label = state.endLabelByComponentId[componentId];
            const element = state.elementByComponentId[componentId];
            if (!label || !element) {
                return;
            }
            const position = element.position();
            const size = element.size();
            label.position(position.x + size.width + 14, position.y - 2);
        });

        const positions = collectComponentPositions(state);
        computeLineLabelPositions(state.payload, positions).forEach(function (lineLabel) {
            const label = state.lineLabelByLineId[lineLabel.lineId];
            if (label) {
                label.position(lineLabel.x, lineLabel.y);
            }
        });
    }

    function refreshDerivedGeometry(root) {
        refreshDynamicLabels(root);
        updateLinkGeometry(root);
    }

    function buildGraphAdjacency(payload) {
        const adjacency = {};
        const edgesByComponent = {};
        (payload.nodes || []).forEach(function (node) {
            adjacency[node.component_id] = new Set();
            edgesByComponent[node.component_id] = [];
        });
        (payload.edges || []).forEach(function (edge) {
            if (!adjacency[edge.from_component_id]) {
                adjacency[edge.from_component_id] = new Set();
                edgesByComponent[edge.from_component_id] = [];
            }
            if (!adjacency[edge.to_component_id]) {
                adjacency[edge.to_component_id] = new Set();
                edgesByComponent[edge.to_component_id] = [];
            }
            adjacency[edge.from_component_id].add(edge.to_component_id);
            adjacency[edge.to_component_id].add(edge.from_component_id);
            edgesByComponent[edge.from_component_id].push(edge);
            edgesByComponent[edge.to_component_id].push(edge);
        });
        return { adjacency: adjacency, edgesByComponent: edgesByComponent };
    }

    function highlightSelection(root, componentId) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        state.selectedComponentId = componentId || null;
        const adjacency = state.graphAdjacency || {};
        const edgesByComponent = state.edgesByComponent || {};

        if (!componentId || !state.nodeByComponentId[componentId]) {
            Object.keys(state.elementByComponentId).forEach(function (id) {
                applyDefaultElementStyle(state.elementByComponentId[id]);
            });
            Object.keys(state.linkByEdgeKey).forEach(function (edgeKey) {
                applyDefaultLinkStyle(state.linkByEdgeKey[edgeKey].link);
            });
            renderInspector(root, null, 0, 0);
            return;
        }

        const visited = new Set();
        const queue = [componentId];
        while (queue.length) {
            const current = queue.shift();
            if (visited.has(current)) {
                continue;
            }
            visited.add(current);
            (adjacency[current] || new Set()).forEach(function (neighbor) {
                if (!visited.has(neighbor)) {
                    queue.push(neighbor);
                }
            });
        }

        Object.keys(state.elementByComponentId).forEach(function (id) {
            if (!visited.has(id)) {
                applyMutedElementStyle(state.elementByComponentId[id]);
            } else {
                applyPathElementStyle(state.elementByComponentId[id], id === componentId);
            }
        });

        const adjacentKeys = new Set((edgesByComponent[componentId] || []).map(getEdgeKey));
        Object.keys(state.linkByEdgeKey).forEach(function (edgeKey) {
            const entry = state.linkByEdgeKey[edgeKey];
            const edge = entry.edge;
            const inPath = visited.has(edge.from_component_id) && visited.has(edge.to_component_id);
            if (!inPath) {
                applyMutedLinkStyle(entry.link);
            } else {
                applyPathLinkStyle(entry.link, adjacentKeys.has(edgeKey));
            }
        });

        renderInspector(root, state.nodeByComponentId[componentId], visited.size, adjacentKeys.size);
    }

    function zoomPaper(root, scaleFactor) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const nextScale = Math.max(0.35, Math.min(1.8, Number((state.scale * scaleFactor).toFixed(3))));
        state.scale = nextScale;
        state.paper.scale(nextScale, nextScale);
    }

    function fitPaperToContent(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const area = state.graph.getBBox(state.graph.getElements());
        if (!area || !area.width || !area.height) {
            return;
        }
        const hostWidth = root.clientWidth || 1200;
        const hostHeight = root.clientHeight || 420;
        const scale = Math.max(0.4, Math.min(1.25, Math.min((hostWidth - 40) / area.width, (hostHeight - 40) / area.height)));
        state.scale = Number(scale.toFixed(3));
        state.paper.scale(state.scale, state.scale);
        const shell = root;
        const centeredLeft = Math.max(0, (area.x * state.scale) - ((hostWidth - area.width * state.scale) / 2));
        const centeredTop = Math.max(0, (area.y * state.scale) - ((hostHeight - area.height * state.scale) / 2));
        shell.scrollLeft = centeredLeft;
        shell.scrollTop = centeredTop;
    }

    function exportPaperAsSvg(root) {
        const state = root.__sldState;
        if (!state || !state.paper || !state.paper.svg) {
            return;
        }
        const svgMarkup = state.paper.svg.outerHTML;
        const blob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const projectId = root.dataset.projectId || 'project';
        link.href = url;
        link.download = `${projectId}_sld.svg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function () {
            URL.revokeObjectURL(url);
        }, 0);
    }

    function scheduleDerivedGeometryRefresh(root) {
        if (!root) {
            return;
        }
        if (root.__sldRefreshFrame) {
            cancelAnimationFrame(root.__sldRefreshFrame);
        }
        root.__sldRefreshFrame = requestAnimationFrame(function () {
            root.__sldRefreshFrame = null;
            refreshDerivedGeometry(root);
        });
    }

    function renderSldGraph(root, payload, savedLayout) {
        if (!payload || !payload.nodes || !payload.nodes.length) {
            renderEmptyState(root, 'No stored graph nodes were returned for this project.');
            return;
        }
        if (typeof joint === 'undefined') {
            renderEmptyState(root, 'JointJS is not available in the current page context.');
            return;
        }

        root.innerHTML = '';
        const canvas = document.createElement('div');
        canvas.className = 'sld-canvas';
        root.appendChild(canvas);

        const autoPositions = buildAutoLayout(payload);
        const layoutPositions = mergeSavedPositions(autoPositions, (savedLayout && savedLayout.positions) || {});
        const lineLabels = computeLineLabelPositions(payload, layoutPositions);
        const canvasSize = computeCanvasSize(payload, layoutPositions);

        const graph = new joint.dia.Graph();
        const paper = new joint.dia.Paper({
            el: canvas,
            model: graph,
            width: canvasSize.width,
            height: canvasSize.height,
            gridSize: 20,
            drawGrid: {
                name: 'mesh',
                args: [
                    {
                        color: 'rgba(148, 163, 184, 0.18)',
                        thickness: 1,
                    },
                ],
            },
            background: {
                color: 'rgba(255, 255, 255, 0.42)',
            },
            interactive: function (cellView) {
                const meta = cellView.model.prop('sldMeta') || {};
                return !!meta.componentId;
            },
        });

        const cells = [];
        const elementByComponentId = {};
        const endLabelByComponentId = {};
        const lineLabelByLineId = {};
        const linkByEdgeKey = {};
        const nodeByComponentId = {};

        lineLabels.forEach(function (lineLabel) {
            const label = createLineLabel(lineLabel.lineId, lineLabel.x, lineLabel.y);
            lineLabelByLineId[lineLabel.lineId] = label;
            cells.push(label);
        });

        payload.nodes.forEach(function (node) {
            const position = layoutPositions[node.component_id];
            if (!position) {
                return;
            }
            nodeByComponentId[node.component_id] = node;
            const element = createComponentElement(node, position);
            elementByComponentId[node.component_id] = element;
            cells.push(element);

            if (node.component_type === 'EndTermination') {
                const label = createEndTerminationLabel(node, position);
                endLabelByComponentId[node.component_id] = label;
                cells.push(label);
            }
        });

        payload.edges.forEach(function (edge) {
            const sourceCell = elementByComponentId[edge.from_component_id];
            const targetCell = elementByComponentId[edge.to_component_id];
            const sourceNode = nodeByComponentId[edge.from_component_id];
            const targetNode = nodeByComponentId[edge.to_component_id];
            if (!sourceCell || !targetCell || !sourceNode || !targetNode) {
                return;
            }
            const link = createDiagramLink(edge, sourceCell, targetCell, sourceNode, targetNode);
            linkByEdgeKey[getEdgeKey(edge)] = {
                edge: edge,
                link: link,
            };
            cells.push(link);
        });

        graph.resetCells(cells);

        const graphConnections = buildGraphAdjacency(payload);
        root.__sldState = {
            payload: payload,
            graph: graph,
            paper: paper,
            scale: 1,
            elementByComponentId: elementByComponentId,
            endLabelByComponentId: endLabelByComponentId,
            lineLabelByLineId: lineLabelByLineId,
            linkByEdgeKey: linkByEdgeKey,
            nodeByComponentId: nodeByComponentId,
            graphAdjacency: graphConnections.adjacency,
            edgesByComponent: graphConnections.edgesByComponent,
            isDirty: false,
            hasSavedLayout: !!(savedLayout && savedLayout.meta && savedLayout.meta.has_saved_layout),
            selectedComponentId: null,
        };

        graph.on('change:position', function (cell) {
            const meta = cell.prop('sldMeta') || {};
            if (!meta.componentId) {
                return;
            }
            scheduleDerivedGeometryRefresh(root);
            setDirtyState(root, true, true);
        });

        paper.on('element:pointerclick', function (elementView) {
            const meta = elementView.model.prop('sldMeta') || {};
            if (!meta.componentId) {
                return;
            }
            highlightSelection(root, meta.componentId);
        });

        paper.on('blank:pointerdown', function () {
            highlightSelection(root, null);
        });

        refreshDerivedGeometry(root);
        updateSavedCountBadge(root, (savedLayout && savedLayout.meta && savedLayout.meta.saved_count) || 0);
        setDirtyState(root, false, !!(savedLayout && savedLayout.meta && savedLayout.meta.has_saved_layout));
        highlightSelection(root, null);
        fitPaperToContent(root);
    }

    function filterPayloadForSelectedLine(payload, selectedLineId) {
        if (!selectedLineId) {
            return payload;
        }
        const targetGroup = (payload.line_groups || []).find(function (lineGroup) {
            return lineGroup.line_id === selectedLineId;
        });
        if (!targetGroup) {
            return payload;
        }
        const nodes = payload.nodes.filter(function (node) {
            return (node.line_ids || []).includes(selectedLineId);
        });
        const componentIds = new Set(nodes.map(function (node) { return node.component_id; }));
        const edges = payload.edges.filter(function (edge) {
            return componentIds.has(edge.from_component_id)
                && componentIds.has(edge.to_component_id)
                && (edge.line_ids || []).includes(selectedLineId);
        });
        return {
            project_id: payload.project_id,
            nodes: nodes,
            edges: edges,
            line_groups: [targetGroup],
            meta: {
                branch_count: (targetGroup.branch_indices || []).length,
                node_count: nodes.length,
                edge_count: edges.length,
            },
        };
    }

    function fetchSavedLayout(projectId, layoutUrl) {
        return $.ajax({
            url: layoutUrl,
            type: 'GET',
            data: { project_id: projectId },
        });
    }

    function fetchAndRenderSld(root) {
        const payloadUrl = root.dataset.sldPayloadUrl;
        const layoutUrl = root.dataset.sldLayoutUrl;
        const projectId = root.dataset.projectId;
        const selectedLineId = root.dataset.selectedLineId;
        if (!payloadUrl || !layoutUrl || !projectId) {
            return;
        }

        setSldMessage(root, 'Loading SLD', 'Preparing the stored project graph for rendering.', true);

        $.ajax({
            url: payloadUrl,
            type: 'GET',
            data: { project_id: projectId },
            success: function (payload) {
                const filteredPayload = filterPayloadForSelectedLine(payload, selectedLineId);
                fetchSavedLayout(projectId, layoutUrl)
                    .done(function (savedLayout) {
                        renderSldGraph(root, filteredPayload, savedLayout);
                    })
                    .fail(function () {
                        renderSldGraph(root, filteredPayload, { positions: {}, meta: { saved_count: 0, has_saved_layout: false, save_mode: 'merge' } });
                    });
            },
            error: function (xhr) {
                let errorMessage = 'Failed to load the stored SLD graph payload.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                }
                renderEmptyState(root, errorMessage);
            },
        });
    }

    function saveCurrentLayout(root) {
        const state = root.__sldState;
        const panel = root.closest('.sld-panel');
        const saveButton = panel ? panel.querySelector('#sld-save-layout') : null;
        if (!state || !saveButton || !state.isDirty) {
            return;
        }

        saveButton.disabled = true;
        const layoutUrl = saveButton.dataset.sldLayoutUrl;
        const projectId = saveButton.dataset.projectId;
        const positions = collectComponentPositions(state);

        $.ajax({
            url: layoutUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify({
                project_id: projectId,
                positions: positions,
            }),
            success: function (response) {
                updateSavedCountBadge(root, response.layout.meta.saved_count);
                setDirtyState(root, false, response.layout.meta.has_saved_layout);
                refreshDerivedGeometry(root);
                if (typeof window.showToast === 'function') {
                    window.showToast(response.success || 'SLD layout saved.', 'success');
                }
            },
            error: function (xhr) {
                saveButton.disabled = false;
                if (typeof window.handleErrorResponse === 'function' && xhr.response) {
                    window.handleErrorResponse(xhr);
                } else if (typeof window.showToast === 'function') {
                    const errorMessage = (xhr.responseJSON && xhr.responseJSON.error) || 'Failed to save the SLD layout.';
                    window.showToast(errorMessage, 'error');
                }
            },
        });
    }

    function resetCurrentLayout(root) {
        const panel = root.closest('.sld-panel');
        const resetButton = panel ? panel.querySelector('#sld-reset-layout') : null;
        if (!resetButton) {
            return;
        }
        const resetUrl = resetButton.dataset.sldLayoutResetUrl;
        const projectId = resetButton.dataset.projectId;

        resetButton.disabled = true;
        $.ajax({
            url: resetUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify({ project_id: projectId }),
            success: function (response) {
                root.__sldState = null;
                updateSavedCountBadge(root, 0);
                if (typeof window.showToast === 'function') {
                    window.showToast(response.success || 'Stored SLD layout reset.', 'info');
                }
                fetchAndRenderSld(root);
            },
            error: function (xhr) {
                resetButton.disabled = false;
                if (typeof window.handleErrorResponse === 'function' && xhr.response) {
                    window.handleErrorResponse(xhr);
                } else if (typeof window.showToast === 'function') {
                    const errorMessage = (xhr.responseJSON && xhr.responseJSON.error) || 'Failed to reset the SLD layout.';
                    window.showToast(errorMessage, 'error');
                }
            },
        });
    }

    $(document).on('click', '#sld-save-layout', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        saveCurrentLayout(root);
    });

    $(document).on('click', '#sld-reset-layout', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        resetCurrentLayout(root);
    });

    $(document).on('click', '#sld-fit-view', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        fitPaperToContent(root);
    });

    $(document).on('click', '#sld-zoom-in', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        zoomPaper(root, 1.12);
    });

    $(document).on('click', '#sld-zoom-out', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        zoomPaper(root, 0.9);
    });

    $(document).on('click', '#sld-export-svg', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        exportPaperAsSvg(root);
    });

    window.initializeSldWorkspace = function (container) {
        const root = $(container).find('#sld-diagram-shell')[0];
        if (!root) {
            return;
        }
        if (root.dataset.rendering === 'true') {
            return;
        }
        root.dataset.rendering = 'true';
        fetchAndRenderSld(root);
    };
}());
