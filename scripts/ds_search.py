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
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_INDEX = ".registry/components.jsonl"
ADAPTER_DIR = ROOT / "templates" / "adapters"
STYLE_DIR = ROOT / "templates" / "styles"
INDUSTRY_DIR = ROOT / "references" / "industries"
LICENSE_ALLOWLISTS = {
    "mit-only": {"MIT"},
    "permissive": {"MIT", "Apache-2.0", "ISC", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0"},
}

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


def load_jsonl(path: Path, missing_hint: str) -> list[dict]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise SystemExit(missing_hint)
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
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


def slug(value: str) -> str:
    value = CAMEL_RE.sub(r"\1-\2", str(value).replace("_", "-"))
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()


def token_overlap(a: str, b: str) -> bool:
    at, bt = set(tokenize(a)), set(tokenize(b))
    return bool(at and bt and (at <= bt or bt <= at or at & bt))


def load_adapters(adapter_dir: Path = ADAPTER_DIR) -> dict[str, dict]:
    adapters = {}
    for path in sorted(adapter_dir.glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ds_search: skipped adapter {path}: {e}", file=sys.stderr)
            continue
        key = path.stem
        data["_id"] = key
        adapters[key] = data
        adapters[slug(data.get("library", key))] = data
    return adapters


def adapter_for(record: dict, adapters: dict[str, dict]) -> dict:
    library = record.get("library", "")
    return adapters.get(slug(library), {"_id": slug(library), "library": library, "stateGaps": [], "avoidFor": []})


def load_style(style_id: str | None) -> dict:
    if not style_id:
        return {}
    path = STYLE_DIR / f"{slug(style_id)}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ds_search: style {style_id} unavailable: {e}", file=sys.stderr)
        return {}


def load_industry(industry_id: str | None, query: str, surface: str) -> tuple[str, str, float]:
    packs = []
    for path in sorted(INDUSTRY_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        packs.append({"id": path.stem, "text": f"{path.stem} {text}"})
    if not packs:
        return "", "", 0.0
    if industry_id:
        for pack in packs:
            if pack["id"] == slug(industry_id):
                return pack["id"], pack["text"], 999.0
    ranked = BM25(packs).ranked(f"{query} {surface}")
    if not ranked or ranked[0][0] < 1.0:
        return "", "", 0.0
    score, pack = ranked[0]
    return pack["id"], pack["text"], score


def industry_motion_budget(industry_text: str) -> str:
    m = re.search(r"## Motion Budget\s+(.+?)(?=\n## |\Z)", industry_text, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else ""


def registry_text(record: dict) -> str:
    return " ".join([
        str(record.get("name", "")),
        str(record.get("description", "")),
        str(record.get("category", "")),
        str(record.get("library", "")),
        " ".join(str(x) for x in record.get("tags", [])),
    ])


def animation_heavy(record: dict, adapter: dict) -> bool:
    haystack = " ".join([
        record.get("library", ""),
        record.get("name", ""),
        record.get("description", ""),
        record.get("category", ""),
        " ".join(record.get("tags", [])),
        " ".join(adapter.get("avoidFor", [])),
    ]).lower()
    return bool(re.search(r"\b(animation|animated|motion|gesture|marquee|sparkle|orbit|beam|effect|transition)\b", haystack))


def surface_excluded(avoid_for: list[str], surface: str) -> str:
    surface_slug = slug(surface)
    for item in avoid_for:
        item_slug = slug(item)
        if item_slug == surface_slug or item_slug.startswith(f"{surface_slug}-") or surface_slug.startswith(f"{item_slug}-"):
            return item
    return ""


def style_library_conflict(style: dict, record: dict, adapter: dict, surface: str) -> str:
    if not style:
        return ""
    blocked_surface = surface_excluded(style.get("avoidFor", []), surface)
    if blocked_surface:
        return f"style avoids surface {blocked_surface}"
    style_text = " ".join(style.get("avoidFor", []) + style.get("prohibitions", [])).lower()
    if animation_heavy(record, adapter) and (
        "no-expressive-animation-libraries" in style_text
        or "decorative motion" in style_text
        or "animation" in style_text
    ):
        return "style prohibits expressive animation libraries"
    library_slug = slug(record.get("library", ""))
    adapter_slug = slug(adapter.get("_id", ""))
    style_slugs = {slug(item) for item in style.get("avoidFor", []) + style.get("prohibitions", [])}
    if library_slug in style_slugs or adapter_slug in style_slugs:
        return "style explicitly avoids this library"
    return ""


def motion_decision(record: dict, adapter: dict, surface: str, industry_id: str, industry_text: str) -> tuple[float, str, bool]:
    if not animation_heavy(record, adapter):
        return 0.0, "component is not animation-heavy", False
    motion = industry_motion_budget(industry_text)
    surface_tokens = set(tokenize(surface))
    if industry_id == "healthcare" and "form" in surface_tokens:
        return -999.0, "healthcare forms must not offer animation-heavy components", True
    if "dashboard" in surface_tokens or "near-zero" in motion or "very low" in motion:
        return -1.5, "animation-heavy component down-ranked for low-motion surface", False
    if "low" in motion:
        return -0.75, "animation-heavy component down-ranked for low motion budget", False
    return -0.25, "animation-heavy component lightly down-ranked", False


def component_docs_url(record: dict) -> str:
    return record.get("docs_url") or record.get("registry_url") or ""


def fetch_command(record: dict, adapter: dict) -> str:
    sync_id = adapter.get("_id") or slug(record.get("library", ""))
    url = component_docs_url(record)
    suffix = f"  # docs: {url}" if url else ""
    return f"python scripts/registry_sync.py --sync {sync_id}{suffix}"


def rank_components(args, records: list[dict], adapters: dict[str, dict]) -> tuple[list[dict], list[dict], dict]:
    style = load_style(args.style)
    industry_id, industry_text, industry_score = load_industry(getattr(args, "industry", None), args.query, args.surface)
    docs = [{"id": r.get("id", ""), "text": registry_text(r), "record": r} for r in records]
    bm25 = BM25(docs)
    allow = LICENSE_ALLOWLISTS[args.license]
    ranked = []
    blocked = []
    for i, doc in enumerate(docs):
        record = doc["record"]
        adapter = adapter_for(record, adapters)
        bm_score = bm25.score(args.query, i)
        if bm_score <= 0:
            continue
        reasons = []
        penalties = []
        license_id = record.get("license") or adapter.get("license", "")
        if license_id not in allow:
            blocked.append({"record": record, "blocked": f"license {license_id} outside {args.license}", "score": bm_score})
            continue
        if args.framework:
            frameworks = set(tokenize(" ".join(adapter.get("frameworks", [])) + " " + record.get("framework", "")))
            wanted = set(tokenize(args.framework))
            if wanted and not frameworks.intersection(wanted):
                blocked.append({"record": record, "blocked": f"framework does not include {args.framework}", "score": bm_score})
                continue
        adapter_penalty = 0.0
        adapter_block = surface_excluded(adapter.get("avoidFor", []), args.surface)
        if adapter_block and "dashboard" in set(tokenize(args.surface)) and animation_heavy(record, adapter):
            adapter_penalty = -1.0
            penalties.append(f"library adapter discourages {adapter_block}")
        elif adapter_block:
            blocked.append({"record": record, "blocked": f"library adapter avoids {adapter_block}", "score": bm_score})
            continue
        style_block = style_library_conflict(style, record, adapter, args.surface)
        if style_block:
            blocked.append({"record": record, "blocked": style_block, "score": bm_score})
            continue
        motion_penalty, motion_reason, motion_block = motion_decision(record, adapter, args.surface, industry_id, industry_text)
        if motion_block:
            blocked.append({"record": record, "blocked": motion_reason, "score": bm_score})
            continue
        if motion_penalty:
            penalties.append(motion_reason)
        final = bm_score + motion_penalty + adapter_penalty
        tags = ", ".join(record.get("tags", [])[:3])
        reasons.append(f"matched {record.get('name')} / {record.get('category', 'component')}")
        if tags:
            reasons.append(f"tags: {tags}")
        ranked.append({
            "record": record,
            "adapter": adapter,
            "bm25": bm_score,
            "motionPenalty": motion_penalty,
            "adapterPenalty": adapter_penalty,
            "final": final,
            "reasons": reasons,
            "penalties": penalties,
            "license": license_id,
            "industry": industry_id,
            "industryScore": industry_score,
        })
    ranked.sort(key=lambda x: (-x["final"], x["record"].get("id", "")))
    context = {"style": style, "industry_id": industry_id, "industry_text": industry_text}
    return ranked, blocked, context


def print_component_result(item: dict) -> None:
    record, adapter = item["record"], item["adapter"]
    gaps = record.get("stateGaps") or adapter.get("stateGaps", [])
    reason = "; ".join(item["reasons"][:2])
    if item["penalties"]:
        reason += f"; {item['penalties'][0]}"
    print(f"### {record.get('name')} ({record.get('id')})")
    print(f"- Component: {record.get('name')}")
    print(f"- Library: {record.get('library')} ({record.get('framework', adapter.get('frameworks', [''])[0])})")
    print(f"- License: {item['license']}")
    print(f"- Reason: {reason}")
    print(f"- Known state gaps: {', '.join(gaps) if gaps else 'none recorded'}")
    print(f"- Fetch command: `{fetch_command(record, adapter)}`")


def tradeoffs_line(results: list[dict]) -> str:
    if len(results) < 2:
        return "Tradeoffs: only one strong result remained after filters, so there is no meaningful runner-up comparison."
    first, second = results[0], results[1]
    f, s = first["record"], second["record"]
    first_penalty = "less motion risk" if first["motionPenalty"] >= second["motionPenalty"] else "stronger text match"
    second_advantage = "broader interaction coverage" if len(second["adapter"].get("stateGaps", [])) < len(first["adapter"].get("stateGaps", [])) else "a different implementation shape"
    return (
        f"Tradeoffs: {f.get('name')} ranks above {s.get('name')} on {first_penalty}; "
        f"{s.get('name')} may still win if you prefer {second_advantage}."
    )


def cmd_component(args) -> int:
    records = load_jsonl(
        Path(args.registry_index),
        f"Registry index not found: {args.registry_index}. Run scripts/registry_sync.py --sync-all first.",
    )
    adapters = load_adapters()
    ranked, blocked, context = rank_components(args, records, adapters)
    if args.why:
        target = next((r for r in ranked if r["record"].get("id") == args.why), None)
        blocked_target = next((r for r in blocked if r["record"].get("id") == args.why), None)
        if not target and not blocked_target:
            print(f"No ranked or filtered component found for id {args.why}")
            return 1
        if blocked_target:
            print(f"{args.why}: filtered out")
            print(f"- BM25: {blocked_target['score']:.3f}")
            print(f"- Reason: {blocked_target['blocked']}")
            return 0
        record, adapter = target["record"], target["adapter"]
        print(f"{record.get('id')}: ranking breakdown")
        print(f"- BM25: {target['bm25']:.3f}")
        print(f"- Motion penalty: {target['motionPenalty']:.3f}")
        print(f"- Final score: {target['final']:.3f}")
        print(f"- License filter: {target['license']} allowed by {args.license}")
        print(f"- Style: {context['style'].get('id', args.style or 'none')}")
        print(f"- Surface: {args.surface}")
        print(f"- Industry: {target['industry'] or 'not detected'}")
        print(f"- Known state gaps: {', '.join(record.get('stateGaps') or adapter.get('stateGaps', [])) or 'none recorded'}")
        print(f"- Fetch command: `{fetch_command(record, adapter)}`")
        if target["penalties"]:
            print(f"- Penalties: {'; '.join(target['penalties'])}")
        return 0

    top = ranked[:max(1, min(args.top, 5))]
    if not top:
        print("No component matches remained after filters.")
        if blocked:
            print(f"Closest filtered result: {blocked[0]['record'].get('id')} — {blocked[0]['blocked']}")
        return 0
    print(f"Showing {len(top)} component result(s).")
    if context["industry_id"]:
        print(f"Detected industry pack: {context['industry_id']}")
    for idx, item in enumerate(top, 1):
        if idx > 1:
            print()
        print_component_result(item)
    print()
    print(tradeoffs_line(top))
    return 0


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
    c = sub.add_parser("component")
    c.add_argument("query")
    c.add_argument("--style")
    c.add_argument("--surface", default="")
    c.add_argument("--license", choices=sorted(LICENSE_ALLOWLISTS), default="permissive")
    c.add_argument("--framework")
    c.add_argument("--industry")
    c.add_argument("--top", type=int, default=5)
    c.add_argument("--why", metavar="ID")
    c.add_argument("--registry-index", default=DEFAULT_REGISTRY_INDEX)
    c.set_defaults(func=cmd_component)
    args = ap.parse_args()
    if getattr(args, "cmd", "") == "component":
        args.top = max(1, min(args.top, 5))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
