"""Play the three furina sounds once each at low volume to verify audio out."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.pop("QT_QPA_PLATFORM", None)

from PyQt5.QtWidgets import QApplication

from furmula import assets
from furmula.audio import SfxPlayer

app = QApplication(sys.argv)
p = SfxPlayer()
files = assets.sound_files()
print("sound files:", [os.path.basename(f) for f in files])
assert files, "no sounds found"

for f in files:
    # play each file directly at low volume
    from PyQt5.QtCore import QUrl
    from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

    pl = QMediaPlayer()
    state = {}

    def on_status(s, pl=pl, state=state):
        state["status"] = int(s)

    pl.mediaStatusChanged.connect(on_status)
    pl.setVolume(30)
    pl.setMedia(QMediaContent(QUrl.fromLocalFile(f)))
    pl.play()
    deadline = time.time() + 8
    while time.time() < deadline and state.get("status") not in (7, 8):  # EndOfMedia
        app.processEvents()
        time.sleep(0.02)
    pl.stop()
    print("played", os.path.basename(f), "status", state.get("status"))

print("audio OK")
