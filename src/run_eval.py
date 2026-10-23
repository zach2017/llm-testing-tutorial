#!/usr/bin/env python3
"""Run the grocery-store reading-comprehension benchmark against Ollama models.

Examples
--------
  # smoke test the pipeline without Ollama (fake models)
  python run_eval.py --backend mock --models mock-strong mock-weak --out results/demo

  # real run: three small models, all prompt variants, deterministic decoding
  python run_eval.py --models llama3.2:1b llama3.2:3b gemma3:1b --out results/run1

  # consistency study: sample 3 times at temperature 0.7, include paraphrased questions
  python run_eval.py --models llama3.2:1b --repeats 3 --temperature 0.7 --paraphrases --out results/consistency

  # add an LLM judge (a bigger local model) as a second opinion on the heuristic scorer
  python run_eval.py --models llama3.2:1b --judge-model qwen2.5:7b --out results/judged

  # check the scorer itself against the reference answers / plausible wrong answers
  python run_eval.py --self-test

Every call is appended to <out>/results.jsonl as it completes, so a run can be resumed with
--resume. When all calls are done, results.csv, summary.json and report.md are written.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grocery_eval import license as lic  # noqa: E402
from grocery_eval.mock_backend import MOCK_MODELS, mock_chat  # noqa: E402
from grocery_eval.ollama_client import OllamaClient, OllamaError  # noqa: E402
from grocery_eval.report import load_jsonl, write_report  # noqa: E402
from grocery_eval.scoring import score_response  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "data")
DEFAULT_MODELS = ["llama3.2:1b", "llama3.2:3b", "gemma3:1b"]

JUDGE_PROMPT = (
    "You are grading an answer to a reading-comprehension question about a short text.\n\n"
    "QUESTION: {question}\n"
    "REFERENCE ANSWER: {reference}\n"
    "CANDIDATE ANSWER: {candidate}\n\n"
    "Is the candidate answer correct, i.e. does it convey the same answer as the reference "
    "(extra explanation is fine, a different claim is not)? Reply with exactly one word: CORRECT or INCORRECT."
)


# --------------------------------------------------------------------------- data loading
def load_data(data_dir: str) -> Dict[str, Any]:
    with open(os.path.join(data_dir, "questions.json"), "r", encoding="utf-8") as f:
        qfile = json.load(f)
    with open(os.path.join(data_dir, "prompts.json"), "r", encoding="utf-8") as f:
        pfile = json.load(f)
    doc_path = os.path.join(data_dir, qfile.get("document", "grocery_store.txt"))
    with open(doc_path, "r", encoding="utf-8") as f:
        document = f.read().strip()
    sha = hashlib.sha256(document.encode("utf-8")).hexdigest()
    return {"questions": qfile["questions"], "prompts": pfile, "document": document,
            "document_name": os.path.basename(doc_path), "document_sha256": sha}


def expand_questions(questions: List[Dict[str, Any]], include_paraphrases: bool) -> List[Dict[str, Any]]:
    """Return question instances; paraphrases become extra instances with phrasing >= 1."""
    out = []
    for q in questions:
        base = dict(q)
        base["phrasing"] = 0
        out.append(base)
        if include_paraphrases:
            for i, text in enumerate(q.get("paraphrases", []), start=1):
                alt = dict(q)
                alt["phrasing"] = i
                alt["question"] = text
                out.append(alt)
    return out


def build_messages(variant: Dict[str, Any], prompts: Dict[str, Any], document: str,
                   question_text: str) -> List[Dict[str, str]]:
    mode = variant.get("context_mode", "document")
    if mode == "document":
        context = document
    elif mode == "document_plus_distractor":
        context = document + "\n\n" + prompts.get("distractor_text", "")
    else:
        context = ""
    few_shot = "\n\n".join(f"QUESTION: {ex['question']}\nANSWER: {ex['answer']}"
                           for ex in prompts.get("few_shot_examples", []))

    def render(template: Optional[str]) -> Optional[str]:
        if template is None:
            return None
        return (template.replace("{context}", context)
                        .replace("{question}", question_text)
                        .replace("{few_shot}", few_shot))

    messages: List[Dict[str, str]] = []
    system = render(variant.get("system"))
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": render(variant["user"]) or question_text})
    return messages


# --------------------------------------------------------------------------- self-test
def self_test(data: Dict[str, Any]) -> int:
    """Score every reference answer (must be correct) and every plausible_wrong answer (must be wrong)."""
    failures = 0
    for q in data["questions"]:
        good = score_response(q, q["expected_response"])
        if not good["correct"]:
            failures += 1
            print(f"[FAIL] {q['id']} reference answer scored INCORRECT: {good['scoring_detail']}")
        bad = score_response(q, q["plausible_wrong"])
        if bad["correct"]:
            failures += 1
            print(f"[FAIL] {q['id']} plausible_wrong answer scored CORRECT: {bad['scoring_detail']}")
        cot = score_response(q, "Step 1: look at the text.\nStep 2: reason.\nFINAL ANSWER: " + q["expected_response"])
        if not cot["correct"]:
            failures += 1
            print(f"[FAIL] {q['id']} reference answer behind FINAL ANSWER scored INCORRECT: {cot['scoring_detail']}")
    n = len(data["questions"])
    print(f"Self-test: {3 * n - failures}/{3 * n} checks passed across {n} questions.")
    return 1 if failures else 0


# --------------------------------------------------------------------------- main loop
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=None, help=f"Ollama model tags (default: {' '.join(DEFAULT_MODELS)})")
    ap.add_argument("--variants", nargs="+", default=None, help="prompt variants to run (default: all in prompts.json)")
    ap.add_argument("--questions", nargs="+", default=None, help="question ids to run, e.g. Q01 Q15 (default: all)")
    ap.add_argument("--categories", nargs="+", default=None, help="restrict to these categories")
    ap.add_argument("--limit", type=int, default=None, help="only the first N questions (quick smoke test)")
    ap.add_argument("--paraphrases", action="store_true", help="also ask the paraphrased versions of questions that have them")
    ap.add_argument("--repeats", type=int, default=1, help="times to ask each question (use with --temperature > 0)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=42, help="base seed; repeat i uses seed+i when temperature > 0")
    ap.add_argument("--num-predict", type=int, default=400, help="max tokens to generate per answer")
    ap.add_argument("--num-ctx", type=int, default=None, help="context window to request from Ollama (optional)")
    ap.add_argument("--think", choices=["on", "off"], default=None,
                    help="send think=true/false to Ollama (only for models that support thinking)")
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--timeout", type=float, default=180.0, help="seconds to wait for one answer")
    ap.add_argument("--backend", choices=["ollama", "mock"], default="ollama")
    ap.add_argument("--judge-model", default=None, help="Ollama model used as an LLM judge (optional, slower)")
    ap.add_argument("--data", default=DEFAULT_DATA, help="folder containing grocery_store.txt, questions.json, prompts.json")
    ap.add_argument("--out", default=None, help="output folder (default: results/<timestamp>)")
    ap.add_argument("--resume", action="store_true", help="skip (model, variant, question, repeat) rows already in results.jsonl")
    ap.add_argument("--no-report", action="store_true", help="only collect answers; build the report later with make_report.py")
    ap.add_argument("--no-charts", action="store_true")
    ap.add_argument("--examples", type=int, default=5, help="example failures per model in the report")
    ap.add_argument("--list-models", action="store_true", help="print the models installed in Ollama and exit")
    ap.add_argument("--self-test", action="store_true", help="validate the scorer against the reference answers and exit")
    ap.add_argument("--dry-run", action="store_true", help="print one rendered prompt per variant and exit")
    args = ap.parse_args(argv)

    data = load_data(args.data)
    if args.self_test:
        return self_test(data)

    prompts = data["prompts"]
    variant_names = args.variants or list(prompts["variants"].keys())
    unknown = [v for v in variant_names if v not in prompts["variants"]]
    if unknown:
        ap.error(f"unknown variant(s) {unknown}; available: {list(prompts['variants'])}")

    questions = data["questions"]
    if args.questions:
        wanted = set(args.questions)
        questions = [q for q in questions if q["id"] in wanted]
    if args.categories:
        questions = [q for q in questions if q["category"] in set(args.categories)]
    if args.limit:
        questions = questions[: args.limit]
    # --- license / trial limits (the mock backend and self-test are always free)
    lic_status = lic.status()
    print(lic.banner())
    if not lic_status["licensed"] and args.backend == "ollama":
        before_q, before_v = len(questions), len(variant_names)
        questions = [q for q in questions if q["id"] in lic.TRIAL_QUESTIONS]
        variant_names = [v for v in variant_names if v in lic.TRIAL_VARIANTS]
        if len(questions) < before_q or len(variant_names) < before_v:
            print(f"Trial mode: limited to questions {', '.join(lic.TRIAL_QUESTIONS)} and the {', '.join(lic.TRIAL_VARIANTS)} style "
                  f"({len(questions)} questions x {len(variant_names)} style). Activate to unlock all 42 questions and 8 styles.")
    instances = expand_questions(questions, args.paraphrases)
    if not instances:
        ap.error("no questions selected")

    if args.dry_run:
        q = instances[0]
        for v in variant_names:
            print(f"===== variant: {v} =====")
            for m in build_messages(prompts["variants"][v], prompts, data["document"], q["question"]):
                print(f"--- {m['role']} ---\n{m['content']}\n")
        return 0

    client: Optional[OllamaClient] = None
    ollama_version = None
    if args.backend == "ollama":
        client = OllamaClient(args.host, timeout=args.timeout)
        if args.list_models:
            try:
                for m in client.list_models():
                    print(m)
            except OllamaError as e:
                print(e)
                return 1
            return 0
        ollama_version = client.version()
        if ollama_version is None:
            print(f"Could not reach Ollama at {args.host}. Is `ollama serve` running? (Use --backend mock to test without it.)")
            return 1
        models = args.models or DEFAULT_MODELS
        try:
            installed = set(client.list_models())
            missing = [m for m in models if m not in installed and m.split(":")[0] not in {i.split(":")[0] for i in installed}]
            if missing:
                print(f"Warning: not found in `ollama list`: {missing}. Pull them first (ollama pull <model>) or they will error.")
        except OllamaError as e:
            print(f"Warning: could not list models: {e}")
    else:
        models = args.models or MOCK_MODELS

    out_dir = args.out or os.path.join("results", dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, "results.jsonl")
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

    done = set()
    if args.resume and os.path.exists(jsonl_path):
        for r in load_jsonl([jsonl_path]):
            done.add((r["model"], r["variant"], r["question_id"], r.get("phrasing", 0), r.get("repeat", 0)))
        print(f"Resuming: {len(done)} rows already present.")
    elif os.path.exists(jsonl_path) and os.path.getsize(jsonl_path) > 0:
        print(f"{jsonl_path} already exists; use --resume to continue it or choose another --out folder.")
        return 1

    config = {k: v for k, v in vars(args).items()}
    config.update({"run_id": run_id, "models": models, "variants": variant_names,
                   "n_question_instances": len(instances), "document_sha256": data["document_sha256"],
                   "ollama_version": ollama_version, "started_at": dt.datetime.now().isoformat(timespec="seconds")})
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)

    total = len(models) * len(variant_names) * len(instances) * args.repeats
    print(f"Run {run_id}: {len(models)} model(s) x {len(variant_names)} variant(s) x {len(instances)} question(s) "
          f"x {args.repeats} repeat(s) = {total} calls -> {out_dir}")

    n_done = 0
    t_start = time.time()
    with open(jsonl_path, "a", encoding="utf-8") as fout:
        for model in models:
            if client is not None:  # warm-up so model load time is not charged to the first question
                try:
                    client.chat(model, [{"role": "user", "content": "Say OK."}], num_predict=5, temperature=0.0)
                except OllamaError as e:
                    print(f"[{model}] warm-up failed: {e}")
            for vname in variant_names:
                variant = prompts["variants"][vname]
                for q in instances:
                    for rep in range(args.repeats):
                        key = (model, vname, q["id"], q["phrasing"], rep)
                        if key in done:
                            continue
                        messages = build_messages(variant, prompts, data["document"], q["question"])
                        seed = args.seed + (rep if args.temperature > 0 else 0)
                        error = None
                        resp: Dict[str, Any] = {}
                        try:
                            if client is None:
                                resp = mock_chat(model, vname, q, rep, args.temperature)
                            else:
                                resp = client.chat(model, messages, temperature=args.temperature, seed=seed,
                                                   num_predict=args.num_predict, num_ctx=args.num_ctx,
                                                   think=(None if args.think is None else args.think == "on"))
                        except OllamaError as e:
                            error = str(e)
                        raw = resp.get("content", "")
                        if resp.get("thinking") and "<think>" not in raw:
                            raw = f"<think>{resp['thinking']}</think>\n{raw}"
                        scored = score_response(q, raw, error=error)

                        judge_verdict = None
                        if args.judge_model and client is not None and not error:
                            reference = q["expected_response"]
                            jm = [{"role": "user", "content": JUDGE_PROMPT.format(
                                question=q["question"], reference=reference, candidate=scored["final_answer"] or raw)}]
                            try:
                                jr = client.chat(args.judge_model, jm, temperature=0.0, num_predict=5)
                                jtxt = jr["content"].strip().upper()
                                judge_verdict = "CORRECT" if jtxt.startswith("CORRECT") else ("INCORRECT" if "INCORRECT" in jtxt else "UNPARSED:" + jtxt[:20])
                            except OllamaError as e:
                                judge_verdict = "ERROR:" + str(e)[:60]

                        row: Dict[str, Any] = {
                            "run_id": run_id,
                            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                            "backend": args.backend,
                            "model": model,
                            "variant": vname,
                            "question_id": q["id"],
                            "phrasing": q["phrasing"],
                            "category": q["category"],
                            "position": q.get("position"),
                            "difficulty": q.get("difficulty"),
                            "repeat": rep,
                            "temperature": args.temperature,
                            "seed": seed,
                            "question": q["question"],
                            "expected_response": q["expected_response"],
                            "messages": messages,
                            "raw_response": raw,
                            "prompt_tokens": resp.get("prompt_tokens"),
                            "completion_tokens": resp.get("completion_tokens"),
                            "latency_s": resp.get("latency_s"),
                            "tokens_per_s": resp.get("tokens_per_s"),
                            "load_s": resp.get("load_s"),
                            "done_reason": resp.get("done_reason"),
                            "error": error,
                            "judge_verdict": judge_verdict,
                        }
                        row.update(scored)
                        fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                        fout.flush()
                        n_done += 1
                        mark = "ERR" if error else ("ok " if scored["correct"] else "X  ")
                        elapsed = time.time() - t_start
                        print(f"[{n_done + len(done):4d}/{total}] {mark} {model:<18} {vname:<16} {q['id']}"
                              f"{'p' + str(q['phrasing']) if q['phrasing'] else '  '} r{rep} "
                              f"{(resp.get('latency_s') or 0):5.1f}s  {scored['failure_mode'] or ''}"
                              f"  ({elapsed:.0f}s elapsed)")

    print(f"Done: {n_done} new calls in {time.time() - t_start:.0f}s. Raw results: {jsonl_path}")
    if args.no_report:
        return 0
    rows = load_jsonl([jsonl_path])
    meta = {
        "title": "Grocery-Store Reading Comprehension Benchmark" + ("" if lic_status["licensed"] else " (TRIAL MODE - unlicensed copy)"),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "document": data["document_name"], "document_sha256": data["document_sha256"],
        "backend": args.backend, "ollama_version": ollama_version, "run_id": run_id,
        "config": {k: config[k] for k in ("models", "variants", "repeats", "temperature", "seed",
                                           "num_predict", "paraphrases", "judge_model")},
    }
    write_report(rows, out_dir, meta, n_examples=args.examples, charts=not args.no_charts)
    print(f"Report: {os.path.join(out_dir, 'report.md')}  (plus results.csv, summary.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
