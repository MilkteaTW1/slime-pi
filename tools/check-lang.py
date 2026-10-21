#!/usr/bin/env python3
"""Check every locales/*.json against en.json: same keys, same {0} placeholders.

Usage: python tools/check-lang.py
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "locales")
PH = re.compile(r"\{\d+\}")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def walk(node, prefix=""):
    """Yield (path, value) for every string; list items are one path with the list itself."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{prefix}{k}.")
    else:
        yield prefix[:-1], node


def main():
    base = dict(walk(load(os.path.join(ROOT, "en.json"))))
    bad = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "*.json"))):
        name = os.path.basename(path)[:-5]
        if name == "en":
            continue
        other = dict(walk(load(path)))
        for key, val in base.items():
            if key.startswith("taste."):
                continue  # translators may add or skip file types
            if key not in other:
                print(f"{name}: missing {key}"); bad += 1
            elif isinstance(val, str):
                if sorted(PH.findall(val)) != sorted(PH.findall(other[key])):
                    print(f"{name}: placeholders differ in {key}"); bad += 1
            elif not (isinstance(other[key], list) and other[key] and all(isinstance(x, str) for x in other[key])):
                print(f"{name}: {key} must be a non-empty list of strings"); bad += 1
        for key in other:
            if key not in base and not key.startswith("taste."):
                print(f"{name}: unknown key {key}"); bad += 1
    print("languages OK" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
