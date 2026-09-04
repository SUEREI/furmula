"""Integration self-test for Furmula (runs headless with the offscreen plugin).

Walks the real Controller + FloatingWindow + ClipLibrary stack with a fake
recognizer, verifying the state-machine choreography:
  sleeping --click--> (sleeping2waiting) --> waiting --new image--> working
  --(waiting2working, working loop, boundary)--> working2waiting --> waiting
and the reverse toggle, plus failure handling and click lockouts.
"""
import io
import os
import sys
import time
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_ERRLOG = os.path.join(ROOT, "tools", "_selftest_err.txt")


def _excepthook(typ, val, tb):
    with open(_ERRLOG, "a", encoding="utf-8") as f:
        f.write("".join(traceback.format_exception(typ, val, tb)))
    traceback.print_exception(typ, val, tb)


sys.excepthook = _excepthook

from PyQt5.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QMouseEvent, QPixmap
from PyQt5.QtWidgets import QApplication

from furmula.animation import ClipLibrary, load_frames
from furmula.config import Config, ConfigStore
from furmula.controller import Controller
from furmula.floating import FloatingWindow
from furmula.settings_dialog import SettingsDialog

PASS = 0
FAIL = 0
LOG = []


def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        LOG.append(f"  ok   - {label}")
    else:
        FAIL += 1
        LOG.append(f"  FAIL - {label}")


def make_png_bytes(w=80, h=60, color=(255, 0, 0)):
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(0xFFFFFFFF)
    return _png(img)


def _png(img):
    from PyQt5.QtCore import QBuffer, QIODevice

    b = QBuffer()
    b.open(QIODevice.WriteOnly)
    img.save(b, "PNG")
    data = bytes(b.data())
    b.close()
    return data


