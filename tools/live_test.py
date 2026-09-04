"""Live on-desktop integration test (windows platform, ~10 s).

Verifies the real clipboard event loop: the app watches while *waiting*, an
image placed on the system clipboard triggers recognition (fake worker), and
the LaTeX result is written back and readable.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.pop("QT_QPA_PLATFORM", None)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

from furmula.animation import ClipLibrary
from furmula.config import Config, ConfigStore
from furmula.controller import Controller
from furmula.floating import FloatingWindow
from tools.gui_selftest import FakeResult, make_png_bytes  # noqa: E402


def wait_until(fn, timeout, app):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if fn():
            return True
        time.sleep(0.01)
    return False


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    library = ClipLibrary()
    window = FloatingWindow(library)
    window.move_to_corner()
    cfg = Config(api_key="sk-live-test", output_target="word")
    controller = Controller(
        app=app,
        window=window,
        library=library,
        store=ConfigStore(path=os.path.join(ROOT, "tools", "_live_config.json")),
        cfg=cfg,
        settings_factory=None,
        recognizer_factory=lambda png, cfg: FakeResult(
            png, cfg, latex=r"E=mc^2", delay=0.5
        ),
        sfx=None,
    )
    events = []
    controller.event.connect(events.append)
    window.show()
    app.processEvents()
    time.sleep(0.6)

    # 1) toggle to waiting (real state machine)
    controller.on_toggle()
    if not wait_until(lambda: controller.state == "waiting", 10, app):
        print("FAIL never reached waiting; events:", events)
        controller.shutdown()
        return 1
    print("OK  waiting after sleeping2waiting (on desktop)")

    # 2) place an image onto the *real* clipboard -> should auto-trigger
    img = QImage(240, 60, QImage.Format_RGB32)
    img.fill(0xFFFFFFFF)
    app.clipboard().setImage(img)
    # the QImage above is blank white; content doesn't matter for the fake worker
    if not wait_until(lambda: controller.state == "working", 6, app):
        print("FAIL never entered working; events:", events)
        controller.shutdown()
        return 1
    print("OK  clipboard image detected -> working")

    # 3) verify clipboard as soon as the recognition result is written
    import win32clipboard

    ok_text = False
    has_html = False
    end = time.time() + 25
    while time.time() < end and not (ok_text and has_html):
        app.processEvents()
        if not any(e.startswith("recognize:ok") for e in events):
            time.sleep(0.02)
            continue
        text = ""
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            fmt = win32clipboard.RegisterClipboardFormat("HTML Format")
            has_html = win32clipboard.IsClipboardFormatAvailable(fmt)
        finally:
            win32clipboard.CloseClipboard()
        if "E=mc^2" in text.replace(" ", ""):
            ok_text = True
        if not (ok_text and has_html):
            time.sleep(0.2)
    print("OK  clipboard contains formula" if ok_text else "FAIL clipboard text missing")
    print("OK  word/html format present" if has_html else "FAIL html format missing")

    # wait for the full choreography back to waiting
    if not wait_until(lambda: controller.state == "waiting", 30, app):
        print("FAIL never returned to waiting; events:", events)
        controller.shutdown()
        return 1
    print("OK  returned to waiting")

    controller.shutdown()
    print("live test done; events:", [e for e in events if e.startswith(("transition", "recognize", "state"))])
    return 0 if (ok_text and has_html) else 1


if __name__ == "__main__":
    sys.exit(main())
