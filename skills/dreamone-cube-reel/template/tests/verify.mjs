// 發布前必跑：npm run verify
// 1. 方塊引擎的每一種轉動，都和 cubing.js（WCA 生態系的標準函式庫）逐張貼紙比對
// 2. 影片腳本每個檢查點的狀態，合法／不合法都符合畫面上的說法
// 3. 畫面上的每個數字都重新算一次
import assert from "node:assert/strict";
import { Alg } from "cubing/alg";
import { cube3x3x3 } from "cubing/puzzles";
import "../lib/cube-engine.js";
import "../lib/timing.js";
import "../lib/reel-data.js";

const E = globalThis.CubeEngine, R = globalThis.ReelData;
const kpuzzle = await cube3x3x3.kpuzzle();
const rotl = (s, i) => s.slice(i) + s.slice(0, i);
// cubing.js 的狀態 → Reid 表示法（每個位置依序讀出各面顏色）
function refReid(alg) {
  const d = kpuzzle.defaultPattern().applyAlg(new Alg(alg)).patternData;
  return {
    edges: E.EDGES.map((_, i) => rotl(E.EDGES[d.EDGES.pieces[i]], d.EDGES.orientation[i])),
    corners: E.CORNERS.map((_, i) => rotl(E.CORNERS[d.CORNERS.pieces[i]], d.CORNERS.orientation[i])),
  };
}
const mine = (alg) => {
  const r = E.toReid(E.applyAlg(E.solved(), alg));
  return { edges: r.edges, corners: r.corners };
};
const same = (alg) => assert.deepEqual(mine(alg), refReid(alg), "與 cubing.js 不一致：" + alg);

// ── 1. 轉動 ──
const moves = [..."UDLRFB"].flatMap((f) => [f, f + "'", f + "2"]);
moves.forEach(same);
let seed = 20261112;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0), seed / 2 ** 32);
for (let n = 0; n < 500; n++) same(Array.from({ length: 30 }, () => moves[Math.floor(rnd() * 18)]).join(" "));
// 對照組：方向轉反一定要被抓到，確認這個比對不是空轉
assert.notDeepEqual(mine("R"), refReid("R'"));
assert.notDeepEqual(mine("U"), refReid("D"));
console.log("✓ 18 種基本轉動＋500 組 30 步隨機公式，全部與 cubing.js 逐張貼紙一致");

// 驗收用的黃金測試：還原狀態（白頂綠前）做一次 R，頂面右排應該全是綠色（F 面的顏色）
const f = E.facelets(E.applyAlg(E.solved(), "R"));
[-1, 0, 1].forEach((z) => assert.equal(f[`1,1,${z}|0,1,0`], "F"));
assert.equal(E.COLORS.U + E.COLORS.F + E.COLORS.R, "#ffffff#10b24a#e3262e");
console.log("✓ 黃金測試：做一次 R，頂面右排變綠色；配色為白頂、綠前、紅右");

// R U R' U' 做 6 次回到原點
assert.ok(E.isSolved(E.applyAlg(E.solved(), Array(6).fill("R U R' U'").join(" "))));

// ── 2. 影片腳本 ──
const cp = Object.fromEntries(R.compiled.checkpoints.map((c) => [c.name, c.state]));
const A = (name) => E.analyse(cp[name]);
assert.deepEqual({ edges: E.toReid(cp["開場打亂"]).edges, corners: E.toReid(cp["開場打亂"]).corners }, refReid(R.SCRAMBLE));
assert.ok(A("開場打亂").legal && !E.isSolved(cp["開場打亂"]));
assert.ok(E.isSolved(cp["開場還原"]), "開場 4 秒必須真的轉回還原");
assert.ok(E.isSolved(cp["主角角塊轉三下"]), "同一個角轉三下要回到原樣");
assert.ok(!A("扭了 7 個角").legal && A("扭了 7 個角").twist !== 0, "只扭 7 個角應該是不合法狀態");
assert.ok(A("第 8 個角補上").legal, "第 8 個角補上後必須合法");
assert.ok(!A("翻了 11 個邊").legal && A("翻了 11 個邊").flip !== 0, "只翻 11 個邊應該是不合法狀態");
assert.ok(A("第 12 個邊補上").legal, "第 12 個邊補上後必須合法");
assert.ok(!A("只交換兩塊").legal && A("只交換兩塊").swap, "只交換兩塊應該是不合法狀態");
assert.ok(A("換回來").legal);
assert.deepEqual(E.toReid(cp["換回來"]), E.toReid(cp["第 12 個邊補上"]));
// 結尾每秒一轉：從「第 12 個邊補上」的合法狀態開始做真實轉動，結果必須仍合法
assert.ok(A("片尾").legal);
assert.deepEqual(E.toReid(cp["片尾"]), E.toReid(E.applyAlg(E.clone(cp["換回來"]), R.tickAlg)));
// 任意時間點取樣：每個小塊都還在 26 個格點之一，沒有兩塊疊在一起（動作結束的瞬間）
for (const c of R.compiled.checkpoints) assert.equal(new Set(c.state.map((x) => x.pos.join())).size, 26);
console.log("✓ 影片腳本 " + R.compiled.checkpoints.length + " 個檢查點：合法／不合法都與畫面說法一致");

// ── 3. 數字 ──
const N = R.numbers;
assert.equal(N.cornerPerm, "40,320");
assert.equal(N.cornerOri, "2,187");
assert.equal(N.edgePerm, "479,001,600");
assert.equal(N.edgeOri, "2,048");
assert.equal(N.totalRaw, (40320n * 2187n * 479001600n * 2048n / 2n).toString());
assert.equal(N.total, "43,252,003,274,489,856,000");
assert.equal(N.digits, 20);
assert.equal(N.jing, "4,325");
assert.equal(N.yearsZhao, "1.37");
assert.ok(Math.abs(N.universeRatio - 100) < 2 && N.universeTimes === 100);
console.log(`✓ 數字：${N.total}（${N.digits} 位數，約 ${N.jing} 京）；每秒一種要 ${N.yearsZhao} 兆年，約宇宙年齡的 ${N.universeRatio.toFixed(1)} 倍`);
console.log("全部通過");
