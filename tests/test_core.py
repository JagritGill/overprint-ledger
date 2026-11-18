from itertools import product
import unittest

from overprint_ledger import LogError, audit
from overprint_ledger.core import MAX_COLUMNS, MAX_LINES
from overprint_ledger.parser import MAX_BYTES, operations


class CoreTests(unittest.TestCase):
    def test_status_change_provenance(self):
        r = audit(b'tests: FAIL\rtests: PASS\n')
        self.assertEqual(r.lines, ('tests: PASS',))
        self.assertEqual((r.lost_glyphs, r.same_glyph_rewrites, r.affected_lines), (3, 8, 1))
        self.assertEqual([c.byte_start for c in r.changes], [19, 21, 22])
        self.assertEqual([c.witnesses[0].prior_byte for c in r.changes], [7, 9, 10])
        self.assertEqual([c.witnesses[0].column for c in r.changes], [8, 10, 11])

    def test_erase_provenance_and_cap(self):
        r = audit(b'abcdefghijk\r\x1b[2K')
        c = r.changes[0]
        self.assertEqual((r.erased_glyphs, r.destructive_operations), (11, 1))
        self.assertEqual((c.byte_start, c.byte_end, c.omitted_witnesses), (12, 16, 3))
        self.assertEqual([w.prior_byte for w in c.witnesses], list(range(8)))
        self.assertEqual(r.lines, ('',))

    def test_erase_modes_include_cursor_and_do_not_move_it(self):
        for mode, expected, loss in [(0, 'ab', 3), (1, '   de', 3), (2, '', 5)]:
            r = audit(b'abcde\x1b[3G\x1b[' + str(mode).encode() + b'K')
            self.assertEqual((r.lines, r.erased_glyphs), ((expected,), loss))
        self.assertEqual(audit(b'abc\r\x1b[2CX\x1b[KZ').lines, ('abXZ',))

    def test_same_glyph_updates_last_writer(self):
        r = audit(b'A\rA\rB')
        self.assertEqual((r.same_glyph_rewrites, r.lost_glyphs), (1, 1))
        self.assertEqual(r.changes[0].witnesses[0].prior_byte, 2)

    def test_restoration_retains_history(self):
        r = audit(b'A\rB\rA')
        self.assertEqual(r.lines, ('A',))
        self.assertEqual(r.lost_glyphs, 2)
        self.assertTrue(r.gate_failed)

    def test_spaces_are_not_lost_glyphs(self):
        r = audit(b' \rA\r \r\x1b[2K')
        self.assertEqual((r.overwritten_glyphs, r.erased_glyphs), (1, 0))
        self.assertEqual(r.changes[0].witnesses[0].new_glyph, ' ')
        self.assertEqual(r.lines, ('',))

    def test_line_profile_and_tabs(self):
        self.assertEqual(audit(b'A\nB').lines, ('A', 'B'))  # Explicit LF reset.
        self.assertEqual(audit(b'\n\n').lines, ('', ''))
        self.assertEqual(audit(b'').lines, ())
        self.assertEqual(audit(b'\r').lines, ('',))
        self.assertEqual(audit(b'A\tB').lines, ('A       B',))
        self.assertEqual(audit(b'\b\bA\bB').lines, ('B',))
        self.assertEqual(audit(b'A\r\nB\r\n').lines, ('A', 'B'))

    def test_motion_defaults_and_style(self):
        self.assertEqual(audit(b'AB\x1b[DX').lines, ('AX',))
        self.assertEqual(audit(b'AB\x1b[0DX').lines, ('AX',))
        self.assertEqual(audit(b'AB\x1b[99DX').lines, ('XB',))
        self.assertEqual(audit(b'A\x1b[CX').lines, ('A X',))
        self.assertEqual(audit(b'AB\x1b[0GX').lines, ('XB',))
        r = audit(b'\x1b[1;32mOK\x1b[m\rOK')
        self.assertEqual((r.ignored_styles, r.same_glyph_rewrites, r.gate_failed), (2, 2, False))

    def test_truncation_never_changes_gate(self):
        data = b'AB\rCD\rEF'
        full, hidden = audit(data, evidence=50), audit(data, evidence=0)
        self.assertEqual(full.lost_glyphs, hidden.lost_glyphs)
        self.assertEqual(hidden.changes, ())
        self.assertEqual(hidden.omitted_changes, 4)
        self.assertTrue(hidden.gate_failed)

    def test_byte_column_and_line_limits(self):
        for data in [b'x' * (MAX_BYTES + 1), 'text', bytearray(b'A')]:
            with self.assertRaises(LogError):
                audit(data)
        self.assertEqual(len(audit(b'A' * MAX_COLUMNS).lines[0]), MAX_COLUMNS)
        for data in [b'A' * (MAX_COLUMNS + 1), b'\x1b[9999G', b'\x1b[1025CA', b'\n' * (MAX_LINES + 1)]:
            with self.assertRaises(LogError):
                audit(data)
        self.assertEqual(len(audit(b'\n' * MAX_LINES).lines), MAX_LINES)
        self.assertEqual(audit(b'A' * MAX_COLUMNS + b'\rB').overwritten_glyphs, 1)
        for value in [True, -1, 51, '1', 1.0]:
            with self.assertRaises(LogError):
                audit(b'', evidence=value)

    def test_unsupported_and_malformed_controls(self):
        for data in [b'\x00', b'\x07', b'\x7f', b'\xff', '☃'.encode(), b'\x1b', b'\x1b[',
                     b'\x1b]8;;url\x07', b'\x1b[2J', b'\x1b[1A', b'\x1b[8m', b'\x1b[40m',
                     b'\x1b[?25l', b'\x1b[1;2C', b'\x1b[3K', b'\x1b[12345C',
                     b'\x1b[' + b';' * 40 + b'm', b'\x1b[12', b'\x1b[1\x00m']:
            with self.subTest(data=repr(data)), self.assertRaises(LogError) as ctx:
                audit(data)
            self.assertNotIn('\x1b', str(ctx.exception))

    def test_parser_spans(self):
        ops = list(operations(b'A\x1b[2K\r'))
        self.assertEqual([(o.kind, o.start, o.end) for o in ops], [('write', 0, 1), ('erase', 1, 5), ('return', 5, 6)])

    def test_exhaustive_dense_cell_history_oracle(self):
        # Dense cells and explicit byte histories; independent of sparse-map replay.
        alphabet = [b'A', b'B', b'\r', b'\b', b'\n', b'\x1b[2K', b'\x1b[2G']
        cases = 0
        for length in range(5):
            for tokens in product(alphabet, repeat=length):
                cells = [None] * 8
                col = 0
                rows = []
                byte = 0
                touched = False
                changes = []
                overwrite = erase = same = 0
                for token in tokens:
                    touched = True
                    witnesses = []
                    if token in (b'A', b'B'):
                        glyph = token.decode()
                        old = cells[col]
                        if old:
                            if old[0] == glyph:
                                same += 1
                            else:
                                overwrite += 1
                                witnesses = [(col + 1, old[0], old[1], glyph)]
                        cells[col] = (glyph, byte)
                        col += 1
                    elif token == b'\r':
                        col = 0
                    elif token == b'\b':
                        col = max(0, col - 1)
                    elif token == b'\x1b[2G':
                        col = 1
                    elif token == b'\x1b[2K':
                        witnesses = [(i+1, c[0], c[1], ' ') for i, c in enumerate(cells) if c]
                        erase += len(witnesses)
                        cells = [None] * 8
                    else:
                        rows.append(''.join(c[0] if c else ' ' for c in cells).rstrip())
                        cells = [None] * 8
                        col = 0
                        touched = False
                    if witnesses:
                        changes.append((len(rows)+1, byte, byte+len(token), witnesses))
                    byte += len(token)
                if touched:
                    rows.append(''.join(c[0] if c else ' ' for c in cells).rstrip())
                report = audit(b''.join(tokens), evidence=50)
                self.assertEqual(report.lines, tuple(rows))
                self.assertEqual((report.overwritten_glyphs, report.erased_glyphs, report.same_glyph_rewrites), (overwrite, erase, same))
                actual = [(c.line, c.byte_start, c.byte_end,
                           [(w.column,w.old_glyph,w.prior_byte,w.new_glyph) for w in c.witnesses]) for c in report.changes]
                self.assertEqual(actual, changes)
                self.assertEqual(report.gate_failed, bool(overwrite + erase))
                cases += 1
        self.assertEqual(cases, 2801)


if __name__ == '__main__':
    unittest.main()
