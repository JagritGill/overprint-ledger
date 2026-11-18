# Architecture and tradeoffs

## Parser and replay

`parser.py` walks bytes and yields immutable operations with source spans. It
accepts only printable ASCII, CR/BS/TAB/LF and the documented CSI subset. A CSI
is at most 32 bytes; each numeric parameter is at most four digits. Unsupported
commands, malformed sequences and arbitrary high bytes stop the audit. Parsing
is not a permissive regex removal pass. Controls never execute in a terminal.

`core.py` holds a sparse current-row map: zero-based column to `(glyph, writer
byte)`. A printable write replaces the cell and updates its writer. If the old
glyph was non-space and differs, the old glyph and writer enter the loss ledger.
Same-character rewrites update writer provenance but are counted separately.
An erase removes cells in its selected interval, collecting at most eight prior
non-space glyph witnesses and counting every loss. Erase does not move the cursor.

Rows finalize on LF and the cursor resets to zero. This is a **line-log profile**,
not terminal LF behavior in every mode. Finished rows cannot be revisited. The
row is serialized through its last stored column, with missing cells as spaces
and trailing spaces trimmed. EOF finalizes only a nonempty suffix of operations.
No newline-only trailing row is invented.

`__main__.py` emits a report only after the complete audit succeeds. It quotes
row strings and glyphs with JSON escaping; output contains no raw source control
bytes. Numeric error positions avoid echoing unsupported bytes as characters.
Argparse may still echo invalid command-line arguments. No HTML rendering or
security sanitization promise is made for downstream consumers of reports.

## Bounded evidence and resource use

Keep the earliest at most 50 destructive operations, eight witnesses each. Exact
loss counts and the gate do not depend on retained evidence. Later restoration
does not retract earlier losses. `affected_lines` counts distinct changed rows.
Counts are versions lost, not distinct characters/cells. Prior-byte provenance
points to the most recent printable write, including same-glyph rewrites; it does
not provide a full ancestry chain through all identical writes.

At most 65,536 input stream bytes, 500 output rows and 1,024 columns are supported.
Cursor positions 0..1,024 are permitted internally; position 1,024 is a one-past
sentinel where another write fails. A return/backward move or LF may leave it.
The profile never clamps rightward motion or wraps silently. Tabs use the next
multiple of eight; exceeding the cursor bound is an error.

Erasure sorts currently stored column keys, so worst-case work is proportional
to the number of erase operations times C log C, plus input processing and row
serialization, where C<=1,024. Retained cells are bounded by C, rows by 500*C
characters, and witnesses by 50*8. These are design bounds, not performance claims.

`io.py` reads one bounded buffer from a trusted stable local regular file. Raw
input is capped at 65,536 bytes. Optional JSON-string fixtures allow up to eight
times that file size before decoding, then enforce the original stream cap and
ASCII encoding. The bounded JSON tree is parsed before checking it is a string;
decoder recursion/encoding errors are rejected. The file check/open sequence is
not a defense against malicious concurrent path replacement.

## Interpretation and limitations

These are glyph values under a restricted profile. Accepted foreground/bold
style operations do not alter glyphs, but appearance can differ on a real screen.
Non-ASCII text, Unicode widths, concealment, vertical motion, terminal resizing,
wrapping, screen/alternate-buffer control and OSC sequences are out of scope.
Rejecting them avoids claiming a faithful partial rendering. A pass is not a
safe/clean/malicious verdict; legitimate progress bars may fail the edit gate.

The evidence cannot reconstruct bytes missing from an already-cleaned capture,
prove a capture is authentic, or tell whether an edit was intended. Reports can
disclose removed source text and are not anonymized. Do not use private logs in
examples or tests. Similar render/audit tools are acknowledged in
[related work](related-work.md), especially reizan-ansigate's broader audit.

## Verification

Checked-in tests enumerate 2,801 token streams against an independent dense-cell
model with explicit writer histories. Focused cases cover all supported movement
and erase modes, profile defaults, bounds, same-glyph provenance, restored text,
parser failures, raw/encoded input and actual CLI output. Release guard mutations
use synthetic temporary trees. [README](../README.md) lists runnable commands;
[AGENTS](../AGENTS.md) supplies contribution boundaries and handoff requirements.
No static checker is configured; syntax parsing is explicitly not type checking.
