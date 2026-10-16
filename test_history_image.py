import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from PIL import Image, ImageChops
from streamlit.testing.v1 import AppTest

from history_store import list_reports, load_report, save_report
from image_export import create_image


class HistoryImageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict('os.environ', {
            'GSOLD_HISTORY_DB': str(Path(self.directory.name) / 'history.sqlite3'),
        })
        self.environment.start()
        self.roster = pd.DataFrame({
            'No.': [1], '협력회사': ['테스트회사'], '이름': ['테스트근로자'], '공종': ['목공'],
            '혈압잰 일자': ['2026년 10월      일'], '오늘의 혈압': ['     /     '], '서명란': [''],
        })

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def save(self, roster=None):
        return save_report(self.roster if roster is None else roster, date(2026, 10, 19),
                           date(2026, 10, 20), '2026.10.19~10.20 고령자 혈압측정',
                           2, io.BytesIO(b'original-excel'), io.BytesIO(b'original-png'))

    def test_record_survives_new_connection_and_deduplicates(self):
        first = self.save()
        self.assertEqual(self.save(), first)
        self.assertEqual(len(list_reports()), 1)
        record = load_report(first)
        self.assertEqual(record['excel'], b'original-excel')
        self.assertEqual(record['png'], b'original-png')
        self.assertEqual(record['label'], '26.10.19~10.20 고령자 혈압측정')
        restored = pd.read_json(io.StringIO(record['roster']), orient='split', dtype=False)
        pd.testing.assert_frame_equal(restored, self.roster)
        changed = self.roster.copy()
        changed.loc[0, '이름'] = '다른근로자'
        self.assertNotEqual(self.save(changed), first)
        self.assertEqual(len(list_reports()), 2)
        self.assertEqual(load_report(first)['roster'], record['roster'])

    def test_image_reserves_title_table_and_footer_space(self):
        # Run from the app's font directory, just like the Streamlit service.
        for count in (1, 13, 60):
            with self.subTest(count=count):
                roster = pd.concat([self.roster] * count, ignore_index=True)
                png = create_image(roster, '2026.10.19~10.20 고령자 혈압측정', 'NanumGothic.ttf')
                image = Image.open(png).convert('RGB')
                ink = ImageChops.difference(image, Image.new('RGB', image.size, 'white'))
                self.assertIsNotNone(ink.crop((80, 40, 2400, 150)).getbbox())
                self.assertIsNone(ink.crop((80, 150, 2400, 185)).getbbox())
                table_bottom = 190 + 90 + count * 85
                self.assertIsNone(ink.crop((80, table_bottom + 5, 2400, table_bottom + 45)).getbbox())
                self.assertIsNotNone(ink.crop((80, table_bottom + 50, 2400, table_bottom + 150)).getbbox())
                self.assertGreaterEqual(image.height, table_bottom + 230)

    def test_new_session_can_open_record_and_original_downloads(self):
        # Generate through the app, then reopen through a separate app session.
        source = io.BytesIO()
        row = [''] * 12
        row[3], row[4], row[5], row[9], row[11] = '테스트회사', '목공', '테스트근로자', '한국', '500101-1'
        pd.DataFrame([row]).to_excel(source, index=False)
        source.seek(0)
        app_file = str(Path(__file__).with_name('app.py'))
        with patch('streamlit.file_uploader', return_value=source):
            first = AppTest.from_file(app_file).run(timeout=30)
        self.assertFalse(first.exception)
        self.assertFalse(first.error)
        reports = list_reports()
        self.assertEqual(len(reports), 1)
        original = load_report(reports[0]['id'])
        second = AppTest.from_file(app_file).run(timeout=30)
        second.radio[0].set_value('생성 기록').run(timeout=30)
        self.assertFalse(second.exception)
        self.assertFalse(second.error)
        self.assertEqual(len(second.selectbox[0].options), 1)
        self.assertIn('고령자 혈압측정', second.selectbox[0].options[0])
        self.assertEqual(second.dataframe[0].value['이름'].tolist(), ['테스트근로자'])
        self.assertEqual(len(second.get('download_button')), 2)
        self.assertEqual(load_report(reports[0]['id'])['png'], original['png'])


if __name__ == '__main__':
    unittest.main()
