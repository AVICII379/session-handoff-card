#!/usr/bin/env python3
"""Check that the five-domain handoff benchmark is complete and internally consistent."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "benchmarks" / "sources"
TRUTH = ROOT / "benchmarks" / "ground-truth"
EXPECTED = {"coding", "research", "writing", "browser", "planning"}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdio()
    errors: list[str] = []
    domains = {path.stem for path in TRUTH.glob("*.json")}
    if domains != EXPECTED:
        errors.append(f"benchmark domains mismatch: {sorted(domains)}")
    profiles: dict[str, str] = {}
    for domain in sorted(EXPECTED):
        source_path = SOURCES / f"{domain}.md"
        truth_path = TRUTH / f"{domain}.json"
        if not source_path.is_file() or not truth_path.is_file():
            errors.append(f"missing source or truth for {domain}")
            continue
        source = source_path.read_text(encoding="utf-8")
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        profiles[domain] = truth.get("recommended_profile", "")
        for key in ("domain", "recommended_profile", "must_preserve", "must_not_revive", "next_action", "stop_condition"):
            if not truth.get(key):
                errors.append(f"{domain}: missing {key}")
        if truth.get("domain") != domain:
            errors.append(f"{domain}: domain field mismatch")
        if truth.get("recommended_profile") not in {"QUICK", "VERIFIED"}:
            errors.append(f"{domain}: invalid profile")
        for item in truth.get("must_preserve", []) + truth.get("must_not_revive", []):
            if item.casefold() not in source.casefold():
                errors.append(f"{domain}: source does not contain ground-truth phrase")
        if truth.get("next_action", "").casefold() not in source.casefold():
            errors.append(f"{domain}: next action missing from source")
        if truth.get("stop_condition", "").casefold() not in source.casefold():
            errors.append(f"{domain}: stop condition missing from source")
    result = {"ok": not errors, "domains": sorted(domains), "profiles": profiles, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
