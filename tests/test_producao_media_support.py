import tempfile
import unittest
from pathlib import Path

from Martelo_Orcamentos_V2.ui.pages.producao_media_support import (
    build_external_names,
    build_folder_preview_text,
    find_imos_ix_image_path,
)


class ProducaoMediaSupportTests(unittest.TestCase):
    def test_build_external_names_uses_supplied_builders(self):
        plano, enc = build_external_names(
            ano="2026",
            num_enc="123",
            versao_obra="01",
            versao_plano="02",
            nome_simplex="CLIENTE",
            nome_cliente="Cliente",
            ref_cliente="REF",
            plano_builder=lambda *args, **kwargs: "PLANO",
            imos_builder=lambda *args, **kwargs: "IMOS",
        )
        self.assertEqual(plano, "PLANO")
        self.assertEqual(enc, "IMOS")

    def test_find_imos_ix_image_path_returns_existing_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "ENC_001"
            folder.mkdir()
            file_path = folder / "ENC_001.png"
            file_path.write_bytes(b"png")
            self.assertEqual(find_imos_ix_image_path(tmp, "ENC_001"), file_path)

    def test_build_folder_preview_text_handles_folder_and_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("x", encoding="utf-8")
            preview = build_folder_preview_text(tmp)
            self.assertIn("Conteudo da pasta:", preview)
            self.assertIn("a.txt", preview)
        self.assertEqual(build_folder_preview_text(""), "")


if __name__ == "__main__":
    unittest.main()
