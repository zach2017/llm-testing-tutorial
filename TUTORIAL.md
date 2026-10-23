# Tutorial: testing a small language model on a grocery store, step by step

This is a hands-on walk-through for someone who has never evaluated a language model before.
By the end you will have run a small model on your own computer (CPU only, no GPU), asked it
questions about a fictional grocery store, seen exactly where it goes wrong, and produced a
report you can share.

Time needed: about 30 minutes, plus waiting time while the model answers.

---

## 1. The idea in one paragraph

A language model (LLM) is a program that continues text. If you give it a passage and a question,
it writes an answer. Small models (1–3 billion parameters) can run on an ordinary laptop, but they
make mistakes: they misread numbers, confuse similar names, invent facts that are not in the text,
agree with false claims in the question, and ignore formatting instructions. To study *how* a model
fails you need (a) a text whose facts you control, (b) questions with known answers, each designed
to trigger one kind of mistake, (c) a way to score the answers automatically, and (d) statistics
so you can tell a real difference from noise. That is what this kit is.

## 2. Install the pieces (10 minutes)

You need two things: **Python** (runs the scripts) and **Ollama** (runs the model). Everything is CPU-only.

| | Windows | macOS | Linux |
|---|---|---|---|
| Python 3.9+ | https://www.python.org/downloads/ — tick **"Add python.exe to PATH"** | `brew install python` or python.org | usually installed; else `sudo apt install python3` |
| Ollama | https://ollama.com/download/windows (installer) | https://ollama.com/download/mac (or `brew install ollama`) | `curl -fsSL https://ollama.com/install.sh \| sh` |

Then check everything with the script for your system (run it from inside the `grocery-llm-eval` folder):

```
Windows:      check_tools.bat          (double-click works too)
macOS/Linux:  bash check_tools.sh
```

Every line shows `[OK]`, `[WARN]` or `[MISSING]` with the exact command to fix it. The most common
"missing" items are the Ollama server not running (start the Ollama app, or run `ollama serve` in a
second terminal window and leave it open) and the model not downloaded yet:

```
ollama pull deepseek-r1:1.5b
```

That downloads about 1.1 GB once. If you prefer to be walked through everything interactively, run
the wizard instead — it checks the same things, downloads the model, does a first chat, and runs a
3-question mini benchmark for you:

```
Windows:      setup_wizard.bat
macOS/Linux:  bash setup_wizard.sh
```

**About the model.** `deepseek-r1:1.5b` is a "thinking" model: before answering it writes out its
reasoning (Ollama returns it separately, or inside `<think>…</think>` tags). That makes it a nice
model to study because you can read *why* it answered the way it did. It also means each answer
takes longer (20–90 seconds on a CPU) and needs a generous token budget, which is why every command
below uses `--num-predict 1500`. If you only want quick answers, add `--think off` (Ollama 0.9+), or
try a non-thinking model such as `gemma3:1b` or `llama3.2:1b`.

**What "CPU only" means in practice.** Expect roughly 5–20 words per second from a 1.5B model.
Nothing needs configuring: Ollama uses the GPU if it finds one and the CPU otherwise. Close
memory-hungry programs if you have less than 8 GB of RAM.

## 3. Meet the store (2 minutes)

Open `data/grocery_store.txt`. It is five short paragraphs about **Maple Street Market**: who
founded it and who owns it now, opening hours, prices, promotions, delivery rules, returns policy.
It is fictional, so the model cannot know any of it from training — everything it says has to come
from the text (or be made up).

The text contains deliberate traps. Some examples:

* The founder is **Helen Park**, the current owner is **Daniel Park**, the manager is **Rosa Delgado**. Small models mix these up.
* Two bakery times: loaves arrive at **6:00 AM**, the counter **closes at 4:00 PM**.
* The pharmacy opened in **2005** and **closed in 2023** — so any question about the pharmacy's hours has a false premise.
* Delivery costs **$4.00** but is free from **$50.00** — a threshold rule that needs a comparison.
* The store does **not** sell alcohol or tobacco — a negation.
* There is an email address but **no phone number** — a question about the phone number is unanswerable.

## 4. Ask your first questions by hand (5 minutes)

`ask.py` sends one question to the model, shows the answer, and scores it if the question is one
of the 42 in the benchmark. Start with the easiest fact:

```
python ask.py "Who founded Maple Street Market?"
```

You will see something like:

