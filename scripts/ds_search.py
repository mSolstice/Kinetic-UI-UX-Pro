#!/usr/bin/env python3
"""Search and match code against a design-system corpus."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from color_tools import parse_color, to_hex  # noqa: E402

K1, B = 1.5, 0.75
NEAR_SCORE = 1.2
LENGTH_EPS = 0.01
COLOR_EPS = 0.6

CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
OKLCH_RE = re.compile(r"oklch\([^)]+\)", re.I)
RGB_RE = re.compile(r"rgba?\(\s*[\d.]+%?\s*,?\s*[\d.]+%?\s*,?\s*[\d.]+%?(?:\s*[,/]\s*[\d.]+%?)?\s*\)", re.I)
VAR_RE = re.compile(r"var\(--[-\w]+\)")
DECL_RE = re.compile(r"(?P<prop>[-\w]+)\s*:\s*(?P<value>[^;{}]+);")
TS_STYLE_RE = re.compile(r"(?P<prop>[A-Za-z][\w]*)\s*:\s*['\"](?P<value>[^'\"]+)['\"]")
LEN_RE = re.compile(r"(?<![-\w.])(-?\d*\.?\d+)(px|rem|em)(?![-\w])")
DUR_RE = re.compile(r"(?<![-\w.])(\d*\.?\d+)(ms|s)(?![-\w])")

KIND_PROPS = {
    "radius": ("radius",),
    "type": ("font-size",),
    "motion": ("duration", "transition", "animation"),
    "space": (
        "gap", "margin", "padding", "inset", "top", "right", "bottom", "left",
        "width", "height", "block-size", "inline-size", "min-height",
        "min-width", "max-height", "max-width",
    ),
}


def tokenize(text: str) -> list[str]:
    text = CAMEL_RE.sub(r"\1-\2", text.replace("_", "-")).lower()
    out = []
    for token in TOKEN_RE.findall(text):
        out.append(token)
        out.extend(p for p in token.split("-") if p and p != token)
    return out


def load_corpus(path: Path) -> list[dict]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise SystemExit(f"Index not found: {path}. Run scripts/ds_index.py first.")
    for i, line in enumerate(lines, 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"ds_search: skipped {path}:{i}: {e}", file=sys.stderr)
    return rows


class BM25:
    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.tokens = [tokenize(d.get("text", "")) for d in docs]
        self.avgdl = sum(len(t) for t in self.tokens) / len(self.tokens) if docs else 0
        self.df = Counter()
        for toks in self.tokens:
            self.df.update(set(toks))

    def score(self, query: str, i: int) -> float:
        q = tokenize(query)
        if not q or not self.docs:
            return 0.0
        tf = Counter(self.tokens[i])
        dl = len(self.tokens[i]) or 1
        total = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (len(self.docs) - self.df[term] + 0.5) / (self.df[term] + 0.5))
            total += idf * (tf[term] * (K1 + 1)) / (tf[term] + K1 * (1 - B + B * dl / (self.avgdl or 1)))
        return total

    def ranked(self, query: str, kind: str | None = None) -> list[tuple[float, dict]]:
        scores = []
        for i, doc in enumerate(self.docs):
            if kind and doc.get("kind") != kind:
                continue
            score = self.score(query, i)
            if score > 0:
                scores.append((score, doc))
        return sorted(scores, key=lambda x: (-x[0], x[1]["id"]))


def srgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(max(0.0, min(1.0, c))) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def delta_e(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) * 100


def parse_rgb(s: str):
    nums = re.findall(r"[\d.]+%?", s)
    if len(nums) < 3:
        raise ValueError(s)
    vals = []
    for n in nums[:3]:
        vals.append(float(n[:-1]) / 100 if n.endswith("%") else float(n) / 255)
    return tuple(vals)


def color_rgb(value: str):
    value = value.strip()
    if value.lower().startswith("rgb"):
        return parse_rgb(value)
    return parse_color(value)


def parse_color_candidate(value: str):
    for part in [value] + re.findall(r"#[0-9a-fA-F]{3,6}\b|oklch\([^)]+\)|rgba?\([^)]+\)", value, re.I):
        try:
            return color_rgb(part)
        except Exception:
            pass
    return None


def length_px(value: str):
    m = re.fullmatch(r"(-?\d*\.?\d+)(px|rem|em)", value.strip())
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2)
    return n if unit == "px" else n * 16


def duration_ms(value: str):
    m = re.fullmatch(r"(\d*\.?\d+)(ms|s)", value.strip())
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2) == "ms" else n * 1000


def token_value_number(doc: dict, kind: str):
    name = str(doc.get("name", "")).lower()
    if kind != "color" and any(x in name for x in ("hue", "chroma", "palette", "semantic")):
        return None
    vals = [doc.get("value", "")] + doc.get("aliases", [])
    for val in vals:
        if kind == "motion":
            got = duration_ms(str(val))
            if got is not None:
                return got
            if str(val).isdigit():
                return float(val)
        else:
            got = length_px(str(val))
            if got is not None:
                return got
            if str(val).isdigit():
                return float(val)
    return None


def color_tokens(corpus: list[dict]) -> list[tuple[dict, tuple[float, float, float], str]]:
    out = []
    for doc in corpus:
        if doc.get("kind") != "color":
            continue
        for val in [doc.get("value", "")] + doc.get("aliases", []):
            rgb = parse_color_candidate(str(val))
            if rgb:
                out.append((doc, srgb_to_oklab(rgb), to_hex(rgb)))
                break
    return out


def nearest_color(value: str, tokens):
    rgb = parse_color_candidate(value)
    if not rgb:
        return None
    lab = srgb_to_oklab(rgb)
    best = None
    for doc, t_lab, hexv in tokens:
        cur = (delta_e(lab, t_lab), doc, hexv)
        if best is None or cur[0] < best[0]:
            best = cur
    return best


def infer_kind(prop: str, value: str) -> str | None:
    prop = CAMEL_RE.sub(r"\1-\2", prop.replace("_", "-")).lower()
    if HEX_RE.search(value) or OKLCH_RE.search(value) or RGB_RE.search(value):
        return "color"
    for kind, props in KIND_PROPS.items():
        if any(p in prop for p in props):
            return kind
    return None


def extract_values(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = []
    for line_no, line in enumerate(text.splitlines(), 1):
        clean = re.sub(r"/\*.*?\*/", "", line)
        for prop, raw in DECL_RE.findall(clean):
            if prop.startswith("--") or VAR_RE.fullmatch(raw.strip()):
                continue
            scan_value(found, path, line_no, prop, raw)
        for prop, raw in TS_STYLE_RE.findall(clean):
            scan_value(found, path, line_no, prop, raw)
    return found


def scan_value(found: list[dict], path: Path, line: int, prop: str, raw: str) -> None:
    raw = raw.strip()
    norm_prop = CAMEL_RE.sub(r"\1-\2", prop.replace("_", "-")).lower()
    parts = []
    parts += HEX_RE.findall(raw) + OKLCH_RE.findall(raw) + RGB_RE.findall(raw)
    if "duration" in norm_prop or "transition" in norm_prop or "animation" in norm_prop:
        parts += [n + u for n, u in DUR_RE.findall(raw)]
    if "font-size" in norm_prop or any(p in norm_prop for p in KIND_PROPS["space"] + KIND_PROPS["radius"]):
        parts += [n + u for n, u in LEN_RE.findall(raw) if float(n) != 0]
    for value in dict.fromkeys(parts):
        kind = infer_kind(prop, value)
        if kind:
            found.append({"file": str(path), "line": line, "property": prop, "value": value, "kind": kind})


def best_value_token(item: dict, corpus: list[dict], bm25: BM25, c_tokens) -> tuple[str, dict | None, float, str]:
    kind, value, prop = item["kind"], item["value"], item["property"]
    ranked = bm25.ranked(f"{prop} {value}", kind)
    bm_score, bm_doc = ranked[0] if ranked else (0.0, None)
    if kind == "color":
        near = nearest_color(value, c_tokens)
        if near:
            de, doc, hexv = near
            if de <= COLOR_EPS:
                return "EXACT", doc, bm_score, f"deltaE={de:.2f} hex={hexv}"
            if de <= 8:
                return "NEAR", doc, bm_score, f"deltaE={de:.2f} hex={hexv}"
            return "UNMATCHED", doc, bm_score, f"nearest deltaE={de:.2f} hex={hexv}"
    target = token_value_number({"value": value, "aliases": []}, kind)
    best_doc, best_diff = None, math.inf
    for doc in corpus:
        if doc.get("kind") != kind:
            continue
        num = token_value_number(doc, kind)
        if target is not None and num is not None:
            diff = abs(target - num)
            if diff < best_diff:
                best_doc, best_diff = doc, diff
        if str(doc.get("value", "")).strip() == value or value in doc.get("aliases", []):
            return "EXACT", doc, bm_score, "value match"
    if best_doc and best_diff <= LENGTH_EPS:
        return "EXACT", best_doc, bm_score, "normalized value match"
    if best_doc and target is not None and best_diff <= max(4, abs(target) * 0.25):
        return "NEAR", best_doc, bm_score, f"nearest value diff={best_diff:.2f}px/ms"
    if target is not None:
        return "UNMATCHED", bm_doc, bm_score, "no approved token"
    if bm_doc and bm_score >= NEAR_SCORE:
        return "NEAR", bm_doc, bm_score, "BM25"
    return "UNMATCHED", bm_doc, bm_score, "no approved token"


def cmd_search(args) -> int:
    corpus = load_corpus(Path(args.index))
    bm25 = BM25(corpus)
    for score, doc in bm25.ranked(args.query, args.kind)[:args.top]:
        print(f"{score:7.3f} {doc['kind']:<9} {doc['name']:<28} {doc['value']} ({doc['source_file']})")
    return 0


def match_items(path: Path, corpus: list[dict]) -> tuple[list[str], int]:
    bm25, c_tokens = BM25(corpus), color_tokens(corpus)
    lines, unmatched = [], 0
    for item in extract_values(path):
        verdict, doc, score, note = best_value_token(item, corpus, bm25, c_tokens)
        if verdict == "UNMATCHED":
            unmatched += 1
        token = doc["name"] if doc else "-"
        lines.append(
            f"{path}:{item['line']} {item['kind']:<7} {item['value']:<18} "
            f"{verdict:<9} -> {token} score={score:.2f} {note}"
        )
    return lines, unmatched


def cmd_match(args) -> int:
    corpus = load_corpus(Path(args.index))
    lines, unmatched = match_items(Path(args.file), corpus)
    print("\n".join(lines) if lines else f"No hardcoded design values found in {args.file}")
    return 1 if unmatched else 0


def cmd_drift(args) -> int:
    corpus = load_corpus(Path(args.index))
    root = Path(args.dir)
    counts, examples = Counter(), defaultdict(list)
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".css", ".tsx", ".jsx", ".ts", ".js"} or ".ds-index" in path.parts:
            continue
        for item in extract_values(path):
            key = (item["kind"], item["value"])
            counts[key] += 1
            if len(examples[key]) < 3:
                examples[key].append(f"{path}:{item['line']}")
    if not counts:
        print(f"No hardcoded design values found under {root}")
        return 0
    bm25, c_tokens = BM25(corpus), color_tokens(corpus)
    for (kind, value), count in counts.most_common():
        item = {"kind": kind, "value": value, "property": kind}
        verdict, doc, score, note = best_value_token(item, corpus, bm25, c_tokens)
        token = doc["name"] if doc else "-"
        print(f"{count:4} {kind:<7} {value:<18} {verdict:<9} -> {token} score={score:.2f} {note}")
        print(f"     examples: {', '.join(examples[(kind, value)])}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", default=".ds-index/corpus.jsonl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--kind", choices=["color", "space", "radius", "type", "motion", "shadow", "component", "prop"])
    s.add_argument("--top", type=int, default=5)
    s.set_defaults(func=cmd_search)
    m = sub.add_parser("match")
    m.add_argument("file")
    m.set_defaults(func=cmd_match)
    d = sub.add_parser("drift")
    d.add_argument("dir")
    d.set_defaults(func=cmd_drift)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
