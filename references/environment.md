# 环境配置参考

## 路径解析优先级

按以下顺序取实际值，**绝不照搬文档示例里的盘符或用户名**：

1. `check_env.py --md <显式路径>` 指定的 `环境说明.md`
2. `{用户主目录}/视频转写工具/环境说明.md`
3. 环境变量 `TRANSCRIBE_PY` / `TRANSCRIBE_MODELS`
4. 脚本内置默认（基于 `Path.home()` 与 `shutil.which`）

## 必需字段

| 变量 | 含义 | 本机默认值（仅示例，实际以解析为准） |
|---|---|---|
| PY | 配置好的 Python 解释器（venv） | 从环境说明.md 解析，或 `TRANSCRIBE_PY` |
| ASR_SCRIPT | 转写脚本 | `~/视频转写工具/transcribe.py`（发布版用本 skill 的 `scripts/transcribe.py`） |
| MODELS | 模型根目录 | 从环境说明.md 解析，或 `TRANSCRIBE_MODELS` |
| FFMPEG | ffmpeg 可执行文件 | `/opt/homebrew/bin/ffmpeg` 或 PATH 中的 ffmpeg |
| FFPROBE | ffprobe 可执行文件 | `/opt/homebrew/bin/ffprobe` 或 PATH 中的 ffprobe |
| SKILL_DIR | Web Access 目录 | `~/.workbuddy/skills/web-access` |
| CDP_BASE | CDP Proxy 地址 | `http://localhost:3456`（可用环境变量覆盖） |

Windows 主目录从 `USERPROFILE` 取得，Mac 从当前用户主目录取得。

## 依赖组件（本机实测版本，2026-11-20）

- Python 3.11.16 venv；funasr-onnx 0.4.11；onnxruntime 1.32.0（CPU）；numpy 1.26.4。
- 三个量化模型目录名固定：
  - ASR：`speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx`
  - VAD：`speech_fsmn_vad_zh-cn-16k-common-onnx`
  - 标点：`punc_ct-transformer_zh-cn-common-vocab272727-onnx`
- Web Access v2.5.4；Chrome 需本人开启远程调试。

换机器时：模型目录、venv、ffmpeg 路径都不同，须重新解析或显式传入 `--models-dir/--ffmpeg`。缺失模型文件 `transcribe.py` 会在启动时列出清单并退出，不会联网下载。

## CDP Proxy 接口（来自 Web Access 文档）

- `POST /new`，body = 完整 URL，返回 targetId。
- `POST /eval?target=<t>`，body = JS 源码；读返回 `value`，若 value 是 JSON 字符串需再解析一次（`cdp.py` 已处理）。
- `POST /navigate?target=<t>`，body = 完整 URL，仅在必要跳转时用。
- `GET /close?target=<t>`，只关闭自己创建的页面。
- `GET /health`，检查可达性。

访问 localhost 时绕过系统代理（`download.py`、`cdp.py` 均已用 `ProxyHandler({})`）。不读取或导出账号 Cookie、密码。

## 常见卡点

- **CDP 不可达**：提示本人打开 `chrome://inspect/#remote-debugging` 勾选允许远程调试。Agent 不代点授权、登录或验证码。本地文件任务无需 CDP。
- **librosa 导入触发 safe-delete 拦截**：已通过 `sys.dont_write_bytecode=True` + `PYTHONDONTWRITEBYTECODE=1` 双保险规避。
- **TTY/沙箱限制的副作用**：某个成功运行的末尾可能出现与本任务无关的清理拦截（如 sqlite journal），只判断是否影响产物文件，不影响则忽略。
