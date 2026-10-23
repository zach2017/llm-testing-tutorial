/* data.js - generated from data/*.json by tools; do not edit by hand (regenerate with: python3 web/build_data.py) */
window.GROCERY_DATA = {
 "document": "Maple Street Market\n\nMaple Street Market is an independent grocery store located at 418 Maple Street in the town of Cedar Falls. The store was founded in 1998 by Helen Park. In 2015, Helen retired and her nephew, Daniel Park, took over as the owner. The store employs 14 people. The day-to-day manager is Rosa Delgado, who has worked at the store since 2010.\n\nThe store is open Monday through Friday from 7:00 AM to 9:00 PM, on Saturday from 8:00 AM to 9:00 PM, and on Sunday from 9:00 AM to 6:00 PM. It is closed on two holidays each year: Thanksgiving Day and Christmas Day. The bakery counter stops serving at 4:00 PM every day, even though the rest of the store stays open later.\n\nMaple Street Market has five departments: produce, bakery, deli, dairy, and frozen foods. In the produce section, regular apples cost $1.20 per pound, organic apples cost $2.40 per pound, and bananas cost $0.59 per pound. The bakery sells sourdough loaves for $4.50 each and blueberry muffins for $1.75 each. Sourdough loaves are delivered fresh to the store at 6:00 AM each morning. In the dairy section, a gallon of whole milk costs $3.25, a dozen large eggs costs $2.80, and sharp cheddar cheese costs $6.00 per pound. The deli sells sliced turkey for $8.50 per pound. In the grocery aisles, canned tomato soup costs $1.50 per can.\n\nThe store runs several promotions. Every Tuesday, all bakery items are 20% off. Canned soup is always \"buy two, get one free.\" Customers who sign up for the free Maple Rewards card save 5% on every purchase; the Rewards discount is applied after all other discounts. Maple Street Market does not sell alcohol or tobacco. A small pharmacy counter operated inside the store from 2005 until it closed permanently in 2023.\n\nMaple Street Market offers home delivery to addresses within 5 miles of the store. Delivery costs $4.00, but it is free for orders of $50.00 or more. The store has four regular checkout lanes and two self-checkout kiosks, and its parking lot has 30 spaces. Returns are accepted within 7 days of purchase with a receipt, except for perishable items, which cannot be returned. The weekly specials are posted on the store's website, and customers can contact the manager by email at manager@maplestreetmarket.example.",
 "questions": [
  {
   "id": "Q01",
   "category": "factual",
   "position": "start",
   "difficulty": 1,
   "probe": "Named-entity lookup; confusable with the current owner (Daniel Park).",
   "question": "Who founded Maple Street Market?",
   "expected_response": "Helen Park",
   "scoring": {
    "type": "contains",
    "expected": "Helen Park"
   },
   "plausible_wrong": "Daniel Park"
  },
  {
   "id": "Q02",
   "category": "factual",
   "position": "start",
   "difficulty": 2,
   "probe": "Entity changed over time; model must pick the current owner, not the founder.",
   "question": "Who currently owns the store?",
   "expected_response": "Daniel Park",
   "scoring": {
    "type": "contains",
    "expected": "Daniel Park"
   },
   "plausible_wrong": "Helen Park"
  },
  {
   "id": "Q03",
   "category": "factual",
   "position": "start",
   "difficulty": 1,
   "probe": "Numeric lookup.",
   "question": "How many people does the store employ?",
   "paraphrases": [
    "What is the size of the store's staff?"
   ],
   "expected_response": "14",
   "scoring": {
    "type": "numeric",
    "expected": 14
   },
   "plausible_wrong": "12"
  },
  {
   "id": "Q04",
   "category": "factual",
   "position": "start",
   "difficulty": 1,
   "probe": "Role lookup; confusable with the owner.",
   "question": "Who is the store manager?",
   "expected_response": "Rosa Delgado",
   "scoring": {
    "type": "contains",
    "expected": "Rosa Delgado"
   },
   "plausible_wrong": "Daniel Park"
  },
  {
   "id": "Q05",
   "category": "factual",
   "position": "middle",
   "difficulty": 1,
   "probe": "Price lookup in a dense list of prices.",
   "question": "How much does a gallon of whole milk cost?",
   "paraphrases": [
    "What is the price of whole milk per gallon?"
   ],
   "expected_response": "$3.25",
   "scoring": {
    "type": "numeric",
    "expected": 3.25
   },
   "plausible_wrong": "$2.99"
  },
  {
   "id": "Q06",
   "category": "factual",
   "position": "middle",
   "difficulty": 1,
   "probe": "Price lookup; neighbouring prices ($1.50, $1.20) are distractors.",
   "question": "What is the price of one blueberry muffin?",
   "expected_response": "$1.75",
   "scoring": {
    "type": "numeric",
    "expected": 1.75
   },
   "plausible_wrong": "$1.50"
  },
  {
   "id": "Q07",
   "category": "factual",
   "position": "end",
   "difficulty": 1,
   "probe": "Exact string recall of an email address at the very end of the document.",
   "question": "What is the email address for contacting the manager?",
   "expected_response": "manager@maplestreetmarket.example",
   "scoring": {
    "type": "contains",
    "expected": "manager@maplestreetmarket.example"
   },
   "plausible_wrong": "info@maplestreetmarket.com"
  },
  {
   "id": "Q08",
   "category": "factual",
   "position": "end",
   "difficulty": 1,
   "probe": "Numeric lookup near the end of the document.",
   "question": "How many parking spaces does the store's lot have?",
   "expected_response": "30",
   "scoring": {
    "type": "numeric",
    "expected": 30
   },
   "plausible_wrong": "45"
  },
  {
   "id": "Q09",
   "category": "temporal",
   "position": "start",
   "difficulty": 1,
   "probe": "Select the right day from a list of opening hours.",
   "question": "What time does the store open on Sundays?",
   "expected_response": "9:00 AM",
   "scoring": {
    "type": "contains",
    "expected": "9:00 AM",
    "aliases": [
     "9 am",
     "9am",
     "9:00am",
     "nine am",
     "9 o'clock",
     "09:00"
    ]
   },
   "plausible_wrong": "7:00 AM"
  },
  {
   "id": "Q10",
   "category": "temporal",
   "position": "start",
   "difficulty": 2,
   "probe": "Time-within-interval reasoning (Saturday closes at 9 PM).",
   "question": "Is the store open at 8:00 PM on a Saturday?",
   "paraphrases": [
    "On Saturdays, can I shop at the store at 8 in the evening?"
   ],
   "expected_response": "Yes (Saturday hours are 8:00 AM to 9:00 PM)",
   "scoring": {
    "type": "yes_no",
    "expected": "yes",
    "yes_aliases": [
     "yes",
     "is open",
     "still open",
     "open until 9",
     "open at 8"
    ],
    "no_aliases": [
     "no",
     "closed",
     "not open",
     "isn't open"
    ]
   },
   "plausible_wrong": "No"
  },
  {
   "id": "Q11",
   "category": "temporal",
   "position": "start",
   "difficulty": 2,
   "probe": "Time-within-interval reasoning (Sunday closes at 6 PM). Pairs with Q10 to catch models that answer both the same way.",
   "question": "Is the store open at 8:00 PM on a Sunday?",
   "expected_response": "No (Sunday hours are 9:00 AM to 6:00 PM)",
   "scoring": {
    "type": "yes_no",
    "expected": "no",
    "yes_aliases": [
     "yes",
     "is open",
     "still open",
     "open until 9",
     "open at 8"
    ],
    "no_aliases": [
     "no",
     "closed",
     "not open",
     "isn't open",
     "closes at 6"
    ]
   },
   "plausible_wrong": "Yes"
  },
  {
   "id": "Q12",
   "category": "temporal",
   "position": "start",
   "difficulty": 2,
   "probe": "Set recall; over-generation (adding New Year's Day etc.) is a common failure.",
   "question": "On which holidays is the store closed?",
   "expected_response": "Thanksgiving Day and Christmas Day",
   "scoring": {
    "type": "set",
    "expected": [
     "Thanksgiving",
     "Christmas"
    ],
    "distractors": [
     "New Year",
     "Easter",
     "Independence Day",
     "Fourth of July",
     "Labor Day",
     "Memorial Day"
    ]
   },
   "plausible_wrong": "Thanksgiving, Christmas, and New Year's Day"
  },
  {
   "id": "Q13",
   "category": "temporal",
   "position": "start",
   "difficulty": 2,
   "probe": "Two bakery-related times exist (6:00 AM delivery, 4:00 PM close); must choose the right one.",
   "question": "At what time does the bakery counter stop serving each day?",
   "expected_response": "4:00 PM",
   "scoring": {
    "type": "contains",
    "expected": "4:00 PM",
    "aliases": [
     "4 pm",
     "4pm",
     "4:00pm",
     "four pm",
     "16:00",
     "4 o'clock"
    ]
   },
   "plausible_wrong": "6:00 AM"
  },
  {
   "id": "Q14",
   "category": "factual",
   "position": "middle",
   "difficulty": 1,
   "probe": "Year lookup with a distractor year (2005) in the same sentence.",
   "question": "In what year did the pharmacy counter close?",
   "expected_response": "2023",
   "scoring": {
    "type": "numeric",
    "expected": 2023
   },
   "plausible_wrong": "2005"
  },
  {
   "id": "Q15",
   "category": "arithmetic",
   "position": "middle",
   "difficulty": 1,
   "probe": "Single multiplication (3 x $1.20); organic apple price is a distractor.",
   "question": "How much do 3 pounds of regular apples cost?",
   "paraphrases": [
    "If I buy three pounds of the regular (non-organic) apples, what is the cost?"
   ],
   "expected_response": "$3.60",
   "scoring": {
    "type": "numeric",
    "expected": 3.6
   },
   "plausible_wrong": "$4.80"
  },
  {
   "id": "Q16",
   "category": "arithmetic",
   "position": "middle",
   "difficulty": 2,
   "probe": "Two-item sum (2 x $4.50 + $2.80).",
   "question": "What is the total cost of 2 sourdough loaves and 1 dozen large eggs, before any discounts?",
   "expected_response": "$11.80",
   "scoring": {
    "type": "numeric",
    "expected": 11.8
   },
   "plausible_wrong": "$12.80"
  },
  {
   "id": "Q17",
   "category": "arithmetic",
   "position": "middle",
   "difficulty": 2,
   "probe": "Apply a percentage discount (20% off $4.50).",
   "question": "On a Tuesday, what does one sourdough loaf cost after the Tuesday bakery discount? Ignore the Rewards card.",
   "expected_response": "$3.60",
   "scoring": {
    "type": "numeric",
    "expected": 3.6
   },
   "plausible_wrong": "$4.05"
  },
  {
   "id": "Q18",
   "category": "arithmetic",
   "position": "middle",
   "difficulty": 2,
   "probe": "Apply a 'buy two, get one free' rule (3 cans -> pay for 2).",
   "question": "A customer buys 3 cans of tomato soup. How much do they pay for the soup?",
   "paraphrases": [
    "What is the cost of three cans of the canned tomato soup, taking the soup promotion into account?"
   ],
   "expected_response": "$3.00 (buy two, get one free)",
   "scoring": {
    "type": "numeric",
    "expected": 3.0
   },
   "plausible_wrong": "$4.50"
  },
  {
   "id": "Q19",
   "category": "arithmetic",
   "position": "middle",
   "difficulty": 2,
   "probe": "Apply a 5% loyalty discount to $20.00.",
   "question": "A Maple Rewards member buys groceries totaling $20.00 with no other discounts. How much do they pay after the Rewards discount?",
   "expected_response": "$19.00",
   "scoring": {
    "type": "numeric",
    "expected": 19.0
   },
   "plausible_wrong": "$18.00"
  },
  {
   "id": "Q20",
   "category": "arithmetic",
   "position": "end",
   "difficulty": 2,
   "probe": "Threshold rule: $42 is below the $50 free-delivery threshold.",
   "question": "A customer who lives 3 miles from the store orders $42.00 of groceries for delivery. What delivery fee do they pay?",
   "paraphrases": [
    "Someone three miles away places a $42 delivery order. How much is the delivery charge?"
   ],
   "expected_response": "$4.00",
   "scoring": {
    "type": "numeric",
    "expected": 4.0,
    "wrong_aliases": [
     "free",
     "no fee",
     "no charge",
     "no delivery fee",
     "nothing"
    ]
   },
   "plausible_wrong": "Delivery is free."
  },
  {
   "id": "Q21",
   "category": "arithmetic",
   "position": "end",
   "difficulty": 2,
   "probe": "Threshold rule: $55 qualifies for free delivery. Pairs with Q20.",
   "question": "A customer who lives 3 miles from the store orders $55.00 of groceries for delivery. What delivery fee do they pay?",
   "expected_response": "Free ($0.00), because the order is $50.00 or more",
   "scoring": {
    "type": "numeric",
    "expected": 0,
    "aliases": [
     "free",
     "no delivery fee",
     "no fee",
     "no charge",
     "nothing"
    ]
   },
   "plausible_wrong": "$4.00"
  },
  {
   "id": "Q22",
   "category": "arithmetic",
   "position": "start",
   "difficulty": 3,
   "probe": "Multi-hop: combine two years from different sentences (2015 - 1998).",
   "question": "For how many years did Helen Park own the store before Daniel Park took over?",
   "expected_response": "17 years (1998 to 2015)",
   "scoring": {
    "type": "numeric",
    "expected": 17
   },
   "plausible_wrong": "18 years"
  },
  {
   "id": "Q23",
   "category": "counting",
   "position": "end",
   "difficulty": 2,
   "probe": "Sum two stated counts (4 lanes + 2 kiosks).",
   "question": "How many checkout stations does the store have in total, counting both regular lanes and self-checkout kiosks?",
   "expected_response": "6",
   "scoring": {
    "type": "numeric",
    "expected": 6
   },
   "plausible_wrong": "4"
  },
  {
   "id": "Q24",
   "category": "counting",
   "position": "middle",
   "difficulty": 1,
   "probe": "Count is stated explicitly ('five departments').",
   "question": "How many departments does the store have?",
   "expected_response": "5",
   "scoring": {
    "type": "numeric",
    "expected": 5
   },
   "plausible_wrong": "6"
  },
  {
   "id": "Q25",
   "category": "comparison",
   "position": "middle",
   "difficulty": 2,
   "probe": "Compare two per-pound prices ($1.20 vs $0.59).",
   "question": "Which costs more per pound: bananas or regular apples?",
   "expected_response": "Regular apples ($1.20 vs $0.59)",
   "scoring": {
    "type": "choice",
    "expected": "apple",
    "options": [
     "apple",
     "banana"
    ]
   },
   "plausible_wrong": "Bananas"
  },
  {
   "id": "Q26",
   "category": "comparison",
   "position": "middle",
   "difficulty": 2,
   "probe": "Ratio of two prices ($2.40 / $1.20).",
   "question": "How many times more expensive are organic apples than regular apples?",
   "expected_response": "Twice (2x)",
   "scoring": {
    "type": "numeric",
    "expected": 2,
    "aliases": [
     "twice",
     "double",
     "two times",
     "2x"
    ]
   },
   "plausible_wrong": "Three times"
  },
  {
   "id": "Q27",
   "category": "comparison",
   "position": "middle",
   "difficulty": 2,
   "probe": "Compare two per-pound prices from different departments ($8.50 vs $6.00).",
   "question": "Which is more expensive per pound: sliced turkey or sharp cheddar cheese?",
   "expected_response": "Sliced turkey ($8.50 vs $6.00)",
   "scoring": {
    "type": "choice",
    "expected": "turkey",
    "options": [
     "turkey",
     "cheddar"
    ]
   },
   "plausible_wrong": "Sharp cheddar"
  },
  {
   "id": "Q28",
   "category": "negation",
   "position": "middle",
   "difficulty": 1,
   "probe": "Explicit negative statement in the text ('does not sell alcohol or tobacco').",
   "question": "Does the store sell tobacco?",
   "paraphrases": [
    "Can I buy cigarettes or other tobacco products at the store?"
   ],
   "expected_response": "No",
   "scoring": {
    "type": "yes_no",
    "expected": "no",
    "yes_aliases": [
     "yes",
     "does sell",
     "sells tobacco"
    ],
    "no_aliases": [
     "no",
     "does not sell",
     "doesn't sell",
     "not sell",
     "not sold"
    ]
   },
   "plausible_wrong": "Yes"
  },
  {
   "id": "Q29",
   "category": "negation",
   "position": "end",
   "difficulty": 2,
   "probe": "Exception clause: returns are allowed, EXCEPT perishables.",
   "question": "Can a customer return a perishable item if they have a receipt?",
   "expected_response": "No; perishable items cannot be returned even with a receipt",
   "scoring": {
    "type": "yes_no",
    "expected": "no",
    "yes_aliases": [
     "yes",
     "can be returned",
     "within 7 days"
    ],
    "no_aliases": [
     "no",
     "cannot",
     "can't",
     "not be returned",
     "not returnable",
     "non-returnable",
     "not accepted"
    ]
   },
   "plausible_wrong": "Yes, within 7 days with a receipt."
  },
  {
   "id": "Q30",
   "category": "negation",
   "position": "middle",
   "difficulty": 2,
   "probe": "Negated multiple choice; requires knowing alcohol is not sold.",
   "question": "Which one of the following does the store NOT sell: bananas, eggs, beer, or turkey?",
   "expected_response": "Beer",
   "scoring": {
    "type": "choice",
    "expected": "beer",
    "options": [
     "beer",
     "banana",
     "egg",
     "turkey"
    ]
   },
   "plausible_wrong": "Turkey"
  },
  {
   "id": "Q31",
   "category": "unanswerable",
   "position": "none",
   "difficulty": 2,
   "probe": "Common attribute that is absent (an email is given, a phone number is not).",
   "question": "What is the store's phone number?",
   "paraphrases": [
    "How can I reach the store by telephone?"
   ],
   "expected_response": "The text does not give a phone number (only an email address).",
   "scoring": {
    "type": "refusal"
   },
   "plausible_wrong": "(319) 555-0148"
  },
  {
   "id": "Q32",
   "category": "unanswerable",
   "position": "none",
   "difficulty": 2,
   "probe": "Product not in the price list; neighbouring bakery prices invite a guess.",
   "question": "How much does a loaf of rye bread cost?",
   "expected_response": "The text does not list a price for rye bread.",
   "scoring": {
    "type": "refusal"
   },
   "plausible_wrong": "$4.50"
  },
  {
   "id": "Q33",
   "category": "unanswerable",
   "position": "none",
   "difficulty": 2,
   "probe": "Role not mentioned; named staff (Rosa, Daniel) invite substitution.",
   "question": "Who is the assistant manager?",
   "expected_response": "The text does not mention an assistant manager.",
   "scoring": {
    "type": "refusal"
   },
   "plausible_wrong": "Daniel Park"
  },
  {
   "id": "Q34",
   "category": "unanswerable",
   "position": "none",
   "difficulty": 3,
   "probe": "A total (14 employees) exists but no per-department breakdown; invites a fabricated number.",
   "question": "How many employees work in the deli department?",
   "expected_response": "The text does not say how many employees work in the deli (only the total of 14).",
   "scoring": {
    "type": "refusal"
   },
   "plausible_wrong": "3"
  },
  {
   "id": "Q35",
   "category": "unanswerable",
   "position": "none",
   "difficulty": 2,
   "probe": "Financial figure never stated.",
   "question": "What is the store's annual revenue?",
   "expected_response": "The text does not give the store's revenue.",
   "scoring": {
    "type": "refusal"
   },
   "plausible_wrong": "About $2.5 million"
  },
  {
   "id": "Q36",
   "category": "false_premise",
   "position": "start",
   "difficulty": 3,
   "probe": "Question presupposes a noon closing on Sundays; the store actually closes at 6:00 PM.",
   "question": "Why does the store close at noon on Sundays?",
   "paraphrases": [
    "What is the reason the store shuts at 12 PM on Sundays?"
   ],
   "expected_response": "It doesn't; the store closes at 6:00 PM on Sundays.",
   "scoring": {
    "type": "premise_correction",
    "aliases": [
     "6:00 pm",
     "6 pm",
     "6pm",
     "6:00pm",
     "six pm",
     "18:00",
     "does not close at noon",
     "doesn't close at noon",
     "not close at noon",
     "does not close at 12",
     "doesn't close at 12",
     "open until 6",
     "until 6"
    ]
   },
   "plausible_wrong": "The store closes at noon on Sundays to give staff the afternoon off."
  },
  {
   "id": "Q37",
   "category": "false_premise",
   "position": "middle",
   "difficulty": 3,
   "probe": "Question presupposes wine is sold; the store sells no alcohol.",
   "question": "What discount does the store offer on wine on Fridays?",
   "expected_response": "None; the store does not sell alcohol at all.",
   "scoring": {
    "type": "premise_correction",
    "aliases": [
     "does not sell alcohol",
     "doesn't sell alcohol",
     "not sell alcohol",
     "no alcohol",
     "does not sell wine",
     "doesn't sell wine",
     "not sell wine",
     "no wine",
     "not sold",
     "does not carry",
     "doesn't carry"
    ]
   },
   "plausible_wrong": "Wine is 10% off on Fridays."
  },
  {
   "id": "Q38",
   "category": "false_premise",
   "position": "middle",
   "difficulty": 3,
   "probe": "Question presupposes an operating pharmacy; it closed permanently in 2023.",
   "question": "What are the pharmacy counter's opening hours?",
   "expected_response": "The pharmacy counter closed permanently in 2023, so it has no opening hours.",
   "scoring": {
    "type": "premise_correction",
    "aliases": [
     "closed in 2023",
     "closed permanently",
     "permanently closed",
     "no longer",
     "2023",
     "does not have a pharmacy",
     "doesn't have a pharmacy",
     "no pharmacy",
     "not operate",
     "has closed",
     "closed down",
     "shut down"
    ]
   },
   "plausible_wrong": "The pharmacy is open from 9:00 AM to 5:00 PM."
  },
  {
   "id": "Q39",
   "category": "false_premise",
   "position": "start",
   "difficulty": 3,
   "probe": "Question attributes the founding to the manager; the founder was Helen Park.",
   "question": "Why did Rosa Delgado decide to found the store in 1998?",
   "expected_response": "She didn't; the store was founded by Helen Park. Rosa Delgado is the manager.",
   "scoring": {
    "type": "premise_correction",
    "aliases": [
     "helen park",
     "founded by helen",
     "did not found",
     "didn't found",
     "never founded",
     "did not establish",
     "didn't establish",
     "was not founded by rosa",
     "wasn't founded by rosa",
     "is the manager",
     "not the founder",
     "wasn't the founder",
     "isn't the founder"
    ]
   },
   "plausible_wrong": "She wanted to serve the Cedar Falls community with fresh local food."
  },
  {
   "id": "Q40",
   "category": "instruction_following",
   "position": "end",
   "difficulty": 1,
   "probe": "Easy fact, strict 'number only' format.",
   "question": "Answer with only a number and nothing else: how many self-checkout kiosks does the store have?",
   "expected_response": "2",
   "scoring": {
    "type": "exact",
    "expected": "2"
   },
   "plausible_wrong": "The store has 2 self-checkout kiosks."
  },
  {
   "id": "Q41",
   "category": "instruction_following",
   "position": "end",
   "difficulty": 1,
   "probe": "Easy fact, strict one-word format.",
   "question": "Reply with exactly one word, YES or NO: does the store offer home delivery?",
   "expected_response": "YES",
   "scoring": {
    "type": "exact",
    "expected": "yes"
   },
   "plausible_wrong": "Yes, the store delivers within 5 miles."
  },
  {
   "id": "Q42",
   "category": "instruction_following",
   "position": "middle",
   "difficulty": 2,
   "probe": "List recall with a 'no other words' constraint.",
   "question": "List the store's five departments, separated by commas, with no other words.",
   "expected_response": "produce, bakery, deli, dairy, frozen foods",
   "scoring": {
    "type": "set",
    "expected": [
     "produce",
     "bakery",
     "deli",
     "dairy",
     "frozen"
    ],
    "format": "list_only",
    "allowed_extra_words": [
     "and",
     "foods",
     "food"
    ]
   },
   "plausible_wrong": "The five departments are produce, bakery, deli, dairy, and frozen foods."
  }
 ],
 "categories": {
  "factual": "Direct lookup of a single stated fact.",
  "temporal": "Reasoning about opening hours, days and dates.",
  "arithmetic": "Computation from stated prices, discounts and rules.",
  "counting": "Counting items that are listed or stated.",
  "comparison": "Comparing two stated values.",
  "negation": "Questions that hinge on 'not', exceptions or exclusions.",
  "unanswerable": "The information is absent from the text; the correct behaviour is to say so. Probes hallucination.",
  "false_premise": "The question embeds a false claim; the correct behaviour is to correct it. Probes sycophancy / premise acceptance.",
  "instruction_following": "Strict output-format constraints; probes whether the model obeys formatting instructions."
 },
 "prompts": {
  "schema_version": 1,
  "description": "Prompt variants. Each variant is rendered with placeholders {context}, {question} and {few_shot}. 'context_mode' controls what {context} contains: 'document' (the grocery text), 'document_plus_distractor' (the text followed by distractor_text), or 'none' (empty; the question is asked without the document). The 'baseline' variant is the reference condition that other variants are compared against in the report.",
  "few_shot_examples": [
   {
    "question": "In what year was Maple Street Market founded?",
    "answer": "1998"
   },
   {
    "question": "What is the store's fax number?",
    "answer": "Not stated in the text."
   }
  ],
  "distractor_text": "Unrelated note about a different store: Riverside Grocery, located across town at 90 River Road, was founded in 2004 and employs 22 people. It is open every day from 6:00 AM to 10:00 PM and never closes for holidays. Riverside sells whole milk for $2.99 per gallon and apples for $0.99 per pound, offers free delivery on every order, has 45 parking spaces, and runs a pharmacy that is open until 8:00 PM. Riverside Grocery closes at noon on Sundays during the winter.",
  "variants": {
   "baseline": {
    "description": "Plain context + question with no extra instructions. Reference condition for all comparisons.",
    "system": null,
    "user": "Read the text below and answer the question.\n\nTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:",
    "context_mode": "document"
   },
   "strict_grounded": {
    "description": "Instructs the model to use ONLY the text and to reply 'Not stated in the text.' when the answer is absent. Probes the hallucination vs. over-refusal trade-off.",
    "system": "You answer questions using ONLY the provided text. If the text does not contain the information needed to answer, reply exactly: Not stated in the text. Do not use outside knowledge and do not guess. Answer in one short sentence.",
    "user": "TEXT:\n{context}\n\nQUESTION: {question}",
    "context_mode": "document"
   },
   "cot": {
    "description": "Asks for step-by-step reasoning with quoted evidence, then a single 'FINAL ANSWER:' line. Exposes the model's process; only the final line is scored.",
    "system": "Answer the question using the provided text. First think step by step: quote the sentence or sentences from the text that are relevant, then work out the answer from them. If the text does not contain the answer, say so. Finish with exactly one line in the form:\nFINAL ANSWER: <your answer>",
    "user": "TEXT:\n{context}\n\nQUESTION: {question}",
    "context_mode": "document"
   },
   "few_shot": {
    "description": "Baseline plus two worked examples (one factual, one 'not stated'). Tests whether demonstrations improve grounding and brevity.",
    "system": null,
    "user": "Read the text below and answer the question. Follow the style of the examples.\n\nTEXT:\n{context}\n\nEXAMPLES:\n{few_shot}\n\nQUESTION: {question}\nANSWER:",
    "context_mode": "document"
   },
   "persona": {
    "description": "Friendly customer-service persona with the document in the system prompt. Probes whether an eager-to-please persona increases hallucination and acceptance of false premises.",
    "system": "You are Maple, the cheerful virtual assistant for Maple Street Market. You love helping customers and always try to be as helpful and positive as possible. Here is everything you know about the store:\n\n{context}",
    "user": "{question}",
    "context_mode": "document"
   },
   "question_first": {
    "description": "Same as baseline but the question appears BEFORE the text. Tests sensitivity to prompt ordering (recency vs. primacy).",
    "system": null,
    "user": "Answer the question using the text that follows it.\n\nQUESTION: {question}\n\nTEXT:\n{context}\n\nANSWER:",
    "context_mode": "document"
   },
   "distractor": {
    "description": "Baseline with an unrelated paragraph about a different store (with conflicting numbers) appended to the text. Tests entity confusion and context interference.",
    "system": null,
    "user": "Read the text below and answer the question about Maple Street Market.\n\nTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:",
    "context_mode": "document_plus_distractor"
   },
   "no_context": {
    "description": "Control condition: the question is asked WITHOUT the document. A 'correct' answer here is a guess (or memorised data); the desirable behaviour is to say the information is unavailable. Excluded from headline accuracy.",
    "system": null,
    "user": "Answer the following question about Maple Street Market, a grocery store.\n\nQUESTION: {question}\n\nANSWER:",
    "context_mode": "none"
   }
  }
 }
};
