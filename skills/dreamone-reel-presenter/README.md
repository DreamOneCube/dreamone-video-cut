# dreamone-reel-presenter

夢想一號「方塊動畫＋真人講解」Reel 的合成 Skill：動畫由同事用程式做好放在 GitHub，講師自拍講解，這裡把兩邊合成一支 1080×1920 的定稿——挑取樣、對切點、變速、讓動畫配合人聲、疊右下角的人像圓框與名牌、墊配樂。

給 Claude／Codex 用：把整個資料夾放進 skills，之後說「01 的講解錄好了，幫我合進動畫」就會照 `SKILL.md` 的流程走。片單在 [`docs/videos.md`](../../docs/videos.md)。

```
SKILL.md                      規則、編號與片單、十個步驟、驗收清單（從這裡開始讀）
references/lessons.md         01 踩過的 18 個坑：原因與現在的做法
references/animation-hook.md  動畫專案怎麼接時間軸掛鉤；做動畫的人可以先留的東西
references/music.md           配樂來源、授權、用過的曲目、混音設定
template/timing.js            時間軸掛鉤，複製到動畫專案的 src/
cuts.example.json             剪輯清單的格式與欄位說明
requirements.txt              語音辨識需要的 Python 套件
scripts/transcribe.py         把錄影抄成帶時間碼的逐字稿（本機 faster-whisper）
scripts/snap.py               把剪接點對到安靜處，並檢查有沒有切到字
scripts/assemble.py           照剪輯清單接旁白、變速、算出動畫的新時間軸
scripts/pip.sh                把講解做成圓框＋名牌疊到動畫上
scripts/music.sh              墊配樂、校響度
scripts/probe.sh              查影片規格
```

## 本機準備

**ffmpeg**（要有 libx264 和 aac，6.0 以上）。工具依序找：環境變數 `FFMPEG`／`FFPROBE` → `scripts/bin/` → 系統 PATH。
Mac 上沒有 Homebrew 的話，可以用 npm 裝一份放在專案旁邊：

```bash
npm install ffmpeg-static ffprobe-static
export FFMPEG="$PWD/node_modules/ffmpeg-static/ffmpeg"
export FFPROBE="$PWD/node_modules/ffprobe-static/bin/darwin/arm64/ffprobe"
```

**Python**：`transcribe.py` 和 `snap.py` 要裝 `requirements.txt`，請用 3.10～3.13。系統的 Python 太新（3.14 以上）會裝不起來，用 `uv` 另外帶一個：

```bash
pip install uv
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

之後用 `.venv/bin/python scripts/transcribe.py …`。`assemble.py` 只用標準函式庫，系統的 python3 就能跑。

**語音辨識模型**第一次執行會下載（small 約 460MB），預設放在 `~/.cache/dreamone-asr`，可以用環境變數 `ASR_MODELS` 換位置。辨識全程在本機，聲音不會送出去。

**字型**：名牌用 dreamone-cube-reel 附的粉圓體 2.1，兩個 skill 放在同一層就找得到；也可以用 `LFONT` 指定。

**Node**：重新匯出動畫要跑動畫專案自己的預覽頁（`npm install`、`npm start`），依動畫專案的說明。

## 一支片從頭到尾的指令

```bash
# 3. 抄稿
.venv/bin/python scripts/transcribe.py 01_片名/素材/主檔.MOV --script 01_片名/逐字稿.md

# 4. 讀辨識稿，寫 01_片名/cuts.json（格式見 cuts.example.json）

# 5–6. 對切點、接旁白（會把時間軸寫進動畫的 timing.js）
.venv/bin/python scripts/snap.py 01_片名/cuts.json --write
scripts/assemble.py 01_片名/cuts.json
.venv/bin/python scripts/transcribe.py 01_片名/旁白.mp4      # 回讀，逐字對

# 7. 到動畫專案的預覽頁重新匯出 → 動畫_配合旁白.mp4

# 8. 疊人像（START、END 抄 旁白.json）
START=1.0 END=33.43 LABEL=樹懶老師 scripts/pip.sh 01_片名/無配樂.mp4 動畫_配合旁白.mp4 01_片名/旁白.mp4

# 9. 配樂
scripts/music.sh 01_片名/成品/01_片名_A.mp4 01_片名/無配樂.mp4 music/曲.mp3
```

`pip.sh` 和 `music.sh` 的可調參數寫在各自檔案開頭的註解裡。

## 驗證

[驗證記錄](../../docs/reports/2026-11-17-dreamone-reel-presenter.md)
