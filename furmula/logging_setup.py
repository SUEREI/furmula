"""Minimal crash-proof logging: everything lands in data/furmula.log.

PyQt5 aborts the process when a Python exception escapes an event handler
(silently under pythonw), so every Qt callback in Furmula is wrapped and any
exception is recorded here instead of killing the app.
"""
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

from . import paths

LOGGER = logging.getLogger("furmula")
_INITIALIZED = False


def ensure_logging():
    global _INITIALIZED
    if _INITIALIZED:
        return LOGGER
    _INITIALIZED = True
    LOGGER.setLevel(logging.INFO)
    try:
        os.makedirs(os.path.join(paths.ROOT, "data"), exist_ok=True)
        log_path = os.path.join(paths.ROOT, "data", "furmula.log")
        fh = RotatingFileHandler(
            log_path, maxBytes=400_000, backupCount=2, encoding="utf-8"
        )
    except OSError:
        fh = None
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    if fh:
        fh.setFormatter(fmt)
        LOGGER.addHandler(fh)
    if sys.stderr is not None:      # only when a console exists
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        LOGGER.addHandler(ch)

    def _excepthook(typ, val, tb):
        LOGGER.error("Unhandled exception:\n%s", "".join(traceback.format_exception(typ, val, tb)))
        sys.__excepthook__(typ, val, tb)

    sys.excepthook = _excepthook

    def _unraisable(arg):
        LOGGER.error(
            "Unraisable %r: %s",
            arg.object,
            "".join(traceback.format_exception(arg.exc_type, arg.exc_value, arg.exc_traceback))
            if arg.exc_traceback
            else f"{arg.exc_type.__name__}: {arg.exc_value}",
        )

    sys.unraisablehook = _unraisable
    return LOGGER


def log_exc(context: str):
    """Log the current exception with context; call inside except blocks."""
    LOGGER.error("%s failed:\n%s", context, traceback.format_exc())
