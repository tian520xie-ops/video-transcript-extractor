#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建任务目录（含 media/、asr/）与 manifest.json 模板。

用法：
  python init_task.py <工作区> <平台标签> [--video-id <ID>] [--page-url <URL>] [--duration <秒>]
输出：新任务目录绝对路径（打印到最后一行，便于 shell 捕获）。
"""
import argparse, json, sys, time
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser(description="初始化转写任务目录")
    ap.add_argument("workspace")
    ap.add_argument("platform", help="平台标签，如 douyin / xiaohongshu / bilibili / local")
    ap.add_argument("--video-id", default="")
    ap.add_argument("--page-url", default="")
    ap.add_argument("--duration", default="")
    ap.add_argument("--cache-dir", help="缓存根目录，用于检测命中")
    args = ap.parse_args()

    ws = Path(args.workspace).expanduser().resolve()
    task = ws / f"视频转写任务_{args.platform}_{time.strftime('%Y%m%d_%H%M%S')}"
    (task / "media").mkdir(parents=True, exist_ok=True)
    (task / "asr").mkdir(parents=True, exist_ok=True)

    cache = ""
    if args.cache_dir and args.video_id:
        d = Path(args.cache_dir).expanduser()
        if d.exists():
            for m in d.glob("*/manifest.json"):
                try:
                    j = json.loads(m.read_text(encoding="utf-8"))
                    if (j.get("video_id") == args.video_id and
                            str(j.get("duration_sec", "")) == str(args.duration)):
                        cache = str(m.parent)
                        break
                except Exception:
                    pass

    manifest = {
        "video_id": args.video_id,
        "page_url": args.page_url,
        "media_file": "media/<待填>",
        "duration_sec": args.duration,
        "cache_hit": cache or None,
        "steps": {
            "step1_env_task": "done" if not cache else "cached",
            "step2_webaccess": "pending",
            "step3_media_url": "pending",
            "step4_download": "pending",
            "step5_asr": "pending",
            "step6_proofread": "pending",
        },
        "timing": {},
        "notes": [],
    }
    (task / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(task))


if __name__ == "__main__":
    main()
