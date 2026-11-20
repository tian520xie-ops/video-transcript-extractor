#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web Access CDP Proxy 通用封装。localhost 绕过系统代理。

用法：
  python cdp.py new <url>                  # 打开新标签，返回 targetId
  python cdp.py eval <targetId> <js>       # 执行 JS，打印 value
  python cdp.py eval-file <targetId> <js文件>  # 从文件读 JS（推荐，避免 shell 转义）
  python cdp.py navigate <targetId> <url>  # 仅必要跳转
  python cdp.py info <targetId>            # 页面信息
  python cdp.py close <targetId>           # 只关闭自己创建的标签
  python cdp.py targets                    # 列出标签
"""
import argparse, json, os, sys, urllib.request

sys.dont_write_bytecode = True

BASE = os.environ.get("CDP_BASE", "http://localhost:3456")
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(method, path, body=None):
    data, headers = None, {}
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(body, str):
            data = body.encode("utf-8")
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with _opener.open(r, timeout=60) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except Exception:
        return raw


def new(url):
    return req("POST", "/new", url)


def navigate(t, url):
    return req("POST", f"/navigate?target={t}", url)


def evaljs(t, js):
    return req("POST", f"/eval?target={t}", js)


def info(t):
    return req("GET", f"/info?target={t}")


def close(t):
    return req("GET", f"/close?target={t}")


def targets():
    return req("GET", "/targets")


def unwrap(value):
    """Proxy 的 value 可能是 JSON 字符串，再解析一次。"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def main():
    ap = argparse.ArgumentParser(description="CDP Proxy 封装")
    ap.add_argument("cmd", choices=["new", "eval", "eval-file", "navigate", "info", "close", "targets"])
    ap.add_argument("a1", nargs="?", help="targetId（或 new 时的 url）")
    ap.add_argument("a2", nargs="?", help="JS 代码/文件，或 navigate 时的 url")
    args = ap.parse_args()

    if args.cmd == "new":
        out = new(args.a1)
    elif args.cmd == "eval":
        out = unwrap(evaljs(args.a1, args.a2))
    elif args.cmd == "eval-file":
        js = Path(args.a2).read_text(encoding="utf-8")
        out = unwrap(evaljs(args.a1, js))
    elif args.cmd == "navigate":
        out = navigate(args.a1, args.a2)
    elif args.cmd == "info":
        out = info(args.a1)
    elif args.cmd == "close":
        out = close(args.a1)
    else:
        out = targets()
    print(json.dumps(out, ensure_ascii=False, indent=2))


# eval-file 需要 Path，放到这里避免顶部再 import
from pathlib import Path

if __name__ == "__main__":
    main()
