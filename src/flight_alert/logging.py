from __future__ import annotations

from datetime import datetime
import sys


def log(message: str, *, error: bool = False, **kwargs: object) -> None:
    stream = sys.stderr if error else sys.stdout
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    flush = bool(kwargs.get("flush", True))
    print(f"{timestamp} {message}", file=stream, flush=flush)
