"""Random notification sounds.

The user's assets are MP3s; Qt plays those through the audio engine which we
verified works on this machine. A fresh QMediaPlayer is created per sound so
rapid repeats never get stuck in a stale state.
"""
import random

from PyQt5.QtCore import QObject, QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

from . import assets
from .logging_setup import log_exc


class SfxPlayer(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player: QMediaPlayer | None = None

    def _stop_current(self):
        if self._player is not None:
            try:
                self._player.mediaStatusChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._player.stop()
            except Exception:
                log_exc("audio.stop")
            self._player = None

    def play_random(self, volume: int):
        """Pick a random furina voice line and play it at *volume* (0..100)."""
        try:
            files = assets.sound_files()
            if not files:
                return
            self._stop_current()
            path = random.choice(files)
            p = QMediaPlayer(self)
            p.setVolume(max(0, min(100, int(volume or 0))))
            p.mediaStatusChanged.connect(self._on_status)
            p.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            p.play()
            self._player = p  # keep alive while playing
        except Exception:
            log_exc("audio.play")

    def _on_status(self, status):
        try:
            # MediaStatus.EndOfMedia == 7
            if status == QMediaPlayer.EndOfMedia:
                if self._player is not None:
                    try:
                        self._player.mediaStatusChanged.disconnect()
                    except (TypeError, RuntimeError):
                        pass
                self._player = None
        except Exception:
            log_exc("audio.status")

    def stop(self):
        self._stop_current()
