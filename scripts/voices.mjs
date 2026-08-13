#!/usr/bin/env node
/**
 * 顧客ボイス台帳 CLI
 *
 *   node "${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" <new|validate|query|stats> [options]
 *
 * 依存パッケージ0（Node 標準モジュールのみ）。
 * スキーマの正本は plugin の skills/pd/uiux/voice-schema.md と scripts/validate.py。
 * **この3つは必ず一致させること。**
 *
 * v2.0.0: 置き場所を pd/voices/{プロダクト}/{年}/ に変更し、index コマンドを廃止した。
 * 索引ファイルは更新漏れで実態と乖離する（pd の規約）。一覧は query / stats で取る。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(__dirname, "..");

// 検証対象のプロジェクト。validate.py と同じ順序で解決する。
const ROOT = path.resolve(
  process.env.PD_PROJECT_DIR || process.env.CLAUDE_PROJECT_DIR || process.cwd(),
);
// 旧レイアウト（root 直下）でも読めるようにする
const VOICES_DIR = fs.existsSync(path.join(ROOT, "pd", "voices"))
  ? path.join(ROOT, "pd", "voices")
  : fs.existsSync(path.join(ROOT, "voices"))
    ? path.join(ROOT, "voices")
    : path.join(ROOT, "pd", "voices");
const ENTRIES_DIR = VOICES_DIR;
const TEMPLATE = path.join(PLUGIN_ROOT, "skills", "pd", "uiux", "voice-template.md");
const TAXONOMY = path.join(VOICES_DIR, "taxonomy.json");

const ID_PREFIX = "VOICE";

// ---------------------------------------------------------------- スキーマ定義
// skills/pd/uiux/voice-schema.md および scripts/validate.py と完全に一致させる
const REQUIRED_KEYS = [
  "id",
  "product",
  "type",
  "source",
  "speaker_role",
  "speaker_id",
  "captured_at",
  "captured_by",
  "layer",
  "severity",
  "frequency",
  "status",
];

const OPTIONAL_KEYS = [
  "object",
  "phase",
  "screen",
  "principles",
  "linked_stories",
  "linked_uxdr",
  "tags",
  "context",
];

const ENUMS = {
  type: ["pain", "request", "negative", "positive", "question"],
  source: [
    "interview",
    "in-app-feedback",
    "review",
    "support-ticket",
    "sales-call",
    "meeting",
    "user-validation",
  ],
  speaker_role: ["guest", "store-staff", "store-owner", "admin", "unknown"],
  layer: ["戦略", "要件", "構造", "骨格", "表層", "未判定"],
  severity: ["high", "medium", "low"],
  status: ["未検証", "検証済み", "対応中", "解消", "却下"],
};

const SECTIONS = ["## 逐語", "## 文脈", "## 解釈", "## 派生"];

// ---------------------------------------------------------------- 小物

const red = (s) => `\u001b[31m${s}\u001b[0m`;
const green = (s) => `\u001b[32m${s}\u001b[0m`;
const yellow = (s) => `\u001b[33m${s}\u001b[0m`;
const dim = (s) => `\u001b[2m${s}\u001b[0m`;

function die(msg) {
  console.error(red(`✗ ${msg}`));
  process.exit(1);
}

/** frontmatter を自前でパースする（スカラーとインライン配列のみ対応） */
function parseFrontmatter(text) {
  if (!text.startsWith("---")) return { data: null, body: text };
  const lines = text.split("\n");
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) return { data: null, body: text };

  const data = {};
  for (let i = 1; i < end; i++) {
    const line = lines[i];
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const sep = line.indexOf(":");
    if (sep === -1) continue;
    const key = line.slice(0, sep).trim();
    let raw = line.slice(sep + 1).trim();
    // 値のあとの " # コメント" を落とす（値の途中の # は残す）
    const c = raw.indexOf(" #");
    if (c !== -1) raw = raw.slice(0, c).trim();
    data[key] = parseValue(raw);
  }
  return { data, body: lines.slice(end + 1).join("\n") };
}

function parseValue(raw) {
  if (raw === "") return "";
  if (raw.startsWith("[") && raw.endsWith("]")) {
    const inner = raw.slice(1, -1).trim();
    if (!inner) return [];
    return inner.split(",").map((v) => parseScalar(v.trim()));
  }
  return parseScalar(raw);
}

