import re
from pathlib import Path
path = Path('Martelo_Orcamentos_V2/ui/pages/dados_gerais.py')
text = path.read_text(encoding='utf-8')
pattern = r"    def _carregar_tipos_familias\(self\) -> None:\n(?:.*?\n)*?    def _post_table_setup"
replacement = "    def _carregar_tipos_familias(self) -> None:\n\n        try:\n            self._tipos_cache = svc_mp.listar_tipos(self.session)\n        except Exception:\n            self._tipos_cache = []\n\n        try:\n            familias_map = svc_mp.mapear_tipos_por_familia(self.session)\n        except Exception:\n            familias_map = {}\n\n        self._tipos_por_familia = familias_map\n\n        default_familias = {\n            value\n            for value in (self.svc.MENU_DEFAULT_FAMILIA.get(menu) for menu in self.tab_order)\n            if value\n        }\n\n        todas = default_familias.union(familias_map.keys())\n        if not todas:\n            todas = {\"PLACAS\"}\n\n        self._familias_cache = sorted(todas)\n\n    def _post_table_setup"
text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
if count != 1:
    raise SystemExit('pattern replacement failed')
path.write_text(text, encoding='utf-8')
