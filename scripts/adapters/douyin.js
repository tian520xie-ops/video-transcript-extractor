/* 抖音取址适配器 —— 方法 A：video 元素 currentSrc / src / source 子元素。
   返回：http(s) URL 字符串数组（按直链优先排序）。
   已验证：2026-11-20，页面 https://www.douyin.com/video/<id> */
(function () {
  var vs = [].slice.call(document.querySelectorAll('video'));
  var arr = [];
  vs.forEach(function (v) {
    if (v.currentSrc) arr.push(v.currentSrc);
    if (v.src) arr.push(v.src);
    [].slice.call(v.querySelectorAll('source')).forEach(function (s) {
      if (s.src) arr.push(s.src);
    });
  });
  arr = arr.filter(function (u) { return /^https?:\/\//.test(u); });
  arr = arr.filter(function (u, i) { return arr.indexOf(u) === i; });
  // 优先带 video_mp4 的直链（douyinvod），其次任意直链
  var direct = arr.filter(function (u) { return /video_mp4/.test(u) || /douyinvod\.com/.test(u); });
  return JSON.stringify(direct.length ? direct.concat(arr.filter(function (u) { return direct.indexOf(u) < 0; })) : arr);
})()
