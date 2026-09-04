"""Deep-blue settings window for Furmula.

Fields: API key, Base URL, model + a few basic knobs (temperature, max
tokens, timeout), formula target (LaTeX / Word), success-sound toggle,
volume, and an optional system prompt override. Emits ``saved(Config)``.
"""
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import paths
from .config import Config, DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT
from .theme import QSS, TEXT_DIM


class SettingsDialog(QDialog):
    saved = pyqtSignal(object)

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("Furmula · 设置")
        self.setWindowIcon(QIcon(paths.icon("app.ico")))
        self.setModal(False)
        self.setMinimumWidth(520)
        self.setStyleSheet(QSS)
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        root.addLayout(self._header())

        # --- API & model ------------------------------------------------ #
        box_api = QGroupBox("模型接口")
        f = QFormLayout(box_api)
        f.setLabelAlignment(Qt.AlignRight)
        f.setSpacing(8)

        self.key_edit = QLineEdit(self._cfg.api_key)
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-…")
        self.show_key = QCheckBox("显示")
        self.show_key.toggled.connect(
            lambda on: self.key_edit.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        key_row = QWidget()
        kr = QHBoxLayout(key_row)
        kr.setContentsMargins(0, 0, 0, 0)
        kr.addWidget(self.key_edit, 1)
        kr.addWidget(self.show_key)
        f.addRow("API Key", key_row)

        self.url_edit = QLineEdit(self._cfg.base_url or DEFAULT_BASE_URL)
        self.url_edit.setPlaceholderText(DEFAULT_BASE_URL)
        f.addRow("Base URL", self.url_edit)

        self.model_edit = QLineEdit(self._cfg.model or DEFAULT_MODEL)
        self.model_edit.setPlaceholderText(DEFAULT_MODEL)
        f.addRow("模型名称", self.model_edit)

        row = QWidget()
        rr = QHBoxLayout(row)
        rr.setContentsMargins(0, 0, 0, 0)
        rr.setSpacing(8)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.5)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setValue(self._cfg.temperature)
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(64, 16384)
        self.tokens_spin.setSingleStep(256)
        self.tokens_spin.setValue(self._cfg.max_tokens)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setSuffix(" s")
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setValue(self._cfg.timeout_seconds)
        rr.addWidget(QLabel("温度"))
        rr.addWidget(self.temp_spin)
        rr.addWidget(QLabel("最大输出"))
        rr.addWidget(self.tokens_spin)
        rr.addWidget(QLabel("超时"))
        rr.addWidget(self.timeout_spin)
        rr.addStretch(1)
        f.addRow("参数", row)
        root.addWidget(box_api)

        # --- output target ---------------------------------------------- #
        box_out = QGroupBox("公式识别目标")
        h = QHBoxLayout(box_out)
        self.rb_latex = QRadioButton("LaTeX")
        self.rb_word = QRadioButton("Word（粘贴为可编辑公式）")
        h.addWidget(self.rb_latex)
        h.addWidget(self.rb_word)
        h.addStretch(1)
        if self._cfg.output_target == "word":
            self.rb_word.setChecked(True)
        else:
            self.rb_latex.setChecked(True)
        root.addWidget(box_out)

        # --- sound -------------------------------------------------------- #
        box_snd = QGroupBox("识别完成提示音")
        s = QHBoxLayout(box_snd)
        self.sound_check = QCheckBox("启用提示音（随机播放 furina 语音）")
        self.sound_check.setChecked(self._cfg.sound_enabled)
        s.addWidget(self.sound_check)
        s.addSpacing(12)
        s.addWidget(QLabel("音量"))
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self._cfg.volume)
        self.vol_label = QLabel(f"{self._cfg.volume}%")
        self.vol_label.setMinimumWidth(40)
        self.vol_slider.valueChanged.connect(
            lambda v: self.vol_label.setText(f"{v}%")
        )
        s.addWidget(self.vol_slider, 1)
        s.addWidget(self.vol_label)
        root.addWidget(box_snd)

        # --- floating window look ------------------------------------------ #
        box_win = QGroupBox("悬浮窗外观")
        wn = QVBoxLayout(box_win)
        hint = QLabel("按住悬浮窗主体可拖拽移动位置；单击仍是切换状态。")
        hint.setProperty("dim", True)
        wn.addWidget(hint)
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("窗口尺寸"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(60, 160)
        self.scale_slider.setValue(self._cfg.window_scale)
        self.scale_label = QLabel(f"{self._cfg.window_scale}%")
        self.scale_label.setMinimumWidth(40)
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_label.setText(f"{v}%")
        )
        r1.addWidget(self.scale_slider, 1)
        r1.addWidget(self.scale_label)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("窗口透明度"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(15, 100)
        self.opacity_slider.setValue(self._cfg.window_opacity)
        self.opacity_label = QLabel(f"{self._cfg.window_opacity}%")
        self.opacity_label.setMinimumWidth(40)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        r2.addWidget(self.opacity_slider, 1)
        r2.addWidget(self.opacity_label)
        wn.addLayout(r1)
        wn.addLayout(r2)
        root.addWidget(box_win)

        # --- advanced ------------------------------------------------------ #
        box_adv = QGroupBox("高级")
        va = QVBoxLayout(box_adv)
        va.addWidget(QLabel("系统提示词（默认已针对公式识别优化）："))
        self.prompt_edit = QPlainTextEdit(self._cfg.system_prompt or DEFAULT_SYSTEM_PROMPT)
        self.prompt_edit.setMaximumHeight(110)
        va.addWidget(self.prompt_edit)
        btn_reset = QPushButton("恢复默认提示词")
        btn_reset.setProperty("flat", True)
        btn_reset.setMaximumWidth(140)
        btn_reset.clicked.connect(lambda: self.prompt_edit.setPlainText(DEFAULT_SYSTEM_PROMPT))
        va.addWidget(btn_reset, 0, Qt.AlignRight)
        root.addWidget(box_adv)

        self._hint_default = "配置保存在本机 data\\config.json（跟随应用目录），不会写入代码。"
        self._hint = QLabel(self._hint_default)
        self._hint.setProperty("dim", True)
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        buttons = QDialogButtonBox()
        btn_cancel = buttons.addButton("取消", QDialogButtonBox.RejectRole)
        btn_save = buttons.addButton("保存", QDialogButtonBox.AcceptRole)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._save)
        root.addWidget(buttons)

    def _header(self):
        h = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(
            QIcon(paths.icon("app.ico")).pixmap(44, 44)
        )
        ttl = QVBoxLayout()
        t = QLabel("Furmula 设置")
        t.setStyleSheet("font-size: 16px; font-weight: 700;")
        sub = QLabel("截屏 → 识别 → 公式入剪贴板")
        sub.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM};")
        ttl.addWidget(t)
        ttl.addWidget(sub)
        h.addWidget(logo)
        h.addLayout(ttl)
        h.addStretch(1)
        return h

    # ------------------------------------------------------------------ #
    def _save(self):
        try:
            target = "word" if self.rb_word.isChecked() else "latex"
            new_cfg = Config(
                api_key=self.key_edit.text().strip(),
                base_url=self.url_edit.text().strip() or DEFAULT_BASE_URL,
                model=self.model_edit.text().strip() or DEFAULT_MODEL,
                temperature=self.temp_spin.value(),
                max_tokens=self.tokens_spin.value(),
                timeout_seconds=self.timeout_spin.value(),
                output_target=target,
                sound_enabled=self.sound_check.isChecked(),
                volume=self.vol_slider.value(),
                window_scale=self.scale_slider.value(),
                window_opacity=self.opacity_slider.value(),
                system_prompt=self.prompt_edit.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT,
            )
            new_cfg.validate()
            self._cfg = new_cfg
            self.saved.emit(new_cfg)
            # keep the dialog open; flash a saved hint on the status label
            self._hint.setText("已保存")
            QTimer.singleShot(2000, lambda: self._hint.setText(self._hint_default))
        except Exception:
            from .logging_setup import log_exc

            log_exc("settings.save")
