#!/usr/bin/env python3
"""夢想一號短影音「綜藝字幕」風格：NG 多、要講不停的直式口播片。

- 每句只留最好的 take（keep），字和字之間的停頓剪到 0.06 秒，最後一句講完就切
- 字幕：jf 金萱拿鐵 ExtraBold 白字粗黑邊、置中偏下（約畫面 60%）
- 強調字：金萱 Heavy、放大、黃色 #F2E92A、陰影，講到時彈一下（課程名稱、活動名稱等重要資訊）
- 頂部標題列：深色半透明長條，金萱 Heavy 斜體，白字＋黃字
- 資訊卡（例：從課程介紹圖裁出來的卡片）放在字幕下方、不擋臉，連續的卡直接換卡
- 右上角三角形 Logo；整支可加速（字幕先燒再一起加速）

    python styled_short.py --dir <專案> --models <辨識模型> [--ss 0 --t 10 --out test.mp4]

專案資料夾放 styled.json（見 styled.example.json）；字幕內容與 take 選擇由 Claude 讀辨識稿後手寫進 cues。
jf 金萱拿鐵是商用字型，不放進 repo，從 fonts_dir（預設 ~/Library/Fonts）讀取。
"""
import argparse, glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
LOGO = os.path.join(SKILL, "assets/logo_triangle.png")
SUB_FONT, EMPH_FONT = "jf-jinxuanlatte-2.0 ExtraBold", "jf-jinxuanlatte-2.0 Heavy"
HEAVY_FILE = "JF-JINXUANLATTE-2.0-HEAVY.OTF"
YELLOW = "&H2AE9F2&"                     # ASS 是 BGR：#F2E92A
W, H, FPS = 1080, 1920, 30


def load(d):
    c = json.load(open(os.path.join(d, "styled.json"), encoding="utf-8"))
    c.setdefault("speed", 1.0)
    c.setdefault("title_y", 140)
    c.setdefault("sub_y", 1150)
    c.setdefault("card_w", 900)
    c.setdefault("card_bottom", 30)
    c.setdefault("fonts_dir", os.path.expanduser("~/Library/Fonts"))
    c["fonts_dir"] = os.path.expanduser(c["fonts_dir"])
    return c


def tighten(c, d, models):
    """每段剪到緊貼著字；字和字之間比講話音量低 10dB、超過 0.1 秒的空檔剪到只剩約 0.06 秒。"""
    import wave
    import numpy as np
    import sherpa_onnx
    a16 = os.path.join(d, "work", "_tighten16k.wav")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", os.path.join(d, c["audio"]), "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", a16], check=True)
    sv = glob.glob(os.path.join(models, "sherpa-onnx-sense-voice-*"))[0]
    rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=os.path.join(sv, "model.int8.onnx"), tokens=os.path.join(sv, "tokens.txt"), use_itn=True, language="zh")
    w = wave.open(a16)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    env = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(320) / 320, "same")[::160]) + 1e-9)   # 10ms
    out = []
    for a, b in c["keep"]:
        st = rec.create_stream(); st.accept_waveform(16000, x[int(a * 16000):int(b * 16000)]); rec.decode_stream(st)
        toks = [a + t for u, t in zip(st.result.tokens, st.result.timestamps) if u not in "，。？！、 "]
        if not toks:
            out.append((a, b)); continue
        th = np.percentile(env[int(a * 100):int(b * 100)], 80) - 10
        loud = lambda i: env[i] > th
        i = int((toks[0] - 0.05) * 100)                    # 開頭：第一個字的音量起點
        while i > a * 100 and loud(i - 1):
            i -= 1
        start = max(a, i / 100 - 0.04)
        j = int((toks[-1] + 0.15) * 100)                   # 結尾：最後一個字的音量終點（講完就切）
        while j < b * 100 and loud(j):
            j += 1
        end = min(b, j / 100 + 0.06)
        cur = start
        for t0, t1 in zip(toks, toks[1:]):
            lo, hi = int((t0 + 0.12) * 100), int((t1 + 0.08) * 100)
            run, best = None, None
            for k in range(lo, hi):
                if not loud(k):
                    run = k if run is None else run
                    if k - run + 1 >= 10 and (best is None or k - run > best[1] - best[0]):
                        best = (run, k)
                else:
                    run = None
            if best:
                # 下一個字前多留 0.06 秒：m、n 鼻音起頭很小聲，剪太近會被吃掉（魔術 -> 武術）
                c0, c1 = best[0] / 100 + 0.03, best[1] / 100 - 0.06
                if c1 - c0 >= 0.08:
                    out.append((round(cur, 3), round(c0, 3))); cur = c1
        out.append((round(cur, 3), round(end, 3)))
    for a0, b0, n_end, n_start in c.get("joins", []):     # 看片後指定要更密的接點
        for i, (p, q) in enumerate(out):
            if p <= a0 <= q and n_end:
                out[i] = (p, n_end)
            if p <= b0 <= q and n_start:
                out[i] = (n_start, out[i][1])
    return [(p, q) for p, q in out if q - p > 0.05]


