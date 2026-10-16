"""제목과 안내문 영역을 분리한 인쇄용 명단 이미지."""

import io

from PIL import Image, ImageDraw, ImageFont


NOTICE = (
    '반장님들께서는 근로자들이 월요일 또는 화요일 중 편한 시간에',
    '혈압을 측정하고 결과를 기록한 뒤 가실 수 있도록 독려해 주세요.',
)


def wrap_cell(text, font, width):
    lines = ['']
    for char in str(text):
        if char == '\n':
            lines.append('')
        elif font.getlength(lines[-1] + char) > width and lines[-1]:
            lines.append(char)
        else:
            lines[-1] += char
    return '\n'.join(lines)


def create_image(roster, title, font_path):
    width, margin = 2480, 80
    font = ImageFont.truetype(str(font_path), 40)
    title_font = ImageFont.truetype(str(font_path), 60)
    while title_font.getlength(title) > width - margin * 2:
        title_font = ImageFont.truetype(str(font_path), title_font.size - 1)
    note_font = ImageFont.truetype(str(font_path), 32)
    edges = [margin]
    for proportion in (0.08, 0.45, 0.20, 0.27):
        edges.append(edges[-1] + round((width - 2 * margin) * proportion))

    rows = []
    for row in roster[['No.', '협력회사', '이름', '공종']].itertuples(index=False, name=None):
        cells = [wrap_cell(value, font, edges[i + 1] - edges[i] - 30)
                 for i, value in enumerate(row)]
        height = max(85, max(cell.count('\n') + 1 for cell in cells) * 52 + 24)
        rows.append((cells, height))

    table_top, header_height = 190, 90
    table_bottom = table_top + header_height + sum(height for _, height in rows)
    image = Image.new('RGB', (width, max(3508, table_bottom + 230)), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((width // 2, 65), title, font=title_font, fill='black', anchor='mt')
    y = table_top
    for cells, height, fill in [(['No.', '협력회사', '이름', '공종'], header_height, '#D9D9D9')] + [
            (cells, height, 'white') for cells, height in rows]:
        for col, text in enumerate(cells):
            draw.rectangle((edges[col], y, edges[col + 1], y + height), fill=fill,
                           outline='black', width=2)
            bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=8)
            x = (edges[col] + edges[col + 1] - bounds[2] - bounds[0]) / 2
            text_y = y + (height - bounds[3] - bounds[1]) / 2
            draw.multiline_text((x, text_y), text, font=font, fill='black',
                                align='center', spacing=8)
        y += height
    for line, note in enumerate(NOTICE):
        draw.text((width // 2, table_bottom + 50 + line * 48), note,
                  font=note_font, fill='#444444', anchor='mt')
    output = io.BytesIO()
    image.save(output, format='PNG', dpi=(300, 300))
    output.seek(0)
    return output
