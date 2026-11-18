"""Replay a no-wrap line-log profile and retain destructive-operation evidence."""

from dataclasses import asdict, dataclass

from .parser import LogError, operations

MAX_COLUMNS = 1024
MAX_LINES = 500
MAX_EVIDENCE = 50
WITNESSES_PER_CHANGE = 8


@dataclass(frozen=True)
class Witness:
    column: int
    old_glyph: str
    prior_byte: int
    new_glyph: str


@dataclass(frozen=True)
class Change:
    line: int
    kind: str
    byte_start: int
    byte_end: int
    lost_glyphs: int
    witnesses: tuple[Witness, ...]
    omitted_witnesses: int


@dataclass(frozen=True)
class Report:
    source_bytes: int
    operations: int
    ignored_styles: int
    overwritten_glyphs: int
    erased_glyphs: int
    same_glyph_rewrites: int
    destructive_operations: int
    affected_lines: int
    lines: tuple[str, ...]
    changes: tuple[Change, ...]
    omitted_changes: int

    @property
    def lost_glyphs(self) -> int:
        return self.overwritten_glyphs + self.erased_glyphs

    @property
    def gate_failed(self) -> bool:
        return self.lost_glyphs > 0

    def to_dict(self) -> dict:
        return {"schema_version": 1, **asdict(self), "lost_glyphs": self.lost_glyphs,
                "gate_failed": self.gate_failed}


def audit(data: bytes, *, evidence: int = 20) -> Report:
    """Inspect raw bytes without executing controls or mutating input.

    LF finalizes the current row and resets the column; there is no wrap or
    vertical addressing. A loss means replacement/erasure of a non-space glyph
    by a different glyph. Same-character rewrites update writer provenance.
    """
    if type(evidence) is not int or not 0 <= evidence <= MAX_EVIDENCE:
        raise LogError(f"evidence must be an integer from 0 through {MAX_EVIDENCE}")
    cells: dict[int, tuple[str, int]] = {}
    column = 0
    rows: list[str] = []
    changes: list[Change] = []
    touched = False
    op_count = styles = overwritten = erased = same = destructive = 0
    affected: set[int] = set()

    def finish_line() -> None:
        if len(rows) >= MAX_LINES:
            raise LogError(f"rendered log exceeds {MAX_LINES} lines")
        extent = max(cells, default=-1) + 1
        rows.append("".join(cells.get(c, (" ", 0))[0] for c in range(extent)).rstrip(" "))

    for op in operations(data):
        op_count += 1
        if len(rows) >= MAX_LINES:
            raise LogError(f"byte {op.start}: log exceeds {MAX_LINES} lines")
        touched = True
        losses: list[Witness] = []
        loss_count = 0
        if op.kind == "write":
            if column >= MAX_COLUMNS:
                raise LogError(f"byte {op.start}: write exceeds {MAX_COLUMNS} columns; wrapping is unsupported")
            glyph = chr(op.value)
            old = cells.get(column)
            if old is not None and old[0] == glyph:
                same += 1
            elif old is not None and old[0] != " ":
                overwritten += 1
                loss_count = 1
                losses.append(Witness(column + 1, old[0], old[1], glyph))
            cells[column] = (glyph, op.start)
            column += 1
        elif op.kind == "erase":
            targets = sorted(c for c in cells if op.value == 2 or
                             (op.value == 0 and c >= column) or (op.value == 1 and c <= column))
            for c in targets:
                old, origin = cells.pop(c)
                if old != " ":
                    erased += 1
                    loss_count += 1
                    if len(losses) < WITNESSES_PER_CHANGE:
                        losses.append(Witness(c + 1, old, origin, " "))
        elif op.kind == "newline":
            finish_line()
            cells = {}
            column = 0
            touched = False
        elif op.kind == "return":
            column = 0
        elif op.kind == "backspace":
            column = max(0, column - 1)
        elif op.kind == "tab":
            column = (column // 8 + 1) * 8
        elif op.kind == "absolute":
            column = op.value - 1
        elif op.kind == "forward":
            column += op.value
        elif op.kind == "backward":
            column = max(0, column - op.value)
        elif op.kind == "style":
            styles += 1
        if column > MAX_COLUMNS:
            raise LogError(f"byte {op.start}: cursor exceeds the {MAX_COLUMNS}-column profile")
        if loss_count:
            destructive += 1
            line = len(rows) + 1
            affected.add(line)
            if len(changes) < evidence:
                changes.append(Change(line, op.kind, op.start, op.end, loss_count,
                                      tuple(losses), loss_count - len(losses)))
    if touched:
        finish_line()
    return Report(len(data), op_count, styles, overwritten, erased, same, destructive,
                  len(affected), tuple(rows), tuple(changes), destructive - len(changes))
