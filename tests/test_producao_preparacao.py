import tempfile
import unittest
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
            )

            statuses = producao_preparacao.collect_preparacao_statuses(context)

        status_map = {status.key: status for status in statuses}
        self.assertTrue(status_map["conj_pdf"].ok)
        self.assertTrue(status_map["projeto_pdf"].ok)
        self.assertTrue(status_map["cnc_source"].ok)
        self.assertTrue(status_map["cnc_work"].ok)
        self.assertTrue(status_map["mpr_year"].ok)
        self.assertTrue(status_map["mpr_sent"].ok)

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
