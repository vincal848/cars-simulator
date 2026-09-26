"""Crash reports. The Windows build has no console, so an uncaught error would
otherwise close the game without a trace; instead it is appended to crash.log."""

import platform
import sys
import traceback
from datetime import datetime

from cars import __version__
from cars.paths import crash_log_path

# Keep the log from growing without bound; older reports are trimmed first.
MAX_LOG_CHARACTERS = 200_000


def format_report(error: BaseException) -> str:
    stack = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    lines = [
        f"=== C.A.R.S. {__version__} crashed at {datetime.now().isoformat(timespec='seconds')} ===",
        f"Python {platform.python_version()} on {platform.platform()}",
        f"Arguments: {sys.argv[1:]}",
        "",
        stack,
    ]
    return "\n".join(lines)


def write_report(error: BaseException) -> str:
    """Append a report for ``error`` to the crash log and return the log's path."""
    path = crash_log_path()
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    text = (previous + format_report(error) + "\n")[-MAX_LOG_CHARACTERS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)
