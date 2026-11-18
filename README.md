# overprint-ledger

**Keep evidence of text that a log redraw replaced or erased.**

An offline Python CLI for a deliberately small ASCII line-log profile. It reports
final glyph rows **and** a ledger of destructive writes/erasures: modifying byte
spans, previous-writer byte offsets, line/column locations and exact loss counts.
This helps review progress output or explain why a final line differs from earlier
text. It does not classify intent or certify a log as safe.

## Quickstart

From the repository root with installed CPython 3.13 or 3.15, no installation,
network, service or runtime dependency is needed:

```sh
python3 -B -m overprint_ledger examples/status.json --json-string
```

The fixture safely encodes `tests: FAIL\rtests: PASS\n` as a JSON string. Expected
exit **1** and exact output:

```text
bytes=24 lines=1 lost_glyphs=3 overwritten=3 erased=0
destructive_operations=3 affected_lines=1 same_glyph_rewrites=8
gate=FAIL (glyph changes found)
line 1: "tests: PASS"
change line=1 bytes=[19,20) kind=write lost=1 omitted_witnesses=0
  column=8 prior_byte=7 "F" -> "P"
change line=1 bytes=[21,22) kind=write lost=1 omitted_witnesses=0
  column=10 prior_byte=9 "I" -> "S"
change line=1 bytes=[22,23) kind=write lost=1 omitted_witnesses=0
  column=11 prior_byte=10 "L" -> "S"
```

The A was rewritten unchanged, so three glyphs were lost, not four. The other
seven same-glyph rewrites are the `tests: ` prefix. This is evidence of edits,
not proof of deception: ordinary progress output also changes earlier text.

```sh
python3 -B -m overprint_ledger examples/status.json --json-string --format json
python3 -B -m overprint_ledger examples/status.json --json-string --evidence 0 --format json
python3 -B -m overprint_ledger examples/erase.json --json-string
python3 -B -m overprint_ledger examples/unchanged.json --json-string
python3 -B -m overprint_ledger examples/restored.json --json-string
python3 -B -m overprint_ledger --help
```

Status, erase and restored exit 1. Erase removes seven glyphs before writing OK.
Restored returns A to its initial value but retains both A-to-B and B-to-A changes.
Unchanged and help exit 0. `--evidence 0` hides witnesses without changing counts
or the gate. The example harness also exercises an actual raw temporary log:

```sh
python3 -B scripts/check_examples.py
```

For an existing trusted raw file, omit `--json-string`:

```sh
python3 -B -m overprint_ledger capture.log --format json
```

`capture.log` is your input path, not a bundled file. The raw-file form is tested
with a synthetic temporary fixture. Input is read only; controls are never sent
to a terminal. Reports quote glyph rows and use escaped JSON text. They expose
source text and offsets and **are not redacted or anonymized**.

## Exact profile

| Input | Modeled effect |
| --- | --- |
| ASCII bytes 32–126 | Write one glyph at the current column, replacing any cell there; advance one. |
| CR | Return to column 1. |
| BS | Move left one column, clamped at the start; do not erase. |
| TAB | Move to the next 8-column stop; do not write spaces. |
| LF | Finalize the current row and reset to column 1. **An explicit log-profile choice.** |
| `CSI n C`, `CSI n D`, `CSI n G` | Forward, backward, absolute horizontal position. Missing/zero parameter means 1. Backward movement clamps at the start. |
| `CSI 0 K`, `CSI 1 K`, `CSI 2 K` | Erase from cursor right, from start through cursor, or the entire row; cursor unchanged. Missing parameter means 0. |
| `CSI ... m` with only 0, 1, 22, 30–37, 39, 90–97 | Accept reset/bold/basic foreground styling as glyph-neutral; count ignored style operations. |

CSI must use the two bytes ESC followed by `[`. Only the table's subset is
accepted. Unicode, vertical motion, wrapping, OSC links/titles, screen erase,
conceal, background colors and other controls are rejected. There are no hidden
best-effort fallbacks. Accepted styling is not visually modeled: glyph rows say
nothing about contrast, font rendering or actual visibility on a particular terminal.

Rows omit trailing blanks. Empty input has no rows; each LF finalizes a row;
nonempty content after the last LF produces a final row. No extra blank row is
added solely because a stream ends in LF. Cursor movement can create leading
blank gaps when later text is written.

## Counts and evidence

A **lost glyph** is a previously stored non-space character replaced by a
different character or erased. Printing into blank space is not loss. Rewriting
the same character updates last-writer provenance and increments
`same_glyph_rewrites`, without failing the gate. The counter includes explicit
space rewrites. Deleting only spaces does not count as loss.

Counts represent glyph versions, not unique cells: repeated edits to one cell
count repeatedly. Loss history is retained even if a later write restores the
initial text. Each print-byte replacement is one destructive operation; an erase
sequence can lose many glyphs in one operation. Counts remain exact when evidence
is capped. Keep the earliest 0–50 destructive operations (default 20), with at
most eight changed-cell witnesses each, sorted by column within an erasure.

Byte offsets are **zero-based in the raw/decoded stream**, not positions in a JSON
fixture. Operation spans have exclusive ends; lines and columns are one-based.
`prior_byte` identifies the last printable writer of that cell. This is not a
complete history of every identical rewrite. Erasure's replacement glyph is a space.

| Exit | Meaning |
| --- | --- |
| 0 | Valid supported stream with no non-space glyph loss. Not a security verdict. |
| 1 | Glyph replacement/erasure found; complete report emitted. |
| 2 | Invalid, unsupported or over-limit input/argument; no partial report. |

## API and verification

```python
from overprint_ledger import audit

report = audit(b"A\rB\rA\n", evidence=20)
assert report.lines == ("A",)
assert report.lost_glyphs == 2
assert report.gate_failed
```

`audit` accepts immutable bytes. `load_log(path, json_string=False)` reads a file.
`Report.to_dict()` supplies JSON schema version 1. `LogError` identifies invalid
input. There is no source execution or input mutation.

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
python3 -B scripts/check_release.py --json
git diff --check
```

Tests include 2,801 exhaustive streams compared with a dense-cell history oracle,
control grammar/boundary checks and actual CLI invocations. Local runtimes are
Python 3.13.5 and 3.15.0; CI uses standard public GitHub runners for those versions.
Check the actual final-commit workflow result. Release checks cover exact inventory,
local links, Python syntax and selected credential/private-path patterns. They are
not a static type check, full linter or comprehensive disclosure guarantee. No
static checker is configured.

Limits: 65,536 decoded stream bytes, 1,024 columns, 500 rows; encoded input files
at most 524,288 bytes. Trusted stable regular files only; symlinks/devices are
rejected, but malicious path replacement races are not addressed. See
[architecture](docs/architecture.md) for bounds and modeling tradeoffs,
[related work](docs/related-work.md) for close alternatives, [AGENTS](AGENTS.md)
for contribution/handoff rules and [NOTICE](NOTICE.md) for AI assistance and
dependency provenance. Original files use [MIT](LICENSE).
