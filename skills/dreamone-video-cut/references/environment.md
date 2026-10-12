# 環境限制與實際踩過的坑

這些是原 CoWork 剪《大師不藏私》斜轉系列時的環境紀錄，不是所有執行環境的限制。

Codex 本機可直接執行 build 與 run；逾時、下載權限、ffmpeg 版本與背景程序支援須依當次工具確認。大檔加 faststart 會重寫檔案，是否可用取決於時間與磁碟預算，沒有通用的 2 GB 禁令。

## 兩台機器

| | 雲端 sandbox（`Bash`） | 使用者的 Mac（`device_bash`） |
|---|---|---|
| 放什麼 | 辨識模型、腳本、規劃產物 | 原始影片、成品 |
| 做什麼 | 語音辨識、`build.py`、看截圖 | 抽音訊、量音量、`run.py` 編碼 |
| 檔案搬運 | `device_stage_files`（Mac→雲端）| `device_commit_files`（雲端→Mac）|

影片幾 GB，**永遠留在 Mac 上處理**；只把 wav（每分鐘約 2 MB）、截圖、json 搬來搬去。

## device_bash

- 每次呼叫最多 180 秒，逾時就中斷；`nohup`、`setsid`、`&` 的背景程序在呼叫結束時一起被砍。
  → 工作要切成小單元，每次呼叫做一點，用 `.done` 檔記錄進度，可重入。
- 1080p60 HEVC 解碼＋疊圖＋x264 superfast 大約 0.6–0.8 倍即時：55 秒的單元要 70–120 秒。
- 不能刪檔（rm 會 Operation not permitted）。換版本就開新資料夾；做完告訴使用者哪些資料夾可以刪。
- 連線偶爾斷（"Device disconnected"）：重試一次讀 status，已完成的單元不會重做。
- 偶爾整個工作區重開（`up 3 min`），之前跑的東西不受影響，只要從 status 繼續。
- `device_list_dir` 結果太大會存成檔案，用 python 讀那份 JSON。

## 取得素材

- Google Drive 連接器讀不到「知道連結者皆可檢視」的資料夾內容，要請對方**直接共享給使用者的帳號**才看得到檔案清單。
- 但不論雲端或 Mac 工作區，都連不到 Drive 下載網址（proxy 403）。實際檔案只能請使用者自己下載。
- Drive 打包下載會是好幾個 `drive-download-…-00N.zip`，同一章的素材會散在不同 zip 裡——用 `find` 找，不要假設路徑。

## 語音辨識

- HuggingFace 被擋，模型要從 GitHub releases 抓（見 `scripts/asr.py` 開頭）。
- 辨識結果是簡體，`subtitles.py` 用 OpenCC `s2twp` 轉。

## ffmpeg（Mac 工作區是 4.4）

- `drawbox` 的寬度不能用 `t` 運算式 → 進度條改用「預先畫好的紅條 PNG + overlay 的 x 運算式從左側滑入」，再用 `top.png` 蓋住段與段之間的縫。
- 素材解析度不一定一樣（前言是 2560×1440）：濾鏡鏈一律先 `scale`，不要假設 1920×1080。
- 跳剪剛好切在素材結尾會產生 0 秒單元，concat 會出錯 → `build.py` 已過濾 < 0.05 秒的單元。
- 50 分鐘成品約 2.2 GB（superfast、CRF 20）；`concat -c copy` 本身要 2 分鐘，**不要加 `-movflags +faststart`**，也不要和抽截圖放同一次呼叫。

## 字型

- jf open 粉圓體在 GitHub release 被擋；`npm pack @expo-openfonts/huninn` 拿得到 `jf-openhuninn-1.1.ttf`。
- PIL 畫中文要指定這個 ttf；Noto CJK 的 .ttc 要選 index 才會是繁中字形。

## 給使用者看東西

- 先給**一張示意圖＋5 秒試剪**再全跑。版面在這一步改最便宜——全片編碼要 1–2 小時。
- 版面每改一次，舊的 `.done` 不能沿用（疊圖變了），要開新的 plan 資料夾。
