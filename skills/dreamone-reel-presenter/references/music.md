# 配樂

## 規則

- 用可商用、不必標示作者的無版權音樂。目前都從 Pixabay Music 找（Pixabay Content License，跟 dreamone-cube-reel 的音效同一個授權）。
- **音樂檔不放進這個 repo。** 授權允許用在影片裡，但不允許把音樂檔本身單獨轉發。這裡只記曲名、作者、頁面，要用的人自己到頁面下載，放在本機的 `music/`。
- 每支片一次做三四種調性讓講師挑。AI 只能量響度，聽不出合不合。
- 新下載的曲子加進下面的表；被選中用在哪一支也記下來，之後找同類型的比較快。

授權條款：<https://pixabay.com/service/license-summary/>

## 已經下載過的

2026-11-16 下載。四首講師都覺得可以用，之後的片可以直接從這裡挑。

| 本機檔名 | 曲名 | 作者 | 調性 | 長度 | 用在 |
|---|---|---|---|---|---|
| `01_curious.mp3` | [Curious Background Music](https://pixabay.com/music/comedy-curious-background-music-634638/) | Sonican | 好奇、俏皮 | 1:05 | |
| `02_mysterious.mp3` | [Mysterious Fog Curious Discovery](https://pixabay.com/music/electronic-mysterious-fog-curious-discovery-575877/) | alex-morgan | 神祕、探索 | 1:30 | **02** |
| `03_classroom.mp3` | [Education Classroom Learning Flow](https://pixabay.com/music/happy-childrens-tunes-education-classroom-learning-flow-578471/) | alex-morgan | 教室、輕快 | 1:04 | **01** |
| `04_sunlight.mp3` | [Sunlight](https://pixabay.com/music/house-sunlight-633626/) | SoSimpleAudio | 明亮、律動 | 2:12 | |

## 混音的設定

`scripts/music.sh` 的預設值：

| 項目 | 值 |
|---|---|
| 人聲 | 校到 −15 LUFS（`VOICE=-15`） |
| 配樂 | 比人聲小 13 dB（`BED=13`；團隊規範寫「約 10 dB」，這裡保守一點） |
| 淡入／淡出 | 0.4 秒／1.5 秒 |
| 限幅 | −1.5 dBFS（AAC 壓縮後會過衝，成品實測峰值約 −1.3） |

01 四個版本實測都是 −16.1～−16.2 LUFS、峰值 −1.3～−1.4 dBFS——其實已經低於標準下限。02 起人聲預設改成 −15，四版實測 −15.5～−15.6 LUFS、峰值 −1.1～−1.3 dBFS，落在範圍中間。墊了配樂之後把成品丟回語音辨識，十句都抄得出來，只有一個詞（「京種變化」）被聽錯。
