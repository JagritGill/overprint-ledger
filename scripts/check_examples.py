"""Verify documented examples, expected findings and raw-file input safely."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, code):
    p = subprocess.run([sys.executable, '-B', '-m', 'overprint_ledger', *args], cwd=ROOT,
                       capture_output=True, check=False)
    if p.returncode != code or p.stderr or any(b != 10 and not 32 <= b <= 126 for b in p.stdout):
        raise SystemExit('example exit/output check failed')
    return p.stdout.decode('ascii')


def main():
    cases = [(['examples/status.json','--json-string'],1),
             (['examples/status.json','--json-string','--format','json'],1),
             (['examples/status.json','--json-string','--evidence','0','--format','json'],1),
             (['examples/erase.json','--json-string'],1),
             (['examples/unchanged.json','--json-string'],0),
             (['examples/restored.json','--json-string'],1),
             (['--help'],0)]
    for args, code in cases:
        output = run(args, code)
        if args == cases[0][0] and output != (ROOT/'examples/status.txt').read_text():
            raise SystemExit('example text snapshot mismatch')
        if '--format' in args and json.loads(output)['lost_glyphs'] != 3:
            raise SystemExit('example count mismatch')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'capture.log'
        path.write_bytes(b'tests: FAIL\rtests: PASS\n')
        result=json.loads(run([str(path),'--format','json'],1))
        if result['lost_glyphs'] != 3 or result['lines'] != ['tests: PASS']:
            raise SystemExit('raw example mismatch')
    print('8 CLI examples passed, including raw-file input and expected finding exits')


if __name__ == '__main__':
    main()
