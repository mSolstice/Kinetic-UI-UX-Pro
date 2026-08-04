#!/usr/bin/env python3
"""Manual-paste eval harness for Kinetic UI UX Pro."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.yaml"


def clean_value(value: str) -> str:
    value = value.strip()
    if value[:1] in ("'", '"') and value[-1:] == value[0]:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def parse_cases(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cases, cur, block_key, list_key, buf = [], None, None, None, []

    def flush_block() -> None:
        nonlocal block_key, buf
        if cur is not None and block_key:
            cur[block_key] = "\n".join(buf).rstrip()
        block_key, buf = None, []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "cases:":
            continue
        if line.startswith("  - id:"):
            flush_block()
            cur = {"id": line.split(":", 1)[1].strip()}
            cases.append(cur)
            list_key = None
            continue
        if cur is None:
            continue
        item = re.match(r"^      -\s*(.*)$", line)
        if item and list_key:
            cur[list_key].append(clean_value(item.group(1)))
            continue
        if block_key and (line.startswith("      ") or not stripped):
            buf.append(line[6:] if line.startswith("      ") else "")
            continue
        flush_block()
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", line)
        if m:
            name, value = m.groups()
            if value == "|":
                block_key = name
                list_key = None
                buf = []
            elif value == "":
                cur[name] = []
                list_key = name
            else:
                cur[name] = clean_value(value)
                list_key = None
            continue
    flush_block()
    return cases


def prompt_block(case: dict) -> str:
    refs = "\n".join(f"- {x}" for x in case["must_load"])
    scripts = "\n".join(f"- {x}" for x in case["must_run"])
    return f"""## {case['id']}

Paste into a fresh session:

```text
Use Kinetic UI UX Pro for this request.

{case['prompt']}
```

Expected reference loads:
{refs}

Expected script runs:
{scripts}
"""


def contains_all(text: str, needles: list[str]) -> tuple[bool, list[str]]:
    lower = text.lower()
    missing = [n for n in needles if n.lower() not in lower]
    return not missing, missing


def score_case(case: dict, result_dir: Path) -> dict:
    result_file = result_dir / f"{case['id']}.md"
    if not result_file.exists():
        return {"id": case["id"], "pass": False, "missing": ["response file"]}
    text = result_file.read_text(encoding="utf-8", errors="replace")
    checks = case["must_load"] + case["must_run"] + case["must_contain"]
    ok, missing = contains_all(text, checks)
    return {"id": case["id"], "pass": ok, "missing": missing}


def score(cases: list[dict], result_dir: Path) -> str:
    rows = score_rows(cases, result_dir)
    passed = sum(1 for row in rows if row["pass"])
    total = len(rows)
    rate = (passed / total * 100) if total else 0
    out = [
        "# Kinetic UI UX Pro Eval Scorecard",
        "",
        f"- **Result directory:** `{result_dir}`",
        f"- **Aggregate trigger rate:** {passed}/{total} ({rate:.1f}%)",
        "",
    ]
    return "\n".join(out + table(rows))


def table(rows: list[dict]) -> list[str]:
    out = ["| Case | Result | Missing |", "|---|---:|---|"]
    for row in rows:
        result = "PASS" if row["pass"] else "FAIL"
        missing = ", ".join(f"`{x}`" for x in row["missing"]) or "-"
        out.append(f"| `{row['id']}` | {result} | {missing} |")
    return out + [""]


def score_rows(cases: list[dict], result_dir: Path) -> list[dict]:
    if result_dir.is_file():
        wanted = result_dir.stem
        cases = [case for case in cases if case["id"] == wanted]
        if not cases:
            raise SystemExit(f"No case id matches response file: {wanted}")
        result_dir = result_dir.parent
    return [score_case(case, result_dir) for case in cases]


def read_rate(scorecard: Path) -> tuple[int, int]:
    text = scorecard.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Aggregate trigger rate:\*\*\s+(\d+)/(\d+)", text)
    if not m:
        raise SystemExit(f"Could not read aggregate rate from {scorecard}")
    return int(m.group(1)), int(m.group(2))


def compare_report(cases: list[dict], result_dir: Path, baseline: Path) -> str:
    rows = score_rows(cases, result_dir)
    passed = sum(1 for row in rows if row["pass"])
    total = len(rows)
    base_passed, base_total = read_rate(baseline)
    base_rate = (base_passed / base_total * 100) if base_total else 0
    rate = (passed / total * 100) if total else 0
    delta = rate - base_rate
    out = [
        "# Kinetic UI UX Pro Eval Comparison",
        "",
        f"- **Result directory:** `{result_dir}`",
        f"- **Baseline:** `{baseline}`",
        f"- **Baseline trigger rate:** {base_passed}/{base_total} ({base_rate:.1f}%)",
        f"- **Current trigger rate:** {passed}/{total} ({rate:.1f}%)",
        f"- **Delta:** {delta:+.1f} percentage points",
        "",
    ]
    return "\n".join(out + table(rows))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--list", action="store_true", help="print pasteable prompts")
    ap.add_argument("--score", help="directory containing <id>.md responses")
    ap.add_argument("--compare", help="baseline scorecard to compare against")
    ap.add_argument("--out", help="write markdown scorecard here")
    args = ap.parse_args()

    cases = parse_cases(Path(args.cases))
    if args.list:
        print("\n---\n".join(prompt_block(case) for case in cases))
        return 0
    if args.score:
        report = compare_report(cases, Path(args.score), Path(args.compare)) \
            if args.compare else score(cases, Path(args.score))
        if args.out:
            Path(args.out).write_text(report + "\n", encoding="utf-8")
        print(report)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
