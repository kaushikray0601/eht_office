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
UPSTREAM_TYPES = {'MCB', 'Cable4C', 'Isolator3PH', 'JB3PH'}
BOX_STYLES = {
    'MCB': (58, 34, colors.HexColor('#eaf3fb'), colors.HexColor('#17324d')),
    'Cable4C': (70, 16, colors.HexColor('#fff5df'), colors.HexColor('#8a5b12')),
    'Cable3C': (70, 16, colors.HexColor('#fff5df'), colors.HexColor('#8a5b12')),
    'Isolator3PH': (54, 24, colors.HexColor('#edf4fb'), colors.HexColor('#17324d')),
    'Isolator1PH': (54, 24, colors.HexColor('#edf4fb'), colors.HexColor('#17324d')),
    'JB3PH': (58, 34, colors.HexColor('#edf4fb'), colors.HexColor('#17324d')),
    'JB1PH': (58, 34, colors.HexColor('#edf4fb'), colors.HexColor('#17324d')),
    'Tracer': (76, 18, colors.HexColor('#f3fbf3'), colors.HexColor('#287a41')),
    'EndTermination': (28, 28, colors.HexColor('#17324d'), colors.HexColor('#17324d')),
}


def _node_matches_line_group(node, group):
    line_uid = group.get('line_uid')
    if line_uid and node.get('line_uid'):
        return str(node.get('line_uid')) == str(line_uid)
    return group.get('line_id') in node.get('line_ids', [])


def _sort_nodes(nodes):
    return sorted(
        nodes,
        key=lambda node: (
            node.get('branch_index') or 0,
            -1 if node.get('circuit_index') is None else node.get('circuit_index'),
            COMPONENT_ORDER.get(node.get('component_type'), 99),
            node.get('display_tag') or '',
        ),
    )


def _draw_centered_text(pdf, text, x, y, width, size=7, color=colors.HexColor('#17324d')):
    pdf.setFillColor(color)
    pdf.setFont('Helvetica', size)
    value = str(text or '')
    if len(value) > 18:
        value = value[:17] + '...'
    pdf.drawCentredString(x + width / 2, y, value)


def _component_width(node):
    return BOX_STYLES.get(node.get('component_type'), (62, 24, None, None))[0]


def _draw_component(pdf, node, x, y):
    component_type = node.get('component_type')
    width, height, fill, stroke = BOX_STYLES.get(
        component_type,
        (62, 24, colors.HexColor('#f8fafc'), colors.HexColor('#5b748b')),
    )
    if component_type == 'EndTermination':
        pdf.setFillColor(fill)
        pdf.circle(x + width / 2, y, width / 2, stroke=0, fill=1)
        _draw_centered_text(pdf, node.get('display_tag'), x + width + 8, y + 4, 82, size=7)
        return width

    pdf.setStrokeColor(stroke)
    pdf.setFillColor(fill)
    pdf.roundRect(x, y - height / 2, width, height, 3, stroke=1, fill=1)
    _draw_centered_text(pdf, node.get('display_tag'), x, y - 2, width)
    if component_type in {'MCB', 'JB1PH', 'JB3PH'}:
        _draw_centered_text(pdf, node.get('display_name'), x, y - 11, width, size=6)
    return width


def _draw_link(pdf, x1, y1, x2, y2):
    pdf.setStrokeColor(colors.HexColor('#17324d'))
    pdf.setLineWidth(1.2)
    mid_x = x1 + (x2 - x1) / 2
    pdf.line(x1, y1, mid_x, y1)
    pdf.line(mid_x, y1, mid_x, y2)
    pdf.line(mid_x, y2, x2, y2)


def _draw_branch_link(pdf, anchor, x2, y2):
    source_right = anchor['source_right']
    source_y = anchor['source_y']
    trunk_x = anchor['trunk_x']
    pdf.setStrokeColor(colors.HexColor('#17324d'))
    pdf.setLineWidth(1.2)
    pdf.line(source_right, source_y, trunk_x, source_y)
    pdf.line(trunk_x, source_y, trunk_x, y2)
    pdf.line(trunk_x, y2, x2, y2)


