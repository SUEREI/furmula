"""Furmula launcher.

Run with the project's virtualenv python, e.g.
    .venv\\Scripts\\pythonw.exe main.py
or double-click 启动Furmula.bat.
"""
import sys

from furmula.app import main

if __name__ == "__main__":
    sys.exit(main())
