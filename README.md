# Furmula 使用手册

Furmula 是一只住在桌面右下角的「芙宁娜」小悬浮窗：截图 → 自动调用视觉模型识别公式 → 把 **LaTeX / Word 公式**写回剪贴板，直接 `Ctrl+V` 即可粘贴。配上芙宁娜的场景动画与随机语音，让写公式这件事多一点乐趣。

---

## 目录

1. [功能一览](#功能一览)
2. [快速开始](#快速开始)
3. [悬浮窗交互](#悬浮窗交互)
4. [设置详解](#设置详解)
5. [日常使用流程](#日常使用流程)
6. [粘贴到 Word 的说明](#粘贴到-word-的说明)
7. [素材与动画实现](#素材与动画实现)
8. [常见问题](#常见问题)
9. [项目结构](#项目结构)
10. [已知限制](#已知限制)

---

## 功能一览

悬浮窗有三种状态，左上角的状态标签实时显示当前状态：

| 状态 | 标签 | 行为 |
| --- | --- | --- |
| 闲置中 | `● 闲 置 中` | 显示芙宁娜睡眠场景；**不监听剪贴板**；单击切到监听 |
| 监听中 | `● 监 听 中` | 显示芙宁娜等待场景；**监听剪贴板**，检测到新截图自动识别；单击切回闲置 |
| 工作中 | `● 工 作 中` | 播放 waiting→working 动画 → 循环 working 动画直到识别完成 → 播完当前整轮后回到监听 |

其他特性：

- **识别目标徽章**：悬浮窗右下角显示当前输出目标（LaTeX / Word）。
- **衔接动画**：状态切换会播放对应的过渡动画，播放期间与切换后 2 秒内的点击会被忽略，防止误触。
- **提示音**：识别成功约 1 秒后，随机播放 `assets/furina_sound` 里的一段芙宁娜语音（可在设置中开关、调音量）。
- **可拖拽**：按住悬浮窗主体可拖到屏幕任意位置（拖拽不会触发状态切换；位置不跨会话记忆）。
- **尺寸与透明度**：设置中可调窗口大小（60%–160%）与不透明度（15%–100%）。
- **单例运行**：重复启动会提示"Furmula 已经在运行了"。

---

## 快速开始

### 环境要求

- Windows 10/11
- 项目自带虚拟环境 `.venv`（Python 3.11 + PyQt5 + requests + Pillow + pywin32 + latex2mathml），无需额外安装 Python。

如果需要重建虚拟环境或安装依赖：

```powershell
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

### 启动

双击项目根目录的 **`启动Furmula.bat`** 即可（无控制台窗口）。

也可以手动启动：

```powershell
start "" ".venv\Scripts\pythonw.exe" main.py
```

启动后悬浮窗出现在主屏右下角，初始为「闲置中」的睡眠场景。

---

## 悬浮窗交互

| 操作 | 效果 |
| --- | --- |
| **单击**主体 | 闲置 ↔ 监听 切换（播放过渡动画） |
| **按住拖动** | 移动悬浮窗位置 |
| **右键** | 打开菜单：`设置…` / `退出 Furmula` |

提示：

- 从闲置切到监听时，如果还没填写 API Key，会弹出提示并自动打开设置窗口。
- 工作中（识别进行中）点击不会打断任务。

---

## 设置详解

右键悬浮窗 → **设置…** 打开设置窗口。点击"保存"后配置立即生效，**窗口不会自动关闭**，底部会短暂显示"已保存"；确认无误后点"取消"或右上角 × 关闭即可。

### API 与模型

| 配置项 | 说明 |
| --- | --- |
| **API Key** | 必填。首次运行会尝试从本机 DeepSeek 凭据文件（`~/.dsh/.credentials.yaml`）自动预填；密钥只保存在本机，不会上传 |
| **Base URL** | 默认 `https://api.deepseek.com`，可换成任意 OpenAI 兼容接口 |
| **模型** | 默认 `deepseek-v4-flash-vision-exp`，需支持图片输入 |

### 识别参数（高级）

| 配置项 | 默认 | 范围 |
| --- | --- | --- |
| Temperature | 0.1 | 0 – 1.5 |
| Max Tokens | 2048 | 64 – 16384 |
| 超时（秒） | 90 | 5 – 600 |
| 系统提示词 | 内置公式识别优化版 | 可自定义，一键"恢复默认提示词" |

### 输出与体验

| 配置项 | 说明 |
| --- | --- |
| **识别目标** | `LaTeX`（纯文本输出）或 `Word`（带 MathML 的 HTML，粘贴进 Word 变原生公式） |
| **提示音** | 开关 + 音量（0–100） |
| **窗口尺寸** | 60%–160% |
| **窗口不透明度** | 15%–100% |

### 配置文件位置

所有配置保存在本机 `data\config.json`（跟随应用目录，可移植），删除该文件即恢复默认。

---

## 日常使用流程

1. **首次使用**：右键悬浮窗 → 设置 → 填 API Key → 选识别目标 → 保存。
2. **单击悬浮窗**切入「监听中」。
3. 用任意截图工具（Win+Shift+S、QQ/微信截图等）截取含公式的区域——截图进入剪贴板即自动开始识别，无需粘贴到 Furmula。
4. 等待右下角动画结束，听到提示音后，**剪贴板里已经是公式**，到编辑器里 `Ctrl+V`。
5. 不用时单击切回「闲置中」，或右键退出。

> 识别过程中可以继续正常使用电脑，Furmula 只关心剪贴板里新出现的图片。

---

## 粘贴到 Word 的说明

- 识别目标为 **Word** 时，Furmula 会把 LaTeX 先转成 MathML，再以 HTML 形式写入剪贴板；在 Word 中粘贴即得到**原生可编辑公式**（Alt+= 同款）。
- 个别复杂结构若转换失败，会自动退化为纯文本 LaTeX，保证剪贴板始终可用。
- 识别目标为 **LaTeX** 时写入纯文本，适用于 Typora、Obsidian、VS Code、Overleaf 等一切支持 LaTeX 的编辑器。

---

## 素材与动画实现

`assets/furina_visual/*.mp4` 是 H.264 视频。部分系统（如缺少解码组件的精简版 Windows）Qt 无法直接解码，因此先用本地 ffmpeg 把视频解码成帧序列缓存在 `assets/furina_visual/_cache/`，运行时按帧播放——**运行时不再依赖任何系统视频解码器**。

帧缓存已随仓库提供；更换素材后重新执行一次即可：

```powershell
.venv\Scripts\python.exe tools\prepare_frames.py
```

```
assets/
├── app_icon/        # 蓝色水滴 + 白色求和号（应用图标，tools/draw_icon.py 生成）
├── furina_visual/   # 芙宁娜场景/动画（原始 mp4/png + _cache 帧缓存 + source）
└── furina_sound/    # 成功提示音（随机播放）
```

---

## 常见问题

**Q：点击悬浮窗没反应？**
刚完成切换的 2 秒内点击会被忽略；过渡动画播放中也点击无效。稍等再点即可。

**Q：截图了但没有识别？**
确认状态标签是「监 听 中」（闲置状态不监听）；确认剪贴板里是新截图（纯文本不会触发）。

**Q：提示"还没有填写 API Key"？**
右键 → 设置 → 填入 DeepSeek 或其他兼容平台的 API Key 后保存。

**Q：任务栏/窗口图标还是旧样式？**
Windows 会缓存应用图标，重启应用（必要时重启资源管理器）后生效。

**Q：想换提示音/动画？**
往 `assets/furina_sound/` 丢 mp3/wav/ogg 即可参与随机播放；动画需用 `tools/prepare_frames.py` 重建帧缓存。

**Q：如何彻底退出？**
右键悬浮窗 → 退出 Furmula。

---

## 项目结构

```
main.py                 入口
furmula/
  app.py                QApplication 装配、单例锁、主题
  config.py             本地配置（data\config.json），默认值合并
  assets.py             素材注册与帧缓存 meta
  paths.py              路径常量
  formula.py            LaTeX 清洗 / latex→MathML / Word(HTML) 载荷
  clipboard.py          剪贴板读写（图片检测 / 结果写回）
  api_client.py         OpenAI 兼容视觉识别 worker（QThread + requests）
  audio.py              随机提示音播放
  animation.py          后台帧解码 ClipLibrary + 播放控件 FrameStage
  floating.py           悬浮窗（场景/状态标签/目标徽章/气泡/右键菜单）
  controller.py         状态机（sleeping/waiting/working + 过渡编排）
  settings_dialog.py    深蓝主题设置界面
  theme.py              配色与 QSS
tools/
  prepare_frames.py     视频 → 帧缓存（需 ffmpeg，自动探测剪映/Trae 内置）
  draw_icon.py          绘制应用图标
  gui_selftest.py       无头自测
  live_test.py          真实桌面剪贴板集成测试
  check_audio.py        提示音播放检查
  make_preview.py       生成界面预览
```

---

## 已知限制

- 悬浮窗位置拖拽后不跨会话记忆，重启后回到右下角默认位置。
- 动画按静音播放（视频自带音轨不播出），只保留识别成功的提示音。
- macOS 兼容需移除 `pywin32` 依赖，且剪贴板/截屏监听需要"屏幕录制"权限（当前仅支持 Windows）。
