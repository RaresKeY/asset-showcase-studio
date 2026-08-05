#!/usr/bin/env python3
"""Regression fixtures for project-specific Godot source guards."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path


VALIDATOR = runpy.run_path(str(Path(__file__).with_name("validate_project.py")))
COMMA_FILE_FILTER = VALIDATOR["COMMA_FILE_FILTER"]
VARIANT_ARRAY_INFERENCE = VALIDATOR["VARIANT_ARRAY_INFERENCE"]


class StaticGuardTests(unittest.TestCase):
    def test_rejects_comma_packed_file_filters(self) -> None:
        for annotation in ("export_file", "export_file_path", "export_global_file"):
            source = f'@{annotation}("*.glb,*.gltf") var path := ""'
            self.assertIsNotNone(COMMA_FILE_FILTER.search(source))

    def test_accepts_separate_or_single_file_filters(self) -> None:
        self.assertIsNone(
            COMMA_FILE_FILTER.search('@export_file("*.glb", "*.gltf") var path := ""')
        )
        self.assertIsNone(COMMA_FILE_FILTER.search('@export_file("*.glb") var path := ""'))

    def test_rejects_variant_array_inference(self) -> None:
        for method in ("pop_back", "pop_front", "pop_at", "front", "back"):
            argument = "0" if method == "pop_at" else ""
            source = f"var current := queue.{method}({argument})"
            self.assertIsNotNone(VARIANT_ARRAY_INFERENCE.search(source))

    def test_accepts_explicitly_typed_pop(self) -> None:
        source = "var current: Node = queue.pop_back() as Node"
        self.assertIsNone(VARIANT_ARRAY_INFERENCE.search(source))


if __name__ == "__main__":
    unittest.main()
