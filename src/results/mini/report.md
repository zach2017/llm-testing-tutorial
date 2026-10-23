# Grocery-Store Reading Comprehension Benchmark

Generated 2026-10-23T16:02:25  
Document: `grocery_store.txt` (sha256 `0d304fededf1`)  
Backend: ollama; Ollama version: 0.34.0  
Rows: 3 calls (0 errors); repeats: 1; temperature(s): 0.0  
Models: deepseek-r1:1.5b  
Prompt variants: baseline

## 1. Headline results

Accuracy excludes the `no_context` control condition (see section 5). CI = 95% Wilson interval. Hallucination = answered an unanswerable question; over-refusal = declined an answerable one; premise acceptance = went along with a false premise.

| Model | n | Accuracy | 95% CI | Mean score | Hallucination | Over-refusal | Premise accept. | Format OK | Repeat consist. | Median latency | tok/s | Words/answer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **deepseek-r1:1.5b** | 3 | 66.7% | 20.8%–93.9% | 0.667 | 0.0% | 0.0% | 100.0% | n/a | n/a | 4.25s | 73 | 22 |

## 2. Accuracy by question category

| Category | deepseek-r1:1.5b |
|---|---|
| factual | 100.0% (1/1) |
| false_premise | 0.0% (0/1) |
| unanswerable | 100.0% (1/1) |

## 3. Effect of prompt variant

Δ is the change in accuracy relative to the `baseline` variant for the same model. Refusal rate counts answers that said the information was unavailable (desirable only for unanswerable questions).

| Variant | deepseek-r1:1.5b acc (Δ) | deepseek-r1:1.5b refusal |
|---|---|---|
| baseline | 66.7% | 33.3% |

## 4. Evidence position and difficulty

Position = where the supporting sentence sits in the document (probe for 'lost in the middle' effects). Unanswerable questions have no position and are excluded here.

| Position | deepseek-r1:1.5b |
|---|---|
| start | 50.0% (1/2) |
| middle | n/a |
| end | n/a |

| Difficulty | deepseek-r1:1.5b |
|---|---|
| 1 | 100.0% (1/1) |
| 2 | 100.0% (1/1) |
| 3 | 0.0% (0/1) |

## 5. Control condition: question without the document (`no_context`)

_Not run._

## 6. Pairwise model comparison

_Only one model; nothing to compare._

## 7. Failure-mode taxonomy

Counts of incorrect answers by type (control condition excluded).

| Failure mode | Meaning | deepseek-r1:1.5b |
|---|---|---|
| premise_accepted | went along with a false premise instead of correcting it | 1 |

## 8. Process and consistency metrics

| Model | Repeat agreement | Flip rate | Paraphrase consist. | CoT marker adherence | CoT words (correct) | CoT words (wrong) | Words/answer (correct) | Words/answer (wrong) | Rows with <think> |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1:1.5b | n/a | n/a | n/a | n/a | n/a | n/a | 12 | 41 | 3 |

* Repeat agreement: share of repeated runs giving the modal answer (needs `--repeats > 1`); flip rate: share of question groups whose correctness changed between repeats.
* Paraphrase consistency: share of (question, variant) groups where the original and reworded question were scored the same (needs `--paraphrases`).
* CoT marker adherence: share of `cot` responses that actually produced a `FINAL ANSWER:` line.

## 9. Hardest questions (all models pooled)

| ID | Category | Question | Overall | deepseek-r1:1.5b |
|---|---|---|---|---|
| Q36 | false_premise | Why does the store close at noon on Sundays? | 0.0% | 0.0% |
| Q01 | factual | Who founded Maple Street Market? | 100.0% | 100.0% |
| Q31 | unanswerable | What is the store's phone number? | 100.0% | 100.0% |

## 10. Example failures (up to 5 per model, one per failure mode first)

### deepseek-r1:1.5b

| Q | Variant | Failure | Expected | Model answer (final) | Scorer note |
|---|---|---|---|---|---|
| Q36 | baseline | premise_accepted | It doesn't; the store closes at 6:00 PM on Sundays. | The store closes at noon on Sundays because of the holiday, but the manager closes it earlier for scheduling purposes.  ANSWER: The store closes at noon on Sun… | went along with the premise |

## 11. Methodology and reproducibility

* **Task.** Each model reads a ~430-word fictional grocery-store description and answers 42 questions tagged by category, evidence position and difficulty. Questions were authored so that every answerable item has one unambiguous answer in the text, five items are unanswerable, and four contain a false premise.
* **Prompt variants.** The same question is asked under several prompt templates (see `data/prompts.json`); `baseline` is the reference. `no_context` is a control that omits the document.
* **Scoring.** Deterministic string rules (`grocery_eval/scoring.py`): numeric match with ±0.01 tolerance (number words accepted, clock times ignored), case-insensitive phrase match with aliases, earliest yes/no signal, first-mentioned option for multiple choice, item-level F1 for lists, abstention regex for unanswerable items, and true-fact / contradiction markers for false premises. When a response contains a `FINAL ANSWER:` line only that line is scored; `<think>` blocks are stripped. A scorer self-test (`python run_eval.py --self-test`) confirms every reference answer scores correct and every `plausible_wrong` answer scores incorrect.
* **Known scorer limitations.** Free-form comparative answers ('bananas are cheaper than apples') can be mis-read by the first-mention rule; a model that states the right number alongside wrong ones is scored correct; refusal detection is pattern-based. Use `--judge-model` to add an LLM judge and compare the two columns, and inspect `results.jsonl` for raw responses.
* **Statistics.** Wilson 95% intervals for proportions; paired bootstrap over questions and an exact sign test for model-vs-model differences. With 42 questions × variants the per-category cells are small; treat category-level differences of a few points as noise.
* **Reproduce.** `python run_eval.py --models deepseek-r1:1.5b --variants baseline --repeats 1 --temperature 0.0` then `python make_report.py --inputs <run>/results.jsonl`.
* **Files.** `results.jsonl` (full prompts and raw responses), `results.csv` (flat table), `summary.json` (every number in this report), `charts/` (if matplotlib was available).
