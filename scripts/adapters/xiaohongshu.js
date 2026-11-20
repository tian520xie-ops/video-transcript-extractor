/* 小红书取址适配器 —— 方法 B：window.__INITIAL_STATE__.note.noteDetailMap。
   自动从 window 找当前笔记 ID，不硬编码。
   关键：只取 audioCodec 存在且 audioChannels>0 的有声流（EF4），其余为无声。
   已验证：2026-11-20，页面 https://www.xiaohongshu.com/discovery/item/<id> */
(function () {
  var s = window.__INITIAL_STATE__;
  if (!s || !s.note || !s.note.noteDetailMap) return '[]';
  var map = s.note.noteDetailMap;
  var id = String(s.note.currentNoteId || s.note.firstNoteId || '');
  var entry = (id && map[id]) || map[Object.keys(map)[0]];
  if (!entry) return '[]';
  var note = entry.note || entry;
  var v = note.video && note.video.media && note.video.media.stream;
  if (!v) return '[]';
  var out = [];
  Object.keys(v).forEach(function (k) {
    (v[k] || []).forEach(function (st) {
      if (st.masterUrl && st.audioCodec && st.audioChannels > 0) {
        out.push({ url: st.masterUrl, codec: k, duration: st.duration, size: st.size,
                   audioCodec: st.audioCodec, audioChannels: st.audioChannels });
      }
    });
  });
  // 优先 mp4
  out.sort(function (a, b) {
    var am = /\.mp4/.test(a.url) ? 0 : 1, bm = /\.mp4/.test(b.url) ? 0 : 1;
    return am - bm;
  });
  return JSON.stringify(out);
})()