def remapper(keep):
    def remap(t):
        acc = 0.0
        for a, b in keep:
            if t < a:
                return acc
            if t <= b:
                return acc + t - a
            acc += b - a
        return acc
    return remap


def ts(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def line(text, emph, dur_ms):
    """強調字換金萱 Heavy、放大、黃色、陰影，講到時彈一下（可以有好幾個）。"""
    for word in sorted(emph, key=text.find, reverse=True):
        i = text.find(word)
        if i < 0:
            continue
        o = max(0, int(dur_ms * i / len(text)) - 60)
        tag = (f"{{\\fn{EMPH_FONT}\\c{YELLOW}\\bord4\\3c&H1A1A1A&\\shad7\\4c&H000000&\\4a&H40&"
               f"\\fscx100\\fscy100\\t({o},{o + 120},\\fscx122\\fscy122)\\t({o + 120},{o + 260},\\fscx108\\fscy108)\\fs110}}")
        text = text[:i] + tag + word + "{\\r}" + text[i + len(word):]
    return text


def write_ass(c, d, remap, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n\n"
                "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
                "Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
                f"Style: Default,{SUB_FONT},84,&H00FFFFFF,&H00141414,&H80000000,0,1,8,4,5,30,30,0\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Text\n")
        for a, b, text, emph in c["cues"]:
            s, e = remap(a), remap(b)
            f.write(f"Dialogue: 0,{ts(s)},{ts(e)},Default,{{\\pos({W // 2},{c['sub_y']})}}{line(text, emph, int((e - s) * 1000))}\n")
    with open(os.path.join(d, f"{c['out_name']}_字幕.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(t for _, _, t, _ in c["cues"]) + "\n")


def title_png(c, path):
    """頂部標題列：深色半透明長條，金萱 Heavy 斜體（水平錯切），白字＋黃字；字太多自動縮小。"""
    from PIL import Image, ImageDraw, ImageFont
    S, size = 2, 82
    while True:
        font = ImageFont.truetype(os.path.join(c["fonts_dir"], HEAVY_FILE), size * S)
        if sum(font.getlength(t) for t, _ in c["title"]) <= (W - 80) * S or size <= 50:
            break
        size -= 2
    bh = 118 * S
    im = Image.new("RGBA", (W * S, bh), (20, 22, 26, 170))
    txt = Image.new("RGBA", (W * S, bh), (0, 0, 0, 0))
    dr = ImageDraw.Draw(txt)
    x = (W * S - sum(font.getlength(t) for t, _ in c["title"])) / 2
    for t, col in c["title"]:
        fill = (255, 255, 255, 255) if col == "white" else (242, 233, 42, 255)
        dr.text((x + 5 * S, bh / 2 + 6 * S), t, font=font, fill=(0, 0, 0, 160), anchor="lm")
        dr.text((x, bh / 2), t, font=font, fill=fill, anchor="lm")
        x += font.getlength(t)
    txt = txt.transform(txt.size, Image.AFFINE, (1, 0.18, -0.18 * bh / 2, 0, 1, 0), Image.BICUBIC)
    im.alpha_composite(txt)
    im.resize((W, bh // S), Image.LANCZOS).save(path)


def burn(d, models, ss, dur, out):
    c = load(d)
    os.makedirs(os.path.join(d, "work"), exist_ok=True)
    raw = sum(b - a for a, b in c["keep"])
    keep = tighten(c, d, models)
    remap = remapper(keep)
    total, speed = sum(b - a for a, b in keep), c["speed"]
    print(f"剪停頓：{raw:.1f} 秒 -> {total:.1f} 秒（{len(keep)} 段），加速 {speed} 倍後 {total / speed:.1f} 秒")
    ass = os.path.join(d, "work", "styled.ass")
    write_ass(c, d, remap, ass)
    inputs = ["-i", c["src"], "-i", os.path.join(d, c["audio"]), "-loop", "1", "-t", f"{raw + 5:.0f}", "-i", LOGO]
    g = [f"[0:v]select='{'+'.join(f'between(t,{a},{b})' for a, b in keep)}',setpts=N/FRAME_RATE/TB[b0]"]
    base, F, cards = "b0", 0.2, c.get("cards", [])
    for k, (png, a, b) in enumerate(cards):
        S, E = remap(a), remap(b)
        prev_join = k > 0 and abs(remap(cards[k - 1][2]) - S) < 0.05     # 剪輯後緊接：直接換卡
        next_join = k + 1 < len(cards) and abs(remap(cards[k + 1][1]) - E) < 0.05
        fx = ("" if prev_join else f"fade=in:st={S}:d={F}:alpha=1,") + ("" if next_join else f"fade=out:st={E - F}:d={F}:alpha=1,")
        n = inputs.count("-i")
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{E - S:.3f}", "-i", os.path.join(d, png)]
        y = f"H-h-{c['card_bottom']}" + ("" if prev_join else f"+max(0\\,{S}+0.25-t)*240")
        g += [f"[{n}:v]scale={c['card_w']}:-1,format=rgba,setpts=PTS-STARTPTS+{S}/TB,{fx}null[cc{k}]",
              f"[{base}][cc{k}]overlay=x=(W-w)/2:y='{y}':eof_action=pass[cv{k}]"]
        base = f"cv{k}"
    if c.get("title"):
        title = os.path.join(d, "work", "title.png")
        title_png(c, title)
        n = inputs.count("-i")
        inputs += ["-loop", "1", "-t", f"{raw + 5:.0f}", "-i", title]
        g += [f"[{base}][{n}:v]overlay=0:{c['title_y']}[tt]"]
        base = "tt"
    esc = lambda p: p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    sel = "+".join(f"between(t,{a},{b})" for a, b in keep)
    g += [f"[2:v]scale=124:-1[logo]", f"[{base}][logo]overlay=W-w-36:22[lg]",
          f"[lg]subtitles='{esc(ass)}':fontsdir='{esc(c['fonts_dir'])}',format=yuv420p,"
          f"sidedata=mode=delete:type=DISPLAYMATRIX,setpts=PTS/{speed}[v]",
          f"[1:a]aselect='{sel}',asetpts=N/SR/TB,atempo={speed}[a]"]
    out = out or os.path.join(d, f"{c['out_name']}_初稿.mp4")
    subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(g), "-map", "[v]", "-map", "[a]",
                    "-ss", str(ss), "-t", f"{dur or total / speed - ss:.3f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
    print("->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--models", required=True)
    ap.add_argument("--ss", type=float, default=0)
    ap.add_argument("--t", type=float, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    burn(os.path.abspath(a.dir), a.models, a.ss, a.t, a.out)
