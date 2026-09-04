"""Verify an actual synthesized mouse release on the stage toggles the state."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.pop("QT_QPA_PLATFORM", None)

from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

import gui_selftest as T


def click(widget, x, y):
    pos = QPoint(x, y)
    press = QMouseEvent(QEvent.MouseButtonPress, QPointF(pos), Qt.LeftButton,
                        Qt.LeftButton, Qt.NoModifier)
    release = QMouseEvent(QEvent.MouseButtonRelease, QPointF(pos), Qt.LeftButton,
                          Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(widget, press)
    QApplication.sendEvent(widget, release)


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def main():
    app = QApplication(sys.argv)
    h = T.Harness()          # api key set -> toggle allowed
    h.window.move_to_corner()
    ok1 = False
    # click centre of the stage -> sleeping -> waiting
    click(h.window.stage, h.window.stage.width() // 2, h.window.stage.height() // 2)
    end = time.time() + 12
    while time.time() < end and not ok1:
        app.processEvents()
        ok1 = h.controller.state == "waiting"
        time.sleep(0.01)
    print("mouse click toggled to waiting:", ok1)

    # click again after a pause -> back to sleeping
    pump(app, 2.5)
    click(h.window.stage, h.window.stage.width() // 2, h.window.stage.height() // 2)
    ok2 = False
    end = time.time() + 12
    while time.time() < end and not ok2:
        app.processEvents()
        ok2 = h.controller.state == "sleeping"
        time.sleep(0.01)
    print("second mouse click back to sleeping:", ok2)
    h.controller.shutdown()
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
