"""Furmula state controller.

sleeping --(click, plays sleeping2waiting)--> waiting --(click, plays
waitting2sleeping)--> sleeping.

waiting + fresh screenshot --> working: play waiting2working, then loop
working until the recogniser answers, finish the *current full loop*, play
working2waiting and settle back into waiting.

Click toggles are locked for 2 s after each accepted click, and clicks are
ignored while a transition/loop is running.
"""
import functools
import time

from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal

from . import clipboard
from .api_client import RecognizeWorker
from .config import Config, ConfigStore
from .formula import ClipPayload, build_word_payload, clean_latex
from .logging_setup import log_exc

TOGGLE_LOCK_SECONDS = 2.0


def _now():
    return time.monotonic()


def _guarded(label):
    """Never let a Qt-slot exception reach PyQt (which would abort the app).

    The exception is logged; if the machine is mid-recognition we fall back
    to the safe 'waiting' state so the user can simply try again.
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except Exception:
                log_exc(f"controller.{label}")
                try:
                    if getattr(self, "_state", None) == "working":
                        self._finish_pending = False
                        self._phase = "idle"
                        self._state = "waiting"
                        self.window.set_state("waiting")
                        self.state_changed.emit("waiting")
                except Exception:
                    pass
                return None

        return wrapper

    return deco


class Controller(QObject):
    """Owns the state machine, clipboard listener, recogniser jobs & SFX."""

    state_changed = pyqtSignal(str)      # sleeping | waiting | working
    # NOTE: never name a pyqtSignal "event" — it shadows QObject.event() and
    # every child-object event then raises "native Qt signal is not callable".
    note_event = pyqtSignal(str)         # coarse instrumentation for self-tests

    def __init__(
        self,
        app,
        window,
        library,
        store: ConfigStore,
        cfg: Config,
        settings_factory=None,
        recognizer_factory=None,
        sfx=None,
        parent=None,
    ):
        super().__init__(parent)
        self._app = app
        self.window = window
        self.library = library
        self.store = store
        self.cfg = cfg
        self._settings_factory = settings_factory or (lambda: None)
        self._recognizer_factory = recognizer_factory or self._default_recognizer
        self.sfx = sfx

        self._state = "sleeping"
        self._phase = "idle"        # idle | transition | loop
        self._lock_until = 0.0
        self._finish_pending = False
        self._ignore_clipboard_until = 0.0
        self._thread: QThread | None = None
        self._worker = None
        self._settings_dialog = None

        window.toggle_requested.connect(self.on_toggle)
        window.settings_requested.connect(self.open_settings)
        window.quit_requested.connect(self.shutdown)
        window.stage.once_finished.connect(self._on_clip_done)
        window.stage.loop_stopped.connect(self._on_loop_stopped)
        window.set_target_text(cfg.output_target)
        window.apply_visual(cfg.window_scale, cfg.window_opacity)

        # preload the clips that sleeping/waiting toggling needs
        library.ensure(
            ["sleeping2waiting", "waitting2sleeping", "waiting2working",
             "working", "working2waiting"]
        )
        # clipboard listener
        app.clipboard().dataChanged.connect(self._on_clipboard_changed)

    # ---------------------------------------------------------------- #
    @property
    def state(self):
        return self._state

    @property
    def phase(self):
        return self._phase

    # ---------------------------------------------------------------- #
    # -- user gestures ------------------------------------------------- #
    @_guarded("on_toggle")
    def on_toggle(self):
        if self._phase != "idle":
            self._note("toggle-ignored:busy")
            return
        if _now() < self._lock_until:
            self._note("toggle-ignored:lock")
            return
        if self._state == "sleeping":
            if not self.cfg.api_key.strip():
                self._note("toggle:no-key")
                self.window.show_toast("还没有填写 API Key，请先完成设置", kind="info")
                self.open_settings()
                return
            self._lock_until = _now() + TOGGLE_LOCK_SECONDS
            self._begin_transition("sleeping2waiting", to="waiting")
        elif self._state == "waiting":
            self._lock_until = _now() + TOGGLE_LOCK_SECONDS
            self._begin_transition("waitting2sleeping", to="sleeping")

    @_guarded("open_settings")
    def open_settings(self):
        if self._settings_dialog is None:
            self._settings_dialog = self._settings_factory()
            self._settings_dialog.saved.connect(self._apply_settings)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()
    # ---------------------------------------------------------------- #
    # -- transitions --------------------------------------------------- #
    def _begin_transition(self, clip: str, to: str):
        self._phase = "transition"
        self._note(f"transition:{clip}")
        self.window.play_once(clip)

    def _enter_idle(self, state: str):
        self._state = state
        self._phase = "idle"
        self.window.set_state(state)
        self.state_changed.emit(state)
        self._note(f"state:{state}")

    @_guarded("on_clip_done")
    def _on_clip_done(self, clip: str):
        """A once-mode clip reached its end (last frame stays on stage)."""
        if clip == "sleeping2waiting":
            self._enter_idle("waiting")
        elif clip == "waitting2sleeping":
            self._enter_idle("sleeping")
        elif clip == "waiting2working":
            # entering the working loop, unless the answer already arrived
            if self._finish_pending:
                self._phase = "transition"
                self.window.play_once("working2waiting")
            else:
                self._phase = "loop"
                self._note("state:working")
                self.window.play_loop("working")
        elif clip == "working2waiting":
            self._finish_pending = False
            self._enter_idle("waiting")

    @_guarded("on_loop_stopped")
    def _on_loop_stopped(self, clip: str):
        """The working loop completed one full iteration after the result."""
        if clip == "working" and self._finish_pending:
            self._phase = "transition"
            self._note("transition:working2waiting")
            self.window.play_once("working2waiting")

    # ---------------------------------------------------------------- #
    # -- clipboard ------------------------------------------------------ #
    @_guarded("on_clipboard_changed")
    def _on_clipboard_changed(self):
        # our own result writes are suppressed for a short window so a stale
        # Qt clipboard cache (image) can never re-trigger recognition
        if _now() < self._ignore_clipboard_until:
            return
        if self._state != "waiting" or self._phase != "idle":
            return
        if not clipboard.clipboard_has_image(self._app):
            return
        png = clipboard.read_clipboard_image_bytes(self._app)
        if not png:
            return
        self._start_recognition(png)

    def _start_recognition(self, png_bytes: bytes):
        self._state = "working"
        self._phase = "transition"
        self._finish_pending = False
        self.window.set_status("working")
        self.state_changed.emit("working")
        self._note("recognize:start")
        # ensure the follow-up clips decode in the background
        self.library.ensure(["working", "working2waiting"])
        self.window.play_once("waiting2working")
        self._spawn_job(png_bytes)

    # ---------------------------------------------------------------- #
    # -- recognition job ------------------------------------------------ #
    def _default_recognizer(self, png_bytes, cfg):
        return RecognizeWorker(png_bytes, cfg)

    def _spawn_job(self, png_bytes: bytes):
        snapshot = Config.from_dict(self.cfg.to_dict())
        worker = self._recognizer_factory(png_bytes, snapshot)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_recognition_ok)
        worker.failed.connect(self._on_recognition_err)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    @_guarded("on_recognition_ok")
    def _on_recognition_ok(self, latex: str):
        self._worker = None
        self._thread = None
        try:
            latex = clean_latex(latex)
        except Exception as exc:
            self._finish_with_error(f"内容无效：{exc}")
            return
        if self.cfg.output_target == "word":
            pl = build_word_payload(latex)
        else:
            pl = ClipPayload(plain=latex)
        self._ignore_clipboard_until = _now() + 2.0
        try:
            clipboard.write_payload(pl)
        except Exception as exc:
            self._finish_with_error(f"写入剪贴板失败：{exc}")
            return
        self._finish_pending = True
        self._note("recognize:ok")
        if self.sfx is not None and self.cfg.sound_enabled:
            # play the voice line a second after the result lands
            QTimer.singleShot(2000, lambda: self._play_sfx_safe())
        self._request_boundary_stop()

    @_guarded("on_recognition_err")
    def _on_recognition_err(self, reason: str):
        self._worker = None
        self._thread = None
        self._finish_with_error(reason)

    def _play_sfx_safe(self):
        try:
            self.sfx.play_random(self.cfg.volume)
        except Exception:
            log_exc("controller.play_sfx")

    def _finish_with_error(self, reason: str):
        self._ignore_clipboard_until = _now() + 2.0
        try:
            clipboard.write_text(f"Furmula 识别失败：{reason}")
        except Exception:
            pass
        self.window.show_toast(f"识别失败：{reason}", kind="error")
        self._note(f"recognize:error:{reason}")
        self._finish_pending = True
        self._request_boundary_stop()

    def _request_boundary_stop(self):
        # If the working loop is playing, finish the current full iteration
        # first; if we are still in the waiting2working transition, the loop
        # will be skipped and working2waiting plays right away.
        if self._phase == "loop":
            self.window.stage_stop_at_boundary()
        elif self._phase == "transition":
            pass  # handled when waiting2working completes

    # ---------------------------------------------------------------- #
    # -- settings -------------------------------------------------------- #
    @_guarded("apply_settings")
    def _apply_settings(self, new_cfg: Config):
        self.cfg = new_cfg
        self.store.save(new_cfg)
        self.window.set_target_text(new_cfg.output_target)
        self.window.apply_visual(new_cfg.window_scale, new_cfg.window_opacity)
        if not new_cfg.sound_enabled and self.sfx is not None:
            self.sfx.stop()
        self._note("settings:saved")

    def job_is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _note(self, msg: str):
        self.note_event.emit(msg)

    # ---------------------------------------------------------------- #
    @_guarded("shutdown")
    def shutdown(self):
        """Cancel in-flight work and quit cleanly."""
        if self._settings_dialog is not None:
            try:
                self._settings_dialog.close()
            except Exception:
                pass
            self._settings_dialog = None
        if self._worker is not None:
            try:
                self._worker.abort()
            except Exception:
                pass
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1500)
        if self.sfx is not None:
            self.sfx.stop()
        self.library.shutdown()
        self.window.close()
        try:
            self._app.clipboard().dataChanged.disconnect(self._on_clipboard_changed)
        except Exception:
            pass
        QTimer.singleShot(0, self._app.quit)
