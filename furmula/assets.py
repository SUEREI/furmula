"""Asset registry: names, expected files and frame-cache meta handling."""
import json
import os
import threading

from . import paths

# clips we expect under furina_visual (video or cached frames)
CLIPS = {
    "sleeping2waiting": "sleeping2waiting.mp4",
    "waitting2sleeping": "waitting2sleeping.mp4",
    "waiting2working": "waiting2working.mp4",
    "working": "working.mp4",
    "working2waiting": "working2waiting.mp4",
}

STATIC = {
    "sleeping": "sleeping.png",
    "waiting": "waiting.png",
}

_cache_lock = threading.Lock()
_cache_meta_cache = {}


class AssetError(RuntimeError):
    pass


def static_png(state: str) -> str:
    name = STATIC.get(state)
    if not name:
        raise AssetError(f"unknown static state: {state}")
    return paths.visual(name)


def cache_dir(clip: str) -> str:
    return os.path.join(paths.FRAME_CACHE, clip)


def clip_meta(clip: str) -> dict | None:
    """Return parsed meta.json for a cached clip, or None."""
    with _cache_lock:
        if clip in _cache_meta_cache:
            return _cache_meta_cache[clip]
    meta_path = os.path.join(cache_dir(clip), "meta.json")
    if not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["dir"] = cache_dir(clip)
    except Exception:
        return None
    with _cache_lock:
        _cache_meta_cache[clip] = meta
    return meta


def source_matches_meta(clip: str, meta: dict) -> bool:
    """True when the cached frames still correspond to the current mp4 file."""
    try:
        src = paths.visual(CLIPS[clip])
        st = os.stat(src)
    except OSError:
        return False
    return meta.get("source_size") == st.st_size and meta.get("source_mtime") == st.st_mtime


def has_cache(clip: str) -> bool:
    meta = clip_meta(clip)
    return bool(meta and meta.get("count", 0) > 0)


def sound_files() -> list[str]:
    if not os.path.isdir(paths.FURINA_SOUND):
        return []
    return sorted(
        os.path.join(paths.FURINA_SOUND, f)
        for f in os.listdir(paths.FURINA_SOUND)
        if f.lower().endswith((".mp3", ".wav", ".ogg"))
    )