```
Model: deepseek-r1:1.5b   Variant: baseline   Temperature: 0.0
Question: Who founded Maple Street Market?
Expected (factual): Helen Park

=== Response ===  (31.4s, 212 tokens, 7.1 tok/s)
[the model thought for 150 words before answering; add --show-thinking to read it]
The store was founded by Helen Park.
--> Score: CORRECT   (matched 'Helen Park')
```

Now try the kinds of questions that trip small models up, and watch what happens:

```
python ask.py "Who currently owns the store?"                 # founder vs. current owner
python ask.py "What is the store's phone number?"             # not in the text - does it make one up?
python ask.py "Why does the store close at noon on Sundays?"  # false premise - does it push back?
python ask.py "A customer buys 3 cans of tomato soup. How much do they pay for the soup?"   # buy-2-get-1
python ask.py "Answer with only a number and nothing else: how many self-checkout kiosks does the store have?"
```

Useful flags while exploring:

* `--show-thinking` prints the model's hidden reasoning. Read it when the answer is wrong — often the model *found* the right sentence and then mis-copied the number.
* `--show-prompt` prints exactly what was sent, so you can see how the text and question are packaged.
* `--variant strict_grounded` (or `cot`, `persona`, `few_shot` …) changes the instructions around the question. Ask the phone-number question with `--variant strict_grounded` and `--variant persona` and compare.
* `--temperature 0.8 --repeats 3` asks three times with randomness on. If the answers differ, the model is not confident — it is sampling.
* You can type any question, not only the 42; unknown questions are shown but not scored.
* `Q15` (an id from `data/questions.md`) works instead of typing the question.

Spend five minutes here. What you observe by hand is what the benchmark measures at scale.

## 5. How a question gets scored

Look at one entry in `data/questions.json`:

```json
{
  "id": "Q20",
  "category": "arithmetic",
  "question": "A customer who lives 3 miles from the store orders $42.00 of groceries for delivery. What delivery fee do they pay?",
  "expected_response": "$4.00",
  "scoring": {"type": "numeric", "expected": 4.00, "wrong_aliases": ["free", "no fee"]},
  "plausible_wrong": "Delivery is free."
}
```

