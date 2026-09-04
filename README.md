# Furmula

桌面的小「芙宁娜」悬浮窗：监听剪贴板截图 → 调用视觉模型识别公式 → 自动把
**LaTeX / Word 公式** 写回剪贴板。右下角显示识别目标，☰ 打开设置。

## 功能一览

| 状态 | 行为 |
| --- | --- |
| 闲置中 `sleeping` | 显示芙宁娜睡眠场景；**不监听剪贴板**；单击切到监听 |
| 监听中 `waiting` | 显示芙宁娜等待场景；**监听剪贴板**；截图图片会自动触发识别；单击切回闲置 |
| 工作中 `working` | 播放 waiting→working 动画 → 循环 working 动画直到识别完成 → 播完完整一轮后播放 working→waiting 动画并回到监听 |

- 单击切换会播放 `sleeping2waiting` / `waitting2sleeping` 衔接动画，切换后的
  2 秒内、以及播放过程中点击均被忽略，防止连点 bug。
- 识别结果自动覆盖剪贴板；识别目标为 **LaTeX** 时写入纯文本；
  为 **Word** 时额外写入带 MathML 的 HTML，粘贴到 Word 会变成原生可编辑公式。
- 识别完成（成功）后随机播放 `assets/furina_sound` 里的一段语音（可在设置中开关、调音量）。
- 从闲置切到监听时若尚未填写 API Key，会自动弹出设置界面。
- 悬浮窗主体**可按住拖拽**移动（拖拽不会触发状态切换）；在设置中可调
  **窗口尺寸（60%–160%）与透明度（15%–100%）**。

## 素材与「视频」

`assets/furina_visual/*.mp4` 是 H.264 视频。部分系统（如缺少解码组件的精简版
Windows）Qt 无法直接解码，因此构建时先用本地 ffmpeg 把它们解码成帧序列缓存在
`assets/furina_visual/_cache/`，运行时按帧播放——运行时不再依赖任何系统视频解码器。
缓存由 `tools/prepare_frames.py` 生成，已随仓库提供；换素材后重新执行即可。

```
assets/
├── app_icon/        # 深蓝水滴 + 白色求和号（应用图标，tools/draw_icon.py 生成）
├── furina_visual/   # 芙宁娜场景/动画（原始 mp4/png + _cache 帧缓存 + source）
└── furina_sound/    # 成功提示音（随机播放）
```

## 环境

项目内已配置虚拟环境 `.venv`（Python 3.11 + PyQt5 + requests + Pillow +
pywin32 + latex2mathml）。确认：

```powershell
.venv\Scripts\python.exe --version
```

需要安装/重建依赖：

```powershell
.venv\Scripts\pip.exe install -r requirements.txt
```

## 运行

```powershell
# 无控制台窗口启动（推荐）
start "" ".venv\Scripts\pythonw.exe" main.py

# 或双击 启动Furmula.bat
```

单例运行：重复启动会提示“已在运行”。

### 使用流程

1. ☰ 打开设置：填写 **API Key**（首次运行会自动读取本机已有的
   `DEEPSEEK_API_KEY` 并预填，密钥只保存在本机 `data\config.json`）。
   默认 Base URL `https://api.deepseek.com`、模型
   `deepseek-v4-flash-vision-exp`，均可改。
2. 选择识别目标 LaTeX / Word，勾选提示音并调音量，保存。
3. 单击悬浮窗进入“监听中”，用任意截图工具截图后自动识别；
   完成后剪贴板里就是公式，直接 Ctrl+V 粘贴。
4. 右键悬浮窗可退出。

## 代码结构

```
main.py                 入口
furmula/
  app.py                QApplication 装配、单例锁、主题
  config.py             本地配置（data\config.json），默认值合并
  assets.py             素材注册与帧缓存 meta
  paths.py              路径常量
  formula.py            LaTeX 清洗 / latex→MathML / Word(HTML) 载荷
  clipboard.py          剪贴板读写（Qt 实现，图片检测/结果写回）
  api_client.py         OpenAI 兼容视觉识别 worker（QThread + requests）
  audio.py              随机提示音播放
  animation.py          后台帧解码 ClipLibrary + 播放控件 FrameStage
  floating.py           悬浮窗（场景/状态徽章/☰/气泡/右键菜单）
  controller.py         状态机（sleeping/waiting/working + 过渡编排）
  settings_dialog.py    深蓝主题设置界面
  theme.py              配色与 QSS
tools/
  prepare_frames.py     视频 → 帧缓存（需 ffmpeg，自动探测 剪映/Trae 内置）
  draw_icon.py          绘制应用图标
  selftest.py           无头自测（状态机/锁/设置/失败路径）
  live_test.py          真实桌面剪贴板集成测试
  check_audio.py        提示音播放检查
  make_preview.py       生成 data\preview\*.png 界面预览
```

## 说明与已知限制

- 识别目标为 Word 时，若 LaTeX→MathML 转换失败会自动退化为纯文本。
- 动画/过渡视频按静音播放（视频自带音轨不播出），只保留提示音。
- 悬浮窗默认贴主屏右下角，可拖拽到任意位置（位置不跨会话记忆）。
- 应用退出时若仍有识别请求在途，会立即结束进程，避免卡在退出。
