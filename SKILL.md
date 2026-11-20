---
name: video-transcript-extractor
description: Extract a verbatim transcript (逐字稿) from a video URL or a local video/audio file. Use when the user asks to extract 文案、逐字稿、字幕文字 or transcription from 抖音、小红书、B站 or a local media file. Handles browser login state via Web Access CDP, downloads audio-bearing media, runs local Paraformer ASR, and proofreads with homophone correction. Does not collect comments, analyze authors, or produce Excel/PDF.
agent_created: true
---

# 视频逐字稿提取

## 目的

从视频链接或本地媒体文件提取完整、忠实的逐字稿。ASR 部分平台无关；成败全在"取到完整、有声、可下载的媒体"这一段。全程只做全文提取，不采评论、不研究作者、不做 Excel/PDF 或内容分析。

## 触发条件

- 用户给出抖音 / 小红书 / B站 视频链接，要求提取文案、逐字稿、字幕文字、转文字。
- 用户给出本地视频或音频文件，要求提取文案、逐字稿。
- 用户提及本 skill 名称或"用视频转写流程"。

不触发：只要求摘要、翻译、评论分析、作者研究、生成字幕文件（SRT 交付）。

## 环境解析（每次任务开始先做）

1. 读取 `{用户主目录}/视频转写工具/环境说明.md`，取出 PY / ASR_SCRIPT / MODELS / FFMPEG / FFPROBE / SKILL_DIR。找不到时查 `AI课程工具` 和当前智能体技能目录。**不要照搬任何示例盘符或用户名**。
2. 运行 `scripts/check_env.py` 一次性解析并打印实际路径与可用性；它同时检查 CDP Proxy 健康状态。
3. 若 CDP 不可用，提示用户本人在 Chrome 打开 `chrome://inspect/#remote-debugging` 勾选允许远程调试；此授权不可代点。**本地文件任务完全跳过此步**。

详细字段与回退规则见 `references/environment.md`。

## 工作流（6 步 + 收尾）

每一步都有交接条件，达到即进入下一步；失败只处理失败环节，不重新设计流程。完整规范见 `references/workflow.md`。

1. **建任务目录**：在工作区创建 `视频转写任务_<平台>_<时间戳>/`，含 `media/`、`asr/`，写 `manifest.json`（视频 ID、页面 URL、媒体文件、时长、各步状态）。命中缓存（视频 ID + 媒体来源 + 时长一致）则复用，不重复识别。
2. **Web Access**：仅在链接任务执行。复用同一 Proxy 与日常 Chrome 登录态，不重复检查依赖、不重启浏览器、不切账号。用 `scripts/cdp.py` 调用 Proxy。保留用户原有标签页。
3. **解析身份与取址**：跟随跳转保存最终 URL 与真实视频 ID，**用页面内数据确认身份，不能只看标题**。按 A→B→C 顺序取址，成功即停；A/B 在 `scripts/adapters/` 已有平台适配器，C 用 `generic.js`。禁止 blob: 直传、改签名、研究 a_bogus。
4. **下载与核验**：用 `scripts/download.py` 带同页 UA/Referer 分块下载，不打印完整 URL 或二进制；401/403 时只刷新同页一次重试一次。用 `scripts/probe.py` 校验：可解析、有 audio 流、时长与页面声明相符。无声或分片预览一律不合格。
5. **ASR**：运行 `scripts/transcribe.py`（已内置 CT-punc 元组修复与禁止 pyc 写入），命令为 `<PY> scripts/transcribe.py <媒体> -o <TASK>/asr/transcript`。脚本内部完成 FFmpeg 提音→VAD→Paraformer→CT-punc→TXT/JSON/SRT。等待时查看进程与日志，不重复启动。核对段数非空、末段时间与媒体吻合；失败片段只重试一次。
6. **校对与输出**：完整通读原稿一次，只修正有依据的错字、同音误识和标点，保留原话、语气词、重复和自我修正。疑点最多局部复核一次，不能确认就标注 `[听不清，时间点]`。保存 UTF-8 校对 TXT，在对话中按语义分段输出全文（正文无时间戳，疑点标记除外），最后给路径。

**收尾**：用 `cdp.py close <targetId>` 只关闭自己创建的标签页，保留 Proxy 与用户页面。复用缓存要说明来源，不冒称本次重新识别。最后只附一行耗时和真实缺项。

## 平台适配器

| 平台 | 取址方法 | 适配器 | 音轨处理 |
|---|---|---|---|
| 抖音 | A：`video` 元素 source 直链 | `scripts/adapters/douyin.js` | 视频内置 AAC |
| 小红书 | B：`__INITIAL_STATE__` | `scripts/adapters/xiaohongshu.js` | 按 audioCodec/audioChannels 筛出有声流 |
| B站 | B：`__playinfo__.data.dash.audio` | `scripts/adapters/bilibili.js` | 独立音轨，取最高码率 |
| 本地文件 | 跳过取址下载 | — | 直接 probe + ASR |
| 其他/兜底 | A + C（performance 资源） | `scripts/adapters/generic.js` | 需人工确认对应关系 |

**适配器未覆盖的平台**：不要臆造字段。按 `references/platforms.md` 的方法现场读取页面数据，确认后把新适配器加入 `scripts/adapters/`，并标注实测日期。方法 C 从未实测，首次使用属于尝试，必须说明。

## 必须遵守的三个修复（否则第 5 步会失败）

1. **CT-punc 返回元组**：`funasr_onnx 0.4.11` 的 `CT_Transformer.__call__` 返回 `(文本, 标点序列)`。`scripts/transcribe.py` 已取 `[0]`，不要改回 `text = punc(text)`，也不要修改用户原始脚本。
2. **禁止 pyc 写入**：脚本顶部已设 `sys.dont_write_bytecode = True`，调用时另加环境变量 `PYTHONDONTWRITEBYTECODE=1`，规避 librosa 导入触发的 safe-delete 批量拦截。
3. **SRT 冗余**：脚本强制输出 SRT 且无开关，产出后忽略、不交付即可。

另：本机脚本真实接口是 `<media> -o <前缀> [--asr-only]`，**不存在** `--out-dir/--models-dir/--formats/--no-time-prefix` 等参数。不要套用不存在的选项。

## 交叉核对（可选）

独立转写服务实测约 1/3 成功、两次 900 秒超时。若要用，设 60–120 秒短超时，失败即降级到本地稿 + 视频内证（标题、重复专名），不反复重试。校对规则不变。

## 输出规范

- 校对稿 UTF-8，路径 `<TASK>/asr/transcript_校对.txt`；原稿 `<TASK>/asr/transcript.txt` 与 `.json` 保留。
- 对话中输出完整校对稿，按语义分段，正文无时间戳，仅疑点标记含时间点。
- 结尾附：完整性核对结果、产物路径、一行耗时与真实缺项。不反复"最终检查"。

## 边界与诚实声明

- 已实测：抖音、小红书、B站、本地文件（2026-11-20）。其他平台未验证。
- 不覆盖：HLS/DASH 加密流、直播、会员或需验证码内容、音频视频分离且无完整音轨的平台。
- 媒体 URL 签名时效短，拿到即下载，不缓存地址。
- 全程以权利人授权为前提；不读取或导出账号 Cookie、密码。
