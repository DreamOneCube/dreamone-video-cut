#!/usr/bin/env python3
"""Plan one finished video: overlay PNGs + units.json + SRT/TXT.  Runs in the CLOUD sandbox.

    python3 build.py --config config.json --edl edl.json --out <dir>

config.json  — see config.example.json (title, logo, font, chapters, layout, terms, output_name)
edl.json     — ordered list of clips:
    {"clip_id": "4-2", "path": "<path relative to the project folder on the Mac>",
     "chapter": "一步底", "tin": 1.04, "tout": 120.16, "gain_db": 9.0,
     "segs": [...ASR segments...]  or  "segs_file": "audio/4-2.json",
     "drops": [[s, e], ...]}            # jump cuts, source-time seconds
Clips play in list order; each chapter's clips must be contiguous and follow config["chapters"] order.

Writes into <out>: base_<k>.png, bar_<i>.png, dot.png, top.png, units.json,
<output_name>_字幕.srt, <output_name>_字幕.txt.  Copy the whole folder plus run.py to the Mac.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subtitles import clean, load_terms, split_text  # noqa: E402

W, H = 1920, 1080
STRIP_H, BAND_H = 176, 150          # top chapter strip, bottom CC band
TRACK_Y, X0, X1, GAP, MINW = 100, 40, 1880, 8, 210
CROP_FRAC = 73 / 900                # trim ~8% top+bottom of the source before fitting
BAR = (14, 17, 22, 255); RED = (214, 54, 43, 255); WHITE = (255, 255, 255, 255)
GREY = (138, 147, 163, 255); LINE = (46, 54, 65, 255); DIM = (90, 98, 112, 255)


def mmss(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def srt_ts(s):
    total_ms = max(0, int(round(s * 1000)))
    seconds, ms = divmod(total_ms, 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def even(x):
    return int(round(x / 2)) * 2


def keep_ranges(c):
    keep = [[c["tin"], c["tout"]]]
    for ds, de in sorted(c.get("drops", [])):
        nk = []
        for s, e in keep:
            if de <= s or ds >= e:
                nk.append([s, e]); continue
            if ds > s: nk.append([s, ds])
            if de < e: nk.append([de, e])
        keep = nk
    return [r for r in keep if r[1] - r[0] > 0.05]          # never emit empty units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--edl", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")); clips = json.load(open(a.edl, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.config))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    os.makedirs(a.out, exist_ok=True)
    CH = cfg["chapters"]; lay = cfg.get("layout", {}); chunk = cfg.get("chunk_seconds", 55)
    top_on, band_on = lay.get("top_strip", True), lay.get("cc_band", True)
    terms = load_terms(*[rel(p) for p in cfg.get("terms", [])])
    F = lambda s: ImageFont.truetype(rel(cfg["font"]), s)

    # ---- timeline -------------------------------------------------------------------------
    units, G, ch_start, last_ci = [], 0.0, {}, -1
    for c in clips:
        ci = CH.index(c["chapter"])
        assert ci >= last_ci, f"clip {c['clip_id']}: chapter order breaks config['chapters']"
        last_ci = ci
        n_for_clip = 0
        for s, e in keep_ranges(c):
            n = max(1, round((e - s) / chunk)); L = (e - s) / n
            for k in range(n):
                ua = s + k * L; ub = e if k == n - 1 else s + (k + 1) * L
                ch_start.setdefault(ci, G)
                units.append(dict(id=f"{c['clip_id']}_{n_for_clip:02d}", clip=c["clip_id"], src=c["path"],
                                  a=round(ua, 3), b=round(ub, 3), G=round(G, 3), chapter=ci, gain=c.get("gain_db", 0)))
                n_for_clip += 1; G += ub - ua
    TOTAL = G
    missing = [CH[i] for i in range(len(CH)) if i not in ch_start]
    assert not missing, f"chapters with no clips: {missing}"
    bounds = [ch_start[i] for i in range(len(CH))] + [TOTAL]
    print(f"{cfg['output_name']}: {mmss(TOTAL)} ({TOTAL:.1f}s), {len(units)} units, chapters at {[mmss(b) for b in bounds[:-1]]}")

    # ---- geometry -------------------------------------------------------------------------
    strip = STRIP_H if top_on else 0; band = BAND_H if band_on else 0
    vh = H - strip - band
    sh = even(vh / (1 - 2 * CROP_FRAC)); sw = even(sh * 16 / 9)
    if sw >= W: sw, sh = W, H
    crop_y = max(0, (sh - vh) // 2); vx = (W - sw) // 2
    n = len(CH); avail = (X1 - X0) - GAP * (n - 1)
    w = [(bounds[i + 1] - bounds[i]) / TOTAL * avail for i in range(n)]
    small = [i for i in range(n) if w[i] < MINW]
    rest = avail - MINW * len(small); big = sum(w[i] for i in range(n) if i not in small) or 1
    w = [MINW if i in small else w[i] * rest / big for i in range(n)]
    seg, x = [], X0
    for i in range(n):
        seg.append((int(round(x)), int(round(x + w[i])))); x += w[i] + GAP

    # ---- overlay PNGs ---------------------------------------------------------------------
    logo = Image.open(rel(cfg["logo"])).convert("RGBA"); logo = logo.crop(logo.getbbox())
    title = cfg.get("title", "")
    for k in range(n):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if top_on:
            d.rectangle([0, 0, W, strip], fill=BAR); d.line([0, strip, W, strip], fill=LINE, width=2)
            for i, (sa, sb) in enumerate(seg):
                d.rounded_rectangle([sa, TRACK_Y, sb, TRACK_Y + 10], 5, fill=LINE)
                lab = f"{i + 1}  {CH[i]}"; fs = 32 if i == k else 30
                while d.textlength(lab, font=F(fs)) > (sb - sa) - 4 and fs > 18: fs -= 2
                d.text((sa, 38 + (32 - fs) // 2), lab, font=F(fs), fill=WHITE if i == k else (GREY if i < k else DIM))
                d.text((sa, 118), mmss(bounds[i]), font=F(20), fill=GREY if i == k else DIM)
            d.text((X1 - d.textlength(mmss(TOTAL), font=F(20)), 118), mmss(TOTAL), font=F(20), fill=DIM)
        if band_on:
            d.rectangle([0, H - band, W, H], fill=(0, 0, 0, 255)); d.line([0, H - band, W, H - band], fill=LINE, width=2)
            r = min(320 / logo.width, (band - 40) / logo.height)   # fit width 320 and the band height
            lg = logo.resize((int(logo.width * r), int(logo.height * r)), Image.LANCZOS)
            im.paste(lg, (40, H - band + (band - lg.height) // 2), lg)
            if title: d.text((X1 - d.textlength(title, font=F(40)), H - band + (band - 52) // 2), title, font=F(40), fill=WHITE)
        else:
            r = min(360 / logo.width, 110 / logo.height)
            lg = logo.resize((int(logo.width * r), int(logo.height * r)), Image.LANCZOS)
            im.paste(lg, (40, H - 40 - lg.height), lg)
            if title: d.text((X1 - d.textlength(title, font=F(44)), H - 100), title, font=F(44), fill=WHITE)
        im.save(os.path.join(a.out, f"base_{k}.png"))
    if top_on:
        top = Image.new("RGBA", (W, strip), (0, 0, 0, 0)); d = ImageDraw.Draw(top)
        d.rectangle([0, TRACK_Y - 8, X0 - 1, TRACK_Y + 18], fill=BAR); d.rectangle([X1 + 1, TRACK_Y - 8, W, TRACK_Y + 18], fill=BAR)
        for i in range(n - 1): d.rectangle([seg[i][1] + 1, TRACK_Y - 8, seg[i + 1][0] - 1, TRACK_Y + 18], fill=BAR)
        top.save(os.path.join(a.out, "top.png"))
        for i, (sa, sb) in enumerate(seg):
            b = Image.new("RGBA", (sb - sa, 10), (0, 0, 0, 0)); ImageDraw.Draw(b).rounded_rectangle([0, 0, sb - sa - 1, 9], 5, fill=RED)
            b.save(os.path.join(a.out, f"bar_{i}.png"))
        dot = Image.new("RGBA", (22, 22), (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, 21, 21], fill=WHITE); dot.save(os.path.join(a.out, "dot.png"))

    # ---- subtitles: raw ASR, mechanically cleaned -----------------------------------------
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    segs_of = {}
    for c in clips:
        segs_of[c["clip_id"]] = c["segs"] if "segs" in c else json.load(open(os.path.join(edl_dir, c["segs_file"]), encoding="utf-8"))
    lines = []
    clip_G = 0.0
    for c in clips:
        ranges = []
        mapped_G = clip_G
        for a0, b0 in keep_ranges(c):
            ranges.append((a0, b0, mapped_G))
            mapped_G += b0 - a0
        for s in segs_of[c["clip_id"]]:
            overlaps = []
            for a0, b0, g0 in ranges:
                st, en = max(s["start"], a0), min(s["end"] + 0.25, b0)
                if en - st > 0.2:
                    overlaps.append((g0 + st - a0, g0 + en - a0))
            if not overlaps: continue
            # An ASR sentence is emitted once, independently of encoding chunks.
            st, en = overlaps[0][0], overlaps[-1][1]
            if len(overlaps) > 1:
                print(f"字幕跨剪點，請校對: {c['clip_id']} {s['start']:.2f}s", file=sys.stderr)
            txt = clean(s["text"], terms)
            if not txt: continue
            pieces = split_text(txt); tot = sum(len(p) for p in pieces) or 1; t = st
            for p in pieces:
                dur = (en - st) * len(p) / tot
                lines.append((t, t + dur, p)); t += dur
        clip_G = mapped_G
    name = cfg["output_name"]
    with open(os.path.join(a.out, f"{name}_字幕.srt"), "w", encoding="utf-8") as f:
        for i, (s, e, p) in enumerate(lines, 1): f.write(f"{i}\n{srt_ts(s)} --> {srt_ts(e)}\n{p}\n\n")
    txt, ch = [], -1
    for s, e, p in lines:
        while ch + 1 < n and s >= bounds[ch + 1] - 0.01:
            ch += 1; txt.append(f"\n【{ch + 1}. {CH[ch]}】")
        txt.append(p)
    open(os.path.join(a.out, f"{name}_字幕.txt"), "w", encoding="utf-8").write("\n".join(txt).strip() + "\n")

    # ---- per-unit overlay expressions (ffmpeg 4.4: drawbox has no t, so use overlay x) -----
    for u in units:
        G0 = u["G"]; u["bars"] = []; u["dotx"] = None
        if top_on:
            for i, (sa, sb) in enumerate(seg):
                g0, g1 = bounds[i], bounds[i + 1]; ww = sb - sa
                u["bars"].append(dict(x=f"{sa}-{ww}+{ww}*clip((t+{G0:.3f}-{g0:.3f})/{g1 - g0:.3f},0,1)",
                                      enable=f"gte(t+{G0:.3f},{g0:.3f})"))
            u["dotx"] = "(" + "+".join(
                f"gte(t+{G0:.3f},{bounds[i]:.3f})*lt(t+{G0:.3f},{bounds[i + 1]:.3f})*({sa}+{sb - sa}*(t+{G0:.3f}-{bounds[i]:.3f})/{bounds[i + 1] - bounds[i]:.3f})"
                for i, (sa, sb) in enumerate(seg)) + ")-11"
    json.dump(dict(output_name=name, total=TOTAL, bounds=bounds, chapters=CH, units=units,
                   geom=dict(strip=strip, band=band, vh=vh, sw=sw, sh=sh, crop_y=crop_y, vx=vx, track_y=TRACK_Y)),
              open(os.path.join(a.out, "units.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(lines)} subtitle lines -> {name}_字幕.srt / .txt")


if __name__ == "__main__":
    main()
