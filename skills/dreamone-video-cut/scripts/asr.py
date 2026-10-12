#!/usr/bin/env python3
"""Speech recognition for 16 kHz mono WAVs -> segment JSON.  Runs in the CLOUD sandbox.

    python3 asr.py --models <dir> a.wav b.wav ...
writes a.json, b.json next to each wav:  [{"start": s, "end": e, "text": "..."}, ...]

One-time setup (HuggingFace is blocked; GitHub releases work):
    pip install sherpa-onnx --break-system-packages
    curl -L -O https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2
    curl -L -O https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
    tar xjf sherpa-onnx-sense-voice-*.tar.bz2
Pass the directory holding both as --models.

Make the WAVs on the Mac (keeps the big video there):
    ffmpeg -i clip.MOV -vn -ac 1 -ar 16000 -c:a pcm_s16le clip.wav
"""
import argparse
import glob
import json
import os
import wave

import numpy as np
import sherpa_onnx


def load(models, lang):
    sv = glob.glob(os.path.join(models, "sherpa-onnx-sense-voice-*"))[0]
    rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=os.path.join(sv, "model.int8.onnx"), tokens=os.path.join(sv, "tokens.txt"),
        num_threads=4, use_itn=True, language=lang)
    v = sherpa_onnx.VadModelConfig()
    v.silero_vad.model = os.path.join(models, "silero_vad.onnx")
    v.silero_vad.threshold = 0.5
    v.silero_vad.min_silence_duration = 0.35
    v.silero_vad.min_speech_duration = 0.25
    v.silero_vad.max_speech_duration = 12
    v.sample_rate = 16000
    return rec, v


def transcribe(path, rec, vcfg):
    with wave.open(path) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            raise ValueError("WAV must be 16 kHz, mono, 16-bit PCM")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    vad = sherpa_onnx.VoiceActivityDetector(vcfg, buffer_size_in_seconds=60)
    win, segs = vcfg.silero_vad.window_size, []

    def drain():
        while not vad.empty():
            seg = vad.front
            st = rec.create_stream()
            st.accept_waveform(16000, seg.samples)
            rec.decode_stream(st)
            segs.append({"start": round(seg.start / 16000, 3),
                         "end": round((seg.start + len(seg.samples)) / 16000, 3),
                         "text": st.result.text.strip()})
            vad.pop()

    for i in range(0, len(data), win):
        vad.accept_waveform(data[i:i + win])
        drain()
    vad.flush()
    drain()
    return segs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--lang", default="zh")
    ap.add_argument("wavs", nargs="+")
    a = ap.parse_args()
    rec, vcfg = load(a.models, a.lang)
    for p in a.wavs:
        segs = transcribe(p, rec, vcfg)
        json.dump(segs, open(os.path.splitext(p)[0] + ".json", "w"), ensure_ascii=False, indent=0)
        print(f"## {os.path.basename(p)}: {len(segs)} segs")
        for s in segs:
            print(f"[{s['start']:7.2f}-{s['end']:7.2f}] {s['text']}")
