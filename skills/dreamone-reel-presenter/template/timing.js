// 讓動畫的快慢配合旁白
//
// 放進動畫專案的 src/，再照 references/animation-hook.md 在主程式接上三行，
// 之後這支動畫就能在「錄完旁白以後」改成配合人聲的速度，不必回頭調每一個寫死的秒數。
//
// ANCHORS_SRC：動畫原本的錨點＝開頭、每一句字幕出現的時間、結尾。
//              做動畫的人填，填完就不要再改。N 句字幕就有 N+2 個數字。
// VOICE_ANCHORS：同樣這些時間點在成品裡的位置。由 scripts/assemble.py 從旁白算出來寫入，
//                不要手改。null = 照動畫原本的速度跑。
//
// 範例是「上帝的數字 20」：十句字幕，原本 48 秒。

export const ANCHORS_SRC = [0, 1.5, 4, 8, 13, 17, 24, 30, 34, 40, 44, 48];

export const VOICE_ANCHORS = null;

export const ANCHORS_OUT = VOICE_ANCHORS || ANCHORS_SRC;

// 成品長度。主程式的 DURATION 要改成用這個值
export const DURATION_OUT = ANCHORS_OUT[ANCHORS_OUT.length - 1];

// 把成品的第 t 秒，換算成原本動畫的第幾秒（每一句各自等比例伸縮）
export function toSource(t) {
  const out = ANCHORS_OUT;
  const src = ANCHORS_SRC;
  if (t <= out[0]) return src[0];
  for (let i = 0; i < out.length - 1; i++) {
    if (t < out[i + 1]) {
      const k = (t - out[i]) / (out[i + 1] - out[i]);
      return src[i] + k * (src[i + 1] - src[i]);
    }
  }
  return src[src.length - 1];
}
