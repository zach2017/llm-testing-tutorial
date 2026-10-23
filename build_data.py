#!/usr/bin/env python3
"""Regenerate web/data.js from data/questions.json, data/prompts.json and data/grocery_store.txt."""
import json, os
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
q = json.load(open(os.path.join(root, "data/questions.json"), encoding="utf-8"))
p = json.load(open(os.path.join(root, "data/prompts.json"), encoding="utf-8"))
doc = open(os.path.join(root, "data/grocery_store.txt"), encoding="utf-8").read().strip()
js = "/* data.js - generated from data/*.json by tools; do not edit by hand (regenerate with: python3 web/build_data.py) */\n"
js += "window.GROCERY_DATA = " + json.dumps({"document": doc, "questions": q["questions"], "categories": q["categories"], "prompts": p}, indent=1, ensure_ascii=False) + ";\n"
open(os.path.join(here, "data.js"), "w", encoding="utf-8").write(js)
print("wrote web/data.js")
