"""Launch the lab with an input prompt and no startup messages."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys

from .diagnostics import ERROR_LOG, record_failure, redact_paths


def main():
    # ManimGL parses CLI arguments on import. Run the same scene without its
    # version-printing CLI wrapper; retain optional ManimGL flags.
    sys.argv = [sys.argv[0], str(Path(__file__).with_name("scene.py")), "FruitLabScene", *sys.argv[1:]]
    startup = StringIO()
    try:
        # IPython determines terminal capabilities at import time, before any
        # stream redirection; otherwise completion falls back to a plain prompt.
        import IPython.terminal.interactiveshell

        # Limit redirection to dependency imports so the live terminal keeps
        # its real console output and completion menu.
        with redirect_stdout(startup), redirect_stderr(startup):
            from manimlib.__main__ import run_scenes
        run_scenes()
    except Exception as exc:
        record_failure(exc)
    finally:
        if startup.getvalue():
            try:
                ERROR_LOG.parent.mkdir(exist_ok=True)
                with ERROR_LOG.open("a", encoding="utf-8") as stream:
                    stream.write(redact_paths(startup.getvalue()))
            except OSError:
                pass


if __name__ == "__main__":
    main()
