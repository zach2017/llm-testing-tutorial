"""Deterministic fake models for testing the pipeline without Ollama.

Three profiles (mock-strong / mock-medium / mock-weak) answer with the question's reference
answer or its 'plausible_wrong' answer according to per-profile probabilities, modulated by the
prompt variant in ways that imitate real small-model behaviour (e.g. strict prompts raise
abstention, personas lower it, distractors cost accuracy, no_context collapses accuracy).

The randomness is seeded from (model, variant, question, repeat) so a run is reproducible, and
repeats only differ when temperature > 0 - again mirroring real sampling behaviour.
"""

import hashlib
import random
from typing import Any, Dict

MOCK_MODELS = ["mock-strong", "mock-medium", "mock-weak"]

_PROFILES = {
    "mock-strong": {"acc": 0.88, "refuse_unanswerable": 0.85, "correct_premise": 0.75, "over_refuse": 0.03, "verbose": 0.55, "speed": 55.0},
    "mock-medium": {"acc": 0.68, "refuse_unanswerable": 0.50, "correct_premise": 0.40, "over_refuse": 0.08, "verbose": 0.45, "speed": 90.0},
    "mock-weak":   {"acc": 0.45, "refuse_unanswerable": 0.20, "correct_premise": 0.15, "over_refuse": 0.15, "verbose": 0.35, "speed": 140.0},
}

_VARIANT_MODIFIERS = {
    "baseline":        {},
    "strict_grounded": {"acc": -0.02, "refuse_unanswerable": +0.30, "over_refuse": +0.15, "verbose": -0.3},
    "cot":             {"acc": +0.06, "correct_premise": +0.15, "refuse_unanswerable": +0.05},
    "few_shot":        {"acc": +0.04, "refuse_unanswerable": +0.20, "verbose": -0.25},
    "persona":         {"acc": -0.03, "refuse_unanswerable": -0.25, "correct_premise": -0.20, "verbose": +0.35},
    "question_first":  {"acc": -0.04},
    "distractor":      {"acc": -0.15, "refuse_unanswerable": -0.10, "correct_premise": -0.10},
    "no_context":      {"acc": -0.80, "refuse_unanswerable": +0.10, "over_refuse": +0.55, "correct_premise": -0.3},
}

_CATEGORY_MODIFIERS = {  # some categories are harder for small models
    "arithmetic": -0.12,
    "false_premise": 0.0,
    "negation": -0.05,
    "comparison": -0.05,
    "instruction_following": +0.05,
    "counting": -0.03,
}

_REFUSALS = [
    "The text does not say.",
    "Not stated in the text.",
    "This information is not provided in the passage.",
    "I cannot determine that from the given text.",
]
_CHATTY_PREFIX = ["Sure! ", "Great question! ", "Happy to help. ", "Of course! "]
_CHATTY_SUFFIX = [" Let me know if you need anything else!", " Hope that helps!", ""]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def mock_chat(model: str, variant: str, question: Dict[str, Any], repeat: int,
              temperature: float) -> Dict[str, Any]:
    profile = dict(_PROFILES.get(model, _PROFILES["mock-medium"]))
    for k, v in _VARIANT_MODIFIERS.get(variant, {}).items():
        profile[k] = profile[k] + v
    profile["acc"] += _CATEGORY_MODIFIERS.get(question["category"], 0.0)
    profile["acc"] -= 0.06 * (question.get("difficulty", 1) - 1)

    key = f"{model}|{variant}|{question['id']}|{question.get('phrasing', 0)}|{repeat if temperature > 0 else 0}"
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))

    category = question["category"]
    if category == "unanswerable":
        correct = rng.random() < _clamp(profile["refuse_unanswerable"])
        text = rng.choice(_REFUSALS) if correct else question["plausible_wrong"]
    elif category == "false_premise":
        correct = rng.random() < _clamp(profile["correct_premise"])
        text = question["expected_response"] if correct else question["plausible_wrong"]
    elif rng.random() < _clamp(profile["over_refuse"]):
        text = rng.choice(_REFUSALS)
    else:
        correct = rng.random() < _clamp(profile["acc"])
        text = question["expected_response"] if correct else question["plausible_wrong"]

    verbose = profile["verbose"]
    if category == "instruction_following":      # stronger profiles obey format instructions more often
        verbose *= (1.0 - _clamp(profile["acc"]))
    chatty = rng.random() < _clamp(verbose)
    if variant == "cot":
        text = ("Step 1: Find the relevant sentence in the text.\n"
                "Step 2: The text says something relevant to the question.\n"
                "Step 3: Work out the answer from that sentence.\n"
                f"FINAL ANSWER: {text}")
    elif chatty:
        text = rng.choice(_CHATTY_PREFIX) + text + rng.choice(_CHATTY_SUFFIX)

    words = len(text.split())
    completion_tokens = int(words * 1.3) + 1
    tps = profile["speed"] * rng.uniform(0.85, 1.15)
    gen_s = completion_tokens / tps
    return {
        "content": text,
        "thinking": "",
        "prompt_tokens": 520 + rng.randint(-20, 20) + (150 if variant == "distractor" else 0) - (480 if variant == "no_context" else 0),
        "completion_tokens": completion_tokens,
        "latency_s": gen_s + rng.uniform(0.05, 0.15),
        "generation_s": gen_s,
        "load_s": 0.0,
        "tokens_per_s": tps,
        "done_reason": "stop",
    }
