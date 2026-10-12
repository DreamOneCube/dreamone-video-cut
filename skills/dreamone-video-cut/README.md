# dreamone-video-cut

夢想一號的影片剪輯 Skill：把多支手機直拍的教學／講解素材，剪成一支有章節進度條、Logo、標題、統一音量的 1080p 橫式影片，並輸出 SRT 與純文字字幕。

給 Claude／Codex 用：把整個資料夾放進 Claude 的 skills（或上傳到組織的 Skill 庫），之後說「幫我剪這個資料夾的影片」就會照 `SKILL.md` 的流程走。

```
SKILL.md                    流程、剪輯與字幕規則、版面規格（從這裡開始讀）
config.example.json         每支成品的設定：標題、章節、Logo、字型、版面開關、詞彙表
scripts/asr.py              語音辨識（雲端）
scripts/subtitles.py        辨識稿清理：簡轉繁、詞彙表、去語助詞、切行
scripts/build.py            規劃：版面 PNG、編碼單元表、SRT/TXT（雲端）
scripts/measure_gain.py     量每支素材音量、算增益（Mac）
scripts/run.py              分段編碼、串接、截圖檢查表（Mac）
terms/common.json           系列共用詞彙（大師不藏私、魔術方塊、夢想一號）
terms/skewb.json            斜轉專用詞彙（範例；新主題照格式新增一個檔）
references/environment.md   環境限制與實際踩過的坑
assets/README.md            字型與 Logo 的取得方式
```

第一個用這套流程剪出的成品：《大師不藏私》斜轉進階 第一部（50:43）、第二部（13:56），2026 年 9 月。

## 本機準備

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp config.example.json config.json
```

另需 PATH 上可執行的 ffmpeg／ffprobe。內附白字 Logo 原檔及粉圓體 1.1；字型的官方 SIL OFL 授權見 `assets/FONT-LICENSE.txt`。`terms/skewb.json` 是斜轉範例，換主題時自行選用對應詞彙表。

語音辨識模型另依 `scripts/asr.py` 下載，放在模型父資料夾內（包含 SenseVoice 子資料夾與 `silero_vad.onnx`），模型與原始影片不提交到 Git。
