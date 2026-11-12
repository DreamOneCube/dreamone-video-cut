/*
 * 這支影片的唯一資料來源：方塊在幾秒做什麼、畫面上每個數字是多少、哪裡要有音效（音效只有 audio: true 才用得到）。
 * 所有時間都掛在稿子的句子上（lib/timing.js 由 `npm run build` 依每句的長度產生）。
 * 改完跑 `npm run build`（會自動跑驗證）。
 */
(function (g) {
  const E = g.CubeEngine, TM = g.ReelTiming;
  const DURATION = TM.duration;
  // 句子的時間：L("cperm").at(0.5) = 那一句進行到一半的時間點
  const L = (id) => {
    const l = TM.lines[id];
    if (!l) throw new Error("稿子沒有這一句：" + id);
    return { t0: l.t0, t1: l.t1, d: l.t1 - l.t0, at: (f) => l.t0 + f * (l.t1 - l.t0) };
  };

  // ── 數字（全部由這裡算出，畫面不另外手打）─────────────────────────
  const fact = (n) => (n <= 1n ? 1n : n * fact(n - 1n));
  const comma = (n) => n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const cornerPerm = fact(8n); // 8 個角塊排 8 個位置
  const cornerOri = 3n ** 7n; // 每塊 3 種朝向，最後一塊被決定
  const edgePerm = fact(12n); // 12 個邊塊排 12 個位置
  const edgeOri = 2n ** 11n; // 每塊 2 種朝向，最後一塊被決定
  const total = (cornerPerm * cornerOri * edgePerm * edgeOri) / 2n; // 奇偶限制再除以 2
  const SECONDS_PER_YEAR = 31557600; // 365.25 天
  const UNIVERSE_AGE_YEARS = 1.38e10; // 約 138 億年
  const years = Number(total) / SECONDS_PER_YEAR;
  const numbers = {
    cornerPerm: comma(cornerPerm),
    cornerOri: comma(cornerOri),
    edgePerm: comma(edgePerm),
    edgeOri: comma(edgeOri),
    total: comma(total),
    totalRaw: total.toString(),
    digits: total.toString().length,
    jing: comma(total / 10n ** 16n), // 京 = 10 的 16 次方
    yearsZhao: (years / 1e12).toFixed(2), // 兆年
    universeTimes: Math.round(years / UNIVERSE_AGE_YEARS / 10) * 10,
    universeRatio: years / UNIVERSE_AGE_YEARS,
  };

  // ── 方塊動作 ────────────────────────────────────────────────────
  const SCRAMBLE = "R U2 F' L D' B2 R' F U' L2 D R2 B' U F2 L'"; // 開場的打亂狀態
  const HOOK_SOLVE = E.invertAlg(SCRAMBLE); // 開場把它轉回還原
  const TICK_CYCLE = "R U F' L D B' R' U' F L' D' B".split(" "); // 結尾每秒轉一下，循環使用

  const CAM_DIR = [0.553, 0.438, 0.708]; // 鏡頭方向，用來把小塊由遠排到近
  const depth = (name) => E.slotPos(name).reduce((a, v, i) => a + v * CAM_DIR[i], 0);
  const farToNear = (names) => [...names].sort((a, b) => depth(a) - depth(b));
  const corners = farToNear(E.CORNERS); // 最後一個是離鏡頭最近的 UFR
  const edges = farToNear(E.EDGES);
  const HERO_CORNER = corners[corners.length - 1];
  const HERO_EDGE = "UF";
  const otherEdges = edges.filter((e) => e !== HERO_EDGE);

  const ops = [], sfx = [], ev = {};
  const mark = (t, name) => ops.push({ kind: "mark", t, name });
  const cue = (t, name, vol) => sfx.push({ t: Math.max(0, t), name, vol });

  // 開場：打亂的方塊在兩句旁白之間轉回還原
  mark(0, "開場打亂");
  {
    const moves = E.parseAlg(HOOK_SOLVE), a = 0.35, b = L("hook2").t1 - 0.3, step = (b - a) / moves.length;
    moves.forEach((m, i) => {
      ops.push({ kind: "move", t: a + i * step, dur: step * 0.86, ...m });
      cue(a + i * step + step * 0.4, "turn", 0.36);
    });
    ev.hookEnd = L("hook2").t1 + 0.25;
    mark(b + 0.05, "開場還原");
  }

  // 拆開
  const center = L("center"), movers = L("movers");
  cue(center.t0, "whoosh-short", 0.4);

  // 角塊：依序點名 → 主角轉三下看 3 種朝向 →「前 7 塊自由、第 8 塊被決定」
  const cperm = L("cperm"), cori = L("cori"), clast = L("clast"), cpow = L("cpow");
  const pops = [];
  corners.forEach((slot, i) => {
    const t = cperm.at(0.06) + i * ((cperm.d * 0.5) / 8);
    pops.push({ slot, t });
    cue(t, "click-soft", 0.26);
  });
  ev.cornerPermEq = cperm.at(0.74);
  ev.chain1 = cperm.t1 - 0.05;
  cue(ev.cornerPermEq, "pop", 0.4);
  const heroTwists = [0, 1, 2].map((i) => cori.t0 + 0.25 + i * 0.62);
  heroTwists.forEach((t) => {
    ops.push({ kind: "twist", t, dur: 0.5, slot: HERO_CORNER, dir: 1 });
    cue(t + 0.2, "turn", 0.34);
  });
  mark(heroTwists[2] + 0.55, "主角角塊轉三下");
  const cStep = Math.min(0.2, (clast.d * 0.42) / 7);
  const cTwists = corners.slice(0, 7).map((slot, i) => ({ slot, t: clast.at(0.02) + i * cStep }));
  cTwists.forEach(({ slot, t }) => {
    ops.push({ kind: "twist", t, dur: 0.45, slot, dir: 1 });
    cue(t + 0.18, "turn", 0.24);
  });
  const c8 = Math.max(clast.at(0.56), cTwists[6].t + 0.5);
  mark(c8 - 0.02, "扭了 7 個角");
  ops.push({ kind: "twist", t: c8, dur: 0.55, slot: HERO_CORNER, dir: -1 });
  cue(c8 + 0.22, "turn", 0.4);
  cue(c8 + 0.5, "pop", 0.36);
  mark(c8 + 0.6, "第 8 個角補上");
  ev.cornerOriTerms = cTwists.map((x) => x.t).concat(c8);
  ev.cornerOriEq = cpow.at(0.45);
  ev.chain2 = cpow.t1 - 0.05;
  cue(ev.cornerOriEq, "pop", 0.4);

  // 邊塊：依序點名 →「前 11 塊自由、第 12 塊被決定」
  const eperm = L("eperm"), elast = L("elast"), epow = L("epow");
  edges.forEach((slot, i) => {
    const t = eperm.at(0.06) + i * ((eperm.d * 0.46) / 12);
    pops.push({ slot, t });
    cue(t, "click-soft", 0.26);
  });
  ev.edgePermEq = eperm.at(0.74);
  ev.chain3 = eperm.t1 - 0.05;
  cue(ev.edgePermEq, "pop", 0.4);
  const eStep = Math.min(0.17, (elast.d * 0.46) / 11);
  const eFlips = otherEdges.map((slot, i) => ({ slot, t: elast.at(0.04) + i * eStep }));
  eFlips.forEach(({ slot, t }) => {
    ops.push({ kind: "flip", t, dur: 0.4, slot });
    cue(t + 0.16, "turn", 0.22);
  });
  const e12 = Math.max(elast.at(0.68), eFlips[10].t + 0.5);
  mark(e12 - 0.02, "翻了 11 個邊");
  ops.push({ kind: "flip", t: e12, dur: 0.5, slot: HERO_EDGE });
  cue(e12 + 0.2, "turn", 0.4);
  cue(e12 + 0.45, "pop", 0.36);
  mark(e12 + 0.55, "第 12 個邊補上");
  ev.edgeOriTerms = eFlips.map((x) => x.t).concat(e12);
  ev.edgeOriEq = epow.at(0.45);
  ev.chain4 = epow.t1 - 0.05;
  cue(ev.edgeOriEq, "pop", 0.4);

  // 奇偶：只交換兩塊（不合法），打 ✕，再換回來
  const rule = L("rule"), half = L("half");
  const swapT = rule.at(0.48), swapBack = half.t0;
  ops.push({ kind: "swap", t: swapT, dur: 0.8, a: "UF", b: "UR", axis: "U" });
  cue(swapT, "whoosh-short", 0.26);
  ev.xIn = swapT + 0.82;
  ev.xOut = swapBack - 0.12;
  cue(ev.xIn, "error", 0.42);
  mark(ev.xIn + 0.05, "只交換兩塊");
  ops.push({ kind: "swap", t: swapBack, dur: 0.7, a: "UF", b: "UR", axis: "U" });
  cue(swapBack, "whoosh-short", 0.22);
  mark(swapBack + 0.75, "換回來");
  ev.chain5 = half.at(0.6);
  cue(ev.chain5, "pop", 0.4);

  // 答案：收合、20 位數逐位鎖定、主角數字落定、轉一圈展示
  const all = L("all"), jing = L("jing");
  cue(all.t0, "whoosh", 0.36);
  ev.digitsIn = all.t0 + 0.7;
  ev.rollStart = all.t0 + 0.95;
  ev.rollDur = 1.3;
  cue(ev.rollStart, "typing", 0.3);
  ev.hero = jing.t0 + 0.12;
  cue(ev.hero - 3.3, "riser-tail", 0.1);
  cue(ev.hero, "impact-bass-1", 0.14);
  const yawStart = jing.t0 + 0.7, yawEnd = yawStart + 2.6;

  // 結尾：每秒轉出一種新狀態
  const yearsL = L("years"), universe = L("universe"), god = L("god");
  ev.payoffOut = yearsL.t0 - 0.15;
  let ticks = 0;
  for (let t = yearsL.t0 + 0.1; t + 0.5 < DURATION - 0.2; t += 1) {
    ops.push({ kind: "move", t, dur: 0.5, ...E.parseAlg(TICK_CYCLE[ticks % TICK_CYCLE.length])[0] });
    cue(t + 0.24, "turn", 0.42);
    ticks++;
  }
  mark(DURATION - 0.05, "片尾");
  ev.years = yearsL.at(0.62);
  ev.universe = universe.at(0.55);
  ev.sizeOut = god.t0 - 0.12;
  ev.god = god.at(0.55);
  cue(ev.years, "pop", 0.4);
  cue(ev.universe, "pop", 0.4);
  cue(ev.god, "chime", 0.34);

  const start = E.applyAlg(E.solved(), SCRAMBLE);
  const compiled = E.compile(start, ops);
  const tickAlg = Array.from({ length: ticks }, (_, i) => TICK_CYCLE[i % TICK_CYCLE.length]).join(" ");

  // ── 純視覺的軌道（不影響方塊狀態）─────────────────────────────────
  // 每筆 [秒, 值, 緩動]；兩筆之間內插，之外維持。
  const explode = [[center.t0, 0], [center.t0 + 0.9, 1, "out"], [all.t0, 1], [all.t0 + 0.8, 0, "inOut"]];
  const fade = (t, a, b) => [[t, a], [t + 0.4, b]];
  const cIn = center.at(0.32), mIn = movers.t0;
  // 變暗：0 = 原色，1 = 壓暗
  const edgeBase = [...fade(cIn, 0, 1), ...fade(mIn, 1, 0), ...fade(cperm.t0, 0, 1), ...fade(eperm.t0, 1, 0)];
  const dim = {
    center: [...fade(mIn, 0, 1), ...fade(all.t0, 1, 0)],
    edge: [...edgeBase, ...fade(rule.t0, 0, 1), ...fade(all.t0, 1, 0)],
    corner: [...fade(cIn, 0, 1), ...fade(mIn, 1, 0), ...fade(eperm.t0, 0, 1), ...fade(all.t0, 1, 0)],
  };
  // 被交換的那兩塊在奇偶段落保持原色
  const dimOverride = { [E.slotPos("UF").join()]: edgeBase, [E.slotPos("UR").join()]: edgeBase };
  // 半透明：講中心塊時，其他小塊退成半透明，露出中心軸
  const ghostKeys = [...fade(cIn, 0, 1), ...fade(mIn, 1, 0)];
  const ghost = { center: [[0, 0]], edge: ghostKeys, corner: ghostKeys };
  // 整顆方塊的展示轉盤（度）：答案出現後轉一整圈
  const yaw = [[yawStart, 0], [yawEnd, 360, "inOut"]];
  // 往外抬（避免穿過別塊、或讓主角更醒目）
  const lifts = [
    { slot: HERO_CORNER, keys: [[heroTwists[0] - 0.3, 0], [heroTwists[0], 0.45, "out"], [heroTwists[2] + 0.5, 0.45], [heroTwists[2] + 0.9, 0, "inOut"]] },
    {
      slot: "UF",
      keys: [
        [swapT - 0.15, 0], [swapT + 0.15, 0.55, "out"], [swapT + 0.5, 0.55], [swapT + 0.8, 0, "inOut"],
        [swapBack - 0.1, 0], [swapBack + 0.15, 0.55, "out"], [swapBack + 0.42, 0.55], [swapBack + 0.7, 0, "inOut"],
      ],
    },
  ];
  // 畫面上方資訊的進出時間
  Object.assign(ev, {
    kCenter: center.at(0.4), kCorner: movers.at(0.45), kEdge: movers.at(0.75), kOut: cperm.t0 - 0.1,
    cornerPermIn: cperm.at(0.04), cornerPermOut: cori.t0 + 0.1,
    cornerOriIn: clast.t0, cornerOriOut: eperm.t0 - 0.05,
    edgePermIn: eperm.at(0.04), edgePermOut: elast.t0 - 0.05,
    edgeOriIn: elast.t0, edgeOriOut: rule.t0 - 0.05,
    chainOut: jing.t0,
  });

  g.ReelData = {
    DURATION, numbers, SCRAMBLE, HOOK_SOLVE, tickAlg, CAM_DIR,
    corners, edges, HERO_CORNER, HERO_EDGE, ops, sfx, ev, start, compiled,
    explode, dim, dimOverride, ghost, yaw, pops, lifts,
  };
})(globalThis);
