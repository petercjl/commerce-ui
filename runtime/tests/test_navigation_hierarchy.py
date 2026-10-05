#!/usr/bin/env python3
"""Regression tests for fixed reading paths and sidebar-owned tab indexes."""

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


class NavigationHierarchyTests(unittest.TestCase):
    def test_reading_path_and_child_tabs_render_in_navigation(self):
        document = json.loads((ROOT / "tests" / "minimal.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            output_path = root / "report.html"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            html = output_path.read_text(encoding="utf-8")
            self.assertIn('class="reading-path"', html)
            self.assertIn('data-reading-view="details" data-reading-tab="sample-products"', html)
            self.assertIn('class="nav-child" data-child-view="details" data-child-tab="sample-products"', html)
            self.assertIn('body class="sidebar-tabs"', html)
            self.assertIn('.sidebar-tabs .tab-buttons{display:none}', html)
            self.assertIn("function activateTab", html)
            self.assertIn("split('/')", html)
            self.assertIn("ResizeObserver", html)
            self.assertTrue(validate_file(output_path)["ok"])


if __name__ == "__main__":
    unittest.main()
