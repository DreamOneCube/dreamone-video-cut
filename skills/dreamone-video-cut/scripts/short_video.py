#!/usr/bin/env python3
"""短影片：剪停頓／贅字、單行字幕（重點詞上色＋放大）、資訊卡、B-roll、三角形 Logo，全部燒進影片。

    python short_video.py --dir <專案> make          # 辨識稿 -> SRT/TXT（時間軸已套用剪輯）
    python short_video.py --dir <專案> burn [--ss 0 --t 10 --out test.mp4]

專案資料夾（--dir，預設目前資料夾）：
  short.json        設定，見 short.example.json
  terms.json        可選：本片的 [[regex, 取代], ...]
  work/<name>.json  asr.py 的辨識結果（<name> 為 short.json 的 name）
停頓與贅字的剪點由 cleanup.py 寫進 short.json 的 keep / drops。
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from subtitles import clean, load_terms  # noqa: E402

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"
FONTDIR = os.path.join(SKILL, "assets")
FONT = os.path.join(FONTDIR, "jf-openhuninn-1.1.ttf")
MAXLEN = 15                   # 直式畫面，字幕只用一行，最多 15 字（重點詞放大後仍不出界）
LOGO_W, LOGO_M = 170, 50      # 右上角三角形 Logo 寬度、離邊距離
CARD_MB = 36                  # 字卡貼底，離下緣 36px
SUB_MV = CARD_MB + 190 + 20   # 字幕固定在字卡上方（最高的字卡約 190px），字卡與字幕都在胸口、不擋臉
FILLER_RE = [(r"(^|[，。？！])那(?![個些麼裡邊樣種時就])", r"\1"), (r"(^|[，。？！])好，", r"\1")]

D = C = None                  # 專案資料夾、設定（setup() 填入）


def setup(d):
    global D, C, KEEP, HL, HL_COLOR, NOBREAK, SRC, NAME, OUT_NAME, SRT, TXT, LOGO
    D = os.path.abspath(d)
    C = json.load(open(os.path.join(D, "short.json"), encoding="utf-8"))
    SRC, NAME = C["src"], C["name"]
    OUT_NAME = C.get("out_name", NAME)
    LOGO = os.path.join(SKILL, C.get("logo", "assets/logo_triangle.png"))
    SRT = os.path.join(D, f"{OUT_NAME}_字幕.srt")
    TXT = os.path.join(D, f"{OUT_NAME}_字幕.txt")
    KEEP = C.get("keep")
    if KEEP and (C.get("drops") or C.get("repeat_drops")):   # 從保留區段再挖掉贅字、重講
        for d0, d1 in C.get("drops", []) + C.get("repeat_drops", []):
            KEEP = [p for a, b in KEEP for p in ([[a, b]] if d1 <= a or d0 >= b else
                    [q for q in ([a, d0], [d1, b]) if q[1] - q[0] > 0.04])]
    HL = sorted(C.get("highlights", []), key=len, reverse=True)
    HL_COLOR = C.get("color", "&H0000D4FF&")
    NOBREAK = C.get("nobreak", []) + ["三階", "魔術方塊"]


def ts(t, sep=","):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def remap(t):
    """原片時間 -> 剪輯後時間（落在剪掉的區段就貼到下一段開頭）。"""
    if not KEEP:
        return t
    acc = 0.0
    for a, b in KEEP:
        if t < a:
            return acc
        if t <= b:
            return acc + t - a
        acc += b - a
    return acc


def protected(p):
    """不可斷的位置：詞的中間（jieba 斷詞）、重點詞與常用詞的中間。"""
    bad, pos = set(), 0
    try:
        import jieba
        jieba.setLogLevel(60)
        from opencc import OpenCC
        sp = OpenCC("t2s").convert(p)        # jieba 詞典是簡體，繁體會被拆成單字
        for wd in jieba.cut(sp if len(sp) == len(p) else p):
            bad.update(range(pos + 1, pos + len(wd)))
            pos += len(wd)
    except ImportError:
        pass
    for h in HL + NOBREAK:
        for m in re.finditer(re.escape(h), p):
            bad.update(range(m.start() + 1, m.end()))
    return bad


def cut(p, lim):
    """找 p 的第一刀：左邊 <= lim、不增加段數，優先在標點／虛詞後、靠近平均位置，不切斷詞。"""
    bad = protected(p)
    n = -(-len(p) // lim)
    mid = len(p) / n
    ok = [k for k in range(1, min(lim, len(p) - 1) + 1)
          if k not in bad and not (p[k - 1].isascii() and p[k].isascii() and " " not in p[k - 1:k + 1])]

    def cost(k):
        c = abs(k - mid)
        if p[k - 1] in "，、 ":
            c -= 4
        elif p[k - 1] in "是在了呢會跟和到要就把的":
            c -= 1.5
        if p[k] in "的了呢嘍哦" or p[k:k + 2] == "時候":   # 下一句不要用助詞開頭
            c += 3
        if -(-(len(p) - k) // lim) > n - 1:      # 這刀會讓總段數變多
            c += 6
        return c
    return min(ok or [int(mid)], key=cost)


def cues_of(t):
    """依標點切片段，短的合併到 MAXLEN 字，太長的拆成下一句；字幕永遠只有一行。"""
    parts = [x for x in re.split(r"(?<=[。？！，；])", t) if x.strip("，；。 ")]
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) <= MAXLEN:
            cur += p
            continue
        if cur:
            out.append(cur)
        cur = p
        while len(cur) > MAXLEN:
            k = cut(cur, MAXLEN)
            out.append(cur[:k]); cur = cur[k:]
    if cur:
        out.append(cur)
    return [x.strip("，； ") for x in out]


def make():
    segs = json.load(open(os.path.join(D, "work", f"{NAME}.json"), encoding="utf-8"))
    paths = [os.path.join(SKILL, "terms", t) for t in C.get("terms", ["common.json"])]
    if os.path.exists(os.path.join(D, "terms.json")):
        paths.append(os.path.join(D, "terms.json"))
    terms = load_terms(*paths)
    cues, txt = [], []
    for s in segs:
        t = clean(s["text"], terms)
        for ctx, rest in C.get("text_edits", []):        # 剪掉重講後，字幕也拿掉前一次
            t = re.sub("[，。、 ]*".join(map(re.escape, ctx)), rest, t)
        if C.get("drops"):
            for k in C.get("fillers_kept", []):     # 剪不乾淨而保留的發語詞，字幕也留著
                t = t.replace(k, "\0" + k[1:])
            for p, r in FILLER_RE:
                t = re.sub(p, r, t)
            t = t.replace("\0", "那")
        if not t:
            continue
        txt.append(t)
        lines = cues_of(t)
        total = sum(len(x) for x in lines)
        cur = s["start"]
        for ln in lines:
            end = cur + (s["end"] - s["start"]) * len(ln) / total
            a, b = remap(cur), remap(end)
            if b - a > 0.05:
                cues.append((a, b, re.sub(r"。(?=.)", "　", ln.rstrip("。"))))
            cur = end
    with open(SRT, "w", encoding="utf-8") as f:
        for i, (a, b, ln) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{ln}\n\n")
    with open(TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(txt) + "\n")
    print(f"{len(cues)} 句字幕 -> {SRT}")
    if HL:
        body = "\n".join(txt)
        miss = [h for h in HL if h not in body]
        print("重點詞：", ", ".join(h for h in HL if h not in miss), "| 找不到：", miss or "無")


def read_srt(path):
    out = []
    for blk in re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip()):
        ls = blk.strip().splitlines()
        if len(ls) < 3:
            continue
        a, b = [x.strip() for x in ls[1].split("-->")]
        sec = lambda x: (lambda h, m, s: int(h) * 3600 + int(m) * 60 + float(s.replace(",", ".")))(*x.split(":"))
        out.append((sec(a), sec(b), "\\N".join(ls[2:])))
    return out


def color(t, dur_ms):
    """重點詞上色＋放大動畫（130% 再回 110%）；時間按字數比例對到大約講到那個詞的時候。"""
    spans = []
    for h in HL:
        for m in re.finditer(re.escape(h), t):
            if not any(m.start() < e and s < m.end() for s, e in spans):
                spans.append((m.start(), m.end()))
    for s0, e0 in sorted(spans, reverse=True):
        o = max(0, int(dur_ms * s0 / max(1, len(t))) - 80)
        tag = ("{\\c" + HL_COLOR + "\\fscx100\\fscy100\\t(%d,%d,\\fscx130\\fscy130)"
               "\\t(%d,%d,\\fscx110\\fscy110)}" % (o, o + 130, o + 130, o + 320))
        t = t[:s0] + tag + t[s0:e0] + "{\\r}" + t[e0:]
    return t


def probe(entries):
    o = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                        "-of", "json", SRC], capture_output=True, text=True, check=True).stdout
    return json.loads(o)["streams"][0]


def display_size():
    s = probe("stream=width,height:stream_side_data=rotation")
    rot = abs(int(next((d.get("rotation", 0) for d in s.get("side_data_list", [])), 0)))
    return (s["height"], s["width"]) if rot in (90, 270) else (s["width"], s["height"])


def fps():
    n, d = probe("stream=r_frame_rate")["r_frame_rate"].split("/")
    return round(int(n) / int(d), 3)


def anchor(cues, text):
    """字幕文字從 text 開始的那句的開始時間（剪輯後時間軸）；錨點可以跨好幾句。"""
    flat = [t.replace("\\N", "") for _, _, t in cues]
    for i, (a, _, _) in enumerate(cues):
        if "".join(flat[i:i + 4]).replace(" ", "").startswith(text.replace(" ", "")):
            return a
    raise SystemExit(f"short.json 的錨點找不到字幕：{text}")


def insert_graph(inputs, graph, w, h, base):
    """把 inserts（資訊卡、B-roll）疊到 base 上，回傳新的 label。"""
    from cards import card, label, tag
    ins = C.get("inserts", [])
    if not ins:
        return base
    cues, r, F = read_srt(SRT), fps(), 0.25
    work = os.path.join(D, "work")
    for k, it in enumerate(ins):
        S, E = anchor(cues, it["at"]), anchor(cues, it["until"])
        dur = E - S
        nxt = ins[k + 1] if k + 1 < len(ins) else {}
        fade_in = it.get("anim", True)
        fade_out = not (nxt.get("type") == "card" and nxt.get("anim") is False)   # 下一張接續就不淡出
        fades = (f"fade=in:st={S}:d={F}:alpha=1," if fade_in else "") + \
                (f"fade=out:st={E - F}:d={F}:alpha=1," if fade_out else "")
        n = inputs.count("-i")
        loop = ["-loop", "1", "-framerate", str(r), "-t", f"{dur:.3f}", "-i"]
        if it["type"] == "card":
            png = os.path.join(work, f"card{k}.png")
            _, ch = card(FONT, png, w - 80, it["title"], it.get("num"), it.get("lines", ()), it.get("checks", False))
            y = h - CARD_MB - ch
            yexpr = f"{y}+max(0\\,{S}+0.3-t)*110" if fade_in else str(y)     # 由下往上滑入
            inputs += loop + [png]
            graph += [f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{S}/TB,{fades}null[c{k}]",
                      f"[{base}][c{k}]overlay=x=(W-w)/2:y='{yexpr}':eof_action=pass[b{k + 1}]"]
            base = f"b{k + 1}"
        elif it["type"] == "broll":
            vh = round(w * 9 / 16 / 2) * 2
            y = int(h * 0.2)
            lbl = os.path.join(work, f"label{k}.png")
            _, lh = label(FONT, lbl, it["label"], it["credit"])
            inputs += ["-ss", str(it.get("src_ss", 0)), "-t", f"{dur:.3f}", "-i", it["src"]] + loop + [lbl]
            crop = f"crop={it['crop']}," if it.get("crop") else ""
            graph += [f"[{base}]split[x{k}][y{k}]",
                      f"[y{k}]boxblur=30:2,eq=brightness=-0.15,format=yuva420p,"
                      f"fade=in:st={S}:d={F}:alpha=1,fade=out:st={E - F}:d={F}:alpha=1[bl{k}]",
                      f"[x{k}][bl{k}]overlay=0:0[z{k}]",
                      f"[{n}:v]{crop}scale={w}:{vh},fps={r},format=yuva420p,"
                      f"setpts=PTS-STARTPTS+{S}/TB,{fades}null[f{k}]",
                      f"[z{k}][f{k}]overlay=0:{y}:eof_action=pass[g{k}]",
                      f"[{n + 1}:v]format=rgba,setpts=PTS-STARTPTS+{S}/TB,{fades}null[t{k}]",
                      f"[g{k}][t{k}]overlay=40:{y - lh - 16}:eof_action=pass[b{k + 1}]"]
            base = f"b{k + 1}"
            for j, (txt, frac) in enumerate(it.get("tags", [])):     # 例：上半「荷蘭隊」、下半「台灣隊」
                tp = os.path.join(work, f"tag{k}_{j}.png")
                tag(FONT, tp, txt)
                m = inputs.count("-i")
                inputs += loop + [tp]
                graph += [f"[{m}:v]format=rgba,setpts=PTS-STARTPTS+{S}/TB,{fades}null[p{k}_{j}]",
                          f"[{base}][p{k}_{j}]overlay=16:{y + int(frac * vh) + 14}:eof_action=pass[q{k}_{j}]"]
                base = f"q{k}_{j}"
    return base


def burn(ss, dur, out):
    w, h = display_size()
    os.makedirs(os.path.join(D, "work"), exist_ok=True)
    ass = os.path.join(D, "work", f"{NAME}.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\n\n"
                "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
                "Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
                f"Style: Default,jf-openhuninn-1.1,58,&H00FFFFFF,&H00000000,&H80000000,0,1,5,1,2,40,40,{SUB_MV}\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Text\n")
        for a, b, t in read_srt(SRT):
            f.write(f"Dialogue: 0,{ts(a, '.')[1:-1]},{ts(b, '.')[1:-1]},Default,{color(t, int((b - a) * 1000))}\n")
    esc = lambda p: p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    vf = f"subtitles='{esc(ass)}':fontsdir='{esc(FONTDIR)}'"
    if KEEP:
        sel = "+".join(f"between(t,{a},{b})" for a, b in KEEP)
        vcut, acut = f"select='{sel}',setpts=N/FRAME_RATE/TB,", f"aselect='{sel}',asetpts=N/SR/TB"
    else:
        vcut, acut = "", "anull"
    inputs, graph = ["-i", SRC, "-i", LOGO], [f"[0:v]{vcut}format=yuv420p[b0]"]
    base = insert_graph(inputs, graph, w, h, "b0")
    # iPhone 素材帶 rotation 標記，filter_complex 會把它帶到輸出造成二次旋轉，最後一律拿掉
    graph += [f"[{base}]{vf}[s]", f"[1:v]scale={LOGO_W}:-1[l]",
              f"[s][l]overlay=W-w-{LOGO_M}:{LOGO_M}:format=auto,sidedata=mode=delete:type=DISPLAYMATRIX[v]",
              f"[0:a]{acut}[a]"]
    cmd = [FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]"]
    if dur:
        cmd += ["-ss", str(ss), "-t", str(dur)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("cmd", choices=["make", "burn"])
    ap.add_argument("--ss", type=float, default=0)
    ap.add_argument("--t", type=float, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    setup(a.dir)
    if a.cmd == "make":
        make()
    else:
        burn(a.ss, a.t, a.out or os.path.join(D, f"{OUT_NAME}_字幕版.mp4"))
