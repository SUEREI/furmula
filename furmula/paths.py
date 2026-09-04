"""Filesystem layout helpers: project root and asset folders."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

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
