import unittest

import pandas as pd
from PIL import Image, ImageChops

from image_export import create_image


class ImageExportTests(unittest.TestCase):
    def setUp(self):
        self.roster = pd.DataFrame({
            'No.': [1], '협력회사': ['테스트회사'], '이름': ['테스트근로자'], '공종': ['목공'],
        })

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


if __name__ == '__main__':
    unittest.main()
