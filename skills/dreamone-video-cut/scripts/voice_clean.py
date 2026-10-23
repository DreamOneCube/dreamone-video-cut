#!/usr/bin/env python3
"""人聲修復：去爆音、降噪、人聲不悶、兩段式響度統一。輸出 48kHz 單聲道 wav。

    python voice_clean.py <影片> <輸出.wav> --mode speech [--rnnoise std.rnnn] [--lufs -16]
    python voice_clean.py <影片> <輸出.wav> --mode music --noise 15.5 21.5 [--lufs -14]

speech：一般環境噪音、鍵盤滑鼠聲（PublishVideo）。adeclip + RNNoise（std.rnnn，GitHub richardpl/arnndn-models）。
music ：背景有音樂（大鼓、貝斯在 150Hz 以下，VID_20261023）。RNNoise 對音樂沒用：
        高通 140Hz×2、拿 --noise 指定的空檔（只有背景、沒講話）當樣本做輕度 afftdn、
        壓 420Hz 箱音、補 3kHz 與 6kHz 以上（降噪太重人聲會悶）。
兩種都用兩段式 loudnorm（先量測、再 linear=true），單段 loudnorm 會把安靜處的噪音一起拉大。
"""
import argparse, json, os, re, shutil, subprocess, tempfile

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def chain(a, tmp):
    if a.mode == "speech":
        return (f"highpass=f=80,adeclip,arnndn=m={a.rnnoise}:mix=0.9,"
                "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=200")
    cmd = os.path.join(tmp, "sn.txt")
    with open(cmd, "w") as f:
        f.write(f"{a.noise[0]} afftdn sn start;\n{a.noise[1]} afftdn sn stop;\n")
    return ("highpass=f=140:p=2,highpass=f=140:p=2,"
            f"asendcmd=f={cmd},afftdn=nr=12:nf=-40:tn=0,"
            "equalizer=f=420:t=q:w=1.2:g=-5,equalizer=f=3000:t=q:w=1:g=6,highshelf=f=6000:g=6,"
            "acompressor=threshold=-20dB:ratio=2:attack=8:release=200")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--mode", choices=["speech", "music"], required=True)
    ap.add_argument("--noise", type=float, nargs=2, help="music 模式：只有背景、沒講話的區段（秒）")
    ap.add_argument("--rnnoise", default=os.path.expanduser("~/Desktop/video cut/tools/rnnoise/std.rnnn"))
    ap.add_argument("--lufs", type=float)
    a = ap.parse_args()
    if a.mode == "music" and not a.noise:
        ap.error("music 模式要用 --noise 指定一段只有背景音樂的空檔")
    lufs = a.lufs or (-14 if a.mode == "music" else -16)
    with tempfile.TemporaryDirectory() as tmp:
        pre = chain(a, tmp)
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", a.src, "-vn", "-ac", "1", "-af",
                            f"{pre},loudnorm=I={lufs}:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True)
        m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr).group(0))
        ln = (f"loudnorm=I={lufs}:TP=-1.5:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", a.src, "-vn", "-ac", "1", "-af", f"{pre},{ln},aresample=48000",
                        "-ar", "48000", "-c:a", "pcm_s16le", a.out], check=True)
    print("->", a.out)


if __name__ == "__main__":
    main()
