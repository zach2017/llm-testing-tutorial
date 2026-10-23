"""License key verification and activation (offline, no dependencies).

Key format: GLE1-<base64url(JSON payload)>.<base64url(Ed25519 signature)>  (issued by license/licensetool).
Verification uses a small pure-Python Ed25519 implementation (RFC 8032) against the seller's
public key below. The private key never leaves the seller; a customer cannot forge a key, but a
key can be copied - this is a convenience gate, not DRM (see docs/GO_TO_MARKET.md).

Where the key is stored after `python activate.py <KEY>`:
  1. the file  license.key  in the project folder (checked first), or
  2. ~/.grocery-llm-eval/license.key, or
  3. the environment variable GROCERY_LICENSE
"""

import base64
import datetime as _dt
import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

# Must match license/main.go, server/license.go and web/license.js.
PUBLIC_KEY_HEX = "cdfee672299ee1b13ea0718511fdeb50aaf06d07daba24fecc44c6d75c080a01"
PREFIX = "GLE1-"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_PATH = os.path.join(HERE, "license.key")
HOME_PATH = os.path.join(os.path.expanduser("~"), ".grocery-llm-eval", "license.key")

# ----------------------------------------------------------------------------- Ed25519 (RFC 8032)
_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = (x * _I) % _P
    if x % 2 != 0:
        x = _P - x
    return x


_BY = 4 * pow(5, _P - 2, _P) % _P
_BX = _xrecover(_BY)
_B = (_BX, _BY, 1, (_BX * _BY) % _P)  # extended coordinates


def _add(p, q):
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = t1 * 2 * _D * t2 % _P
    d = z1 * 2 * z2 % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(p, e: int):
    q = (0, 1, 1, 0)
    while e > 0:
        if e & 1:
            q = _add(q, p)
        p = _add(p, p)
        e >>= 1
    return q


def _decode_point(s: bytes):
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != (s[31] >> 7):
        x = _P - x
    pt = (x, y, 1, (x * y) % _P)
    # on-curve check: -x^2 + y^2 = 1 + d x^2 y^2
    if (-x * x + y * y - 1 - _D * x * x * y * y) % _P != 0:
        raise ValueError("point not on curve")
    return pt


def _equal(p, q) -> bool:
    x1, y1, z1, _ = p
    x2, y2, z2, _ = q
    return (x1 * z2 - x2 * z1) % _P == 0 and (y1 * z2 - y2 * z1) % _P == 0


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(public_key) != 32 or len(signature) != 64:
        return False
    try:
        a = _decode_point(public_key)
        r = _decode_point(signature[:32])
    except ValueError:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(_sha512(signature[:32] + public_key + message), "little") % _L
    return _equal(_mul(_B, s), _add(r, _mul(a, h)))


# ----------------------------------------------------------------------------- keys
def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_key(key: str, public_key_hex: str = PUBLIC_KEY_HEX) -> Tuple[Optional[Dict[str, Any]], str]:
    """Returns (payload, '') if valid, else (None, reason)."""
    key = (key or "").strip()
    if not key.startswith(PREFIX):
        return None, f"key must start with {PREFIX}"
    parts = key[len(PREFIX):].split(".")
    if len(parts) != 2:
        return None, "key has wrong shape"
    try:
        body, sig = _unb64(parts[0]), _unb64(parts[1])
        pub = bytes.fromhex(public_key_hex)
    except Exception:
        return None, "key is not valid base64"
    if not ed25519_verify(pub, body, sig):
        return None, "signature does not match: key was altered or issued for a different product"
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None, "payload is not valid JSON"
    return payload, ""


def stored_key() -> Optional[str]:
    for p in (LOCAL_PATH, HOME_PATH):
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
    return os.environ.get("GROCERY_LICENSE") or None


def status() -> Dict[str, Any]:
    """{'licensed': bool, 'payload': {...} or None, 'reason': str, 'updates_expired': bool}"""
    key = stored_key()
    if not key:
        return {"licensed": False, "payload": None, "reason": "no license key found (trial mode)", "updates_expired": False}
    payload, reason = verify_key(key)
    if payload is None:
        return {"licensed": False, "payload": None, "reason": reason, "updates_expired": False}
    expired = False
    try:
        expired = _dt.date.fromisoformat(payload.get("expires", "9999-12-31")) < _dt.date.today()
    except ValueError:
        pass
    return {"licensed": True, "payload": payload, "reason": "", "updates_expired": expired}


def activate(key: str, where: str = "project") -> Dict[str, Any]:
    payload, reason = verify_key(key)
    if payload is None:
        return {"ok": False, "error": reason}
    path = LOCAL_PATH if where == "project" else HOME_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key.strip() + "\n")
    return {"ok": True, "payload": payload, "path": path}


def banner() -> str:
    s = status()
    if s["licensed"]:
        p = s["payload"]
        note = " (updates/support period ended; software keeps working)" if s["updates_expired"] else ""
        return f"Licensed to {p.get('name')} <{p.get('email')}> - {p.get('plan')} plan, updates until {p.get('expires')}{note}"
    return f"TRIAL MODE - {s['reason']}. Trial limits: starter questions and baseline style only; exports are watermarked. Activate: python activate.py <KEY>"


# Trial limits shared by run_eval.py and ask.py
TRIAL_QUESTIONS = ["Q01", "Q05", "Q15", "Q28", "Q31", "Q36"]
TRIAL_VARIANTS = ["baseline"]
