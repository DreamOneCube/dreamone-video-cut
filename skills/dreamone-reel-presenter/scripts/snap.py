#!/usr/bin/env python3
"""把剪輯清單裡的切點對到「安靜的地方」，避免切到字或帶進雜音。

用法（要用裝了 requirements.txt 的那個 Python）：
    python scripts/snap.py 影片資料夾/cuts.json            只看報告
    python scripts/snap.py 影片資料夾/cuts.json --write    把修正後的秒數寫回 cuts.json

做法：語音辨識給的字詞時間只準到 0.1～0.3 秒，不能直接拿來下刀。
這裡在每一段「大概的範圍」裡量音量，找出真正開口和收尾的位置，
前後各留一小段空白再切。相連的兩段（上一段的結束＝下一段的開始）不會動交界。
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent

PRE = 0.10    # 開口前留多久
POST = 0.14   # 收尾後留多久
STEP = 0.01   # 量音量的格子大小（秒）


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


def envelope(path):
    """每 10ms 一格的音量（dB）"""
    r = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(path), "-f", "f32le",
                        "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True)
    a = np.frombuffer(r.stdout, dtype=np.float32)
    k = int(48000 * STEP)
    m = len(a) // k
    return 20 * np.log10(np.sqrt((a[:m * k].reshape(m, k) ** 2).mean(axis=1) + 1e-12))


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cuts")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    CUTS = pathlib.Path(a.cuts).resolve()
    spec = json.loads(CUTS.read_text(encoding="utf-8"))
    cuts = spec["剪輯"]
    env = {name: envelope(p if os.path.isabs(p) else CUTS.parent / p)
           for name, p in spec["來源"].items()}
    floor = float(np.percentile(env[cuts[0]["檔"]], 10))
    loud = floor + 12   # 高過這個就算有人在講話
    print(f"環境底噪 {floor:.1f} dB，高於 {loud:.1f} dB 算有聲音\n")

    def linked(i, j):
        return (0 <= i < len(cuts) and 0 <= j < len(cuts) and cuts[i]["檔"] == cuts[j]["檔"]
                and abs(cuts[i]["結束"] - cuts[j]["開始"]) < 0.011)

    bad = 0
    for i, c in enumerate(cuts):
        e = env[c["檔"]]
        s, t = c["開始"], c["結束"]
        i0, i1 = int(round(s / STEP)), min(len(e), int(round(t / STEP)))
        seg = e[i0:i1]
        idx = np.where(seg > loud)[0]
        if len(idx) == 0:
            print(f"第 {c['句']:2} 句：這個範圍裡沒有聲音，請檢查")
            bad += 1
            continue
        onset = (i0 + idx[0]) * STEP
        offset = (i0 + idx[-1] + 1) * STEP
        new_s = s if linked(i - 1, i) else round(max(s, onset - PRE), 2)
        new_t = t if linked(i, i + 1) else round(min(t, offset + POST), 2)

        # 檢查切下去的那一點安不安靜
        def level(sec):
            j = int(round(sec / STEP))
            return float(e[max(0, j - 1):j + 2].max())
        notes = []
        if not linked(i - 1, i) and level(new_s) > loud:
            notes.append(f"開頭切在有聲音的地方（{level(new_s):.0f} dB）")
        if not linked(i, i + 1) and level(new_t) > loud:
            notes.append(f"結尾切在有聲音的地方（{level(new_t):.0f} dB）")
        if onset - s < 0.03 and not linked(i - 1, i):
            notes.append("範圍一開始就有聲音，開頭可能被切到，請把「開始」往前移")
        if t - offset < 0.03 and not linked(i, i + 1):
            notes.append("聲音一路到範圍結束，結尾可能被切到，請把「結束」往後移")
        bad += len(notes)
        mark = "⚠ " + "；".join(notes) if notes else "乾淨"
        print(f"第 {c['句']:2} 句 {c['檔']}　{s:7.2f}→{t:7.2f}　⇒　{new_s:7.2f}→{new_t:7.2f}"
              f"　（開口 {onset:.2f}、收尾 {offset:.2f}）　{mark}")
        c["開始"], c["結束"] = new_s, new_t

    if a.write:
        CUTS.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已寫回 {CUTS}")
    print(f"\n{'全部乾淨' if bad == 0 else f'還有 {bad} 個地方要處理'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
