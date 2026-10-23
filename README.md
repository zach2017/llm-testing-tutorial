# Grocery-Store LLM Evaluation Kit

A small, self-contained benchmark for probing **how small local language models go wrong** on a
reading-comprehension task. A model reads a ~430-word description of a fictional grocery store
("Maple Street Market") and answers 42 questions that are each designed to expose a specific
failure mode. The same questions are asked under 8 prompt variants so you can see how the prompt
changes both the answer and the model's process. Results are scored automatically, summarised
with confidence intervals and significance tests, and written up as a Markdown report that can be
shared with other researchers together with the raw data.

Built for [Ollama](https://ollama.com) models (e.g. `llama3.2:1b`, `gemma3:1b`, `qwen3:1.7b`), but
the runner only uses Ollama's HTTP API, so any server that speaks it works. Pure Python 3.9+,
no dependencies (matplotlib is optional, for charts).

## Web pages and API server

```
web/index.html   step-by-step tutorial with a simulated model (no install needed; open the file or serve it)
web/lab.html     Live Lab: connects to your local Ollama, settings in localStorage, prerequisite checks,
                 runs questions, shows thinking + score, exports Markdown / CSV / JSON / print-to-PDF
server/          optional Go API server: serves the pages, proxies Ollama, saves runs, exports MD/HTML/PDF/CSV
```

Quickest path: `cd server && go run .` then open http://localhost:8080. Without Go, just open
`web/index.html` in a browser (the lab talks to Ollama directly; see its setup guide if the browser blocks it).
Pages use Tailwind CSS from a CDN and the IBM Plex font, so they need internet for styling, but
all model traffic stays on your machine. After editing `data/*.json`, run `python3 web/build_data.py`.

## New here? Start with the helpers

```
check_tools.bat / bash check_tools.sh     verify Python, Ollama, the server, the model and the project files
setup_wizard.bat / bash setup_wizard.sh   guided CPU-only setup with deepseek-r1:1.5b, ending in a 3-question mini run
python ask.py "Who founded the store?"    ask one question, see the answer (and the model's thinking), get it scored
TUTORIAL.md                               step-by-step guide to testing a model on the grocery store
```

Thinking models such as `deepseek-r1:1.5b` need a larger token budget: add `--num-predict 1500`
(or `--think off`) to `run_eval.py` commands.

## Quick start

```bash
# 1. Prove the scorer is sound (no Ollama needed)
python run_eval.py --self-test

# 2. Exercise the whole pipeline with fake models (no Ollama needed); open example_output/ afterwards
python run_eval.py --backend mock --out example_output/smoke

# 3. Real run. Make sure `ollama serve` is running and the models are pulled:
ollama pull llama3.2:1b && ollama pull llama3.2:3b && ollama pull gemma3:1b
python run_eval.py --models llama3.2:1b llama3.2:3b gemma3:1b --out results/run1
#    -> results/run1/report.md, results.csv, summary.json, results.jsonl, charts/
```

A full run is `models × 8 variants × 42 questions` calls (336 per model). Small models answer in
0.5–3 s each on a laptop, so budget roughly 5–15 minutes per model. Use `--variants baseline cot`
or `--limit 10` for a quicker look, and `--resume` to continue an interrupted run.

## What is in the box

| Path | Purpose |
|---|---|
| `data/grocery_store.txt` | The source document (5 paragraphs; facts, prices, hours, policies). |
| `data/questions.json` | 42 questions with expected responses, scoring rules, category, evidence position, difficulty, the failure mode each probes, a realistic wrong answer, and paraphrases for 9 of them. **Source of truth.** |
| `data/questions.md` | The same questions as a readable table. |
| `data/prompts.json` | 8 prompt variants (templates) + few-shot examples + distractor paragraph. |
| `run_eval.py` | Runs models, scores answers, writes everything. |
| `make_report.py` | Rebuilds / merges reports from one or more `results.jsonl` files. |
| `ask.py` | Asks one question interactively and scores it; the teaching tool. |
| `check_tools.bat`, `check_tools.sh` | Verify the installation (Windows / macOS+Linux). |
| `setup_wizard.py` (+ `.bat`/`.sh` launchers) | Interactive CPU-only setup through to a first mini benchmark. |
| `TUTORIAL.md` | Beginner's walk-through (text version). |
| `web/` | Tutorial page, Live Lab page, shared JS (scorer port, data bundle). |
| `server/` | Go API server (see `server/README.md`). |
| `grocery_eval/scoring.py` | Heuristic scorer and failure-mode taxonomy. |
| `grocery_eval/stats.py` | Wilson intervals, paired bootstrap, exact sign test. |
| `grocery_eval/report.py` | Aggregation and Markdown / CSV / JSON / chart writers. |
| `grocery_eval/ollama_client.py` | Minimal Ollama API client. |
| `grocery_eval/mock_backend.py` | Deterministic fake models for pipeline testing. |
| `example_output/demo_run/` | A complete sample output produced with the mock models. |

## Question categories (what each one probes)

| Category | n | Probe |
|---|---|---|
| factual | 9 | Direct lookup; several have a confusable neighbour (founder vs. current owner, 2005 vs. 2023). |
| temporal | 5 | Opening-hours reasoning; Q10/Q11 are a matched pair (8 PM Saturday = open, 8 PM Sunday = closed). |
| arithmetic | 8 | Multiplication, sums, a 20% discount, a 5% loyalty discount, buy-two-get-one-free, a delivery threshold (matched pair Q20/Q21), and a two-year subtraction that needs two sentences. |
| counting | 2 | A stated count and a count that must be summed (4 lanes + 2 kiosks). |
| comparison | 3 | Which of two prices is higher; a ratio. |
| negation | 3 | "does NOT sell", an exception clause, a negated multiple choice. |
| unanswerable | 5 | Information that is absent. Correct = abstain. Measures **hallucination**. |
| false_premise | 4 | The question embeds a false claim. Correct = correct the claim. Measures **premise acceptance / sycophancy**. |
| instruction_following | 3 | "Only a number", "exactly one word", "comma-separated, no other words". Measures **format compliance**. |

Each question is also tagged with the **position** of its evidence (start / middle / end of the
document) to look for "lost in the middle" effects, and a **difficulty** of 1–3.

## Prompt variants (how the same question is asked)

| Variant | What changes | What it tests |
|---|---|---|
| `baseline` | Text, then question, no instructions. | Reference condition. |
| `strict_grounded` | System prompt: use only the text, say "Not stated in the text." if absent. | Hallucination vs. over-refusal trade-off. |
| `cot` | Quote evidence, reason step by step, end with `FINAL ANSWER:`. | Does reasoning help? Also captures the model's process. |
| `few_shot` | Two worked examples (one factual, one "not stated"). | Do demonstrations improve grounding and brevity? |
| `persona` | Cheerful customer-service assistant; document in the system prompt. | Does eagerness to please raise hallucination / premise acceptance? |
| `question_first` | Question placed before the text. | Prompt-order sensitivity. |
| `distractor` | A paragraph about a different store with conflicting numbers is appended. | Entity confusion / context interference. |
| `no_context` | Question only, no document. **Control.** | Guess rate; the desirable behaviour is to abstain. Excluded from headline accuracy. |

Additional knobs: `--repeats N --temperature 0.7` measures answer **consistency** across samples;
`--paraphrases` asks reworded versions of 9 questions to measure **phrasing sensitivity**;
`--judge-model <bigger model>` adds an LLM judge as a second opinion on the heuristic scorer.

## Scoring and failure modes

Scoring is deterministic string matching (see `grocery_eval/scoring.py`), so results are
reproducible and free. Every incorrect answer gets one label:

`wrong_value` · `wrong_entity` · `partial` · `no_answer` · `hallucination` · `over_refusal` ·
`premise_accepted` · `format_violation` · `error`

If a response contains a `FINAL ANSWER:` line only that line is scored; `<think>…</think>` blocks
from reasoning models are stripped (and kept in the raw data). `python run_eval.py --self-test`
checks that every reference answer scores correct and every `plausible_wrong` answer scores
incorrect, so you can edit the questions and know the scorer still agrees with you.

Known limitations are listed in the report's methodology section. For free-form answers, run with
`--judge-model` and compare the heuristic and judge columns.

## Report contents

`report.md` has: headline table (accuracy with 95% Wilson CI, hallucination, over-refusal, premise
acceptance, format compliance, repeat consistency, latency, tokens/s, verbosity); accuracy by
category, by prompt variant (with Δ vs. baseline and refusal rate), by evidence position and
difficulty; the no-context control; pairwise model comparisons (paired bootstrap CI + exact sign
test); failure-mode counts; process metrics (CoT adherence, reasoning length vs. correctness,
paraphrase consistency); hardest questions; example failures; methodology. `summary.json` holds
every number in the report; `results.csv` is one row per call; `results.jsonl` additionally has
the full prompt and raw response for every call.

To compare runs made on different days or machines:

```bash
python make_report.py --inputs results/run1/results.jsonl results/run2/results.jsonl --out results/combined
```

## Extending it

* **Add questions**: append to `data/questions.json` (keep `expected_response` and
  `plausible_wrong` in sync with the scoring rule) and run `--self-test`.
* **Add prompt variants**: add an entry to `data/prompts.json`; the placeholders are
  `{context}`, `{question}`, `{few_shot}`.
* **Swap the document**: replace `grocery_store.txt` and rewrite the questions; nothing in the
  code depends on the grocery theme.
* **Other servers**: `--host http://other-machine:11434`, or any server implementing Ollama's
  `/api/chat`.

## Useful flags

```
--models M [M ...]        Ollama tags to test (default llama3.2:1b llama3.2:3b gemma3:1b)
--variants V [V ...]      subset of prompt variants
--questions Q01 Q15 ...   subset of questions          --categories arithmetic negation
--limit N                 first N questions            --paraphrases   include reworded questions
--repeats N               ask each question N times    --temperature T (0 = deterministic)
--num-predict N           max answer tokens (400)      --think on|off  for thinking-capable models
--judge-model M           LLM judge second opinion     --resume        continue a partial run
--list-models             show what Ollama has         --dry-run       print the rendered prompts
--self-test               validate the scorer          --backend mock  fake models, no Ollama
```
