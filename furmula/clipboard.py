"""Clipboard service.

Reading side (Qt, GUI thread):
  * a freshly screenshotted image arrives as a DIB / PNG / image URL list;
  * we normalise it to PNG bytes for the vision API.

Writing side (win32, GUI thread) - authoritative for *all* applications:
  * LaTeX target -> CF_UNICODETEXT
  * Word target  -> CF_UNICODETEXT + "HTML Format" carrying MathML (Word turns
    that into a native editable equation on paste).

Rationale: QClipboard.setMimeData in this PyQt build stops re-advertising the
Windows "HTML Format" once Qt previously owned an image clipboard, and mixing
Qt + win32 writes lets Qt re-assert a stale text-only clipboard. Plain win32
writes behave perfectly (verified: both formats stay available for seconds,
and Qt's own reads stay correct). The controller guards its clipboard-change
handler against the moment we write so our own write never re-triggers a job.
"""
import os

from .formula import ClipPayload, build_cf_html


def read_clipboard_image_bytes(app) -> bytes | None:
    """Return the clipboard image as PNG bytes, or None when no image present.

    Must run on the GUI thread (uses QApplication.clipboard()).
    """
    from PyQt5.QtGui import QImage

    mime = app.clipboard().mimeData()
    if mime is None:
        return None
    if mime.hasImage():
        img = mime.imageData()
        if isinstance(img, QImage) and not img.isNull():
            return _qimage_to_png(img)
    # A copied image *file* (e.g. from Explorer) often carries only a URL list.
    for url in mime.urls():
        local = url.toLocalFile()
        if local and os.path.splitext(local)[1].lower() in {
            ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff",
        }:
            data = _file_to_png(local)
            if data:
                return data
    return None


def clipboard_has_image(app) -> bool:
    mime = app.clipboard().mimeData()
    if mime is None:
        return False
    if mime.hasImage():
        return True
    return any(
        os.path.splitext(url.toLocalFile())[1].lower()
        in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}
        for url in mime.urls()
    )


def _qimage_to_png(img) -> bytes:
    from PyQt5.QtCore import QBuffer, QIODevice

    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def _file_to_png(path: str) -> bytes | None:
    try:
        from PyQt5.QtGui import QImage

        img = QImage(path)
        if img.isNull():
            return None
        return _qimage_to_png(img)
    except Exception:
        return None


def write_payload(payload: ClipPayload) -> None:
    """Write the recognised result onto the clipboard (GUI thread)."""
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, payload.plain)
        if payload.html:
            fmt = win32clipboard.RegisterClipboardFormat("HTML Format")
            win32clipboard.SetClipboardData(fmt, build_cf_html(payload.html))
    finally:
        win32clipboard.CloseClipboard()


def write_text(text: str) -> None:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()