def _line_rows(payload, line_group):
    nodes = [node for node in payload.get('nodes', []) if _node_matches_line_group(node, line_group)]
    rows = []
    branch_indices = sorted({node.get('branch_index') or 0 for node in nodes}) or [0]
    for branch_index in branch_indices:
        branch_nodes = [node for node in nodes if (node.get('branch_index') or 0) == branch_index]
        upstream = [
            node for node in branch_nodes
            if node.get('component_type') in UPSTREAM_TYPES and node.get('circuit_index') is None
        ]
        circuit_indices = sorted({
            node.get('circuit_index')
            for node in branch_nodes
            if node.get('circuit_index') is not None
        }) or [None]
        for circuit_index in circuit_indices:
            downstream = [
                node for node in branch_nodes
                if node.get('circuit_index') == circuit_index and node.get('component_type') not in UPSTREAM_TYPES
            ]
            rows.append({
                'branch_index': branch_index,
                'circuit_index': circuit_index,
                'upstream': _sort_nodes(upstream),
                'downstream': _sort_nodes(downstream),
            })
    return rows


def _start_page(pdf, project_id, page_width, page_height, margin):
    pdf.setTitle(f'{project_id} Single Line Diagram')
    pdf.setFont('Helvetica-Bold', 13)
    pdf.setFillColor(colors.HexColor('#17324d'))
    pdf.drawString(margin, page_height - margin + 4, f'{project_id} - Single Line Diagram')
    pdf.setStrokeColor(colors.HexColor('#b7c7d6'))
    pdf.line(margin, page_height - margin - 6, page_width - margin, page_height - margin - 6)


def build_sld_pdf(project_id, payload):
    buffer = BytesIO()
    page_size = landscape(A3)
    pdf = canvas.Canvas(buffer, pagesize=page_size)
    page_width, page_height = page_size
    margin = 12 * mm
    x_line = margin
    x_start = margin + 126
    column_gap = 28
    row_gap = 58
    y = page_height - margin - 42

    _start_page(pdf, project_id, page_width, page_height, margin)
    for group in payload.get('line_groups', []):
        rows = _line_rows(payload, group)
        block_height = max(1, len(rows)) * row_gap + 20
        if y - block_height < margin:
            pdf.showPage()
            _start_page(pdf, project_id, page_width, page_height, margin)
            y = page_height - margin - 42

        pdf.setFillColor(colors.HexColor('#edf4fb'))
        pdf.setStrokeColor(colors.HexColor('#c7d6e2'))
        pdf.roundRect(x_line, y - 14, 116, 24, 3, stroke=1, fill=1)
        _draw_centered_text(pdf, f"Line: {group.get('line_id')}", x_line + 4, y - 2, 108, size=7)

        branch_anchors = {}
        for row_index, row in enumerate(rows):
            row_y = y - row_index * row_gap
            pdf.setFont('Helvetica', 6)
            pdf.setFillColor(colors.HexColor('#5b748b'))
            pdf.drawCentredString(x_line + 58, row_y - 28, f"B{row['branch_index']}")

            previous_right = None
            previous_y = row_y
            branch_key = row['branch_index']
            upstream = row['upstream'] if branch_key not in branch_anchors else []
            downstream_x_offset = len(row['upstream']) * (78 + column_gap)
            components = upstream + row['downstream']
            for column_index, node in enumerate(components):
                if upstream:
                    x = x_start + column_index * (78 + column_gap)
                else:
                    x = x_start + downstream_x_offset + column_index * (78 + column_gap)
                width = _draw_component(pdf, node, x, row_y)
                if not upstream and column_index == 0 and branch_key in branch_anchors:
                    _draw_branch_link(pdf, branch_anchors[branch_key], x, row_y)
                if previous_right is not None:
                    _draw_link(pdf, previous_right, previous_y, x, row_y)
                previous_right = x + width
                previous_y = row_y
            if upstream and previous_right is not None:
                branch_anchors[branch_key] = {
                    'source_right': x_start + (len(upstream) - 1) * (78 + column_gap) + _component_width(upstream[-1]),
                    'source_y': row_y,
                    'trunk_x': x_start + downstream_x_offset - (column_gap / 2),
                }
        y -= block_height

    if not payload.get('line_groups'):
        pdf.setFont('Helvetica', 10)
        pdf.drawString(margin, y, 'No SLD line groups are available for export.')

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
