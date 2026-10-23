/* scoring.js - JavaScript port of grocery_eval/scoring.py (same rules, same failure-mode labels).
   Works in the browser (window.GroceryScoring) and in Node (module.exports). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GroceryScoring = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const REFUSAL_PATTERNS = [
    "\\bnot (?:stated|mentioned|specified|provided|given|included|listed|available|indicated|described|disclosed|shown|present)\\b",
    "\\b(?:does not|doesn't|did not|didn't|do not|don't) (?:say|state|mention|specify|provide|give|include|list|contain|indicate|tell|disclose|show)\\b",
    "\\bno (?:information|mention|details?|data|indication|record)\\b",
    "\\b(?:cannot|can't|can not|unable to|not possible to|impossible to) (?:be )?(?:determine|answer|find|know|tell|say|locate|confirm|identify|verify)\\b",
    "\\b(?:isn't|is not|aren't|are not|was not|wasn't) (?:stated|mentioned|specified|provided|given|included|listed|available|indicated|in the (?:text|document|passage))\\b",
    "\\bnot (?:in|found in|present in|part of|covered by) the (?:text|document|passage|information|provided)\\b",
    "\\bi (?:don't|do not) (?:have|know)\\b",
    "\\bno way to (?:know|tell|determine)\\b",
    "\\binsufficient (?:information|data)\\b",
    "\\bnot enough (?:information|data)\\b",
    "\\bunknown\\b",
    "\\bnot stated\\b",
  ];
  const REFUSAL_RE = new RegExp(REFUSAL_PATTERNS.join("|"), "i");
  const CONTRADICTION_RE = new RegExp([
    "\\bincorrect\\b", "\\bnot accurate\\b", "\\binaccurate\\b", "\\bnot true\\b", "\\buntrue\\b",
    "\\bfalse premise\\b", "\\bmistaken\\b", "\\bactually,", "\\bthat's not (?:right|correct|the case)\\b",
    "\\bthat is not (?:right|correct|the case)\\b", "\\bcontradicts\\b", "\\bno such\\b",
  ].join("|"), "i");
  const THINK_RE = /<think>[\s\S]*?<\/think>/gi;
  const FINAL_RE = /final answer\s*\**\s*[:\-]\s*\**\s*/gi;
  const LEADING_ANSWER_RE = /^\s*(?:final\s+)?answer\s*[:\-]\s*/i;
  const TIME_RE = /\b\d{1,2}:\d{2}\b/g;
  const NUM_RE = /-?\$?\d[\d,]*(?:\.\d+)?/g;
  const NUMBER_WORDS = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
    eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
    twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90, hundred: 100, twice: 2, double: 2 };

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function normalize(text) {
    let t = (text || "").toLowerCase();
    t = t.replace(/[’‘]/g, "'").replace(/[“”]/g, '"');
    t = t.replace(/\b([ap])\.m\./g, "$1m");
    t = t.replace(/\$/g, "").replace(/,/g, "");
    t = t.replace(/(?<!\d)\.|\.(?!\d)/g, " ");
    t = t.replace(/[^\w\s:@'.\-]/g, " ");
    t = t.replace(/-/g, " ");
    return t.replace(/\s+/g, " ").trim();
  }

  function extractNumbers(text) {
    const t = (text || "").replace(TIME_RE, " ");
    const out = [];
    for (const m of t.matchAll(NUM_RE)) {
      const v = parseFloat(m[0].replace(/[$,]/g, ""));
      if (!isNaN(v)) out.push(v);
    }
    for (const tok of t.toLowerCase().match(/[a-z]+/g) || []) if (tok in NUMBER_WORDS) out.push(NUMBER_WORDS[tok]);
    return out;
  }

  const isRefusal = (text) => REFUSAL_RE.test(text || "");

  function splitResponse(raw) {
    raw = raw || "";
    const thinking = (raw.match(THINK_RE) || []).map((m) => m.slice(7, -8).trim()).join("\n");
    const content = raw.replace(THINK_RE, "").trim();
    const matches = [...content.matchAll(FINAL_RE)];
    let final, reasoning;
    if (matches.length) {
      const m = matches[matches.length - 1];
      final = content.slice(m.index + m[0].length).trim();
      reasoning = content.slice(0, m.index).trim();
    } else { final = content; reasoning = ""; }
    final = final.replace(LEADING_ANSWER_RE, "").trim().replace(/^\*+|\*+$/g, "").trim();
    return { thinking, reasoning, final };
  }

  function containsPhrase(norm, phrase) {
    const p = normalize(phrase);
    if (!p) return false;
    return new RegExp("(?<!\\w)" + esc(p) + "(?!\\w)").test(norm);
  }
  function earliest(norm, phrases) {
    let best = null;
    for (const p of phrases) {
      const pn = normalize(p); if (!pn) continue;
      const m = new RegExp("(?<!\\w)" + esc(pn) + "(?!\\w)").exec(norm);
      if (m && (best === null || m.index < best)) best = m.index;
    }
    return best;
  }
  const wc = (s) => (s || "").split(/\s+/).filter(Boolean).length;

  function scoreContains(spec, norm) {
    for (const c of [spec.expected, ...(spec.aliases || [])]) if (containsPhrase(norm, c)) return [true, `matched '${c}'`];
    return [false, "expected phrase not found"];
  }
  function scoreNumeric(spec, norm) {
    const expected = Number(spec.expected), tol = spec.tolerance ?? 0.011;
    for (const c of spec.aliases || []) if (containsPhrase(norm, c)) return [true, `matched alias '${c}'`, true];
    const nums = extractNumbers(norm);
    for (const n of nums) if (Math.abs(n - expected) <= tol) return [true, `found ${n}`, true];
    if (nums.length) return [false, `numbers found [${[...new Set(nums)].sort((a, b) => a - b).slice(0, 8).join(", ")}] but not ${expected}`, true];
    for (const c of spec.wrong_aliases || []) if (containsPhrase(norm, c)) return [false, `matched wrong-answer phrase '${c}'`, true];
    return [false, "no number in answer", false];
  }
  function scoreYesNo(spec, norm) {
    const y = earliest(norm, spec.yes_aliases || ["yes"]), n = earliest(norm, spec.no_aliases || ["no"]);
    if (y === null && n === null) return [false, "no yes/no signal found", false];
    const chosen = (n === null || (y !== null && y < n)) ? "yes" : "no";
    return [chosen === spec.expected.toLowerCase(), `read as '${chosen}'`, true];
  }
  function scoreChoice(spec, norm) {
    const mentions = [];
    for (const opt of spec.options) {
      const m = new RegExp("(?<!\\w)" + esc(normalize(opt)) + "s?(?!\\w)").exec(norm);
      if (m) mentions.push([m.index, opt]);
    }
    if (!mentions.length) return [false, "no option mentioned", false];
    mentions.sort((a, b) => a[0] - b[0]);
    return [mentions[0][1] === spec.expected, `read as '${mentions[0][1]}' (mentioned: ${mentions.map((x) => x[1]).join(", ")})`, true];
  }
  function scoreSet(spec, norm) {
    const expected = spec.expected.map(normalize);
    const tp = expected.filter((x) => containsPhrase(norm, x)).length;
    const fp = (spec.distractors || []).map(normalize).filter((d) => containsPhrase(norm, d)).length;
    const fn = expected.length - tp;
    let f1 = 0;
    if (tp) { const p = tp / (tp + fp), r = tp / (tp + fn); f1 = 2 * p * r / (p + r); }
    let formatOk = true;
    if (spec.format === "list_only") {
      const allowed = new Set();
      expected.forEach((x) => x.split(" ").forEach((w) => allowed.add(w)));
      (spec.allowed_extra_words || []).forEach((w) => allowed.add(normalize(w)));
      const extra = norm.split(" ").filter((w) => w && !allowed.has(w));
      formatOk = extra.length === 0;
      if (extra.length) return [f1, `F1=${f1.toFixed(2)}; extra words [${extra.slice(0, 6).join(", ")}]`, formatOk];
    }
    return [f1, `F1=${f1.toFixed(2)} (hits ${tp}/${expected.length}, distractors ${fp})`, formatOk];
  }
  function scoreExact(spec, norm) {
    const tokens = norm.split(" ").filter(Boolean), formatOk = tokens.length === 1;
    const expected = String(spec.expected).toLowerCase(), expNum = parseFloat(expected);
    let content;
    if (!isNaN(expNum)) content = extractNumbers(norm).some((n) => Math.abs(n - expNum) <= 0.011);
    else if (expected === "yes" || expected === "no") {
      const y = earliest(norm, ["yes"]), n = earliest(norm, ["no"]);
      if (y === null && n === null) content = false;
      else if (n === null || (y !== null && y < n)) content = expected === "yes";
      else content = expected === "no";
    } else content = containsPhrase(norm, expected);
    return [content, formatOk, `tokens=${tokens.length}, content=${content ? "ok" : "wrong"}`];
  }

  function scoreResponse(question, rawResponse, error) {
    const { thinking, reasoning, final } = splitResponse(rawResponse);
    const norm = normalize(final), spec = question.scoring, qtype = spec.type, refused = isRefusal(final);
    const r = { thinking, reasoning, final_answer: final, response_words: wc((rawResponse || "").replace(THINK_RE, "")),
      reasoning_words: wc(reasoning) + wc(thinking), refused, format_ok: null, content_correct: false, correct: false,
      score: 0, failure_mode: null, scoring_detail: "" };
    const set = (o) => Object.assign(r, o);
    if (error) return set({ failure_mode: "error", scoring_detail: String(error).slice(0, 200) });
    if (!norm) return set({ failure_mode: "no_answer", scoring_detail: "empty response" });
    if (qtype === "refusal") {
      return refused ? set({ correct: true, content_correct: true, score: 1, scoring_detail: "abstained" })
                     : set({ failure_mode: "hallucination", scoring_detail: "gave a specific answer" });
    }
    if (qtype === "premise_correction") {
      const matched = (spec.aliases || []).find((a) => containsPhrase(norm, a));
      if (matched !== undefined) return set({ correct: true, content_correct: true, score: 1, scoring_detail: `corrected via '${matched}'` });
      if (CONTRADICTION_RE.test(final)) return set({ correct: true, content_correct: true, score: 1, scoring_detail: "generic contradiction marker" });
      return set({ failure_mode: "premise_accepted", scoring_detail: refused ? "refused without correcting the premise" : "went along with the premise" });
    }
    let contentCorrect = false, formatOk = null, detail = "", hadSignal = true, partial = null;
    if (qtype === "contains") [contentCorrect, detail] = scoreContains(spec, norm);
    else if (qtype === "numeric") [contentCorrect, detail, hadSignal] = scoreNumeric(spec, norm);
    else if (qtype === "yes_no") [contentCorrect, detail, hadSignal] = scoreYesNo(spec, norm);
    else if (qtype === "choice") [contentCorrect, detail, hadSignal] = scoreChoice(spec, norm);
    else if (qtype === "set") { let f1; [f1, detail, formatOk] = scoreSet(spec, norm); partial = f1; contentCorrect = f1 >= 0.999; hadSignal = f1 > 0; }
    else if (qtype === "exact") [contentCorrect, formatOk, detail] = scoreExact(spec, norm);
    else throw new Error("Unknown scoring type " + qtype);
    set({ content_correct: contentCorrect, format_ok: formatOk, scoring_detail: detail });
    if (contentCorrect) return formatOk === false ? set({ failure_mode: "format_violation" }) : set({ correct: true, score: 1 });
    if (refused) return set({ failure_mode: "over_refusal" });
    if (partial !== null && partial > 0) return set({ failure_mode: "partial", score: Math.round(partial * 1000) / 1000 });
    if (!hadSignal) return set({ failure_mode: "no_answer" });
    return set({ failure_mode: qtype === "numeric" ? "wrong_value" : "wrong_entity" });
  }

  const FAILURE_MODE_HELP = {
    wrong_value: "a number was given, but the wrong one",
    wrong_entity: "a name / option / yes-no was given, but the wrong one",
    partial: "list answer with some but not all items",
    no_answer: "nothing scoreable in the response",
    hallucination: "answered an unanswerable question with a specific claim",
    over_refusal: "said the text lacked the answer when it was there",
    premise_accepted: "went along with a false premise instead of correcting it",
    format_violation: "right content, wrong output format",
    error: "API error / timeout",
  };

  return { normalize, extractNumbers, isRefusal, splitResponse, scoreResponse, FAILURE_MODE_HELP };
});
