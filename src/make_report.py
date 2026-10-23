#!/usr/bin/env python3
"""(Re)build the report from one or more results.jsonl files.

Use this to merge runs made at different times or on different machines into a single
model comparison, or to regenerate a report after editing report.py.

  python make_report.py --inputs results/run1/results.jsonl results/run2/results.jsonl --out results/combined
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grocery_eval.report import load_jsonl, write_report  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", nargs="+", required=True, help="one or more results.jsonl files")
    ap.add_argument("--out", required=True, help="output folder for report.md, results.csv, summary.json")
    ap.add_argument("--title", default="Grocery-Store Reading Comprehension Benchmark")
    ap.add_argument("--examples", type=int, default=5)
    ap.add_argument("--baseline", default="baseline", help="variant that Δ values are measured against")
    ap.add_argument("--no-charts", action="store_true")
    ap.add_argument("--document", default=os.path.join(HERE, "data", "grocery_store.txt"))
    args = ap.parse_args()

    rows = load_jsonl(args.inputs)
    if not rows:
        print("No rows found.")
        return 1
    sha = "?"
    if os.path.exists(args.document):
        with open(args.document, "rb") as f:
            sha = hashlib.sha256(f.read().strip()).hexdigest()
    backends = sorted({r.get("backend") for r in rows})
    meta = {
        "title": args.title,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "document": os.path.basename(args.document), "document_sha256": sha,
        "backend": ", ".join(str(b) for b in backends),
        "ollama_version": None,
        "inputs": args.inputs,
        "run_ids": sorted({r.get("run_id") for r in rows}),
    }
    summary = write_report(rows, args.out, meta, n_examples=args.examples, charts=not args.no_charts,
                           baseline_variant=args.baseline)
    print(f"Wrote {os.path.join(args.out, 'report.md')} covering {summary['n_rows']} rows and {len(summary['models'])} model(s).")
    for m in summary["models"]:
        h = summary["headline"][m]
        print(f"  {m:<20} accuracy {100 * (h['accuracy'] or 0):5.1f}%  hallucination {100 * (h['hallucination_rate'] or 0):5.1f}%"
              f"  over-refusal {100 * (h['over_refusal_rate'] or 0):5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
