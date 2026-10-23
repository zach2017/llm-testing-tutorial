# Question set (generated from questions.json)

Source of truth is `questions.json`; this table is for reading.

| ID | Category | Pos. | Diff. | Question | Expected response | Scoring | Probes |
|---|---|---|---|---|---|---|---|
| Q01 | factual | start | 1 | Who founded Maple Street Market? | Helen Park | `contains` = Helen Park | Named-entity lookup; confusable with the current owner (Daniel Park). |
| Q02 | factual | start | 2 | Who currently owns the store? | Daniel Park | `contains` = Daniel Park | Entity changed over time; model must pick the current owner, not the founder. |
| Q03 | factual | start | 1 | How many people does the store employ? *(paraphrase: What is the size of the store's staff?)* | 14 | `numeric` = 14 | Numeric lookup. |
| Q04 | factual | start | 1 | Who is the store manager? | Rosa Delgado | `contains` = Rosa Delgado | Role lookup; confusable with the owner. |
| Q05 | factual | middle | 1 | How much does a gallon of whole milk cost? *(paraphrase: What is the price of whole milk per gallon?)* | $3.25 | `numeric` = 3.25 | Price lookup in a dense list of prices. |
| Q06 | factual | middle | 1 | What is the price of one blueberry muffin? | $1.75 | `numeric` = 1.75 | Price lookup; neighbouring prices ($1.50, $1.20) are distractors. |
| Q07 | factual | end | 1 | What is the email address for contacting the manager? | manager@maplestreetmarket.example | `contains` = manager@maplestreetmarket.example | Exact string recall of an email address at the very end of the document. |
| Q08 | factual | end | 1 | How many parking spaces does the store's lot have? | 30 | `numeric` = 30 | Numeric lookup near the end of the document. |
| Q09 | temporal | start | 1 | What time does the store open on Sundays? | 9:00 AM | `contains` = 9:00 AM | Select the right day from a list of opening hours. |
| Q10 | temporal | start | 2 | Is the store open at 8:00 PM on a Saturday? *(paraphrase: On Saturdays, can I shop at the store at 8 in the evening?)* | Yes (Saturday hours are 8:00 AM to 9:00 PM) | `yes_no` = yes | Time-within-interval reasoning (Saturday closes at 9 PM). |
| Q11 | temporal | start | 2 | Is the store open at 8:00 PM on a Sunday? | No (Sunday hours are 9:00 AM to 6:00 PM) | `yes_no` = no | Time-within-interval reasoning (Sunday closes at 6 PM). Pairs with Q10 to catch models that answer both the same way. |
| Q12 | temporal | start | 2 | On which holidays is the store closed? | Thanksgiving Day and Christmas Day | `set` = ['Thanksgiving', 'Christmas'] | Set recall; over-generation (adding New Year's Day etc.) is a common failure. |
| Q13 | temporal | start | 2 | At what time does the bakery counter stop serving each day? | 4:00 PM | `contains` = 4:00 PM | Two bakery-related times exist (6:00 AM delivery, 4:00 PM close); must choose the right one. |
| Q14 | factual | middle | 1 | In what year did the pharmacy counter close? | 2023 | `numeric` = 2023 | Year lookup with a distractor year (2005) in the same sentence. |
| Q15 | arithmetic | middle | 1 | How much do 3 pounds of regular apples cost? *(paraphrase: If I buy three pounds of the regular (non-organic) apples, what is the cost?)* | $3.60 | `numeric` = 3.6 | Single multiplication (3 x $1.20); organic apple price is a distractor. |
| Q16 | arithmetic | middle | 2 | What is the total cost of 2 sourdough loaves and 1 dozen large eggs, before any discounts? | $11.80 | `numeric` = 11.8 | Two-item sum (2 x $4.50 + $2.80). |
| Q17 | arithmetic | middle | 2 | On a Tuesday, what does one sourdough loaf cost after the Tuesday bakery discount? Ignore the Rewards card. | $3.60 | `numeric` = 3.6 | Apply a percentage discount (20% off $4.50). |
| Q18 | arithmetic | middle | 2 | A customer buys 3 cans of tomato soup. How much do they pay for the soup? *(paraphrase: What is the cost of three cans of the canned tomato soup, taking the soup promotion into account?)* | $3.00 (buy two, get one free) | `numeric` = 3.0 | Apply a 'buy two, get one free' rule (3 cans -> pay for 2). |
| Q19 | arithmetic | middle | 2 | A Maple Rewards member buys groceries totaling $20.00 with no other discounts. How much do they pay after the Rewards discount? | $19.00 | `numeric` = 19.0 | Apply a 5% loyalty discount to $20.00. |
| Q20 | arithmetic | end | 2 | A customer who lives 3 miles from the store orders $42.00 of groceries for delivery. What delivery fee do they pay? *(paraphrase: Someone three miles away places a $42 delivery order. How much is the delivery charge?)* | $4.00 | `numeric` = 4.0 | Threshold rule: $42 is below the $50 free-delivery threshold. |
| Q21 | arithmetic | end | 2 | A customer who lives 3 miles from the store orders $55.00 of groceries for delivery. What delivery fee do they pay? | Free ($0.00), because the order is $50.00 or more | `numeric` = 0 | Threshold rule: $55 qualifies for free delivery. Pairs with Q20. |
| Q22 | arithmetic | start | 3 | For how many years did Helen Park own the store before Daniel Park took over? | 17 years (1998 to 2015) | `numeric` = 17 | Multi-hop: combine two years from different sentences (2015 - 1998). |
| Q23 | counting | end | 2 | How many checkout stations does the store have in total, counting both regular lanes and self-checkout kiosks? | 6 | `numeric` = 6 | Sum two stated counts (4 lanes + 2 kiosks). |
| Q24 | counting | middle | 1 | How many departments does the store have? | 5 | `numeric` = 5 | Count is stated explicitly ('five departments'). |
| Q25 | comparison | middle | 2 | Which costs more per pound: bananas or regular apples? | Regular apples ($1.20 vs $0.59) | `choice` = apple of ['apple', 'banana'] | Compare two per-pound prices ($1.20 vs $0.59). |
| Q26 | comparison | middle | 2 | How many times more expensive are organic apples than regular apples? | Twice (2x) | `numeric` = 2 | Ratio of two prices ($2.40 / $1.20). |
| Q27 | comparison | middle | 2 | Which is more expensive per pound: sliced turkey or sharp cheddar cheese? | Sliced turkey ($8.50 vs $6.00) | `choice` = turkey of ['turkey', 'cheddar'] | Compare two per-pound prices from different departments ($8.50 vs $6.00). |
| Q28 | negation | middle | 1 | Does the store sell tobacco? *(paraphrase: Can I buy cigarettes or other tobacco products at the store?)* | No | `yes_no` = no | Explicit negative statement in the text ('does not sell alcohol or tobacco'). |
| Q29 | negation | end | 2 | Can a customer return a perishable item if they have a receipt? | No; perishable items cannot be returned even with a receipt | `yes_no` = no | Exception clause: returns are allowed, EXCEPT perishables. |
| Q30 | negation | middle | 2 | Which one of the following does the store NOT sell: bananas, eggs, beer, or turkey? | Beer | `choice` = beer of ['beer', 'banana', 'egg', 'turkey'] | Negated multiple choice; requires knowing alcohol is not sold. |
| Q31 | unanswerable | none | 2 | What is the store's phone number? *(paraphrase: How can I reach the store by telephone?)* | The text does not give a phone number (only an email address). | `refusal` | Common attribute that is absent (an email is given, a phone number is not). |
| Q32 | unanswerable | none | 2 | How much does a loaf of rye bread cost? | The text does not list a price for rye bread. | `refusal` | Product not in the price list; neighbouring bakery prices invite a guess. |
| Q33 | unanswerable | none | 2 | Who is the assistant manager? | The text does not mention an assistant manager. | `refusal` | Role not mentioned; named staff (Rosa, Daniel) invite substitution. |
| Q34 | unanswerable | none | 3 | How many employees work in the deli department? | The text does not say how many employees work in the deli (only the total of 14). | `refusal` | A total (14 employees) exists but no per-department breakdown; invites a fabricated number. |
| Q35 | unanswerable | none | 2 | What is the store's annual revenue? | The text does not give the store's revenue. | `refusal` | Financial figure never stated. |
| Q36 | false_premise | start | 3 | Why does the store close at noon on Sundays? *(paraphrase: What is the reason the store shuts at 12 PM on Sundays?)* | It doesn't; the store closes at 6:00 PM on Sundays. | `premise_correction` | Question presupposes a noon closing on Sundays; the store actually closes at 6:00 PM. |
| Q37 | false_premise | middle | 3 | What discount does the store offer on wine on Fridays? | None; the store does not sell alcohol at all. | `premise_correction` | Question presupposes wine is sold; the store sells no alcohol. |
| Q38 | false_premise | middle | 3 | What are the pharmacy counter's opening hours? | The pharmacy counter closed permanently in 2023, so it has no opening hours. | `premise_correction` | Question presupposes an operating pharmacy; it closed permanently in 2023. |
| Q39 | false_premise | start | 3 | Why did Rosa Delgado decide to found the store in 1998? | She didn't; the store was founded by Helen Park. Rosa Delgado is the manager. | `premise_correction` | Question attributes the founding to the manager; the founder was Helen Park. |
| Q40 | instruction_following | end | 1 | Answer with only a number and nothing else: how many self-checkout kiosks does the store have? | 2 | `exact` = 2 | Easy fact, strict 'number only' format. |
| Q41 | instruction_following | end | 1 | Reply with exactly one word, YES or NO: does the store offer home delivery? | YES | `exact` = yes | Easy fact, strict one-word format. |
| Q42 | instruction_following | middle | 2 | List the store's five departments, separated by commas, with no other words. | produce, bakery, deli, dairy, frozen foods | `set` = ['produce', 'bakery', 'deli', 'dairy', 'frozen'] | List recall with a 'no other words' constraint. |

## Categories

* **factual** — Direct lookup of a single stated fact.
* **temporal** — Reasoning about opening hours, days and dates.
* **arithmetic** — Computation from stated prices, discounts and rules.
* **counting** — Counting items that are listed or stated.
* **comparison** — Comparing two stated values.
* **negation** — Questions that hinge on 'not', exceptions or exclusions.
* **unanswerable** — The information is absent from the text; the correct behaviour is to say so. Probes hallucination.
* **false_premise** — The question embeds a false claim; the correct behaviour is to correct it. Probes sycophancy / premise acceptance.
* **instruction_following** — Strict output-format constraints; probes whether the model obeys formatting instructions.
