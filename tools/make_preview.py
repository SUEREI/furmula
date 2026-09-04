"""Render the main UI states to PNG previews (offscreen, no desktop flash).

Outputs into data/preview_*.png so the user can eyeball layout/theming
without running the live app. Also a handy build-time regression probe.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication

from furmula.animation import ClipLibrary
from furmula.config import Config
from furmula.floating import FloatingWindow
from furmula.settings_dialog import SettingsDialog


def pump(app, seconds):
    from time import sleep

    end = __import__("time").time() + seconds
    while __import__("time").time() < end:
        app.processEvents()
        sleep(0.01)


def main():
    app = QApplication(sys.argv)
    library = ClipLibrary()
    library.ensure(
        ["sleeping2waiting", "waitting2sleeping", "waiting2working",
         "working", "working2waiting"]
    )
    w = FloatingWindow(library)
    w.show()
    pump(app, 1.5)  # let clips decode in background

    out_dir = os.path.join(ROOT, "data", "preview")
    os.makedirs(out_dir, exist_ok=True)

    def snap(state, name):
        if state == "sleeping":
            w.set_state("sleeping")
        elif state == "waiting":
            w.set_state("waiting")
        elif state == "working":
            w.set_status("working")
            w.play_loop("working")
        pump(app, 0.5)
        w.grab().save(os.path.join(out_dir, f"{name}.png"))
        print("saved", name)

    snap("sleeping", "sleeping")
    snap("waiting", "waiting")
    snap("working", "working")

    dlg = SettingsDialog(Config(api_key="sk-demo"), parent=w)
    dlg.show()
    pump(app, 0.4)
    dlg.grab().save(os.path.join(out_dir, "settings.png"))
    print("saved settings")
    dlg.close()
    w.close()
    print("previews in", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
