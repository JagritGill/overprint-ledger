"""An explicit small control grammar, not a permissive ANSI stripper."""

from dataclasses import dataclass

MAX_BYTES = 65_536
MAX_SEQUENCE = 32
SGR = {0, 1, 22, 39, *range(30, 38), *range(90, 98)}


class LogError(ValueError):
    """Unsupported or malformed input; never echo raw control bytes."""


@dataclass(frozen=True)
class Operation:
    kind: str
    value: int
    start: int
    end: int


def operations(data: bytes):
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise LogError(f"input must be bytes, at most {MAX_BYTES} bytes")
    index = 0
    simple = {8: "backspace", 9: "tab", 10: "newline", 13: "return"}
    while index < len(data):
        start = index
        byte = data[index]
        index += 1
        if 32 <= byte <= 126:
            yield Operation("write", byte, start, index)
        elif byte in simple:
            yield Operation(simple[byte], 0, start, index)
        elif byte == 27:
            if index >= len(data) or data[index] != 91:
                raise LogError(f"byte {start}: only the documented CSI subset is supported")
            index += 1
            parameter_start = index
            while index < len(data) and (48 <= data[index] <= 57 or data[index] == 59):
                index += 1
                if index - start >= MAX_SEQUENCE:
                    raise LogError(f"byte {start}: CSI exceeds {MAX_SEQUENCE} bytes")
            if index >= len(data) or index - start + 1 > MAX_SEQUENCE:
                raise LogError(f"byte {start}: incomplete or oversized CSI")
            final = data[index]
            params = data[parameter_start:index].split(b";")
            index += 1
            if any(len(p) > 4 for p in params):
                raise LogError(f"byte {start}: CSI parameters must be at most four digits")
            values = [int(p) if p else 0 for p in params]
            if final == 109 and all(v in SGR for v in values):
                yield Operation("style", 0, start, index)
            elif len(values) == 1 and final in (67, 68, 71):
                kind = {67: "forward", 68: "backward", 71: "absolute"}[final]
                yield Operation(kind, values[0] or 1, start, index)
            elif len(values) == 1 and final == 75 and values[0] in (0, 1, 2):
                yield Operation("erase", values[0], start, index)
            else:
                raise LogError(f"byte {start}: unsupported CSI command or parameters")
        else:
            raise LogError(f"byte {start}: unsupported byte value {byte}; ASCII line-log profile only")
