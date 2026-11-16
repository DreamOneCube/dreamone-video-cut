#!/bin/zsh
# 查影片規格：scripts/probe.sh 影片.mp4
DIR=${0:A:h}
find_tool() {  # 找 ffmpeg／ffprobe：環境變數 → scripts/bin/ → 系統 PATH
  local name=$1 preset=$2
  if [[ -n "$preset" ]]; then echo "$preset"; return; fi
  if [[ -x "$DIR/bin/$name" ]]; then echo "$DIR/bin/$name"; return; fi
  command -v "$name" || { echo "找不到 $name。請先安裝 ffmpeg，或用環境變數 ${name:u} 指定路徑" >&2; exit 1 }
}
FFMPEG=$(find_tool ffmpeg "$FFMPEG")
FFPROBE=$(find_tool ffprobe "$FFPROBE")
if [[ -z "$1" ]]; then echo "用法：$0 <影片檔>"; exit 1; fi
"$FFPROBE" -v error -show_entries \
  format=duration,size,bit_rate:stream=index,codec_type,codec_name,profile,width,height,r_frame_rate,nb_frames,sample_rate,channels,bit_rate \
  -of default=noprint_wrappers=1 "$1"
