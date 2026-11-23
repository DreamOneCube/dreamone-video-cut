#!/bin/zsh
# 幫成品墊上背景音樂，並把整體響度校到發布標準
#
# 用法：
#   scripts/music.sh 輸出.mp4 無配樂的成品.mp4 音樂.mp3
#
# 可用環境變數調整：
#   BED=13       音樂比人聲小幾 dB（越大越小聲。團隊規範是「約 10 dB」，
#                這裡保守一點用 13，嫌音樂太小聲就調成 10）
#   VOICE=-15    人聲校到多少 LUFS（-16 的話墊了配樂成品會掉到 -16.2，低於標準）
#   SKIP=0       音樂從第幾秒開始用（前奏太長時跳過）
#   FADEIN=0.4   音樂淡入秒數
#   FADEOUT=1.5  音樂淡出秒數
#
# 畫面不會重新壓縮，只換聲音。限幅器設在 -1.5 dBFS：AAC 壓縮後會過衝約 0.1～0.3 dB，
# 留一點餘裕，成品的真實峰值才會在 -1 dBFS 以下。
set -e
DIR=${0:A:h}
find_tool() {  # 找 ffmpeg／ffprobe：環境變數 → scripts/bin/ → 系統 PATH
  local name=$1 preset=$2
  if [[ -n "$preset" ]]; then echo "$preset"; return; fi
  if [[ -x "$DIR/bin/$name" ]]; then echo "$DIR/bin/$name"; return; fi
  command -v "$name" || { echo "找不到 $name。請先安裝 ffmpeg，或用環境變數 ${name:u} 指定路徑" >&2; exit 1 }
}
FFMPEG=$(find_tool ffmpeg "$FFMPEG")
FFPROBE=$(find_tool ffprobe "$FFPROBE")

if [[ $# -lt 3 ]]; then
  echo "用法：$0 輸出.mp4 無配樂的成品.mp4 音樂.mp3"
  exit 1
fi
OUT=$1; VIDEO=$2; MUSIC=$3
for f in "$VIDEO" "$MUSIC"; do
  [[ -f "$f" ]] || { echo "找不到檔案：$f"; exit 1 }
done

BED=${BED:-13}
VOICE=${VOICE:-15}; VOICE=${VOICE#-}   # 寫 16 或 -16 都可以
SKIP=${SKIP:-0}
FADEIN=${FADEIN:-0.4}
FADEOUT=${FADEOUT:-1.5}

DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$VIDEO")

# 量響度（LUFS）
lufs() {
  "$FFMPEG" -hide_banner -nostats "$@" -af loudnorm=print_format=json -f null - 2>&1 \
    | python3 -c "import sys,re,json; t=sys.stdin.read(); print(json.loads(re.search(r'\{[^{}]*input_i[^{}]*\}',t,re.S).group(0))['input_i'])"
}
V_NOW=$(lufs -i "$VIDEO")
M_NOW=$(lufs -ss "$SKIP" -t "$DUR" -i "$MUSIC")
V_GAIN=$(python3 -c "print(round(-$VOICE - ($V_NOW), 2))")
M_GAIN=$(python3 -c "print(round(-$VOICE - $BED - ($M_NOW), 2))")
FO_AT=$(python3 -c "print(round($DUR - $FADEOUT, 3))")

echo "人聲 ${V_NOW} LUFS → 調 ${V_GAIN} dB（目標 -${VOICE}）"
echo "音樂 ${M_NOW} LUFS → 調 ${M_GAIN} dB（比人聲小 ${BED} dB）"

"$FFMPEG" -y -v error -i "$VIDEO" -ss "$SKIP" -t "$DUR" -i "$MUSIC" -filter_complex "
[0:a]volume=${V_GAIN}dB[v];
[1:a]aresample=48000,volume=${M_GAIN}dB,afade=t=in:d=${FADEIN},afade=t=out:st=${FO_AT}:d=${FADEOUT},apad[m];
[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:level=disabled[a]
" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 -t "$DUR" -movflags +faststart "$OUT"

# 驗收：量成品
"$FFMPEG" -hide_banner -nostats -i "$OUT" -af loudnorm=print_format=json -f null - 2>&1 \
  | python3 -c "
import sys,re,json
d=json.loads(re.search(r'\{[^{}]*input_i[^{}]*\}',sys.stdin.read(),re.S).group(0))
i=float(d['input_i']); tp=float(d['input_tp'])
print(f'成品 {i:.1f} LUFS（標準 -16～-14）{\"✓\" if -16.5<=i<=-13.5 else \"⚠\"}　峰值 {tp:.1f} dBFS（標準 ≤ -1）{\"✓\" if tp<=-0.9 else \"⚠\"}')"
echo "完成：$OUT"
