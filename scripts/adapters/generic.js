/* 通用取址适配器 —— 方法 A + 方法 C 兜底。
   A：页面 video 元素的 http(s) 直链（currentSrc / src / source）。
   C：performance.getEntriesByType('resource') 中的媒体类资源，结合扩展名启发式筛选。
   注意：方法 C 从未实测，返回值只是候选，必须人工结合当前视频 ID/时长确认对应关系，
   不能随便拿第一个视频域名地址。不要把 blob: 交给下载器。 */
(function () {
  var arr = [];
  // A
  [].slice.call(document.querySelectorAll('video')).forEach(function (v) {
    if (v.currentSrc) arr.push(v.currentSrc);
    if (v.src) arr.push(v.src);
    [].slice.call(v.querySelectorAll('source')).forEach(function (s) {
      if (s.src) arr.push(s.src);
    });
  });
  // C
  try {
    performance.getEntriesByType('resource').forEach(function (e) {
      if (/\.(mp4|m4s|m4a|mp3|webm)(\?|$)/i.test(e.name)) arr.push(e.name);
    });
  } catch (e) {}
  arr = arr.filter(function (u) { return /^https?:\/\//.test(u); });
  arr = arr.filter(function (u, i) { return arr.indexOf(u) === i; });
  return JSON.stringify(arr);
})()
