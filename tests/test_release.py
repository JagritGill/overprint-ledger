import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_check',ROOT/'scripts/check_release.py')
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in checker.FILES:
            target=self.root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)

    def test_current_inventory(self):
        self.assertEqual(checker.check(self.root)['files'],23)

    def test_unexpected_file_and_symlink(self):
        path=self.root/'extra'
        path.write_text('synthetic')
        with self.assertRaises(ValueError):checker.check(self.root)
        path.unlink()
        target=self.root/'README.md'
        target.unlink()
        target.symlink_to(self.root/'NOTICE.md')
        with self.assertRaises(ValueError):checker.check(self.root)

    def test_secret_private_path_link_and_raw_control(self):
        target=self.root/'README.md'
        for text in ['gh'+'p_'+'a'*36,'/'+'Users/example/private','[broken](absent.md)','raw'+chr(27)]:
            target.write_text(text)
            with self.assertRaises(ValueError):checker.check(self.root)

    def test_syntax_and_mode(self):
        target=self.root/'overprint_ledger/core.py'
        target.write_text('def bad(:\n')
        with self.assertRaises(SyntaxError):checker.check(self.root)
        target.write_text('pass\n')
        target.chmod(0o755)
        with self.assertRaises(ValueError):checker.check(self.root)


if __name__=='__main__':unittest.main()
