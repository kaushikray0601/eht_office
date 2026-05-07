from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


COMPONENT_ORDER = {
    'MCB': 0,
    'Cable4C': 1,
    'Isolator3PH': 2,
    'JB3PH': 3,
    'Isolator1PH': 4,
    'Cable3C': 5,
    'JB1PH': 6,
    'Tracer': 7,
    'EndTermination': 8,
}
SCHEMATIC_WIDTHS = {
    'MCB': 86,
    'Cable4C': 58,
    'Cable3C': 58,
    'Isolator3PH': 74,
    'Isolator1PH': 74,
    'JB3PH': 78,
    'JB1PH': 62,
    'Tracer': 96,
    'EndTermination': 18,
}
POWER_COLOR = colors.HexColor('#17324d')
TRACER_COLOR = colors.HexColor('#c2410c')
MUTED_COLOR = colors.HexColor('#5b748b')
PAGE_WARNING_COLOR = colors.HexColor('#9a3412')


def _line_values(item):
    return {value for value in item.get('line_ids', []) if value}


def _node_matches_line_group(node, group):
    line_uid = group.get('line_uid')
    line_ids = _line_values(node)
    if line_uid and node.get('line_uid'):
        if str(node.get('line_uid')) == str(line_uid):
            return True
        return group.get('line_id') in line_ids
    return group.get('line_id') in line_ids


def _edge_lookup(payload):
    incoming = {}
    outgoing = {}
    for edge in payload.get('edges', []):
        incoming.setdefault(edge.get('to_component_id'), []).append(edge)
        outgoing.setdefault(edge.get('from_component_id'), []).append(edge)
    return incoming, outgoing


def _node_lookup(payload):
    return {node.get('component_id'): node for node in payload.get('nodes', [])}


def _node_sort_key(node):
    return (
        str(node.get('line_id') or ''),
        str(node.get('line_uid') or ''),
        node.get('branch_index') or 0,
        -1 if node.get('circuit_index') is None else node.get('circuit_index'),
        COMPONENT_ORDER.get(node.get('component_type'), 99),
        str(node.get('display_tag') or ''),
    )


def _edge_target_sort_key(edge, node_by_id):
    return _node_sort_key(node_by_id.get(edge.get('to_component_id'), {}))


def _component_width(node):
    return SCHEMATIC_WIDTHS.get(node.get('component_type'), 62)


def _inline_symbol_point(raw_x, raw_y, center_x, center_y, length_scale=0.86, width_scale=1.7):
    return (
        center_x + ((raw_y - 25) * length_scale),
        center_y - ((raw_x - 10) * width_scale),
    )


def _short_text(value, max_chars=24):
    value = str(value or '')
    return value if len(value) <= max_chars else f'{value[:max_chars - 3]}...'


def _draw_text(pdf, text, x, y, size=7, color=POWER_COLOR, bold=False, align='center'):
    pdf.setFillColor(color)
    pdf.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
    if align == 'left':
        pdf.drawString(x, y, _short_text(text, 36))
    elif align == 'right':
        pdf.drawRightString(x, y, _short_text(text, 36))
    else:
        pdf.drawCentredString(x, y, _short_text(text, 32))


def _cable_label(node):
    metadata = node.get('metadata') or {}
    cable_size = metadata.get('manual_cable_size') or metadata.get('cable_size') or node.get('display_name') or ''
    length = metadata.get('manual_length_m') or metadata.get('length_m')
    parts = [node.get('display_tag') or 'Cable']
    if cable_size:
        parts.append(str(cable_size))
    if length:
        parts.append(f'{length:g} m' if isinstance(length, float) else f'{length} m')
    return ' '.join(parts)


def _body_label(node):
    metadata = node.get('metadata') or {}
    component_type = node.get('component_type')
    if component_type == 'MCB' and metadata.get('breaker_size'):
        return f"{metadata.get('breaker_size')}A MCB"
    if component_type == 'Isolator3PH':
        return '3PH Isolator'
    if component_type == 'Isolator1PH':
        return '1PH Isolator'
    if component_type == 'JB3PH':
        return '3PH JB'
    if component_type == 'JB1PH':
        return '1PH JB'
    if component_type == 'Tracer':
        return 'Heat Tracing Cable'
    if component_type == 'EndTermination':
        return 'End Termination'
    return node.get('display_name') or component_type or ''


