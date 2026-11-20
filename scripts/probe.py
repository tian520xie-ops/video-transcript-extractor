#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ffprobe 校验媒体：可解析、有 audio 流、时长。

用法：
  python probe.py <媒体路径> [--ffprobe <路径>]

输出 JSON：streams / duration / has_audio / ok
"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser(description="ffprobe 媒体校验")
    ap.add_argument("media")
    ap.add_argument("--ffprobe", help="ffprobe 可执行文件路径")
    args = ap.parse_args()

    ffprobe = args.ffprobe or shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    media = str(Path(args.media).expanduser().resolve())
    cmd = [ffprobe, "-v", "error", "-show_entries",
           "format=duration:stream=codec_type,codec_name", "-of", "json", media]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(json.dumps({"ok": False, "error": p.stderr.strip()[:300]}, ensure_ascii=False))
        sys.exit(1)
    try:
        d = json.loads(p.stdout)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"parse: {e}"}, ensure_ascii=False))
        sys.exit(1)

    streams = d.get("streams", [])
    types = [s.get("codec_type") for s in streams]
    duration = float(d.get("format", {}).get("duration", 0) or 0)
    has_audio = "audio" in types
    out = {
        "ok": has_audio and duration > 0,
        "has_audio": has_audio,
        "duration": duration,
        "streams": [{"type": s.get("codec_type"), "codec": s.get("codec_name")} for s in streams],
        "media": media,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ok"] else 2)


if __name__ == "__main__":
    main()
