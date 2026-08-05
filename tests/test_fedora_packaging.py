import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FEDORA_DIR = ROOT / "packaging" / "fedora"


class FedoraPackagingTestCase(unittest.TestCase):
    def test_required_packaging_files_exist(self):
        expected_files = (
            "install.sh",
            "uninstall.sh",
            "io.github.erenynk.CryptoDesk.desktop.in",
            "README.md",
        )

        for file_name in expected_files:
            with self.subTest(file_name=file_name):
                self.assertTrue(
                    (FEDORA_DIR / file_name).is_file(),
                )

    def test_shell_scripts_have_valid_bash_syntax(self):
        bash = shutil.which("bash")

        if bash is None:
            self.skipTest("bash bulunamadı")

        for file_name in ("install.sh", "uninstall.sh"):
            with self.subTest(file_name=file_name):
                result = subprocess.run(
                    [
                        bash,
                        "-n",
                        str(FEDORA_DIR / file_name),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=result.stderr,
                )

    def test_desktop_entry_matches_application_identity(self):
        content = (
            FEDORA_DIR
            / "io.github.erenynk.CryptoDesk.desktop.in"
        ).read_text(encoding="utf-8")

        self.assertIn("Name=Caspian", content)
        self.assertIn("Exec=@EXEC@", content)
        self.assertIn(
            "Icon=io.github.erenynk.CryptoDesk",
            content,
        )
        self.assertIn(
            "StartupWMClass=io.github.erenynk.CryptoDesk",
            content,
        )
        self.assertIn("Terminal=false", content)

    def test_default_uninstall_preserves_user_data(self):
        content = (
            FEDORA_DIR
            / "uninstall.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("PURGE_DATA=false", content)
        self.assertIn('--purge-data', content)
        self.assertIn(
            'if [[ "${PURGE_DATA}" == true ]]',
            content,
        )


if __name__ == "__main__":
    unittest.main()
