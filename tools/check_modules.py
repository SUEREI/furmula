"""Headless sanity checks for pure modules (no GUI)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from furmula.config import Config, ConfigStore
from furmula.formula import (
    build_cf_html,
    build_word_payload,
    clean_latex,
    latex_to_mathml,
)

# clean_latex
assert clean_latex("```latex\nx^2+1\n```") == "x^2+1"
assert clean_latex("  $$a+b$$  ") == "a+b"
assert clean_latex(" $a+b$ ") == "a+b"
print("clean_latex ok")

mml = latex_to_mathml(r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}")
assert mml.startswith("<math"), mml[:50]
assert "xmlns" in mml[:90] or "<math " in mml[:40]
print("latex_to_mathml ok, len", len(mml))

pl = build_word_payload(r"x^2+1")
assert pl.html is not None
blob = build_cf_html(pl.html)
assert b"StartHTML" in blob and b"<!--StartFragment-->" in blob
print("cf_html ok, bytes", len(blob))

# config
c = Config()
assert c.chat_endpoint() == "https://api.deepseek.com/chat/completions"
c2 = Config(base_url="http://localhost:8000/v1")
assert c2.chat_endpoint() == "http://localhost:8000/chat/completions"
c3 = Config.from_dict({"output_target": "nope", "volume": 999, "api_key": ""})
assert c3.output_target == "latex" and c3.volume == 100
print("config ok")

# word payload fallback when latex invalid
pl2 = build_word_payload(r"\int_0^1 x \, dx")
assert pl2.html is not None
print("word payload ok")

print("ALL MODULE CHECKS PASSED")
