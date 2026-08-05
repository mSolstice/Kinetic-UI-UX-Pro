#!/usr/bin/env python3
"""Print and lightly check industry-specific UI rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULE_DIR = ROOT / "references" / "industries" / "rules"
CATEGORIES = (
    "trust",
    "error-cost",
    "density",
    "motion",
    "compliance-orientation",
    "terminology",
    "state-coverage",
)
STOPWORDS = {
    "about", "action", "after", "allows", "around", "before", "beside",
    "block", "causes", "changes", "check", "context", "critical", "data",
    "detect", "display", "does", "during", "every", "expose", "field",
    "final", "flow", "give", "given", "having", "hide", "hides", "keep",
    "label", "labels", "missing", "must", "near", "only", "path",
    "preserve", "primary", "provide", "required", "review", "show",
    "silent", "state", "states", "status", "step", "submit", "the",
    "this", "use", "user", "users", "value", "values", "view", "when",
    "where", "whether", "with", "without",
}
MOTION_RE = re.compile(
    r"framer-motion|motion/react|\\banimate[-A-Za-z]*\\b|@keyframes|transition|animation|"
    r"layoutId|useAnimate|AutoAnimate",
    re.I,
)
REDUCED_RE = re.compile(r"prefers-reduced-motion|useReducedMotion|matchMedia", re.I)
MOBILE_RE = re.compile(r"@media|@container|min-width|max-width|viewport|sm:|md:|lg:", re.I)
RECOVERY_RE = re.compile(r"recover|retry|undo|cancel|appeal|correction|resume|draft|restore|reversal", re.I)
REVIEW_RE = re.compile(r"review|confirm|confirmation|preview|summary|are you sure|before submit", re.I)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_rules(path: Path) -> tuple[str, list[dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"could not read {path}: {exc}")
    rules = data.get("rules", data if isinstance(data, list) else [])
    if not isinstance(rules, list):
        raise SystemExit(f"{path} does not contain a rules array")
    return data.get("disclaimer", ""), rules


def all_rule_files() -> list[Path]:
    return sorted(RULE_DIR.glob("*.json"))


def load_industry(industry: str) -> tuple[str, list[dict], Path]:
    wanted = slug(industry)
    path = RULE_DIR / f"{wanted}.json"
    if not path.exists():
        available = ", ".join(p.stem for p in all_rule_files())
        raise SystemExit(f"unknown industry '{industry}'. Available: {available}")
    disclaimer, rules = read_rules(path)
    return disclaimer, rules, path


def validate_rule(rule: dict, path: Path) -> list[str]:
    errors = []
    required = {
        "id", "industry", "category", "rule", "rationale",
        "failureMode", "detectable", "severity",
    }
    missing = required - set(rule)
    if missing:
        errors.append(f"{path}: {rule.get('id', '<missing id>')} missing {sorted(missing)}")
    if rule.get("category") not in CATEGORIES:
        errors.append(f"{path}: {rule.get('id')} invalid category {rule.get('category')}")
    if rule.get("severity") not in {"ERROR", "WARN", "INFO"}:
        errors.append(f"{path}: {rule.get('id')} invalid severity {rule.get('severity')}")
    if not isinstance(rule.get("detectable"), bool):
        errors.append(f"{path}: {rule.get('id')} detectable must be boolean")
    return errors


def command_count(_args) -> int:
    total = 0
    invalid = []
    print("| Industry | Rules |")
    print("| --- | ---: |")
    for path in all_rule_files():
        _disclaimer, rules = read_rules(path)
        total += len(rules)
        print(f"| {path.stem} | {len(rules)} |")
        for rule in rules:
            invalid.extend(validate_rule(rule, path))
    print(f"\nTotal rules: {total}")
    if invalid:
        print("\nInvalid rules:", file=sys.stderr)
        for line in invalid:
            print(f"- {line}", file=sys.stderr)
        return 1
    return 0 if total >= 180 else 1


def tokens(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
        if t not in STOPWORDS and len(t) >= 4
    ]


def strongest_terms(rule: dict) -> list[str]:
    raw = tokens(rule["rule"] + " " + rule["failureMode"])
    keep = []
    for token in raw:
        if token not in keep:
            keep.append(token)
    return keep[:12]


def heuristic(rule: dict, text: str, suffix: str) -> tuple[str, str]:
    if suffix not in {".tsx", ".jsx", ".ts", ".js", ".css", ".scss", ".html", ".md"}:
        return "needs-review", "unsupported file type"
    lower = text.lower()
    category = rule["category"]
    rule_text = rule["rule"].lower()
    if category == "motion":
        has_motion = bool(MOTION_RE.search(text))
        has_reduced = bool(REDUCED_RE.search(text))
        if "do not use decorative motion" in rule_text:
            return ("fail", "motion primitives found") if has_motion else ("pass", "no obvious motion primitives")
        if "reduced-motion" in rule_text:
            if has_reduced:
                return "pass", "reduced-motion branch found"
            if has_motion:
                return "fail", "motion found without reduced-motion branch"
            return "needs-review", "no motion found to exercise this rule"
    if category == "density" and "mobile" in rule_text:
        return ("pass", "responsive rule or breakpoint found") if MOBILE_RE.search(text) else ("needs-review", "mobile visibility needs rendered review")
    if category == "error-cost" and "review" in rule_text:
        return ("pass", "review/confirmation copy found") if REVIEW_RE.search(text) else ("fail", "no review/confirmation language found")
    if category == "error-cost" and "recovery" in rule_text:
        return ("pass", "recovery language found") if RECOVERY_RE.search(text) else ("fail", "no recovery path language found")
    terms = strongest_terms(rule)
    hits = [term for term in terms if term in lower]
    if len(hits) >= min(3, len(terms)):
        return "pass", "matched terms: " + ", ".join(hits[:6])
    if len(hits) == 0:
        return "fail", "missing terms: " + ", ".join(terms[:6])
    return "needs-review", "partial terms: " + ", ".join(hits[:6])


def command_check(args) -> int:
    disclaimer, rules, _path = load_industry(args.industry)
    target = Path(args.target)
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise SystemExit(f"could not read {target}: {exc}")
    grouped = defaultdict(list)
    for rule in rules:
        grouped[rule["category"]].append(rule)
    if disclaimer:
        print(disclaimer)
        print()
    failures = 0
    print(f"# Industry Check: {slug(args.industry)}")
    print(f"Target: {target}\n")
    for category in CATEGORIES:
        items = grouped.get(category)
        if not items:
            continue
        print(f"## {category}")
        for rule in items:
            if rule["detectable"]:
                verdict, note = heuristic(rule, text, target.suffix)
                if verdict == "fail" and rule["severity"] in {"ERROR", "WARN"}:
                    failures += 1
                print(f"- [{verdict.upper()}] {rule['id']} {rule['severity']}: {rule['rule']}")
                print(f"  Heuristic: {note}")
            else:
                print(f"- [MANUAL] {rule['id']} {rule['severity']}: {rule['rule']}")
                print(f"  Review: {rule['rationale']}")
            print(f"  Failure mode: {rule['failureMode']}")
        print()
    return 1 if failures and args.fail_on_findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", action="store_true", help="print rule counts and validate shape")
    parser.add_argument("--fail-on-findings", action="store_true", help="exit non-zero on detectable WARN/ERROR failures")
    parser.add_argument("industry", nargs="?")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args()
    if args.count:
        return command_count(args)
    if not args.industry or not args.target:
        parser.error("provide <industry> <target>, or use --count")
    return command_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
