"""Build-time asset preparation: decode furina mp4 clips into frame caches.

The target machines may lack system H.264 decoders (Qt cannot play the mp4s
directly), so each clip is decoded once with a bundled ffmpeg (Jianying/Trae
ship one) into JPEG frames + meta.json under assets/furina_visual/_cache/.
The app then "plays" videos as timed frame sequences and never needs a video
codec at runtime.

Usage:
    .venv\\Scripts\\python.exe tools\\prepare_frames.py [--rebuild]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIS = os.path.join(BASE, "assets", "furina_visual")
CACHE_ROOT = os.path.join(VIS, "_cache")
CACHE_W = 512  # display works around 260px; 512 keeps hi-DPI headroom

FFMPEG_CANDIDATES = [
    os.environ.get("FURMULA_FFMPEG", ""),
    r"D:\剪映\JianyingPro\11.3.0.14362\ffmpeg.exe",
    r"D:\Trae CN\resources\app\bin\ffmpeg.exe",
    r"C:\Program Files\JianyingPro\ffmpeg.exe",
]


def find_ffmpeg():
    for c in FFMPEG_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    hit = shutil.which("ffmpeg")
    return hit


def probe(path):
    """Return (duration_s, fps) parsed from `ffmpeg -i` stderr."""
    ff = find_ffmpeg()
    p = subprocess.run([ff, "-i", path], capture_output=True, text=True)
    text = p.stderr
    dm = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    dur = None
    if dm:
        h, m, s = dm.groups()
        dur = int(h) * 3600 + int(m) * 60 + float(s)
    fm = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    fps = float(fm.group(1)) if fm else 30.0
    return dur, fps


def build_clip(mp4_path, force=False):
    stem = os.path.splitext(os.path.basename(mp4_path))[0]
    out_dir = os.path.join(CACHE_ROOT, stem)
    meta_path = os.path.join(out_dir, "meta.json")
    st = os.stat(mp4_path)
    meta = None
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = None
    if (
        not force
        and meta
        and meta.get("source_size") == st.st_size
        and meta.get("source_mtime") == st.st_mtime
        and meta.get("count", 0) > 0
        and os.path.isdir(out_dir)
    ):
        print(f"  up-to-date: {stem}")
        return True
    os.makedirs(out_dir, exist_ok=True)
    # clear previous frames
    for f in os.listdir(out_dir):
        if f != "meta.json":
            try:
                os.remove(os.path.join(out_dir, f))
            except OSError:
                pass
    pattern = os.path.join(out_dir, "frame_%05d.jpg")
    ff = find_ffmpeg()
    cmd = [
        ff, "-y", "-loglevel", "error", "-i", mp4_path,
        "-vf", f"fps=30,scale={CACHE_W}:{CACHE_W}:flags=lanczos",
        "-q:v", "2", pattern,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    frames = sorted(f for f in os.listdir(out_dir) if f.endswith(".jpg"))
    if r.returncode != 0 or not frames:
        print(f"  FAILED {stem}: {r.stderr[-300:]}")
        return False
    dur, fps = probe(mp4_path)
    meta = {
        "source": os.path.basename(mp4_path),
        "source_size": st.st_size,
        "source_mtime": st.st_mtime,
        "fps": 30,
        "count": len(frames),
        "width": CACHE_W,
        "height": CACHE_W,
        "duration": dur,
        "loop": stem == "working",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  built {stem}: {len(frames)} frames, {dur:.2f}s @30fps -> {out_dir}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    ff = find_ffmpeg()
    if not ff:
        print("no ffmpeg found; set FURMULA_FFMPEG or add to PATH")
        return 1
    print("ffmpeg:", ff)
    clips = sorted(
        f for f in os.listdir(VIS)
        if f.lower().endswith(".mp4") and not f.startswith("_")
    )
    if not clips:
        print("no mp4 clips found in", VIS)
        return 1
    ok = True
    for c in clips:
        ok &= build_clip(os.path.join(VIS, c), force=args.rebuild)
    print("done, ok =", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
