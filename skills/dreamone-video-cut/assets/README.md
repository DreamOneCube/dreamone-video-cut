本包已附白字 Logo 原檔、粉圓體 1.1，以及官方字型授權；以下保留補件來源。

# 素材

`build.py` 需要兩個檔案，路徑寫在 `config.json`：

## 字型：jf open 粉圓體

開源字型（SIL OFL 1.1）。GitHub release 下載被 proxy 擋，用 npm 取得：

```bash
npm pack @expo-openfonts/huninn
tar xzf expo-openfonts-huninn-*.tgz
cp package/jf-openhuninn-1.1.ttf assets/
```

官方來源：https://github.com/justfont/open-huninn-font

## Logo：夢想一號魔術方塊學院 橫式白字

- 預設用 `魔術方塊學院新 Logo_橫板白字.png`（透明背景、白字，給深色底用）
- 向夢想一號設計素材資料夾取得；放到 `assets/` 後在 `config.json` 的 `logo` 指過去
- `build.py` 會自動裁掉透明邊，依版面縮放（寬 320px 或底部黑區高度，取小者）
- 換別的品牌或活動影片時，換一個透明背景、淺色字的 PNG 即可

內附 `logo_horizontal_white.png` 的來源為夢想一號工作區既有品牌素材原檔，未重新繪製。粉圓體檔案的 Git blob SHA 為 `3b697a71aa192e9bbf73fd7662f157b0451c316e`，與官方 `font/jf-openhuninn-1.1.ttf` 一致。
