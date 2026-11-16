#!/bin/zsh
# 把自拍講解影片做成「畫中畫」，疊在動畫的左下／右下角同時播放
#
# 用法：
#   scripts/pip.sh 輸出.mp4 動畫.mp4 自拍.mov
#
# 可用環境變數調整（都有預設值）：
#   CORNER=br       放哪個角落：bl=左下、br=右下
#   PIPW=336        人像框寬度／圓形直徑（px，整支片是 1080 寬）
#                   量過字幕範圍（y 1343–1500）：380 以下不碰字，400 以上會壓到
#   RATIO=9:16      人像框比例，會從自拍裁切（SHAPE=circle 時自動變 1:1）
#   CROPY=0.07      裁切時取畫面的哪個高度：0=最上面、0.5=正中央、1=最下面
#                   預設 0.07 是對直式自拍、臉在上半部的設定
#   BOTTOM=1912     人像框「底邊」的 y 座標。貼著畫面底部，上面才有位置掛名牌
#   MARGIN=40       離左右邊緣的距離
#   FIT=contain     cover=從畫面中央裁一塊（臉大，但手勢會被切掉）
#                   contain=整張塞進框裡，兩側用模糊的自己補滿（頭到手都看得到）
#   SHAPE=circle    circle=正圓、rect=圓角方框
#   RADIUS=32       圓角半徑（SHAPE=rect 時有效）
#   BORDER=6        外框粗細（0 = 不要外框）
#   BCOLOR=white    外框顏色
#   LABEL=           名牌文字（例如 LABEL=樹懶老師；留空＝不要名牌）
#   LPOS=top         名牌掛在框的上緣（top，頭的上面）或下緣（bottom）
#   LOUT=            名牌凸出框外幾 px（預設：上緣凸出七成高度，下緣凸出 10）
#   LSIZE=36         名牌字級
#   LBG=#ffe36e,#ffc928  名牌底色（上,下 漸層；預設是動畫紅色主題的報名標籤配色）
#   LFG=#7a1210      名牌字色
#   LFONT=…          名牌字型檔（預設用 dreamone-cube-reel 附的粉圓體 2.1）
#   SAFE=0           設成 1 會檢查 IG Reels 安全區並警告
#   START=0         自拍從動畫的第幾秒開始出現
#   END=            圓框在動畫的第幾秒收掉（留空＝自拍播完為止）
#                   結尾 44 秒後畫面本來就有真人照片，通常設 END=43.5
#   FADE=0.4        淡入淡出秒數
#   VOL=1.0         自拍的音量倍率
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
  echo "用法：$0 輸出.mp4 動畫.mp4 自拍.mov"
  exit 1
fi
OUT=$1; BASE=$2; FACE=$3
for f in "$BASE" "$FACE"; do
  [[ -f "$f" ]] || { echo "找不到檔案：$f"; exit 1 }
done

