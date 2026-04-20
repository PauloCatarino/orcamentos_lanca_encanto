import os
import struct
import tempfile
import unittest
import zipfile
from datetime import datetime as real_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6 import QtCore, QtGui

from Martelo_Orcamentos_V2.app.services import producao_preparacao


class _FixedDateTime:
    @classmethod
    def now(cls):
        return real_datetime(2026, 3, 10, 9, 0, 0)


class ProducaoPreparacaoTests(unittest.TestCase):
    def test_qpdf_load_ok_accepts_zero_like_status(self):
        self.assertTrue(producao_preparacao._qpdf_load_ok(0, 0))
        self.assertTrue(producao_preparacao._qpdf_load_ok(SimpleNamespace(name="None_"), 0))
        self.assertFalse(producao_preparacao._qpdf_load_ok(SimpleNamespace(name="Unknown"), 0))

    @unittest.skipUnless(__import__("importlib").util.find_spec("reportlab") is not None, "reportlab nao instalado")
    def test_extract_conj_page_images_reads_real_pdf_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "CONJ.pdf"

            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfgen import canvas

            page_width, page_height = landscape(A4)
            pdf = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
            pdf.drawString(40, page_height - 40, "Pagina 1")
            pdf.showPage()
            pdf.drawString(40, page_height - 40, "Pagina 2")
            pdf.save()

            images = producao_preparacao._extract_conj_page_images(pdf_path, max_pages=2)

        self.assertEqual(len(images), 2)
        self.assertTrue(all(not image.isNull() for image in images))

    def test_resolve_preparacao_context_builds_expected_paths(self):
        processo = SimpleNamespace(id=15, codigo_processo="26.0388_01_01")
        with tempfile.TemporaryDirectory() as tmp:
            work_folder = Path(tmp) / "obra"
            work_folder.mkdir()

            with patch.object(
                producao_preparacao.svc_producao_workflow,
                "load_processo_required",
                return_value=processo,
            ), patch.object(
                producao_preparacao,
                "get_setting",
                side_effect=[
                    str(Path(tmp) / "cnc_root"),
                    str(Path(tmp) / "mpr_root"),
                    str(Path(tmp) / "cutrite_exports"),
                    str(Path(tmp) / "imorder_root"),
                ],
            ), patch.object(producao_preparacao, "datetime", _FixedDateTime):
                context = producao_preparacao.resolve_preparacao_context(
                    object(),
                    current_id=15,
                    pasta_servidor=str(work_folder),
                    nome_enc_imos="0388_01_26_JF_VIVA",
                    nome_plano_cut_rite="0388_01_01_26_JF_VIVA",
                )

        self.assertEqual(context.processo, processo)
        self.assertEqual(context.work_folder, work_folder)
        self.assertEqual(context.cnc_source_folder.name, "0388_01_26_JF_VIVA")
        self.assertEqual(context.work_programs_folder, work_folder / "0388_01_26_JF_VIVA")
        self.assertEqual(context.mpr_year_folder.name, "2026_MPR")
        self.assertEqual(context.mpr_programs_folder.name, "0388_01_26_JF_VIVA")

    def test_collect_preparacao_statuses_reflect_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            conj_pdf = work_folder / producao_preparacao.CONJ_PDF_FILENAME
            projeto_pdf = work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME
            cutrite_export_root = base / "cutrite_exports"
            cutrite_export_root.mkdir()
            (cutrite_export_root / "PROC_PLANO.pdf").write_text("pdf", encoding="utf-8")
            (work_folder / "PROC_PLANO.pdf").write_text("pdf", encoding="utf-8")
            cnc_source = base / "cnc_root" / "PROC"
            cnc_source.mkdir(parents=True)
            (cnc_source / "a.mpr").write_text("x", encoding="utf-8")
            work_programs = work_folder / "PROC"
            work_programs.mkdir()
            (work_programs / "b.mpr").write_text("x", encoding="utf-8")
            mpr_year = base / "mpr_root" / "2026_MPR"
            mpr_year.mkdir(parents=True)
            mpr_programs = mpr_year / "PROC"
            mpr_programs.mkdir()
            (mpr_programs / "b.mpr").write_text("x", encoding="utf-8")
            conj_pdf.write_text("pdf", encoding="utf-8")
            projeto_pdf.write_text("pdf", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=cnc_source,
                work_programs_folder=work_programs,
                mpr_root=base / "mpr_root",
                mpr_year_folder=mpr_year,
                mpr_programs_folder=mpr_programs,
                conj_pdf_path=conj_pdf,
                projeto_pdf_path=projeto_pdf,
                cutrite_export_root=cutrite_export_root,
            )

            statuses = producao_preparacao.collect_preparacao_statuses(context)

        status_map = {status.key: status for status in statuses}
        self.assertTrue(status_map["cutrite_pdf"].ok)
        self.assertTrue(status_map["conj_pdf"].ok)
        self.assertTrue(status_map["projeto_pdf"].ok)
        self.assertTrue(status_map["cnc_source"].ok)
        self.assertTrue(status_map["cnc_work"].ok)
        self.assertTrue(status_map["mpr_year"].ok)
        self.assertTrue(status_map["mpr_sent"].ok)

    def test_collect_preparacao_statuses_only_returns_selected_configurable_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            lista_pdf = work_folder / "Lista_Material_PROC.pdf"
            lista_pdf.write_text("pdf", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            statuses = producao_preparacao.collect_preparacao_statuses(
                context,
                required_keys={"lista_material_pdf", *producao_preparacao.ALWAYS_REQUIRED_KEYS},
            )

        keys = {status.key for status in statuses}
        self.assertIn("lista_material_pdf", keys)
        self.assertNotIn("conj_pdf", keys)
        self.assertNotIn("cutrite_pdf", keys)
        self.assertIn("cnc_source", keys)
        self.assertIn("obra_pronta", keys)

    def test_lista_material_pdf_is_ok_even_when_excel_is_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            pdf_path = work_folder / "Lista_Material_PROC.pdf"
            xlsm_path = work_folder / "Lista_Material_PROC.xlsm"
            pdf_path.write_text("pdf", encoding="utf-8")
            xlsm_path.write_text("excel", encoding="utf-8")
            os.utime(pdf_path, (1_700_000_000, 1_700_000_000))
            os.utime(xlsm_path, (1_700_000_100, 1_700_000_100))

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            statuses = producao_preparacao.collect_preparacao_statuses(
                context,
                required_keys={"lista_material_pdf"},
            )

        status_map = {status.key: status for status in statuses}
        self.assertEqual(status_map["lista_material_pdf"].state, producao_preparacao.STATUS_OK)
        self.assertIn("Lista_Material_PROC.pdf", status_map["lista_material_pdf"].detail)

    def test_caderno_encargos_status_prepares_workbook_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            caderno_path = work_folder / "Caderno de Encargos_PROC.xlsm"
            caderno_path.write_text("excel", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            prepared = producao_preparacao.CadernoEncargosPreparationResult(
                workbook_path=caderno_path,
                image_path=base / "imos" / "PROC.png",
                worksheet_name="CD&RP",
            )
            with patch.object(producao_preparacao, "prepare_caderno_encargos_workbook", return_value=prepared) as prepare_mock:
                statuses = producao_preparacao.collect_preparacao_statuses(
                    context,
                    required_keys={"caderno_encargos"},
                )

        status_map = {status.key: status for status in statuses}
        self.assertEqual(status_map["caderno_encargos"].state, producao_preparacao.STATUS_OK)
        self.assertIn("Imagem IMOS inserida", status_map["caderno_encargos"].detail)
        prepare_mock.assert_called_once()

    def test_caderno_encargos_status_blocks_when_preparation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            caderno_path = work_folder / "Caderno de Encargos_PROC.xlsm"
            caderno_path.write_text("excel", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            with patch.object(
                producao_preparacao,
                "prepare_caderno_encargos_workbook",
                side_effect=RuntimeError("Imagem IMOS em falta"),
            ):
                statuses = producao_preparacao.collect_preparacao_statuses(
                    context,
                    required_keys={"caderno_encargos"},
                )

        status_map = {status.key: status for status in statuses}
        self.assertEqual(status_map["caderno_encargos"].state, producao_preparacao.STATUS_BLOCKED)
        self.assertIn("Imagem IMOS em falta", status_map["caderno_encargos"].detail)

    def test_patch_printer_settings_blob_forces_duplex_long_edge(self):
        blob = bytearray(b"\x00" * 220)
        struct.pack_into("<H", blob, 68, 220)
        struct.pack_into("<I", blob, 72, 0)
        struct.pack_into("<h", blob, 94, 1)

        patched = producao_preparacao._patch_printer_settings_blob(bytes(blob))

        self.assertIsNotNone(patched)
        self.assertEqual(struct.unpack_from("<h", patched, 94)[0], producao_preparacao.DMDUP_VERTICAL)
        self.assertTrue(struct.unpack_from("<I", patched, 72)[0] & producao_preparacao.DM_DUPLEX_FLAG)

    def test_force_caderno_duplex_long_edge_updates_printer_settings_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            workbook_path = Path(tmp) / "caderno.xlsm"
            blob = bytearray(b"\x00" * 220)
            struct.pack_into("<H", blob, 68, 220)
            struct.pack_into("<I", blob, 72, 0)
            struct.pack_into("<h", blob, 94, 1)

            with zipfile.ZipFile(workbook_path, "w") as zf:
                zf.writestr("xl/printerSettings/printerSettings1.bin", bytes(blob))
                zf.writestr("[Content_Types].xml", "<Types/>")

            producao_preparacao._force_caderno_duplex_long_edge(workbook_path)

            with zipfile.ZipFile(workbook_path, "r") as zf:
                patched = zf.read("xl/printerSettings/printerSettings1.bin")

        self.assertEqual(struct.unpack_from("<h", patched, 94)[0], producao_preparacao.DMDUP_VERTICAL)

    def test_try_place_caderno_picture_in_cell_prefers_shape_method(self):
        class _FakeShape:
            def __init__(self) -> None:
                self.select_calls = 0
                self.place_calls = 0

            def Select(self):
                self.select_calls += 1

            def PlacePictureInCell(self):
                self.place_calls += 1

        class _FakeCommandBars:
            def ExecuteMso(self, candidate: str) -> None:
                raise AssertionError("ExecuteMso nao devia ser chamado quando Shape.PlacePictureInCell funciona.")

        fake_shape = _FakeShape()
        fake_excel = SimpleNamespace(CommandBars=_FakeCommandBars())

        result = producao_preparacao._try_place_caderno_picture_in_cell(fake_excel, fake_shape)

        self.assertTrue(result)
        self.assertEqual(fake_shape.select_calls, 1)
        self.assertEqual(fake_shape.place_calls, 1)

    def test_try_place_caderno_picture_in_cell_uses_first_successful_idmso(self):
        executed: list[str] = []

        class _FakeShape:
            def __init__(self) -> None:
                self.select_calls = 0
                self.place_calls = 0

            def Select(self):
                self.select_calls += 1

            def PlacePictureInCell(self):
                self.place_calls += 1
                raise RuntimeError("shape-fail")

        class _FakeCommandBars:
            def ExecuteMso(self, candidate: str) -> None:
                executed.append(candidate)
                if candidate != "PlacePictureInCell":
                    raise RuntimeError("indisponivel")

        fake_shape = _FakeShape()
        fake_excel = SimpleNamespace(CommandBars=_FakeCommandBars())

        with patch.object(
            producao_preparacao,
            "CADERNO_PLACE_IN_CELL_IDMSO_CANDIDATES",
            ("PicturePlaceInCell", "PlacePictureInCell"),
        ):
            result = producao_preparacao._try_place_caderno_picture_in_cell(fake_excel, fake_shape)

        self.assertTrue(result)
        self.assertEqual(executed, ["PicturePlaceInCell", "PlacePictureInCell"])
        self.assertEqual(fake_shape.select_calls, 3)
        self.assertEqual(fake_shape.place_calls, 1)

    def test_try_place_caderno_picture_in_cell_returns_false_when_all_candidates_fail(self):
        executed: list[str] = []

        class _FakeShape:
            def __init__(self) -> None:
                self.place_calls = 0

            def Select(self):
                return None

            def PlacePictureInCell(self):
                self.place_calls += 1
                raise RuntimeError("shape-fail")

        class _FakeCommandBars:
            def ExecuteMso(self, candidate: str) -> None:
                executed.append(candidate)
                raise RuntimeError(candidate)

        fake_excel = SimpleNamespace(CommandBars=_FakeCommandBars())

        with patch.object(
            producao_preparacao,
            "CADERNO_PLACE_IN_CELL_IDMSO_CANDIDATES",
            ("PicturePlaceInCell", "PlacePictureInCell"),
        ):
            result = producao_preparacao._try_place_caderno_picture_in_cell(fake_excel, _FakeShape())

        self.assertFalse(result)
        self.assertEqual(executed, ["PicturePlaceInCell", "PlacePictureInCell"])

    def test_copy_programas_para_obra_copies_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source_root = base / "cnc_root"
            source_folder = source_root / "PROC"
            source_folder.mkdir(parents=True)
            nested = source_folder / "M1"
            nested.mkdir()
            (nested / "p1.mpr").write_text("mpr", encoding="utf-8")
            work_folder = base / "obra"
            work_folder.mkdir()

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=source_root,
                cnc_source_folder=source_folder,
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            output_path = producao_preparacao.copy_programas_para_obra(context)
            self.assertTrue(output_path.is_dir())
            self.assertTrue((output_path / "M1" / "p1.mpr").is_file())

    def test_copy_cutrite_pdf_para_obra_copies_exported_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            cutrite_export_root = base / "cutrite_exports"
            cutrite_export_root.mkdir()
            source_pdf = cutrite_export_root / "PROC_PLANO.pdf"
            source_pdf.write_text("pdf", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
                cutrite_export_root=cutrite_export_root,
            )

            output_path = producao_preparacao.copy_cutrite_pdf_para_obra(context)

            self.assertEqual(output_path, work_folder / "PROC_PLANO.pdf")
            self.assertTrue(output_path.is_file())
            self.assertEqual(output_path.read_text(encoding="utf-8"), "pdf")

    def test_cutrite_pdf_status_is_outdated_when_export_is_newer_than_work_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            target_pdf = work_folder / "PROC_PLANO.pdf"
            target_pdf.write_text("obra", encoding="utf-8")
            cutrite_export_root = base / "cutrite_exports"
            cutrite_export_root.mkdir()
            source_pdf = cutrite_export_root / "PROC_PLANO.pdf"
            source_pdf.write_text("origem", encoding="utf-8")
            os.utime(target_pdf, (1_700_000_000, 1_700_000_000))
            os.utime(source_pdf, (1_700_000_100, 1_700_000_100))

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=work_folder / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
                cutrite_export_root=cutrite_export_root,
            )

            statuses = producao_preparacao.collect_preparacao_statuses(
                context,
                required_keys={"cutrite_pdf", *producao_preparacao.ALWAYS_REQUIRED_KEYS},
            )

        status_map = {status.key: status for status in statuses}
        self.assertEqual(status_map["cutrite_pdf"].state, producao_preparacao.STATUS_OUTDATED)
        self.assertEqual(
            status_map["cutrite_pdf"].action_key,
            producao_preparacao.ACTION_COPY_CUTRITE_PDF_TO_WORK,
        )
        self.assertIn("Desatualizado face a PROC_PLANO.pdf", status_map["cutrite_pdf"].detail)

    def test_send_programas_para_mpr_creates_year_folder_and_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_programs = base / "obra" / "PROC"
            work_programs.mkdir(parents=True)
            (work_programs / "A" / "prog.mpr").parent.mkdir()
            (work_programs / "A" / "prog.mpr").write_text("mpr", encoding="utf-8")

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=base / "obra",
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_programs,
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=base / "obra" / producao_preparacao.CONJ_PDF_FILENAME,
                projeto_pdf_path=base / "obra" / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME,
            )

            output_path = producao_preparacao.send_programas_para_mpr(context)
            self.assertTrue(output_path.is_dir())
            self.assertTrue((output_path / "A" / "prog.mpr").is_file())

    @unittest.skipUnless(__import__("importlib").util.find_spec("reportlab") is not None, "reportlab nao instalado")
    def test_generate_projeto_producao_pdf_creates_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work_folder = base / "obra"
            work_folder.mkdir()
            conj_pdf = work_folder / producao_preparacao.CONJ_PDF_FILENAME
            output_pdf = work_folder / producao_preparacao.PROJETO_PRODUCAO_PDF_FILENAME
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.pdfgen import canvas
            from pypdf import PdfReader

            page_width, page_height = landscape(A3)
            pdf = canvas.Canvas(str(conj_pdf), pagesize=(page_width, page_height))
            pdf.drawString(40, page_height - 40, "Pagina 1")
            pdf.showPage()
            pdf.drawString(40, page_height - 40, "Pagina 2")
            pdf.save()

            context = producao_preparacao.ProducaoPreparacaoContext(
                processo=SimpleNamespace(id=1),
                work_folder=work_folder,
                nome_enc_imos="PROC",
                nome_plano_cut_rite="PROC_PLANO",
                cnc_source_root=base / "cnc_root",
                cnc_source_folder=base / "cnc_root" / "PROC",
                work_programs_folder=work_folder / "PROC",
                mpr_root=base / "mpr_root",
                mpr_year_folder=base / "mpr_root" / "2026_MPR",
                mpr_programs_folder=base / "mpr_root" / "2026_MPR" / "PROC",
                conj_pdf_path=conj_pdf,
                projeto_pdf_path=output_pdf,
            )

            result = producao_preparacao.generate_projeto_producao_pdf(context)
            generated = PdfReader(str(result))

            self.assertEqual(result, output_pdf)
            self.assertTrue(result.is_file())
            self.assertEqual(len(generated.pages), 2)
            self.assertAlmostEqual(float(generated.pages[0].mediabox.width), producao_preparacao.A4_LANDSCAPE_WIDTH_PT, delta=2.0)
            self.assertAlmostEqual(float(generated.pages[0].mediabox.height), producao_preparacao.A4_LANDSCAPE_HEIGHT_PT, delta=2.0)
