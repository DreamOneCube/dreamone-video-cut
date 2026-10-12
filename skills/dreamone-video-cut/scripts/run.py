#!/usr/bin/env python3
"""Encode a planned video unit-by-unit.  Runs on the MAC via device_bash.

Put this file in the plan folder written by build.py (next to units.json), then:
    python3 run.py --root "<project folder>" run        # encode pending units for ~25 s of wall time, then stop
    python3 run.py --root "<project folder>" status
    python3 run.py --root "<project folder>" concat     # join units -> <project>/<output_name>_初剪_v1.mp4
    python3 run.py --root "<project folder>" shots      # 6 check frames -> check_sheet.jpg
    python3 run.py --root "<project folder>" test <unit_id> <offset_s> <dur_s>   # short preview clip

Why the odd shape: device_bash kills each call at 180 s and kills background processes too,
so every call does a bounded amount of work, records .done markers, and can be re-run safely.
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "units.json"), encoding="utf-8"))
U, GEO = P["units"], P["geom"]
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
BUDGET = 25          # stop starting new units after this many seconds (one unit takes 60-130 s)
PRESET = os.environ.get("PRESET", "superfast")   # use "slow" for a smaller final file


def args():
    a = sys.argv[1:]
    if "--root" not in a: sys.exit("usage: run.py --root <project folder> run|status|concat|shots|test ...")
    i = a.index("--root"); root = a[i + 1]; rest = a[:i] + a[i + 2:]
    return os.path.expanduser(root), (rest or ["run"])


def cmd_for(root, u, a, b, out):
    g = GEO; nb = len(u["bars"])
    fc = [f"[0:v]fps=30,scale={g['sw']}:{g['sh']},crop={g['sw']}:{g['vh']}:0:{g['crop_y']},"
          f"pad=1920:1080:{g['vx']}:{g['strip']}:color=black[v0]",
          "[v0][1:v]overlay=0:0:format=auto[v1]"]
    prev = "v1"
    if nb:
        for i, bar in enumerate(u["bars"]):
            fc.append(f"[{prev}][{3 + i}:v]overlay=x='{bar['x']}':y={g['track_y']}:enable='{bar['enable']}':format=auto[b{i}]"); prev = f"b{i}"
        fc.append(f"[{prev}][2:v]overlay=0:0:format=auto[v2]")
        fc.append(f"[v2][{3 + nb}:v]overlay=x='{u['dotx']}':y={g['track_y'] - 6}:format=auto[v]")
    else:
        fc[-1] = "[v0][1:v]overlay=0:0:format=auto[v]"
    c = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-threads", "4",
         "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", os.path.join(root, u["src"]),
         "-i", os.path.join(HERE, f"base_{u['chapter']}.png")]
    if nb:
        c += ["-i", os.path.join(HERE, "top.png")]
        for i in range(nb): c += ["-i", os.path.join(HERE, f"bar_{i}.png")]
        c += ["-i", os.path.join(HERE, "dot.png")]
    c += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a", "-af", f"volume={u['gain']}dB",
          "-c:v", "libx264", "-preset", PRESET, "-crf", "20", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "160k", "-ar", "48000", out]
    return c


def done(u): return os.path.exists(os.path.join(OUT, u["id"] + ".mp4.done"))


def run(root):
    t0 = time.time()
    for u in U:
        if done(u): continue
        if time.time() - t0 > BUDGET: break
        mp4 = os.path.join(OUT, u["id"] + ".mp4"); s = time.time()
        r = subprocess.run(cmd_for(root, u, u["a"], u["b"], mp4), capture_output=True, text=True)
        if r.returncode: print(f"FAIL {u['id']}\n{r.stderr[-1500:]}"); sys.exit(1)
        open(mp4 + ".done", "w").write("ok")
        print(f"done {u['id']} ({u['b'] - u['a']:.1f}s video in {time.time() - s:.0f}s)")
    status()


def status():
    d = sum(done(u) for u in U); print(f"{d}/{len(U)} units done"); return d == len(U)


def concat(root):
    if not status(): sys.exit("not all units are done")
    lst = os.path.join(HERE, "concat.txt")
    def quote_path(path):
        return path.replace("'", "'\\''")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{quote_path(os.path.join(OUT, u['id'] + '.mp4'))}'\n" for u in U))
    out = os.path.join(root, f"{P['output_name']}_初剪_v1.mp4")
    # no +faststart: rewriting a 2 GB file to move the moov atom overruns the 180 s limit
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", out], capture_output=True, text=True)
    print("concat", "ok -> " + out if r.returncode == 0 else r.stderr[-800:])
    if r.returncode: sys.exit(r.returncode)
    for ext in ("srt", "txt"):
        name = f"{P['output_name']}_字幕.{ext}"
        source, target = os.path.join(HERE, name), os.path.join(root, name)
        if os.path.abspath(source) != os.path.abspath(target):
            shutil.copy2(source, target)


def shots(root):
    from PIL import Image
    out = os.path.join(root, f"{P['output_name']}_初剪_v1.mp4"); T = P["total"]; ims = []
    for k, f in enumerate((0.02, 0.2, 0.4, 0.6, 0.8, 0.98)):
        p = os.path.join(HERE, f"check_{k}.jpg")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{T * f:.1f}", "-i", out, "-frames:v", "1", "-vf", "scale=960:-1", p], check=True)
        ims.append(Image.open(p))
    w, h = ims[0].size; s = Image.new("RGB", (w * 2, h * 3))
    for i, im in enumerate(ims): s.paste(im, ((i % 2) * w, (i // 2) * h))
    s.save(os.path.join(HERE, "check_sheet.jpg"), quality=80); print("check_sheet.jpg")


def test(root, uid, off, dur):
    u = next(x for x in U if x["id"] == uid); out = os.path.join(HERE, f"test_{uid}.mp4")
    r = subprocess.run(cmd_for(root, u, u["a"] + off, u["a"] + off + dur, out), capture_output=True, text=True)
    print("ok -> " + out if r.returncode == 0 else r.stderr[-1500:])
    if r.returncode: sys.exit(r.returncode)


if __name__ == "__main__":
    root, a = args()
    {"run": lambda: run(root), "status": status, "concat": lambda: concat(root), "shots": lambda: shots(root),
     "test": lambda: test(root, a[1], float(a[2]), float(a[3]))}[a[0]]()
