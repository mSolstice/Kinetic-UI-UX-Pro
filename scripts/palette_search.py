#!/usr/bin/env python3
"""Search, preview, pair, and verify generated palette seeds."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ds_search import BM25  # noqa: E402
from token_gen import BUILTIN_RADIX, build_ramps, print_report, verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PALETTES_FILE = ROOT / "templates" / "palettes" / "palettes.json"
STYLE_DIR = ROOT / "templates" / "styles"
TOKEN_GEN = ROOT / "scripts" / "token_gen.py"
SCHEMA_ID = "kinetic-ui-ux-pro/token-schema/1"

SEMANTIC = {
    "light": {
        "surface-base": "neutral-50",
        "surface-raised": "neutral-100",
        "text-primary": "neutral-950",
        "text-muted": "neutral-900",
        "border-subtle": "neutral-600",
        "action-bg": "brand-800",
        "action-text": "neutral-50",
    },
    "dark": {
        "surface-base": "neutral-950",
        "surface-raised": "neutral-900",
        "text-primary": "neutral-50",
        "text-muted": "neutral-100",
        "border-subtle": "neutral-400",
        "action-bg": "brand-100",
        "action-text": "neutral-950",
    },
}

CONTRAST_PAIRS = [
    {"text": "text-primary", "bg": "surface-base", "size": "body"},
    {"text": "text-muted", "bg": "surface-base", "size": "body"},
    {"text": "action-text", "bg": "action-bg", "size": "large"},
    {"text": "border-subtle", "bg": "surface-base", "size": "nontext"},
]


def load_palettes():
    data = json.loads(PALETTES_FILE.read_text(encoding="utf-8"))
    rows = []
    for mood, entries in data.items():
        for entry in entries:
            item = dict(entry)
            item["mood"] = mood
            rows.append(item)
    return rows


def palette_by_id(palette_id):
    wanted = palette_id.strip().lower()
    for palette in load_palettes():
        if palette["id"] == wanted:
            return palette
    available = ", ".join(p["id"] for p in load_palettes())
    raise SystemExit(f"unknown palette '{palette_id}'. Available palettes: {available}")


def related_hue(hue, rule):
    if rule == "analogous":
        return (hue + 32) % 360
    if rule == "complementary":
        return (hue + 180) % 360
    return hue


def schema_for_palette(palette):
    hue = float(palette["baseHue"]) % 360
    chroma = float(palette["chroma"])
    neutral_chroma = min(0.018, max(0.004, chroma * 0.12))
    accent_hue = related_hue(hue, palette["hueRelationshipRule"])
    return {
        "$schema": SCHEMA_ID,
        "name": palette["id"],
        "palettes": {
            "brand": {"hue": hue, "chroma": chroma},
            "neutral": {"hue": hue, "chroma": neutral_chroma},
            "accent": {"hue": accent_hue, "chroma": chroma},
            "danger": {"hue": 27, "chroma": min(0.19, max(0.12, chroma))},
            "success": {"hue": 150, "chroma": min(0.16, max(0.1, chroma * 0.9))},
        },
        "semantic": SEMANTIC,
        "contrastPairs": CONTRAST_PAIRS,
        "motion": {
            "durations": {"micro": 120, "local": 240, "view": 400, "reduced": 90},
            "easings": {
                "out": "cubic-bezier(.2,.8,.2,1)",
                "in": "cubic-bezier(.4,0,1,1)",
                "spring": "cubic-bezier(.34,1.56,.64,1)",
            },
        },
        "space": {"base": 4, "steps": [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32]},
        "radius": {"sm": 4, "md": 8, "lg": 12, "full": 9999},
        "palette": {
            "id": palette["id"],
            "name": palette["name"],
            "mood": palette["mood"],
            "moodTags": palette["moodTags"],
            "baseHue": palette["baseHue"],
            "chroma": palette["chroma"],
            "hueRelationshipRule": palette["hueRelationshipRule"],
            "suggestedStylePairings": palette["suggestedStylePairings"],
            "source": palette.get("source", "generated"),
        },
    }


def verify_with_token_gen(schema):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tokens.schema.json"
        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(TOKEN_GEN), str(path), "--verify"],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


def palette_docs(palettes):
    docs = []
    for p in palettes:
        text = " ".join([
            p["id"],
            p["name"],
            p["mood"],
            " ".join(p["moodTags"]),
            p["hueRelationshipRule"],
            " ".join(p["suggestedStylePairings"]),
        ])
        docs.append({"id": p["id"], "kind": "palette", "text": text, "palette": p})
    return docs


def command_find(args):
    docs = palette_docs(load_palettes())
    ranked = BM25(docs).ranked(args.query)
    for score, doc in ranked[: args.top]:
        p = doc["palette"]
        print(f"{score:6.2f}  {p['id']:<22} {p['name']:<22} mood={p['mood']} tags={', '.join(p['moodTags'])}")


def print_ramp(schema):
    ramps = build_ramps(schema["palettes"])
    for family in ("brand", "accent", "neutral", "danger", "success"):
        print(f"\n{family}")
        print("step  oklch                              hex")
        print("----  ---------------------------------  -------")
        for step, token in ramps[family].items():
            print(f"{step:<4}  {token['oklch']:<33}  {token['hex']}")
    rows, failures = verify(schema, ramps)
    print_report(rows)
    return failures


def command_preview(args):
    palette = palette_by_id(args.palette_id)
    schema = schema_for_palette(palette)
    result = verify_with_token_gen(schema)
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)
    print(json.dumps(schema["palette"], indent=2))
    failures = print_ramp(schema)
    if failures:
        raise SystemExit("preview refused to emit a failing palette")


def load_style(style_id):
    path = STYLE_DIR / f"{style_id}.json"
    if not path.exists():
        available = ", ".join(p.stem for p in sorted(STYLE_DIR.glob("*.json")) if p.name != "_schema.json")
        raise SystemExit(f"unknown style '{style_id}'. Available styles: {available}")
    return json.loads(path.read_text(encoding="utf-8"))


def compatible(palette, style):
    color = style["color"]
    chroma = float(palette["chroma"])
    chroma_ok = float(color["chromaRange"]["min"]) <= chroma <= float(color["chromaRange"]["max"])
    hue_ok = palette["hueRelationshipRule"] in color["hueRelationshipRules"]
    suggested = style["id"] in palette["suggestedStylePairings"]
    return chroma_ok and hue_ok, suggested


def command_pair(args):
    style = load_style(args.style_id)
    rows = []
    for palette in load_palettes():
        ok, suggested = compatible(palette, style)
        if ok:
            rank = 0 if suggested else 1
            rows.append((rank, palette["mood"], palette["id"], palette, suggested))
    rows.sort()
    for _rank, _mood, _pid, palette, suggested in rows:
        mark = "suggested" if suggested else "compatible"
        print(f"{palette['id']:<22} {palette['name']:<22} {mark:<10} mood={palette['mood']} chroma={palette['chroma']} rule={palette['hueRelationshipRule']}")


def command_verify_all(_args):
    failures = []
    for palette in load_palettes():
        schema = schema_for_palette(palette)
        result = verify_with_token_gen(schema)
        if result.returncode != 0:
            failures.append((palette["id"], result.stdout, result.stderr))
            print(f"FAIL {palette['id']}")
        else:
            print(f"PASS {palette['id']}")
    if failures:
        print("\nFailures:")
        for palette_id, stdout, stderr in failures:
            print(f"\n{palette_id}\n{stdout}{stderr}")
        raise SystemExit(1)
    print(f"\nAll {len(load_palettes())} palettes pass token_gen.py --verify.")


RADIX_SEED_MAP = {
    "blue": {
        "mood": "trustworthy",
        "baseHue": 212,
        "chroma": 0.13,
        "hueRelationshipRule": "analogous",
        "moodTags": ["radix", "trustworthy", "blue", "reference", "interface"],
        "suggestedStylePairings": ["swiss-grid", "data-forward", "high-contrast-utility"],
    },
    "gray": {
        "mood": "restrained",
        "baseHue": 240,
        "chroma": 0.02,
        "hueRelationshipRule": "monochrome",
        "moodTags": ["radix", "restrained", "neutral", "reference", "quiet"],
        "suggestedStylePairings": ["swiss-grid", "technical-dense", "luxury-minimal"],
    },
    "green": {
        "mood": "optimistic",
        "baseHue": 145,
        "chroma": 0.13,
        "hueRelationshipRule": "analogous",
        "moodTags": ["radix", "optimistic", "green", "reference", "growth"],
        "suggestedStylePairings": ["warm-organic", "playful-rounded", "data-forward"],
    },
    "red": {
        "mood": "authoritative",
        "baseHue": 24,
        "chroma": 0.14,
        "hueRelationshipRule": "complementary",
        "moodTags": ["radix", "authoritative", "red", "reference", "decisive"],
        "suggestedStylePairings": ["high-contrast-utility", "brutalist", "technical-dense"],
    },
}


def radix_seed(scale):
    if scale not in BUILTIN_RADIX or scale not in RADIX_SEED_MAP:
        known = ", ".join(sorted(RADIX_SEED_MAP))
        raise SystemExit(f"unknown built-in Radix scale '{scale}'. Available: {known}")
    spec = RADIX_SEED_MAP[scale]
    return {
        "id": f"radix-{scale}",
        "name": f"Radix {scale.title()}",
        "moodTags": spec["moodTags"],
        "baseHue": spec["baseHue"],
        "chroma": spec["chroma"],
        "hueRelationshipRule": spec["hueRelationshipRule"],
        "suggestedStylePairings": spec["suggestedStylePairings"],
        "source": "radix",
    }, spec["mood"]


def command_import_radix(args):
    data = json.loads(PALETTES_FILE.read_text(encoding="utf-8"))
    scales = args.import_radix_colors or sorted(RADIX_SEED_MAP)
    added = 0
    for scale in scales:
        seed, mood = radix_seed(scale)
        bucket = data.setdefault(mood, [])
        for i, existing in enumerate(bucket):
            if existing.get("id") == seed["id"]:
                bucket[i] = seed
                break
        else:
            bucket.append(seed)
            added += 1
    if args.out:
        Path(args.out).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(json.dumps(data, indent=2))
    print(f"Radix reference seeds merged: {len(scales)} ({added} new)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-radix-colors", nargs="*", metavar="SCALE",
                        help="merge built-in Radix Colors reference seeds; omit scales for all built-ins")
    parser.add_argument("--out", help="output path for --import-radix-colors")
    sub = parser.add_subparsers(dest="command")

    find = sub.add_parser("find", help="rank palettes by mood or description")
    find.add_argument("query")
    find.add_argument("--top", type=int, default=8)
    find.set_defaults(func=command_find)

    preview = sub.add_parser("preview", help="print generated ramp and contrast report")
    preview.add_argument("palette_id")
    preview.set_defaults(func=command_preview)

    pair = sub.add_parser("pair", help="list palettes compatible with a style")
    pair.add_argument("style_id")
    pair.set_defaults(func=command_pair)

    verify_all = sub.add_parser("verify-all", help="verify every palette seed")
    verify_all.set_defaults(func=command_verify_all)

    args = parser.parse_args()
    if args.import_radix_colors is not None:
        command_import_radix(args)
        return
    if not args.command:
        parser.error("choose a command or --import-radix-colors")
    args.func(args)


if __name__ == "__main__":
    main()
