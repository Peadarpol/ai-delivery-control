#!/usr/bin/env python3
"""
Project Dependency Analyzer
Checks for Clean Architecture layer violations.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Define layer order (inner to outer)
LAYERS = ["domain", "application", "infrastructure", "presentation"]


class DependencyAnalyzer:
    def __init__(self, target_path: str, verbose: bool = False):
        self.target_path = Path(target_path)
        self.verbose = verbose
        self.violations = []

    def get_layer(self, file_path: Path) -> str:
        """Identifies which layer a file belongs to based on its path."""
        parts = file_path.parts
        for layer in LAYERS:
            if layer in parts:
                return layer
        return None

    def analyze_file(self, file_path: Path):
        """Scans a file for illegal imports based on its layer."""
        current_layer = self.get_layer(file_path)
        if not current_layer:
            return

        current_layer_idx = LAYERS.index(current_layer)
        # Forbidden layers are those "outer" to the current layer
        forbidden_layers = LAYERS[current_layer_idx + 1 :]

        if not forbidden_layers:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for layer in forbidden_layers:
                # Look for 'from layer...' or 'import layer...'
                pattern = rf"^(?:from|import)\s+src\.{layer}"
                if re.search(pattern, content, re.MULTILINE):
                    self.violations.append(
                        {
                            "file": str(file_path),
                            "layer": current_layer,
                            "forbidden_import": layer,
                        }
                    )
        except Exception as e:
            if self.verbose:
                print(f"Error reading {file_path}: {e}")

    def run(self):
        print(f"Analyzing dependencies in {self.target_path}...")

        # Walk through src directory
        for root, _, files in os.walk(self.target_path):
            for file in files:
                if file.endswith(".py"):
                    self.analyze_file(Path(root) / file)

        if not self.violations:
            print("No architecture violations found!")
            return 0
        else:
            print(f"Found {len(self.violations)} violations:")
            for v in self.violations:
                print(
                    f"  - {v['file']}: Layer '{v['layer']}' incorrectly imports from '{v['forbidden_import']}'"
                )
            return 1


def main():
    parser = argparse.ArgumentParser(description="Project Dependency Analyzer")
    parser.add_argument("target", help="Directory to scan (e.g., src/)")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()
    analyzer = DependencyAnalyzer(args.target, args.verbose)
    sys.exit(analyzer.run())


if __name__ == "__main__":
    main()
