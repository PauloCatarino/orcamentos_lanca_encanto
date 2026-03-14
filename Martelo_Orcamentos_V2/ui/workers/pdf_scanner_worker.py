from __future__ import annotations

from typing import Optional

from PySide6 import QtCore

from Martelo_Orcamentos_V2.app.services import pdf_scanner


class PDFScannerWorker(QtCore.QObject):
    finished = QtCore.Signal(list, str)

    def __init__(
        self,
        *,
        folder_path: str,
        nome_plano_cut_rite: Optional[str],
        nome_enc_imos_ix: Optional[str],
        recursive: bool = False,
    ) -> None:
        super().__init__()
        self._folder_path = folder_path
        self._nome_plano_cut_rite = nome_plano_cut_rite
        self._nome_enc_imos_ix = nome_enc_imos_ix
        self._recursive = recursive

    @QtCore.Slot()
    def run(self) -> None:
        try:
            rows = pdf_scanner.scan_folder(
                self._folder_path,
                nome_plano_cut_rite=self._nome_plano_cut_rite,
                nome_enc_imos_ix=self._nome_enc_imos_ix,
                recursive=self._recursive,
            )
            self.finished.emit(rows, "")
        except Exception as exc:  # pragma: no cover - runtime safeguard
            self.finished.emit([], str(exc))