* `category` says what the question probes (factual, temporal, arithmetic, counting, comparison, negation, unanswerable, false_premise, instruction_following).
* `scoring` is a rule the computer applies to the answer. `numeric` looks for the number 4.00 anywhere in the final answer (a few cents' tolerance, number words like "four" accepted, clock times ignored). Other rule types: `contains` (a phrase or alias), `yes_no`, `choice` (which option was named first), `set` (list items, scored by F1), `exact` (one token only), `refusal` (did it say the text lacks the answer?), `premise_correction` (did it state the true fact or contradict the question?).
* `plausible_wrong` is a realistic wrong answer. `python run_eval.py --self-test` checks that every expected answer scores correct and every plausible wrong one scores incorrect, so you can edit questions safely.

Every wrong answer gets a **failure-mode label**: `wrong_value`, `wrong_entity`, `hallucination`
(answered an unanswerable question), `over_refusal` (said "not stated" when it was), `premise_accepted`,
`format_violation` (right content, wrong format), `partial`, `no_answer`, `error`. Counting labels,
not just errors, is what tells you *how* the model goes wrong.

For a thinking model only the text after the `<think>` block is scored; for the `cot` prompt only the
line after `FINAL ANSWER:` is scored. The reasoning is kept in the raw results so you can read it.

## 6. Prompt variants: same question, different wrapping

Open `data/prompts.json`. Each variant is a template with `{context}` (the store text) and
`{question}`. The benchmark asks every question under every variant, because small models are very
sensitive to wording:

| Variant | What it does | Watch for |
|---|---|---|
| `baseline` | text + question, no instructions | the reference point |
| `strict_grounded` | "use only the text; say *Not stated in the text.* if absent" | fewer hallucinations, but more over-refusals? |
| `cot` | "quote the evidence, reason step by step, end with FINAL ANSWER:" | does reasoning help arithmetic? does it obey the marker? |
| `few_shot` | two worked examples first | shorter, better-grounded answers? |
| `persona` | "You are Maple, a cheerful assistant…" | does eagerness to please increase made-up answers? |
| `question_first` | question placed before the text | order sensitivity |
| `distractor` | a second store with conflicting numbers is appended | does it mix the stores up? |
| `no_context` | question only, no text (control) | a "correct" answer here is a guess |

Try one question under three variants by hand before running everything:

```
python ask.py Q31 --variant baseline
python ask.py Q31 --variant strict_grounded
python ask.py Q31 --variant persona
```

## 7. Run the benchmark

Start small so you know the timing on your machine (5 questions, 1 variant, a few minutes):

```
python run_eval.py --models deepseek-r1:1.5b --variants baseline --limit 5 --num-predict 1500 --out results/try1
```

Each line printed is one call: `ok`/`X`, model, variant, question id, seconds, failure mode. When
it finishes, open `results/try1/report.md`.

A sensible first real run is two variants (84 calls, roughly 30–90 minutes on a CPU for a thinking model):

```
python run_eval.py --models deepseek-r1:1.5b --variants baseline strict_grounded --num-predict 1500 --out results/first_run
```

The full matrix is all 8 variants (336 calls per model). You can stop any run with Ctrl+C and
continue later with `--resume`; every answer is saved as soon as it arrives.

Optional studies:

* **Consistency:** `--repeats 3 --temperature 0.7` asks every question three times with sampling on; the report shows how often the answer (and its correctness) flips.
* **Phrasing sensitivity:** `--paraphrases` adds reworded versions of 9 questions.
* **Second opinion on the scorer:** `--judge-model llama3.2:3b` (or any larger model you have) asks another model to grade each answer; the report shows how often judge and rules agree.
* **Compare models:** pull another one (`ollama pull gemma3:1b`) and list both after `--models`. Or run them on different days and merge: `python make_report.py --inputs results/a/results.jsonl results/b/results.jsonl --out results/combined`.

## 8. Reading the report

`report.md` is written for sharing with other researchers. Section by section:

1. **Headline table** — accuracy with a 95% confidence interval (with 42 questions one variant, the interval is wide — about ±15 points — which is why the full matrix and repeats matter), plus hallucination rate, over-refusal rate, premise-acceptance rate, format compliance, repeat consistency, median latency, tokens/second and words per answer.
2. **By category** — where the model is weak. Small models typically do well on `factual`, worse on `arithmetic` and `false_premise`.
3. **By prompt variant** — Δ against `baseline`. The interesting pattern is a trade-off: `strict_grounded` usually cuts hallucination *and* raises over-refusal. Look at both columns.
4. **Position and difficulty** — is the model worse on facts from the middle of the text?
5. **Control** — without the text, how often does it "guess" right? Should be near zero, with high abstention.
6. **Pairwise comparison** — for two or more models: difference in accuracy with a bootstrap confidence interval and a sign-test p-value. If the interval includes 0, you have not shown a difference.
7. **Failure-mode counts** — the "how it goes wrong" table.
8. **Process metrics** — did `cot` actually produce a `FINAL ANSWER:` line? Do wrong answers come with longer or shorter reasoning?
9. **Hardest questions** and **10. example failures** — real answers to quote.
11. **Methodology** — paste into a paper or share as-is.

Alongside it: `results.csv` (one row per call, opens in Excel), `summary.json` (every number in
the report), `results.jsonl` (full prompt and raw response for every call, including the thinking),
and `charts/` if matplotlib is installed.

## 9. A short experiment to try

1. Run `baseline` and `strict_grounded` on `deepseek-r1:1.5b`.
2. In section 3 of the report, note hallucination going down and over-refusal going up under `strict_grounded`.
3. In section 10, find a `premise_accepted` example and re-ask it with `python ask.py Qxx --variant cot --show-thinking`. Did the reasoning notice the false premise?
4. Pull `gemma3:1b`, run the same two variants, merge with `make_report.py`, and check section 6: is the difference between the models larger than its confidence interval?

Write down what you expected before each step; the surprises are the findings.

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not reach Ollama` | Start the Ollama app or `ollama serve`; check `http://localhost:11434` opens in a browser ("Ollama is running"). |
| `model not found` | `ollama pull deepseek-r1:1.5b`; `ollama list` shows what you have. |
| Answers cut off / `done_reason: length` | Raise `--num-predict` (2500), or `--think off`. |
| Very slow | Normal on CPU for a thinking model. Use `--limit`, fewer `--variants`, `--think off`, or a non-thinking 1B model. Make sure only one model is loaded (`ollama ps`). |
| Scorer marks a right answer wrong | Read `scoring_detail` in the CSV; add an alias in `questions.json`; run `--self-test`. Use `--judge-model` as a cross-check. |
| `python` not recognised (Windows) | Reinstall Python with "Add python.exe to PATH", or use `py -3` instead of `python`. |
