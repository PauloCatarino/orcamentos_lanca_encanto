from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError

from Martelo_Orcamentos_V2.app import db as db_module


class InitDbSafetyTests(unittest.TestCase):
    def test_init_db_raises_and_never_executes_sql_fallback_when_tables_exist(self):
        with patch.object(db_module.Base.metadata, "create_all", side_effect=SQLAlchemyError("boom")), patch.object(
            db_module, "inspect"
        ) as mock_inspect, patch("builtins.open", side_effect=AssertionError("fallback should not open SQL script")):
            mock_inspect.return_value = MagicMock(get_table_names=MagicMock(return_value=["orcamentos"]))

            with self.assertRaises(SQLAlchemyError):
                db_module.init_db()


if __name__ == "__main__":
    unittest.main()
