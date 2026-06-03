import shutil
import unittest
import uuid
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from Martelo_Orcamentos_V2.app.services import imos_msg_sync


class ImosMsgSyncTests(unittest.TestCase):
    @contextmanager
    def _tmp_dir(self):
        root = Path.cwd() / "tests" / "_tmp_codex_imos_msg_sync"
        root.mkdir(parents=True, exist_ok=True)
        tmp = root / f"case_{uuid.uuid4().hex}"
        tmp.mkdir()
        try:
            yield str(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _write_workbook(self, path: Path, rows: list[tuple[object, object, object]]) -> None:
        workbook = Workbook()
        worksheet = workbook.active
        for row in rows:
            worksheet.append(row)
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()
        path.write_bytes(buffer.getvalue())

    def test_load_translation_overrides_supports_xlx_extension(self):
        with self._tmp_dir() as tmp:
            workbook_path = Path(tmp) / "imos_msg.xlx"
            self._write_workbook(
                workbook_path,
                [
                    ("", "Referencia", "Texto"),
                    ("", "PTG;10280", "Ref do Fornecedor"),
                    ("", "PTG;10280", "Ref. Fornecedor"),
                    ("", 11, "\nAltura do fundo"),
                    ("", "", "Ignorado"),
                ],
            )

            resolved_path, overrides, duplicate_keys = imos_msg_sync.load_translation_overrides(workbook_path)

        self.assertEqual(resolved_path, workbook_path)
        self.assertEqual(overrides["PTG;10280"], "Ref. Fornecedor")
        self.assertEqual(overrides["PTG;11"], r"\nAltura do fundo")
        self.assertEqual(duplicate_keys, ["PTG;10280"])

    def test_sync_updates_msg_preserving_bom_crlf_and_spacing(self):
        with self._tmp_dir() as tmp:
            root = Path(tmp)
            workbook_path = root / "imos_msg.xlsx"
            msg_path = root / "imos.msg"
            self._write_workbook(
                workbook_path,
                [
                    ("", "PTG;10280", "Ref do Fornecedor"),
                    ("", "PTG;11", "\nAltura do fundo"),
                    ("", "PTG;99999", "Nao encontrado"),
                ],
            )

            original_body = (
                "! comentario\r\n"
                "PTG;10280\t;Texto antigo\r\n"
                "ENG;10280\t;Supplier Ref\r\n"
                "PTG;11\t;\\nAltura do fundo\r\n"
            )
            original_raw = b"\xef\xbb\xbf" + original_body.encode("utf-8")
            msg_path.write_bytes(original_raw)

            result = imos_msg_sync.sync_imos_msg_translations(
                msg_path=msg_path,
                workbook_path=workbook_path,
            )

            updated_raw = msg_path.read_bytes()
            self.assertTrue(updated_raw.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(result.updated, 1)
            self.assertEqual(result.unchanged, 1)
            self.assertEqual(result.matched, 2)
            self.assertEqual(result.missing_keys, ["PTG;99999"])
            self.assertIsNotNone(result.backup_path)
            self.assertTrue(result.backup_path.is_file())
            self.assertEqual(result.backup_path.read_bytes(), original_raw)

            updated_text = updated_raw.decode("utf-8-sig")
            self.assertIn("PTG;10280\t;Ref do Fornecedor\r\n", updated_text)
            self.assertIn("ENG;10280\t;Supplier Ref\r\n", updated_text)
            self.assertIn("PTG;11\t;\\nAltura do fundo\r\n", updated_text)


if __name__ == "__main__":
    unittest.main()
