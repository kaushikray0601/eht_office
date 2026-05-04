(function () {
    const UPSTREAM_COMPONENT_ORDER = ['MCB', 'Cable4C', 'Isolator3PH', 'JB3PH'];
    const DOWNSTREAM_COMPONENT_ORDER = ['Isolator1PH', 'Cable3C', 'JB1PH', 'Tracer', 'EndTermination'];
    const COMPONENT_SORT_ORDER = {};
    const EXTERNAL_DETAIL_COMPONENTS = new Set(['Cable4C', 'Cable3C', 'Tracer']);
    const CABLE_COMPONENTS = new Set(['Cable4C', 'Cable3C']);
    const SLD_LABEL_FONT_SIZE = 9.5;
    const SLD_LABEL_FONT_WEIGHT = 500;
    const POWER_LINK_OVERLAP = 4;
    const NODE_STYLE = {
        MCB: { width: 116, height: 60, fill: '#f3f7fb', stroke: '#1f3447' },
        Cable4C: { width: 74, height: 12, fill: '#fff8e8', stroke: '#7a5b2b' },
        Cable3C: { width: 70, height: 12, fill: '#fff8e8', stroke: '#7a5b2b' },
        Isolator3PH: { width: 88, height: 54, fill: '#edf6ff', stroke: '#31597f' },
        Isolator1PH: { width: 88, height: 54, fill: '#edf6ff', stroke: '#31597f' },
        JB3PH: { width: 96, height: 54, fill: '#f5f8fc', stroke: '#20394f' },
        JB1PH: { width: 78, height: 44, fill: '#f5f8fc', stroke: '#20394f' },
        Tracer: { width: 120, height: 28, fill: 'transparent', stroke: '#c2410c' },
        EndTermination: { width: 14, height: 14, fill: '#243b53', stroke: '#1a2735' },
    };
    const SCHEMATIC_SYMBOL_COMPONENTS = new Set(['MCB', 'Isolator3PH', 'Isolator1PH', 'JB3PH', 'JB1PH', 'Tracer']);
    let SchematicSymbolElement = null;
    UPSTREAM_COMPONENT_ORDER.concat(DOWNSTREAM_COMPONENT_ORDER).forEach(function (componentType, index) {
        COMPONENT_SORT_ORDER[componentType] = index;
    });

    function getNodeStyle(componentType) {
        return NODE_STYLE[componentType] || { width: 100, height: 40, fill: '#f8fafc', stroke: '#1f3447' };
    }

    function isSchematicSymbolComponent(componentType) {
        return SCHEMATIC_SYMBOL_COMPONENTS.has(componentType);
    }

    function getSchematicSymbolElementClass() {
        if (!SchematicSymbolElement) {
            SchematicSymbolElement = joint.dia.Element.define('sld.SchematicSymbolElement', {}, {
                markup: [
                    { tagName: 'rect', selector: 'body' },
                    { tagName: 'path', selector: 'terminalPath' },
                    { tagName: 'path', selector: 'symbolPath' },
                    { tagName: 'circle', selector: 'symbolRing' },
                    { tagName: 'circle', selector: 'dot1' },
                    { tagName: 'circle', selector: 'dot2' },
                    { tagName: 'circle', selector: 'dot3' },
                    { tagName: 'text', selector: 'tagLabel' },
                    { tagName: 'text', selector: 'bodyLabel' },
                ],
            });
        }
        return SchematicSymbolElement;
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
            const cableLabel = metadata.manual_cable_size || metadata.cable_size || node.display_name;
            const engineeringLabel = metadata.length_m ? `${cableLabel} ${metadata.length_m} m` : cableLabel;
            return `${node.display_tag}\n${engineeringLabel}`;
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

    function mapInlineSvgSymbolPoint(rawX, rawY, centerX, centerY, lengthScale, widthScale) {
        return {
            x: centerX + ((rawY - 25) * lengthScale),
            y: centerY + ((rawX - 10) * widthScale),
        };
    }

    function getJbOutgoingSlotOffsets(node, context) {
        if (!context || !context.outgoingBySource || node.component_type !== 'JB3PH') {
            return [];
        }
        const outgoing = sortOutgoingEdges(context.outgoingBySource[node.component_id] || [], context.nodeById);
        const downstream = outgoing.filter(function (edge) {
            const targetNode = context.nodeById[edge.to_component_id];
            return targetNode && CABLE_COMPONENTS.has(targetNode.component_type);
        });
        if (downstream.length === 1) {
            return [0];
        }
        if (downstream.length === 2) {
            return [-12, 0];
        }
        if (downstream.length === 3) {
            return [-12, 0, 12];
        }
        const count = Math.max(3, downstream.length);
        const spacing = 36 / Math.max(1, count - 1);
        return Array.from({ length: count }, function (_, index) {
            return -18 + (index * spacing);
        });
    }

    function getJbOutgoingSlotOffset(edge, sourceNode, context) {
        if (!sourceNode || sourceNode.component_type !== 'JB3PH' || !context || !context.outgoingBySource) {
            return 0;
        }
        const outgoing = sortOutgoingEdges(context.outgoingBySource[sourceNode.component_id] || [], context.nodeById)
            .filter(function (candidate) {
                const targetNode = context.nodeById[candidate.to_component_id];
                return targetNode && CABLE_COMPONENTS.has(targetNode.component_type);
            });
        const index = outgoing.findIndex(function (candidate) {
            return getEdgeKey(candidate) === getEdgeKey(edge);
        });
        const slots = getJbOutgoingSlotOffsets(sourceNode, context);
        return index >= 0 && slots[index] !== undefined ? slots[index] : 0;
    }

    function getJbOutgoingCableIndex(edge, sourceNode, context) {
        if (!sourceNode || sourceNode.component_type !== 'JB3PH' || !context || !context.outgoingBySource) {
            return { index: -1, count: 0 };
        }
        const outgoing = sortOutgoingEdges(context.outgoingBySource[sourceNode.component_id] || [], context.nodeById)
            .filter(function (candidate) {
                const targetNode = context.nodeById[candidate.to_component_id];
                return targetNode && CABLE_COMPONENTS.has(targetNode.component_type);
            });
        return {
            index: outgoing.findIndex(function (candidate) {
                return getEdgeKey(candidate) === getEdgeKey(edge);
            }),
            count: outgoing.length,
        };
    }

    function getSchematicSymbolAttrs(node, style, context) {
        const width = style.width;
        const height = style.height;
        const centerY = height / 2;
        const stroke = style.stroke;
        const common = {
            body: {
                width: width,
                height: height,
                fill: 'transparent',
                stroke: 'transparent',
                cursor: 'pointer',
            },
            terminalPath: {
                d: '',
                fill: 'none',
                stroke: stroke,
                strokeWidth: 2,
                strokeLinecap: 'round',
                strokeLinejoin: 'round',
                pointerEvents: 'none',
            },
            symbolPath: {
                d: '',
                fill: 'none',
                stroke: stroke,
                strokeWidth: 2.2,
                strokeLinecap: 'round',
                strokeLinejoin: 'round',
                pointerEvents: 'none',
            },
            symbolRing: {
                cx: width / 2,
                cy: centerY,
                r: 0,
                fill: '#ffffff',
                stroke: stroke,
                strokeWidth: 2,
                pointerEvents: 'none',
            },
            dot1: { r: 0, fill: stroke, pointerEvents: 'none' },
            dot2: { r: 0, fill: stroke, pointerEvents: 'none' },
            dot3: { r: 0, fill: stroke, pointerEvents: 'none' },
            tagLabel: {
                text: node.display_tag || node.component_type,
                x: width / 2,
                y: 8,
                fill: '#17324d',
                fontSize: SLD_LABEL_FONT_SIZE,
                fontWeight: SLD_LABEL_FONT_WEIGHT,
                textAnchor: 'middle',
                textVerticalAnchor: 'middle',
                pointerEvents: 'none',
            },
            bodyLabel: {
                text: formatNodeBody(node),
                x: width / 2,
                y: height - 6,
                fill: '#17324d',
                fontSize: SLD_LABEL_FONT_SIZE,
                fontWeight: SLD_LABEL_FONT_WEIGHT,
                textAnchor: 'middle',
                textVerticalAnchor: 'middle',
                pointerEvents: 'none',
            },
        };

        if (node.component_type === 'MCB') {
            const symbolX = width / 2;
            const point = function (rawX, rawY) { return mapInlineSvgSymbolPoint(rawX, rawY, symbolX, centerY, 0.86, 2.2); };
            common.tagLabel.text = formatNodeBody(node);
            common.bodyLabel.text = node.display_tag || 'MCB';
            const p = {
                top1: point(10, 0),
                top2: point(10, 15),
                crossA1: point(12, 13),
                crossA2: point(8, 17),
                crossB1: point(8, 13),
                crossB2: point(12, 17),
                bottom1: point(10, 50),
                bottom2: point(10, 35),
                blade1: point(10, 35),
                blade2: point(5, 15),
            };
            common.terminalPath.d = `M -2 ${centerY} L ${p.top1.x} ${p.top1.y} M ${p.bottom1.x} ${p.bottom1.y} L ${width + 2} ${centerY}`;
            common.symbolPath.d = [
                `M ${p.top1.x} ${p.top1.y} L ${p.top2.x} ${p.top2.y}`,
                `M ${p.crossA1.x} ${p.crossA1.y} L ${p.crossA2.x} ${p.crossA2.y}`,
                `M ${p.crossB1.x} ${p.crossB1.y} L ${p.crossB2.x} ${p.crossB2.y}`,
                `M ${p.bottom1.x} ${p.bottom1.y} L ${p.bottom2.x} ${p.bottom2.y}`,
                `M ${p.blade1.x} ${p.blade1.y} L ${p.blade2.x} ${p.blade2.y}`,
            ].join(' ');
            return common;
        }

        if (node.component_type === 'Isolator3PH' || node.component_type === 'Isolator1PH') {
            const symbolX = width / 2;
            const point = function (rawX, rawY) { return mapInlineSvgSymbolPoint(rawX, rawY, symbolX, centerY, 0.86, 2.2); };
            common.tagLabel.text = '';
            const p = {
                top1: point(10, 0),
                top2: point(10, 15),
                bottom1: point(10, 50),
                bottom2: point(10, 35),
                blade: point(5, 15),
                contact1: point(8, 15),
                contact2: point(12, 15),
            };
            common.terminalPath.d = `M -2 ${centerY} L ${p.top1.x} ${p.top1.y} M ${p.bottom1.x} ${p.bottom1.y} L ${width + 2} ${centerY}`;
            common.symbolPath.d = [
                `M ${p.top1.x} ${p.top1.y} L ${p.top2.x} ${p.top2.y}`,
                `M ${p.bottom1.x} ${p.bottom1.y} L ${p.bottom2.x} ${p.bottom2.y} L ${p.blade.x} ${p.blade.y}`,
                `M ${p.contact1.x} ${p.contact1.y} L ${p.contact2.x} ${p.contact2.y}`,
            ].join(' ');
            common.bodyLabel.text = node.component_type === 'Isolator3PH' ? '3PH Isolator' : '1PH Isolator';
            return common;
        }

        if (node.component_type === 'Tracer') {
            const leftLeadEnd = 28;
            const rightLeadStart = width - 28;
            const toothWidth = (rightLeadStart - leftLeadEnd) / 6;
            const topY = centerY - 9;
            const bottomY = centerY + 9;
            common.terminalPath.stroke = style.stroke;
            common.terminalPath.strokeWidth = 2.4;
            common.terminalPath.d = `M 0 ${centerY} L ${leftLeadEnd} ${centerY} M ${rightLeadStart} ${centerY} L ${width} ${centerY}`;
            common.symbolPath.stroke = style.stroke;
            common.symbolPath.strokeWidth = 3;
            common.symbolPath.d = [
                `M ${leftLeadEnd} ${centerY}`,
                `L ${leftLeadEnd + toothWidth} ${topY}`,
                `L ${leftLeadEnd + (toothWidth * 2)} ${bottomY}`,
                `L ${leftLeadEnd + (toothWidth * 3)} ${topY}`,
                `L ${leftLeadEnd + (toothWidth * 4)} ${bottomY}`,
                `L ${leftLeadEnd + (toothWidth * 5)} ${topY}`,
                `L ${rightLeadStart} ${centerY}`,
            ].join(' ');
            common.tagLabel.text = '';
            common.bodyLabel.text = '';
            return common;
        }

        if (node.component_type === 'JB3PH' || node.component_type === 'JB1PH') {
            const busX = Math.round(width * 0.36);
            common.terminalPath.d = `M -2 ${centerY} L ${busX} ${centerY}`;
            common.symbolPath.strokeWidth = 5;
            common.tagLabel.x = busX - 8;
            common.tagLabel.y = centerY - 17;
            common.tagLabel.fontSize = SLD_LABEL_FONT_SIZE;
            common.tagLabel.textAnchor = 'end';
            common.bodyLabel.x = busX + 8;
            common.bodyLabel.y = centerY + 22;
            common.bodyLabel.fontSize = SLD_LABEL_FONT_SIZE;
            common.bodyLabel.textAnchor = 'start';
            common.bodyLabel.text = node.component_type === 'JB3PH' ? '3PH JB' : '1PH JB';
            if (node.component_type === 'JB3PH') {
                const slots = getJbOutgoingSlotOffsets(node, context);
                const fullSlots = new Set(slots.map(function (offset) { return Math.round(offset); }));
                common.symbolPath.d = `M ${busX} ${centerY - 18} L ${busX} ${centerY + 18}`;
                [-12, 0, 12].forEach(function (offset) {
                    const y = centerY + offset;
                    const endX = fullSlots.has(offset) ? width + 2 : busX + Math.round((width - busX) * 0.5);
                    common.terminalPath.d += ` M ${busX} ${y} L ${endX} ${y}`;
                });
                slots.forEach(function (offset) {
                    if ([-12, 0, 12].includes(offset)) {
                        return;
                    }
                    const y = centerY + offset;
                    common.terminalPath.d += ` M ${busX} ${y} L ${width + 2} ${y}`;
                });
            } else {
                common.symbolPath.d = `M ${busX} ${centerY - 10} L ${busX} ${centerY + 10}`;
                common.terminalPath.d += ` M ${busX} ${centerY} L ${width + 2} ${centerY}`;
            }
        }

        return common;
    }

    function createSchematicSymbolElement(node, position, style, context) {
        const ElementClass = getSchematicSymbolElementClass();
        const element = new ElementClass();
        element.position(position.x, position.y - style.height / 2);
        element.resize(style.width, style.height);
        element.attr(getSchematicSymbolAttrs(node, style, context));
        element.prop('sldMeta', { componentId: node.component_id, node: node });
        return element;
    }

    function createComponentElement(node, position, context) {
        const style = getNodeStyle(node.component_type);

        if (node.component_type === 'EndTermination') {
            const square = new joint.shapes.standard.Rectangle();
            square.position(position.x, position.y - style.height / 2);
            square.resize(style.width, style.height);
            square.attr({
                body: {
                    fill: style.fill,
                    stroke: style.stroke,
                    strokeWidth: 2,
                    rx: 0,
                    ry: 0,
                },
                label: {
                    text: '',
                },
            });
            square.prop('sldMeta', { componentId: node.component_id, node: node });
            return square;
        }

        if (isSchematicSymbolComponent(node.component_type)) {
            return createSchematicSymbolElement(node, position, style, context);
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
                text: CABLE_COMPONENTS.has(node.component_type) ? '' : (isExternalDetailNode ? node.display_tag : `${node.display_tag}\n${formatNodeBody(node)}`),
                fill: '#17324d',
                fontSize: SLD_LABEL_FONT_SIZE,
                fontWeight: SLD_LABEL_FONT_WEIGHT,
                textVerticalAnchor: 'middle',
                textAnchor: 'middle',
            },
        });
        if (node.component_type === 'Tracer') {
            rectangle.attr('body/strokeDasharray', '6 4');
        }
        if (
            (node.component_type === 'Cable4C' || node.component_type === 'Cable3C')
            && ((node.metadata || {}).cable_override_active || (node.metadata || {}).manual_length_m || (node.metadata || {}).manual_cable_size)
        ) {
            rectangle.attr('body/stroke', '#d97706');
            rectangle.attr('body/strokeWidth', 2.6);
        }
        rectangle.prop('sldMeta', { componentId: node.component_id, node: node });
        return rectangle;
    }

    function createExternalDetailLabel(node, position) {
        const style = getNodeStyle(node.component_type);
        const metadata = node.metadata || {};
        const isCableOverride = (node.component_type === 'Cable4C' || node.component_type === 'Cable3C')
            && !!(metadata.cable_override_active || metadata.manual_length_m || metadata.manual_cable_size);
        const isCable = CABLE_COMPONENTS.has(node.component_type);
        const labelWidth = isCable ? 132 : style.width + 48;
        const label = new joint.shapes.standard.TextBlock();
        label.position(position.x - ((labelWidth - style.width) / 2), position.y + (style.height / 2) + 7);
        label.resize(labelWidth, isCable ? 36 : 24);
        label.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
            },
            label: {
                text: formatExternalDetail(node),
                fill: isCableOverride ? '#8a5b12' : '#486581',
                fontSize: SLD_LABEL_FONT_SIZE,
                fontWeight: SLD_LABEL_FONT_WEIGHT,
                textAnchor: 'middle',
                textVerticalAnchor: 'top',
                x: labelWidth / 2,
                y: 0,
            },
        });
        label.prop('sldMeta', { type: 'external-detail-label', ownerComponentId: node.component_id });
        return label;
    }

    function createEndTerminationLabel(node, position) {
        const label = new joint.shapes.standard.TextBlock();
        label.position(position.x + 28, position.y - 16);
        label.resize(120, 32);
        label.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
            },
            label: {
                text: `${node.display_tag}\nEnd Termination`,
                fill: '#17324d',
                fontSize: SLD_LABEL_FONT_SIZE,
                fontWeight: SLD_LABEL_FONT_WEIGHT,
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
        const startX = 240;
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

    function placeEditedTopology(payload, positions) {
        if (!payload.meta || !payload.meta.has_topology_edit) {
            return { positions: positions, lockedComponentIds: new Set() };
        }
        const nodeById = getNodeByComponentId(payload);
        const roots = (payload.nodes || []).filter(function (node) {
            return node.component_type === 'MCB';
        }).sort(compareNodesForLayout);
        if (!roots.length) {
            return { positions: positions, lockedComponentIds: new Set() };
        }
        const context = {
            positions: positions,
            nodeById: nodeById,
            outgoingBySource: buildOutgoingEdgesBySource(payload),
            lockedComponentIds: new Set(),
            startX: 240,
            startY: 98,
            rowGap: 124,
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
        let maxY = 220;
        payload.nodes.forEach(function (node) {
            const position = positions[node.component_id];
            if (!position) {
                return;
            }
            const style = getNodeStyle(node.component_type);
            maxX = Math.max(maxX, position.x + style.width + 180);
            maxY = Math.max(maxY, position.y + style.height + 44);
        });
        return {
            width: Math.max(1400, maxX),
            height: Math.max(240, maxY),
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

    function getAnchorYOffset(edge, sourceNode, role, context) {
        if (role === 'source') {
            return getJbOutgoingSlotOffset(edge, sourceNode, context);
        }
        return 0;
    }

    function getLinkPortPoint(cell, edge, node, role, context) {
        const position = cell.position();
        const size = cell.size();
        const overlap = node && (isSchematicSymbolComponent(node.component_type) && node.component_type !== 'Tracer')
            ? POWER_LINK_OVERLAP
            : 0;
        return {
            x: role === 'source' ? position.x + size.width - overlap : position.x + overlap,
            y: position.y + (size.height / 2) + getAnchorYOffset(edge, node, role, context),
        };
    }

    function getCellAnchorY(cell, edge, node, role, context) {
        return getLinkPortPoint(cell, edge, node, role, context).y;
    }

    function buildLinkVertices(sourceCell, targetCell, edge, sourceNode, targetNode, context) {
        const sourcePoint = getLinkPortPoint(sourceCell, edge, sourceNode, 'source', context);
        const targetPoint = getLinkPortPoint(targetCell, edge, targetNode, 'target', context);
        const sourceCenterY = sourcePoint.y;
        const targetCenterY = targetPoint.y;

        if (Math.abs(sourceCenterY - targetCenterY) <= 8) {
            return [];
        }

        const outgoing = getJbOutgoingCableIndex(edge, sourceNode, context);
        const isJbFanout = sourceNode
            && sourceNode.component_type === 'JB3PH'
            && targetNode
            && CABLE_COMPONENTS.has(targetNode.component_type)
            && outgoing.index >= 0
            && outgoing.count > 1;
        const branchX = isJbFanout
            ? Math.min(
                targetPoint.x - 26,
                sourcePoint.x + 34 + (outgoing.index * 44)
            )
            : Math.round((sourcePoint.x + targetPoint.x) / 2);
        return [
            { x: branchX, y: sourceCenterY },
            { x: branchX, y: targetCenterY },
        ];
    }

    function createDiagramLink(edge, sourceCell, targetCell, sourceNode, targetNode, context) {
        const link = new joint.shapes.standard.Link();

        link.source(getLinkPortPoint(sourceCell, edge, sourceNode, 'source', context));
        link.target(getLinkPortPoint(targetCell, edge, targetNode, 'target', context));
        link.attr({
            line: {
                stroke: '#1f3447',
                strokeWidth: 2,
                targetMarker: null,
                sourceMarker: null,
                pointerEvents: 'stroke',
                cursor: 'pointer',
            },
        });
        link.connector('rounded', { radius: 8 });
        link.vertices(buildLinkVertices(sourceCell, targetCell, edge, sourceNode, targetNode, context));

        link.prop('sldMeta', {
            edge: edge,
            sourceNode: sourceNode,
            targetNode: targetNode,
        });
        return link;
    }

    function applySchematicElementStyle(element, node, options) {
        const style = getNodeStyle(node.component_type);
        const isMuted = !!options.isMuted;
        const isPath = !!options.isPath;
        const isSelected = !!options.isSelected;
        const stroke = isSelected ? '#c05621' : (isPath ? '#2f6c43' : style.stroke);
        const opacity = isMuted ? 0.22 : 1;
        const strokeWidth = isSelected ? 3 : (isPath ? 2.6 : 2.1);
        let symbolStrokeWidth = strokeWidth;
        if (node.component_type === 'JB3PH' || node.component_type === 'JB1PH') {
            symbolStrokeWidth = 5;
        } else if (node.component_type === 'Tracer') {
            symbolStrokeWidth = isSelected ? 3.4 : 3;
        }
        const terminalStrokeWidth = node.component_type === 'Tracer' ? 2.4 : strokeWidth;
        const ringFill = isSelected ? '#fff1e6' : '#ffffff';
        const textFill = isMuted ? '#829ab1' : '#17324d';

        element.attr({
            body: {
                fill: 'transparent',
                stroke: 'transparent',
                opacity: 1,
            },
            terminalPath: {
                stroke: stroke,
                strokeWidth: terminalStrokeWidth,
                opacity: opacity,
            },
            symbolPath: {
                stroke: stroke,
                strokeWidth: symbolStrokeWidth,
                opacity: opacity,
            },
            symbolRing: {
                fill: ringFill,
                stroke: stroke,
                strokeWidth: strokeWidth,
                opacity: opacity,
            },
            dot1: {
                fill: stroke,
                opacity: opacity,
            },
            dot2: {
                fill: stroke,
                opacity: opacity,
            },
            dot3: {
                fill: stroke,
                opacity: opacity,
            },
            tagLabel: {
                fill: textFill,
                opacity: opacity,
            },
            bodyLabel: {
                fill: textFill,
                opacity: opacity,
            },
        });
    }

    function applyDefaultElementStyle(element) {
        const meta = element.prop('sldMeta') || {};
        const node = meta.node;
        if (!node) {
            return;
        }
        const style = getNodeStyle(node.component_type);
        if (isSchematicSymbolComponent(node.component_type)) {
            applySchematicElementStyle(element, node, {});
            return;
        }
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
        if (isSchematicSymbolComponent(node.component_type)) {
            applySchematicElementStyle(element, node, { isMuted: true });
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
        if (isSchematicSymbolComponent(node.component_type)) {
            applySchematicElementStyle(element, node, { isPath: true, isSelected: isSelected });
            return;
        }
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
                cursor: 'pointer',
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
                cursor: 'pointer',
            },
        });
    }

    function applySelectedLinkStyle(link) {
        link.attr({
            line: {
                stroke: '#0d6efd',
                strokeWidth: 3.8,
                opacity: 1,
                cursor: 'pointer',
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

    function getCableEditorContainer(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-cable-editor') : null;
    }

    function getCombineSummaryContainer(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-combine-summary') : null;
    }

    function getTopologyMode(state) {
        if (!state) {
            return '';
        }
        if (state.downstreamJbMode) {
            return 'downstream_jb';
        }
        if (state.attachJbMode) {
            return 'attach_to_jb';
        }
        if (state.splitMode) {
            return 'split';
        }
        if (state.combineMode) {
            return 'combine';
        }
        return '';
    }

    function getDownstreamLengthInput(root) {
        const panel = root.closest('.sld-panel');
        return panel ? panel.querySelector('#sld-downstream-jb-length') : null;
    }

    function selectedDownstreamBranchCount(state) {
        return state && state.downstreamJbSelectionIds ? state.downstreamJbSelectionIds.size : 0;
    }

    function clearTopologyPreviewState(state) {
        if (!state) {
            return;
        }
        state.combinePreview = null;
        state.splitPreview = null;
        state.downstreamJbPreview = null;
        state.attachJbPreview = null;
        state.topologyPreviewStatus = 'idle';
        state.topologyPreviewError = '';
        state.topologyPreviewKey = '';
    }

    function directDownstreamJbChildIds(state) {
        if (!state || !state.downstreamJbParentId) {
            return new Set();
        }
        const edges = state.outgoingBySource[state.downstreamJbParentId] || [];
        return new Set(edges.map(function (edge) { return edge.to_component_id; }));
    }

    function selectedAttachCount(state) {
        return state && state.attachSourceId && state.attachTargetJbId ? 2 : 0;
    }

    function updateCombineControls(root) {
        const state = root.__sldState;
        const panel = root.closest('.sld-panel');
        const combineButton = panel ? panel.querySelector('#sld-combine-mode') : null;
        const splitButton = panel ? panel.querySelector('#sld-split-mode') : null;
        const downstreamButton = panel ? panel.querySelector('#sld-downstream-jb-mode') : null;
        const attachButton = panel ? panel.querySelector('#sld-attach-jb-mode') : null;
        const downstreamLengthGroup = panel ? panel.querySelector('#sld-downstream-jb-length-group') : null;
        const applyButton = panel ? panel.querySelector('#sld-combine-apply') : null;
        const summary = getCombineSummaryContainer(root);
        const mode = getTopologyMode(state);
        const isSplit = mode === 'split';
        const isDownstreamJb = mode === 'downstream_jb';
        const isAttachJb = mode === 'attach_to_jb';
        const selectedSet = isDownstreamJb ? state.downstreamJbSelectionIds : (isSplit ? state.splitSelectionIds : state.combineSelectionIds);
        const selectedCount = isAttachJb ? selectedAttachCount(state) : (selectedSet ? selectedSet.size : 0);
        const preview = isAttachJb ? state.attachJbPreview : (isDownstreamJb ? state.downstreamJbPreview : (isSplit ? state.splitPreview : state.combinePreview));
        const minimumSelection = isSplit ? 1 : 2;

        if (combineButton) {
            combineButton.classList.toggle('active', !!(state && state.combineMode));
        }
        if (splitButton) {
            splitButton.classList.toggle('active', isSplit);
        }
        if (downstreamButton) {
            downstreamButton.classList.toggle('active', isDownstreamJb);
        }
        if (attachButton) {
            attachButton.classList.toggle('active', isAttachJb);
        }
        if (downstreamLengthGroup) {
            downstreamLengthGroup.classList.toggle('d-none', !isDownstreamJb);
        }
        if (applyButton) {
            applyButton.disabled = !(preview && preview.ok);
            applyButton.textContent = isAttachJb
                ? 'Apply Attach'
                : (isDownstreamJb
                ? 'Apply Downstream JB'
                : (isSplit ? 'Apply Split' : (mode === 'combine' ? 'Apply Combine' : 'Apply Edit')));
        }
        if (summary && state) {
            if (!mode) {
                summary.textContent = 'Select Combine, Split, Add JB, or Attach to start a topology edit.';
            } else if (isDownstreamJb && !state.downstreamJbParentId) {
                summary.textContent = 'Select the upstream 3PH JB, then select outgoing branches to move under a new downstream 3PH JB.';
            } else if (isAttachJb && !state.attachSourceId) {
                summary.textContent = 'Select an MCB-fed circuit or downstream branch to feed from another 3PH JB.';
            } else if (isAttachJb && !state.attachTargetJbId) {
                summary.textContent = `Selected ${(state.nodeByComponentId[state.attachSourceId] || {}).display_tag || 'source'}. Select a target 3PH JB with spare outgoing capacity.`;
            } else if (selectedCount < minimumSelection) {
                summary.textContent = isDownstreamJb
                    ? `Selected parent ${(state.nodeByComponentId[state.downstreamJbParentId] || {}).display_tag || '3PH JB'}. Select at least two direct outgoing branches.`
                    : (isSplit
                    ? 'Select one MCB feeder source with multiple downstream circuits.'
                    : `Select at least ${minimumSelection} MCB feeder sources.`);
            } else if (state.topologyPreviewStatus === 'checking') {
                summary.textContent = 'Checking selected topology edit...';
            } else if (state.topologyPreviewError) {
                summary.innerHTML = `<span class="text-danger fw-semibold">Cannot apply:</span> ${escapeHtml(state.topologyPreviewError)}`;
            } else if (preview && preview.ok && isSplit) {
                summary.innerHTML = `Selected ${escapeHtml(preview.source_mcb_display_tag || 'MCB')}. Add ${escapeHtml((preview.added_display_tags || []).join(', ') || '-')}; remove ${escapeHtml((preview.removed_display_tags || []).join(', ') || '-')}; recommended MCB: <strong>${escapeHtml(preview.recommended_breaker_rating)}A</strong>.`;
            } else if (preview && preview.ok && isDownstreamJb) {
                summary.innerHTML = `Parent ${escapeHtml(preview.parent_display_tag || '3PH JB')}: ${escapeHtml(preview.parent_outgoing_before)} outgoing now, ${escapeHtml(preview.parent_outgoing_after)} after edit. Move ${escapeHtml(preview.downstream_outgoing_count)} branch(es) under ${escapeHtml((preview.added_display_tags || [])[1] || 'new JB')} with ${escapeHtml(preview.trunk_length_m)} m 4C trunk.`;
            } else if (preview && preview.ok && isAttachJb) {
                if (preview.edit_type === 'move_branch_to_jb') {
                    summary.innerHTML = `Move ${escapeHtml(preview.branch_root_display_tag || preview.source_display_tag || 'branch')} from ${escapeHtml(preview.source_jb_display_tag || 'source JB')} to ${escapeHtml(preview.target_jb_display_tag || 'target JB')}. Target outgoing: ${escapeHtml(preview.target_outgoing_before)} to ${escapeHtml(preview.target_outgoing_after)}.`;
                } else {
                    summary.innerHTML = `Feed ${escapeHtml(preview.source_display_tag || 'source')} from ${escapeHtml(preview.target_jb_display_tag || '3PH JB')}. Target outgoing: ${escapeHtml(preview.target_outgoing_before)} to ${escapeHtml(preview.target_outgoing_after)}. Recommended source MCB: <strong>${escapeHtml(preview.recommended_breaker_rating)}A</strong>.`;
                }
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

    function renderCableEditor(root, node) {
        const editor = getCableEditorContainer(root);
        if (!editor) {
            return;
        }
        if (!node || !(node.component_type === 'Cable4C' || node.component_type === 'Cable3C')) {
            editor.innerHTML = '';
            return;
        }
        const metadata = node.metadata || {};
        const generatedLength = metadata.generated_length_m || metadata.length_m || '';
        const manualLength = metadata.manual_length_m || '';
        const generatedSize = metadata.generated_cable_size || metadata.cable_size || '';
        const manualSize = metadata.manual_cable_size || '';
        const remarks = metadata.cable_override_remarks || '';
        const isCableOverride = !!(metadata.cable_override_active || metadata.manual_length_m || metadata.manual_cable_size);
        const statusText = isCableOverride
            ? 'Using user-entered cable values for this cable.'
            : 'Using generated project setup values for this cable.';
        const labelClass = isCableOverride ? 'form-label small mb-1 sld-cable-manual-label' : 'form-label small text-muted mb-1';
        editor.innerHTML = `
            <div class="border-top pt-3">
                <h6 class="mb-2">Cable Management</h6>
                <div class="small text-muted mb-2">Generated length: ${escapeHtml(generatedLength || '-')} m${generatedSize ? ` | Generated size: ${escapeHtml(generatedSize)}` : ''}</div>
                <div class="mb-2">
                    <label class="${labelClass}" for="sld-cable-length-input">Manual length (m)</label>
                    <input type="number" step="0.01" min="0" class="form-control form-control-sm" id="sld-cable-length-input" value="${escapeHtml(manualLength)}" placeholder="${escapeHtml(generatedLength || '')}">
                </div>
                <div class="mb-2">
                    <label class="${labelClass}" for="sld-cable-size-input">Manual cable size</label>
                    <input type="text" class="form-control form-control-sm" id="sld-cable-size-input" value="${escapeHtml(manualSize)}" placeholder="${escapeHtml(generatedSize || 'Pending cable sizing')}">
                </div>
                <textarea class="form-control form-control-sm mb-2" id="sld-cable-remarks-input" rows="2" placeholder="Optional reason / location note">${escapeHtml(remarks)}</textarea>
                <div class="d-flex gap-2">
                    <button type="button" class="btn btn-primary btn-sm" id="sld-cable-save">Save Cable</button>
                    <button type="button" class="btn btn-outline-secondary btn-sm" id="sld-cable-reset" ${metadata.cable_override_active ? '' : 'disabled'}>Reset</button>
                </div>
                <div class="small mt-2 ${isCableOverride ? 'sld-cable-manual-note' : 'text-muted'}">${statusText}</div>
            </div>
        `;
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
            renderCableEditor(root, null);
            return;
        }
        summary.innerHTML = `Selected <strong>${escapeHtml(node.display_tag || node.component_type)}</strong>. Highlighted path follows the directed source-to-component route in the current rendered graph.`;
        details.innerHTML = buildInspectorRows(node, pathNodeCount, pathLinkCount).map(function (row) {
            return `<dt>${escapeHtml(row[0])}</dt><dd>${escapeHtml(row[1])}</dd>`;
        }).join('');
        renderCableEditor(root, node);
    }

    function renderLinkInspector(root, edge, sourceNode, targetNode) {
        const summary = getSelectionSummaryContainer(root);
        const details = getInspectorDetailsContainer(root);
        if (!summary || !details) {
            return;
        }
        summary.innerHTML = `Selected link from <strong>${escapeHtml((sourceNode || {}).display_tag || 'source')}</strong> to <strong>${escapeHtml((targetNode || {}).display_tag || 'target')}</strong>.`;
        details.innerHTML = [
            ['From', (sourceNode || {}).display_tag || edge.from_component_id || '-'],
            ['To', (targetNode || {}).display_tag || edge.to_component_id || '-'],
            ['Line IDs', (edge.line_ids || []).join(', ') || '-'],
            ['Branch', edge.branch_index !== null && edge.branch_index !== undefined ? edge.branch_index : '-'],
            ['Circuit', edge.circuit_index !== null && edge.circuit_index !== undefined ? edge.circuit_index : '-'],
        ].map(function (row) {
            return `<dt>${escapeHtml(row[0])}</dt><dd>${escapeHtml(row[1])}</dd>`;
        }).join('');
        renderCableEditor(root, null);
    }

    function applyCombineSelectionStyle(state) {
        Object.keys(state.elementByComponentId).forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            const node = state.nodeByComponentId[componentId];
            if (!element || !node) {
                return;
            }
            if (
                state.combineSelectionIds.has(componentId)
                || state.splitSelectionIds.has(componentId)
                || state.downstreamJbParentId === componentId
                || state.downstreamJbSelectionIds.has(componentId)
                || state.attachSourceId === componentId
                || state.attachTargetJbId === componentId
            ) {
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
        if (!state || !node || node.component_type !== 'MCB') {
            return;
        }
        if (state.splitSelectionIds.has(componentId)) {
            state.splitSelectionIds.delete(componentId);
        } else {
            state.splitSelectionIds.clear();
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

    function toggleDownstreamJbSelection(root, componentId) {
        const state = root.__sldState;
        const node = state && state.nodeByComponentId[componentId];
        if (!state || !node) {
            return;
        }
        if (node.component_type === 'JB3PH') {
            if (state.downstreamJbParentId !== componentId) {
                state.downstreamJbParentId = componentId;
                state.downstreamJbSelectionIds.clear();
            }
        } else {
            const validChildIds = directDownstreamJbChildIds(state);
            if (!state.downstreamJbParentId) {
                state.topologyPreviewError = 'Select the upstream 3PH JB before selecting branches.';
                updateCombineControls(root);
                return;
            }
            if (!validChildIds.has(componentId)) {
                state.topologyPreviewError = 'Select direct outgoing branch components from the selected 3PH JB.';
                updateCombineControls(root);
                return;
            }
            if (state.downstreamJbSelectionIds.has(componentId)) {
                state.downstreamJbSelectionIds.delete(componentId);
            } else {
                state.downstreamJbSelectionIds.add(componentId);
            }
        }
        clearTopologyPreviewState(state);
        applyCombineSelectionStyle(state);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    }

    function toggleAttachJbSelection(root, componentId) {
        const state = root.__sldState;
        const node = state && state.nodeByComponentId[componentId];
        if (!state || !node) {
            return;
        }
        if (node.component_type === 'MCB') {
            state.attachSourceId = componentId;
        } else if (node.component_type === 'JB3PH') {
            if (!state.attachSourceId) {
                state.topologyPreviewError = 'Select the circuit or branch before selecting a target 3PH JB.';
                updateCombineControls(root);
                return;
            }
            state.attachTargetJbId = componentId;
        } else {
            state.attachSourceId = componentId;
        }
        clearTopologyPreviewState(state);
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
            const sourceNode = state.nodeByComponentId[linkEntry.edge.from_component_id];
            const targetNode = state.nodeByComponentId[linkEntry.edge.to_component_id];
            const renderContext = {
                outgoingBySource: state.outgoingBySource || {},
                nodeById: state.nodeByComponentId || {},
            };

            linkEntry.link.source(getLinkPortPoint(sourceCell, linkEntry.edge, sourceNode, 'source', renderContext));
            linkEntry.link.target(getLinkPortPoint(targetCell, linkEntry.edge, targetNode, 'target', renderContext));
            linkEntry.link.vertices(buildLinkVertices(sourceCell, targetCell, linkEntry.edge, sourceNode, targetNode, renderContext));
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
        state.selectedEdgeKey = null;

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

    function highlightLinkSelection(root, edgeKey) {
        const state = root.__sldState;
        const entry = state && state.linkByEdgeKey[edgeKey];
        if (!state || !entry) {
            return;
        }
        state.selectedComponentId = null;
        state.selectedEdgeKey = edgeKey;
        Object.keys(state.elementByComponentId).forEach(function (id) {
            applyMutedElementStyle(state.elementByComponentId[id]);
        });
        [entry.edge.from_component_id, entry.edge.to_component_id].forEach(function (componentId) {
            const element = state.elementByComponentId[componentId];
            if (element) {
                applyPathElementStyle(element, false);
            }
        });
        Object.keys(state.linkByEdgeKey).forEach(function (key) {
            if (key === edgeKey) {
                applySelectedLinkStyle(state.linkByEdgeKey[key].link);
            } else {
                applyMutedLinkStyle(state.linkByEdgeKey[key].link);
            }
        });
        setFitSelectedLineState(root, false);
        renderLinkInspector(
            root,
            entry.edge,
            state.nodeByComponentId[entry.edge.from_component_id],
            state.nodeByComponentId[entry.edge.to_component_id]
        );
    }

    function zoomPaper(root, scaleFactor) {
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const nextScale = Math.max(0.35, Math.min(1.8, Number((state.scale * scaleFactor).toFixed(3))));
        state.scale = nextScale;
        state.paper.scale(nextScale, nextScale);
        resizePaperToScaledContent(root);
    }

    function resizePaperToScaledContent(root) {
        const state = root.__sldState;
        if (!state || !state.paper || !state.graph) {
            return;
        }
        const elements = state.graph.getElements();
        if (!elements.length) {
            return;
        }
        const area = state.graph.getBBox(elements);
        if (!area || !area.width || !area.height) {
            return;
        }
        const scale = state.scale || 1;
        const width = Math.max(root.clientWidth || 1200, Math.ceil((area.x + area.width) * scale + 96));
        const height = Math.max(220, Math.ceil((area.y + area.height) * scale + 34));
        if (typeof state.paper.setDimensions === 'function') {
            state.paper.setDimensions(width, height);
        }
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
        resizePaperToScaledContent(root);
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

    function hideSldContextMenu() {
        const existing = document.querySelector('.sld-context-menu');
        if (existing) {
            existing.remove();
        }
    }

    function showSldContextMenu(root, event, componentId, edgeKey) {
        hideSldContextMenu();
        const state = root.__sldState;
        if (!state) {
            return;
        }
        const node = componentId ? state.nodeByComponentId[componentId] : null;
        const edgeEntry = edgeKey ? state.linkByEdgeKey[edgeKey] : null;
        const menu = document.createElement('div');
        menu.className = 'sld-context-menu';
        const mode = getTopologyMode(state);
        const activePreview = mode === 'downstream_jb'
            ? state.downstreamJbPreview
            : (mode === 'attach_to_jb'
                ? state.attachJbPreview
                : (state.splitMode ? state.splitPreview : state.combinePreview));
        const applyAction = activePreview && activePreview.ok
            ? `<button type="button" data-sld-context-action="apply-edit">${mode === 'attach_to_jb' ? 'Apply Attach' : (mode === 'downstream_jb' ? 'Apply Downstream JB' : (state.splitMode ? 'Apply Split' : 'Apply Combine'))}</button>`
            : '';
        const isDirectDownstreamBranch = componentId && directDownstreamJbChildIds(state).has(componentId);
        menu.innerHTML = edgeEntry ? `
            <button type="button" data-sld-context-action="inspect-link">Inspect Link</button>
            <button type="button" data-sld-context-action="attach-link-source">Feed Downstream From JB</button>
            ${applyAction}
            <button type="button" data-sld-context-action="clear">Clear Selection</button>
        ` : (node ? `
            <button type="button" data-sld-context-action="inspect">Inspect ${escapeHtml(node.display_tag || 'Component')}</button>
            <button type="button" data-sld-context-action="fit-line">Fit Line</button>
            ${node.component_type === 'MCB' ? '<button type="button" data-sld-context-action="combine">Select for Combine</button>' : ''}
            ${node.component_type === 'MCB' ? '<button type="button" data-sld-context-action="split">Select for Split</button>' : ''}
            ${node.component_type !== 'JB3PH' ? '<button type="button" data-sld-context-action="attach-source">Feed This From JB</button>' : ''}
            ${node.component_type === 'JB3PH' ? '<button type="button" data-sld-context-action="downstream-parent">Use as Upstream 3PH JB</button>' : ''}
            ${node.component_type === 'JB3PH' ? '<button type="button" data-sld-context-action="attach-target">Use as Target JB</button>' : ''}
            ${isDirectDownstreamBranch ? '<button type="button" data-sld-context-action="downstream-branch">Move Branch Under New JB</button>' : ''}
            ${applyAction}
            <button type="button" data-sld-context-action="clear">Clear Selection</button>
        ` : `
            <button type="button" data-sld-context-action="fit-all">Fit All</button>
            ${applyAction}
            <button type="button" data-sld-context-action="clear">Clear Selection</button>
        `);
        menu.dataset.componentId = componentId || '';
        menu.dataset.edgeKey = edgeKey || '';
        document.body.appendChild(menu);
        const maxLeft = window.innerWidth - menu.offsetWidth - 8;
        const maxTop = window.innerHeight - menu.offsetHeight - 8;
        menu.style.left = `${Math.max(8, Math.min(event.clientX, maxLeft))}px`;
        menu.style.top = `${Math.max(8, Math.min(event.clientY, maxTop))}px`;
    }

    function handleSldContextAction(root, action, componentId, edgeKey) {
        if (!root || !root.__sldState) {
            return;
        }
        const edgeEntry = edgeKey ? root.__sldState.linkByEdgeKey[edgeKey] : null;
        if (action === 'inspect' && componentId) {
            highlightSelection(root, componentId);
        } else if (action === 'inspect-link' && edgeEntry) {
            highlightLinkSelection(root, edgeKey);
        } else if (action === 'fit-line' && componentId) {
            highlightSelection(root, componentId);
            fitSelectedLine(root);
        } else if (action === 'combine' && componentId) {
            root.__sldState.combineMode = true;
            root.__sldState.splitMode = false;
            root.__sldState.downstreamJbMode = false;
            root.__sldState.attachJbMode = false;
            if (!root.__sldState.combineSelectionIds.has(componentId)) {
                toggleCombineSelection(root, componentId);
            }
        } else if (action === 'split' && componentId) {
            root.__sldState.splitMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.downstreamJbMode = false;
            root.__sldState.attachJbMode = false;
            if (!root.__sldState.splitSelectionIds.has(componentId)) {
                toggleSplitSelection(root, componentId);
            }
        } else if (action === 'downstream-parent' && componentId) {
            root.__sldState.downstreamJbMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.splitMode = false;
            root.__sldState.attachJbMode = false;
            toggleDownstreamJbSelection(root, componentId);
        } else if (action === 'downstream-branch' && componentId) {
            root.__sldState.downstreamJbMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.splitMode = false;
            root.__sldState.attachJbMode = false;
            toggleDownstreamJbSelection(root, componentId);
        } else if (action === 'attach-source' && componentId) {
            root.__sldState.attachJbMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.splitMode = false;
            root.__sldState.downstreamJbMode = false;
            toggleAttachJbSelection(root, componentId);
        } else if (action === 'attach-target' && componentId) {
            root.__sldState.attachJbMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.splitMode = false;
            root.__sldState.downstreamJbMode = false;
            toggleAttachJbSelection(root, componentId);
        } else if (action === 'attach-link-source' && edgeEntry) {
            root.__sldState.attachJbMode = true;
            root.__sldState.combineMode = false;
            root.__sldState.splitMode = false;
            root.__sldState.downstreamJbMode = false;
            root.__sldState.attachSourceId = edgeEntry.edge.to_component_id;
            clearTopologyPreviewState(root.__sldState);
            highlightLinkSelection(root, edgeKey);
            updateCombineControls(root);
            scheduleTopologyPreview(root);
        } else if (action === 'fit-all') {
            fitPaperToContent(root);
        } else if (action === 'apply-edit') {
            applyCombineFeeders(root);
        } else if (action === 'clear') {
            highlightSelection(root, null);
        }
        updateCombineControls(root);
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

    function pageSizeValue(rawValue) {
        return rawValue === 'all' ? 'all' : Math.max(1, parseInt(rawValue || '10', 10) || 10);
    }

    function slicePayloadByLinePage(payload, page, pageSize) {
        const lineGroups = payload.line_groups || [];
        if (pageSize === 'all' || lineGroups.length <= pageSize) {
            return {
                payload: payload,
                page: 1,
                pageCount: 1,
                start: lineGroups.length ? 1 : 0,
                end: lineGroups.length,
                total: lineGroups.length,
            };
        }
        const pageCount = Math.max(1, Math.ceil(lineGroups.length / pageSize));
        const currentPage = Math.min(Math.max(1, page || 1), pageCount);
        const startIndex = (currentPage - 1) * pageSize;
        const selectedGroups = lineGroups.slice(startIndex, startIndex + pageSize);
        const selectedNodes = (payload.nodes || []).filter(function (node) {
            return selectedGroups.some(function (lineGroup) {
                return nodeBelongsToLineGroup(node, lineGroup);
            });
        });
        const componentIds = new Set(selectedNodes.map(function (node) { return node.component_id; }));
        const selectedEdges = (payload.edges || []).filter(function (edge) {
            return componentIds.has(edge.from_component_id) && componentIds.has(edge.to_component_id);
        });
        return {
            payload: {
                ...payload,
                nodes: selectedNodes,
                edges: selectedEdges,
                line_groups: selectedGroups,
                meta: {
                    ...(payload.meta || {}),
                    branch_count: selectedGroups.reduce(function (total, group) {
                        return total + (group.branch_indices || []).length;
                    }, 0),
                    node_count: selectedNodes.length,
                    edge_count: selectedEdges.length,
                    paginated: true,
                },
            },
            page: currentPage,
            pageCount: pageCount,
            start: selectedGroups.length ? startIndex + 1 : 0,
            end: startIndex + selectedGroups.length,
            total: lineGroups.length,
        };
    }

    function getSldPagerControls(root) {
        const panel = root.closest('.sld-panel');
        return {
            pageSize: panel ? panel.querySelector('#sld-lines-page-size') : null,
            previous: panel ? panel.querySelector('#sld-page-prev') : null,
            next: panel ? panel.querySelector('#sld-page-next') : null,
            status: panel ? panel.querySelector('#sld-page-status') : null,
        };
    }

    function updateSldPagerControls(root, pageInfo) {
        const controls = getSldPagerControls(root);
        if (controls.previous) {
            controls.previous.disabled = !pageInfo || pageInfo.page <= 1;
        }
        if (controls.next) {
            controls.next.disabled = !pageInfo || pageInfo.page >= pageInfo.pageCount;
        }
        if (controls.status) {
            controls.status.textContent = pageInfo
                ? `Lines ${pageInfo.start}-${pageInfo.end} of ${pageInfo.total}`
                : 'Lines 0-0 of 0';
        }
    }

    function renderCurrentSldPage(root) {
        const pager = root.__sldPager;
        if (!pager || !pager.payload) {
            return;
        }
        const pageInfo = slicePayloadByLinePage(pager.payload, pager.page, pager.pageSize);
        pager.page = pageInfo.page;
        renderSldGraph(root, pageInfo.payload, pager.savedLayout);
        updateSldPagerControls(root, pageInfo);
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
            manualLayout = placeEditedTopology(payload, manualLayout.positions);
        } catch (error) {
            // Experimental edited-topology layout must never prevent SLD rendering.
            console.error('SLD edited-topology layout failed; falling back to generated layout.', error);
        }
        const savedPositions = (savedLayout && savedLayout.positions) || {};
        const canUseSavedLayout = savedLayoutMatchesActiveTopology(payload, savedPositions);
        const mergedPositions = canUseSavedLayout
            ? mergeSavedPositions(manualLayout.positions, savedPositions, new Set())
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
                return !!meta.componentId || !!meta.draggableGroup || !!meta.edge;
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
        const nodeByComponentId = getNodeByComponentId(payload);
        const renderContext = {
            outgoingBySource: buildOutgoingEdgesBySource(payload),
            nodeById: nodeByComponentId,
        };

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
            const element = createComponentElement(node, position, renderContext);
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
            const link = createDiagramLink(edge, sourceCell, targetCell, sourceNode, targetNode, renderContext);
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
            outgoingBySource: renderContext.outgoingBySource,
            outgoingByComponent: graphNavigation.outgoingByComponent,
            incomingCountByComponent: graphNavigation.incomingCountByComponent,
            isDirty: false,
            hasSavedLayout: !!(savedLayout && savedLayout.meta && savedLayout.meta.has_saved_layout),
            dirtyComponentIds: new Set(),
            selectedComponentId: null,
            selectedEdgeKey: null,
            combineMode: false,
            combineSelectionIds: new Set(),
            combinePreview: null,
            splitMode: false,
            splitSelectionIds: new Set(),
            splitPreview: null,
            downstreamJbMode: false,
            downstreamJbParentId: '',
            downstreamJbSelectionIds: new Set(),
            downstreamJbPreview: null,
            attachJbMode: false,
            attachSourceId: '',
            attachTargetJbId: '',
            attachJbPreview: null,
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
            hideSldContextMenu();
            if (root.__sldState && root.__sldState.combineMode) {
                toggleCombineSelection(root, meta.componentId);
                return;
            }
            if (root.__sldState && root.__sldState.splitMode) {
                toggleSplitSelection(root, meta.componentId);
                return;
            }
            if (root.__sldState && root.__sldState.downstreamJbMode) {
                toggleDownstreamJbSelection(root, meta.componentId);
                return;
            }
            if (root.__sldState && root.__sldState.attachJbMode) {
                toggleAttachJbSelection(root, meta.componentId);
                return;
            }
            highlightSelection(root, meta.componentId);
        });

        paper.on('link:pointerclick', function (linkView) {
            const meta = linkView.model.prop('sldMeta') || {};
            if (!meta.edge) {
                return;
            }
            hideSldContextMenu();
            const edgeKey = getEdgeKey(meta.edge);
            if (root.__sldState && root.__sldState.attachJbMode) {
                root.__sldState.attachSourceId = meta.edge.to_component_id;
                clearTopologyPreviewState(root.__sldState);
                highlightLinkSelection(root, edgeKey);
                updateCombineControls(root);
                scheduleTopologyPreview(root);
                return;
            }
            highlightLinkSelection(root, edgeKey);
        });

        paper.on('blank:pointerdown', function () {
            hideSldContextMenu();
            highlightSelection(root, null);
        });

        paper.on('cell:pointerup', function () {
            refreshDerivedGeometry(root);
        });

        paper.el.addEventListener('contextmenu', function (event) {
            event.preventDefault();
            const view = paper.findView(event.target);
            const meta = view && view.model ? (view.model.prop('sldMeta') || {}) : {};
            showSldContextMenu(root, event, meta.componentId || '', meta.edge ? getEdgeKey(meta.edge) : '');
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
                        const controls = getSldPagerControls(root);
                        root.__sldPager = {
                            payload: payload,
                            savedLayout: savedLayout,
                            pageSize: pageSizeValue(controls.pageSize ? controls.pageSize.value : '10'),
                            page: 1,
                        };
                        renderCurrentSldPage(root);
                    })
                    .fail(function () {
                        const controls = getSldPagerControls(root);
                        root.__sldPager = {
                            payload: payload,
                            savedLayout: { positions: {}, meta: { saved_count: 0, has_saved_layout: false, save_mode: 'merge' } },
                            pageSize: pageSizeValue(controls.pageSize ? controls.pageSize.value : '10'),
                            page: 1,
                        };
                        renderCurrentSldPage(root);
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

    function postDownstreamJbRequest(root, url, includeRemarks) {
        const state = root.__sldState;
        if (!state || !url || !state.downstreamJbParentId || selectedDownstreamBranchCount(state) < 2) {
            return null;
        }
        const panel = root.closest('.sld-panel');
        const remarks = panel ? panel.querySelector('#sld-combine-remarks') : null;
        const lengthInput = getDownstreamLengthInput(root);
        const payload = {
            project_id: root.dataset.projectId,
            parent_component_id: state.downstreamJbParentId,
            branch_component_ids: Array.from(state.downstreamJbSelectionIds),
            trunk_length_m: lengthInput ? lengthInput.value : root.dataset.defaultJbLoopLength,
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

    function postAttachJbRequest(root, url, includeRemarks) {
        const state = root.__sldState;
        if (!state || !url || !state.attachSourceId || !state.attachTargetJbId) {
            return null;
        }
        const panel = root.closest('.sld-panel');
        const remarks = panel ? panel.querySelector('#sld-combine-remarks') : null;
        const payload = {
            project_id: root.dataset.projectId,
            source_component_id: state.attachSourceId,
            target_jb_component_id: state.attachTargetJbId,
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
        const mode = getTopologyMode(state);
        const isSplit = mode === 'split';
        const isDownstreamJb = mode === 'downstream_jb';
        const isAttachJb = mode === 'attach_to_jb';
        const url = isDownstreamJb
            ? root.dataset.sldTopologyDownstreamJbPreviewUrl
            : (isAttachJb
                ? root.dataset.sldTopologyAttachJbPreviewUrl
                : (isSplit ? root.dataset.sldTopologySplitPreviewUrl : root.dataset.sldTopologyCombinePreviewUrl));
        const selectedIds = isDownstreamJb ? state.downstreamJbSelectionIds : (isSplit ? state.splitSelectionIds : state.combineSelectionIds);
        const minimumSelection = isSplit ? 1 : 2;
        if (
            !mode
            || (!isAttachJb && selectedIds.size < minimumSelection)
            || (isDownstreamJb && !state.downstreamJbParentId)
            || (isAttachJb && (!state.attachSourceId || !state.attachTargetJbId))
        ) {
            state.topologyPreviewStatus = 'idle';
            state.topologyPreviewError = '';
            state.topologyPreviewKey = '';
            updateCombineControls(root);
            return;
        }
        const lengthInput = getDownstreamLengthInput(root);
        const lengthValue = isDownstreamJb && lengthInput ? lengthInput.value : '';
        const requestKey = isDownstreamJb
            ? `${mode}:${state.downstreamJbParentId}:${Array.from(selectedIds).sort().join('|')}:${lengthValue}`
            : (isAttachJb
                ? `${mode}:${state.attachSourceId}:${state.attachTargetJbId}`
                : `${mode}:${Array.from(selectedIds).sort().join('|')}`);
        state.topologyPreviewKey = requestKey;
        state.topologyPreviewStatus = 'checking';
        state.topologyPreviewError = '';
        updateCombineControls(root);
        const request = isDownstreamJb
            ? postDownstreamJbRequest(root, url, false)
            : (isAttachJb
                ? postAttachJbRequest(root, url, false)
                : postTopologyRequest(root, url, selectedIds, false));
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
            } else if (isDownstreamJb) {
                root.__sldState.downstreamJbPreview = preview;
            } else if (isAttachJb) {
                root.__sldState.attachJbPreview = preview;
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
            } else if (isDownstreamJb) {
                root.__sldState.downstreamJbPreview = null;
            } else if (isAttachJb) {
                root.__sldState.attachJbPreview = null;
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
        const mode = getTopologyMode(state);
        const isSplit = mode === 'split';
        const isDownstreamJb = mode === 'downstream_jb';
        const isAttachJb = mode === 'attach_to_jb';
        const url = isDownstreamJb
            ? root.dataset.sldTopologyDownstreamJbApplyUrl
            : (isAttachJb
                ? root.dataset.sldTopologyAttachJbApplyUrl
                : (isSplit ? root.dataset.sldTopologySplitApplyUrl : root.dataset.sldTopologyCombineApplyUrl));
        const selectedIds = isSplit ? state.splitSelectionIds : state.combineSelectionIds;
        const request = isDownstreamJb
            ? postDownstreamJbRequest(root, url, true)
            : (isAttachJb
                ? postAttachJbRequest(root, url, true)
                : postTopologyRequest(root, url, selectedIds, true));
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
            const anchor = panel.querySelector('.sld-header-alert-anchor');
            alert = document.createElement('div');
            alert.className = 'alert alert-warning alert-dismissible fade show py-2 mb-2 sld-topology-edit-alert';
            if (anchor) {
                anchor.appendChild(alert);
            }
        }
        if (alert) {
            const editType = topologyState.editType || 'manual';
            const warning = topologyState.warning || 'Review downstream BOQ and cable schedule outputs before issue.';
            alert.innerHTML = `
                <span>Active topology edit: <strong>${escapeHtml(editType)}</strong>. ${escapeHtml(warning)}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
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
                root.__sldState.downstreamJbMode = false;
                root.__sldState.attachJbMode = false;
                root.__sldState.combineSelectionIds.clear();
                root.__sldState.splitSelectionIds.clear();
                root.__sldState.downstreamJbParentId = '';
                root.__sldState.downstreamJbSelectionIds.clear();
                root.__sldState.attachSourceId = '';
                root.__sldState.attachTargetJbId = '';
                root.__sldState.combinePreview = null;
                root.__sldState.splitPreview = null;
                root.__sldState.downstreamJbPreview = null;
                root.__sldState.attachJbPreview = null;
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

    function saveCableOverride(root) {
        const state = root.__sldState;
        const componentId = state && state.selectedComponentId;
        const node = componentId ? state.nodeByComponentId[componentId] : null;
        const saveUrl = root.dataset.sldCableOverrideSaveUrl;
        if (!node || !(node.component_type === 'Cable4C' || node.component_type === 'Cable3C') || !saveUrl) {
            return;
        }
        const lengthInput = document.getElementById('sld-cable-length-input');
        const sizeInput = document.getElementById('sld-cable-size-input');
        const remarksInput = document.getElementById('sld-cable-remarks-input');
        $.ajax({
            url: saveUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify({
                project_id: root.dataset.projectId,
                component_id: componentId,
                manual_length_m: lengthInput ? lengthInput.value : '',
                manual_cable_size: sizeInput ? sizeInput.value : '',
                remarks: remarksInput ? remarksInput.value : '',
            }),
        }).done(function (response) {
            if (typeof window.showToast === 'function') {
                window.showToast(response.success || 'Cable override saved.', 'success');
            }
            fetchAndRenderSld(root);
        }).fail(function (xhr) {
            if (typeof window.showToast === 'function') {
                window.showToast((xhr.responseJSON && xhr.responseJSON.error) || 'Unable to save cable override.', 'error');
            }
        });
    }

    function resetCableOverride(root) {
        const state = root.__sldState;
        const componentId = state && state.selectedComponentId;
        const resetUrl = root.dataset.sldCableOverrideResetUrl;
        if (!componentId || !resetUrl) {
            return;
        }
        $.ajax({
            url: resetUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getSldCsrfToken() },
            contentType: 'application/json',
            data: JSON.stringify({
                project_id: root.dataset.projectId,
                component_id: componentId,
            }),
        }).done(function (response) {
            if (typeof window.showToast === 'function') {
                window.showToast(response.success || 'Cable override reset.', 'info');
            }
            fetchAndRenderSld(root);
        }).fail(function (xhr) {
            if (typeof window.showToast === 'function') {
                window.showToast((xhr.responseJSON && xhr.responseJSON.error) || 'Unable to reset cable override.', 'error');
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
        root.__sldState.downstreamJbMode = false;
        root.__sldState.attachJbMode = false;
        clearTopologyPreviewState(root.__sldState);
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
        root.__sldState.downstreamJbMode = false;
        root.__sldState.attachJbMode = false;
        clearTopologyPreviewState(root.__sldState);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    });

    $(document).on('click', '#sld-downstream-jb-mode', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldState) {
            return;
        }
        root.__sldState.downstreamJbMode = !root.__sldState.downstreamJbMode;
        root.__sldState.combineMode = false;
        root.__sldState.splitMode = false;
        root.__sldState.attachJbMode = false;
        clearTopologyPreviewState(root.__sldState);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    });

    $(document).on('click', '#sld-attach-jb-mode', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldState) {
            return;
        }
        root.__sldState.attachJbMode = !root.__sldState.attachJbMode;
        root.__sldState.combineMode = false;
        root.__sldState.splitMode = false;
        root.__sldState.downstreamJbMode = false;
        clearTopologyPreviewState(root.__sldState);
        updateCombineControls(root);
        scheduleTopologyPreview(root);
    });

    $(document).on('input change', '#sld-downstream-jb-length', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldState) {
            return;
        }
        clearTopologyPreviewState(root.__sldState);
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

    $(document).on('click', '#sld-cable-save', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (root) {
            saveCableOverride(root);
        }
    });

    $(document).on('click', '#sld-cable-reset', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (root) {
            resetCableOverride(root);
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

    $(document).on('change', '#sld-lines-page-size', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldPager) {
            return;
        }
        root.__sldPager.pageSize = pageSizeValue(this.value);
        root.__sldPager.page = 1;
        renderCurrentSldPage(root);
    });

    $(document).on('click', '#sld-page-prev', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldPager) {
            return;
        }
        root.__sldPager.page = Math.max(1, root.__sldPager.page - 1);
        renderCurrentSldPage(root);
    });

    $(document).on('click', '#sld-page-next', function () {
        const root = document.getElementById('sld-diagram-shell');
        if (!root || !root.__sldPager) {
            return;
        }
        root.__sldPager.page += 1;
        renderCurrentSldPage(root);
    });

    $(document).on('click', '.sld-context-menu button', function () {
        const menu = this.closest('.sld-context-menu');
        const root = document.getElementById('sld-diagram-shell');
        const action = this.dataset.sldContextAction;
        const componentId = menu ? menu.dataset.componentId : '';
        const edgeKey = menu ? menu.dataset.edgeKey : '';
        hideSldContextMenu();
        handleSldContextAction(root, action, componentId, edgeKey);
    });

    $(document).on('click', function (event) {
        if (!event.target.closest('.sld-context-menu')) {
            hideSldContextMenu();
        }
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
