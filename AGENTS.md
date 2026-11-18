# Working on overprint-ledger

Purpose: bounded evidence of glyph replacement/erasure in ASCII line logs.
Read [README](README.md), [architecture](docs/architecture.md) and
[related work](docs/related-work.md). It is not a full terminal or intent detector.

Map: `parser.py` validates the strict byte/control grammar; `core.py` tracks cells,
last-writer offsets and immutable evidence; `io.py` loads local files;
`__main__.py` formats escaped reports. `examples/` are JSON-encoded synthetic
streams. `tests/` contain independent definitions, boundaries and subprocess
checks. `scripts/` verify examples and release scope. CI uses standard public
GitHub runners with pinned actions and read-only permissions.

Invariants: source byte spans are zero-based/exclusive-end in the decoded stream;
line/column evidence is one-based. LF resets column by explicit profile choice.
No wrap, Unicode widths or vertical motion. Never silently skip unsupported bytes
or replay raw controls to output. Loss counts non-space glyph versions, not unique
cells or malicious instructions. Same-glyph writes update provenance without
failing the gate. Erasure evidence retains prior writer offsets. Evidence caps
must not change totals/gate; later restoration must not erase historical losses.

Commands from repo root, with installed Python and no installation step:

```sh
python3 -B -m unittest discover -s tests -v
python3.13 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
python3 -B scripts/check_release.py --json
git diff --check
```

Local target interpreters: Python 3.15.0 and 3.13.5. Actual verification is recorded
in the handoff; do not infer pass status from commands or CI configuration. No
static checker/full linter configured; syntax parsing is neither. Documented loss
examples exit 1 intentionally, invalid input exits 2 without partial report.

Preserve owner edits and other repos. No private/customer logs, credentials,
CodeRabbit/external reviewers, paid tools, live terminals, hardware, shell/PTY
capture, network features or account changes. Publication requires applicable task
authorization. Do not bypass failing CI or permissions. Use synthetic fixtures,
an independent oracle and actual CLI regressions for semantic changes. Do not
broaden the control grammar without defining and testing its limits.

Keep release inventory and linked docs accurate. Handoff with exact commit,
dirty files, executed checks, expected exits, unrun checks and limitations. Keep
machine-specific evidence outside public source. See [NOTICE](NOTICE.md) and
[LICENSE](LICENSE) before introducing third-party material.