def _draw_mcb(pdf, node, x, y, width):
    center_x = x + width / 2
    points = {
        'left_1': _inline_symbol_point(10, 0, center_x, y),
        'left_2': _inline_symbol_point(10, 15, center_x, y),
        'cross_a1': _inline_symbol_point(12, 13, center_x, y),
        'cross_a2': _inline_symbol_point(8, 17, center_x, y),
        'cross_b1': _inline_symbol_point(8, 13, center_x, y),
        'cross_b2': _inline_symbol_point(12, 17, center_x, y),
        'right_1': _inline_symbol_point(10, 50, center_x, y),
        'right_2': _inline_symbol_point(10, 35, center_x, y),
        'blade_2': _inline_symbol_point(5, 15, center_x, y),
    }
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setLineWidth(1.2)
    pdf.line(x, y, *points['left_1'])
    pdf.line(*points['right_1'], x + width, y)
    pdf.line(*points['left_1'], *points['left_2'])
    pdf.line(*points['cross_a1'], *points['cross_a2'])
    pdf.line(*points['cross_b1'], *points['cross_b2'])
    pdf.line(*points['right_1'], *points['right_2'])
    pdf.line(*points['right_2'], *points['blade_2'])
    _draw_text(pdf, _body_label(node), center_x, y + 16, size=7, bold=True)
    _draw_text(pdf, node.get('display_tag'), center_x, y - 17, size=7, bold=True)


def _draw_isolator(pdf, node, x, y, width):
    center_x = x + width / 2
    points = {
        'left_1': _inline_symbol_point(10, 0, center_x, y),
        'left_2': _inline_symbol_point(10, 15, center_x, y),
        'right_1': _inline_symbol_point(10, 50, center_x, y),
        'right_2': _inline_symbol_point(10, 35, center_x, y),
        'blade': _inline_symbol_point(5, 15, center_x, y),
        'contact_1': _inline_symbol_point(8, 15, center_x, y),
        'contact_2': _inline_symbol_point(12, 15, center_x, y),
    }
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setLineWidth(1.2)
    pdf.line(x, y, *points['left_1'])
    pdf.line(*points['right_1'], x + width, y)
    pdf.line(*points['left_1'], *points['left_2'])
    pdf.line(*points['right_1'], *points['right_2'])
    pdf.line(*points['right_2'], *points['blade'])
    pdf.line(*points['contact_1'], *points['contact_2'])
    _draw_text(pdf, _body_label(node), center_x, y - 17, size=7, bold=True)


def _draw_jb(pdf, node, x, y, width):
    bus_x = x + 22
    component_type = node.get('component_type')
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setLineCap(1)
    pdf.setLineWidth(1.2)
    pdf.line(x, y, bus_x, y)
    pdf.setLineWidth(4.2)
    if component_type == 'JB3PH':
        pdf.line(bus_x, y - 15, bus_x, y + 15)
        pdf.setLineWidth(1.2)
        for offset in (10, 0, -10):
            pdf.line(bus_x, y + offset, x + width, y + offset)
    else:
        pdf.line(bus_x, y - 9, bus_x, y + 9)
        pdf.setLineWidth(1.2)
        pdf.line(bus_x, y, x + width, y)
    _draw_text(pdf, node.get('display_tag'), bus_x - 3, y + 18, size=7, bold=True, align='right')
    _draw_text(pdf, _body_label(node), bus_x + 4, y - 22, size=7, bold=True, align='left')


def _draw_cable(pdf, node, x, y, width):
    body_x = x + 8
    body_w = width - 16
    pdf.setStrokeColor(colors.HexColor('#8a5b12'))
    pdf.setFillColor(colors.HexColor('#fff5df'))
    pdf.setLineWidth(1)
    pdf.line(x, y, body_x, y)
    pdf.line(body_x + body_w, y, x + width, y)
    pdf.roundRect(body_x, y - 5, body_w, 10, 1.8, stroke=1, fill=1)
    _draw_text(pdf, _cable_label(node), x + width / 2, y - 18, size=7)


def _draw_tracer(pdf, node, x, y, width):
    left = x + 20
    right = x + width - 20
    tooth = (right - left) / 6
    pdf.setStrokeColor(TRACER_COLOR)
    pdf.setLineWidth(1.8)
    pdf.line(x, y, left, y)
    pdf.line(right, y, x + width, y)
    points = [
        (left, y),
        (left + tooth, y + 9),
        (left + 2 * tooth, y - 9),
        (left + 3 * tooth, y + 9),
        (left + 4 * tooth, y - 9),
        (left + 5 * tooth, y + 9),
        (right, y),
    ]
    path = pdf.beginPath()
    path.moveTo(*points[0])
    for px, py in points[1:]:
        path.lineTo(px, py)
    pdf.drawPath(path, stroke=1, fill=0)
    _draw_text(pdf, node.get('display_tag'), x + width / 2, y + 15, size=7, color=TRACER_COLOR)
    _draw_text(pdf, _body_label(node), x + width / 2, y - 18, size=7)


