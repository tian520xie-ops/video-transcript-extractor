#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地量化模型转写：FFmpeg 提音 -> VAD 分段 -> Paraformer 识别 -> CT-punc 补标点。

只使用本地量化模型与 CPU 推理，运行时不下载任何模型。
输出 UTF-8 TXT / JSON / SRT（SRT 含加上 VAD 偏移后的词级时间戳）。

用法:
  python transcribe.py 输入.mp4 [-o 输出前缀] [--asr-only]
      [--models-dir <模型根目录>] [--ffmpeg <ffmpeg路径>]
      [--venv-python <解释器路径>]

相对课程原脚本的两处修复（发布版必须保留）：
  1. CT-punc 返回 (文本, 标点序列) 元组 -> 取 [0]；原脚本直接当字符串会 TypeError。
  2. 顶部 sys.dont_write_bytecode = True，规避 librosa 导入时的 pyc 批量删除拦截。
"""
import sys

sys.dont_write_bytecode = True

import argparse, json, os, shutil, subprocess, tempfile, wave
from pathlib import Path

HOME = Path.home()


def default_models():
    return Path(os.environ.get("TRANSCRIBE_MODELS", HOME / "AI课程工具/模型"))


def default_ffmpeg():
    return os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def main():
    ap = argparse.ArgumentParser(description="本地量化模型转写（CPU，不下载模型）")
    ap.add_argument("video", help="输入视频/音频文件路径")
    ap.add_argument("-o", "--out", help="输出前缀（不含扩展名），默认与输入同名")
    ap.add_argument("--asr-only", action="store_true", help="跳过 CT-punc 补标点")
    ap.add_argument("--models-dir", help="模型根目录（默认从 TRANSCRIBE_MODELS 或 ~/AI课程工具/模型）")
    ap.add_argument("--ffmpeg", help="ffmpeg 路径（默认从 PATH 或常见安装位置）")
    ap.add_argument("--venv-python", help="课程 venv 解释器路径（仅用于提示，不在此脚本内调用）")
    args = ap.parse_args()

    model_root = Path(args.models_dir).expanduser().resolve() if args.models_dir else default_models()
    ffmpeg = args.ffmpeg or default_ffmpeg()

    asr_model = model_root / "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx"
    vad_model = model_root / "speech_fsmn_vad_zh-cn-16k-common-onnx"
    punc_model = model_root / "punc_ct-transformer_zh-cn-common-vocab272727-onnx"

    required = {
        asr_model: ["model_quant.onnx", "config.yaml", "am.mvn", "tokens.json"],
        vad_model: ["model_quant.onnx", "config.yaml", "am.mvn", "configuration.json"],
        punc_model: ["model_quant.onnx", "config.yaml", "tokens.json"],
    }
    missing = [str(d / f) for d, files in required.items() for f in files if not (d / f).exists()]
    if missing:
        raise SystemExit("缺少本地模型文件，请先完成模型下载:\n  " + "\n  ".join(missing))

    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"输入文件不存在: {video}")
    out_prefix = Path(args.out).expanduser().resolve() if args.out else video.with_suffix("")

    from funasr_onnx import Paraformer, Fsmn_vad, CT_Transformer

    def extract_wav(src, dst):
        cmd = [ffmpeg, "-y", "-i", str(src), "-vn",
               "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def read_wav(path):
        import numpy as np
        with wave.open(str(path), "rb") as w:
            if w.getnchannels() != 1 or w.getframerate() != 16000:
                raise RuntimeError("音频必须为 16kHz 单声道")
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        return pcm.astype("float32") / 32768.0

    def write_wav(pcm, path):
        import numpy as np
        data = (np.clip(pcm, -1.0, 1.0) * 32767).astype("<i2")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(data.tobytes())

    def srt_ts(ms):
        h, ms = divmod(int(ms), 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    print("[1/5] FFmpeg 提取 16kHz 单声道音频", flush=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wav16k = td / "audio16k.wav"
        extract_wav(video, wav16k)
        pcm = read_wav(wav16k)

        print("[2/5] VAD 分段", flush=True)
        vad = Fsmn_vad(model_dir=str(vad_model), quantize=True, device_id="-1")
        segments = vad(str(wav16k))[0] or []
        if not segments:
            segments = [[0, len(pcm) / 16.0 * 1000]]

        print(f"[3/5] Paraformer 识别（{len(segments)} 段）", flush=True)
        asr = Paraformer(model_dir=str(asr_model), quantize=True, device_id="-1")
        punc = None if args.asr_only else CT_Transformer(model_dir=str(punc_model), quantize=True, device_id="-1")

        records = []
        for idx, seg in enumerate(segments):
            start_ms, end_ms = int(seg[0]), int(seg[1])
            s0, s1 = int(start_ms / 1000 * 16000), int(end_ms / 1000 * 16000)
            seg_pcm = pcm[s0:s1]
            if seg_pcm.size == 0:
                continue
            seg_wav = td / f"seg_{idx:05d}.wav"
            write_wav(seg_pcm, seg_wav)
            res = asr(str(seg_wav))[0]
            text = res.get("preds", "")
            toks = res.get("timestamp", []) or []
            words = []
            for t in toks:
                if len(t) >= 3:
                    words.append({"char": t[0], "start": int(t[1]) + start_ms, "end": int(t[2]) + start_ms})
            if punc and text:
                # 关键修复：funasr_onnx 0.4.11 返回 (text, punc_ids) 元组
                _pr = punc(text)
                text = _pr[0] if isinstance(_pr, tuple) else _pr
            records.append({"seg": idx, "start": start_ms, "end": end_ms,
                            "text": text, "words": words})

        print("[4/5] 写出 TXT / JSON / SRT", flush=True)
        txt = out_prefix.with_suffix(".txt")
        jsn = out_prefix.with_suffix(".json")
        srt = out_prefix.with_suffix(".srt")
        txt.write_text("\n".join(r["text"] for r in records if r["text"]) + "\n", encoding="utf-8")
        jsn.write_text(json.dumps({"source": str(video), "segments": records},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        srt_lines = []
        for i, r in enumerate(records, 1):
            if not r["text"]:
                continue
            srt_lines += [str(i), f"{srt_ts(r['start'])} --> {srt_ts(r['end'])}", r["text"], ""]
        srt.write_text("\n".join(srt_lines), encoding="utf-8")

        print("[5/5] 完成", flush=True)
        print(f"  TXT: {txt}\n  JSON: {jsn}\n  SRT: {srt}", flush=True)
        print(f"  分段数: {len(records)}（词级时间戳已写入 JSON 的 words 字段，含 VAD 偏移）", flush=True)


if __name__ == "__main__":
    main()
