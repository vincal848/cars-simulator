"""Guards the package layering: sim <- persist <- ui <- app.

The simulation must stay free of pygame so it can run headless, in tests and in
replays, and so rules never depend on how the map is drawn.
"""

import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "cars"
ALLOWED = {
    "sim": {"cars.paths", "cars.sim"},
    "persist": {"cars.paths", "cars.sim", "cars.persist"},
    "ui": {"cars", "cars.paths", "cars.sim", "cars.persist", "cars.ui"},
}
THIRD_PARTY_FORBIDDEN = {"sim": {"pygame"}, "persist": {"pygame"}}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def allowed(module: str, prefixes: set[str]) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


class LayeringTests(unittest.TestCase):
    def test_packages_only_import_lower_layers(self):
        for layer, prefixes in ALLOWED.items():
            for path in (PACKAGE / layer).rglob("*.py"):
                for module in imported_modules(path):
                    if module.startswith("cars"):
                        with self.subTest(file=path.name, module=module):
                            self.assertTrue(allowed(module, prefixes), f"{layer} must not import {module}")
                    for forbidden in THIRD_PARTY_FORBIDDEN.get(layer, ()):
                        with self.subTest(file=path.name, module=module):
                            self.assertFalse(
                                allowed(module, {forbidden}), f"{layer} must not import {forbidden}"
                            )

    def test_imports_live_at_module_level(self):
        """Function-local imports usually hide a dependency cycle; only the launcher may defer one."""
        exempt = {PACKAGE / "app.py"}
        local_imports = []
        for path in PACKAGE.rglob("*.py"):
            if path in exempt:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for function in ast.walk(tree):
                if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(function):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        local_imports.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
        self.assertEqual(local_imports, [])


if __name__ == "__main__":
    unittest.main()
