"""Frame-sequence playback.

The mp4 clips cannot be decoded through Qt on machines without system H.264
codecs, so clips are pre-decoded (tools/prepare_frames.py) into JPEG frame
caches. ClipLibrary decodes those JPEGs to QImages in a background thread;
FrameStage plays them back with a QTimer, with an explicit "stop at the end of
a full loop iteration" semantic needed by the state machine.
"""
import os

from PyQt5.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QPainterPath
from PyQt5.QtWidgets import QWidget

from . import assets
from .logging_setup import log_exc


def load_frames(name: str) -> list[QImage]:
    """Decode one cached clip into a list of QImages (call in worker thread)."""
    meta = assets.clip_meta(name)
    if not meta:
        return []
    count = int(meta.get("count", 0))
    d = meta.get("dir", assets.cache_dir(name))
    frames: list[QImage] = []
    for i in range(1, count + 1):
        path = os.path.join(d, f"frame_{i:05d}.jpg")
        img = QImage(path)
        if img.isNull():
            continue
        frames.append(img)
    return frames


class _Loader(QThread):
    loaded = pyqtSignal(str)          # clip name ready
    failed = pyqtSignal(str)          # clip name unusable

    def __init__(self, names, store, parent=None):
        super().__init__(parent)
        self._names = names
        self._store = store

    def run(self):
        for name in self._names:
            frames = load_frames(name)
            if frames:
                self._store[name] = frames
                self.loaded.emit(name)
            else:
                self.failed.emit(name)


class ClipLibrary(QObject):
    """GUI-thread owner of decoded clip frames (loaded on demand)."""

    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store: dict[str, list[QImage]] = {}
        self._queue: list[str] = []
        self._thread: _Loader | None = None

    def is_ready(self, name: str) -> bool:
        return name in self._store

    def frames(self, name: str) -> list[QImage] | None:
        return self._store.get(name)

    def ensure(self, names):
        """Queue missing clips for background decoding (deduplicated)."""
        added = False
        for n in names:
            if n not in self._store and n not in self._queue:
                self._queue.append(n)
                added = True
        if added:
            self._pump()

    def _pump(self):
        if self._thread is not None and self._thread.isRunning():
            return
        if not self._queue:
            return
        batch = self._queue[:2]
        del self._queue[:2]
        self._thread = _Loader(batch, self._store, self)
        self._thread.loaded.connect(self.ready)
        self._thread.failed.connect(self.failed)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_thread_finished(self):
        self._thread = None
        self._pump()

    def shutdown(self):
        if self._thread is not None and self._thread.isRunning():
            self._thread.wait(2500)


class FrameStage(QWidget):
    """Square stage painting static PNGs or animated clips with rounded clips."""

    once_finished = pyqtSignal(str)     # a non-loop clip reached its end
    loop_stopped = pyqtSignal(str)      # a loop stopped at a full-iteration boundary

    def __init__(self, library: ClipLibrary, parent=None):
        super().__init__(parent)
        self.library = library
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._frames: list[QImage] | None = None
        self._name: str | None = None
        self._static: QImage | None = None
        self._idx = 0
        self._fps = 30
        self._once = False
        self._stop_at_boundary = False
        self._stop_when_started = False
        self._pending: tuple[str, bool] | None = None
        self._paint_image: QImage | None = None
        self.library.ready.connect(self._library_ready)
        self.setMinimumSize(1, 1)

    # ---------------------------------------------------------------- #
    def show_static(self, state: str):
        self._stop_timer()
        self._name = None
        self._frames = None
        self._pending = None
        self._static = QImage(assets.static_png(state))
        self._paint_image = self._static
        self.update()

    def play(self, name: str, loop: bool = False):
        meta = assets.clip_meta(name)
        if not meta:
            return
        self._stop_timer()
        self._name = name
        self._once = not loop
        self._stop_at_boundary = False
        self._stop_when_started = False
        self._fps = max(1, int(meta.get("fps", 30)))
        self._pending = None
        frames = self.library.frames(name)
        if frames:
            self._start_frames(frames)
        else:
            # keep the previous picture while the decode finishes
            self._frames = None
            self._paint_image = None
            first = os.path.join(meta.get("dir", ""), "frame_00001.jpg")
            if first and os.path.isfile(first):
                self._paint_image = QImage(first)
            self.library.ensure([name])
            self._pending = (name, loop)
            self.update()

    def stop_at_boundary(self):
        """Finish the current full iteration, then stop (emits loop_stopped).

        Also remembered if the frames are still decoding, so a loop that
        starts later respects the pending stop request.
        """
        if self._frames is not None and not self._once:
            self._stop_at_boundary = True
        elif self._frames is not None and self._once:
            pass  # a one-shot clip ends by itself
        else:
            self._stop_when_started = True

    def stop_now(self):
        self._stop_timer()
        self._frames = None
        self._pending = None
        self._once = False

    def current_name(self) -> str | None:
        return self._name

    # ---------------------------------------------------------------- #
    def _library_ready(self, name):
        try:
            if not self._pending:
                return
            clip, loop = self._pending
            if name != clip or self._name != clip:
                return
            frames = self.library.frames(clip)
            if not frames:
                return
            self._pending = None
            self._stop_timer()
            self._once = not loop
            if not self._once and self._stop_when_started:
                self._stop_at_boundary = True
            self._stop_when_started = False
            self._start_frames(frames)
        except Exception:
            log_exc("animation.library_ready")

    def _start_frames(self, frames):
        self._frames = frames
        self._idx = 0
        self._paint_image = frames[0]
        self.update()
        interval = max(1, round(1000 / self._fps))
        self._timer.start(interval)

    def _stop_timer(self):
        if self._timer.isActive():
            self._timer.stop()

    def _tick(self):
        try:
            if self._frames is None or not self._timer.isActive():
                return
            total = len(self._frames)
            img = self._frames[self._idx]
            self._paint_image = img
            self.update()
            if self._once:
                if self._idx >= total - 1:
                    self._stop_timer()
                    self.once_finished.emit(self._name or "")
                else:
                    self._idx += 1
            else:
                self._idx += 1
                if self._idx >= total:
                    if self._stop_at_boundary:
                        self._stop_timer()
                        self.loop_stopped.emit(self._name or "")
                    else:
                        self._idx = 0
        except Exception:
            log_exc("animation.tick")

    # ---------------------------------------------------------------- #
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            rect = self.rect()
            path = QPainterPath()
            radius = max(8, min(28, int(self.width() * 0.07)))
            x, y = rect.x() + 1, rect.y() + 1
            w, h = rect.width() - 2, rect.height() - 2
            path.addRoundedRect(x, y, w, h, radius, radius)
            painter.setClipPath(path)
            img = self._paint_image
            if img is not None and not img.isNull():
                scaled = img.scaled(
                    rect.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = (rect.width() - scaled.width()) // 2
                y = (rect.height() - scaled.height()) // 2
                painter.drawImage(x, y, scaled)
            painter.end()
        except Exception:
            log_exc("animation.paint")
