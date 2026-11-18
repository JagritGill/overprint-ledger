"""Local inventory, syntax, documentation-target and heuristic disclosure checks."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import unquote, urlsplit

FILES = frozenset('''
.github/workflows/ci.yml
.gitignore
AGENTS.md
LICENSE
NOTICE.md
README.md
docs/architecture.md
docs/related-work.md
examples/status.json
examples/status.txt
examples/erase.json
examples/unchanged.json
examples/restored.json
overprint_ledger/__init__.py
overprint_ledger/__main__.py
overprint_ledger/core.py
overprint_ledger/io.py
overprint_ledger/parser.py
scripts/check_examples.py
scripts/check_release.py
tests/test_core.py
tests/test_cli_io.py
tests/test_release.py
'''.split())
SENSITIVE = [r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?' + r'PRIVATE KEY-----',
             r'gh[pousr]_' + r'[A-Za-z0-9]{30,}', r'github_pat_' + r'[A-Za-z0-9_]{30,}',
             r'AKIA' + r'[A-Z0-9]{16}', r'/' + r'Users/[^/\s]+/', r'/' + r'home/[^/\s]+/']


def check(root: Path) -> dict:
    found = set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        parent=Path(directory)
        if any((parent/n).is_symlink() for n in dirs+names):
            raise ValueError('symlink in release tree')
        dirs[:]=[d for d in dirs if d not in {'.git','__pycache__','out'}]
        found.update((parent/n).relative_to(root).as_posix() for n in names if not n.endswith('.pyc'))
    if found != FILES:
        raise ValueError(f'inventory mismatch: missing={sorted(FILES-found)}, extra={sorted(found-FILES)}')
    hashes={}
    links=syntax=0
    for name in sorted(FILES):
        path=root/name
        mode=path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o111:
            raise ValueError(f'non-regular or executable release entry: {name}')
        raw=path.read_bytes()
        if len(raw)>128_000 or any(b<32 and b not in (9,10) for b in raw) or 127 in raw:
            raise ValueError(f'oversized file or raw control byte: {name}')
        text=raw.decode('utf-8')
        if any(re.search(pattern,text) for pattern in SENSITIVE):
            raise ValueError(f'credential/private-path pattern: {name}')
        if name.endswith('.py'):
            ast.parse(text,filename=name)
            syntax+=1
        if name.endswith('.md'):
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if urlsplit(target).scheme:
                    continue
                relative=unquote(target.split('#',1)[0])
                if relative:
                    resolved=(path.parent/relative).resolve()
                    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
                        raise ValueError(f'broken or escaping Markdown target: {name}')
                    links+=1
        hashes[name]=hashlib.sha256(raw).hexdigest()
    return {'files':len(hashes),'local_links':links,'python_syntax_files':syntax,'sha256':hashes,
            'limits':'Heuristic inventory scan, not comprehensive provenance/secrets safety, static typing or external-link verification.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    try:
        result=check(Path(__file__).resolve().parents[1])
    except (ValueError,OSError,SyntaxError) as exc:
        raise SystemExit(f'release check failed: {exc}') from None
    print(json.dumps(result,indent=2) if args.json else
          f"release checks passed: {result['files']} files, {result['local_links']} local links, "
          f"{result['python_syntax_files']} Python syntax files; heuristic scan only")


if __name__=='__main__':
    main()
