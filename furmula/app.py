"""Application bootstrap: single instance, QApplication, theme, wiring."""
import os
import sys

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from . import paths
from .audio import SfxPlayer
from .animation import ClipLibrary
from .config import ConfigStore
from .controller import Controller
from .floating import FloatingWindow
from .settings_dialog import SettingsDialog
from .theme import QSS, app_palette


def _ensure_single_instance() -> bool:
    try:
        import win32event
        import win32api

        mutex = win32event.CreateMutex(None, False, "Furmula_Single_Instance_Mutex")
        return win32api.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True  # non-Windows / degraded: allow


def main(argv=None) -> int:
    from .logging_setup import ensure_logging

    ensure_logging()
    if not _ensure_single_instance():
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "Furmula 已经在运行了。\n可以在右下角悬浮窗查看。",
                "Furmula",
                0x40,
            )
        except Exception:
            pass
        return 0

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Furmula")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(QSS)
    app.setPalette(app_palette())
    icon = QIcon(paths.icon("app.ico"))
    app.setWindowIcon(icon)

    store = ConfigStore()
    cfg = store.load()

    library = ClipLibrary()
    window = FloatingWindow(library)
    sfx = SfxPlayer()

    controller = Controller(
        app=app,
        window=window,
        library=library,
        store=store,
        cfg=cfg,
        settings_factory=lambda: SettingsDialog(controller.cfg, parent=window),
        sfx=sfx,
    )
    window.show()
    smoke = "--smoke" in (argv if argv is not None else sys.argv)
    if smoke:
        from PyQt5.QtCore import QTimer

        def _smoke_exit():
            controller.shutdown()
            print("SMOKE OK")

        QTimer.singleShot(4000, _smoke_exit)
    code = app.exec_()
    # A recogniser request may still be mid-flight; never let interpreter
    # shutdown hang on a non-daemon worker thread -> hard exit in that case.
    try:
        if controller.job_is_running():
            os._exit(0)
    except Exception:
        pass
    return code


if __name__ == "__main__":
    sys.exit(main())