def _draw_end(pdf, node, x, y, width):
    side = 8
    pdf.setFillColor(POWER_COLOR)
    pdf.setStrokeColor(POWER_COLOR)
    pdf.rect(x + width / 2 - side / 2, y - side / 2, side, side, stroke=1, fill=1)
    _draw_text(pdf, node.get('display_tag'), x + width + 4, y + 3, size=7, align='left')
    _draw_text(pdf, _body_label(node), x + width + 4, y - 8, size=6, align='left')


def _draw_box(pdf, node, x, y, width):
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setFillColor(colors.HexColor('#f8fafc'))
    pdf.roundRect(x + 4, y - 12, width - 8, 24, 2, stroke=1, fill=1)
    _draw_text(pdf, node.get('display_tag'), x + width / 2, y + 2, size=7)
    _draw_text(pdf, _body_label(node), x + width / 2, y - 9, size=6)


def _draw_component(pdf, node, x, y):
    width = _component_width(node)
    component_type = node.get('component_type')
    if component_type == 'MCB':
        _draw_mcb(pdf, node, x, y, width)
    elif component_type in {'Isolator3PH', 'Isolator1PH'}:
        _draw_isolator(pdf, node, x, y, width)
    elif component_type in {'JB3PH', 'JB1PH'}:
        _draw_jb(pdf, node, x, y, width)
    elif component_type in {'Cable4C', 'Cable3C'}:
        _draw_cable(pdf, node, x, y, width)
    elif component_type == 'Tracer':
        _draw_tracer(pdf, node, x, y, width)
    elif component_type == 'EndTermination':
        _draw_end(pdf, node, x, y, width)
    else:
        _draw_box(pdf, node, x, y, width)
    return width


def _draw_link(pdf, x1, y1, x2, y2):
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setLineWidth(1.1)
    pdf.line(x1, y1, x2, y2)


def _draw_branch_link(pdf, anchor, x2, y2):
    _draw_link(pdf, anchor['source_right'], anchor['source_y'], x2, y2)


def _terminal_paths(payload):
    node_by_id = _node_lookup(payload)
    incoming_by_id, outgoing_by_id = _edge_lookup(payload)
    roots = sorted(
        [
            node for node in payload.get('nodes', [])
            if node.get('component_type') == 'MCB'
            and not incoming_by_id.get(node.get('component_id'))
        ],
        key=_node_sort_key,
    )
    if not roots:
        roots = sorted(
            [node for node in payload.get('nodes', []) if node.get('component_type') == 'MCB'],
            key=_node_sort_key,
        )

    paths = []

    def walk(node_id, path, visited):
        outgoing = [
            edge for edge in outgoing_by_id.get(node_id, [])
            if edge.get('to_component_id') in node_by_id
        ]
        if not outgoing:
            paths.append(path)
            return
        for edge in sorted(outgoing, key=lambda item: _edge_target_sort_key(item, node_by_id)):
            target_id = edge.get('to_component_id')
            if target_id in visited:
                paths.append(path)
                continue
            walk(target_id, [*path, node_by_id[target_id]], {*visited, target_id})

    for root in roots:
        walk(root.get('component_id'), [root], {root.get('component_id')})

    return sorted(paths, key=lambda path: [_node_sort_key(node) for node in path])


def _path_line_ids(path):
    line_ids = []
    for node in path:
        for line_id in node.get('line_ids') or ([node.get('line_id')] if node.get('line_id') else []):
            if line_id and line_id not in line_ids:
                line_ids.append(line_id)
    return line_ids


def _path_matches_group(path, group):
    return any(_node_matches_line_group(node, group) for node in path)


def _line_rows(payload, line_group):
    return [
        {
            'line_id': line_group.get('line_id'),
            'branch_index': path[-1].get('branch_index') or path[0].get('branch_index') or 0,
            'circuit_index': path[-1].get('circuit_index'),
            'upstream': [],
            'downstream': path,
            'path': path,
        }
        for path in _terminal_paths(payload)
        if _path_matches_group(path, line_group)
    ]


