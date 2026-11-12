/*
 * 方塊引擎：影片裡每一格方塊畫面的唯一資料來源。
 * 瀏覽器（影片）與 Node（tests/verify.mjs）共用同一份程式。
 *
 * 座標：x 向右、y 向上、z 朝觀眾。U=+y D=-y R=+x L=-x F=+z B=-z。
 * 配色：U 白、F 綠、R 紅、L 橘、B 藍、D 黃（白頂綠前的標準配色）。
 * 轉動：面的順時針（從該面外側看）＝繞該面朝外法線轉 -90 度。
 */
(function (g) {
  const FACES = {
    U: [0, 1, 0],
    D: [0, -1, 0],
    R: [1, 0, 0],
    L: [-1, 0, 0],
    F: [0, 0, 1],
    B: [0, 0, -1],
  };
  const COLORS = { U: "#ffffff", F: "#10b24a", R: "#e3262e", L: "#ff7a00", B: "#1668e8", D: "#ffd500" };
  const EDGES = "UF UR UB UL DF DR DB DL FR FL BR BL".split(" ");
  const CORNERS = "UFR URB UBL ULF DRF DFL DLB DBR".split(" ");

  const I3 = () => [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const mulMV = (m, v) => [dot(m[0], v), dot(m[1], v), dot(m[2], v)];
  const mulMM = (a, b) =>
    a.map((row) => [0, 1, 2].map((j) => row[0] * b[0][j] + row[1] * b[1][j] + row[2] * b[2][j]));
  const unit = (v) => {
    const n = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / n, v[1] / n, v[2] / n];
  };
  const faceOf = (n) => Object.keys(FACES).find((f) => dot(FACES[f], n) === 1);

  // Rodrigues 旋轉矩陣。axis 不必是單位向量。
  function rotMat(axis, deg) {
    const [x, y, z] = unit(axis);
    const a = (deg * Math.PI) / 180;
    const c = Math.cos(a), s = Math.sin(a), t = 1 - c;
    return [
      [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
      [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
      [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ];
  }
  const roundM = (m) => m.map((r) => r.map((v) => Math.round(v) + 0));
  const roundV = (v) => v.map((x) => Math.round(x) + 0);

  // 26 個小塊。id 就是它還原時的位置（home）。
  function solved() {
    const cubies = [];
    for (let x = -1; x <= 1; x++)
      for (let y = -1; y <= 1; y++)
        for (let z = -1; z <= 1; z++) {
          if (!x && !y && !z) continue;
          cubies.push({ id: `${x},${y},${z}`, home: [x, y, z], pos: [x, y, z], rot: I3() });
        }
    return cubies;
  }
  const clone = (s) => s.map((c) => ({ id: c.id, home: c.home, pos: [...c.pos], rot: c.rot.map((r) => [...r]) }));
  const kind = (c) => ["", "center", "edge", "corner"][Math.abs(c.home[0]) + Math.abs(c.home[1]) + Math.abs(c.home[2])];

  // 把一組小塊繞通過原點的軸轉 deg 度（只接受會落回格點的角度）。
  function rotate(state, ids, axis, deg) {
    const m = roundM(rotMat(axis, deg));
    for (const c of state) {
      if (!ids.includes(c.id)) continue;
      c.pos = roundV(mulMV(m, c.pos));
      c.rot = roundM(mulMM(m, c.rot));
    }
    return state;
  }
  const layerIds = (state, face) => state.filter((c) => dot(c.pos, FACES[face]) === 1).map((c) => c.id);
  const idAt = (state, pos) => state.find((c) => c.pos.join() === pos.join()).id;
  const slotPos = (name) => [...name].reduce((p, f) => p.map((v, i) => v + FACES[f][i]), [0, 0, 0]);

  // "R U2 F'" → [{face:"R",turns:1},{face:"U",turns:2},{face:"F",turns:-1}]
  function parseAlg(alg) {
    return alg.trim().split(/\s+/).filter(Boolean).map((tok) => {
      const m = /^([UDLRFB])(2|'|)$/.exec(tok);
      if (!m) throw new Error("不支援的轉動代號：" + tok);
      return { face: m[1], turns: m[2] === "2" ? 2 : m[2] === "'" ? -1 : 1 };
    });
  }
  const invertAlg = (alg) =>
    parseAlg(alg).reverse().map((m) => m.face + (m.turns === 2 ? "2" : m.turns === 1 ? "'" : "")).join(" ");
  const moveDeg = (m) => -90 * m.turns;
  function applyAlg(state, alg) {
    for (const m of parseAlg(alg)) rotate(state, layerIds(state, m.face), FACES[m.face], moveDeg(m));
    return state;
  }

  // 54 張貼紙：「位置|朝向」→ 顏色所屬的面
  function facelets(state) {
    const map = {};
    for (const c of state)
      for (let i = 0; i < 3; i++) {
        if (!c.home[i]) continue;
        const n0 = [0, 0, 0];
        n0[i] = c.home[i];
        map[c.pos.join() + "|" + mulMV(c.rot, n0).join()] = faceOf(n0);
      }
    return map;
  }

  // Reid 表示法（與 cubing.js 對照用）：每個位置依序讀出各面的顏色
  function toReid(state) {
    const f = facelets(state);
    const read = (name) => [...name].map((ch) => f[slotPos(name).join() + "|" + FACES[ch].join()]).join("");
    return { edges: EDGES.map(read), corners: CORNERS.map(read), centers: Object.keys(FACES).map(read).join("") };
  }

  // 合法性：角塊朝向總和 ≡ 0 (mod 3)、邊塊朝向總和 ≡ 0 (mod 2)、角與邊的排列奇偶相同
  function analyse(state) {
    const r = toReid(state);
    const find = (names, s) => {
      for (let j = 0; j < names.length; j++)
        for (let o = 0; o < names[j].length; o++)
          if (names[j].slice(o) + names[j].slice(0, o) === s) return [j, o];
      throw new Error("不是真實存在的小塊：" + s);
    };
    const parity = (p) => {
      let n = 0;
      for (let i = 0; i < p.length; i++) for (let j = i + 1; j < p.length; j++) if (p[i] > p[j]) n++;
      return n % 2;
    };
    const c = r.corners.map((s) => find(CORNERS, s)), e = r.edges.map((s) => find(EDGES, s));
    const twist = c.reduce((a, x) => a + x[1], 0) % 3;
    const flip = e.reduce((a, x) => a + x[1], 0) % 2;
    const swap = parity(c.map((x) => x[0])) !== parity(e.map((x) => x[0]));
    const centersOk = r.centers === "UDRLFB";
    return { twist, flip, swap, centersOk, legal: centersOk && !twist && !flip && !swap };
  }
  const isSolved = (state) => state.every((c) => c.pos.join() === c.home.join() && c.rot.join() === I3().join());

  /*
   * 時間軸：把「在幾秒做什麼」編成每個小塊自己的動作清單，
   * renderAt(t) 只靠 t 就能算出每一塊的位置與角度（可任意跳格）。
   *
   * op: { t, dur, kind, ... }
   *   move  : { face, turns }            真實轉動
   *   twist : { slot:"UFR", dir:+1|-1 }  單獨扭一個角（順時針 +1）。單獨存在時是不合法狀態
   *   flip  : { slot:"UF" }              單獨翻一個邊。單獨存在時是不合法狀態
   *   swap  : { a:"UF", b:"UR", axis:"U" } 只交換兩塊。單獨存在時是不合法狀態
   */
  function compile(start, ops) {
    const state = clone(start);
    const tracks = {};
    for (const c of state) tracks[c.id] = [];
    const checkpoints = [];
    const sorted = [...ops].sort((a, b) => a.t - b.t);
    for (const op of sorted) {
      let parts;
      if (op.kind === "move") parts = [[layerIds(state, op.face), FACES[op.face], moveDeg(op)]];
      else if (op.kind === "twist") parts = [[[idAt(state, slotPos(op.slot))], slotPos(op.slot), -120 * op.dir]];
      else if (op.kind === "flip") parts = [[[idAt(state, slotPos(op.slot))], slotPos(op.slot), 180]];
      else if (op.kind === "swap") {
        const pa = slotPos(op.a), pb = slotPos(op.b), ax = FACES[op.axis];
        const deg = roundV(mulMV(rotMat(ax, 90), pa)).join() === pb.join() ? 90 : -90;
        parts = [[[idAt(state, pa)], ax, deg], [[idAt(state, pb)], ax, -deg]];
      } else if (op.kind === "mark") {
        checkpoints.push({ name: op.name, t: op.t, state: clone(state) });
        continue;
      } else throw new Error("未知動作：" + op.kind);
      for (const [ids, axis, deg] of parts) {
        for (const id of ids) {
          const c = state.find((x) => x.id === id);
          const tr = tracks[id], last = tr[tr.length - 1];
          if (last && last.t1 > op.t + 1e-9) throw new Error(`小塊 ${id} 在 ${op.t}s 動作重疊`);
          tr.push({ t0: op.t, t1: op.t + op.dur, axis: unit(axis), deg, pos: [...c.pos], rot: c.rot.map((r) => [...r]) });
        }
      }
      // 同一個動作的各部分要一起生效（交換兩塊時不能先動一塊再找另一塊）
      for (const [ids, axis, deg] of parts) rotate(state, ids, axis, deg);
    }
    return { start: clone(start), end: state, tracks, checkpoints };
  }

  const easeInOut = (f) => (f < 0.5 ? 4 * f * f * f : 1 - Math.pow(-2 * f + 2, 3) / 2);

  // 回傳某小塊在 t 秒的姿態：{ pos, rot, axis, angle }，畫面＝先擺成 pos/rot，再繞 axis 轉 angle 度
  function poseAt(compiled, id, t) {
    const tr = compiled.tracks[id];
    let k = -1;
    for (let i = 0; i < tr.length; i++) if (tr[i].t0 <= t) k = i;
    if (k < 0) {
      const c = compiled.start.find((x) => x.id === id);
      return { pos: c.pos, rot: c.rot, axis: [0, 1, 0], angle: 0 };
    }
    const o = tr[k];
    if (t < o.t1) return { pos: o.pos, rot: o.rot, axis: o.axis, angle: o.deg * easeInOut((t - o.t0) / (o.t1 - o.t0)) };
    const next = tr[k + 1];
    if (next) return { pos: next.pos, rot: next.rot, axis: [0, 1, 0], angle: 0 };
    const c = compiled.end.find((x) => x.id === id);
    return { pos: c.pos, rot: c.rot, axis: [0, 1, 0], angle: 0 };
  }

  g.CubeEngine = {
    FACES, COLORS, EDGES, CORNERS,
    solved, clone, kind, rotate, layerIds, slotPos, parseAlg, invertAlg, applyAlg,
    facelets, toReid, analyse, isSolved, compile, poseAt, rotMat, easeInOut,
  };
})(globalThis);
