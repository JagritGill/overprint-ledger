# Related work and independent implementation

Research date: 2026-11-18, before code. Searches included:

- `terminal log auditor overwritten text carriage return backspace ansi log hidden output tool github`
- `ANSI terminal log forensic overwrite history pyte ansifilter`
- `"terminal" "overwritten" "history" "audit" ANSI log tool`
- `ANSI log detect carriage return backspace hidden text sanitizer tool`
- `"overprint-ledger"`

Local catalog and public personal repository names were also reviewed. Search
does not establish global novelty or prove repository-name availability.

## Material overlap and deliberate scope

| Primary source | What overlaps | Focus of this project |
| --- | --- | --- |
| [reizan-ansigate](https://pypi.org/project/reizan-ansigate/) | **Closest audit comparator.** Its published description compares raw and rendered streams, detects concealment-capable ANSI/invisible Unicode and reports deterministic hidden-instruction findings. | A narrow per-change ledger: byte offsets of prior writers and modifying operations, replaced/erased glyph counts, and bounded witnesses. No instruction classifier, intent verdict, Unicode analysis or claim to replace its broader detection. |
| [ghostty-logger](https://github.com/pshickeydev/ghostty-logger) | Resolves carriage returns, backspaces and basic movements when creating rendered plain-text session logs. It documents limits to log integrity. | Read an existing file only; preserve evidence of destructive character edits instead of running a PTY/shell or collecting live sessions. |
| [pyte documentation](https://pyte.readthedocs.io/en/latest/) and [tutorial](https://pyte.readthedocs.io/en/latest/tutorial.html) | An in-memory terminal emulator with stream/screen behavior, text buffers and attributes. | A small explicitly restricted line-log profile with strict rejection of unsupported input and no full terminal claims. No pyte code/dependency used. |
| [TextArray Strip ANSI](https://textarray.com/strip-ansi) | Browser cleanup can collapse carriage-return redraws to final line states. | Report changes that final-only cleanup can omit, with source offsets and a CLI gate. This is a scope comparison, not exhaustive testing of its features. |
| [Ansifilter's official project page](https://sourceforge.net/projects/ansifilter/) | Strips or interprets ANSI sequences for formatted output. | Character-loss evidence rather than format conversion. The author's separate documentation page timed out; comparison is limited to the official project description. |

Rendering controls, showing raw-versus-rendered differences and auditing hidden
text are established ideas. This project claims neither global novelty nor feature
absence in those alternatives. The meaningful scope is a bounded review artifact:
identify the prior glyph writer, modifying byte, line/column and exact loss count,
including erased text and changes later restored. Cosmetic same-glyph rewrites
are counted separately and do not fail the glyph-change gate.

## Semantics, example and provenance

[XTerm control-sequence documentation](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html)
was consulted for CR, BS, tab, horizontal positioning and erase-line concepts.
Our LF-reset/no-wrap ASCII profile is deliberately narrower and explicitly
defined in [architecture](architecture.md); it is not a faithful terminal model.

The synthetic example replaces `tests: FAIL` with `tests: PASS` using a carriage
return. Final glyphs alone show PASS, while the ledger retains three changed-cell
witnesses (the A was rewritten unchanged). A separate erase example shows why
counting just the final text is insufficient. Neither example is a malicious-intent
classification, and ordinary progress output can legitimately contain changes.

No comparator implementation, fixture, test or documentation prose was copied or
translated. The code, synthetic data and tests are independently written with AI
assistance. No private/employer/customer log is used. Runtime uses Python's standard
library only. Routine portfolio release conventions and verified CI pins are
reused with attribution in [NOTICE](../NOTICE.md); no external code is vendored.
