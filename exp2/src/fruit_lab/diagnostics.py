"""Detailed failures stay in ignored local reports, outside public sources."""

from datetime import datetime
from pathlib import Path
import re
import traceback


ERROR_LOG = Path(__file__).resolve().parents[2] / "report" / "fruit_lab_error.log"


def redact_paths(text):
    home = str(Path.home())
    for value in (home, home.replace("\\", "/")):
        text = re.sub(re.escape(value), "<USER_HOME>", text, flags=re.IGNORECASE)
    return text


def failure_summary(exc):
    first_line = next((line.strip() for line in str(exc).splitlines() if line.strip()), "未知原因")
    return f"{type(exc).__name__}: {redact_paths(first_line)[:160]}"


def record_failure(exc):
    try:
        ERROR_LOG.parent.mkdir(exist_ok=True)
        with ERROR_LOG.open("a", encoding="utf-8") as stream:
            stream.write("\n" + datetime.now().astimezone().isoformat(timespec="seconds") + "\n")
            detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            stream.write(redact_paths(detail))
        return True
    except OSError:
        return False
