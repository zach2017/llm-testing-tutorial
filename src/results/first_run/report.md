# Grocery-Store Reading Comprehension Benchmark

Generated 2026-10-23T16:18:42  
Document: `grocery_store.txt` (sha256 `0d304fededf1`)  
Backend: ollama; Ollama version: 0.34.0  
Rows: 84 calls (0 errors); repeats: 1; temperature(s): 0.0  
Models: deepseek-r1:1.5b  
Prompt variants: baseline, strict_grounded

## 1. Headline results

Accuracy excludes the `no_context` control condition (see section 5). CI = 95% Wilson interval. Hallucination = answered an unanswerable question; over-refusal = declined an answerable one; premise acceptance = went along with a false premise.

| Model | n | Accuracy | 95% CI | Mean score | Hallucination | Over-refusal | Premise accept. | Format OK | Repeat consist. | Median latency | tok/s | Words/answer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **deepseek-r1:1.5b** | 84 | 61.9% | 51.2%–71.6% | 0.619 | 50.0% | 3.0% | 87.5% | 16.7% | n/a | 7.66s | 43 | 18 |

## 2. Accuracy by question category

| Category | deepseek-r1:1.5b |
|---|---|
| arithmetic | 75.0% (12/16) |
| comparison | 66.7% (4/6) |
| counting | 100.0% (4/4) |
| factual | 77.8% (14/18) |
| false_premise | 12.5% (1/8) |
| instruction_following | 0.0% (0/6) |
| negation | 66.7% (4/6) |
| temporal | 80.0% (8/10) |
| unanswerable | 50.0% (5/10) |

## 3. Effect of prompt variant

Δ is the change in accuracy relative to the `baseline` variant for the same model. Refusal rate counts answers that said the information was unavailable (desirable only for unanswerable questions).

| Variant | deepseek-r1:1.5b acc (Δ) | deepseek-r1:1.5b refusal |
|---|---|---|
| baseline | 66.7% | 11.9% |
| strict_grounded | 57.1% (-9.5) | 19.0% |

## 4. Evidence position and difficulty

Position = where the supporting sentence sits in the document (probe for 'lost in the middle' effects). Unanswerable questions have no position and are excluded here.

| Position | deepseek-r1:1.5b |
|---|---|
| start | 79.2% (19/24) |
| middle | 61.8% (21/34) |
| end | 43.8% (7/16) |

| Difficulty | deepseek-r1:1.5b |
|---|---|
| 1 | 71.4% (20/28) |
| 2 | 65.9% (29/44) |
| 3 | 25.0% (3/12) |

## 5. Control condition: question without the document (`no_context`)

_Not run._

## 6. Pairwise model comparison

_Only one model; nothing to compare._

## 7. Failure-mode taxonomy

Counts of incorrect answers by type (control condition excluded).

| Failure mode | Meaning | deepseek-r1:1.5b |
|---|---|---|
| wrong_value | a number was given, but the wrong one | 3 |
| wrong_entity | a name / option / yes-no was given, but the wrong one | 5 |
| no_answer | nothing scoreable in the response | 8 |
| hallucination | answered an unanswerable question with a specific claim | 4 |
| over_refusal | said the text lacked the answer when it was there | 2 |
| premise_accepted | went along with a false premise instead of correcting it | 7 |
| format_violation | right content, wrong output format | 3 |

## 8. Process and consistency metrics

| Model | Repeat agreement | Flip rate | Paraphrase consist. | CoT marker adherence | CoT words (correct) | CoT words (wrong) | Words/answer (correct) | Words/answer (wrong) | Rows with <think> |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1:1.5b | n/a | n/a | n/a | n/a | n/a | n/a | 20 | 14 | 84 |

* Repeat agreement: share of repeated runs giving the modal answer (needs `--repeats > 1`); flip rate: share of question groups whose correctness changed between repeats.
* Paraphrase consistency: share of (question, variant) groups where the original and reworded question were scored the same (needs `--paraphrases`).
* CoT marker adherence: share of `cot` responses that actually produced a `FINAL ANSWER:` line.

## 9. Hardest questions (all models pooled)

