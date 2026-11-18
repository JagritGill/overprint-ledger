"""Bounded file loading; examples may encode the raw stream as a JSON string."""

import json
import os
from pathlib import Path
import stat

from .parser import LogError, MAX_BYTES

MAX_FILE_BYTES = 8 * MAX_BYTES


def load_log(path: str | Path, *, json_string: bool = False) -> bytes:
    try:
        source = Path(path)
        if not stat.S_ISREG(source.lstat().st_mode):
            raise LogError("input must be a trusted regular file, not a symlink or device")
        with source.open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise LogError("input must be a regular file")
            raw = stream.read((MAX_FILE_BYTES if json_string else MAX_BYTES) + 1)
    except (OSError, ValueError) as exc:
        if isinstance(exc, LogError):
            raise
        raise LogError("cannot read local input file") from None
    if len(raw) > (MAX_FILE_BYTES if json_string else MAX_BYTES):
        raise LogError("input file exceeds its byte limit")
    if not json_string:
        return raw
    try:
        decoded = json.loads(raw.decode("utf-8"))
        if type(decoded) is not str:
            raise LogError("encoded input must be one JSON string")
        data = decoded.encode("ascii")
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise LogError("invalid JSON string or non-ASCII stream") from None
    if len(data) > MAX_BYTES:
        raise LogError("decoded stream exceeds its byte limit")
    return data
