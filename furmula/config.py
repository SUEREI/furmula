"""Persistent user configuration.

Stored as plain JSON under %APPDATA%\\Furmula\\config.json (never inside the
code tree), merged over the shipped defaults so older configs keep working.
"""
import dataclasses
import json
import os
import tempfile

from . import APP_NAME

DEFAULT_SYSTEM_PROMPT = (
    "你是一个严谨的数学公式识别器。请把图片里的数学内容完整转写成 LaTeX，"
    "只输出 LaTeX 本体：不要任何解释、前言、代码块标记或 ``` 围栏，"
    "不要行内 $ 或 $$ 包裹符。对无法辨认的部分尽力推断，保持公式结构正确。"
)

DEFAULT_MODEL = "deepseek-v4-flash-vision-exp"
DEFAULT_BASE_URL = "https://api.deepseek.com"


def _config_dir():
    # Personal app data kept next to the app folder: portable, visible and
    # clearly separate from the source code.
    from . import paths

    path = os.path.join(paths.ROOT, "data")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_NAME)
        os.makedirs(path, exist_ok=True)
    return path


@dataclasses.dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout_seconds: int = 90
    output_target: str = "latex"          # "latex" | "word"
    sound_enabled: bool = True
    volume: int = 80                      # 0..100
    window_scale: int = 100               # floating window size, % of base
    window_opacity: int = 100             # floating window opacity, %
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def chat_endpoint(self) -> str:
        url = (self.base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        if url.endswith("/v1"):
            url = url[:-3].rstrip("/")
        return f"{url}/chat/completions"

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Config":
        known = {f.name for f in dataclasses.fields(cls)}
        data = {k: v for k, v in (raw or {}).items() if k in known}
        cfg = cls(**data)
        cfg.validate()
        return cfg

    def validate(self):
        if self.output_target not in ("latex", "word"):
            self.output_target = "latex"
        self.volume = max(0, min(100, int(self.volume or 0)))
        self.window_scale = max(60, min(200, int(self.window_scale or 100)))
        self.window_opacity = max(15, min(100, int(self.window_opacity or 100)))
        self.temperature = max(0.0, min(1.5, float(self.temperature)))
        self.max_tokens = max(64, min(16384, int(self.max_tokens)))
        self.timeout_seconds = max(5, min(600, int(self.timeout_seconds)))
        if not self.system_prompt or not self.system_prompt.strip():
            self.system_prompt = DEFAULT_SYSTEM_PROMPT
        return self


class ConfigStore:
    """Load/save the user config; persists atomically."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(_config_dir(), "config.json")

    def load(self) -> Config:
        return Config.from_dict(self._read_file())

    def save(self, cfg: Config) -> None:
        cfg.validate()
        raw = json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(raw)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    def _read_file(self) -> dict:
        if not os.path.isfile(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

