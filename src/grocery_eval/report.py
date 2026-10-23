"""Aggregate result rows into statistics and render the researcher-facing report.

Inputs are the JSONL rows written by run_eval.py (one row per model call). Outputs:
  report.md     - Markdown report with all tables (renders on GitHub, in VS Code, etc.)
  results.csv   - flat per-call table for pandas / R / spreadsheets
  summary.json  - every aggregate number in the report, machine-readable
  charts/*.png  - optional, only if matplotlib is installed
"""

import csv
import datetime as _dt
import json
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

from .scoring import normalize
from .stats import (agreement_rate, exact_sign_test_p, fmt_num, fmt_pct, mean, median,
                    paired_bootstrap_ci, wilson_interval)

CONTROL_VARIANTS = {"no_context"}
FAILURE_MODE_ORDER = ["wrong_value", "wrong_entity", "partial", "no_answer", "hallucination",
                      "over_refusal", "premise_accepted", "format_violation", "error"]
FAILURE_MODE_HELP = {
    "wrong_value": "a number was given, but the wrong one",
    "wrong_entity": "a name / option / yes-no was given, but the wrong one",
    "partial": "list answer with some but not all items (score = F1)",
    "no_answer": "nothing scoreable in the response",
    "hallucination": "answered an unanswerable question with a specific claim",
    "over_refusal": "said the text lacked the answer when it was there",
    "premise_accepted": "went along with a false premise instead of correcting it",
    "format_violation": "right content, wrong output format",
    "error": "API error / timeout",
}

CSV_COLUMNS = [
    "run_id", "timestamp", "backend", "model", "variant", "question_id", "phrasing", "category",
    "position", "difficulty", "repeat", "temperature", "seed", "question", "expected_response",
    "final_answer", "correct", "score", "content_correct", "format_ok", "refused", "failure_mode",
    "scoring_detail", "judge_verdict", "response_words", "reasoning_words", "prompt_tokens",
    "completion_tokens", "latency_s", "tokens_per_s", "load_s", "done_reason", "error",
]


