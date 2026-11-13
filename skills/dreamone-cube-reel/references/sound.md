# 聲音：現況與接手方式

最後更新：2026-11-13。**這一頁是留給之後把聲音做法定下來的人更新的。**

## 現況

範本預設靜音（`lib/script.js` 的 `audio: false`），成品不含音軌。

原因：2026 年 11 月樣片的第二、三版加了 AI 旁白、配樂與音效，回饋是「聲音還不正確，先不要有聲音」。在聲音被人聽過並確認之前，一律出靜音版。

已經確認的方向只有這些：

- 想要有旁白（AI 配音）、配樂與音效。
- 音效被認為是加分，能讓人一直看下去。
- 目前的聲音還不能用。

## 試過的做法

| 做法 | 結果 | 能不能用 |
|---|---|---|
| 本機 Kokoro 中文語音 | 把配音丟回語音辨識，大半辨識不出來，判定發音不清楚 | 不能 |
| macOS 內建語音 Meijia（`say`） | 台灣口音，語音辨識回讀與稿子一致。Apple 的授權只限個人非商業用途 | 只能試聽，不能發布 |
| Runway 開發者 API 的文字轉語音 | 文件顯示有 `/v1/text_to_speech`，要在開發者平台另外建金鑰並加值（最少 US$10）。沒有實測 | 未知 |
| Runway 網頁版的 Audio 工具 | 有 ElevenLabs、Fish Audio、Gemini 等文字轉語音模型，一次最多 5,000 字，要登入才能選聲音。沒有實測中文發音與口音 | 未知 |

配樂與音效在第三版的量測值正常（成品 −15.6 LUFS、峰值 −3.0 dBFS），但沒有被人聽過確認，風格合不合適還不知道。

## AI 做聲音時的限制

- AI 聽不到聲音，只能量測。語氣自不自然、配樂合不合，一定要有人聽過才算數。
- 配音內容用語音辨識回讀來驗證：`npx --yes hyperframes@0.9.33 transcribe <音檔> --model small --language zh`，轉出的文字要和稿子一致（同音字差異可接受）。
- 金鑰不寫進檔案、不貼進對話。

## 範本裡已經寫好的音軌流程

把 `lib/script.js` 的 `audio` 改成 `true` 再 `npm run build`，就會做出三條音軌並掛進影片。這套流程在第三版實際用過。

| 音軌 | 來源 | 音量 |
|---|---|---|
| 人聲 | 一句一個檔，放到各自的時間點，整軌校到約 −16 LUFS | 1 |
| 音效 | `lib/reel-data.js` 的 `cue(時間, 名稱, 音量)`；每個素材先校到同一個峰值（−3 dB） | 0.7 |
| 配樂 | 一首曲子裁成影片長度，頭尾淡入淡出 | 0.14 |

有聲時句長改用配音的實際長度，所以換配音後整支影片的時間軸會自動重排。

配音來源由 `engine` 決定：

- `"say"`：macOS 內建語音，只能試聽。
- `"file"`：自備每句一檔的配音，放在 `assets/voice-src/<句子 id>.mp3`（或 `.wav`）。真人錄音或任何配音工具的輸出都走這條路。

目標值：成品 −16 到 −14 LUFS、峰值不超過 −1 dBFS，配樂墊在人聲下約 10 dB，所有音效低於人聲。

## 打開聲音需要的素材

範本只附方塊轉動聲，其餘要自己準備。缺檔時建置會列出缺哪些。

| 素材 | 放哪裡 | 來源與授權 |
|---|---|---|
| 方塊轉動聲（已附） | `assets/sfx-src/cube-turn.mp3` | Freesound「1000000001.aif」by ewrandom，CC0 |
| 其他音效（咻、啵、喀、錯誤音、打字、重低音、鈴聲、升音） | `~/.claude/skills/media-use/audio/assets/sfx/` | HyperFrames `media-use` Skill 內建（來自 Pixabay，Pixabay Content License，可商用但不可單獨轉發，所以不放進這個儲存庫） |
| 配樂 | `assets/bgm/wallpaper-kevin-macleod.mp3` | "Wallpaper"，Kevin MacLeod（incompetech.com），CC BY 4.0，發布時貼文要附署名 |

配樂署名文字：

```
Music: "Wallpaper" Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/
```

## 接手的人要決定的事

1. **旁白用誰的聲音。** 必須有商用授權、台灣口音、聽得清楚。可以是真人錄音，也可以是配音工具。
2. **配樂與音效要不要沿用。** 請人實際聽過第三版的做法再決定。
3. **預設要不要改成有聲。**

定案後請更新：這一頁、`SKILL.md` 第 10 節與第 0 節第 3 條、範本 `lib/script.js` 的 `audio` 預設值、範本的 `CREDITS.md`。
