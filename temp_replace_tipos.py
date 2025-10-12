from pathlib import Path
path = Path('Martelo_Orcamentos_V2/ui/pages/dados_gerais.py')
text = path.read_text(encoding='utf-8')
pre, remainder = text.split('    def _carregar_tipos_familias(self) -> None:\n', 1)
old_body, rest = remainder.split('    def _post_table_setup', 1)
new_body = "    def _carregar_tipos_familias(self) -> None:\n\n\n\n        try:\n\n\n\n            self._tipos_cache = svc_mp.listar_tipos(self.session)\n\n\n\n        except Exception:\n\n\n\n            self._tipos_cache = []\n\n\n\n        try:\n\n\n\n            familias_map = svc_mp.mapear_tipos_por_familia(self.session)\n\n\n\n        except Exception:\n\n\n\n            familias_map = {}\n\n\n\n        self._tipos_por_familia = familias_map\n\n\n\n        default_familias = {\n\n\n\n            value\n\n\n\n            for value in (self.svc.MENU_DEFAULT_FAMILIA.get(menu) for menu in self.tab_order)\n\n\n\n            if value\n\n\n\n        }\n\n\n\n        todas = default_familias.union(familias_map.keys())\n\n\n\n        if not todas:\n\n\n\n            todas = {\"PLACAS\"}\n\n\n\n        self._familias_cache = sorted(todas)\n\n\n\n"
text = pre + new_body + '    def _post_table_setup' + rest
path.write_text(text, encoding='utf-8')
