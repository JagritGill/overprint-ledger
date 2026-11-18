"""Read-only log audit. Raw control bytes are never replayed to stdout."""

import argparse
import json
import sys

from .core import audit
from .io import load_log
from .parser import LogError


def render(report) -> str:
    lines = [f"bytes={report.source_bytes} lines={len(report.lines)} lost_glyphs={report.lost_glyphs} "
             f"overwritten={report.overwritten_glyphs} erased={report.erased_glyphs}",
             f"destructive_operations={report.destructive_operations} affected_lines={report.affected_lines} "
             f"same_glyph_rewrites={report.same_glyph_rewrites}",
             "gate=FAIL (glyph changes found)" if report.gate_failed else "gate=PASS (supported glyph profile only)"]
    for number, line in enumerate(report.lines, 1):
        lines.append(f"line {number}: {json.dumps(line, ensure_ascii=True)}")
    for change in report.changes:
        lines.append(f"change line={change.line} bytes=[{change.byte_start},{change.byte_end}) "
                     f"kind={change.kind} lost={change.lost_glyphs} omitted_witnesses={change.omitted_witnesses}")
        for witness in change.witnesses:
            lines.append(f"  column={witness.column} prior_byte={witness.prior_byte} "
                         f"{json.dumps(witness.old_glyph)} -> {json.dumps(witness.new_glyph)}")
    if report.omitted_changes:
        lines.append(f"omitted_changes={report.omitted_changes}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trace overwritten/erased glyphs in a bounded ASCII line-log profile.")
    parser.add_argument("input", help="stable local raw log file")
    parser.add_argument("--json-string", action="store_true", help="decode one JSON string containing the stream")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--evidence", type=int, default=20, help="earliest destructive operations retained (0..50)")
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.evidence <= 50:
            raise LogError("evidence must be an integer from 0 through 50")
        result = audit(load_log(args.input, json_string=args.json_string), evidence=args.evidence)
    except LogError as exc:
        print(f"overprint-ledger: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True, allow_nan=False)
          if args.format == "json" else render(result), end="\n" if args.format == "json" else "")
    return int(result.gate_failed)


if __name__ == "__main__":
    raise SystemExit(main())
