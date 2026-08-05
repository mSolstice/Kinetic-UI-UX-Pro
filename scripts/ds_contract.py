#!/usr/bin/env python3
"""Manage a persistent per-project Kinetic design contract."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_PATH = Path("design-system") / "contract.json"
TOKEN_CANDIDATES = (
    "design-system/tokens.css",
    "design-system/tokens.native.ts",
    "design-system/tokens.json",
    "tokens.css",
    "tokens.native.ts",
    "tokens.json",
    "templates/tokens.css",
    "templates/tokens.schema.json",
)
CONFIG_CANDIDATES = (
    "package.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "vite.config.ts",
    "next.config.js",
    "app.json",
    "app.config.js",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except Exception as e:
        raise SystemExit(f"could not read {path}: {e}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_project_name(root: Path) -> str:
    package = read_json(root / "package.json", {})
    if isinstance(package, dict) and package.get("name"):
        return str(package["name"])
    return root.name


def infer_surfaces(root: Path) -> list[str]:
    skip = {".git", "node_modules", ".venv", "dist", "build", "out", ".registry"}
    names = []
    for p in root.rglob("*"):
        if any(part in skip for part in p.parts):
            continue
        if p.is_file():
            names.append(p.name.lower())
    names = " ".join(names)
    surfaces = []
    for label, needles in {
        "dashboard": ("dashboard", "metric", "chart"),
        "settings": ("settings", "preferences"),
        "wizard": ("wizard", "onboarding", "stepper", "checkout"),
        "editor": ("editor", "canvas", "builder"),
        "mobile": ("react-native", ".native.", "expo", "app.json"),
    }.items():
        if any(n in names for n in needles):
            surfaces.append(label)
    return surfaces


def infer_token_ref(root: Path) -> dict:
    for raw in TOKEN_CANDIDATES:
        path = root / raw
        if path.exists() and path.is_file():
            return {"path": raw, "sha256": sha256(path), "lastValidatedAt": now_iso()}
    return {"path": "", "sha256": "", "lastValidatedAt": ""}


def infer_open_questions(root: Path) -> list[str]:
    questions = []
    if not any((root / p).exists() for p in TOKEN_CANDIDATES):
        questions.append("Where should generated design tokens live?")
    if not any((root / p).exists() for p in CONFIG_CANDIDATES):
        questions.append("Which app framework and build target does this project use?")
    return questions


def empty_contract(root: Path) -> dict:
    return {
        "project": {
            "name": infer_project_name(root),
            "surfaceTypes": infer_surfaces(root),
            "industryPack": "",
        },
        "decisions": {},
        "tokens": infer_token_ref(root),
        "components": [],
        "rejected": [],
        "openQuestions": infer_open_questions(root),
    }


def load_contract(root: Path) -> dict:
    data = read_json(root / CONTRACT_PATH)
    if data is None:
        raise SystemExit(f"contract not found: {CONTRACT_PATH}. Run init first.")
    return data


def compact(value, width=84) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= width else text[: width - 3] + "..."


def cmd_init(args) -> None:
    root = Path.cwd()
    path = root / CONTRACT_PATH
    if path.exists() and not args.force:
        raise SystemExit(f"contract already exists: {CONTRACT_PATH}; use --force to replace scaffold")
    contract = empty_contract(root)
    write_json(path, contract)
    print(f"wrote {CONTRACT_PATH}")


def cmd_read(args) -> None:
    c = load_contract(Path.cwd())
    lines = []
    project = c.get("project", {})
    lines.append(f"Project: {project.get('name', '')}")
    surfaces = ", ".join(project.get("surfaceTypes") or []) or "unset"
    lines.append(f"Surfaces: {surfaces}")
    if project.get("industryPack"):
        lines.append(f"Industry: {project['industryPack']}")
    tokens = c.get("tokens", {})
    if tokens.get("path"):
        lines.append(f"Tokens: {tokens.get('path')} ({str(tokens.get('sha256', ''))[:12]})")
    decisions = c.get("decisions", {})
    if decisions:
        lines.append("Decisions:")
        for key in sorted(decisions):
            d = decisions[key]
            lines.append(f"- {key}: {compact(d.get('value', ''))} - {compact(d.get('rationale', ''), 54)}")
    rejected = c.get("rejected", [])
    if rejected:
        lines.append("Rejected:")
        for item in rejected[-5:]:
            lines.append(f"- {compact(item.get('thing', ''))}: {compact(item.get('reason', ''), 60)}")
    components = c.get("components", [])
    if components:
        lines.append(f"Components: {len(components)} recorded")
        for item in components[-5:]:
            src = item.get("sourceLibrary") or "authored"
            lines.append(f"- {item.get('name', 'unnamed')} ({src})")
    questions = c.get("openQuestions", [])
    if questions:
        lines.append("Open questions:")
        for q in questions[:8]:
            lines.append(f"- {compact(q)}")
    for line in lines[:39]:
        print(line)
    if len(lines) > 39:
        print(f"... {len(lines) - 39} more line(s) omitted")


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def cmd_record(args) -> None:
    root = Path.cwd()
    c = load_contract(root)
    decisions = c.setdefault("decisions", {})
    existing = decisions.get(args.key)
    entry = {
        "value": parse_value(args.value),
        "rationale": args.rationale,
        "decidedAt": now_iso(),
    }
    if existing and not args.supersede:
        raise SystemExit(f"decision '{args.key}' already exists; use --supersede to change it")
    if existing:
        history = list(existing.get("history", []))
        previous = {k: v for k, v in existing.items() if k != "history"}
        history.append(previous)
        entry["history"] = history
    decisions[args.key] = entry
    write_json(root / CONTRACT_PATH, c)
    print(f"recorded decision {args.key}")


def cmd_reject(args) -> None:
    root = Path.cwd()
    c = load_contract(root)
    c.setdefault("rejected", []).append({
        "thing": args.thing,
        "reason": args.reason,
        "rejectedAt": now_iso(),
    })
    write_json(root / CONTRACT_PATH, c)
    print(f"recorded rejection {args.thing}")


def git_head_contract() -> str:
    try:
        got = subprocess.run(
            ["git", "show", f"HEAD:{CONTRACT_PATH.as_posix()}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        return ""
    return got.stdout if got.returncode == 0 else ""


def cmd_diff(args) -> None:
    path = Path.cwd() / CONTRACT_PATH
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    previous = git_head_contract()
    if not previous and not current:
        raise SystemExit(f"contract not found: {CONTRACT_PATH}")
    if previous == current:
        print("no contract changes since last commit")
        return
    diff = difflib.unified_diff(
        previous.splitlines(),
        current.splitlines(),
        fromfile=f"HEAD:{CONTRACT_PATH.as_posix()}",
        tofile=CONTRACT_PATH.as_posix(),
        lineterm="",
    )
    print("\n".join(diff))


def cmd_validate(args) -> None:
    root = Path.cwd()
    c = load_contract(root)
    errors = []
    for key in ("project", "decisions", "tokens", "components", "rejected", "openQuestions"):
        if key not in c:
            errors.append(f"missing top-level key: {key}")
    tokens = c.get("tokens", {})
    token_path = tokens.get("path")
    if token_path:
        path = root / token_path
        if not path.exists():
            errors.append(f"token file missing: {token_path}")
        else:
            current_hash = sha256(path)
            expected = tokens.get("sha256")
            if expected and current_hash != expected:
                errors.append(
                    f"token drift: {token_path} hash {current_hash[:12]} != recorded {expected[:12]}"
                )
    else:
        print("tokens: no generated token file recorded")
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        raise SystemExit(1)
    print("contract valid")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="scaffold design-system/contract.json")
    init.add_argument("--force", action="store_true", help="replace an existing scaffold")
    init.set_defaults(func=cmd_init)

    read = sub.add_parser("read", help="print a compact contract summary")
    read.set_defaults(func=cmd_read)

    record = sub.add_parser("record", help="record a design decision")
    record.add_argument("key")
    record.add_argument("value")
    record.add_argument("--rationale", required=True)
    record.add_argument("--supersede", action="store_true")
    record.set_defaults(func=cmd_record)

    reject = sub.add_parser("reject", help="record a rejected direction")
    reject.add_argument("thing")
    reject.add_argument("--reason", required=True)
    reject.set_defaults(func=cmd_reject)

    diff = sub.add_parser("diff", help="show contract changes since HEAD")
    diff.set_defaults(func=cmd_diff)

    validate = sub.add_parser("validate", help="validate token hash and structure")
    validate.set_defaults(func=cmd_validate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
