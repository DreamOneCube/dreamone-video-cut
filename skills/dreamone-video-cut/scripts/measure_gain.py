#!/usr/bin/env python3
"""Measure loudness per clip and write gain_db into the EDL.  Runs on the MAC via device_bash.

    python3 measure_gain.py --root "<project folder>" edl.json [--target -19]

For each clip, measures mean_volume over [tin, tout] with volumedetect and sets
gain_db = target - mean_volume.  A fixed per-clip gain keeps loudness identical across
units encoded separately (loudnorm is adaptive and would differ unit to unit).
Long projects: run on a slice of the EDL per call (--only 4-1,4-2) to stay under 180 s.
"""
import argparse
import json
import os
import re
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True); ap.add_argument("edl"); ap.add_argument("--target", type=float, default=-19.0)
ap.add_argument("--only", default="")
a = ap.parse_args()
edl = json.load(open(a.edl, encoding="utf-8")); only = set(filter(None, a.only.split(",")))
for c in edl:
    if only and c["clip_id"] not in only: continue
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-ss", str(c["tin"]), "-to", str(c["tout"]),
                        "-i", os.path.join(os.path.expanduser(a.root), c["path"]), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+)", r.stderr)
    if not m: print(f"{c['clip_id']}: no audio?"); continue
    c["gain_db"] = round(a.target - float(m.group(1)), 1)
    print(f"{c['clip_id']}: mean {m.group(1)} dB -> gain {c['gain_db']} dB")
json.dump(edl, open(a.edl, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
