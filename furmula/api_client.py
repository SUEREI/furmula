"""Vision-LLM recognition worker (OpenAI-compatible chat/completions).

Runs in a dedicated QThread so the GUI never blocks on the network. The
worker receives PNG bytes + a frozen Config snapshot and emits either the
raw recognised LaTeX or a human-readable failure reason.
"""
import base64
import json
import traceback

import requests
from PyQt5.QtCore import QObject, pyqtSignal


def humanise_error(exc: Exception, timeout: int) -> str:
    if isinstance(exc, requests.exceptions.Timeout):
        return f"请求超时（>{timeout}s）"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "无法连接服务器，请检查网络与 Base URL"
    if isinstance(exc, requests.exceptions.HTTPError):
        code = exc.response.status_code if exc.response is not None else "?"
        try:
            detail = exc.response.json()
            msg = detail.get("error", {}).get("message") or detail.get("message")
        except Exception:
            msg = None
        hint = f"（{msg}）" if msg else ""
        if code == 401:
            return f"API Key 无效或未授权 (401){hint}"
        if code == 404:
            return f"接口或模型不存在 (404){hint}"
        if code == 429:
            return f"请求过于频繁或额度不足 (429){hint}"
        return f"API 返回错误 {code}{hint}"
    return f"{type(exc).__name__}: {exc}"


class RecognizeWorker(QObject):
    """One-shot recogniser; call start() after moving to a thread."""

    succeeded = pyqtSignal(str)          # latex text
    failed = pyqtSignal(str)             # human-readable reason

    def __init__(self, png_bytes: bytes, cfg_snapshot, parent=None):
        super().__init__(parent)
        self.png_bytes = png_bytes
        self.cfg = cfg_snapshot
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            latex = self._request()
        except Exception as exc:  # noqa: BLE001 - report everything to UI
            if self._abort:
                return
            try:
                reason = humanise_error(exc, self.cfg.timeout_seconds)
            except Exception:
                reason = str(exc)
            self.failed.emit(reason)
            return
        if self._abort:
            return
        self.succeeded.emit(latex)

    # ------------------------------------------------------------------ #
    def _request(self) -> str:
        from .config import Config

        cfg: Config = self.cfg
        b64 = base64.b64encode(self.png_bytes).decode("ascii")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "stream": False,
            "messages": [
                {"role": "system", "content": cfg.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请识别图片中的数学内容并输出 LaTeX。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                            },
                        },
                    ],
                },
            ],
        }
        timeout = max(5, int(cfg.timeout_seconds))
        session = requests.Session()
        try:
            resp = session.post(
                cfg.chat_endpoint(),
                headers=headers,
                data=json.dumps(payload).encode("utf-8"),
                timeout=(timeout, timeout),
            )
        finally:
            session.close()
        resp.raise_for_status()
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"响应格式异常: {str(data)[:200]}") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型返回内容为空")
        return content.strip()
