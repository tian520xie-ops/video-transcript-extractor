# video-transcript-extractor

视频逐字稿提取 Skill（适用于 WorkBuddy / Claude Agent Skills 格式）。从视频链接或本地媒体文件提取完整、忠实的逐字稿，自动处理浏览器登录态、媒体下载、本地 ASR 与校对。

## 功能

- 支持 **抖音、小红书、B站** 链接，以及**本地视频/音频文件**（2026-11-20 实机验证）。
- 复用日常 Chrome 登录态（Web Access CDP），无需重复登录。
- 优先下载独立完整音轨；没有则下载带声音的视频，并用 ffprobe 校验有声与时长。
- 本地 Paraformer + FSMN-VAD + CT-punc 量化模型（CPU，不联网下载模型）生成 TXT / JSON。
- 一键生成带时间戳的 SRT（ byproduct，默认不交付）。
- 忠实性校对：只改有依据的错字/同音误识，保留语气词与自我修正，疑点就地标注。

## 安装

```bash
# 用户级（所有项目可用）
cp -r video-transcript-extractor ~/.workbuddy/skills/

# 项目级（随仓库共享）
cp -r video-transcript-extractor <你的项目>/.workbuddy/skills/
```

其它兼容 Agent Skills 格式的工具：把整个目录放进其 skills 目录即可。

## 依赖环境

Skill 本身只提供流程与脚本；以下依赖需在本机预先配置（详见 `references/environment.md`）：

- Python 3.10+ 独立环境，安装 `funasr-onnx`、`onnxruntime`、`numpy`、`librosa` 等。
- 三个本地量化模型（ASR / VAD / CT-punc），放到统一模型目录。
- FFmpeg / ffprobe。
- WorkBuddy 内置 Web Access skill（链接任务需要）；Chrome 需本人开启远程调试。

运行 `python scripts/check_env.py` 可一次性查看本机路径解析结果与可用性。

## 使用

直接对智能体说：

- “把这个视频的文案提取出来：&lt;抖音/小红书/B站链接&gt;”
- “帮我把这个本地视频的逐字稿提取出来：&lt;文件路径&gt;”

智能体会按 `SKILL.md` 的 6 步流程执行，并把完整校对稿输出到对话，同时在任务目录留下 `asr/transcript_校对.txt`。

## 目录结构

```
video-transcript-extractor/
├── SKILL.md                     # 触发条件、流程、输出规范、边界
├── scripts/
│   ├── check_env.py             # 环境路径解析与可用性检查
│   ├── cdp.py                   # CDP Proxy 封装
│   ├── init_task.py             # 任务目录与 manifest 初始化
│   ├── download.py              # 带 UA/Referer 的通用媒体下载
│   ├── probe.py                 # ffprobe 有声/时长校验
│   ├── transcribe.py            # 本地 ASR（含 CT-punc 元组修复）
│   └── adapters/                # 平台取址 JS
│       ├── douyin.js
│       ├── xiaohongshu.js
│       ├── bilibili.js
│       └── generic.js           # 方法 A+C 兜底（未实测）
└── references/
    ├── environment.md           # 路径解析、版本、CDP 接口、卡点
    ├── workflow.md              # 6 步完整规范
    └── platforms.md             # 平台对照与新增平台指南
```

## 已知问题与设计取舍

1. **课程原始 `transcribe.py` 有 bug**：`funasr_onnx 0.4.11` 的 CT-punc 返回 `(文本, 标点序列)` 元组，原脚本直接当字符串写出会 `TypeError`。本仓库的 `scripts/transcribe.py` 已取 `[0]` 修复，不修改用户原脚本。
2. **librosa 导入触发环境 safe-delete 拦截**：脚本顶部设置 `sys.dont_write_bytecode=True`，调用时另加 `PYTHONDONTWRITEBYTECODE=1`。
3. **SRT 强制输出**：脚本无关闭选项，产出后忽略，不交付。
4. **交叉核对服务不稳定**：实测约 1/3 成功、两次 900 秒超时；设为可选短超时步骤，失败即降级。
5. **方法 C 未实测**：`generic.js` 中的 performance 资源兜底只能作为候选，须人工确认。
6. **平台适配层脆弱**：小红书/B站取址依赖具体全局变量与键名，平台改版即失效；适配器头部标注了实测日期。

## 边界与授权

本工具仅用于权利人已授权的视频素材。不采集评论、不研究作者、不生成 Excel/PDF 或内容分析。不覆盖加密流、直播、会员/验证码内容。不读取或导出账号 Cookie、密码。

## License

MIT — 见 `LICENSE`。
