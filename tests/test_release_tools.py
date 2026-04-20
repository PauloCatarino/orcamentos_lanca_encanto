from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from Martelo_Orcamentos_V2.release_tools import (
    bump_semver,
    find_installer_output,
    read_static_app_version,
    write_static_app_version,
)


class ReleaseToolsTests(unittest.TestCase):
    def test_bump_semver(self) -> None:
        self.assertEqual(bump_semver("2.2.2", "patch"), "2.2.3")
        self.assertEqual(bump_semver("2.2.2", "minor"), "2.3.0")
        self.assertEqual(bump_semver("2.2.2", "major"), "3.0.0")

    def test_read_and_write_static_app_version(self) -> None:
        contents = 'ENV_APP_VERSION = "MARTELO_APP_VERSION"\nAPP_VERSION = "2.2.2"\n'
        version_file = Mock(spec=Path)

        def fake_read_text(*, encoding: str) -> str:
            self.assertEqual(encoding, "utf-8")
            return contents

        def fake_write_text(new_text: str, *, encoding: str) -> int:
            nonlocal contents
            self.assertEqual(encoding, "utf-8")
            contents = new_text
            return len(new_text)

        version_file.read_text.side_effect = fake_read_text
        version_file.write_text.side_effect = fake_write_text

        self.assertEqual(read_static_app_version(version_file), "2.2.2")
        write_static_app_version("2.2.3", version_file)
        self.assertEqual(read_static_app_version(version_file), "2.2.3")

    def test_find_installer_output_uses_matching_version(self) -> None:
        older = Mock(spec=Path)
        older.stat.return_value.st_mtime = 1
        newer = Mock(spec=Path)
        newer.stat.return_value.st_mtime = 2
        output_dir = Mock(spec=Path)
        output_dir.glob.return_value = [older, newer]

        self.assertIs(find_installer_output("2.2.3", output_dir), newer)
        output_dir.glob.assert_called_once_with("Setup_*_2.2.3.exe")


if __name__ == "__main__":
    unittest.main()
