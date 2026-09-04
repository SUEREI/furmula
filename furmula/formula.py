"""Formula pipeline: clean the model output, convert LaTeX -> MathML, and
assemble clipboard payloads (plain LaTeX text and/or an HTML fragment that
Word turns into a native, editable equation on paste)."""
import dataclasses
import re

MATHML_NS = "http://www.w3.org/1998/Math/MathML"


class FormulaError(ValueError):
    pass


def clean_latex(text: str) -> str:
    """Normalise model output into bare LaTeX."""
    if not text:
        raise FormulaError("模型返回内容为空")
    t = text.strip()
    # strip ```latex ... ``` fences if the model wrapped the answer
    m = re.fullmatch(r"```(?:latex|tex|math)?\s*(.*?)\s*```", t, flags=re.S | re.I)
    if m:
        t = m.group(1).strip()
    # remove a single surrounding display/inline pair
    t = re.sub(r"^\$\$(.*)\$\$$", r"\1", t, flags=re.S)
    t = re.sub(r"^\$(.*)\$$", r"\1", t, flags=re.S)
    # collapse blank lines / stray fences
    t = re.sub(r"\r\n?", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    if not t:
        raise FormulaError("识别结果为空")
    return t


def latex_to_mathml(latex: str) -> str:
    """Convert a LaTeX string to an XHTML-ish MathML fragment."""
    try:
        from latex2mathml.converter import convert
    except Exception as exc:  # pragma: no cover - library present in the venv
        raise FormulaError(f"latex2mathml 不可用: {exc}") from exc
    try:
        mathml = convert(latex)
    except Exception as exc:
        raise FormulaError(f"LaTeX 无法转换为 MathML: {exc}") from exc
    if not mathml or "<math" not in mathml:
        raise FormulaError("MathML 转换结果为空")
    # ensure namespace on the <math> root
    if mathml.startswith("<math") and 'xmlns="' not in mathml[:80]:
        mathml = mathml.replace("<math", f'<math xmlns="{MATHML_NS}"', 1)
    return mathml


@dataclasses.dataclass
class ClipPayload:
    """Everything we put on the clipboard."""

    plain: str                 # LaTeX (fallback / latex target)
    html: str | None = None    # HTML Format carrying MathML for Word


def build_word_payload(latex: str) -> ClipPayload:
    """Try MathML+HTML (Word native equation); degrade to plain text."""
    try:
        mathml = latex_to_mathml(latex)
        html = (
            "<html>\n<head>\n</head>\n<body>\n"
            "<!--StartFragment-->"
            f"{mathml}"
            "<!--EndFragment-->\n</body>\n</html>"
        )
        return ClipPayload(plain=latex, html=html)
    except FormulaError:
        return ClipPayload(plain=latex, html=None)


def build_cf_html(html_fragment_whole: str) -> bytes:
    """Wrap an HTML document into the Windows 'HTML Format' clipboard blob.

    Word reads this private format; MathML inside it is imported as an OMML
    equation on paste.
    """
    doc = html_fragment_whole.encode("utf-8")
    header = (
        "Version:0.9\r\n"
        "StartHTML:0000000000\r\n"
        "EndHTML:0000000000\r\n"
        "StartFragment:0000000000\r\n"
        "EndFragment:0000000000\r\n"
    ).encode("ascii")

    def splice(start_placeholder_len=10, end_placeholder_len=10):
        base = len(header)
        frag_start = doc.find(b"<!--StartFragment-->") + len(b"<!--StartFragment-->")
        frag_end = doc.find(b"<!--EndFragment-->")
        hdr = header.replace(b"StartHTML:0000000000", b"StartHTML:%010d" % base)
        hdr = hdr.replace(b"EndHTML:0000000000", b"EndHTML:%010d" % (base + len(doc)))
        hdr = hdr.replace(b"StartFragment:0000000000", b"StartFragment:%010d" % (base + frag_start))
        hdr = hdr.replace(b"EndFragment:0000000000", b"EndFragment:%010d" % (base + frag_end))
        return hdr + doc

    return splice()