function parseScalar(raw) {
  if (
    (raw.startsWith('"') && raw.endsWith('"')) ||
    (raw.startsWith("'") && raw.endsWith("'"))
  ) {
    return raw.slice(1, -1);
  }
  if (/^-?\d+$/.test(raw)) return Number(raw);
  return raw;
}

// pd/voices/{プロダクト}/{年}/VOICE-NNN-<slug>.md を再帰的に集める
function walkMd(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walkMd(p));
    else if (e.name.endsWith(".md") && e.name.startsWith("VOICE-")) out.push(p);
  }
  return out;
}

function listEntries() {
  return walkMd(ENTRIES_DIR)
    .sort()
    .map((file) => {
      const text = fs.readFileSync(file, "utf8");
      const { data, body } = parseFrontmatter(text);
      return {
        file,
        name: path.basename(file),
        data: data || {},
        body,
        hasFm: data !== null,
      };
    });
}

function readTaxonomy() {
  if (!fs.existsSync(TAXONOMY)) return { object: [], phase: [] };
  try {
    const t = JSON.parse(fs.readFileSync(TAXONOMY, "utf8"));
    return { object: t.object || [], phase: t.phase || [] };
  } catch {
    return { object: [], phase: [] };
  }
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith("--")) {
        out[key] = true;
      } else {
        out[key] = next;
        i++;
      }
    } else {
      out._.push(a);
    }
  }
  return out;
}

// ---------------------------------------------------------------- validate

function validateEntry(entry, taxonomy, seenIds) {
  const errs = [];
  const { data, body, name, hasFm } = entry;

  if (!hasFm) {
    errs.push("frontmatter がない");
    return errs;
  }

  for (const k of REQUIRED_KEYS) {
    if (data[k] === undefined || data[k] === "") errs.push(`必須キーがない: ${k}`);
  }

  const known = new Set([...REQUIRED_KEYS, ...OPTIONAL_KEYS]);
  for (const k of Object.keys(data)) {
    if (!known.has(k)) errs.push(`未知のキー: ${k}（スキーマにないキーは追加できない）`);
  }

  for (const [k, allowed] of Object.entries(ENUMS)) {
    if (data[k] !== undefined && !allowed.includes(String(data[k]))) {
      errs.push(`${k} が不正: "${data[k]}"（許容: ${allowed.join(" / ")}）`);
    }
  }

  const idRe = new RegExp(`^${ID_PREFIX}-\\d{3,}$`);
  if (data.id !== undefined) {
    if (!idRe.test(String(data.id))) {
      errs.push(`id の形式が不正: "${data.id}"（${ID_PREFIX}-001 の形）`);
    } else {
      if (!name.startsWith(`${data.id}-`) && name !== `${data.id}.md`) {
        errs.push(`id とファイル名が一致しない: id=${data.id} / file=${name}`);
      }
      if (seenIds.has(data.id)) errs.push(`id が重複: ${data.id}`);
      seenIds.add(data.id);
    }
  }

  if (data.captured_at !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(String(data.captured_at))) {
    errs.push(`captured_at が YYYY-MM-DD でない: "${data.captured_at}"`);
  }

  if (data.frequency !== undefined) {
    if (!Number.isInteger(data.frequency) || data.frequency < 1) {
      errs.push(`frequency は1以上の整数: "${data.frequency}"`);
    }
  }

  if (data.principles !== undefined) {
    if (!Array.isArray(data.principles) || data.principles.some((n) => !Number.isInteger(n))) {
      errs.push("principles は整数の配列");
    }
  }

  for (const k of ["linked_stories", "linked_uxdr", "tags"]) {
    if (data[k] !== undefined && !Array.isArray(data[k])) {
      errs.push(`${k} は配列で書く（例: [a, b]）`);
    }
  }

  // taxonomy が非空のときだけ検査（プロダクト固有語彙のため）
  for (const k of ["object", "phase"]) {
    const allowed = taxonomy[k];
    if (allowed.length > 0 && data[k] !== undefined && !allowed.includes(String(data[k]))) {
      errs.push(`${k} が taxonomy.json にない: "${data[k]}"（許容: ${allowed.join(" / ")}）`);
    }
  }

  for (const s of SECTIONS) {
    if (!body.includes(`\n${s}`) && !body.startsWith(s)) errs.push(`セクションがない: ${s}`);
  }

  // 逐語の引用行を必須にする（要約したボイスを登録させないため）
  // 「> 」だけの空引用は逐語として認めない
  const quoteLines = extractSection(body, "## 逐語")
    .split("\n")
    .filter((l) => l.trim().startsWith(">") && l.trim().replace(/^>+/, "").trim() !== "");
  if (quoteLines.length === 0) {
    errs.push("## 逐語 に引用行（> …）がない。逐語が取れていない場合は「> 逐語なし」と書き severity を一段下げる");
  }

  return errs;
}