def _pdf_rows(payload):
    rows = []
    seen = set()
    for path in _terminal_paths(payload):
        key = tuple(node.get('component_id') for node in path)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            'line_ids': _path_line_ids(path),
            'branch_index': path[-1].get('branch_index') or path[0].get('branch_index') or 0,
            'path': path,
        })
    return rows


def _pdf_trees(payload):
    trees = []
    current = None
    for row in _pdf_rows(payload):
        root_id = row['path'][0].get('component_id') if row.get('path') else ''
        if not current or current['root_id'] != root_id:
            current = {
                'root_id': root_id,
                'line_ids': [],
                'paths': [],
            }
            trees.append(current)
        current['paths'].append(row['path'])
        for line_id in row.get('line_ids') or []:
            if line_id not in current['line_ids']:
                current['line_ids'].append(line_id)
    return trees


def _tree_layout(tree, gap=24, leaf_gap=72):
    paths = tree.get('paths') or []
    node_by_id = {}
    depth_by_id = {}
    path_leaf_y = {}
    leaf_ids = []
    for path_index, path in enumerate(paths):
        leaf_y = -path_index * leaf_gap
        path_leaf_y[path_index] = leaf_y
        if path:
            leaf_ids.append(path[-1].get('component_id'))
        for depth, node in enumerate(path):
            node_id = node.get('component_id')
            if not node_id:
                continue
            node_by_id[node_id] = node
            depth_by_id[node_id] = min(depth, depth_by_id.get(node_id, depth))

    max_depth = max(depth_by_id.values(), default=0)
    level_widths = {
        depth: max(
            [_component_width(node) for node_id, node in node_by_id.items() if depth_by_id[node_id] == depth] or [62]
        )
        for depth in range(max_depth + 1)
    }
    level_x = {0: 0}
    for depth in range(1, max_depth + 1):
        level_x[depth] = level_x[depth - 1] + level_widths[depth - 1] + gap

    node_leaf_ys = {node_id: [] for node_id in node_by_id}
    for path_index, path in enumerate(paths):
        for node in path:
            node_id = node.get('component_id')
            if node_id in node_leaf_ys:
                node_leaf_ys[node_id].append(path_leaf_y[path_index])

    positions = {}
    for node_id, node in node_by_id.items():
        values = node_leaf_ys.get(node_id) or [0]
        positions[node_id] = {
            'x': level_x[depth_by_id[node_id]],
            'y': (min(values) + max(values)) / 2,
            'node': node,
        }

    edges = []
    seen_edges = set()
    for path in paths:
        for source, target in zip(path, path[1:]):
            key = (source.get('component_id'), target.get('component_id'))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(key)

    width = 0
    height = max(1, len(paths)) * leaf_gap
    for item in positions.values():
        width = max(width, item['x'] + _component_width(item['node']) + 72)
    return {
        'positions': positions,
        'edges': edges,
        'width': width,
        'height': height,
        'leaf_ids': leaf_ids,
    }


def _start_page(pdf, project_id, page_width, page_height, margin, warning=''):
    pdf.setTitle(f'{project_id} Single Line Diagram')
    pdf.setFont('Helvetica-Bold', 13)
    pdf.setFillColor(POWER_COLOR)
    pdf.drawString(margin, page_height - margin + 4, f'{project_id} - Single Line Diagram')
    if warning:
        pdf.setFont('Helvetica', 7)
        pdf.setFillColor(PAGE_WARNING_COLOR)
        pdf.drawRightString(page_width - margin, page_height - margin + 4, warning[:150])
    pdf.setStrokeColor(colors.HexColor('#b7c7d6'))
    pdf.line(margin, page_height - margin - 6, page_width - margin, page_height - margin - 6)


def _draw_row_label(pdf, row, x, y):
    line_text = ', '.join(row['line_ids'][:3]) if row.get('line_ids') else 'Manual feeder'
    if len(row.get('line_ids') or []) > 3:
        line_text = f'{line_text}, ...'
    pdf.setFillColor(colors.HexColor('#edf4fb'))
    pdf.setStrokeColor(colors.HexColor('#c7d6e2'))
    pdf.roundRect(x, y - 12, 120, 24, 3, stroke=1, fill=1)
    _draw_text(pdf, f'Line: {line_text}', x + 60, y - 2, size=7, bold=True)
    _draw_text(pdf, f"B{row.get('branch_index') or 1}", x + 60, y - 28, size=6, color=MUTED_COLOR)


