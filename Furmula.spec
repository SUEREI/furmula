# -*- mode: python ; coding: utf-8 -*-
import os
ROOT = os.path.abspath(SPECPATH)
a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "assets"), "assets"),
        (os.path.join(ROOT, ".venv", "Lib", "site-packages", "latex2mathml", "unimathsymbols.txt"), "latex2mathml"),
    ],
    hiddenimports=["latex2mathml", "latex2mathml.converter", "latex2mathml.symbols_parser", "latex2mathml.tokenizer", "latex2mathml.walker", "latex2mathml.commands", "latex2mathml.exceptions"],
    hookspath=[], runtime_hooks=[], excludes=["tkinter"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Furmula", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, runtime_tmpdir=None, console=False, icon=os.path.join(ROOT, "assets", "app_icon", "app.ico"))
