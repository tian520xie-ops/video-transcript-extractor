# 平台适配器与扩展指南

## 已验证平台（2026-11-20 实机）

| 平台 | 身份确认字段 | 取址方法 | 适配器 | 关键陷阱 |
|---|---|---|---|---|
| 抖音 | 页面描述 + source URL 的 target ID | A：`<video><source>` 的 https 直链 | `douyin.js` | SSR 里的 duration 可能是无关字段；以 ffprobe 为准 |
| 小红书 | `note.noteId` | B：`__INITIAL_STATE__.note.noteDetailMap[id].note.video.media.stream` | `xiaohongshu.js` | 多路流中只有带 audioCodec 且 audioChannels>0 的一路有声（实测 EF4），取错就是无声视频 |
| B站 | `__INITIAL_STATE__` 中的 bvid | B：`__playinfo__.data.dash.audio` | `bilibili.js` | 独立音轨 `.m4s`，可直接识别；remux 成 `.m4a` 仅为了第三方工具容器兼容 |
| 本地文件 | 无 | 跳过取址下载 | — | 直接 `probe.py` + `transcribe.py` |

## 新增平台流程

1. 用 `cdp.py new <url>` 开页，`eval` 读 `location.href`、`document.title`、`document.body.innerText.slice(0,500)`，确认身份（不能只看标题）。
2. 方法 A：`eval` 读 video 元素 currentSrc/src/source。有 http(s) 直链则优先。
3. 方法 B：只有 blob: 时，列出 `Object.keys(window)` 中含 initial/state/ssr/render/data/store/video 的键，逐层 peek 结构（注意 Vue 响应式对象循环引用，不要直接 JSON.stringify 整棵树）。找到与当前视频 ID 匹配的对象后，再定位播放地址字段。
4. 方法 C：读 `performance.getEntriesByType("resource")`，按扩展名和域名筛选候选，结合视频 ID/时长人工确认。
5. 确认可用后，把最终 JS 固化为 `scripts/adapters/<平台>.js`，在文件头注明实测日期与页面 URL 形式，并更新 SKILL.md 的平台表。
6. 若适配器中出现平台特有的音轨筛选逻辑，必须以"有 audioCodec 且 audioChannels>0"或"独立 audio 数组"为依据，不能凭顺序猜。

## 诚实边界

- 未覆盖：HLS/DASH 加密流、直播、会员/验证码内容、音视频分离且无完整音轨的平台。
- 方法 C 从未触发过，属于兜底尝试，不是保证。
- 平台 DOM / JS 全局变量是脆弱点，改版即失效；排查时先看适配器头部实测日期。
- 媒体 URL 签名时效短，拿到即下载，不缓存地址。
