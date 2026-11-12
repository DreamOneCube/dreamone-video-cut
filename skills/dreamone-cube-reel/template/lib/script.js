/*
 * 稿子。say = 這一句的完整講法（數字寫成國字；靜音時用它的字數估這句停多久，有配音時就是念的內容）；
 * show = 畫面下方字幕（<em> 是黃色重點，<br> 換行，每行最多約 12 個字）。
 * gap = 這句結束後停多久再進下一句（秒，預設 0.22）；hold = 從這句開始算起，至少過幾秒才進下一句（留時間給畫面）。
 * 改完跑 `npm run build`，時間軸、字幕、方塊動作會全部跟著重排。
 */
(function (g) {
  g.ReelScript = {
    // 預設靜音：成品沒有任何聲音。聲音的做法還沒定案，現況與待辦見 Skill 的 references/sound.md。
    audio: false,
    // ↓ 以下三項只有 audio: true 才用得到
    //   engine "say"  = macOS 內建語音（台灣口音、聽得清楚；Apple 授權只限個人非商業用途，只能試聽，不能發布）
    //   engine "file" = 自備每句一檔的配音，放在 assets/voice-src/<句子 id>.mp3 或 .wav（真人錄音或任何配音工具皆可）
    engine: "say",
    voice: "Meijia",
    rate: 205, // say 的語速；數字越大越快
    lead: 0.3, // 開場先給 0.3 秒畫面再進第一句
    tail: 2.0, // 最後一句結束後停 2 秒
    lines: [
      { id: "hook1", say: "你知道魔術方塊，總共有幾種狀態嗎？", show: null },
      { id: "hook2", say: "答案是一個二十位數。", show: "答案是一個 <em>20 位數</em>", gap: 0.4 },

      { id: "center", say: "把它拆開來看：六個中心塊鎖在軸上，不會動。", show: "把它拆開來看<br><em>6 個中心塊</em>鎖在軸上不會動" },
      { id: "movers", say: "會換位置的，只有八個角塊，十二個邊塊。", show: "會換位置的，只有<br><em>8 個角塊</em>、<em>12 個邊塊</em>", gap: 0.4 },

      { id: "cperm", say: "八個角塊排進八個位置，有四萬多種排法。", show: "8 個角塊排進 8 個位置<br>有 <em>4 萬多種</em>排法" },
      { id: "cori", say: "每個角塊還有三種朝向。", show: "每個角塊還有 <em>3 種朝向</em>", hold: 2.2 },
      { id: "clast", say: "但前七個定了，最後一個就沒得選。", show: "但前 7 個定了<br><em>最後一個就沒得選</em>" },
      { id: "cpow", say: "所以是三的七次方。", show: "所以是 <em>3 的 7 次方</em>", gap: 0.4 },

      { id: "eperm", say: "十二個邊塊排進十二個位置，將近四億八千萬種。", show: "12 個邊塊排進 12 個位置<br>將近 <em>4 億 8 千萬種</em>" },
      { id: "elast", say: "每個邊塊兩種朝向，最後一個同樣沒得選。", show: "每個邊塊 <em>2 種朝向</em><br>最後一個同樣沒得選" },
      { id: "epow", say: "所以是二的十一次方。", show: "所以是 <em>2 的 11 次方</em>", gap: 0.4 },

      { id: "rule", say: "還有一條規則：不能只交換其中兩塊。", show: "還有一條規則：<br>不能<em>只交換其中兩塊</em>", hold: 3.2 },
      { id: "half", say: "所以再除以二。", show: "所以再<em>除以 2</em>", gap: 0.4 },

      { id: "all", say: "全部乘起來，就是這個二十位數。", show: "全部乘起來<br>就是這個 20 位數", hold: 3.0 },
      { id: "jing", say: "大約四千三百二十五京種！", show: "大約 <em>4,325 京</em>種！", hold: 3.4 },

      { id: "years", say: "就算每秒轉出一種，也要一兆三千七百億年。", show: "就算每秒轉出一種<br>也要 <em>1.37 兆年</em>" },
      { id: "universe", say: "差不多是宇宙年齡的一百倍。", show: "差不多是宇宙年齡的 <em>100 倍</em>", gap: 0.45 },

      { id: "god", say: "但不管哪一種，二十步之內都能還原。", show: "但不管哪一種<br><em>20 步之內</em>都能還原" },
    ],
  };
})(globalThis);