# --------------------------------------------------------------------------- I/O
def load_jsonl(paths: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {k: r.get(k) for k in CSV_COLUMNS}
            for k in ("final_answer", "question", "expected_response", "scoring_detail"):
                if isinstance(out.get(k), str):
                    out[k] = out[k].replace("\n", " ")
            w.writerow(out)


# --------------------------------------------------------------------------- aggregation helpers
def _acc(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    k = sum(1 for r in rows if r.get("correct"))
    lo, hi = wilson_interval(k, n)
    return {"n": n, "correct": k, "accuracy": (k / n) if n else None, "ci_low": lo, "ci_high": hi,
            "mean_score": mean([float(r.get("score") or 0.0) for r in rows]) if n else None}


def _rate(rows: List[Dict[str, Any]], pred) -> Optional[float]:
    return (sum(1 for r in rows if pred(r)) / len(rows)) if rows else None


def build_summary(rows: List[Dict[str, Any]], baseline_variant: str = "baseline",
                  n_boot: int = 2000) -> Dict[str, Any]:
    models = sorted({r["model"] for r in rows})
    variants = sorted({r["variant"] for r in rows})
    categories = sorted({r["category"] for r in rows})
    valid = [r for r in rows if not r.get("error")]
    scored = [r for r in valid if r["variant"] not in CONTROL_VARIANTS]
    control = [r for r in valid if r["variant"] in CONTROL_VARIANTS]
    by_model = {m: [r for r in scored if r["model"] == m] for m in models}

    summary: Dict[str, Any] = {
        "models": models, "variants": variants, "categories": categories,
        "n_rows": len(rows), "n_errors": len(rows) - len(valid),
        "n_scored_rows": len(scored), "baseline_variant": baseline_variant,
        "control_variants": sorted(CONTROL_VARIANTS),
        "repeats": max([int(r.get("repeat", 0)) for r in rows] + [0]) + 1,
        "temperatures": sorted({r.get("temperature") for r in rows}),
    }

    # ---- headline
    headline: Dict[str, Any] = {}
    for m in models:
        mr = by_model[m]
        h = _acc(mr)
        unans = [r for r in mr if r["category"] == "unanswerable"]
        answerable = [r for r in mr if r["category"] not in ("unanswerable", "false_premise")]
        premise = [r for r in mr if r["category"] == "false_premise"]
        instr = [r for r in mr if r["category"] == "instruction_following"]
        h["hallucination_rate"] = _rate(unans, lambda r: not r.get("correct"))
        h["over_refusal_rate"] = _rate(answerable, lambda r: r.get("refused") and not r.get("correct"))
        h["premise_acceptance_rate"] = _rate(premise, lambda r: r.get("failure_mode") == "premise_accepted")
        h["format_compliance"] = _rate(instr, lambda r: r.get("format_ok") is not False)
        h["median_latency_s"] = median([r.get("latency_s") for r in mr])
        h["mean_tokens_per_s"] = mean([r.get("tokens_per_s") for r in mr if r.get("tokens_per_s")])
        h["mean_answer_words"] = mean([r.get("response_words") for r in mr])
        h["errors"] = sum(1 for r in rows if r["model"] == m and r.get("error"))
        judged = [r for r in mr if r.get("judge_verdict") in ("CORRECT", "INCORRECT")]
        h["judge_accuracy"] = _rate(judged, lambda r: r["judge_verdict"] == "CORRECT")
        h["judge_n"] = len(judged)
        h["judge_agreement_with_heuristic"] = _rate(
            judged, lambda r: (r["judge_verdict"] == "CORRECT") == bool(r.get("correct")))
        # repeat consistency
        groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for r in mr:
            groups[(r["variant"], r["question_id"], r.get("phrasing", 0))].append(r)
        multi = [g for g in groups.values() if len(g) > 1]
        h["consistency"] = mean([agreement_rate(normalize(r["final_answer"]) for r in g) for g in multi]) if multi else None
        h["flip_rate"] = _rate(multi, lambda g: len({bool(r.get("correct")) for r in g}) > 1) if multi else None
        # paraphrase consistency (same question, different wording)
        pgroups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for r in mr:
            pgroups[(r["variant"], r["question_id"], r.get("repeat", 0))].append(r)
        pmulti = [g for g in pgroups.values() if len({r.get("phrasing", 0) for r in g}) > 1]
        h["paraphrase_consistency"] = _rate(pmulti, lambda g: len({bool(r.get("correct")) for r in g}) == 1) if pmulti else None
        h["paraphrase_groups"] = len(pmulti)
        headline[m] = h
    summary["headline"] = headline

    # ---- breakdowns
    def breakdown(field: str, keys: List[Any]) -> Dict[str, Dict[Any, Any]]:
        out: Dict[str, Dict[Any, Any]] = {}
        for m in models:
            out[m] = {}
            for k in keys:
                sub = [r for r in by_model[m] if r.get(field) == k]
                if sub:
                    out[m][str(k)] = _acc(sub)
        return out

    summary["by_category"] = breakdown("category", categories)
    positions = [p for p in ["start", "middle", "end"] if any(r.get("position") == p for r in scored)]
    summary["by_position"] = breakdown("position", positions)
    difficulties = sorted({r.get("difficulty") for r in scored if r.get("difficulty") is not None})
    summary["by_difficulty"] = breakdown("difficulty", difficulties)

    by_variant: Dict[str, Dict[str, Any]] = {}
    for m in models:
        by_variant[m] = {}
        base_rows = [r for r in valid if r["model"] == m and r["variant"] == baseline_variant]
        base_acc = _acc(base_rows)["accuracy"] if base_rows else None
        for v in variants:
            sub = [r for r in valid if r["model"] == m and r["variant"] == v]
            if not sub:
                continue
            a = _acc(sub)
            a["refusal_rate"] = _rate(sub, lambda r: r.get("refused"))
            a["mean_answer_words"] = mean([r.get("response_words") for r in sub])
            a["delta_vs_baseline"] = (a["accuracy"] - base_acc) if (base_acc is not None and a["accuracy"] is not None and v != baseline_variant) else None
            by_variant[m][v] = a
    summary["by_variant"] = by_variant

    ctrl: Dict[str, Any] = {}
    for m in models:
        sub = [r for r in control if r["model"] == m]
        if sub:
            ctrl[m] = {"n": len(sub),
                       "guess_accuracy": _rate(sub, lambda r: r.get("correct") and r["category"] not in ("unanswerable", "false_premise")),
                       "abstention_rate": _rate(sub, lambda r: r.get("refused"))}
    summary["control"] = ctrl

    # ---- failure modes
    fm: Dict[str, Dict[str, int]] = {}
    for m in models:
        c = Counter(r.get("failure_mode") for r in rows if r["model"] == m and r["variant"] not in CONTROL_VARIANTS and r.get("failure_mode"))
        fm[m] = {k: c.get(k, 0) for k in FAILURE_MODE_ORDER}
    summary["failure_modes"] = fm

    # ---- process metrics
    proc: Dict[str, Any] = {}
    for m in models:
        mr = by_model[m]
        cot = [r for r in mr if r["variant"] == "cot"]
        p: Dict[str, Any] = {}
        if cot:
            p["cot_n"] = len(cot)
            p["cot_marker_adherence"] = _rate(cot, lambda r: bool(r.get("reasoning")))
            p["cot_reasoning_words_correct"] = mean([r.get("reasoning_words") for r in cot if r.get("correct")])
            p["cot_reasoning_words_incorrect"] = mean([r.get("reasoning_words") for r in cot if not r.get("correct")])
        p["answer_words_correct"] = mean([r.get("response_words") for r in mr if r.get("correct")])
        p["answer_words_incorrect"] = mean([r.get("response_words") for r in mr if not r.get("correct")])
        thinking_rows = [r for r in mr if r.get("thinking")]
        p["thinking_rows"] = len(thinking_rows)
        proc[m] = p
    summary["process"] = proc

    # ---- pairwise comparisons
    pairwise: List[Dict[str, Any]] = []
    index: Dict[str, Dict[tuple, Dict[str, Any]]] = {}
    for m in models:
        index[m] = {(r["variant"], r["question_id"], r.get("phrasing", 0), r.get("repeat", 0)): r for r in by_model[m]}
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            shared = sorted(set(index[a]) & set(index[b]))
            if not shared:
                continue
            per_q: Dict[str, List[float]] = defaultdict(list)
            a_only = b_only = 0
            for key in shared:
                ca, cb = bool(index[a][key].get("correct")), bool(index[b][key].get("correct"))
                per_q[key[1]].append(float(ca) - float(cb))
                a_only += int(ca and not cb)
                b_only += int(cb and not ca)
            diffs = {q: sum(v) / len(v) for q, v in per_q.items()}
            point, lo, hi = paired_bootstrap_ci(diffs, n_boot=n_boot)
            pairwise.append({
                "model_a": a, "model_b": b, "n_pairs": len(shared),
                "acc_a": _rate([index[a][k] for k in shared], lambda r: r.get("correct")),
                "acc_b": _rate([index[b][k] for k in shared], lambda r: r.get("correct")),
                "diff": point, "ci_low": lo, "ci_high": hi,
                "a_only_correct": a_only, "b_only_correct": b_only,
                "p_value": exact_sign_test_p(a_only, b_only),
            })
    summary["pairwise"] = pairwise

    # ---- per-question accuracy (for the 'hardest questions' table)
    per_q: Dict[str, Dict[str, Any]] = {}
    for qid in sorted({r["question_id"] for r in scored}):
        qrows = [r for r in scored if r["question_id"] == qid]
        entry: Dict[str, Any] = {"category": qrows[0]["category"], "question": qrows[0]["question"],
                                 "overall": _acc(qrows)["accuracy"]}
        for m in models:
            sub = [r for r in qrows if r["model"] == m]
            entry[m] = _acc(sub)["accuracy"] if sub else None
        per_q[qid] = entry
    summary["per_question"] = per_q
    return summary


# --------------------------------------------------------------------------- markdown rendering
def _md_table(headers: Sequence[str], body: Sequence[Sequence[Any]]) -> str:
    def cell(x: Any) -> str:
        s = "" if x is None else str(x)
        return s.replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(cell(h) for h in headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in body:
        lines.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(lines)


def _pick_examples(rows: List[Dict[str, Any]], model: str, n: int) -> List[Dict[str, Any]]:
    fails = [r for r in rows if r["model"] == model and r["variant"] not in CONTROL_VARIANTS
             and not r.get("correct") and r.get("failure_mode")]
    chosen: List[Dict[str, Any]] = []
    seen_modes, seen_variants = set(), set()
    for r in fails:                       # one per failure mode first, spread across variants
        if r["failure_mode"] not in seen_modes and r["variant"] not in seen_variants:
            chosen.append(r)
            seen_modes.add(r["failure_mode"])
            seen_variants.add(r["variant"])
        if len(chosen) >= n:
            break
    for r in fails:                       # then any remaining failure modes
        if len(chosen) >= n:
            break
        if r["failure_mode"] not in seen_modes and r not in chosen:
            chosen.append(r)
            seen_modes.add(r["failure_mode"])
    for r in fails:                       # then fill up
        if len(chosen) >= n:
            break
        if r not in chosen:
            chosen.append(r)
    return chosen


def _clip(s: Any, n: int = 160) -> str:
    s = "" if s is None else str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def render_markdown(summary: Dict[str, Any], rows: List[Dict[str, Any]], meta: Dict[str, Any],
                    n_examples: int = 5, chart_paths: Optional[Dict[str, str]] = None) -> str:
    models = summary["models"]
    H = summary["headline"]
    best = max(models, key=lambda m: (H[m]["accuracy"] or 0)) if models else None
    out: List[str] = []
    title = meta.get("title") or "Grocery-Store Reading Comprehension Benchmark"
    out.append(f"# {title}\n")
    out.append(f"Generated {meta.get('generated_at', _dt.datetime.now().isoformat(timespec='seconds'))}  ")
    out.append(f"Document: `{meta.get('document', 'grocery_store.txt')}` (sha256 `{meta.get('document_sha256', '?')[:12]}`)  ")
    out.append(f"Backend: {meta.get('backend', '?')}; Ollama version: {meta.get('ollama_version') or 'n/a'}  ")
    out.append(f"Rows: {summary['n_rows']} calls ({summary['n_errors']} errors); repeats: {summary['repeats']}; "
               f"temperature(s): {', '.join(str(t) for t in summary['temperatures'])}  ")
    out.append(f"Models: {', '.join(models)}  ")
    out.append(f"Prompt variants: {', '.join(summary['variants'])}\n")

    # ---- headline
    out.append("## 1. Headline results\n")
    out.append("Accuracy excludes the `no_context` control condition (see section 5). "
               "CI = 95% Wilson interval. Hallucination = answered an unanswerable question; "
               "over-refusal = declined an answerable one; premise acceptance = went along with a false premise.\n")
    hdr = ["Model", "n", "Accuracy", "95% CI", "Mean score", "Hallucination", "Over-refusal",
           "Premise accept.", "Format OK", "Repeat consist.", "Median latency", "tok/s", "Words/answer"]
    body = []
    for m in models:
        h = H[m]
        body.append([f"**{m}**" if m == best else m, h["n"], fmt_pct(h["accuracy"]),
                     f"{fmt_pct(h['ci_low'])}\u2013{fmt_pct(h['ci_high'])}", fmt_num(h["mean_score"], 3),
                     fmt_pct(h["hallucination_rate"]), fmt_pct(h["over_refusal_rate"]),
                     fmt_pct(h["premise_acceptance_rate"]), fmt_pct(h["format_compliance"]),
                     fmt_pct(h["consistency"]), f"{fmt_num(h['median_latency_s'])}s",
                     fmt_num(h["mean_tokens_per_s"], 0), fmt_num(h["mean_answer_words"], 0)])
    out.append(_md_table(hdr, body))
    if any(H[m]["judge_n"] for m in models):
        out.append("\nLLM-judge scoring (where available):\n")
        out.append(_md_table(["Model", "Judged rows", "Judge accuracy", "Judge/heuristic agreement"],
                             [[m, H[m]["judge_n"], fmt_pct(H[m]["judge_accuracy"]),
                               fmt_pct(H[m]["judge_agreement_with_heuristic"])] for m in models]))
    if chart_paths and chart_paths.get("headline"):
        out.append(f"\n![Accuracy by model]({chart_paths['headline']})")
    out.append("")

    # ---- by category
    out.append("## 2. Accuracy by question category\n")
    cats = summary["categories"]
    hdr = ["Category"] + models
    body = []
    for c in cats:
        row = [c]
        for m in models:
            e = summary["by_category"][m].get(c)
            row.append(f"{fmt_pct(e['accuracy'])} ({e['correct']}/{e['n']})" if e else "n/a")
        body.append(row)
    out.append(_md_table(hdr, body))
    if chart_paths and chart_paths.get("category"):
        out.append(f"\n![Accuracy by category]({chart_paths['category']})")
    out.append("")

    # ---- by variant
    out.append("## 3. Effect of prompt variant\n")
    out.append(f"Δ is the change in accuracy relative to the `{summary['baseline_variant']}` variant for the same model. "
               "Refusal rate counts answers that said the information was unavailable (desirable only for unanswerable questions).\n")
    hdr = ["Variant"] + [f"{m} acc (Δ)" for m in models] + [f"{m} refusal" for m in models]
    body = []
    for v in summary["variants"]:
        row = [v + (" *(control)*" if v in CONTROL_VARIANTS else "")]
        for m in models:
            e = summary["by_variant"][m].get(v)
            if not e:
                row.append("n/a")
            else:
                d = e.get("delta_vs_baseline")
                row.append(fmt_pct(e["accuracy"]) + (f" ({'+' if d >= 0 else ''}{100 * d:.1f})" if d is not None else ""))
        for m in models:
            e = summary["by_variant"][m].get(v)
            row.append(fmt_pct(e["refusal_rate"]) if e else "n/a")
        body.append(row)
    out.append(_md_table(hdr, body))
    if chart_paths and chart_paths.get("variant"):
        out.append(f"\n![Accuracy by prompt variant]({chart_paths['variant']})")
    out.append("")

    # ---- by position / difficulty
    out.append("## 4. Evidence position and difficulty\n")
    out.append("Position = where the supporting sentence sits in the document (probe for 'lost in the middle' effects). "
               "Unanswerable questions have no position and are excluded here.\n")
    hdr = ["Position"] + models
    body = []
    for p in ["start", "middle", "end"]:
        row = [p]
        for m in models:
            e = summary["by_position"][m].get(p)
            row.append(f"{fmt_pct(e['accuracy'])} ({e['correct']}/{e['n']})" if e else "n/a")
        body.append(row)
    out.append(_md_table(hdr, body))
    out.append("")
    hdr = ["Difficulty"] + models
    body = []
    for d in sorted({k for m in models for k in summary["by_difficulty"][m]}, key=lambda x: int(x)):
        row = [d]
        for m in models:
            e = summary["by_difficulty"][m].get(d)
            row.append(f"{fmt_pct(e['accuracy'])} ({e['correct']}/{e['n']})" if e else "n/a")
        body.append(row)
    out.append(_md_table(hdr, body))
    out.append("")

    # ---- control
    out.append("## 5. Control condition: question without the document (`no_context`)\n")
    if summary["control"]:
        out.append("Without the text, a 'correct' answer is a guess; the desirable behaviour is to abstain. "
                   "High guess accuracy suggests the answers are predictable from the question wording (or memorised).\n")
        out.append(_md_table(["Model", "n", "Guess accuracy (answerable Qs)", "Abstention rate"],
                             [[m, summary["control"][m]["n"], fmt_pct(summary["control"][m]["guess_accuracy"]),
                               fmt_pct(summary["control"][m]["abstention_rate"])] for m in models if m in summary["control"]]))
    else:
        out.append("_Not run._")
    out.append("")

    # ---- pairwise
    out.append("## 6. Pairwise model comparison\n")
    if summary["pairwise"]:
        out.append("Paired on identical (variant, question, phrasing, repeat) items. The difference CI is a "
                   "paired bootstrap over questions (2,000 resamples); p is an exact two-sided sign test on "
                   "discordant pairs (McNemar-style). A CI that excludes 0 and p < 0.05 indicate a reliable difference.\n")
        hdr = ["A", "B", "Pairs", "Acc A", "Acc B", "A \u2212 B", "95% CI", "A right / B wrong", "B right / A wrong", "p"]
        body = []
        for p in summary["pairwise"]:
            body.append([p["model_a"], p["model_b"], p["n_pairs"], fmt_pct(p["acc_a"]), fmt_pct(p["acc_b"]),
                         f"{100 * p['diff']:+.1f} pts", f"[{100 * p['ci_low']:+.1f}, {100 * p['ci_high']:+.1f}]",
                         p["a_only_correct"], p["b_only_correct"],
                         "n/a" if p["p_value"] is None else (f"{p['p_value']:.3f}" if p["p_value"] >= 0.001 else "<0.001")])
        out.append(_md_table(hdr, body))
    else:
        out.append("_Only one model; nothing to compare._")
    out.append("")

    # ---- failure modes
    out.append("## 7. Failure-mode taxonomy\n")
    out.append("Counts of incorrect answers by type (control condition excluded).\n")
    hdr = ["Failure mode", "Meaning"] + models
    body = []
    for fmode in FAILURE_MODE_ORDER:
        if any(summary["failure_modes"][m].get(fmode) for m in models):
            body.append([fmode, FAILURE_MODE_HELP[fmode]] + [summary["failure_modes"][m].get(fmode, 0) for m in models])
    out.append(_md_table(hdr, body) if body else "_No failures recorded._")
    out.append("")

    # ---- consistency / process
    out.append("## 8. Process and consistency metrics\n")
    hdr = ["Model", "Repeat agreement", "Flip rate", "Paraphrase consist.", "CoT marker adherence",
           "CoT words (correct)", "CoT words (wrong)", "Words/answer (correct)", "Words/answer (wrong)", "Rows with <think>"]
    body = []
    for m in models:
        h, p = H[m], summary["process"][m]
        body.append([m, fmt_pct(h["consistency"]), fmt_pct(h["flip_rate"]), fmt_pct(h["paraphrase_consistency"]),
                     fmt_pct(p.get("cot_marker_adherence")), fmt_num(p.get("cot_reasoning_words_correct"), 0),
                     fmt_num(p.get("cot_reasoning_words_incorrect"), 0), fmt_num(p.get("answer_words_correct"), 0),
                     fmt_num(p.get("answer_words_incorrect"), 0), p.get("thinking_rows", 0)])
    out.append(_md_table(hdr, body))
    out.append("\n* Repeat agreement: share of repeated runs giving the modal answer (needs `--repeats > 1`); "
               "flip rate: share of question groups whose correctness changed between repeats.\n"
               "* Paraphrase consistency: share of (question, variant) groups where the original and reworded "
               "question were scored the same (needs `--paraphrases`).\n"
               "* CoT marker adherence: share of `cot` responses that actually produced a `FINAL ANSWER:` line.\n")

    # ---- hardest questions
    out.append("## 9. Hardest questions (all models pooled)\n")
    pq = summary["per_question"]
    hardest = sorted(pq.items(), key=lambda kv: (kv[1]["overall"] if kv[1]["overall"] is not None else 1.0))[:8]
    hdr = ["ID", "Category", "Question", "Overall"] + models
    body = []
    for qid, e in hardest:
        body.append([qid, e["category"], _clip(e["question"], 90), fmt_pct(e["overall"])] + [fmt_pct(e.get(m)) for m in models])
    out.append(_md_table(hdr, body))
    out.append("")

    # ---- examples
    out.append(f"## 10. Example failures (up to {n_examples} per model, one per failure mode first)\n")
    for m in models:
        ex = _pick_examples(rows, m, n_examples)
        out.append(f"### {m}\n")
        if not ex:
            out.append("_No failures._\n")
            continue
        out.append(_md_table(["Q", "Variant", "Failure", "Expected", "Model answer (final)", "Scorer note"],
                             [[r["question_id"], r["variant"], r["failure_mode"], _clip(r.get("expected_response"), 70),
                               _clip(r.get("final_answer"), 160), _clip(r.get("scoring_detail"), 60)] for r in ex]))
        out.append("")

    # ---- methodology
    out.append("## 11. Methodology and reproducibility\n")
    out.append(
        "* **Task.** Each model reads a ~430-word fictional grocery-store description and answers 42 questions "
        "tagged by category, evidence position and difficulty. Questions were authored so that every answerable "
        "item has one unambiguous answer in the text, five items are unanswerable, and four contain a false premise.\n"
        "* **Prompt variants.** The same question is asked under several prompt templates (see `data/prompts.json`); "
        "`baseline` is the reference. `no_context` is a control that omits the document.\n"
        "* **Scoring.** Deterministic string rules (`grocery_eval/scoring.py`): numeric match with ±0.01 tolerance "
        "(number words accepted, clock times ignored), case-insensitive phrase match with aliases, earliest yes/no "
        "signal, first-mentioned option for multiple choice, item-level F1 for lists, abstention regex for "
        "unanswerable items, and true-fact / contradiction markers for false premises. When a response contains a "
        "`FINAL ANSWER:` line only that line is scored; `<think>` blocks are stripped. A scorer self-test "
        "(`python run_eval.py --self-test`) confirms every reference answer scores correct and every "
        "`plausible_wrong` answer scores incorrect.\n"
        "* **Known scorer limitations.** Free-form comparative answers ('bananas are cheaper than apples') can be "
        "mis-read by the first-mention rule; a model that states the right number alongside wrong ones is scored "
        "correct; refusal detection is pattern-based. Use `--judge-model` to add an LLM judge and compare the two "
        "columns, and inspect `results.jsonl` for raw responses.\n"
        "* **Statistics.** Wilson 95% intervals for proportions; paired bootstrap over questions and an exact sign "
        "test for model-vs-model differences. With 42 questions × variants the per-category cells are small; "
        "treat category-level differences of a few points as noise.\n"
        f"* **Reproduce.** `python run_eval.py --models {' '.join(models)} --variants {' '.join(summary['variants'])} "
        f"--repeats {summary['repeats']} --temperature {summary['temperatures'][0] if summary['temperatures'] else 0}` "
        "then `python make_report.py --inputs <run>/results.jsonl`.\n"
        "* **Files.** `results.jsonl` (full prompts and raw responses), `results.csv` (flat table), "
        "`summary.json` (every number in this report), `charts/` (if matplotlib was available).\n")
    return "\n".join(out)


# --------------------------------------------------------------------------- charts (optional)
def make_charts(summary: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    """Write PNG charts if matplotlib is importable; returns {name: relative path}."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return {}
    os.makedirs(os.path.join(out_dir, "charts"), exist_ok=True)
    models = summary["models"]
    paths: Dict[str, str] = {}

    def grouped_bar(name: str, groups: List[str], values: Dict[str, List[Optional[float]]], title: str, errs=None):
        fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(groups) + 2), 4))
        width = 0.8 / max(1, len(models))
        for i, m in enumerate(models):
            xs = [g + i * width for g in range(len(groups))]
            ys = [(v or 0) * 100 for v in values[m]]
            kw = {}
            if errs and errs.get(m):
                kw["yerr"] = errs[m]
                kw["capsize"] = 3
            ax.bar(xs, ys, width=width, label=m, **kw)
        ax.set_xticks([g + width * (len(models) - 1) / 2 for g in range(len(groups))])
        ax.set_xticklabels(groups, rotation=30, ha="right")
        ax.set_ylabel("Accuracy (%)")
        ax.set_ylim(0, 105)
        ax.set_title(title)
        ax.legend(fontsize=8)
        fig.tight_layout()
        rel = os.path.join("charts", f"{name}.png")
        fig.savefig(os.path.join(out_dir, rel), dpi=130)
        plt.close(fig)
        paths[name] = rel

    H = summary["headline"]
    grouped_bar("headline", ["overall"], {m: [H[m]["accuracy"]] for m in models}, "Overall accuracy (95% Wilson CI)",
                errs={m: [[100 * (H[m]["accuracy"] - H[m]["ci_low"])], [100 * (H[m]["ci_high"] - H[m]["accuracy"])]]
                      for m in models if H[m]["accuracy"] is not None})
    cats = summary["categories"]
    grouped_bar("category", cats, {m: [summary["by_category"][m].get(c, {}).get("accuracy") for c in cats] for m in models},
                "Accuracy by question category")
    variants = summary["variants"]
    grouped_bar("variant", variants, {m: [summary["by_variant"][m].get(v, {}).get("accuracy") for v in variants] for m in models},
                "Accuracy by prompt variant")
    return paths


# --------------------------------------------------------------------------- one-call writer
def write_report(rows: List[Dict[str, Any]], out_dir: str, meta: Dict[str, Any], n_examples: int = 5,
                 charts: bool = True, baseline_variant: str = "baseline") -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    summary = build_summary(rows, baseline_variant=baseline_variant)
    summary["meta"] = meta
    chart_paths = make_charts(summary, out_dir) if charts else {}
    md = render_markdown(summary, rows, meta, n_examples=n_examples, chart_paths=chart_paths)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    write_csv(rows, os.path.join(out_dir, "results.csv"))
    return summary
