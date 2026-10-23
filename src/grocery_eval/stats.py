"""Small, dependency-free statistics helpers used by the report."""

import math
import random
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def mean(xs: Sequence[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def median(xs: Sequence[float]) -> Optional[float]:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for a binomial proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def paired_bootstrap_ci(diffs_by_unit: Dict[str, float], n_boot: int = 2000, seed: int = 0,
                        alpha: float = 0.05) -> Tuple[float, float, float]:
    """Bootstrap CI for the mean of per-unit differences (units are resampled with replacement).

    Returns (mean_diff, ci_low, ci_high)."""
    units = list(diffs_by_unit.values())
    if not units:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    n = len(units)
    point = sum(units) / n
    samples = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += units[rng.randrange(n)]
        samples.append(s / n)
    samples.sort()
    lo = samples[int((alpha / 2) * n_boot)]
    hi = samples[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (point, lo, hi)


def exact_sign_test_p(b: int, c: int) -> Optional[float]:
    """Two-sided exact binomial (McNemar-style) p-value on discordant pairs.

    b = cases where A is right and B wrong, c = the reverse. Returns None when there are no
    discordant pairs."""
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def agreement_rate(answers: Iterable[str]) -> float:
    """Fraction of answers that equal the most common answer (1.0 = fully consistent)."""
    counts = Counter(a for a in answers)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return counts.most_common(1)[0][1] / total


def fmt_pct(x: Optional[float], digits: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}%"


def fmt_num(x: Optional[float], digits: int = 2) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"
