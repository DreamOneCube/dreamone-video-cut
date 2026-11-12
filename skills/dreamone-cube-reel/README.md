# dreamone-cube-reel

夢想一號的方塊說明型 Reel Skill：畫面中央一顆由程式算出來、轉動與顏色保證正確的 3D 魔術方塊，上方是算式與重點，下方是逐句字幕，輸出 1080×1920、約 60 秒的直式短片。**預設靜音。**

給 Claude／Codex 用：把整個資料夾放進 skills，之後說「做一支方塊 Reel，題目是……」就會照 `SKILL.md` 的流程走。

```
SKILL.md                         規則、版面、文案、流程、驗收清單（從這裡開始讀）
references/sound.md              聲音的現況與接手方式（還沒定案，之後定案的人更新這一頁）
references/topics.md             題材清單
template/                        起手範本＝樣片〈4,325 京種狀態是怎麼算出來的？〉的完整專案
  SPEC.md                        這支影片的規格與分鏡（換題目時改寫）
  CREDITS.md                     素材來源與授權
  lib/cube-engine.js             方塊引擎：所有方塊狀態的唯一來源
  lib/script.js                  稿子與字幕；要不要聲音也在這裡
  lib/reel-data.js               方塊動作、畫面數字、事件時間點
  tools/build.mjs                建置：時間軸、字幕、畫面文字、index.html，最後自動跑驗證
  tools/*.template.html          版面範本（背景、上方資訊區、字幕）
  compositions/cube.html         3D 方塊場景（Three.js）
  tests/verify.mjs               方塊驗證：和 cubing.js 逐張貼紙比對
  assets/                        粉圓體 2.1、橫式 Logo、三角形 Logo、方塊轉動聲
```

## 本機準備

需要 Node 22 以上（在 Node 24 實測）與 ffmpeg。

```bash
cp -R template "YYMMDD_方塊Reel_題目"
```

```bash
npm install
```

```bash
npm run build
```

```bash
npm run check
```

```bash
npx --yes hyperframes@0.9.33 render -o "YYMMDD_方塊Reel_題目_v1.mp4"
```

`npm run build` 的最後會印出四行驗證結果與「全部通過」；沒有全部通過就不要算圖。

## 內附素材

- 粉圓體 2.1：SIL OFL 1.1，授權全文在 `template/assets/fonts/FONT-LICENSE.txt`。
- 橫式 Logo 與三角形 Logo：夢想一號品牌素材原檔，只做等比縮放與裁透明邊，未重新繪製。
- 方塊轉動聲：Freesound「1000000001.aif」by ewrandom，CC0（只有打開聲音時才用得到）。

配樂與其他音效因授權不適合轉發，沒有放進來；需要時的取得方式見 `references/sound.md`。

## 驗證記錄

[2026-11-13 交付驗證](../../docs/reports/2026-11-13-dreamone-cube-reel.md)
