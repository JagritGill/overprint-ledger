import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from overprint_ledger import LogError, load_log
from overprint_ledger.io import MAX_FILE_BYTES
from overprint_ledger.parser import MAX_BYTES

ROOT = Path(__file__).resolve().parents[1]


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'input'

    def test_raw_and_encoded_streams_agree(self):
        stream = b'FAIL\rPASS\x1b[0m\n'
        self.path.write_bytes(stream)
        self.assertEqual(load_log(self.path), stream)
        self.path.write_text(json.dumps(stream.decode()))
        self.assertEqual(load_log(self.path, json_string=True), stream)

    def test_file_kind_and_read_errors(self):
        for path in [self.path, Path(self.temp.name)]:
            with self.assertRaises(LogError):
                load_log(path)
        self.path.write_bytes(b'A')
        link = Path(self.temp.name) / 'link'
        link.symlink_to(self.path)
        with self.assertRaises(LogError):
            load_log(link)

    def test_encoded_json_and_bounds(self):
        for raw in [b'\xff', b'{}', b'[]', b'null', b'NaN', b'"\\ud800"', b'"\\u2603"', b'"bad', b'\xef\xbb\xbf"A"']:
            self.path.write_bytes(raw)
            with self.assertRaises(LogError):
                load_log(self.path, json_string=True)
        self.path.write_bytes(b'A' * MAX_BYTES)
        self.assertEqual(len(load_log(self.path)), MAX_BYTES)
        self.path.write_bytes(b'A' * (MAX_BYTES + 1))
        with self.assertRaises(LogError):
            load_log(self.path)
        self.path.write_text(json.dumps('A' * (MAX_BYTES + 1)))
        with self.assertRaises(LogError):
            load_log(self.path, json_string=True)
        self.path.write_bytes(b' ' * (MAX_FILE_BYTES + 1))
        with self.assertRaises(LogError):
            load_log(self.path, json_string=True)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        p = subprocess.run([sys.executable, '-B', '-m', 'overprint_ledger', *args],
                           cwd=ROOT, capture_output=True, check=False)
        self.assertTrue(all(b == 10 or 32 <= b <= 126 for b in p.stdout), p.stdout)
        self.assertNotIn(b'\x1b', p.stderr)
        return p

    def test_status_json(self):
        p = self.run_cli('examples/status.json', '--json-string', '--format', 'json')
        self.assertEqual(p.returncode, 1, p.stderr)
        report = json.loads(p.stdout)
        self.assertEqual(report['lost_glyphs'], 3)
        self.assertEqual(report['lines'], ['tests: PASS'])
        self.assertEqual(report['changes'][0]['witnesses'][0]['prior_byte'], 7)

    def test_text_snapshot_and_example_exits(self):
        p = self.run_cli('examples/status.json', '--json-string')
        self.assertEqual(p.stdout.decode(), (ROOT/'examples/status.txt').read_text())
        for name, expected in [('erase',1),('unchanged',0),('restored',1)]:
            self.assertEqual(self.run_cli(f'examples/{name}.json','--json-string').returncode,expected)
        self.assertEqual(self.run_cli('--help').returncode,0)

    def test_raw_file_and_safe_output(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'log'
            path.write_bytes(b'A\rB\n')
            p = self.run_cli(str(path), '--format', 'json')
            self.assertEqual(p.returncode,1)
            self.assertEqual(json.loads(p.stdout)['lost_glyphs'],1)
            path.write_bytes(b'A\rB\x1b[2J')
            p = self.run_cli(str(path))
            self.assertEqual(p.returncode,2)
            self.assertEqual(p.stdout,b'')

    def test_invalid_arguments_no_partial_output(self):
        for args in [[],['absent'],['examples/status.json','--evidence','-1'],
                     ['examples/status.json','--evidence','x'],['examples/status.json','--format','xml']]:
            p=self.run_cli(*args)
            self.assertEqual(p.returncode,2)
            self.assertEqual(p.stdout,b'')
            self.assertNotIn(b'Traceback',p.stderr)

    def test_hidden_evidence_preserves_findings(self):
        p=self.run_cli('examples/status.json','--json-string','--evidence','0','--format','json')
        r=json.loads(p.stdout)
        self.assertEqual(p.returncode,1)
        self.assertEqual(r['changes'],[])
        self.assertEqual(r['omitted_changes'],3)

    def test_oversized_json_integer_is_invalid_input_not_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'invalid.json'
            path.write_text('1'*5000)
            p=self.run_cli(str(path),'--json-string')
            self.assertEqual(p.returncode,2)
            self.assertEqual(p.stdout,b'')
            self.assertNotIn(b'Traceback',p.stderr)
            self.assertIn(b'overprint-ledger:',p.stderr)


if __name__ == '__main__':
    unittest.main()