CORNER=${CORNER:-br}
PIPW=${PIPW:-336}
RATIO=${RATIO:-9:16}
CROPY=${CROPY:-0.07}
BOTTOM=${BOTTOM:-1912}
MARGIN=${MARGIN:-40}
SHAPE=${SHAPE:-circle}
FIT=${FIT:-contain}
RADIUS=${RADIUS:-32}
BORDER=${BORDER:-6}
BCOLOR=${BCOLOR:-white}
LABEL=${LABEL:-}
LPOS=${LPOS:-top}
LOUT=${LOUT:-}
LSIZE=${LSIZE:-36}
LBG=${LBG:-#ffe36e,#ffc928}
LFG=${LFG:-#7a1210}
if [[ -z "$LFONT" ]]; then
  for f in "$DIR/../../dreamone-cube-reel/template/assets/fonts/jf-openhuninn-2.1.ttf" \
           "$HOME/.claude/skills/dreamone-cube-reel/template/assets/fonts/jf-openhuninn-2.1.ttf"; do
    [[ -f "$f" ]] && { LFONT=$f; break }
  done
fi
START=${START:-0}
END=${END:-}
FADE=${FADE:-0.4}
VOL=${VOL:-1.0}
W=1080; H=1920; FPS=30

[[ $SHAPE == circle ]] && RATIO=1:1
RW=${RATIO%%:*}; RH=${RATIO##*:}
PIPH=$(( PIPW * RH / RW ))
(( PIPH % 2 )) && PIPH=$(( PIPH + 1 ))
[[ $SHAPE == circle ]] && RADIUS=$(( PIPW / 2 ))

# 含外框的整體尺寸
OW=$(( PIPW + BORDER*2 )); OH=$(( PIPH + BORDER*2 )); OR=$(( RADIUS + BORDER ))
X=$MARGIN
[[ $CORNER == br ]] && X=$(( W - OW - MARGIN ))
Y=$(( BOTTOM - OH ))

# IG Reels 安全區檢查（SAFE=1 才檢查。上 270／下 350／左 65／右 120 是各家指南的保守共識，
# Meta 只對廣告公布官方數字）。預設版位是刻意放在安全區外的，所以預設不檢查。
if [[ ${SAFE:-0} == 1 ]]; then
  (( BOTTOM > 1570 )) && echo "⚠ 底邊 ${BOTTOM} 已進入 IG 下方介面區（建議 ≤1570）"
  (( Y < 270 )) && echo "⚠ 上緣 ${Y} 已進入 IG 上方介面區（建議 ≥270）"
  [[ $CORNER == bl ]] && (( MARGIN < 65 )) && echo "⚠ 左邊距 ${MARGIN} 太小（IG 建議 ≥65）"
  [[ $CORNER == br ]] && (( MARGIN < 120 )) && echo "⚠ 右邊距 ${MARGIN} 太小（IG 右側有按鈕列，建議 ≥120）"
fi

BASE_DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$BASE")
FACE_DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$FACE")
HAS_A=$("$FFPROBE" -v error -select_streams a -show_entries stream=index -of csv=p=0 "$FACE" | head -1)
# 自拍比動畫長的話，把動畫最後一格定格補到一樣長，不要剪掉講解
TOTAL=$(python3 -c "print(round(max($BASE_DUR, $START+$FACE_DUR),3))")
PAD=$(python3 -c "print(round(max(0, $TOTAL-$BASE_DUR),3))")
# 圓框實際要出現多久
SHOWN=$FACE_DUR
TRIM=""
if [[ -n "$END" ]]; then
  SHOWN=$(python3 -c "print(round(min($FACE_DUR, max(0.1,$END-$START)),3))")
  TRIM="trim=0:${SHOWN},setpts=PTS-STARTPTS,"
fi
FADE_OUT=$(python3 -c "print(round($SHOWN-$FADE,3))")
DELAY=$(python3 -c "print(int($START*1000))")

echo "人像框 ${PIPW}×${PIPH}（${SHAPE}），位置 x=${X} y=${Y}（${CORNER}），第 ${START} 秒進場"
echo "動畫 ${BASE_DUR}s ／ 自拍 ${FACE_DUR}s → 成品 ${TOTAL}s"
[[ -n "$END" ]] && echo "圓框在第 ${END} 秒收掉（出現 ${SHOWN}s），聲音照常播完"
[[ $(python3 -c "print(1 if $PAD>0.05 else 0)") == 1 ]] && echo "※ 自拍比動畫長 ${PAD}s，動畫最後一格會定格補滿"

# 把自拍變成一塊 PIPW×PIPH 的方形畫面
if [[ $FIT == contain ]]; then
  # 整張塞進去，空出來的地方用放大模糊的同一張補滿
  FACE_CHAIN="[1:v]fps=${FPS},setsar=1,split[fbg][ffg];
[fbg]scale=${PIPW}:${PIPH}:force_original_aspect_ratio=increase,crop=${PIPW}:${PIPH},gblur=sigma=24[fbgb];
[ffg]scale=${PIPW}:${PIPH}:force_original_aspect_ratio=decrease[ffgs];
[fbgb][ffgs]overlay=(W-w)/2:(H-h)/2:format=auto,format=rgba[cut];"
else
  FACE_CHAIN="[1:v]fps=${FPS},crop='min(iw,ih*${RW}/${RH})':'min(ih,iw*${RH}/${RW})':'(iw-ow)/2':'(ih-oh)*${CROPY}',scale=${PIPW}:${PIPH},setsar=1,format=rgba[cut];"
fi

# 遮罩先畫成 PNG 再重複使用，比每一格重算快很多
rounded() { echo "if(lte(hypot(max(abs(X-$1/2)-($1/2-$3),0),max(abs(Y-$2/2)-($2/2-$3),0)),$3),255,0)"; }
MASK=$(mktemp -t pipmask).png
OMASK=$(mktemp -t pipomask).png
"$FFMPEG" -y -v error -f lavfi -i "color=black:s=${PIPW}x${PIPH}" -vf "format=gray,geq=lum='$(rounded $PIPW $PIPH $RADIUS)'" -frames:v 1 "$MASK"
"$FFMPEG" -y -v error -f lavfi -i "color=black:s=${OW}x${OH}" -vf "format=gray,geq=lum='$(rounded $OW $OH $OR)'" -frames:v 1 "$OMASK"

# 有外框就先把人像疊在一塊同形狀的色塊上
if (( BORDER > 0 )); then
  FRAME_FILTER="color=${BCOLOR}:s=${OW}x${OH}:r=${FPS}[bc];[3:v]scale=${OW}:${OH},format=gray[om];[bc][om]alphamerge[bd];[bd][cut2]overlay=${BORDER}:${BORDER}:format=auto[pipraw];"
else
  FRAME_FILTER="[cut2]null[pipraw];"
fi

# 名牌：黃底圓角標籤＋白邊，掛在框的上緣或下緣，凸出框外 LOUT px
NEXT=4
LIN=()
LABEL_FILTER="[pipraw]null[piplab];"
XO=$X
YO=$Y
if [[ -n "$LABEL" ]]; then
  [[ -f "$LFONT" ]] || { echo "找不到名牌字型：$LFONT"; exit 1 }
  LB=4
  # 估字寬：中日韓字一個字寬 1em，其他約 0.55em
  TW=$(python3 -c "import sys; t=sys.argv[1]; print(int(sum(1.0 if ord(c)>0x2E80 else 0.55 for c in t)*$LSIZE))" "$LABEL")
  LW=$(( TW + LSIZE*3/2 )); (( LW % 2 )) && LW=$(( LW + 1 ))
  LH=$(( LSIZE*17/10 )); (( LH % 2 )) && LH=$(( LH + 1 ))
  LWT=$(( LW + LB*2 )); LHT=$(( LH + LB*2 ))
  LPNG=$(mktemp -t piplabel).png
  "$FFMPEG" -y -v error \
    -f lavfi -i "color=white:s=${LWT}x${LHT}" \
    -f lavfi -i "gradients=s=${LW}x${LH}:c0=${LBG%%,*}:c1=${LBG##*,}:x0=0:y0=0:x1=0:y1=${LH}:nb_colors=2" \
    -filter_complex "
[0:v]format=rgba,geq=r=255:g=255:b=255:a='$(rounded $LWT $LHT $((LHT/2)))'[lo];
[1:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='$(rounded $LW $LH $((LH/2)))'[li];
[lo][li]overlay=${LB}:${LB}:format=auto,drawtext=fontfile='${LFONT}':text='${LABEL}':fontsize=${LSIZE}:fontcolor=${LFG}:x=(w-text_w)/2:y=(h-text_h)/2" \
    -frames:v 1 "$LPNG"
  # 畫布要夠寬夠高才放得下名牌
  if [[ $LPOS == top ]]; then
    [[ -z "$LOUT" ]] && LOUT=$(( LHT * 7 / 10 ))
    PY=$LOUT; LY=0; YO=$(( Y - LOUT ))
  else
    [[ -z "$LOUT" ]] && LOUT=10
    PY=0; LY=$(( OH + LOUT - LHT ))
  fi
  CW=$(( OW > LWT ? OW : LWT )); CH=$(( OH + LOUT ))
  PX=$(( (CW - OW) / 2 ))
  XO=$(( X - PX ))
  LIN=(-loop 1 -i "$LPNG")
  LABEL_FILTER="[pipraw]format=rgba,pad=${CW}:${CH}:${PX}:${PY}:color=0x00000000[pp];[${NEXT}:v]format=rgba[lb];[pp][lb]overlay=$(( (CW - LWT) / 2 )):${LY}:format=auto[piplab];"
  NEXT=$(( NEXT + 1 ))
  echo "名牌「${LABEL}」${LWT}×${LHT}，掛在框的$([[ $LPOS == top ]] && echo 上緣 || echo 下緣)，畫面上 y=$(( YO + LY ))–$(( YO + LY + LHT ))"
fi

# 自拍沒有聲音時補一段無聲，才有音軌可以輸出
if [[ -n "$HAS_A" ]]; then
  AUDIO="[1:a]volume=${VOL},adelay=${DELAY}|${DELAY},apad[aout]"
  AIN=()
else
  AUDIO="[${NEXT}:a]atrim=0:0.1,asetpts=N/SR/TB,apad[aout]"
  AIN=(-f lavfi -t 0.1 -i "anullsrc=channel_layout=stereo:sample_rate=48000")
  echo "※ 自拍沒有音軌，成品會是無聲"
fi

"$FFMPEG" -y -i "$BASE" -i "$FACE" -loop 1 -i "$MASK" -loop 1 -i "$OMASK" "${LIN[@]}" "${AIN[@]}" -filter_complex "
[0:v]fps=${FPS},scale=${W}:${H},setsar=1,tpad=stop_mode=clone:stop_duration=${PAD}[base];
${FACE_CHAIN}
[2:v]scale=${PIPW}:${PIPH},format=gray[mk];
[cut][mk]alphamerge[cut2];
${FRAME_FILTER}
${LABEL_FILTER}
[piplab]${TRIM}fade=t=in:st=0:d=${FADE}:alpha=1,fade=t=out:st=${FADE_OUT}:d=${FADE}:alpha=1,setpts=PTS-STARTPTS+${START}/TB[pip];
[base][pip]overlay=${XO}:${YO}:eof_action=pass:format=auto[vout];
${AUDIO}
" -map "[vout]" -map "[aout]" -t "$TOTAL" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r $FPS \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
rm -f "$MASK" "$OMASK" "$LPNG"
echo "完成：$OUT"
