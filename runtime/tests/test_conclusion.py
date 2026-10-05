#!/usr/bin/env python3
"""Structured conclusion contract and rendering tests."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renderer import render_file  # noqa: E402
from validator import validate_file  # noqa: E402


class ConclusionTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "tests" / "minimal.json").read_text(encoding="utf-8"))

    def render(self, document):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path, output_path = root / "report.json", root / "report.html"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            return output_path.read_text(encoding="utf-8"), validate_file(output_path)

    def test_structured_conclusion_renders_and_validates(self):
        document = self.fixture()
        schema = json.loads((ROOT / "schema" / "compact-workbench-1.0.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(document, schema)
        page, result = self.render(document)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(page.count('class="conclusion-item '), 2)
        self.assertIn("emphasis-strong", page)
        self.assertIn("emphasis-italic", page)
        self.assertIn("conclusion-color-positive", page)
        self.assertIn("font-style:italic", page)

    def test_text_is_escaped_and_not_interpreted_as_html(self):
        document = self.fixture()
        document["views"][0]["blocks"][0]["items"][0]["segments"][1]["text"] = "<script>alert(1)</script>"
        page, result = self.render(document)
        self.assertTrue(result["ok"], result["errors"])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_invalid_conclusion_shape_is_rejected(self):
        document = self.fixture()
        document["views"][0]["blocks"][0]["items"] = document["views"][0]["blocks"][0]["items"][:1]
        schema = json.loads((ROOT / "schema" / "compact-workbench-1.0.schema.json").read_text(encoding="utf-8"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(document, schema)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least two structured items"):
                render_file(input_path, root / "report.html")

    def test_legacy_report_without_conclusion_remains_valid(self):
        document = self.fixture()
        document["views"][0]["blocks"].pop(0)
        _, result = self.render(document)
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
