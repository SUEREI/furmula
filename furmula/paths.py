"""Filesystem layout helpers: project root and asset folders.

Frozen (PyInstaller) mode: bundled assets live under ``sys._MEIPASS`` while
user data (data/config.json, logs) stays next to the exe for portability.
"""
import os
import sys

if getattr(sys, "frozen", False):          # running as a PyInstaller bundle
    ROOT = os.path.dirname(sys.executable)
    _BASE = sys._MEIPASS                    # dir holding the bundled assets
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _BASE = ROOT

ASSETS = os.path.join(_BASE, "assets")

FURINA_VISUAL = os.path.join(ASSETS, "furina_visual")
FURINA_SOUND = os.path.join(ASSETS, "furina_sound")
APP_ICON = os.path.join(ASSETS, "app_icon")
FRAME_CACHE = os.path.join(FURINA_VISUAL, "_cache")


def asset(*parts):
    return os.path.join(ASSETS, *parts)


def visual(*parts):
    return os.path.join(FURINA_VISUAL, *parts)


def sound(*parts):
    return os.path.join(FURINA_SOUND, *parts)


def icon(*parts):
    return os.path.join(APP_ICON, *parts)