def _draw_tree_labels(pdf, tree, layout, x, origin_y, scale=1):
    for path in tree.get('paths') or []:
        if not path:
            continue
        leaf_id = path[-1].get('component_id')
        leaf_position = layout['positions'].get(leaf_id, {'y': 0})
        line_ids = _path_line_ids(path)
        label_row = {
            'line_ids': line_ids,
            'branch_index': path[-1].get('branch_index') or path[0].get('branch_index') or 1,
        }
        _draw_row_label(pdf, label_row, x, origin_y + leaf_position['y'] * scale)


def _jb3ph_outlet_offsets(count):
    if count <= 1:
        return [0]
    if count == 2:
        return [10, 0]
    if count == 3:
        return [10, 0, -10]
    step = 24 / (count - 1)
    return [12 - index * step for index in range(count)]


def _edge_source_offsets(edges, positions):
    offsets = {}
    by_source = {}
    for source_id, target_id in edges:
        by_source.setdefault(source_id, []).append((source_id, target_id))

    for source_id, source_edges in by_source.items():
        source_item = positions.get(source_id)
        if not source_item or source_item['node'].get('component_type') != 'JB3PH':
            continue
        ordered_edges = sorted(
            source_edges,
            key=lambda edge: positions.get(edge[1], {}).get('y', 0),
            reverse=True,
        )
        for edge, offset in zip(ordered_edges, _jb3ph_outlet_offsets(len(ordered_edges))):
            offsets[edge] = offset
    return offsets


def _draw_tree_edge(pdf, source_item, target_item, source_offset=0):
    source = source_item['node']
    x1 = source_item['x'] + _component_width(source)
    y1 = source_item['y'] + source_offset
    x2 = target_item['x']
    y2 = target_item['y']
    pdf.setStrokeColor(POWER_COLOR)
    pdf.setLineWidth(1.1)
    if abs(y1 - y2) < 0.1:
        pdf.line(x1, y1, x2, y2)
        return
    trunk_x = x1 + max(14, (x2 - x1) * 0.45)
    pdf.line(x1, y1, trunk_x, y1)
    pdf.line(trunk_x, y1, trunk_x, y2)
    pdf.line(trunk_x, y2, x2, y2)


def _draw_tree(pdf, tree, x, y, available_width):
    layout = _tree_layout(tree)
    scale = min(1, available_width / max(1, layout['width']))
    source_offsets = _edge_source_offsets(layout['edges'], layout['positions'])
    _draw_tree_labels(pdf, tree, layout, x, y, scale=scale)
    pdf.saveState()
    pdf.translate(x + 128, y)
    pdf.scale(scale, scale)

    for source_id, target_id in layout['edges']:
        source_item = layout['positions'].get(source_id)
        target_item = layout['positions'].get(target_id)
        if source_item and target_item:
            _draw_tree_edge(pdf, source_item, target_item, source_offsets.get((source_id, target_id), 0))

    for item in sorted(layout['positions'].values(), key=lambda pos: (pos['x'], -pos['y'])):
        _draw_component(pdf, item['node'], item['x'], item['y'])

    pdf.restoreState()
    return layout['height'] * scale


def build_sld_pdf(project_id, payload):
    buffer = BytesIO()
    page_size = landscape(A3)
    pdf = canvas.Canvas(buffer, pagesize=page_size)
    page_width, page_height = page_size
    margin = 12 * mm
    x_label = margin
    x_tree = margin
    y = page_height - margin - 44
    tree_gap = 24
    available_width = page_width - margin - x_label - 128 - 70
    meta = payload.get('meta') or {}
    export_warning = ''
    if meta.get('topology_edit_review_required') or meta.get('topology_baseline_changed'):
        export_warning = meta.get('manual_topology_warning') or 'Manual topology edit requires review before issue.'

    _start_page(pdf, project_id, page_width, page_height, margin, export_warning)
    trees = _pdf_trees(payload)
    for tree in trees:
        tree_layout = _tree_layout(tree)
        block_scale = min(1, available_width / max(1, tree_layout['width']))
        block_height = tree_layout['height'] * block_scale + 30
        if y - block_height < margin:
            pdf.showPage()
            _start_page(pdf, project_id, page_width, page_height, margin, export_warning)
            y = page_height - margin - 44

        rendered_height = _draw_tree(pdf, tree, x_tree, y, available_width)
        y -= rendered_height + tree_gap

    if not trees:
        pdf.setFont('Helvetica', 10)
        pdf.drawString(margin, y, 'No SLD line groups are available for export.')

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
