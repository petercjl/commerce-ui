#!/usr/bin/env python3
"""Regression tests for reusable copy actions in report cells and products."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renderer import render_file  # noqa: E402
from validator import validate_file  # noqa: E402


class CopyActionTests(unittest.TestCase):
    def test_product_and_table_cell_render_copy_actions(self):
        document = json.loads((ROOT / "tests" / "minimal.json").read_text(encoding="utf-8"))
        target = "https://item.taobao.com/item.htm?id=123456"
        document["views"][0]["blocks"].append({
            "type": "table",
            "columns": ["商品"],
            "rows": [[{"text": "示例", "copy_value": target, "copy_label": "复制链接"}]],
        })
        document["views"][0]["blocks"].append({
            "type": "products",
            "items": [{"title": "示例商品", "copy_value": target, "copy_label": "复制链接"}],
        })
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            output_path = root / "report.html"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            html = output_path.read_text(encoding="utf-8")
            self.assertGreaterEqual(html.count('data-copy="https://item.taobao.com/item.htm?id=123456"'), 2)
            self.assertIn("async function copyText", html)
            self.assertTrue(validate_file(output_path)["ok"])


if __name__ == "__main__":
    unittest.main()
