#!/usr/bin/env python3
"""Build the customer download: dist/grocery-llm-eval-<version>.zip

    python make_release.py --version 1.0.0 [--with-binaries] [--allow-demo-key]

Excludes private keys, the demo key, the key ledger, results, caches and the sales page.
Refuses to build while the DEMO public key is still configured (unless --allow-demo-key, for testing).
Runs the scorer self-test first.
"""
import argparse
import datetime as dt
import fnmatch
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_PUBLIC_KEY = "cdfee672299ee1b13ea0718511fdeb50aaf06d07daba24fecc44c6d75c080a01"
EXCLUDE = [
    "license/seller_private.key", "license/demo_private.key", "license/issued_keys.jsonl", "license/activations.jsonl",
    "license/revoked.txt", "license/*.key", "docs/DEMO_LICENSE_KEY.txt", "docs/GO_TO_MARKET.md", "web/buy.html",
    "license.key", "results/*", "server/data/*", "dist/*", "*/__pycache__/*", "*.pyc", ".git/*", ".gitignore",
    "make_release.py", "*.DS_Store", "node_modules/*",
]


def excluded(rel: str) -> bool:
    rel = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel, p) for p in EXCLUDE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--with-binaries", action="store_true", help="include dist/bin/* server binaries")
    ap.add_argument("--allow-demo-key", action="store_true")
    a = ap.parse_args()

    # 1. safety: no demo key in a real release
    pub_files = ["license/main.go", "server/license.go", "grocery_eval/license.py", "web/license.js"]
    uses_demo = [f for f in pub_files if DEMO_PUBLIC_KEY in open(os.path.join(HERE, f), encoding="utf-8").read()]
    if uses_demo and not a.allow_demo_key:
        print("Refusing to build: the DEMO public key is still configured in", ", ".join(uses_demo))
        print("Run `licensetool keygen`, paste the new public key into those files, then rebuild (see docs/GO_TO_MARKET.md step 3).")
        return 1
    # 2. self-test
    if subprocess.run([sys.executable, os.path.join(HERE, "run_eval.py"), "--self-test"], capture_output=True).returncode != 0:
        print("Self-test failed; fix the scorer/questions before releasing.")
        return 1
    # 3. zip
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    out = os.path.join(HERE, "dist", f"grocery-llm-eval-{a.version}.zip")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(HERE):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", "dist", "results")]
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, HERE)
                if excluded(rel):
                    continue
                z.write(full, os.path.join("grocery-llm-eval", rel))
                n += 1
        z.writestr("grocery-llm-eval/VERSION", f"{a.version}\nbuilt {dt.date.today().isoformat()}\n")
        if a.with_binaries:
            bin_dir = os.path.join(HERE, "dist", "bin")
            for f in os.listdir(bin_dir) if os.path.isdir(bin_dir) else []:
                z.write(os.path.join(bin_dir, f), os.path.join("grocery-llm-eval", "bin", f))
                n += 1
    print(f"Wrote {out} ({n} files, {os.path.getsize(out) // 1024} KB){' - DEMO KEY BUILD, not for sale' if uses_demo else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
