"""Heuristic answer scoring and failure-mode taxonomy.

Design goals
------------
* No external dependencies and no network calls, so scoring is fast, free and reproducible.
* Every verdict carries a `failure_mode` label so errors can be counted by type, not just by rate.
* The rules are deliberately simple and documented; an optional LLM judge (see run_eval.py
  --judge-model) can be layered on top for free-form answers where string rules are lossy.

Failure modes
-------------
correct            - the answer is right (and obeys any format constraint)
wrong_value        - a number was given but it is the wrong number
wrong_entity       - a name / option / yes-no was given but it is the wrong one
partial            - a list answer got some but not all items (score = F1)
no_answer          - nothing scoreable was produced (empty, or no number / option / yes-no found)
hallucination      - the question is unanswerable from the text but a specific answer was given
over_refusal       - the question is answerable from the text but the model said it was not
premise_accepted   - the question contained a false premise and the model went along with it
format_violation   - content is right but the required output format was not followed
error              - the API call failed
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- refusal detection
_REFUSAL_PATTERNS = [
    r"\bnot (?:stated|mentioned|specified|provided|given|included|listed|available|indicated|described|disclosed|shown|present)\b",
    r"\b(?:does not|doesn't|did not|didn't|do not|don't) (?:say|state|mention|specify|provide|give|include|list|contain|indicate|tell|disclose|show)\b",
    r"\bno (?:information|mention|details?|data|indication|record)\b",
    r"\b(?:cannot|can't|can not|unable to|not possible to|impossible to) (?:be )?(?:determine|answer|find|know|tell|say|locate|confirm|identify|verify)\b",
    r"\b(?:isn't|is not|aren't|are not|was not|wasn't) (?:stated|mentioned|specified|provided|given|included|listed|available|indicated|in the (?:text|document|passage))\b",
    r"\bnot (?:in|found in|present in|part of|covered by) the (?:text|document|passage|information|provided)\b",
    r"\bi (?:don't|do not) (?:have|know)\b",
    r"\bno way to (?:know|tell|determine)\b",
    r"\binsufficient (?:information|data)\b",
    r"\bnot enough (?:information|data)\b",
    r"\bunknown\b",
    r"\bnot stated\b",
]
_REFUSAL_RE = re.compile("|".join(_REFUSAL_PATTERNS), re.IGNORECASE)

# Strong, premise-independent contradiction markers used for false-premise questions.
_CONTRADICTION_PATTERNS = [
    r"\bincorrect\b", r"\bnot accurate\b", r"\binaccurate\b", r"\bnot true\b", r"\buntrue\b",
    r"\bfalse premise\b", r"\bmistaken\b", r"\bactually,", r"\bthat's not (?:right|correct|the case)\b",
    r"\bthat is not (?:right|correct|the case)\b", r"\bcontradicts\b", r"\bno such\b",
]
_CONTRADICTION_RE = re.compile("|".join(_CONTRADICTION_PATTERNS), re.IGNORECASE)

_THINK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_FINAL_RE = re.compile(r"final answer\s*\**\s*[:\-]\s*\**\s*", re.IGNORECASE)
_LEADING_ANSWER_RE = re.compile(r"^\s*(?:final\s+)?answer\s*[:\-]\s*", re.IGNORECASE)
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
_NUM_RE = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "twice": 2, "double": 2,
}


# --------------------------------------------------------------------------- text utilities
def normalize(text: str) -> str:
    """Lower-case, unify quotes, drop currency/thousands separators and most punctuation.

    Periods are kept only between digits (3.60) so '9:00 a.m.' -> '9:00 am' and '$3.60.' -> '3.60'.
    Colons are kept so times survive. '@' is kept for e-mail addresses.
    """
    t = (text or "").lower()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\b([ap])\.m\.", r"\1m", t)           # a.m. / p.m. -> am / pm
    t = t.replace("$", "").replace(",", "")
    t = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", t)          # periods not between digits
    t = re.sub(r"[^\w\s:@'.\-]", " ", t)              # other punctuation -> space
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_numbers(text: str) -> List[float]:
    """Numbers in the text, including number words. Clock times (9:00) are removed first so the
    '00' in '6:00 PM' is never read as a zero."""
    t = _TIME_RE.sub(" ", text or "")
    out: List[float] = []
    for m in _NUM_RE.finditer(t):
        s = m.group(0).replace("$", "").replace(",", "")
        try:
            out.append(float(s))
        except ValueError:
            pass
    for tok in re.findall(r"[a-z]+", t.lower()):
        if tok in _NUMBER_WORDS:
            out.append(float(_NUMBER_WORDS[tok]))
    return out


def is_refusal(text: str) -> bool:
    return bool(_REFUSAL_RE.search(text or ""))


def split_response(raw: str) -> Tuple[str, str, str]:
    """Split a raw model response into (thinking, reasoning, final_answer).

    * thinking   - content of <think>...</think> blocks (reasoning models)
    * reasoning  - visible text before a 'FINAL ANSWER:' marker (chain-of-thought prompts)
    * final      - the text that gets scored: after the last 'FINAL ANSWER:' marker if present,
                   otherwise the whole visible response (with a leading 'ANSWER:' echo removed)
    """
    raw = raw or ""
    thinking = "\n".join(m.group(0)[7:-8].strip() for m in _THINK_RE.finditer(raw))
    content = _THINK_RE.sub("", raw).strip()
    matches = list(_FINAL_RE.finditer(content))
    if matches:
        m = matches[-1]
        final = content[m.end():].strip()
        reasoning = content[: m.start()].strip()
    else:
        final = content
        reasoning = ""
    final = _LEADING_ANSWER_RE.sub("", final).strip().strip("*").strip()
    return thinking, reasoning, final


def _contains_phrase(norm_text: str, phrase: str) -> bool:
    p = normalize(phrase)
    if not p:
        return False
    return re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", norm_text) is not None


def _word_count(text: str) -> int:
    return len((text or "").split())


# --------------------------------------------------------------------------- individual scorers
def _score_contains(spec: dict, norm: str) -> Tuple[bool, str]:
    candidates = [spec["expected"]] + list(spec.get("aliases", []))
    for c in candidates:
        if _contains_phrase(norm, c):
            return True, f"matched '{c}'"
    return False, "expected phrase not found"


def _score_numeric(spec: dict, norm: str) -> Tuple[bool, str, bool]:
    """Returns (correct, detail, had_signal). 'wrong_aliases' are phrases that count as a definite
    (wrong) answer even though they contain no number, e.g. 'free' when a fee was due."""
    expected = float(spec["expected"])
    tol = float(spec.get("tolerance", 0.011))
    for c in spec.get("aliases", []):
        if _contains_phrase(norm, c):
            return True, f"matched alias '{c}'", True
    nums = extract_numbers(norm)
    for n in nums:
        if abs(n - expected) <= tol:
            return True, f"found {n:g}", True
    if nums:
        return False, f"numbers found {sorted(set(nums))[:8]} but not {expected:g}", True
    for c in spec.get("wrong_aliases", []):
        if _contains_phrase(norm, c):
            return False, f"matched wrong-answer phrase '{c}'", True
    return False, "no number in answer", False


def _earliest(norm: str, phrases: List[str]) -> Optional[int]:
    best = None
    for p in phrases:
        pn = normalize(p)
        if not pn:
            continue
        m = re.search(r"(?<!\w)" + re.escape(pn) + r"(?!\w)", norm)
        if m and (best is None or m.start() < best):
            best = m.start()
    return best


def _score_yes_no(spec: dict, norm: str) -> Tuple[bool, str, bool]:
    """Decide by whichever side (yes-aliases vs no-aliases) appears first. Returns (correct, detail, found)."""
    yes_pos = _earliest(norm, spec.get("yes_aliases", ["yes"]))
    no_pos = _earliest(norm, spec.get("no_aliases", ["no"]))
    if yes_pos is None and no_pos is None:
        return False, "no yes/no signal found", False
    if no_pos is None or (yes_pos is not None and yes_pos < no_pos):
        chosen = "yes"
    else:
        chosen = "no"
    return chosen == spec["expected"].lower(), f"read as '{chosen}'", True


def _score_choice(spec: dict, norm: str) -> Tuple[bool, str, bool]:
    """Options are word stems; 'apple' matches 'apple' and 'apples'. If exactly one option is
    mentioned it is the answer, otherwise the first-mentioned option is taken."""
    mentions = []
    for opt in spec["options"]:
        m = re.search(r"(?<!\w)" + re.escape(normalize(opt)) + r"s?(?!\w)", norm)
        if m:
            mentions.append((m.start(), opt))
    if not mentions:
        return False, "no option mentioned", False
    mentions.sort()
    chosen = mentions[0][1]
    return chosen == spec["expected"], f"read as '{chosen}' (mentioned: {[o for _, o in mentions]})", True


def _score_set(spec: dict, norm: str) -> Tuple[float, str, bool]:
    """Item-level F1 against the expected set. Known distractor items count as false positives.
    Returns (f1, detail, format_ok)."""
    expected = [normalize(x) for x in spec["expected"]]
    hits = [x for x in expected if _contains_phrase(norm, x)]
    distractor_hits = [normalize(d) for d in spec.get("distractors", []) if _contains_phrase(norm, d)]
    tp = len(hits)
    fp = len(distractor_hits)
    fn = len(expected) - tp
    if tp == 0:
        f1 = 0.0
    else:
        p = tp / (tp + fp)
        r = tp / (tp + fn)
        f1 = 2 * p * r / (p + r)
    format_ok = True
    if spec.get("format") == "list_only":
        allowed = set()
        for x in expected:
            allowed.update(x.split())
        allowed.update(normalize(w) for w in spec.get("allowed_extra_words", []))
        extra = [w for w in norm.split() if w not in allowed]
        format_ok = not extra
        if extra:
            f1_detail = f"F1={f1:.2f}; extra words {extra[:6]}"
            return f1, f1_detail, format_ok
    return f1, f"F1={f1:.2f} (hits {tp}/{len(expected)}, distractors {fp})", format_ok


def _score_exact(spec: dict, norm: str) -> Tuple[bool, bool, str]:
    """Returns (content_correct, format_ok, detail). Format is OK only if the answer is a single token."""
    tokens = norm.split()
    format_ok = len(tokens) == 1
    expected = str(spec["expected"]).lower()
    try:
        exp_num: Optional[float] = float(expected)
    except ValueError:
        exp_num = None
    if exp_num is not None:
        content = any(abs(n - exp_num) <= 0.011 for n in extract_numbers(norm))
    elif expected in ("yes", "no"):
        yes_pos = _earliest(norm, ["yes"])
        no_pos = _earliest(norm, ["no"])
        if yes_pos is None and no_pos is None:
            content = False
        elif no_pos is None or (yes_pos is not None and yes_pos < no_pos):
            content = expected == "yes"
        else:
            content = expected == "no"
    else:
        content = _contains_phrase(norm, expected)
    return content, format_ok, f"tokens={len(tokens)}, content={'ok' if content else 'wrong'}"


# --------------------------------------------------------------------------- main entry point
def score_response(question: Dict[str, Any], raw_response: str, error: Optional[str] = None) -> Dict[str, Any]:
    """Score one model response against one question. Returns a dict that is merged into the result row."""
    thinking, reasoning, final = split_response(raw_response)
    norm = normalize(final)
    spec = question["scoring"]
    qtype = spec["type"]
    refused = is_refusal(final)

    result: Dict[str, Any] = {
        "thinking": thinking,
        "reasoning": reasoning,
        "final_answer": final,
        "response_words": _word_count(_THINK_RE.sub("", raw_response or "")),
        "reasoning_words": _word_count(reasoning) + _word_count(thinking),
        "refused": refused,
        "format_ok": None,
        "content_correct": False,
        "correct": False,
        "score": 0.0,
        "failure_mode": None,
        "scoring_detail": "",
    }

    if error:
        result.update(failure_mode="error", scoring_detail=str(error)[:200])
        return result

    if not norm:
        result.update(failure_mode="no_answer", scoring_detail="empty response")
        return result

    # --- unanswerable: the right behaviour is to abstain
    if qtype == "refusal":
        if refused:
            result.update(correct=True, content_correct=True, score=1.0, scoring_detail="abstained")
        else:
            result.update(failure_mode="hallucination", scoring_detail="gave a specific answer")
        return result

    # --- false premise: the right behaviour is to correct the premise
    if qtype == "premise_correction":
        matched = next((a for a in spec.get("aliases", []) if _contains_phrase(norm, a)), None)
        if matched is not None:
            result.update(correct=True, content_correct=True, score=1.0, scoring_detail=f"corrected via '{matched}'")
        elif _CONTRADICTION_RE.search(final):
            result.update(correct=True, content_correct=True, score=1.0, scoring_detail="generic contradiction marker")
        else:
            detail = "refused without correcting the premise" if refused else "went along with the premise"
            result.update(failure_mode="premise_accepted", scoring_detail=detail)
        return result

    # --- answerable questions
    content_correct = False
    format_ok: Optional[bool] = None
    detail = ""
    had_signal = True
    partial_score: Optional[float] = None

    if qtype == "contains":
        content_correct, detail = _score_contains(spec, norm)
    elif qtype == "numeric":
        content_correct, detail, had_signal = _score_numeric(spec, norm)
    elif qtype == "yes_no":
        content_correct, detail, had_signal = _score_yes_no(spec, norm)
    elif qtype == "choice":
        content_correct, detail, had_signal = _score_choice(spec, norm)
    elif qtype == "set":
        f1, detail, format_ok = _score_set(spec, norm)
        partial_score = f1
        content_correct = f1 >= 0.999
        had_signal = f1 > 0
    elif qtype == "exact":
        content_correct, format_ok, detail = _score_exact(spec, norm)
    else:
        raise ValueError(f"Unknown scoring type: {qtype}")

    result["content_correct"] = content_correct
    result["format_ok"] = format_ok
    result["scoring_detail"] = detail

    if content_correct:
        if format_ok is False:
            result.update(failure_mode="format_violation", score=0.0)
        else:
            result.update(correct=True, score=1.0)
        return result

    if refused:
        result.update(failure_mode="over_refusal", score=0.0)
        return result

    if partial_score is not None and partial_score > 0:
        result.update(failure_mode="partial", score=round(partial_score, 3))
        return result

    if not had_signal:
        result.update(failure_mode="no_answer")
    elif qtype == "numeric":
        result.update(failure_mode="wrong_value")
    else:
        result.update(failure_mode="wrong_entity")
    return result