function extractSection(body, heading) {
  const idx = body.indexOf(heading);
  if (idx === -1) return "";
  const rest = body.slice(idx + heading.length);
  const next = rest.search(/\n##\s/);
  return next === -1 ? rest : rest.slice(0, next);
}

function cmdValidate() {
  const entries = listEntries();
  const taxonomy = readTaxonomy();
  const seenIds = new Set();
  let bad = 0;

  for (const e of entries) {
    const errs = validateEntry(e, taxonomy, seenIds);
    if (errs.length) {
      bad++;
      console.error(red(`✗ ${e.name}`));
      for (const m of errs) console.error(`    - ${m}`);
    }
  }

  if (entries.length === 0) {
    console.log(yellow("⚠ エントリが0件（台帳が空）。一次情報はまだ存在しない。"));
    console.log(dim(`  ${path.relative(ROOT, ENTRIES_DIR)} に VOICE-001-*.md を作る: voices.mjs new --help`));
    return;
  }
  if (bad) {
    console.error(red(`\n✗ ${bad} / ${entries.length} 件が不適合`));
    process.exit(1);
  }
  console.log(green(`✓ ${entries.length} 件すべて適合`));
}

// ---------------------------------------------------------------- new

const NEW_REQUIRED = ["product", "type", "source", "speaker_role", "speaker_id", "captured_at", "captured_by", "slug"];

function cmdNew(args) {
  if (args.help) {
    console.log(`使い方:
  voices.mjs new --product <プロダクト名> --type <${ENUMS.type.join("|")}> \\
    --source <${ENUMS.source.join("|")}> \\
    --speaker_role <${ENUMS.speaker_role.join("|")}> \\
    --speaker_id <匿名化ID> --captured_at <YYYY-MM-DD> --captured_by <記録者> \\
    --slug <english-slug> [--screen <画面名>] [--severity <high|medium|low>]`);
    return;
  }

  const missing = NEW_REQUIRED.filter((k) => !args[k] || args[k] === true);
  if (missing.length) die(`引数が足りない: ${missing.map((m) => "--" + m).join(" ")}\n  詳しくは: voices.mjs new --help`);

  for (const k of ["type", "source", "speaker_role"]) {
    if (!ENUMS[k].includes(args[k])) die(`--${k} が不正: "${args[k]}"（許容: ${ENUMS[k].join(" / ")}）`);
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(args.captured_at)) die("--captured_at は YYYY-MM-DD");
  const severity = args.severity || "medium";
  if (!ENUMS.severity.includes(severity)) die(`--severity が不正: "${severity}"`);

  if (!fs.existsSync(TEMPLATE)) die(`雛形がない: ${TEMPLATE}`);

  // pd/voices/{プロダクト}/{年}/ に置く。年は captured_at（発言された日）から取る。
  const year = args.captured_at.slice(0, 4);
  const dir = path.join(ENTRIES_DIR, args.product, year);
  fs.mkdirSync(dir, { recursive: true });

  // ID はプロダクトをまたいで一意（引用時に迷わないため）
  const max = listEntries().reduce((m, e) => {
    const n = Number(String(e.data.id || "").split("-")[1]);
    return Number.isInteger(n) && n > m ? n : m;
  }, 0);
  const id = `${ID_PREFIX}-${String(max + 1).padStart(3, "0")}`;
  const file = path.join(dir, `${id}-${args.slug}.md`);
  if (fs.existsSync(file)) die(`すでに存在する: ${path.relative(ROOT, file)}`);

  let text = fs.readFileSync(TEMPLATE, "utf8");
  const set = {
    id,
    product: args.product,
    type: args.type,
    source: args.source,
    speaker_role: args.speaker_role,
    speaker_id: args.speaker_id,
    captured_at: args.captured_at,
    captured_by: args.captured_by,
    severity,
  };
  for (const [k, v] of Object.entries(set)) {
    text = text.replace(new RegExp(`^${k}:.*$`, "m"), `${k}: ${v}`);
  }
  if (args.screen && args.screen !== true) {
    text = text.replace(/^status:.*$/m, (m) => `${m}\nscreen: ${args.screen}`);
  }

  fs.writeFileSync(file, text);
  console.log(green(`✓ 作成: ${path.relative(ROOT, file)}`));
  console.log(dim("  逐語をそのまま貼る（要約・敬語化をしない）→ voices.mjs validate"));
}

// ---------------------------------------------------------------- query

const QUERY_KEYS = [
  "id",
  "type",
  "source",
  "speaker_role",
  "speaker_id",
  "layer",
  "severity",
  "status",
  "screen",
  "object",
  "phase",
];

function cmdQuery(args) {
  const entries = listEntries();
  const conds = [];

  for (const k of QUERY_KEYS) {
    if (args[k] && args[k] !== true) conds.push([k, args[k]]);
  }
  const tag = args.tag && args.tag !== true ? args.tag : null;
  const principle = args.principle && args.principle !== true ? Number(args.principle) : null;

  if (conds.length === 0 && !tag && principle === null) {
    console.log(`使い方: voices.mjs query [${QUERY_KEYS.map((k) => "--" + k).join(" ] [")}] [--tag <t>] [--principle <n>]`);
    return;
  }

  const hits = entries.filter((e) => {
    for (const [k, v] of conds) {
      if (!String(e.data[k] ?? "").includes(v)) return false;
    }
    if (tag && !(Array.isArray(e.data.tags) ? e.data.tags.map(String) : []).includes(tag)) return false;
    if (principle !== null && !(Array.isArray(e.data.principles) ? e.data.principles : []).includes(principle)) {
      return false;
    }
    return true;
  });

  if (hits.length === 0) {
    console.log(yellow("該当なし ＝ この条件に対する一次情報なし"));
    console.log(dim("  → 改善案を出す場合は「デザイナー起案」と明記すること"));
    return;
  }

  for (const e of hits) {
    const quote = extractSection(e.body, "## 逐語")
      .split("\n")
      .find((l) => l.trim().startsWith(">"));
    console.log(
      `${e.data.id}  ${String(e.data.type).padEnd(8)} ${String(e.data.severity).padEnd(6)} freq=${e.data.frequency}  ${e.data.status}  ${e.data.screen ?? ""}`,
    );
    console.log(dim(`   ${(quote || "> (逐語なし)").trim()}`));
  }
  console.log(green(`\n✓ ${hits.length} 件`));
}

// ---------------------------------------------------------------- stats

function cmdStats() {
  const entries = listEntries();
  if (entries.length === 0) {
    console.log(yellow("⚠ エントリが0件。集計対象なし。"));
    return;
  }
  const count = (key) => {
    const m = new Map();
    for (const e of entries) {
      const v = String(e.data[key] ?? "(未設定)");
      m.set(v, (m.get(v) || 0) + 1);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  };
  for (const key of ["type", "status", "severity", "layer", "screen", "speaker_role"]) {
    console.log(`\n■ ${key}`);
    for (const [v, n] of count(key)) console.log(`   ${String(v).padEnd(16)} ${n}`);
  }
  console.log(green(`\n合計 ${entries.length} 件`));
}

// ---------------------------------------------------------------- entry

const [, , sub, ...rest] = process.argv;
const args = parseArgs(rest);

switch (sub) {
  case "new":
    cmdNew(args);
    break;
  case "validate":
    cmdValidate();
    break;
  case "query":
    cmdQuery(args);
    break;
  case "stats":
    cmdStats();
    break;
  default:
    console.log(`顧客ボイス台帳 CLI

  new       新規エントリを作る（ID は自動採番）
  validate  スキーマ検査（逐語の引用行が無いと落ちる）
  query     引き当て（0件なら「一次情報なし」）
  stats     集計

  実行: node "\${CLAUDE_PLUGIN_ROOT}/scripts/voices.mjs" <サブコマンド>

台帳: ${path.relative(ROOT, VOICES_DIR)}
スキーマ: uiux/voices/SCHEMA.md`);
    if (sub) process.exit(1);
}
