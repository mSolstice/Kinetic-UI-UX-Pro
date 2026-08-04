#!/usr/bin/env python3
"""Build a searchable design-system corpus."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KINDS = {"color", "space", "radius", "type", "motion", "shadow", "component", "prop"}
TOKEN_KIND_HINTS = {
    "color": ("color", "brand", "neutral", "surface", "text", "border", "bg", "foreground"),
    "space": ("space", "spacing", "gap", "padding", "margin", "inset"),
    "radius": ("radius", "radii", "rounded", "border-radius"),
    "type": ("type", "font", "text", "line-height", "letter", "leading"),
    "motion": ("motion", "duration", "ease", "easing", "transition", "animation"),
    "shadow": ("shadow", "elevation"),
}
CSS_VAR_RE = re.compile(r"(--[-\w]+)\s*:\s*([^;{}]+);")
THEME_RE = re.compile(r"@theme\s*\{(?P<body>.*?)\}", re.S)
EXPORT_RE = re.compile(
    r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]*)"
)
TYPE_PROPS_RE = re.compile(r"type\s+([A-Z][A-Za-z0-9_]*Props)\s*=\s*\{(?P<body>.*?)\}", re.S)
INTERFACE_PROPS_RE = re.compile(
    r"interface\s+([A-Z][A-Za-z0-9_]*Props)\s*(?:extends[^{]+)?\{(?P<body>.*?)\}", re.S
)
PROP_RE = re.compile(r"^\s*([A-Za-z_$][\w$-]*)\??\s*:", re.M)


def warn(path: Path, msg: str) -> None:
    print(f"ds_index: skipped {path}: {msg}", file=sys.stderr)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def kind_for(name: str, value: object = "") -> str:
    hay = f"{name} {value}".lower()
    if re.search(r"#(?:[0-9a-f]{3}){1,2}\b|oklch\(|rgb\(|hsl\(", hay):
        return "color"
    if re.search(r"\b\d+(?:ms|s)\b|cubic-bezier|spring|ease", hay):
        return "motion"
    if re.search(r"\b\d+(?:px|rem|em)\b", hay) and "radius" in hay:
        return "radius"
    if "shadow" in hay or "elevation" in hay or re.search(r"\b\d+px\s+\d+px", hay):
        return "shadow"
    for kind, hints in TOKEN_KIND_HINTS.items():
        if any(h in hay for h in hints):
            return kind
    return "type" if "font" in hay else "space"


def record(kind: str, name: str, value: object, source: Path, root: Path, aliases=None) -> dict:
    aliases = aliases or []
    value_s = "" if value is None else str(value)
    parts = [kind, name, value_s] + aliases
    return {
        "id": f"{rel(source, root)}::{kind}::{name}",
        "kind": kind if kind in KINDS else "space",
        "name": name,
        "value": value_s,
        "aliases": aliases,
        "source_file": rel(source, root),
        "text": " ".join(p for p in parts if p),
    }


def flatten_tokens(data: object, prefix=()):
    if isinstance(data, dict):
        if "value" in data:
            yield "-".join(prefix), data.get("value")
        elif all(k in data for k in ("oklch", "hex")):
            yield "-".join(prefix), data.get("oklch") or data.get("hex")
        else:
            for k, v in data.items():
                if not str(k).startswith("$"):
                    yield from flatten_tokens(v, prefix + (str(k),))
    elif isinstance(data, (str, int, float)):
        yield "-".join(prefix), data


def ingest_token_json(path: Path, root: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        warn(path, str(e))
        return []
    out = []
    if data.get("generatedBy") == "token_gen.py":
        for fam, ramp in data.get("primitives", {}).items():
            for step, token in ramp.items():
                out.append(record("color", f"{fam}-{step}", token.get("oklch"), path, root, [token.get("hex", "")]))
        for group in ("motion", "space", "radius"):
            for name, value in flatten_tokens(data.get(group, {})):
                out.append(record(kind_for(name, value), name, value, path, root))
    else:
        for name, value in flatten_tokens(data):
            if name:
                out.append(record(kind_for(name, value), name, value, path, root))
    return out


def ingest_css_vars(path: Path, root: Path, theme_only=False) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        warn(path, str(e))
        return []
    bodies = [m.group("body") for m in THEME_RE.finditer(text)] if theme_only else [text]
    out = []
    for body in bodies:
        for name, value in CSS_VAR_RE.findall(body):
            clean = name[2:] if name.startswith("--") else name
            out.append(record(kind_for(clean, value), clean, value.strip(), path, root, [name]))
    return out


def ingest_tailwind(path: Path, root: Path) -> list[dict]:
    out = ingest_css_vars(path, root, theme_only=True)
    if out:
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        warn(path, str(e))
        return []
    pairs = re.findall(r"['\"]?([\w-]+)['\"]?\s*:\s*['\"]([^'\"]+)['\"]", text)
    return [record(kind_for(n, v), n, v, path, root) for n, v in pairs]


def ingest_components(path: Path, root: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        warn(path, str(e))
        return []
    out = [record("component", name, "", path, root) for name in EXPORT_RE.findall(text)]
    for rx in (TYPE_PROPS_RE, INTERFACE_PROPS_RE):
        for m in rx.finditer(text):
            owner = m.group(1).removesuffix("Props")
            for prop in PROP_RE.findall(m.group("body")):
                out.append(record("prop", prop, owner, path, root, [f"{owner}.{prop}"]))
    return out


def collect(root: Path) -> list[dict]:
    records, seen = [], set()
    token_json = sorted(p for p in root.rglob("tokens.json") if ".ds-index" not in p.parts)
    json_tokens = sorted(p for p in root.rglob("*.json") if ".ds-index" not in p.parts and p not in token_json)
    tailwind = sorted(root.rglob("tailwind.config.js"))
    css = sorted(p for p in root.rglob("*.css") if ".ds-index" not in p.parts)
    tsx = sorted(p for p in root.rglob("*.tsx") if ".ds-index" not in p.parts)
    steps = [
        (token_json, ingest_token_json),
        (json_tokens, ingest_token_json),
        (tailwind, ingest_tailwind),
        (css, ingest_css_vars),
        (tsx, ingest_components),
    ]
    for paths, func in steps:
        for path in paths:
            for rec in func(path, root):
                key = (rec["kind"], rec["name"], rec["source_file"])
                if rec["kind"] in KINDS and key not in seen:
                    seen.add(key)
                    records.append(rec)
    return records


def write_jsonl(records: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", default=".", help="design-system root to index")
    ap.add_argument("--out", help="output JSONL path; defaults to <build>/.ds-index/corpus.jsonl")
    ap.add_argument("--stats", action="store_true", help="print counts per kind")
    args = ap.parse_args()
    root = Path(args.build).resolve()
    out = Path(args.out) if args.out else root / ".ds-index" / "corpus.jsonl"
    records = collect(root)
    write_jsonl(records, out)
    if args.stats:
        counts = Counter(r["kind"] for r in records)
        for kind in sorted(KINDS):
            if counts[kind]:
                print(f"{kind}: {counts[kind]}")
        print(f"total: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
