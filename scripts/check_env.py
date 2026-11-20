#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析本机转写环境路径并检查可用性。不修改任何配置。

用法：
  python check_env.py                 # 自动从 环境说明.md 与默认位置解析
  python check_env.py --md <path>     # 指定 环境说明.md 路径
  python check_env.py --json          # 仅输出 JSON（供程序读取）
"""
import argparse, json, os, re, shutil, sys
from pathlib import Path

sys.dont_write_bytecode = True

HOME = Path.home()


def find_env_md(explicit=None):
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.exists() else None
    for c in [HOME / "视频转写工具/环境说明.md"]:
        if c.exists():
            return c
    return None


def _abs_or_none(s):
    """只接受看起来像绝对路径的值，避免把'核实方式'列当成路径。"""
    s = (s or "").strip().strip("`")
    if not s:
        return None
    # 展开 ~ 后判断；Windows 盘符路径以字母+: 开头
    expanded = os.path.expanduser(s)
    if os.path.isabs(expanded) or re.match(r"^[A-Za-z]:[\\/]", s):
        return s
    return None


def parse_env_md(md):
    """从表格行抽取绝对路径。表格第三列才是路径，第四列是核实方式（不能误取）。"""
    out = {}
    if not md:
        return out
    text = md.read_text(encoding="utf-8", errors="replace")

    # 1) 表格：| 组件 | 版本 | 路径 | 核实方式 |
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3:
            continue
        name = cols[0].strip("* ")
        path = _abs_or_none(cols[2])
        if not path:
            continue
        if re.search(r"FFmpeg", name, re.I):
            out["FFMPEG"] = path
        elif re.search(r"ffprobe", name, re.I):
            out["FFPROBE"] = path
        elif re.search(r"Web\s*Access", name, re.I):
            out["SKILL_DIR"] = path
        elif "transcribe.py" in name:
            out["ASR_SCRIPT"] = path

    # 2) 行内标注：解释器：`...`
    m = re.search(r"解释器[：:]\s*`([^`]+)`", text)
    if m:
        v = _abs_or_none(m.group(1))
        if v:
            out["PY"] = v

    # 3) 模型根目录：优先显式 MODELS 字段；否则从 ASR 模型路径的父目录推断
    m = re.search(r"(?:模型根目录|MODELS)\s*[：:]\s*`?([^\s`，,]+)", text)
    if m:
        v = _abs_or_none(m.group(1))
        if v:
            out["MODELS"] = v
    if "MODELS" not in out:
        m = re.search(r"(~/[^\s`]*speech_paraformer[^\s`/]*)", text)
        if m:
            model_dir = os.path.expanduser(m.group(1))
            out["MODELS"] = str(Path(model_dir).parent)
    return out


def resolve():
    md = find_env_md()
    cfg = parse_env_md(md)
    py = cfg.get("PY") or os.environ.get("TRANSCRIBE_PY") or "python3"
    models = cfg.get("MODELS") or os.environ.get("TRANSCRIBE_MODELS") or str(HOME / "transcribe-models")
    script = cfg.get("ASR_SCRIPT") or str(HOME / "视频转写工具/transcribe.py")
    ffmpeg = cfg.get("FFMPEG") or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    ffprobe = cfg.get("FFPROBE") or shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    skill_dir = cfg.get("SKILL_DIR") or str(HOME / ".workbuddy/skills/web-access")
    return {
        "ENV_MD": str(md) if md else None,
        "PY": py, "ASR_SCRIPT": script, "MODELS": models,
        "FFMPEG": ffmpeg, "FFPROBE": ffprobe, "SKILL_DIR": skill_dir,
        "CDP_BASE": os.environ.get("CDP_BASE", "http://localhost:3456"),
    }


def main():
    ap = argparse.ArgumentParser(description="解析并检查本机转写环境")
    ap.add_argument("--md", help="环境说明.md 路径")
    ap.add_argument("--json", action="store_true", help="仅输出 JSON")
    args = ap.parse_args()

    cfg = resolve()
    if args.md:
        md = Path(args.md).expanduser()
        if md.exists():
            cfg.update(parse_env_md(md))
            cfg["ENV_MD"] = str(md)

    checks = {
        "PY": Path(cfg["PY"]).exists(),
        "ASR_SCRIPT": Path(cfg["ASR_SCRIPT"]).exists(),
        "MODELS": Path(cfg["MODELS"]).exists(),
        "FFMPEG": Path(cfg["FFMPEG"]).exists() or shutil.which("ffmpeg") is not None,
        "FFPROBE": Path(cfg["FFPROBE"]).exists() or shutil.which("ffprobe") is not None,
        "SKILL_DIR": Path(cfg["SKILL_DIR"]).exists(),
        "CDP_BASE": None,
    }
    # CDP 健康检查（不打印敏感信息，只报可达性）
    try:
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(cfg["CDP_BASE"].rstrip("/") + "/health", timeout=3) as r:
            checks["CDP_BASE"] = r.status == 200
    except Exception:
        checks["CDP_BASE"] = False

    result = {"paths": cfg, "available": checks}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("=== 环境路径（从 环境说明.md / 默认位置解析）===")
    for k, v in cfg.items():
        print(f"{k}: {v}")
    print("\n=== 可用性 ===")
    for k, v in checks.items():
        if v is None:
            print(f"{k}: 未检查")
        elif k == "CDP_BASE":
            print(f"{k}: {'可达' if v else '不可达（链接任务需在 Chrome 开启远程调试）'}")
        else:
            print(f"{k}: {'OK' if v else '缺失'}")
    if not checks["CDP_BASE"]:
        print("\n提示：本地文件任务无需 CDP；链接任务请本人开启 Chrome 远程调试后重试。")


if __name__ == "__main__":
    main()
