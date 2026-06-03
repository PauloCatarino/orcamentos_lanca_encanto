from pathlib import Path
import unittest

from Martelo_Orcamentos_V2.app.utils.resources import resolve_package_asset_path


class ResourcePathTests(unittest.TestCase):
    def test_resolve_package_asset_path_finds_imos_icon(self):
        path = resolve_package_asset_path("ui", "assets", "icon_imos_2025.ico")
        self.assertTrue(path.is_file(), f"Asset nao encontrado: {path}")
        self.assertEqual(path.suffix.lower(), ".ico")


if __name__ == "__main__":
    unittest.main()
