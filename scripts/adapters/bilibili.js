/* B站取址适配器 —— 方法 B：window.__playinfo__.data.dash.audio（独立音轨）。
   自动取最高码率音轨，不硬编码视频 ID。
   已验证：2026-11-20，页面 https://www.bilibili.com/video/BVxxx */
(function () {
  var p = window.__playinfo__;
  if (!p || !p.data || !p.data.dash || !p.data.dash.audio) return '';
  var aus = p.data.dash.audio.slice().sort(function (a, b) {
    return (b.bandwidth || 0) - (a.bandwidth || 0);
  });
  if (!aus.length) return '';
  return JSON.stringify({
    url: aus[0].baseUrl,
    backup: (aus[0].backupUrl || [])[0] || '',
    id: aus[0].id,
    bandwidth: aus[0].bandwidth,
    timelength: p.data.timelength
  });
})()
