(function () {
    const UPSTREAM_COMPONENT_ORDER = ['MCB', 'Cable4C', 'Isolator3PH', 'JB3PH'];
    const DOWNSTREAM_COMPONENT_ORDER = ['Isolator1PH', 'Cable3C', 'JB1PH', 'Tracer', 'EndTermination'];
    const COMPONENT_SORT_ORDER = {};
    const EXTERNAL_DETAIL_COMPONENTS = new Set(['Cable4C', 'Cable3C', 'Tracer']);
    const NODE_STYLE = {
        MCB: { width: 108, height: 54, fill: '#f3f7fb', stroke: '#1f3447' },
        Cable4C: { width: 132, height: 20, fill: '#fff8e8', stroke: '#7a5b2b' },
        Cable3C: { width: 120, height: 20, fill: '#fff8e8', stroke: '#7a5b2b' },
        Isolator3PH: { width: 82, height: 32, fill: '#edf6ff', stroke: '#31597f' },
        Isolator1PH: { width: 82, height: 32, fill: '#edf6ff', stroke: '#31597f' },
        JB3PH: { width: 96, height: 54, fill: '#f5f8fc', stroke: '#20394f' },
        JB1PH: { width: 78, height: 44, fill: '#f5f8fc', stroke: '#20394f' },
        Tracer: { width: 120, height: 20, fill: '#eefaf1', stroke: '#2f6c43' },
        EndTermination: { width: 28, height: 28, fill: '#243b53', stroke: '#1a2735' },
    };
    UPSTREAM_COMPONENT_ORDER.concat(DOWNSTREAM_COMPONENT_ORDER).forEach(function (componentType, index) {
        COMPONENT_SORT_ORDER[componentType] = index;
    });

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
        root.classList.remove('sld-diagram-shell--canvas');
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
        return node.display_name || node.component_type;
    }

    function formatExternalDetail(node) {
        const metadata = node.metadata || {};
        if (node.component_type === 'Cable4C' || node.component_type === 'Cable3C') {
            return metadata.length_m ? `${node.display_name} | ${metadata.length_m} m` : node.display_name;
        }
        if (node.component_type === 'Tracer') {
            return node.display_name || 'Heat Trace';
        }
        return '';
    }

    function createLineLabel(lineId, x, y) {
        const label = new joint.shapes.standard.TextBlock();
        label.position(x, y);
        label.resize(184, 34);
        label.attr({
            body: {
                fill: '#eef4f8',
                stroke: '#c9d6e2',
                strokeWidth: 1,
                rx: 4,
                ry: 4,
                cursor: 'move',
            },
            label: {
                text: `Line: ${lineId}`,
                fill: '#132f4c',
                fontSize: 15,
                fontWeight: 700,
                textAnchor: 'start',
                textVerticalAnchor: 'middle',
                x: 10,
                y: '50%',
                cursor: 'move',
            },
        });
        return label;
    }

    function createBranchLabel(branchIndex, x, y) {
        const label = new joint.shapes.standard.TextBlock();
        label.position(x, y);
        label.resize(64, 28);
        label.attr({
            body: {
                fill: '#f8fbfd',
                stroke: '#d3dee8',
                strokeWidth: 1,
                rx: 4,
                ry: 4,
                cursor: 'move',
            },
            label: {
                text: `B${branchIndex}`,
                fill: '#486581',
                fontSize: 12,
                fontWeight: 700,
                textAnchor: 'middle',
                textVerticalAnchor: 'middle',
                x: '50%',
                y: '50%',
                cursor: 'move',
            },
        });
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
        const isExternalDetailNode = EXTERNAL_DETAIL_COMPONENTS.has(node.component_type);
        rectangle.position(position.x, position.y - style.height / 2);
        rectangle.resize(style.width, style.height);
        rectangle.attr({
            body: {
                fill: style.fill,
                stroke: style.stroke,
                strokeWidth: 1.8,
                rx: isExternalDetailNode ? 2 : 4,
                ry: isExternalDetailNode ? 2 : 4,
            },
            label: {
                text: isExternalDetailNode ? node.display_tag : `${node.display_tag}\n${formatNodeBody(node)}`,
                fill: '#17324d',
                fontSize: isExternalDetailNode ? 10 : 12,
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

    function createExternalDetailLabel(node, position) {
        const style = getNodeStyle(node.component_type);
        const label = new joint.shapes.standard.TextBlock();
        label.position(position.x - 16, position.y + (style.height / 2) + 7);
        label.resize(style.width + 32, 26);
        label.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
            },
            label: {
                text: formatExternalDetail(node),
                fill: '#486581',
                fontSize: 10.5,
                fontWeight: 600,
                textAnchor: 'middle',
                textVerticalAnchor: 'top',
                x: '50%',
                y: 0,
            },
        });
        label.prop('sldMeta', { type: 'external-detail-label', ownerComponentId: node.component_id });
        return label;
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
        label.prop('sldMeta', { type: 'end-label', ownerComponentId: node.component_id });
        return label;
    }

    function shouldRenderExternalDetailLabel(node) {
        return EXTERNAL_DETAIL_COMPONENTS.has(node.component_type) && !!formatExternalDetail(node);
    }

    function nodeBelongsToLineGroup(node, lineGroup) {
        if (lineGroup.line_uid) {
            return String(node.line_uid || '') === String(lineGroup.line_uid);
        }
        return (node.line_ids || []).includes(lineGroup.line_id);
    }

    function getLineGroupKey(lineGroup) {
        return lineGroup.line_uid ? `uid:${lineGroup.line_uid}` : `line:${lineGroup.line_id}`;
    }

    function getBranchGroupKey(lineGroup, branchIndex) {
        return `${getLineGroupKey(lineGroup)}__branch:${branchIndex}`;
    }

    function getLineComponentIds(payload, lineGroup) {
        return payload.nodes
            .filter(function (node) { return nodeBelongsToLineGroup(node, lineGroup); })
            .map(function (node) { return node.component_id; });
    }

    function getBranchComponentIds(payload, lineGroup, branchIndex) {
        return payload.nodes
            .filter(function (node) {
                return nodeBelongsToLineGroup(node, lineGroup) && node.branch_index === branchIndex;
            })
            .map(function (node) { return node.component_id; });
    }

    function groupNodesByLine(payload) {
        return payload.line_groups.map(function (lineGroup) {
            const lineNodes = payload.nodes.filter(function (node) {
                return nodeBelongsToLineGroup(node, lineGroup);
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
                branches: branches,
            };
        });
    }

    function buildAutoLayout(payload) {
        const lineGroups = groupNodesByLine(payload);
        const positions = {};
        const startX = 200;
        const componentGap = 48;
        const branchGap = 102;
        const circuitGap = 108;
        const lineGap = 110;
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

    function getNodeByComponentId(payload) {
        const nodeById = {};
        (payload.nodes || []).forEach(function (node) {
            nodeById[node.component_id] = node;
        });
        return nodeById;
    }

    function compareNodesForLayout(left, right) {
        const leftCircuit = left.circuit_index === null || left.circuit_index === undefined ? -1 : Number(left.circuit_index);
        const rightCircuit = right.circuit_index === null || right.circuit_index === undefined ? -1 : Number(right.circuit_index);
        const leftOrder = Object.prototype.hasOwnProperty.call(COMPONENT_SORT_ORDER, left.component_type) ? COMPONENT_SORT_ORDER[left.component_type] : 99;
        const rightOrder = Object.prototype.hasOwnProperty.call(COMPONENT_SORT_ORDER, right.component_type) ? COMPONENT_SORT_ORDER[right.component_type] : 99;
        return [
            String(left.line_id || '').localeCompare(String(right.line_id || '')),
            Number(left.branch_index || 0) - Number(right.branch_index || 0),
            leftCircuit - rightCircuit,
            leftOrder - rightOrder,
            String(left.display_tag || '').localeCompare(String(right.display_tag || '')),
        ].find(function (result) { return result !== 0; }) || 0;
    }

    function buildOutgoingEdgesBySource(payload) {
        const outgoing = {};
        (payload.edges || []).forEach(function (edge) {
            outgoing[edge.from_component_id] = outgoing[edge.from_component_id] || [];
            outgoing[edge.from_component_id].push(edge);
        });
        return outgoing;
    }

    function sortOutgoingEdges(edges, nodeById) {
        return (edges || []).slice().sort(function (left, right) {
            return compareNodesForLayout(nodeById[left.to_component_id] || {}, nodeById[right.to_component_id] || {});
        });
    }

    function layoutManualCombineSubtree(componentId, depth, context, stack) {
        const node = context.nodeById[componentId];
        if (!node || stack.has(componentId)) {
            return null;
        }
        const nextStack = new Set(stack);
        nextStack.add(componentId);
        const childRanges = sortOutgoingEdges(context.outgoingBySource[componentId], context.nodeById)
            .map(function (edge) {
                return layoutManualCombineSubtree(edge.to_component_id, depth + 1, context, nextStack);
            })
            .filter(Boolean);

        let minY;
        let maxY;
        if (!childRanges.length) {
            minY = context.startY + (context.rowIndex * context.rowGap);
            maxY = minY;
            context.rowIndex += 1;
        } else {
            minY = Math.min.apply(null, childRanges.map(function (range) { return range.minY; }));
            maxY = Math.max.apply(null, childRanges.map(function (range) { return range.maxY; }));
        }

        context.positions[componentId] = {
            x: context.startX + (depth * context.levelGap),
            y: minY + ((maxY - minY) / 2),
        };
        context.lockedComponentIds.add(componentId);
        return { minY: minY, maxY: maxY };
    }

    function placeManualCombineTopology(payload, positions) {
        if (!payload.meta || payload.meta.topology_edit_type !== 'combine_feeders') {
            return { positions: positions, lockedComponentIds: new Set() };
        }
        const nodeById = getNodeByComponentId(payload);
        const roots = (payload.nodes || []).filter(function (node) {
            const metadata = node.metadata || {};
            return node.component_type === 'MCB' && metadata.manual_topology_edit === 'combine_feeders';
        }).sort(compareNodesForLayout);
        const context = {
            positions: positions,
            nodeById: nodeById,
            outgoingBySource: buildOutgoingEdgesBySource(payload),
            lockedComponentIds: new Set(),
            startX: 190,
            startY: 116,
            rowGap: 112,
            levelGap: 156,
            rowIndex: 0,
        };
        roots.forEach(function (rootNode, index) {
            if (index > 0) {
                context.rowIndex += 1;
            }
            layoutManualCombineSubtree(rootNode.component_id, 0, context, new Set());
        });
        return {
            positions: context.positions,
            lockedComponentIds: context.lockedComponentIds,
        };
    }

    function normalizeLayoutPositions(payload, positions) {
        let minLeft = Infinity;
        let minTop = Infinity;
        (payload.nodes || []).forEach(function (node) {
            const position = positions[node.component_id];
            if (!position) {
                return;
            }
            const style = getNodeStyle(node.component_type);
            minLeft = Math.min(minLeft, position.x);
            minTop = Math.min(minTop, position.y - (style.height / 2));
        });
        if (!Number.isFinite(minLeft) || !Number.isFinite(minTop)) {
            return positions;
        }
        const shiftX = minLeft < 40 ? 40 - minLeft : 0;
        const shiftY = minTop < 42 ? 42 - minTop : 0;
        if (!shiftX && !shiftY) {
            return positions;
        }
        Object.keys(positions).forEach(function (componentId) {
            positions[componentId] = {
                x: positions[componentId].x + shiftX,
                y: positions[componentId].y + shiftY,
            };
        });
        return positions;
    }

    function savedLayoutMatchesActiveTopology(payload, savedPositions) {
        if (!payload.meta || !payload.meta.has_topology_edit) {
            return true;
        }
        const manualNodeIds = (payload.nodes || [])
            .filter(function (node) { return !!((node.metadata || {}).manual_topology_edit); })
            .map(function (node) { return node.component_id; });
        const positions = savedPositions || {};
        return manualNodeIds.length > 0 && manualNodeIds.every(function (componentId) {
            return Boolean(positions[componentId]);
        });
    }

    function mergeSavedPositions(autoPositions, savedPositions, lockedComponentIds) {
        const merged = Object.assign({}, autoPositions);
        Object.keys(savedPositions || {}).forEach(function (componentId) {
            if (!merged[componentId]) {
                return;
            }
            if (lockedComponentIds && lockedComponentIds.has(componentId)) {
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
                return nodeBelongsToLineGroup(node, lineGroup) && positions[node.component_id];
            });
            if (!lineNodes.length) {
                return;
            }
            const yValues = lineNodes.map(function (node) { return positions[node.component_id].y; });
            const minY = Math.min.apply(null, yValues);
            const maxY = Math.max.apply(null, yValues);
            labelPositions.push({
                lineKey: getLineGroupKey(lineGroup),
                lineId: lineGroup.line_id,
                componentIds: getLineComponentIds(payload, lineGroup),
                x: 24,
                y: minY + ((maxY - minY) / 2) - 16,
            });
        });
        return labelPositions;
    }

    function computeBranchLabelPositions(payload, positions) {
        const labelPositions = [];
        payload.line_groups.forEach(function (lineGroup) {
            lineGroup.branch_indices.forEach(function (branchIndex) {
                const branchNodes = payload.nodes.filter(function (node) {
                    return nodeBelongsToLineGroup(node, lineGroup)
                        && node.branch_index === branchIndex
                        && positions[node.component_id];
                });
                if (!branchNodes.length) {
                    return;
                }
                const yValues = branchNodes.map(function (node) { return positions[node.component_id].y; });
                const minY = Math.min.apply(null, yValues);
                const maxY = Math.max.apply(null, yValues);
                labelPositions.push({
                    branchKey: getBranchGroupKey(lineGroup, branchIndex),
                    branchIndex: branchIndex,
                    componentIds: getBranchComponentIds(payload, lineGroup, branchIndex),
                    x: 84,
                    y: minY + ((maxY - minY) / 2) + 22,
                });
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

    function applyPathLinkStyle(link, isSelectedLink) {
        link.attr({
            line: {
                stroke: isSelectedLink ? '#c05621' : '#2f6c43',
                strokeWidth: isSelectedLink ? 3.4 : 2.8,
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
            if (!isDirty && root.__sldState.dirtyComponentIds) {
                root.__sldState.dirtyComponentIds.clear();
            }
        }
    }

    function setFitSelectedLineState(root, enabled) {
        const panel = root.closest('.sld-panel');
        const fitButton = panel ? panel.querySelector('#sld-fit-selected-line') : null;
        if (fitButton) {
            fitButton.disabled = !enabled;
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

    function getCombineSummaryContainer(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-combine-summary') : null;
    }

    function updateCombineControls(root) {
        const state = root.__sldState;
        const panel = root.closest('.sld-panel');
        const combineButton = panel ? panel.querySelector('#sld-combine-mode') : null;
        const splitButton = panel ? panel.querySelector('#sld-split-mode') : null;
        const applyButton = panel ? panel.querySelector('#sld-combine-apply') : null;
        const summary = getCombineSummaryContainer(root);
        const isSplit = !!(state && state.splitMode);
        const selectedSet = isSplit ? state.splitSelectionIds : state.combineSelectionIds;
        const selectedCount = selectedSet ? selectedSet.size : 0;
        const preview = isSplit ? state.splitPreview : state.combinePreview;
        const minimumSelection = isSplit ? 1 : 2;

        if (combineButton) {
            combineButton.classList.toggle('active', !!(state && state.combineMode));
        }
        if (splitButton) {
            splitButton.classList.toggle('active', isSplit);
        }
        if (applyButton) {
            applyButton.disabled = !(preview && preview.ok);
        }
        if (summary && state) {
            if (!(state.combineMode || state.splitMode)) {
                summary.textContent = 'Select Combine Feeders or Split Circuits to start a topology edit.';
            } else if (selectedCount < minimumSelection) {
                summary.textContent = isSplit
                    ? `Select at least ${minimumSelection} downstream circuit component.`
                    : `Select at least ${minimumSelection} MCB feeder sources.`;
            } else if (state.topologyPreviewStatus === 'checking') {
                summary.textContent = 'Checking selected topology edit...';
            } else if (state.topologyPreviewError) {
                summary.innerHTML = `<span class="text-danger fw-semibold">Cannot apply:</span> ${escapeHtml(state.topologyPreviewError)}`;
            } else if (preview && preview.ok && isSplit) {
                summary.innerHTML = `Selected ${selectedCount} circuit path(s). Add ${escapeHtml((preview.added_display_tags || []).join(', ') || '-')}; recommended MCB: <strong>${escapeHtml(preview.recommended_breaker_rating)}A</strong>.`;
            } else if (preview && preview.ok) {
                summary.innerHTML = `Selected ${selectedCount} feeder(s). Add ${escapeHtml((preview.added_display_tags || []).join(', ') || '-')}; remove ${escapeHtml((preview.removed_display_tags || []).join(', ') || '-')}; recommended MCB: <strong>${escapeHtml(preview.recommended_breaker_rating)}A</strong>.`;
            } else {
                summary.textContent = 'Waiting for automatic topology check.';
            }
        }
    }

    function buildInspectorRows(node, pathNodeCount, pathLinkCount) {
        const metadata = node.metadata || {};
        const rows = [
            ['Tag', node.display_tag || '-'],
            ['Component', node.display_name || node.component_type],
            ['Type', node.component_type],
            ['Line IDs', (node.line_ids || []).join(', ') || '-'],
            ['Branch', node.branch_index !== null && node.branch_index !== undefined ? node.branch_index : '-'],
            ['Circuit', node.circuit_index !== null && node.circuit_index !== undefined ? node.circuit_index : '-'],
            ['Path Nodes', pathNodeCount],
            ['Path Links', pathLinkCount],
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

    function renderInspector(root, node, pathNodeCount, pathLinkCount) {
        const summary = getSelectionSummaryContainer(root);
        const details = getInspectorDetailsContainer(root);
        if (!summary || !details) {
            return;
        }
        if (!node) {
            summary.textContent = 'Select a component in the diagram to inspect its details and highlight the source path.';
            details.innerHTML = '';
            return;
        }
        summary.innerHTML = `Selected <strong>${escapeHtml(node.display_tag || node.component_type)}</strong>. Highlighted path follows the directed source-to-component route in the current rendered graph.`;
        details.innerHTML = buildInspectorRows(node, pathNodeCount, pathLinkCount).map(function (row) {
            return `<dt>${escapeHtml(row[0])}</dt><dd>${escapeHtml(row[1])}</dd>`;
        }).join('');
    }

    function applyCombineSelectionStyle(state) {
        Object.keys(state.elementByComponentId).forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            const node = state.nodeByComponentId[componentId];
            if (!element || !node) {
                return;
            }
            if (state.combineSelectionIds.has(componentId) || state.splitSelectionIds.has(componentId)) {
                element.attr('body/stroke', '#0d6efd');
                element.attr('body/strokeWidth', 3.2);
            } else if (!state.selectedComponentId) {
                applyDefaultElementStyle(element);
            }
        });
    }

    function toggleCombineSelection(root, componentId) {
        const state = root.__sldState;
        const node = state && state.nodeByComponentId[componentId];
        if (!state || !node || node.component_type !== 'MCB') {
            return;
        }
        if (state.combineSelectionIds.has(componentId)) {
            state.combineSelectionIds.delete(componentId);
        } else {
            state.combineSelectionIds.add(componentId);
        }
        state.combinePreview = null;
        state.topologyPreviewError = '';
        state.topologyPreviewStatus = 'idle';
        state.topologyPreviewKey = '';
        applyCombineSelectionStyle(state);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    }

    function toggleSplitSelection(root, componentId) {
        const state = root.__sldState;
        const node = state && state.nodeByComponentId[componentId];
        if (!state || !node || node.component_type === 'MCB' || node.circuit_index === null || node.circuit_index === undefined) {
            return;
        }
        if (state.splitSelectionIds.has(componentId)) {
            state.splitSelectionIds.delete(componentId);
        } else {
            state.splitSelectionIds.add(componentId);
        }
        state.splitPreview = null;
        state.topologyPreviewError = '';
        state.topologyPreviewStatus = 'idle';
        state.topologyPreviewKey = '';
        applyCombineSelectionStyle(state);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    }

    function collectComponentPositions(state, componentIds) {
        const positions = {};
        (componentIds || Object.keys(state.elementByComponentId)).forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            if (!element) {
                return;
            }
            const position = element.position();
            const size = element.size();
            positions[componentId] = {
                x: position.x,
                y: position.y + size.height / 2,
            };
        });
        return positions;
    }

    function markDirtyComponents(state, componentIds) {
        if (!state || !state.dirtyComponentIds) {
            return;
        }
        (componentIds || []).forEach(function (componentId) {
            if (state.elementByComponentId[componentId]) {
                state.dirtyComponentIds.add(componentId);
            }
        });
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

    function moveAttachedLabels(state, componentId, deltaX, deltaY) {
        [
            state.externalDetailLabelByComponentId[componentId],
            state.endLabelByComponentId[componentId],
        ].forEach(function (label) {
            if (!label) {
                return;
            }
            const position = label.position();
            label.position(position.x + deltaX, position.y + deltaY);
        });
    }

    function moveComponentGroup(root, componentIds, deltaX, deltaY) {
        const state = root.__sldState;
        if (!state || !componentIds || (!deltaX && !deltaY)) {
            return;
        }
        // Regrouping is presentation-only: move rendered nodes, then save their coordinates.
        state.isApplyingGroupMove = true;
        componentIds.forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            if (!element) {
                return;
            }
            const position = element.position();
            element.position(position.x + deltaX, position.y + deltaY);
            moveAttachedLabels(state, componentId, deltaX, deltaY);
        });
        state.isApplyingGroupMove = false;
        updateLinkGeometry(root);
    }

    function syncGroupHandlePosition(groupHandlePositionById, handle) {
        if (!groupHandlePositionById || !handle) {
            return;
        }
        const position = handle.position();
        groupHandlePositionById[handle.id] = {
            x: position.x,
            y: position.y,
        };
    }

    function refreshDynamicLabels(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }

        // Labels for cable/tracer metadata are derived from node position instead of
        // saved separately. That keeps layout persistence focused on component nodes.
        state.isSyncingDerivedGeometry = true;
        try {
            Object.keys(state.externalDetailLabelByComponentId).forEach(function (componentId) {
                const label = state.externalDetailLabelByComponentId[componentId];
                const element = state.elementByComponentId[componentId];
                const node = state.nodeByComponentId[componentId];
                if (!label || !element || !node) {
                    return;
                }
                const position = element.position();
                const size = element.size();
                label.position(position.x - 16, position.y + size.height + 7);
            });

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
                const label = state.lineLabelByLineKey[lineLabel.lineKey];
                if (label) {
                    label.position(lineLabel.x, lineLabel.y);
                    syncGroupHandlePosition(state.groupHandlePositionById, label);
                }
            });
            computeBranchLabelPositions(state.payload, positions).forEach(function (branchLabel) {
                const label = state.branchLabelByBranchKey[branchLabel.branchKey];
                if (label) {
                    label.position(branchLabel.x, branchLabel.y);
                    syncGroupHandlePosition(state.groupHandlePositionById, label);
                }
            });
        } finally {
            state.isSyncingDerivedGeometry = false;
        }
    }

    function refreshDerivedGeometry(root) {
        refreshDynamicLabels(root);
        updateLinkGeometry(root);
    }

    function buildGraphNavigation(payload) {
        const outgoingByComponent = {};
        const incomingCountByComponent = {};
        (payload.nodes || []).forEach(function (node) {
            outgoingByComponent[node.component_id] = [];
            incomingCountByComponent[node.component_id] = 0;
        });
        (payload.edges || []).forEach(function (edge) {
            if (!outgoingByComponent[edge.from_component_id]) {
                outgoingByComponent[edge.from_component_id] = [];
            }
            if (incomingCountByComponent[edge.to_component_id] === undefined) {
                incomingCountByComponent[edge.to_component_id] = 0;
            }
            outgoingByComponent[edge.from_component_id].push({
                edge: edge,
                targetId: edge.to_component_id,
                edgeKey: getEdgeKey(edge),
            });
            incomingCountByComponent[edge.to_component_id] += 1;
        });
        return { outgoingByComponent: outgoingByComponent, incomingCountByComponent: incomingCountByComponent };
    }

    function findSourcePath(state, componentId) {
        const nodeIds = Object.keys(state.nodeByComponentId);
        const preferredSources = nodeIds.filter(function (nodeId) {
            return state.nodeByComponentId[nodeId].component_type === 'MCB';
        });
        const fallbackSources = nodeIds.filter(function (nodeId) {
            return (state.incomingCountByComponent[nodeId] || 0) === 0;
        });
        const sourceIds = preferredSources.length ? preferredSources : fallbackSources;
        const visited = new Set();
        const previous = {};
        const queue = [];

        sourceIds.forEach(function (sourceId) {
            visited.add(sourceId);
            previous[sourceId] = null;
            queue.push(sourceId);
        });

        // SLD edges are emitted upstream-to-downstream, so this walks the real
        // source path instead of highlighting every node in the connected graph.
        while (queue.length && !visited.has(componentId)) {
            const currentId = queue.shift();
            (state.outgoingByComponent[currentId] || []).forEach(function (entry) {
                if (visited.has(entry.targetId)) {
                    return;
                }
                visited.add(entry.targetId);
                previous[entry.targetId] = {
                    nodeId: currentId,
                    edgeKey: entry.edgeKey,
                };
                queue.push(entry.targetId);
            });
        }

        if (!visited.has(componentId)) {
            return { nodeIds: new Set([componentId]), edgeKeys: new Set() };
        }

        const pathNodeIds = new Set([componentId]);
        const pathEdgeKeys = new Set();
        let cursorId = componentId;
        while (previous[cursorId]) {
            pathEdgeKeys.add(previous[cursorId].edgeKey);
            cursorId = previous[cursorId].nodeId;
            pathNodeIds.add(cursorId);
        }
        return { nodeIds: pathNodeIds, edgeKeys: pathEdgeKeys };
    }

    function highlightSelection(root, componentId) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        state.selectedComponentId = componentId || null;

        if (!componentId || !state.nodeByComponentId[componentId]) {
            Object.keys(state.elementByComponentId).forEach(function (id) {
                applyDefaultElementStyle(state.elementByComponentId[id]);
            });
            Object.keys(state.linkByEdgeKey).forEach(function (edgeKey) {
                applyDefaultLinkStyle(state.linkByEdgeKey[edgeKey].link);
            });
            setFitSelectedLineState(root, false);
            renderInspector(root, null, 0, 0);
            return;
        }

        const path = findSourcePath(state, componentId);

        Object.keys(state.elementByComponentId).forEach(function (id) {
            if (path.nodeIds.has(id)) {
                applyPathElementStyle(state.elementByComponentId[id], id === componentId);
            } else {
                applyMutedElementStyle(state.elementByComponentId[id]);
            }
        });

        Object.keys(state.linkByEdgeKey).forEach(function (edgeKey) {
            const entry = state.linkByEdgeKey[edgeKey];
            if (path.edgeKeys.has(edgeKey)) {
                applyPathLinkStyle(
                    entry.link,
                    entry.edge.from_component_id === componentId || entry.edge.to_component_id === componentId
                );
                return;
            }
            applyMutedLinkStyle(entry.link);
        });

        setFitSelectedLineState(root, true);
        renderInspector(root, state.nodeByComponentId[componentId], path.nodeIds.size, path.edgeKeys.size);
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

    function fitPaperToElements(root, elements) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const area = state.graph.getBBox(elements);
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

    function fitPaperToContent(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        fitPaperToElements(root, state.graph.getElements());
    }

    function getSelectedLineElements(state) {
        const selectedNode = state.nodeByComponentId[state.selectedComponentId];
        if (!selectedNode) {
            return [];
        }
        const matchingGroups = (state.payload.line_groups || []).filter(function (lineGroup) {
            return nodeBelongsToLineGroup(selectedNode, lineGroup);
        });
        const componentIds = new Set();
        matchingGroups.forEach(function (lineGroup) {
            (state.payload.nodes || []).forEach(function (node) {
                if (nodeBelongsToLineGroup(node, lineGroup)) {
                    componentIds.add(node.component_id);
                }
            });
        });

        const elements = [];
        matchingGroups.forEach(function (lineGroup) {
            const label = state.lineLabelByLineKey[getLineGroupKey(lineGroup)];
            if (label) {
                elements.push(label);
            }
            (lineGroup.branch_indices || []).forEach(function (branchIndex) {
                const branchLabel = state.branchLabelByBranchKey[getBranchGroupKey(lineGroup, branchIndex)];
                if (branchLabel) {
                    elements.push(branchLabel);
                }
            });
        });
        componentIds.forEach(function (componentId) {
            [
                state.elementByComponentId[componentId],
                state.externalDetailLabelByComponentId[componentId],
                state.endLabelByComponentId[componentId],
            ].forEach(function (element) {
                if (element) {
                    elements.push(element);
                }
            });
        });
        return elements;
    }

    function fitSelectedLine(root) {
        const state = root.__sldState;
        if (!state || !state.selectedComponentId) {
            return;
        }
        const elements = getSelectedLineElements(state);
        if (elements.length) {
            fitPaperToElements(root, elements);
        }
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
        root.classList.add('sld-diagram-shell--canvas');
        const canvas = document.createElement('div');
        canvas.className = 'sld-canvas';
        root.appendChild(canvas);

        let manualLayout = { positions: buildAutoLayout(payload), lockedComponentIds: new Set() };
        try {
            manualLayout = placeManualCombineTopology(payload, manualLayout.positions);
        } catch (error) {
            // Experimental edited-topology layout must never prevent SLD rendering.
            console.error('SLD edited-topology layout failed; falling back to generated layout.', error);
        }
        const savedPositions = (savedLayout && savedLayout.positions) || {};
        const mergedPositions = savedLayoutMatchesActiveTopology(payload, savedPositions)
            ? mergeSavedPositions(manualLayout.positions, savedPositions, manualLayout.lockedComponentIds)
            : manualLayout.positions;
        const layoutPositions = normalizeLayoutPositions(payload, mergedPositions);
        const lineLabels = computeLineLabelPositions(payload, layoutPositions);
        const branchLabels = computeBranchLabelPositions(payload, layoutPositions);
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
                return !!meta.componentId || !!meta.draggableGroup;
            },
        });

        const cells = [];
        const elementByComponentId = {};
        const externalDetailLabelByComponentId = {};
        const endLabelByComponentId = {};
        const lineLabelByLineKey = {};
        const branchLabelByBranchKey = {};
        const groupHandlePositionById = {};
        const linkByEdgeKey = {};
        const nodeByComponentId = {};

        lineLabels.forEach(function (lineLabel) {
            const label = createLineLabel(lineLabel.lineId, lineLabel.x, lineLabel.y);
            label.prop('sldMeta', {
                type: 'line-label',
                lineId: lineLabel.lineId,
                draggableGroup: true,
                moveComponentIds: lineLabel.componentIds,
            });
            lineLabelByLineKey[lineLabel.lineKey] = label;
            syncGroupHandlePosition(groupHandlePositionById, label);
            cells.push(label);
        });

        branchLabels.forEach(function (branchLabel) {
            const label = createBranchLabel(branchLabel.branchIndex, branchLabel.x, branchLabel.y);
            label.prop('sldMeta', {
                type: 'branch-label',
                branchIndex: branchLabel.branchIndex,
                draggableGroup: true,
                moveComponentIds: branchLabel.componentIds,
            });
            branchLabelByBranchKey[branchLabel.branchKey] = label;
            syncGroupHandlePosition(groupHandlePositionById, label);
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

            if (shouldRenderExternalDetailLabel(node)) {
                const detailLabel = createExternalDetailLabel(node, position);
                externalDetailLabelByComponentId[node.component_id] = detailLabel;
                cells.push(detailLabel);
            }

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

        const graphNavigation = buildGraphNavigation(payload);
        root.__sldState = {
            payload: payload,
            graph: graph,
            paper: paper,
            scale: 1,
            elementByComponentId: elementByComponentId,
            externalDetailLabelByComponentId: externalDetailLabelByComponentId,
            endLabelByComponentId: endLabelByComponentId,
            lineLabelByLineKey: lineLabelByLineKey,
            branchLabelByBranchKey: branchLabelByBranchKey,
            groupHandlePositionById: groupHandlePositionById,
            linkByEdgeKey: linkByEdgeKey,
            nodeByComponentId: nodeByComponentId,
            outgoingByComponent: graphNavigation.outgoingByComponent,
            incomingCountByComponent: graphNavigation.incomingCountByComponent,
            isDirty: false,
            hasSavedLayout: !!(savedLayout && savedLayout.meta && savedLayout.meta.has_saved_layout),
            dirtyComponentIds: new Set(),
            selectedComponentId: null,
            combineMode: false,
            combineSelectionIds: new Set(),
            combinePreview: null,
            splitMode: false,
            splitSelectionIds: new Set(),
            splitPreview: null,
            topologyPreviewStatus: 'idle',
            topologyPreviewError: '',
            topologyPreviewKey: '',
            topologyPreviewTimer: null,
            isApplyingGroupMove: false,
            isSyncingDerivedGeometry: false,
        };
        setFitSelectedLineState(root, false);

        graph.on('change:position', function (cell) {
            const state = root.__sldState;
            if (!state || state.isSyncingDerivedGeometry) {
                return;
            }
            const meta = cell.prop('sldMeta') || {};
            if (meta.draggableGroup) {
                const position = cell.position();
                const previous = state.groupHandlePositionById[cell.id] || position;
                state.groupHandlePositionById[cell.id] = {
                    x: position.x,
                    y: position.y,
                };
                moveComponentGroup(
                    root,
                    meta.moveComponentIds || [],
                    position.x - previous.x,
                    position.y - previous.y
                );
                markDirtyComponents(state, meta.moveComponentIds || []);
                setDirtyState(root, true, true);
                return;
            }
            if (state.isApplyingGroupMove) {
                return;
            }
            if (!meta.componentId) {
                return;
            }
            markDirtyComponents(state, [meta.componentId]);
            scheduleDerivedGeometryRefresh(root);
            setDirtyState(root, true, true);
        });

        paper.on('element:pointerclick', function (elementView) {
            const meta = elementView.model.prop('sldMeta') || {};
            if (!meta.componentId) {
                return;
            }
            if (root.__sldState && root.__sldState.combineMode) {
                toggleCombineSelection(root, meta.componentId);
                return;
            }
            if (root.__sldState && root.__sldState.splitMode) {
                toggleSplitSelection(root, meta.componentId);
                return;
            }
            highlightSelection(root, meta.componentId);
        });

        paper.on('blank:pointerdown', function () {
            highlightSelection(root, null);
        });

        paper.on('cell:pointerup', function () {
            refreshDerivedGeometry(root);
        });

        refreshDerivedGeometry(root);
        updateSavedCountBadge(root, (savedLayout && savedLayout.meta && savedLayout.meta.saved_count) || 0);
        setDirtyState(root, false, !!(savedLayout && savedLayout.meta && savedLayout.meta.has_saved_layout));
        updateCombineControls(root);
        highlightSelection(root, null);
        fitPaperToContent(root);
    }

    function fetchSavedLayout(projectId, layoutUrl, selectedLineId) {
        const requestData = { project_id: projectId };
        if (selectedLineId) {
            requestData.line_id = selectedLineId;
        }
        return $.ajax({
            url: layoutUrl,
            type: 'GET',
            data: requestData,
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

        const requestData = { project_id: projectId };
        if (selectedLineId) {
            requestData.line_id = selectedLineId;
        }

        $.ajax({
            url: payloadUrl,
            type: 'GET',
            data: requestData,
            success: function (payload) {
                fetchSavedLayout(projectId, layoutUrl, selectedLineId)
                    .done(function (savedLayout) {
                        renderSldGraph(root, payload, savedLayout);
                    })
                    .fail(function () {
                        renderSldGraph(root, payload, { positions: {}, meta: { saved_count: 0, has_saved_layout: false, save_mode: 'merge' } });
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
        const dirtyComponentIds = state.dirtyComponentIds && state.dirtyComponentIds.size
            ? Array.from(state.dirtyComponentIds)
            : Object.keys(state.elementByComponentId);
        const positions = collectComponentPositions(state, dirtyComponentIds);
        const selectedLineId = root.dataset.selectedLineId;
        const requestPayload = {
            project_id: projectId,
            positions: positions,
        };
        if (selectedLineId) {
            requestPayload.line_id = selectedLineId;
        }

        $.ajax({
            url: layoutUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify(requestPayload),
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

    function postTopologyRequest(root, url, selectedIds, includeRemarks) {
        const state = root.__sldState;
        if (!state || !url || !selectedIds || !selectedIds.size) {
            return null;
        }
        const panel = root.closest('.sld-panel');
        const remarks = panel ? panel.querySelector('#sld-combine-remarks') : null;
        const payload = {
            project_id: root.dataset.projectId,
            component_ids: Array.from(selectedIds),
        };
        if (includeRemarks && remarks) {
            payload.remarks = remarks.value;
        }
        return $.ajax({
            url: url,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify(payload),
        });
    }

    function runTopologyPreview(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const isSplit = !!(state && state.splitMode);
        const url = isSplit ? root.dataset.sldTopologySplitPreviewUrl : root.dataset.sldTopologyCombinePreviewUrl;
        const selectedIds = isSplit ? state.splitSelectionIds : state.combineSelectionIds;
        const minimumSelection = isSplit ? 1 : 2;
        if (!(state.combineMode || state.splitMode) || selectedIds.size < minimumSelection) {
            state.topologyPreviewStatus = 'idle';
            state.topologyPreviewError = '';
            state.topologyPreviewKey = '';
            updateCombineControls(root);
            return;
        }
        const requestKey = `${isSplit ? 'split' : 'combine'}:${Array.from(selectedIds).sort().join('|')}`;
        state.topologyPreviewKey = requestKey;
        state.topologyPreviewStatus = 'checking';
        state.topologyPreviewError = '';
        updateCombineControls(root);
        const request = postTopologyRequest(root, url, selectedIds, false);
        if (!request) {
            state.topologyPreviewStatus = 'idle';
            updateCombineControls(root);
            return;
        }
        request.done(function (preview) {
            if (!root.__sldState || root.__sldState.topologyPreviewKey !== requestKey) {
                return;
            }
            if (isSplit) {
                root.__sldState.splitPreview = preview;
            } else {
                root.__sldState.combinePreview = preview;
            }
            root.__sldState.topologyPreviewStatus = 'ready';
            root.__sldState.topologyPreviewError = '';
            updateCombineControls(root);
        }).fail(function (xhr) {
            if (!root.__sldState || root.__sldState.topologyPreviewKey !== requestKey) {
                return;
            }
            if (isSplit) {
                root.__sldState.splitPreview = null;
            } else {
                root.__sldState.combinePreview = null;
            }
            root.__sldState.topologyPreviewStatus = 'error';
            root.__sldState.topologyPreviewError = (xhr.responseJSON && xhr.responseJSON.error) || 'Selected topology edit is not allowed.';
            updateCombineControls(root);
        });
    }

    function scheduleTopologyPreview(root) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        if (state.topologyPreviewTimer) {
            clearTimeout(state.topologyPreviewTimer);
        }
        state.topologyPreviewTimer = setTimeout(function () {
            state.topologyPreviewTimer = null;
            runTopologyPreview(root);
        }, 250);
    }

    function applyCombineFeeders(root) {
        const state = root.__sldState;
        const isSplit = !!(state && state.splitMode);
        const url = isSplit ? root.dataset.sldTopologySplitApplyUrl : root.dataset.sldTopologyCombineApplyUrl;
        const selectedIds = isSplit ? state.splitSelectionIds : state.combineSelectionIds;
        const request = postTopologyRequest(root, url, selectedIds, true);
        if (!request) {
            return;
        }
        request.done(function (response) {
            if (typeof window.showToast === 'function') {
                window.showToast(response.success || 'Topology edit applied.', 'success');
            }
            const warnings = response.validation_summary && response.validation_summary.warnings;
            updateTopologyStateUi(root, {
                hasEdit: true,
                editType: response.preview ? response.preview.edit_type : 'manual',
                warning: warnings && warnings.length ? warnings[0] : '',
            });
            fetchAndRenderSld(root);
        }).fail(function (xhr) {
            if (typeof window.showToast === 'function') {
                window.showToast((xhr.responseJSON && xhr.responseJSON.error) || 'Unable to apply topology edit.', 'error');
            }
        });
    }

    function updateTopologyStateUi(root, topologyState) {
        const panel = root.closest('.sld-panel');
        if (!panel) {
            return;
        }
        const hasEdit = !!(topologyState && topologyState.hasEdit);
        const badge = panel.querySelector('.sld-topology-state-badge');
        const resetButton = panel.querySelector('#sld-topology-reset');
        let alert = panel.querySelector('.sld-topology-edit-alert');

        if (badge) {
            if (topologyState && topologyState.baselineChanged) {
                badge.textContent = 'Baseline Recalculated';
                badge.className = 'badge text-bg-danger sld-topology-state-badge';
            } else {
                badge.textContent = hasEdit ? 'Topology Edited' : 'Generated Topology';
                badge.className = hasEdit
                    ? 'badge text-bg-warning text-dark sld-topology-state-badge'
                    : 'badge text-bg-light border sld-topology-state-badge';
            }
        }
        if (resetButton) {
            resetButton.disabled = !hasEdit;
        }
        if (!hasEdit) {
            if (alert) {
                alert.remove();
            }
            return;
        }
        if (!alert) {
            const form = panel.querySelector('#sld-line-filter-form');
            alert = document.createElement('div');
            alert.className = 'alert alert-warning py-2 mb-3 sld-topology-edit-alert';
            if (form && form.parentNode) {
                form.parentNode.insertBefore(alert, form);
            }
        }
        if (alert) {
            const editType = topologyState.editType || 'manual';
            const warning = topologyState.warning || 'Review downstream BOQ and cable schedule outputs before issue.';
            alert.innerHTML = `Active topology edit: <strong>${escapeHtml(editType)}</strong>. ${escapeHtml(warning)}`;
        }
    }

    function resetTopologyEdit(root) {
        const url = root.dataset.sldTopologyResetUrl;
        const projectId = root.dataset.projectId;
        if (!url || !projectId) {
            return;
        }
        $.ajax({
            url: url,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify({ project_id: projectId }),
        }).done(function (response) {
            if (root.__sldState) {
                if (root.__sldState.topologyPreviewTimer) {
                    clearTimeout(root.__sldState.topologyPreviewTimer);
                }
                root.__sldState.combineMode = false;
                root.__sldState.splitMode = false;
                root.__sldState.combineSelectionIds.clear();
                root.__sldState.splitSelectionIds.clear();
                root.__sldState.combinePreview = null;
                root.__sldState.splitPreview = null;
                root.__sldState.topologyPreviewStatus = 'idle';
                root.__sldState.topologyPreviewError = '';
                root.__sldState.topologyPreviewKey = '';
            }
            updateTopologyStateUi(root, { hasEdit: false });
            updateCombineControls(root);
            if (typeof window.showToast === 'function') {
                window.showToast(response.success || 'Topology edit reset.', 'info');
            }
            fetchAndRenderSld(root);
        }).fail(function (xhr) {
            if (typeof window.showToast === 'function') {
                window.showToast((xhr.responseJSON && xhr.responseJSON.error) || 'Unable to reset topology edit.', 'error');
            }
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

    $(document).on('click', '#sld-combine-mode', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldState) {
            return;
        }
        root.__sldState.combineMode = !root.__sldState.combineMode;
        root.__sldState.splitMode = false;
        root.__sldState.combinePreview = null;
        root.__sldState.splitPreview = null;
        root.__sldState.topologyPreviewStatus = 'idle';
        root.__sldState.topologyPreviewError = '';
        root.__sldState.topologyPreviewKey = '';
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    });

    $(document).on('click', '#sld-split-mode', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldState) {
            return;
        }
        root.__sldState.splitMode = !root.__sldState.splitMode;
        root.__sldState.combineMode = false;
        root.__sldState.combinePreview = null;
        root.__sldState.splitPreview = null;
        root.__sldState.topologyPreviewStatus = 'idle';
        root.__sldState.topologyPreviewError = '';
        root.__sldState.topologyPreviewKey = '';
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    });

    $(document).on('click', '#sld-combine-apply', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (root) {
            applyCombineFeeders(root);
        }
    });

    $(document).on('click', '#sld-topology-reset', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (root) {
            resetTopologyEdit(root);
        }
    });

    $(document).on('click', '#sld-fit-view', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        fitPaperToContent(root);
    });

    $(document).on('click', '#sld-fit-selected-line', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root) {
            return;
        }
        fitSelectedLine(root);
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
