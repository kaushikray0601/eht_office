import html
import re
from dataclasses import dataclass


@dataclass
class RenderedManual:
    html: str
    toc: list


def _inline(text):
    text = text.strip()
    rendered = []
    cursor = 0
    for match in re.finditer(r'`([^`]+)`', text):
        rendered.append(html.escape(text[cursor:match.start()]))
        rendered.append(_render_inline_code(match.group(1)))
        cursor = match.end()
    rendered.append(html.escape(text[cursor:]))
    return ''.join(rendered)


def _render_inline_code(value):
    if _looks_like_formula(value):
        return f'<span class="manual-formula">{_format_formula(value)}</span>'
    return f'<code>{html.escape(value)}</code>'


def _looks_like_formula(value):
    return bool(
        '=' in value
        or '^' in value
        or '*' in value
        or any(
            token in value
            for token in (
                'Maint_T',
                'Min_Ambient_T',
                'Spiral Factor',
                'Allowed Current per Circuit',
            )
        )
    )


def _format_formula(value):
    formatted = html.escape(value.strip())
    formatted = re.sub(r'\s*\*\s*', ' · ', formatted)
    formatted = re.sub(r'\bpi\b', 'π', formatted)
    formatted = formatted.replace('^2', '<sup>2</sup>')
    replacements = (
        ('Maint_T', 'T<sub>maint</sub>'),
        ('Min_Ambient_T', 'T<sub>amb,min</sub>'),
        ('Low-Voltage Heat-Delivery Power', 'P<sub>low-voltage</sub>'),
        ('Base Heat Loss after wind correction', 'Q<sub>base,wind</sub>'),
        ('Base Heat Loss', 'Q<sub>base</sub>'),
        ('Design Heat Loss', 'Q<sub>design</sub>'),
        ('Heat Loss SF', 'SF<sub>heat</sub>'),
        ('Spiral Factor', 'SF<sub>spiral</sub>'),
        ('Allowed Current per Circuit', 'I<sub>allowed,circuit</sub>'),
    )
    for source, target in replacements:
        formatted = formatted.replace(source, target)
    formatted = re.sub(r'^Power\s*=', 'P =', formatted)
    formatted = re.sub(r'\s+', ' ', formatted).strip()
    return formatted


def _slugify(title, seen):
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'section'
    base = slug
    index = 2
    while slug in seen:
        slug = f'{base}-{index}'
        index += 1
    seen.add(slug)
    return slug


def _is_table_separator(cells):
    return all(re.fullmatch(r':?-{3,}:?', cell.strip() or '') for cell in cells)


def _split_table_row(line):
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def _render_table(rows):
    parsed_rows = [_split_table_row(row) for row in rows]
    parsed_rows = [row for row in parsed_rows if not _is_table_separator(row)]
    if not parsed_rows:
        return ''

    header = parsed_rows[0]
    body = parsed_rows[1:]
    header_html = ''.join(f'<th>{_inline(cell)}</th>' for cell in header)
    body_html = []
    for row in body:
        body_html.append(
            '<tr>' + ''.join(f'<td>{_inline(cell)}</td>' for cell in row) + '</tr>'
        )
    return (
        '<div class="manual-table-wrap"><table class="manual-table">'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{"".join(body_html)}</tbody>'
        '</table></div>'
    )


def render_markdown_manual(source):
    """Render the manual's controlled Markdown subset to safe HTML."""
    blocks = []
    toc = []
    seen_slugs = set()
    paragraph = []
    table_rows = []
    list_type = None
    list_items = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            blocks.append(f'<p>{" ".join(_inline(item) for item in paragraph)}</p>')
            paragraph = []

    def flush_table():
        nonlocal table_rows
        if table_rows:
            rendered = _render_table(table_rows)
            if rendered:
                blocks.append(rendered)
            table_rows = []

    def flush_list():
        nonlocal list_type, list_items
        if list_type and list_items:
            items = ''.join(f'<li>{_inline(item)}</li>' for item in list_items)
            blocks.append(f'<{list_type}>{items}</{list_type}>')
        list_type = None
        list_items = []

    for raw_line in source.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            flush_paragraph()
            flush_table()
            flush_list()
            continue

        heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading_match:
            flush_paragraph()
            flush_table()
            flush_list()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            slug = _slugify(title, seen_slugs)
            if level in {2, 3}:
                toc.append({'level': level, 'title': title, 'id': slug})
            blocks.append(f'<h{level} id="{slug}">{_inline(title)}</h{level}>')
            continue

        if line.lstrip().startswith('|') and line.rstrip().endswith('|'):
            flush_paragraph()
            flush_list()
            table_rows.append(line)
            continue

        bullet_match = re.match(r'^\s*-\s+(.+)$', line)
        if bullet_match:
            flush_paragraph()
            flush_table()
            if list_type not in (None, 'ul'):
                flush_list()
            list_type = 'ul'
            list_items.append(bullet_match.group(1))
            continue

        number_match = re.match(r'^\s*\d+\.\s+(.+)$', line)
        if number_match:
            flush_paragraph()
            flush_table()
            if list_type not in (None, 'ol'):
                flush_list()
            list_type = 'ol'
            list_items.append(number_match.group(1))
            continue

        if list_type and line.startswith('   ') and list_items:
            list_items[-1] = f'{list_items[-1]} {line.strip()}'
            continue

        flush_table()
        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_table()
    flush_list()
    return RenderedManual(html='\n'.join(blocks), toc=toc)
