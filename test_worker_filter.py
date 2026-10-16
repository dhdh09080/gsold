import io
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import openpyxl
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from worker_filter import parse_blood_pressure, select_high_pressure_workers


class WorkerFilterTests(unittest.TestCase):
    def test_readings_and_unreadable_values(self):
        for text, expected in [
            ('2026.10.16(119/64)', (119, 64)),
            ('2026.10.16(150/90)', (150, 90)),
            ('2026.10.16(140/100)', (140, 100)),
            (' 150 ／ 100 mmHg ', (150, 100)),
            ('수축기: 150 이완기: 90', (150, 90)),
            (None, None), ('', None), ('미측정', None),
            ('2026/10/16', None), ('2026.10.16', None),
            ('150/', None), ('149/99 → 155/101', None),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_blood_pressure(text), expected)

    def test_thresholds_and_age_exclusion(self):
        workers = pd.DataFrame({
            '협력회사명': ['회사'] * 8,
            '성명': ['수축기경계', '이완기경계', '미달', '둘다', '고령', '나이미상', '빈칸', '정상'],
            '만_나이': [62, 40, 40, 40, 63, -1, 40, 40],
            '최종혈압결과': ['2026.10.16(150/90)', '2026.10.16(140/100)',
                         '2026.10.16(149/99)', '2026.10.16(150/100)',
                         '2026.10.16(180/120)', '2026.10.16(180/120)',
                         None, '2026.10.16(119/64)'],
        })
        high, readings = select_high_pressure_workers(workers)
        self.assertEqual(set(high['성명']), {'수축기경계', '이완기경계', '둘다'})
        self.assertTrue(pd.isna(readings.iloc[6]))

    def test_both_tabs_export_distinct_files_with_medication_column(self):
        rows = []
        for name, birth, pressure in [
            ('고령대상', '500101-1', '2026.10.16(180/110)'),
            ('수축기대상', '900101-1', '2026.10.16(150/90)'),
            ('이완기대상', '900101-1', '2026.10.16(140/100)'),
            ('미달', '900101-1', '2026.10.16(149/99)'),
            ('정상', '900101-1', '2026.10.16(119/64)'),
        ]:
            row = [''] * 17
            row[3], row[4], row[5], row[9], row[11], row[16] = '회사', '목공', name, '한국', birth, pressure
            rows.append(row)
        source = io.BytesIO()
        pd.DataFrame(rows).to_excel(source, index=False)
        source.seek(0)
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=30)
        app.date_input[0].set_value(date(2026, 10, 19))
        app.date_input[1].set_value(date(2026, 10, 20))
        downloads = {}
        original = st.download_button

        def capture(**kwargs):
            downloads[kwargs['file_name']] = kwargs['data'].getvalue()
            return original(**kwargs)

        with patch('streamlit.file_uploader', return_value=source), \
                patch('streamlit.download_button', side_effect=capture):
            app.run(timeout=60)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual([metric.value for metric in app.metric], ['5 명', '1 명', '2 명'])
        self.assertEqual(len(downloads), 4)
        self.assertEqual(app.dataframe[0].value['이름'].tolist(), ['고령대상'])
        self.assertEqual(set(app.dataframe[1].value['이름']), {'수축기대상', '이완기대상'})
        for group in ('고령자', '고혈압 근로자'):
            title = f'2026.10.19~10.20 {group} 혈압측정'
            sheet = openpyxl.load_workbook(io.BytesIO(downloads[title + '.xlsx'])).active
            self.assertEqual(sheet['A1'].value, title)
            self.assertEqual(str(sheet.merged_cells), 'A1:H1')
            self.assertEqual(sheet['G2'].value, '고혈압 복용 여부')
            self.assertEqual(sheet['G3'].value, '□예  □아니오')
            self.assertEqual(sheet['H2'].value, '서명란')
            self.assertEqual(sheet.print_title_rows, '$1:$2')
            self.assertTrue(downloads[title + '.png'].startswith(b'\x89PNG\r\n\x1a\n'))


if __name__ == '__main__':
    unittest.main()
