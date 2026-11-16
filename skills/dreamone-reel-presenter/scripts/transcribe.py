#!/usr/bin/env python3
"""把錄音抄成逐字稿，每個字都有時間碼。

用法（要用裝了 requirements.txt 的那個 Python）：
    python scripts/transcribe.py 影片檔 [--script 講稿.txt] [--model small] [--out 檔名.json]

--script 給講稿（純文字）的話，會當成提示餵給辨識器：輸出會是繁體，專有名詞也比較準。
整個辨識都在本機跑，聲音不會送到外面。第一次執行會下載模型。

注意：字詞的時間碼誤差有 0.3～0.6 秒，只能用來「找出哪一段講了什麼」，
不能直接拿來當剪接點。剪接點要再用 snap.py 對到安靜處。
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MODELS = pathlib.Path(os.environ.get("ASR_MODELS", pathlib.Path.home() / ".cache" / "dreamone-asr"))


def tool(name):
    """找 ffmpeg／ffprobe：環境變數 → scripts/bin/ → 系統 PATH"""
    env = os.environ.get(name.upper())
    if env:
        return env
    local = HERE / "bin" / name
    if local.exists():
        return str(local)
    found = shutil.which(name)
    if not found:
        sys.exit(f"找不到 {name}。請先安裝 ffmpeg，或用環境變數 {name.upper()} 指定路徑")
    return found


def load_audio(path):
    """用 ffmpeg 把聲音解成 16kHz 單聲道，避免再裝一套解碼器"""
    import numpy as np
    r = subprocess.run(
        [tool("ffmpeg"), "-v", "error", "-i", str(path), "-f", "f32le",
         "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("audio")
    ap.add_argument("--script")
    ap.add_argument("--model", default="small")
    ap.add_argument("--out")
    a = ap.parse_args()

    path = pathlib.Path(a.audio)
    if not path.exists():
        sys.exit(f"找不到檔案：{path}")

    from faster_whisper import WhisperModel
    prompt = "以下是繁體中文的教學旁白。"
    if a.script:
        # 講稿常是 Markdown：把 ** # > | 這些符號拿掉，不然辨識結果會跟著冒出符號
        raw = pathlib.Path(a.script).read_text(encoding="utf-8")
        text = " ".join(re.sub(r"[*#>|`_\-]+", " ", raw).split())
        prompt = "以下是繁體中文的教學旁白：" + text[:600]
    MODELS.mkdir(parents=True, exist_ok=True)
    print(f"載入模型 {a.model}（第一次會下載，存在 {MODELS}）…", flush=True)
    model = WhisperModel(a.model, device="cpu", compute_type="int8",
                         download_root=str(MODELS))

    print("解音訊…", flush=True)
    audio = load_audio(path)
    print(f"{len(audio) / 16000:.1f} 秒，開始辨識…\n", flush=True)

    segments, info = model.transcribe(
        audio, language="zh", word_timestamps=True,
        initial_prompt=prompt,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
    )

    out = []
    for s in segments:
        item = {
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
            "words": [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2)}
                      for w in (s.words or [])],
        }
        out.append(item)
        print(f"[{item['start']:7.2f} → {item['end']:7.2f}] {item['text']}", flush=True)

    dest = pathlib.Path(a.out) if a.out else path.with_suffix(".json")
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n共 {len(out)} 段，已存到 {dest}")


if __name__ == "__main__":
    main()
