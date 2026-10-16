"""혈압 측정 명단의 제목과 인쇄용 엑셀 서식."""

import io

import pandas as pd


def measurement_title(start, end, group='고령자'):
    if end < start:
        raise ValueError('종료일은 시작일과 같거나 늦어야 합니다.')
    period = start.strftime('%Y.%m.%d')
    if start != end:
        end_format = '%m.%d' if start.year == end.year else '%Y.%m.%d'
        period += '~' + end.strftime(end_format)
    return f'{period} {group} 혈압측정'


def measurement_date_label(start, end):
    if start == end:
        return f'{start.year}년 {start.month}월 {start.day}일'
    if (start.year, start.month) == (end.year, end.month):
        return f'{start.year}년 {start.month}월      일'
    return '        년     월     일'


def create_excel(roster, start, end, group='고령자'):
    title = measurement_title(start, end, group)
    rows = roster.copy()
    blank_rows = pd.DataFrame([[''] * len(rows.columns)] * 10, columns=rows.columns)
    if '고혈압 복용 여부' in rows.columns:
        blank_rows['고혈압 복용 여부'] = '□예  □아니오'
    rows = pd.concat([rows, blank_rows], ignore_index=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet(f'{group}명단')
        base = {'font_name': '맑은 고딕', 'font_size': 12, 'border': 1,
                'align': 'center', 'valign': 'vcenter'}
        title_format = workbook.add_format({**base, 'font_size': 18, 'bold': True})
        header_format = workbook.add_format({**base, 'bold': True, 'bg_color': '#D9D9D9'})
        cell_format = workbook.add_format(base)
        date_format = workbook.add_format({**base, 'bg_color': '#FCE4D6'})
        pressure_format = workbook.add_format({**base, 'bg_color': '#FFFFCC'})
        signature_format = workbook.add_format({**base, 'bg_color': '#EBF1DE'})
        formats = {'혈압잰 일자': date_format, '오늘의 혈압': pressure_format,
                   '서명란': signature_format}

        worksheet.set_default_row(25)
        worksheet.merge_range(0, 0, 0, len(rows.columns) - 1, title, title_format)
        worksheet.set_row(0, 25)
        worksheet.set_row(1, 25)
        for col, name in enumerate(rows.columns):
            worksheet.write_string(1, col, name, header_format)
        for row_index, row in enumerate(rows.itertuples(index=False, name=None), start=2):
            worksheet.set_row(row_index, 25)
            for col, value in enumerate(row):
                fmt = formats.get(rows.columns[col], cell_format)
                if pd.isna(value) or value == '':
                    worksheet.write_blank(row_index, col, None, fmt)
                elif isinstance(value, str):
                    worksheet.write_string(row_index, col, value, fmt)
                else:
                    worksheet.write(row_index, col, value, fmt)

        widths = {'No.': 6, '협력회사': 25, '이름': 12, '공종': 18, '혈압잰 일자': 24,
                  '오늘의 혈압': 19, '고혈압 복용 여부': 22, '서명란': 16}
        for col, name in enumerate(rows.columns):
            worksheet.set_column(col, col, widths.get(name, 16))
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.repeat_rows(0, 1)
        worksheet.print_area(0, 0, len(rows) + 1, len(rows.columns) - 1)
        worksheet.center_horizontally()
    output.seek(0)
    return output
