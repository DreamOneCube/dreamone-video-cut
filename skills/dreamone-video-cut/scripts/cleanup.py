#!/usr/bin/env python3
"""短影片的剪點：過長停頓（pauses）與句首發語詞（fillers），結果寫進 short.json。

    python cleanup.py --dir <專案> --models <模型資料夾> pauses
    python cleanup.py --dir <專案> --models <模型資料夾> fillers

pauses：辨識段落之間空檔 > 0.6 秒就剪，前後各留 0.15 秒 -> short.json "keep"。
        剪之前把空檔再辨識一次，空檔裡其實有字（例如「以上」「那」被 VAD 漏掉）就往前保留。
fillers：句首「那」（不含那個／那些／那麼…）與單獨的「好，」-> short.json "drops"。
        每個候選都試多組剪點，把剪後的局部音訊重新辨識，只有「前兩字＋後兩字緊接、
        沒留下『呢』『啊』之類殘音」才採用；試不出乾淨剪法的就保留（字幕也保留，寫進 fillers_kept）。
注意：SenseVoice 的字時間比實際聲音早約 0.1–0.2 秒，搜尋範圍要往後偏。
需要 work/<name>.wav（16 kHz 單聲道）與 work/<name>.json（asr.py 輸出）。
"""
import argparse, glob, json, os, re, wave
import numpy as np
import sherpa_onnx

SR = 16000
PUNCT = set("，。？！、,.?! ")
NOT_FILLER_NEXT = set("個些麼裡邊樣種時就个么里边样种时")
GAP, PAD = 0.6, 0.15


def recognizer(models):
    sv = glob.glob(os.path.join(models, "sherpa-onnx-sense-voice-*"))[0]
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=os.path.join(sv, "model.int8.onnx"), tokens=os.path.join(sv, "tokens.txt"),
        use_itn=True, language="zh")


def asr(rec, y):
    st = rec.create_stream(); st.accept_waveform(SR, y); rec.decode_stream(st)
    return st.result


def plain(t):
    return re.sub(r"[，。？！、,.?!\s]", "", t)


def pauses(rec, x, segs):
    dur = len(x) / SR
    keep, a = [], max(0.0, segs[0]["start"] - PAD)
    for s, nx in zip(segs, segs[1:]):
        if nx["start"] - s["end"] <= GAP:
            continue
        b = s["end"] + PAD
        # 空檔連同下一段開頭一起辨識（只辨識空檔容易聽出「喂」之類的幻覺），
        # 下一段第一個字之前、且緊貼著它（0.6 秒內）的字，才算 VAD 漏掉的
        r = asr(rec, x[int(s["end"] * SR):int((nx["start"] + 1.0) * SR)])
        toks = [(u, s["end"] + v) for u, v in zip(r.tokens, r.timestamps) if u not in PUNCT]
        head = plain(nx["text"])[:2]
        got = "".join(u for u, _ in toks)
        k = got.find(head) if head else -1
        toks = [tk for tk in toks[:max(k, 0)] if tk[1] >= nx["start"] - 0.6]
        nxt_start = nx["start"]
        if toks:                                  # 空檔裡有字（VAD 漏掉的）：從那個字開始保留，並補回辨識稿
            nxt_start = toks[0][1]                # 字時間本來就偏早，不必再往前
            nx["text"] = "".join(u for u, _ in toks) + nx["text"]
            nx["start"] = round(nxt_start, 3)
        if nxt_start - PAD - b > 0.3:
            keep.append([round(a, 3), round(b, 3)])
            print(f"剪停頓 {b:7.2f}-{nxt_start - PAD:7.2f}" + (f"（空檔裡有「{''.join(u for u, _ in toks)}」，已保留並補進字幕）" if toks else ""))
            a = nxt_start - PAD
    keep.append([round(a, 3), round(min(dur, segs[-1]["end"] + 0.3), 3)])
    return keep


def fillers(rec, x, segs):
    drops, failed, kept = [], [], []
    for s in segs:
        a = max(0.0, s["start"] - 0.25)
        r = asr(rec, x[int(a * SR):int((s["end"] + 0.1) * SR)])
        toks, tms = r.tokens, r.timestamps
        for i, t in enumerate(toks):
            prev = toks[i - 1] if i else "。"
            rest = [(u, a + v) for u, v in zip(toks[i + 1:], tms[i + 1:]) if u not in PUNCT]
            if prev not in PUNCT or not rest:
                continue
            if not ((t == "那" and rest[0][0] not in NOT_FILLER_NEXT) or (t == "好" and toks[i + 1:i + 2] == ["，"])):
                continue
            tc, tn = a + tms[i], rest[0][1]
            prevw = max([a + v for u, v in zip(toks[:i], tms[:i]) if u not in PUNCT] or [tc - 0.8])
            c0, c1 = max(0.0, tc - 2.5), tn + 2.0            # 局部上下文
            ref = plain(asr(rec, x[int(c0 * SR):int(c1 * SR)]).text)
            k = ref.find(t + rest[0][0])
            if k < 0:
                continue
            want = ref[max(0, k - 2):k] + ref[k + 1:k + 3]    # 前兩字＋後兩字要緊接
            best, lo = None, max(prevw + 0.25, tc - 0.3)       # 起點不要碰到前一個字
            for e in np.arange(tn - 0.05, tn + 0.31, 0.03):    # 終點從早到晚：盡量不吃到下一個字
                for b in np.arange(lo, tc + 0.25, 0.03):       # 起點從早到晚：盡量不留殘音
                    if e - b < 0.1:
                        break
                    y = np.concatenate([x[int(c0 * SR):int(b * SR)], x[int(e * SR):int(c1 * SR)]])
                    if want in plain(asr(rec, y).text):
                        best = (b, e)
                        break
                if best:
                    break
            if best:
                drops.append([round(float(best[0]), 3), round(float(best[1]), 3)])
                print(f"剪「{t}」 {best[0]:7.2f}-{best[1]:7.2f}  {t}{rest[0][0]}")
            else:
                failed.append(f"{tc:.2f} {t}{rest[0][0]}")
                kept.append(t + "".join(u for u, _ in rest[:3]))
    if failed:
        print("剪不乾淨、保留：", failed)
    from opencc import OpenCC
    return drops, [OpenCC("s2twp").convert(k) for k in kept]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--models", required=True)
    ap.add_argument("cmd", choices=["pauses", "fillers"])
    a = ap.parse_args()
    p = os.path.join(a.dir, "short.json")
    cfg = json.load(open(p, encoding="utf-8"))
    w = wave.open(os.path.join(a.dir, "work", f"{cfg['name']}.wav"))
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    segs = json.load(open(os.path.join(a.dir, "work", f"{cfg['name']}.json"), encoding="utf-8"))
    rec = recognizer(a.models)
    if a.cmd == "pauses":
        cfg["keep"] = pauses(rec, x, segs)
        json.dump(segs, open(os.path.join(a.dir, "work", f"{cfg['name']}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
    else:
        cfg["drops"], cfg["fillers_kept"] = fillers(rec, x, segs)
    json.dump(cfg, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
