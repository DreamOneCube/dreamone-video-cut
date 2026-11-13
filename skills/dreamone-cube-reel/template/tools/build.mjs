// npm run build
// 稿子（lib/script.js）→ 時間軸（lib/timing.js）→ 字幕與畫面文字（compositions/）→ index.html → 方塊驗證（tests/verify.mjs）
// 預設靜音：句長用字數估，不產生任何聲音。lib/script.js 設 audio: true 才會配音、做音效與配樂三條音軌。
import { execFileSync, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
process.chdir(ROOT);
// ↓ 只有 audio: true 才用得到
const SFX_LIB = path.join(process.env.HOME, ".claude/skills/media-use/audio/assets/sfx"); // HyperFrames media-use 內建音效（Pixabay）
const CUBE_SFX = "assets/sfx-src/cube-turn.mp3"; // Freesound「1000000001.aif」by ewrandom，CC0
const BGM_SRC = "assets/bgm/wallpaper-kevin-macleod.mp3"; // "Wallpaper" Kevin MacLeod，CC BY 4.0；不隨範本附上
const BGM_OFFSET = Number(process.env.BGM_OFFSET ?? 0); // 從配樂的第幾秒開始用
const VOL = { voice: 1, sfx: 0.7, bgm: 0.14 };

const sh = (cmd, args, opt = {}) => execFileSync(cmd, args, { stdio: ["ignore", "pipe", "pipe"], ...opt }).toString();
const ff = (args) => sh("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args]);
const dur = (f) => parseFloat(sh("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]));
const r3 = (x) => Math.round(x * 1000) / 1000;

// ── 1. 每一句有多長 ──────────────────────────────────────────────
await import("../lib/script.js");
const S = globalThis.ReelScript;
// 靜音版沒有配音可量，句長用字數估：每個字 0.2 秒，句中每個停頓（，：、；）0.28 秒。
// 這兩個數字是用 2026-11-12 試聽旁白的實際長度回推的（18 句總長誤差不到 0.1 秒）。
const count = (s, re) => [...s].filter((c) => re.test(c)).length;
const est = (s) => r3(count(s, /[\p{Script=Han}A-Za-z0-9]/u) * 0.2 + count(s, /[，：、；]/) * 0.28);
if (S.audio) {
  const need = [CUBE_SFX, BGM_SRC, path.join(SFX_LIB, "pop.mp3")].filter((f) => !fs.existsSync(f));
  if (need.length) throw new Error(`audio: true 需要這些聲音素材（取得方式見 Skill 的 references/sound.md）：\n${need.join("\n")}`);
  for (const d of ["assets/voice", "assets/audio", "assets/sfx"]) fs.mkdirSync(d, { recursive: true });
}
for (const l of S.lines) {
  if (!S.audio) {
    l.dur = est(l.say);
    continue;
  }
  // 配音：一句一個檔，稿子沒改就不重做
  const wav = `assets/voice/${l.id}.wav`, keyFile = `assets/voice/${l.id}.key`;
  // engine "file"：自備的配音檔（真人錄音或任何配音工具的輸出），放在 assets/voice-src/<句子 id>.mp3 或 .wav
  let src = null;
  if (S.engine === "file") {
    const f = fs.existsSync("assets/voice-src") && fs.readdirSync("assets/voice-src").find((f) => f.startsWith(l.id + "."));
    if (!f) throw new Error(`缺配音檔：assets/voice-src/${l.id}.mp3`);
    src = `assets/voice-src/${f}`;
  }
  const key = crypto.createHash("sha1").update([S.engine, S.voice, S.rate, src && fs.statSync(src).size, l.say].join("|")).digest("hex");
  if (!fs.existsSync(wav) || !fs.existsSync(keyFile) || fs.readFileSync(keyFile, "utf8") !== key) {
    const raw = src || `assets/voice/${l.id}.raw.aiff`;
    // engine "say"：macOS 內建語音，只能試聽（Apple 授權不可商用）
    if (!src) sh("say", ["-v", S.voice, "-r", String(S.rate), "-o", raw, l.say]);
    // 去掉頭尾的空白，句子長度才準
    const trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03";
    ff(["-i", raw, "-af", `${trim},areverse,${trim},areverse`, "-ar", "48000", "-ac", "1", wav]);
    if (!src) fs.rmSync(raw);
    fs.writeFileSync(keyFile, key);
    console.log("配音", l.id, l.say);
  }
  l.dur = dur(wav);
}

// ── 2. 時間軸：稿子是時鐘（有配音時用配音的實際長度）──────────────────
let t = S.lead;
const lines = {};
for (const l of S.lines) {
  const t0 = t, t1 = t0 + l.dur;
  lines[l.id] = { t0: r3(t0), t1: r3(t1) };
  t = Math.max(t1 + (l.gap ?? 0.22), t0 + (l.hold ?? 0));
}
const lastEnd = lines[S.lines.at(-1).id].t1;
const DURATION = Math.ceil((lastEnd + S.tail) * 10) / 10;
fs.writeFileSync("lib/timing.js", `// 由 npm run build 產生，不要手改\nglobalThis.ReelTiming = ${JSON.stringify({ duration: DURATION, lines }, null, 2)};\n`);
await import("../lib/timing.js");
await import("../lib/cube-engine.js");
await import("../lib/reel-data.js");
const R = globalThis.ReelData, ev = R.ev;

// ── 3. 音軌（只有 audio: true 才做）────────────────────────────────
if (S.audio) {
  // 人聲：每句放到自己的時間點，整軌校到約 -16 LUFS
  {
    const ins = S.lines.flatMap((l) => ["-i", `assets/voice/${l.id}.wav`]);
    const fc = S.lines.map((l, i) => `[${i}]adelay=${Math.round(lines[l.id].t0 * 1000)}:all=1[v${i}]`).join(";");
    const mix = S.lines.map((_, i) => `[v${i}]`).join("") + `amix=inputs=${S.lines.length}:normalize=0:duration=longest,apad=whole_dur=${DURATION},loudnorm=I=-16:TP=-1.5:LRA=11,atrim=0:${DURATION}[out]`;
    ff([...ins, "-filter_complex", `${fc};${mix}`, "-map", "[out]", "-ar", "48000", "-ac", "2", "assets/audio/voice.wav"]);
  }
  // 音效素材：方塊轉動聲切成 5 個不同的「喀」，其餘取自內建音效庫，全部校到同一個峰值
  // 每個音效先校到同一個峰值（-3 dB），lib/reel-data.js 裡的音量數字才有可比性
  const peakTo = (f, target = -3) => {
    const log = spawnSync("ffmpeg", ["-hide_banner", "-i", f, "-af", "volumedetect", "-f", "null", "-"], { encoding: "utf8" }).stderr;
    const max = parseFloat(/max_volume: (-?[\d.]+) dB/.exec(log)[1]);
    const tmp = f.replace(/\.wav$/, ".tmp.wav");
    ff(["-i", f, "-af", `volume=${(target - max).toFixed(2)}dB`, tmp]);
    fs.renameSync(tmp, f);
  };
  const TURN_SLICES = [[0.6, 0.2], [1.72, 0.26], [3.05, 0.26], [3.62, 0.21], [4.22, 0.2]];
  TURN_SLICES.forEach(([ss, d], i) =>
    ff(["-ss", String(ss), "-t", String(d), "-i", CUBE_SFX, "-af", `afade=t=in:d=0.005,afade=t=out:st=${d - 0.03}:d=0.03,alimiter=limit=0.8`, "-ar", "48000", "-ac", "2", `assets/sfx/turn${i + 1}.wav`]),
  );
  for (const name of ["whoosh-short", "whoosh", "pop", "click-soft", "error", "typing", "impact-bass-1", "chime"]) {
    ff(["-i", path.join(SFX_LIB, `${name}.mp3`), "-ar", "48000", "-ac", "2", `assets/sfx/${name}.wav`]);
  }
  // 升音：原檔的能量集中在第 1–4.4 秒，之後是空白
  ff(["-ss", "1.0", "-t", "3.4", "-i", path.join(SFX_LIB, "riser.mp3"), "-af", "afade=t=in:d=0.8,afade=t=out:st=3.15:d=0.25", "-ar", "48000", "-ac", "2", "assets/sfx/riser-tail.wav"]);
  for (const f of fs.readdirSync("assets/sfx").filter((x) => x.endsWith(".wav"))) peakTo(`assets/sfx/${f}`);
  // 音效軌：每個音效放到 lib/reel-data.js 指定的時間點
  {
    let turn = 0;
    const cues = R.sfx.map((c) => ({ ...c, file: c.name === "turn" ? `assets/sfx/turn${(turn++ % TURN_SLICES.length) + 1}.wav` : `assets/sfx/${c.name}.wav` }));
    const ins = cues.flatMap((c) => ["-i", c.file]);
    const fc = cues.map((c, i) => `[${i}]volume=${c.vol},adelay=${Math.round(c.t * 1000)}:all=1[s${i}]`).join(";");
    const mix = cues.map((_, i) => `[s${i}]`).join("") + `amix=inputs=${cues.length}:normalize=0:duration=longest,apad,alimiter=limit=0.9[out]`;
    ff([...ins, "-filter_complex", `${fc};${mix}`, "-map", "[out]", "-t", String(DURATION), "-ar", "48000", "-ac", "2", "assets/audio/sfx.wav"]);
    console.log("音效", cues.length, "個");
  }
  // 配樂：裁成影片長度，頭尾淡入淡出
  ff(["-ss", String(BGM_OFFSET), "-t", String(DURATION), "-i", BGM_SRC, "-af", `afade=t=in:d=0.4,afade=t=out:st=${DURATION - 2}:d=2`, "-ar", "48000", "-ac", "2", "assets/audio/bgm.wav"]);
}

// ── 4. 畫面文字與字幕 ─────────────────────────────────────────────
const clip = (id, cls, t0, t1, inner, extra = "") =>
  `    <div id="${id}" class="clip ${cls}" data-start="${r3(Math.max(0, t0))}" data-duration="${r3(Math.min(t1, DURATION) - Math.max(0, t0))}"${extra}><span>${inner}</span></div>`;
const terms = (arr, lastOne) => arr.map((x, i) => `<i${lastOne && i === arr.length - 1 ? ' class="one"' : ""}>${i ? "×" : ""}${x}</i>`).join("");
const eq = (k, v) => `<i class="eq">= <u data-num="${k}">${v}</u></i>`;
const N = R.numbers;
const subs = S.lines
  .map((l, i) => {
    if (!l.show) return "";
    const next = S.lines[i + 1];
    const end = Math.min(next ? lines[next.id].t0 - 0.04 : DURATION, lines[l.id].t1 + 1.2);
    // 字幕停超過 3 秒的地方，畫面是方塊在動，不是卡住
    return clip(`w-sub-${l.id}`, "w-sub", lines[l.id].t0 - 0.04, end, l.show, end - lines[l.id].t0 > 2.9 ? " data-hold" : "");
  })
  .filter(Boolean)
  .join("\n");
const top = [
  clip("w-title", "w-top w-title", 0, ev.hookEnd, "魔術方塊<br />有<em>幾種</em>狀態？", " data-hold"),
  clip("w-k1", "w-top w-k", ev.kCenter, ev.kOut, "<b>6</b><small>中心塊・不會動</small>", ' style="left: 60px"'),
  clip("w-k2", "w-top w-k", ev.kCorner, ev.kOut, "<b>8</b><small>角塊</small>", ' style="left: 380px"'),
  clip("w-k3", "w-top w-k", ev.kEdge, ev.kOut, "<b>12</b><small>邊塊</small>", ' style="left: 700px"'),
  clip("w-d3a", "w-top w-detail", ev.cornerPermIn - 0.05, ev.cornerPermOut, terms([8, 7, 6, 5, 4, 3, 2, 1]) + eq("cornerPerm", N.cornerPerm)),
  clip("w-d3b", "w-top w-detail", ev.cornerOriIn, ev.cornerOriOut, terms([3, 3, 3, 3, 3, 3, 3, 1], true) + eq("cornerOri", N.cornerOri)),
  clip("w-d4a", "w-top w-detail", ev.edgePermIn - 0.05, ev.edgePermOut, terms([12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]) + eq("edgePerm", N.edgePerm)),
  clip("w-d4b", "w-top w-detail", ev.edgeOriIn, ev.edgeOriOut, terms([2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1], true) + eq("edgeOri", N.edgeOri)),
  clip("w-c1", "w-top w-term", ev.chain1, ev.chainOut, "<b>8!</b><small>角塊位置</small>", ' style="left: 44px"'),
  clip("w-c2", "w-top w-term", ev.chain2, ev.chainOut, "<b>× 3<sup>7</sup></b><small>角塊朝向</small>", ' style="left: 242px"'),
  clip("w-c3", "w-top w-term", ev.chain3, ev.chainOut, "<b>× 12!</b><small>邊塊位置</small>", ' style="left: 440px"'),
  clip("w-c4", "w-top w-term", ev.chain4, ev.chainOut, "<b>× 2<sup>11</sup></b><small>邊塊朝向</small>", ' style="left: 638px"'),
  clip("w-c5", "w-top w-term", ev.chain5, ev.chainOut, "<b>÷ 2</b><small>不能只換兩塊</small>", ' style="left: 836px"'),
  clip("w-d6", "w-top w-detail", ev.digitsIn, ev.payoffOut, `<span id="w-d6-digits">= ${N.total}</span>`),
  clip("w-hero", "w-top", ev.hero, ev.payoffOut, `約<b><u data-num="jing">${N.jing}</u> 京</b>種`, " data-hold"),
  clip("w-years", "w-top w-big", ev.years, ev.sizeOut, `<u data-num="yearsZhao">${N.yearsZhao}</u> 兆年`),
  clip("w-universe", "w-top", ev.universe, ev.sizeOut, `≈ 宇宙年齡 <em>× <u data-num="universeTimes">${N.universeTimes}</u></em>`),
  clip("w-src", "w-top", ev.universe + 0.2, ev.sizeOut, "以一年 365.25 天、宇宙年齡 138 億年估算"),
  clip("w-god", "w-top w-big", ev.god, DURATION, "20 步"),
  clip("w-god2", "w-top", ev.god + 0.25, DURATION, "任何一種狀態都能還原"),
].join("\n");
fs.writeFileSync("compositions/words.html", fs.readFileSync("tools/words.template.html", "utf8").replace("<!--TOP-->", top).replaceAll("{{D}}", String(DURATION)));
fs.writeFileSync("compositions/captions.html", fs.readFileSync("tools/captions.template.html", "utf8").replace("<!--SUBS-->", subs));

// ── 5. index.html 與方塊場景的長度 ─────────────────────────────────
const audio = (id, i) => `      <audio id="${id}" class="clip" data-start="0" data-duration="${DURATION}" data-track-index="${i}" data-volume="${VOL[id]}" src="assets/audio/${id}.wav"></audio>`;
fs.writeFileSync(
  "index.html",
  fs.readFileSync("tools/index.template.html", "utf8").replaceAll("{{D}}", String(DURATION)).replace("<!--AUDIO-->", S.audio ? [audio("voice", 10), audio("sfx", 11), audio("bgm", 12)].join("\n") : ""),
);
const cube = fs.readFileSync("compositions/cube.html", "utf8");
fs.writeFileSync("compositions/cube.html", cube.replace(/(<canvas id="cube-canvas"[^>]*data-duration=")[^"]+"/, `$1${DURATION}"`));

console.log(`影片長度 ${DURATION} 秒；${S.audio ? "有聲" : "靜音"}；${S.lines.length} 句，最後一句結束於 ${lastEnd} 秒`);
console.log(sh("node", ["tests/verify.mjs"]));
