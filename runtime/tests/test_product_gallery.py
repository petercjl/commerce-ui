#!/usr/bin/env python3
"""Opt-in product gallery controls and legacy product rendering."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renderer import render_file  # noqa: E402
from validator import validate_file  # noqa: E402


class ProductGalleryTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "tests" / "minimal.json").read_text(encoding="utf-8"))

    def test_paged_gallery_contains_sort_values_and_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "fixture.json"
            output = pathlib.Path(directory) / "fixture.html"
            source.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding="utf-8")
            render_file(source, output)
            html = output.read_text(encoding="utf-8")
            self.assertEqual(html.count('class="product-gallery"'), 1)
            self.assertEqual(html.count('class="gallery-entry"'), 2)
            self.assertIn('data-page-size="1"', html)
            self.assertIn('data-sort-values="{&quot;price&quot;:99}"', html)
            self.assertEqual(html.count('class="product-media-link"'), 1)
            self.assertEqual(html.count('class="product-title-link"'), 1)
            self.assertIn('target="_blank" rel="noopener noreferrer"', html)
            self.assertIn('data-copy="123456">复制商品ID</button>', html)
            self.assertIn('data-copy="https://item.taobao.com/item.htm?id=123456">复制链接</button>', html)
            self.assertIn('function updateGallery(', html)
            self.assertIn('matches.slice((page-1)*size,page*size)', html)
            self.assertTrue(validate_file(output)["ok"])

    def test_product_link_must_be_https(self):
        document = self.fixture()
        document["views"][1]["blocks"][2]["items"][0]["item_url"] = "javascript:alert(1)"
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "fixture.json"
            output = pathlib.Path(directory) / "fixture.html"
            source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                render_file(source, output)

    def test_legacy_products_block_remains_plain_grid(self):
        document = self.fixture()
        block = document["views"][1]["blocks"][2]
        block.pop("page_size")
        block.pop("sort_options")
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "fixture.json"
            output = pathlib.Path(directory) / "fixture.html"
            source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            render_file(source, output)
            html = output.read_text(encoding="utf-8")
            self.assertNotIn('class="product-gallery"', html)
            self.assertTrue(validate_file(output)["ok"])


if __name__ == "__main__":
    unittest.main()
