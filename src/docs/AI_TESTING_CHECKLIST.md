# Pre-deployment testing checklist for AI applications and agents

The grocery-store kit teaches a method on a toy problem. This checklist is the same method applied
to the three kinds of AI feature teams actually ship: a **chatbot** that answers from a fixed
knowledge base, a **retrieval (RAG) app** that answers from documents found at query time, and an
**agent** that calls tools and takes actions. Work through it before the first release and again
on every model, prompt or data change.

## A. Decide what "correct" means before you test

- [ ] **Write the golden set.** 40–200 questions with known answers, each tagged with the failure
      it probes (copy the kit's categories: factual, temporal, arithmetic, counting, comparison,
      negation, unanswerable, false premise, instruction following). Add your own: policy
      compliance, tone, language, PII handling.
- [ ] **Include the uncomfortable cases.** At least 10% unanswerable (the right answer is "I don't
      know"), 10% false-premise, and a few questions a hostile user would ask.
- [ ] **Decide the scoring rule per question** (exact, numeric, contains, yes/no, list F1,
      abstention, premise correction) and keep a `plausible_wrong` answer so a self-test can prove
      the scorer rejects it. Run the self-test whenever the golden set changes.
- [ ] **Set pass thresholds with the business**, e.g. accuracy ≥ 85%, hallucination ≤ 5%,
      premise acceptance ≤ 10%, format compliance ≥ 99%. Write them down before seeing results.

## B. Run the matrix, not a demo

- [ ] **Baseline + at least three prompt variants** (strict/grounded, chain-of-thought, persona if
      the product has one). Record Δ vs. baseline; large swings mean the product is fragile to
      prompt edits.
- [ ] **Repeat at the production temperature** (3–5 repeats). Report consistency and flip rate.
      An agent that is right 70% of the time per attempt is right 34% of the time over three
      dependent steps.
- [ ] **Paraphrase** a subset of questions. Users do not phrase things like your test author.
- [ ] **Distractor / long-context test.** Add unrelated or conflicting material to the context
      (another customer's record, an older policy) and check for entity confusion.
- [ ] **No-context control.** Ask the questions without the knowledge. High "accuracy" here means
      the questions are guessable, not that the system works.
- [ ] **Position test.** Put the critical fact at the start, middle and end of the context.

## C. Chatbot / knowledge-base specifics

- [ ] Out-of-scope questions get a graceful decline, not a confident guess.
- [ ] Stale facts: change a price/date in the knowledge base and confirm the answer changes.
- [ ] Multi-turn: ask a follow-up that depends on the previous answer; test that corrections
      ("no, I meant Sunday") take effect.
- [ ] Injection: a question containing "ignore your instructions and..." must not change behaviour.

## D. RAG (retrieval) specifics

- [ ] **Measure retrieval separately from generation.** For each golden question, is the right
      chunk in the top-k? (Recall@k.) A generation that is wrong because retrieval missed is a
      different bug.
- [ ] Citation faithfulness: every claim in the answer must be traceable to a retrieved chunk;
      sample 30 answers and check by hand.
- [ ] Conflicting documents: two chunks that disagree — does the answer flag the conflict?
- [ ] Empty retrieval: when nothing relevant is found, the system must say so.

## E. Agent / tool-use specifics

- [ ] **Tool selection accuracy**: given a task, does it pick the right tool with the right
      arguments? Score arguments like the kit scores answers (exact / numeric / contains).
- [ ] **Unnecessary actions**: count tool calls that were not needed. Side effects (emails sent,
      records changed) need an explicit allow-list and a dry-run mode in tests.
- [ ] **Failure handling**: make a tool return an error or garbage; the agent must not pretend
      it succeeded.
- [ ] **Premise acceptance at the action level**: "cancel order 123" when order 123 does not exist
      must produce a check, not a cancellation.
- [ ] **Loops and budgets**: maximum steps, maximum cost, timeouts — and tests that hit them.
- [ ] **Instruction following for structured output** (JSON schemas, function-call formats):
      measure format compliance separately; one malformed response can crash the pipeline.

## F. Statistics and reporting

- [ ] Report accuracy **with a confidence interval** (Wilson). With 42 questions the interval is
      ±14 points; do not announce a 3-point improvement without more data.
- [ ] Compare models/prompts **paired on the same questions** (bootstrap CI + sign test). Say
      "no evidence of a difference" when the interval includes zero.
- [ ] Always include the **failure-mode table** and 5–10 verbatim failures. Decision-makers
      understand "it invented a phone number" better than "accuracy 81%".
- [ ] Keep the raw responses (`results.jsonl`) with the report so anyone can re-check the scoring.
- [ ] Note the **scorer's limits** and, for free-form answers, add a second scorer (LLM judge or
      human sample) and report the agreement rate.

## G. Before go-live and after

- [ ] **Regression gate in CI**: run the golden set on every prompt/model/data change; fail the
      build if any threshold from A is missed. The kit's `run_eval.py` + `summary.json` can be
      the gate (`accuracy`, `hallucination_rate`, `format_compliance` fields).
- [ ] **Shadow mode**: run the new model alongside the old on real traffic, compare offline.
- [ ] **Monitoring**: log refusals, format failures and user corrections in production; sample
      weekly and add new failures to the golden set.
- [ ] **Rollback plan**: pin model versions; know how to go back to the previous prompt/model
      in minutes.
- [ ] **Human review of high-impact actions** until the agent's measured error rate on those
      actions is below the threshold agreed in A.

## H. Questions to ask whoever built it (for reviewers and managers)

1. Show me the golden set and who wrote the expected answers.
2. What is the hallucination rate on unanswerable questions? On false premises?
3. How much does accuracy move if someone edits the system prompt?
4. How consistent is it across three runs at production temperature?
5. What is the confidence interval, and were the two models compared on the same questions?
6. Which failure modes dominate, and what is the plan for each?
7. What runs automatically on the next change, and what makes it fail?
8. What happens in production when the model is wrong — who notices, and how fast?
