#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用媒体下载器：从 CDP 取址（或直接用给定 URL），带同页 UA/Referer 分块下载。

用法：
  # 方式 A：从适配器 JS 现场取址（推荐，URL 不进聊天）
  python download.py --target <targetId> --adapter <js文件> --page-url <最终页面URL> --out <输出路径>
  # 方式 B：直接给 URL（仅当 URL 已安全取得，不会打印）
  python download.py --url <媒体URL> --page-url <最终页面URL> --out <输出路径>

可选：
  --ua <User-Agent>         不传则从页面 navigator.userAgent 读取
  --refresh-on-403          401/403 时刷新同页一次再试（默认开启）
  --max-bytes <N>           下载上限保护，默认 500MB
"""
import argparse, json, os, sys, time, urllib.request
from urllib.parse import urlparse

sys.dont_write_bytecode = True

BASE = os.environ.get("CDP_BASE", "http://localhost:3456")
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def evaljs(target, js):
    r = urllib.request.Request(BASE + f"/eval?target={target}", data=js.encode("utf-8"), method="POST")
    with _opener.open(r, timeout=60) as resp:
        obj = json.loads(resp.read().decode("utf-8", "replace"))
    val = obj.get("value", obj) if isinstance(obj, dict) else obj
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            pass
    return val


def pick_from_adapter(target, adapter_path):
    """适配器 JS 返回值约定：
       - 字符串：单个 http(s) URL
       - list：URL 字符串列表，或含 url/masterUrl 的 dict 列表
       - dict：含 url/masterUrl，或含 urls 列表
    """
    js = open(adapter_path, encoding="utf-8").read()
    val = evaljs(target, js)

    urls = []
    if isinstance(val, str) and val.startswith("http"):
        urls = [val]
    elif isinstance(val, list):
        for it in val:
            if isinstance(it, str) and it.startswith("http"):
                urls.append(it)
            elif isinstance(it, dict):
                u = it.get("url") or it.get("masterUrl") or ""
                if u.startswith("http"):
                    urls.append(u)
    elif isinstance(val, dict):
        u = val.get("url") or val.get("masterUrl") or ""
        if u.startswith("http"):
            urls.append(u)
        for u in val.get("urls", []):
            if isinstance(u, str) and u.startswith("http"):
                urls.append(u)
    if not urls:
        return None, {"fatal": "no http(s) media url found", "raw_type": type(val).__name__}
    # 优先 mp4 直链；其次任意 http(s)。不改造签名参数。
    mp4 = [u for u in urls if ".mp4" in u.split("?")[0]]
    return (mp4 or urls)[0], {"candidates": len(urls), "chosen_mp4": bool(mp4)}


def get_ua(target, override):
    if override:
        return override
    try:
        ua = evaljs(target, "navigator.userAgent")
        if isinstance(ua, str) and ua.startswith("Mozilla"):
            return ua
    except Exception:
        pass
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def download(url, out, ua, referer, page_url, target, refresh, max_bytes, attempts=2):
    for a in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Referer": referer})
            t0 = time.time()
            got = 0
            with _opener.open(req, timeout=180) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                with open(out, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                        if got > max_bytes:
                            raise RuntimeError(f"exceeded --max-bytes {max_bytes}")
            return {"ok": True, "attempt": a + 1, "bytes": got,
                    "content_length": total, "seconds": round(time.time() - t0, 1)}
        except Exception as e:
            err = str(e)
            code = getattr(e, "code", None)
            info = {"ok": False, "attempt": a + 1, "error": err[:200], "http_code": code}
            if a + 1 < attempts and refresh and target and code in (401, 403):
                try:
                    rr = urllib.request.Request(BASE + f"/navigate?target={target}",
                                                data=page_url.encode("utf-8"), method="POST")
                    _opener.open(rr, timeout=60).read()
                    time.sleep(1.5)
                    info["refreshed"] = True
                except Exception as e2:
                    info["refresh_error"] = str(e2)[:150]
            print(json.dumps(info, ensure_ascii=False))
    return {"ok": False, "attempts": attempts}


def main():
    ap = argparse.ArgumentParser(description="通用媒体下载器")
    ap.add_argument("--target", help="CDP targetId（用 --adapter 时必填）")
    ap.add_argument("--adapter", help="取址 JS 文件路径")
    ap.add_argument("--url", help="直接给定媒体 URL（不会打印）")
    ap.add_argument("--page-url", required=True, help="最终页面 URL，用作 Referer")
    ap.add_argument("--out", required=True, help="输出路径")
    ap.add_argument("--ua", help="覆盖 User-Agent")
    ap.add_argument("--no-refresh", action="store_true", help="401/403 时不刷新重试")
    ap.add_argument("--max-bytes", type=int, default=500 * 1024 * 1024)
    args = ap.parse_args()

    if not args.url and not args.adapter:
        ap.error("需提供 --url 或 --adapter 之一")

    meta = {}
    if args.adapter:
        if not args.target:
            ap.error("--adapter 需配合 --target")
        url, meta = pick_from_adapter(args.target, args.adapter)
        if not url:
            print(json.dumps(meta, ensure_ascii=False))
            sys.exit(2)
    else:
        url = args.url

    host = urlparse(url).netloc
    print(json.dumps({"media_host": host, **meta}, ensure_ascii=False))
    ua = get_ua(args.target, args.ua) if args.target else (args.ua or "Mozilla/5.0")
    result = download(url, args.out, ua, args.page_url, args.page_url,
                      args.target, not args.no_refresh, args.max_bytes)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
