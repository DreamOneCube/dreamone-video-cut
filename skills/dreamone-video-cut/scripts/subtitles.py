"""Subtitle cleaning for raw ASR output (no rewriting).

clean(text, terms)  -> Traditional Chinese, glossary terms fixed, pure fillers removed.
split_text(text)    -> list of display lines (<= MAXLEN chars), split on punctuation first.

`terms` is a list of [regex, replacement] pairs loaded from terms/*.json.
Load several files and concatenate: common.json first, then the topic file.
"""
import json
import re

try:
    from opencc import OpenCC
    _CC = OpenCC("s2twp")
except Exception:  # pragma: no cover - opencc missing
    _CC = None

MAXLEN = 26

# Mainland -> Taiwan wording that OpenCC s2twp misses.
_TW_FIXES = [(r"迴圈", "循環")]

# Pure filler tokens. Only standalone particles are removed; words are left alone.
_FILLERS = [
    (r"(?<![A-Za-z])[oO][kK]+(?![A-Za-z])[，。]?", ""),
    (r"(?:^|(?<=[\s，。！？；]))[呃啊哦哈呵呢]+(?:[，。]|$)", ""),
    (r"[，。]{2,}", "，"),
    (r"^[，。、\s]+", ""),
    (r"，$", "。"),
]


def load_terms(*paths):
    """Concatenate [pattern, replacement] lists from JSON files."""
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            out.extend(json.load(f))
    return out


def clean(text, terms=()):
    if _CC is None:
        raise RuntimeError("請先安裝 opencc-python-reimplemented，避免未轉繁體就輸出字幕")
    t = _CC.convert(text) if _CC else text
    for p, r in _TW_FIXES:
        t = re.sub(p, r, t)
    for p, r in terms:
        t = re.sub(p, r, t)
    for p, r in _FILLERS:
        t = re.sub(p, r, t)
    t = re.sub(r"\s+", " ", t).strip(" ，。")
    # half-width space between CJK and Latin
    t = re.sub(r"([一-鿿])([A-Za-z])", r"\1 \2", t)
    t = re.sub(r"([A-Za-z])([一-鿿])", r"\1 \2", t)
    return t


def split_text(t, maxlen=MAXLEN):
    parts = [p for p in re.split(r"(?<=[。？！，；])", t) if p.strip()]
    out, cur = [], ""
    for p in parts:
        if not cur or len(cur) + len(p) <= maxlen:
            cur += p
        else:
            out.append(cur)
            cur = p
        while len(cur) > maxlen:  # hard wrap, never inside a Latin word
            k = maxlen
            while k > maxlen - 8 and cur[k - 1].isascii() and cur[k].isascii() and cur[k - 1] != " ":
                k -= 1
            out.append(cur[:k].strip())
            cur = cur[k:].strip()
    if cur:
        out.append(cur)
    return [x.strip("，；") for x in out if x.strip("，；。")]