class FakeResult(QObject):
    """Worker-shaped stub that emits a result after a delay (real QThread)."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, png_bytes, cfg, *, latex="x^2+1", fail_msg=None, delay=0.5):
        super().__init__()
        self.latex = latex
        self.fail_msg = fail_msg
        self.delay = delay
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        if self.fail_msg:
            time.sleep(self.delay)
            self.failed.emit(self.fail_msg)
        else:
            time.sleep(self.delay)
            self.succeeded.emit(self.latex)


class Harness:
    def __init__(self, fail=False, delay=0.35, api_key="sk-test-fake", settings_factory=None):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.library = ClipLibrary()
        self.window = FloatingWindow(self.library)
        self.cfg = Config(api_key=api_key)
        self.events = []
        self.state_seen = []
        self.settings_opened = []
        self.settings_dialog = None

        def _factory():
            return settings_factory() if settings_factory else None

        self.controller = Controller(
            app=self.app,
            window=self.window,
            library=self.library,
            store=ConfigStore(path=os.path.join(ROOT, "tools", "_test_config.json")),
            cfg=self.cfg,
            settings_factory=_factory,
            recognizer_factory=lambda png, cfg: FakeResult(
                png, cfg, fail_msg=("boom" if fail else None), delay=delay
            ),
            sfx=None,
        )
        if settings_factory:
            # emulate a real settings dialog object (parented for safe teardown)
            self.settings_dialog = settings_factory()
            self.settings_dialog.setParent(self.window)
            self.controller._settings_dialog = self.settings_dialog
            self.settings_dialog.saved.connect(self.controller._apply_settings)
        self.controller.event.connect(self.events.append)
        self.controller.state_changed.connect(self.state_seen.append)
        self.window.show()

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def wait_state(self, want, timeout):
        end = time.time() + timeout
        while time.time() < end:
            self.app.processEvents()
            if self.controller.state == want:
                return True
            time.sleep(0.01)
        return self.controller.state == want

    def wait_phase(self, want, timeout):
        end = time.time() + timeout
        while time.time() < end:
            self.app.processEvents()
            if self.controller.phase == want:
                return True
            time.sleep(0.01)
        return self.controller.phase == want


def main():
    # ---- cache sanity -------------------------------------------------- #
    print("[0] frame caches")
    for clip in ("sleeping2waiting", "waitting2sleeping", "waiting2working",
                 "working", "working2waiting"):
        n = len(load_frames(clip))
        check(n > 30, f"{clip} has frames ({n})")

    # ---- scenario A: sleeping -> waiting -> screenshot -> working -> waiting
    print("[A] sleeping -> waiting -> recognition -> waiting")
    h = Harness()
    check(h.controller.state == "sleeping" and h.controller.phase == "idle",
          "starts sleeping/idle")

    # toggle to waiting; immediate second click must be ignored
    h.controller.on_toggle()
    h.controller.on_toggle()          # should be ignored (busy/lock)
    check(h.wait_state("waiting", 12), "reaches waiting after transition")
    assert "state:waiting" in h.events
    check(h.controller.phase == "idle", "idle again after transition")
    LOG.append(f"    timeline: {[e for e in h.events if not e.startswith('recognize')]}")

    # simulate a fresh screenshot while waiting
    before = len(h.events)
    h.controller._start_recognition(make_png_bytes())
    check(h.controller.state == "working", "enters working immediately")
    check(h.wait_state("waiting", 25), "returns to waiting after full choreography")
    ok_evt = any(e.startswith("recognize:ok") for e in h.events[before:])
    check(ok_evt, "recognise succeeded")
    LOG.append(f"    work timeline: {h.events[before:]}")
    h.controller.shutdown()

    # ---- scenario B: toggle back to sleeping ----------------------------
    print("[B] waiting -> sleeping")
    h = Harness()
    h.controller.on_toggle()
    h.wait_state("waiting", 12)
    h.controller.on_toggle()
    check(h.wait_state("sleeping", 12), "back to sleeping via waitting2sleeping")
    h.controller.shutdown()

    # ---- scenario C: failure path ----------------------------------------
    print("[C] recognition failure")
    h = Harness(fail=True)
    h.controller.on_toggle()
    h.wait_state("waiting", 12)
    h.controller._start_recognition(make_png_bytes())
    check(h.wait_state("waiting", 25), "returns to waiting after failure")
    check(any(e.startswith("recognize:error") for e in h.events), "error recorded")
    h.controller.shutdown()

    # ---- scenario D: toggles ignored while working ----------------------
    print("[D] lockout during working")
    h = Harness(delay=2.5)
    h.controller.on_toggle()
    h.wait_state("waiting", 12)
    h.controller._start_recognition(make_png_bytes())
    check(h.controller.state == "working", "working now")
    n_trans = len([e for e in h.events if e.startswith("transition:")])
    h.controller.on_toggle()          # must be ignored
    h.pump(0.3)
    same = [e for e in h.events if e.startswith("transition:")]
    check(len(same) == n_trans and h.controller.state == "working",
          "toggle ignored while working")
    check(h.wait_state("waiting", 30), "still returns to waiting later")
    h.controller.shutdown()

    # ---- scenario E: click lockout 2 s -----------------------------------
    print("[E] 2 s lockout")
    h = Harness()
    h.controller._lock_until = 0.0
    h.controller.on_toggle()          # accepted (sleeping -> waiting clip)
    n = len([e for e in h.events if e.startswith("transition:")])
    h.pump(0.15)                       # mid-transition, click again
    h.controller.on_toggle()
    h.pump(0.1)
    check(
        len([e for e in h.events if e.startswith("transition:")]) == n,
        "click during transition ignored",
    )
    check(h.wait_state("waiting", 12), "waiting after first toggle")
    # from waiting, click within lock window must be ignored
    h.controller._lock_until = time.monotonic() + 5
    n = len([e for e in h.events if e.startswith("transition:")])
    h.controller.on_toggle()
    h.pump(0.1)
    check(
        len([e for e in h.events if e.startswith("transition:")]) == n
        and h.controller.state == "waiting",
        "click inside lockout window ignored",
    )
    h.controller.shutdown()

    # ---- scenario F: no API key -> settings auto-opens on toggle ----------
    print("[F] missing key auto-opens settings")
    h = Harness(api_key="", settings_factory=lambda: SettingsDialog(Config(api_key="")))
    check(h.controller.state == "sleeping", "sleeping at start")
    h.controller.on_toggle()
    h.pump(0.3)
    check(any(e == "toggle:no-key" for e in h.events), "toggle refused: no key")
    check(h.controller.state == "sleeping", "still sleeping (no transition)")
    check(h.settings_dialog.isVisible(), "settings dialog popped up")
    # now fill the key and toggle again -> allowed
    h.settings_dialog.key_edit.setText("sk-fixed")
    h.settings_dialog._save()
    h.controller.on_toggle()
    check(h.wait_state("waiting", 12), "reaches waiting once key present")
    h.controller.shutdown()

    # ---- scenario G: settings apply live -----------------------------------
    print("[G] settings round-trip")
    h = Harness(settings_factory=lambda: SettingsDialog(Config(api_key="sk-x")))
    dlg = h.settings_dialog
    dlg.rb_word.setChecked(True)
    dlg.vol_slider.setValue(33)
    dlg.sound_check.setChecked(False)
    dlg.key_edit.setText("sk-applied")
    dlg._save()
    check(h.controller.cfg.output_target == "word", "target word applied")
    check(h.controller.cfg.volume == 33, "volume applied")
    check(not h.controller.cfg.sound_enabled, "sound disabled applied")
    check(h.controller.cfg.api_key == "sk-applied", "key applied")
    check(h.window.target_label.text() == "Word", "badge shows Word")
    h.controller.shutdown()

    # ---- scenario H: sleeping does not listen ------------------------------
    print("[H] clipboard ignored while sleeping")
    h = Harness()
    probe_img = QImage(40, 40, QImage.Format_RGB32)
    probe_img.fill(0xFFFFFFFF)
    h.app.clipboard().setImage(probe_img)
    h.controller._on_clipboard_changed()
    h.pump(0.3)
    check(not any(e.startswith("recognize:start") for e in h.events)
          and h.controller.state == "sleeping", "image ignored while sleeping")
    h.controller.on_toggle()
    h.wait_state("waiting", 12)
    h.app.clipboard().setImage(probe_img)
    h.controller._on_clipboard_changed()
    h.pump(0.3)
    check(h.controller.state == "working", "image triggers while waiting")
    h.controller.shutdown()

    # ---- scenario I: window visual settings + drag -------------------------
    print("[I] size/opacity/drag")
    h = Harness()
    w = h.window
    w.apply_visual(140, 60)
    h.pump(0.1)
    check(w.width() == 375, f"resized to 140% ({w.width()}px)")
    check(abs(w.windowOpacity() - 0.6) < 0.01, "opacity set to 60%")
    # drag: press centre, move, release -> moves but does NOT toggle
    before_pos = (w.pos().x(), w.pos().y())
    base = w.mapToGlobal(QPoint(w.width() // 2, w.height() // 2))
    drag = QMouseEvent(QEvent.MouseButtonPress, QPointF(30, 30), base,
                       Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(w.stage, drag)
    for dx in (5, 15, 30):
        mv = QMouseEvent(QEvent.MouseMove, QPointF(30 + dx, 30 + dx),
                         base + QPoint(dx, dx), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(w.stage, mv)
        h.pump(0.02)
    rel = QMouseEvent(QEvent.MouseButtonRelease, QPointF(60, 60),
                      base + QPoint(30, 30), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(w.stage, rel)
    h.pump(0.15)
    moved = (w.pos().x(), w.pos().y()) != before_pos
    check(moved, "window moved by drag")
    check(h.controller.state == "sleeping"
          and not any(e.startswith("transition:") for e in h.events),
          "drag did not toggle state")
    w.apply_visual(100, 100)   # restore
    h.controller.shutdown()

    print(f"\n==== PASSED {PASS} / {PASS + FAIL} ====")
    for line in LOG:
        print(line)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