| ID | Category | Question | Overall | deepseek-r1:1.5b |
|---|---|---|---|---|
| Q05 | factual | How much does a gallon of whole milk cost? | 0.0% | 0.0% |
| Q20 | arithmetic | A customer who lives 3 miles from the store orders $42.00 of groceries for delivery. What… | 0.0% | 0.0% |
| Q33 | unanswerable | Who is the assistant manager? | 0.0% | 0.0% |
| Q34 | unanswerable | How many employees work in the deli department? | 0.0% | 0.0% |
| Q36 | false_premise | Why does the store close at noon on Sundays? | 0.0% | 0.0% |
| Q37 | false_premise | What discount does the store offer on wine on Fridays? | 0.0% | 0.0% |
| Q38 | false_premise | What are the pharmacy counter's opening hours? | 0.0% | 0.0% |
| Q40 | instruction_following | Answer with only a number and nothing else: how many self-checkout kiosks does the store … | 0.0% | 0.0% |

## 10. Example failures (up to 5 per model, one per failure mode first)

### deepseek-r1:1.5b

| Q | Variant | Failure | Expected | Model answer (final) | Scorer note |
|---|---|---|---|---|---|
| Q05 | baseline | wrong_value | $3.25 | The cost of a gallon of whole milk at Maple Street Market is $26.00.  ANSWER: $26.00 | numbers found [26.0] but not 3.25 |
| Q05 | strict_grounded | no_answer | $3.25 |  | empty response |
| Q07 | baseline | wrong_entity | manager@maplestreetmarket.example | The email address for contacting the manager is maplestreetmarket.example.  ANSWER: maplestreetmarket.example | expected phrase not found |
| Q33 | baseline | hallucination | The text does not mention an assistant manager. | The assistant manager of Maple Street Market is Rosa Delgado, the day-to-day manager who has been working since 2010.  ANSWER: Rosa Delgado | gave a specific answer |
| Q36 | baseline | premise_accepted | It doesn't; the store closes at 6:00 PM on Sundays. | The store closes at noon on Sundays because of the holiday, but the manager closes it earlier for scheduling purposes.  ANSWER: The store closes at noon on Sun… | went along with the premise |

## 11. Methodology and reproducibility

* **Task.** Each model reads a ~430-word fictional grocery-store description and answers 42 questions tagged by category, evidence position and difficulty. Questions were authored so that every answerable item has one unambiguous answer in the text, five items are unanswerable, and four contain a false premise.
* **Prompt variants.** The same question is asked under several prompt templates (see `data/prompts.json`); `baseline` is the reference. `no_context` is a control that omits the document.
* **Scoring.** Deterministic string rules (`grocery_eval/scoring.py`): numeric match with ±0.01 tolerance (number words accepted, clock times ignored), case-insensitive phrase match with aliases, earliest yes/no signal, first-mentioned option for multiple choice, item-level F1 for lists, abstention regex for unanswerable items, and true-fact / contradiction markers for false premises. When a response contains a `FINAL ANSWER:` line only that line is scored; `<think>` blocks are stripped. A scorer self-test (`python run_eval.py --self-test`) confirms every reference answer scores correct and every `plausible_wrong` answer scores incorrect.
* **Known scorer limitations.** Free-form comparative answers ('bananas are cheaper than apples') can be mis-read by the first-mention rule; a model that states the right number alongside wrong ones is scored correct; refusal detection is pattern-based. Use `--judge-model` to add an LLM judge and compare the two columns, and inspect `results.jsonl` for raw responses.
* **Statistics.** Wilson 95% intervals for proportions; paired bootstrap over questions and an exact sign test for model-vs-model differences. With 42 questions × variants the per-category cells are small; treat category-level differences of a few points as noise.
* **Reproduce.** `python run_eval.py --models deepseek-r1:1.5b --variants baseline strict_grounded --repeats 1 --temperature 0.0` then `python make_report.py --inputs <run>/results.jsonl`.
* **Files.** `results.jsonl` (full prompts and raw responses), `results.csv` (flat table), `summary.json` (every number in this report), `charts/` (if matplotlib was available).
