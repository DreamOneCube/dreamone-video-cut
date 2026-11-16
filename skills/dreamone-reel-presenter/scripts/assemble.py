#!/usr/bin/env python3
"""照剪輯清單把旁白接成一支乾淨的影片，順便算出動畫要用的時間軸。

用法：
    scripts/assemble.py 影片資料夾/cuts.json                接旁白，並把時間軸寫進動畫的 timing.js
    scripts/assemble.py 影片資料夾/cuts.json --no-timing    只接旁白，不動 timing.js

輸出放在 cuts.json 旁邊：
    旁白.mp4     接好、變速後的講解影片（直式 1080×1920、60fps）
    旁白.json    疊人像要用的 START、END，以及寫進動畫的錨點

cuts.json 的格式見 cuts.example.json。

三個踩過的坑，都處理在這裡：
  1. 用 -ss 剪 HEVC，每段實際長度會跟指定的差一點，所以每段都「實測」格數，
     聲音再照實測長度去切，影音才不會愈來愈不同步。
  2. 手機直拍的素材常是「橫的畫面＋90 度旋轉旗標」，ffmpeg 解碼時會自動轉正成直式。
     尺寸一定要寫 1080:1920，寫成 1920:1080 會把人臉壓扁。
  3. 聲音全程用未壓縮的 WAV 去接，最後才壓一次。每段各自壓成 AAC 再串的話，
     每個接點會多出 21 毫秒的空隙，聽起來像一直在頓。
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
FADE = 0.012  # 每個接點的淡入淡出（秒），消掉接點的「啵」聲
FPS = 60


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


FFMPEG = tool("ffmpeg")
FFPROBE = tool("ffprobe")


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def frames_of(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return int(r.stdout.strip())


def to_out(t, src, out):
    """把原始動畫的第 t 秒換算成成品的第幾秒（和 timing.js 的 toSource 相反）"""
    if t <= src[0]:
        return out[0]
    for i in range(len(src) - 1):
        if t < src[i + 1]:
            k = (t - src[i]) / (src[i + 1] - src[i])
            return out[i] + k * (out[i + 1] - out[i])
    return out[-1]


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cuts")
    ap.add_argument("--no-timing", action="store_true")
    a = ap.parse_args()

    cuts_path = pathlib.Path(a.cuts).resolve()
    base = cuts_path.parent
    spec = json.loads(cuts_path.read_text(encoding="utf-8"))
    sources = {k: str((base / v).resolve()) if not os.path.isabs(v) else v
               for k, v in spec["來源"].items()}
    cuts = spec["剪輯"]
    speed = float(spec.get("速度", 1.0))
    lead = float(spec.get("前導", 1.0))   # 開口前留幾秒給動畫開場
    tail = float(spec.get("收尾", 0.5))   # 最後一句講完後再留幾秒
    out_video = base / "旁白.mp4"
    out_info = base / "旁白.json"
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="narration-"))

    try:
        # 來源的聲音先解成 WAV，之後切聲音都從這裡拿（精確到取樣點）
        wavs = {}
        for name, path in sources.items():
            if not pathlib.Path(path).exists():
                sys.exit(f"找不到來源：{path}")
            wavs[name] = tmp / f"src_{len(wavs)}.wav"
            run([FFMPEG, "-y", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", "48000",
                 wavs[name]])

        # 相連的段落（上一段的結束＝下一段的開始）併成一段，中間就不會有接點
        groups = []
        for c in cuts:
            if c["結束"] <= c["開始"]:
                sys.exit(f"第 {c['句']} 句的結束時間比開始還早")
            last = groups[-1][-1] if groups else None
            if last and last["檔"] == c["檔"] and abs(last["結束"] - c["開始"]) < 0.011:
                groups[-1].append(c)
            else:
                groups.append([c])

        vclips, aclips = [], []
        cursor = 0.0
        starts = {}
        print(f"剪出每一段並實測長度（{len(cuts)} 句併成 {len(groups)} 段）：")
        for i, g in enumerate(groups):
            src, t0 = sources[g[0]["檔"]], g[0]["開始"]
            want = round(g[-1]["結束"] - t0, 3)
            # 「後停」：這一段講完後多停幾秒（畫面停在最後一格、聲音補無聲）
            pause = float(g[-1].get("後停", 0))
            hold = f",tpad=stop_mode=clone:stop_duration={pause}" if pause > 0 else ""
            v = tmp / f"{i:02d}.mp4"
            # -t 要放在 -i 前面（限制讀進來的長度）；放後面會把補的停頓也切掉
            run([FFMPEG, "-y", "-v", "error", "-ss", t0, "-t", want, "-i", src, "-an",
                 "-vf", f"fps={FPS},scale=1080:1920,setsar=1{hold}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                 "-pix_fmt", "yuv420p", v])
            real = frames_of(v) / FPS
            spoken = real - pause
            w = tmp / f"{i:02d}.wav"
            run([FFMPEG, "-y", "-v", "error", "-ss", t0, "-t", f"{spoken:.6f}",
                 "-i", wavs[g[0]["檔"]],
                 "-af", f"afade=t=in:d={FADE},afade=t=out:st={spoken - FADE:.6f}:d={FADE},"
                        f"apad=whole_dur={real:.6f}",
                 "-c:a", "pcm_s16le", w])
            vclips.append(v)
            aclips.append(w)
            for c in g:
                starts.setdefault(c["句"], round(cursor + (c["開始"] - t0), 3))
                print(f"  第 {c['句']:2} 句　來源 {c['開始']:7.2f}→{c['結束']:7.2f}"
                      f"　成品 {(cursor + c['開始'] - t0) / speed:6.2f}s 起　{c.get('聽到的', '')[:22]}")
            cursor += real

        vlist, alist = tmp / "v.txt", tmp / "a.txt"
        vlist.write_text("".join(f"file '{c}'\n" for c in vclips), encoding="utf-8")
        alist.write_text("".join(f"file '{c}'\n" for c in aclips), encoding="utf-8")
        run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", vlist,
             "-c", "copy", tmp / "v.mp4"])
        run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", alist,
             "-c", "copy", tmp / "a.wav"])

        # 最後一次壓縮，順便變速（atempo 會保持音高）
        run([FFMPEG, "-y", "-v", "error", "-i", tmp / "v.mp4", "-i", tmp / "a.wav",
             "-filter_complex",
             f"[0:v]setpts=PTS/{speed},fps={FPS}[v];[1:a]atempo={speed}[a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_video])
        total = frames_of(out_video) / FPS
        print(f"\n旁白總長 {total:.2f} 秒（原速 {cursor:.2f} 秒 ÷ {speed}）→ {out_video}")

        # 成品的時間 = 前導 + 旁白裡的時間
        anchors = ([0.0] + [round(lead + starts[n] / speed, 2) for n in sorted(starts)]
                   + [round(lead + total + tail, 2)])
        info = {"START": lead, "總長": anchors[-1], "速度": speed, "anchors": anchors}

        timing = spec.get("動畫時間軸")
        if timing:
            timing = (base / timing).resolve()
            js = timing.read_text(encoding="utf-8")
            m = re.search(r"export const ANCHORS_SRC = \[([^\]]*)\]", js)
            if not m:
                sys.exit(f"{timing} 裡找不到 ANCHORS_SRC")
            src_anchors = [float(x) for x in m.group(1).split(",") if x.strip()]
            if len(src_anchors) != len(anchors):
                sys.exit(f"動畫有 {len(src_anchors) - 2} 句，剪輯清單有 {len(anchors) - 2} 句，對不起來")
            # 人像框要在某個畫面出現前收掉（例如結尾的報名標籤）
            hide = spec.get("收框時間")
            if hide is not None:
                info["END"] = round(to_out(float(hide), src_anchors, anchors) - 0.15, 2)
            if not a.no_timing:
                line = ("export const VOICE_ANCHORS = ["
                        + ", ".join(f"{x:g}" for x in anchors) + "];")
                new = re.sub(r"export const VOICE_ANCHORS = .*?;", line, js, count=1, flags=re.S)
                if "VOICE_ANCHORS" not in js:
                    sys.exit(f"{timing} 裡找不到 VOICE_ANCHORS")
                timing.write_text(new, encoding="utf-8")
                print(f"\n動畫時間軸已更新（成品 {anchors[-1]:.2f} 秒）：\n{line}")

        out_info.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        hint = f"START={info['START']}" + (f" END={info['END']}" if "END" in info else "")
        print(f"\n疊人像時用　{hint}　（已存在 {out_info.name}）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
