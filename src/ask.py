#!/usr/bin/env python3
"""Ask the model ONE question about the grocery store and watch how it is prompted, answered and scored.

    python ask.py "Who founded Maple Street Market?"
    python ask.py "What is the store's phone number?" --variant strict_grounded
    python ask.py Q36 --variant cot --show-prompt          # a question id from data/questions.json
    python ask.py "Does the store sell beer?" --model gemma3:1b --temperature 0.8 --repeats 3

If the question matches one in questions.json (by id or exact text) it is also scored.
This is the teaching tool: run_eval.py does exactly this for every question and every prompt variant.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from grocery_eval import license as lic  # noqa: E402
from grocery_eval.ollama_client import OllamaClient, OllamaError  # noqa: E402
from grocery_eval.scoring import score_response  # noqa: E402
from run_eval import build_messages, load_data  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", help="question text, or a question id such as Q15")
    ap.add_argument("--model", default="deepseek-r1:1.5b")
    ap.add_argument("--variant", default="baseline", help="prompt variant from data/prompts.json")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--repeats", type=int, default=1, help="ask more than once to see how stable the answer is")
    ap.add_argument("--num-predict", type=int, default=1500, help="max tokens (thinking models need a lot)")
    ap.add_argument("--think", choices=["on", "off"], default=None, help="turn thinking on/off for models that support it")
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--show-prompt", action="store_true", help="print the full prompt that is sent")
    ap.add_argument("--show-thinking", action="store_true", help="print the model's hidden reasoning, if any")
    args = ap.parse_args()

    data = load_data("data")
    variants = data["prompts"]["variants"]
    if args.variant not in variants:
        print(f"Unknown variant '{args.variant}'. Choose from: {', '.join(variants)}")
        return 1

    q = next((x for x in data["questions"] if x["id"].lower() == args.question.lower()
              or x["question"].strip().lower() == args.question.strip().lower()), None)
    question_text = q["question"] if q else args.question
    st = lic.status()
    if not st["licensed"]:
        print("TRIAL MODE:", st["reason"])
        if (q and q["id"] not in lic.TRIAL_QUESTIONS) or args.variant not in lic.TRIAL_VARIANTS:
            print(f"Trial limits: questions {', '.join(lic.TRIAL_QUESTIONS)} and the {', '.join(lic.TRIAL_VARIANTS)} style. "
                  "Free-text questions are allowed. Activate with: python activate.py <KEY>")
            if q and q["id"] not in lic.TRIAL_QUESTIONS:
                return 1
            if args.variant not in lic.TRIAL_VARIANTS:
                return 1
    messages = build_messages(variants[args.variant], data["prompts"], data["document"], question_text)

    print(f"Model: {args.model}   Variant: {args.variant}   Temperature: {args.temperature}")
    print(f"Question: {question_text}")
    if q:
        print(f"Expected ({q['category']}): {q['expected_response']}")
    if args.show_prompt:
        for m in messages:
            print(f"\n--- {m['role'].upper()} MESSAGE ---\n{m['content']}")
    print()

    host = args.host if args.host.startswith("http") else "http://" + args.host
    client = OllamaClient(host, timeout=900)
    for i in range(args.repeats):
        try:
            r = client.chat(args.model, messages, temperature=args.temperature,
                            seed=42 + i if args.temperature > 0 else 42, num_predict=args.num_predict,
                            think=(None if args.think is None else args.think == "on"))
        except OllamaError as e:
            print("Ollama error:", e)
            print("Is `ollama serve` running and the model pulled? Try: bash check_tools.sh / check_tools.bat")
            return 1
        raw = r["content"]
        if r["thinking"] and "<think>" not in raw:
            raw = f"<think>{r['thinking']}</think>\n{raw}"
        s = score_response(q, raw) if q else None
        label = f"Attempt {i + 1}/{args.repeats}" if args.repeats > 1 else "Response"
        print(f"=== {label} ===  ({r['latency_s']:.1f}s, {r['completion_tokens']} tokens, "
              f"{(r['tokens_per_s'] or 0):.1f} tok/s{', cut off by --num-predict' if r['done_reason'] == 'length' else ''})")
        thinking = (s["thinking"] if s else "") or r["thinking"]
        if thinking:
            n = len(thinking.split())
            if args.show_thinking:
                print(f"[thinking, {n} words]\n{thinking.strip()}\n[/thinking]")
            else:
                print(f"[the model thought for {n} words before answering; add --show-thinking to read it]")
        visible = s["final_answer"] if s else raw
        if s and s["reasoning"]:
            print(f"[reasoning before FINAL ANSWER, {len(s['reasoning'].split())} words]")
        print(visible.strip() or "(empty answer)")
        if s:
            verdict = "CORRECT" if s["correct"] else f"INCORRECT - {s['failure_mode']}"
            print(f"--> Score: {verdict}   ({s['scoring_detail']})")
        print()
    if not q:
        print("(Not scored: this question is not in data/questions.json. Add it there to score it.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
