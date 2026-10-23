#!/usr/bin/env python3
"""Activate your grocery-llm-eval license.

    python activate.py GLE1-....            # saves license.key in this folder
    python activate.py GLE1-.... --home     # saves to ~/.grocery-llm-eval/license.key (shared by all copies)
    python activate.py --status             # show the current license
    python activate.py --remove             # back to trial mode

The key is checked offline against the seller's public key; nothing is sent anywhere.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grocery_eval import license as lic  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if not args or "--status" in args:
        print(lic.banner())
        return 0
    if "--remove" in args:
        n = 0
        for p in (lic.LOCAL_PATH, lic.HOME_PATH):
            if os.path.exists(p):
                os.remove(p)
                n += 1
        print(f"Removed {n} license file(s). Now in trial mode.")
        return 0
    key = next((a for a in args if a.startswith(lic.PREFIX)), None)
    if not key:
        print("Please paste the key that starts with GLE1- (from your purchase email).")
        return 1
    r = lic.activate(key, "home" if "--home" in args else "project")
    if not r["ok"]:
        print("Activation failed:", r["error"])
        print("Check that you copied the whole key. If it still fails, email support with your order number.")
        return 1
    p = r["payload"]
    print(f"Activated. Licensed to {p['name']} <{p['email']}>, {p['plan']} plan, updates and support until {p['expires']}.")
    print(f"Saved to {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
