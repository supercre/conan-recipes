"""일괄 export가 별도 SDK 레시피를 게시하지 않는지 확인한다."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export.py"
spec = importlib.util.spec_from_file_location("recipe_export", SCRIPT)
recipe_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe_export)


class ManualExportTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        for name, manual in (("fmod", True), ("zlib", False)):
            folder = self.root / "recipes" / name
            (folder / "all").mkdir(parents=True)
            (folder / "all/conanfile.py").write_text("# fixture\n")
            (folder / "config.yml").write_text(
                'versions:\n  "1.0":\n    folder: all\n'
                + ("manual_export: true\n" if manual else ""))
        for name, value in (("ROOT", str(self.root)), ("RECIPES", str(self.root / "recipes"))):
            patcher = patch.object(recipe_export, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_bulk_upload_keeps_ordinary_recipes_and_skips_manual_sdk(self):
        with patch("sys.argv", [str(SCRIPT), "--upload"]), \
                patch.object(recipe_export.subprocess, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            run.return_value.returncode = 0
            recipe_export.main()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(2, len(commands))
        self.assertEqual(["conan", "export"], commands[0][:2])
        self.assertEqual(str(self.root / "recipes/zlib/all"), commands[0][2])
        self.assertEqual(["conan", "upload", "zlib/1.0@sc/dev"], commands[1][:3])

    def test_explicit_manual_target_fails_before_any_export_or_upload(self):
        for target in ("fmod", "fmod/1.0"):
            with self.subTest(target=target), \
                    patch("sys.argv", [str(SCRIPT), "zlib", target, "--upload"]), \
                    patch.object(recipe_export.subprocess, "run") as run, \
                    contextlib.redirect_stderr(io.StringIO()) as error:
                with self.assertRaises(SystemExit) as result:
                    recipe_export.main()
                self.assertEqual(2, result.exception.code)
                self.assertIn("별도 SDK", error.getvalue())
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
