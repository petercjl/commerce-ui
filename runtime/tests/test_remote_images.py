#!/usr/bin/env python3
"""Regression tests for explicitly approved HTTPS product images."""

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


class RemoteImageTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "tests" / "minimal.json").read_text(encoding="utf-8"))

    def test_approved_https_image_renders_and_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            output_path = root / "report.html"
            input_path.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            validation = validate_file(output_path)
            self.assertTrue(validation["ok"], validation["errors"])
            self.assertEqual(validation["external_image_count"], 2)
            self.assertTrue(validation["external_images_approved"])

    def test_product_images_preserve_intrinsic_aspect_without_cropping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            output_path = root / "report.html"
            input_path.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("--product-image-aspect,1/1", html)
            self.assertIn("object-fit:contain", html)
            self.assertIn("syncProductImageAspect", html)
            self.assertIn("image.naturalWidth", html)
            self.assertNotIn(".product-card img,.image-empty", html)

    def test_remote_image_requires_explicit_approval(self):
        document = self.fixture()
        document["meta"]["external_images"] = "forbid"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires meta.external_images=allow_https"):
                render_file(input_path, root / "report.html")

    def test_validator_rejects_unapproved_remote_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_path = root / "report.json"
            output_path = root / "report.html"
            input_path.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding="utf-8")
            render_file(input_path, output_path)
            html = output_path.read_text(encoding="utf-8").replace(
                'name="commerce-ui-external-images" content="allow_https"',
                'name="commerce-ui-external-images" content="forbid"',
            )
            output_path.write_text(html, encoding="utf-8")
            validation = validate_file(output_path)
            self.assertFalse(validation["ok"])
            self.assertIn("found 2 unapproved external image asset(s)", validation["errors"])


if __name__ == "__main__":
    unittest.main()
