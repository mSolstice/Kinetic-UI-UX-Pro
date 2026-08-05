#!/usr/bin/env python3
"""Recommend a style, palette, and industry pack from a product brief."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ds_search import BM25  # noqa: E402
from palette_search import compatible as palette_compatible  # noqa: E402
from palette_search import load_palettes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STYLE_DIR = ROOT / "templates" / "styles"
INDUSTRY_DIR = ROOT / "references" / "industries"
STYLE_APPLY = ROOT / "scripts" / "style_apply.py"


def slug(value):
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def load_styles():
    styles = []
    for path in sorted(STYLE_DIR.glob("*.json")):
        if path.name == "_schema.json":
            continue
        style = json.loads(path.read_text(encoding="utf-8"))
        style["_path"] = path
        styles.append(style)
    return styles


def style_doc(style):
    text = " ".join([
        style["id"],
        style["name"],
        style["intent"],
        " ".join(style["worksFor"]),
        " ".join(style["avoidFor"]),
        " ".join(style["type"].get("trackingRules", [])),
        " ".join(style["motion"].get("permittedEasingFamilies", [])),
        " ".join(style["prohibitions"]),
    ])
    return {"id": style["id"], "kind": "style", "text": text, "style": style}


def palette_doc(palette):
    text = " ".join([
        palette["id"],
        palette["name"],
        palette["mood"],
        " ".join(palette["moodTags"]),
        palette["hueRelationshipRule"],
        " ".join(palette["suggestedStylePairings"]),
    ])
    return {"id": palette["id"], "kind": "palette", "text": text, "palette": palette}


def industry_docs():
    docs = []
    for path in sorted(INDUSTRY_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        docs.append({
            "id": path.stem,
            "kind": "industry",
            "text": f"{path.stem} {text}",
            "path": path,
            "title": title_from_markdown(text, path.stem),
        })
    return docs


def title_from_markdown(text, fallback):
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def surface_in(values, surface):
    surface = slug(surface)
    variants = {surface}
    if surface.endswith("s"):
        variants.add(surface[:-1])
    else:
        variants.add(surface + "s")
    return bool(variants & {slug(v) for v in values})


def industry_style_sets(industry, context=""):
    if not industry:
        return set(), set()
    _score, doc = industry
    text = Path(doc["path"]).read_text(encoding="utf-8", errors="replace")
    suitable, conflicts = set(), set()
    context_tokens = set(slug(context).split("-"))
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("suitable:"):
            for segment in line.split(","):
                ids = {part.split("`")[0] for part in segment.split("`")[1::2]}
                if "only" in segment.lower():
                    segment_tokens = set(slug(segment).split("-"))
                    if not (context_tokens & segment_tokens):
                        continue
                suitable.update(ids)
        elif low.startswith("conflicts:"):
            ids = {part.split("`")[0] for part in line.split("`")[1::2]}
            conflicts.update(ids)
    return suitable, conflicts


def ranked_styles(brief, surface, industry=None):
    docs = [style_doc(s) for s in load_styles()]
    bm25 = BM25(docs)
    ranked = []
    excluded = []
    query = f"{brief} {surface}"
    industry_suitable, industry_conflicts = industry_style_sets(industry, f"{brief} {surface}")
    for i, doc in enumerate(docs):
        score = bm25.score(query, i)
        style = doc["style"]
        if surface_in(style["avoidFor"], surface):
            excluded.append((score, style))
            continue
        if style["id"] in industry_conflicts:
            excluded.append((score, style))
            continue
        bonus = 1.0 if surface_in(style["worksFor"], surface) else 0.0
        if style["id"] in industry_suitable:
            bonus += 4.0
        if score <= 0 and bonus <= 0:
            continue
        ranked.append((score + bonus, score, style))
    ranked.sort(key=lambda row: (-row[0], row[2]["id"]))
    if not ranked:
        raise SystemExit(f"no compatible styles found for surface '{surface}'")
    return ranked, excluded


def ranked_palettes(brief, style):
    docs = [palette_doc(p) for p in load_palettes()]
    bm25 = BM25(docs)
    ranked = []
    query = f"{brief} {style['intent']} {' '.join(style['worksFor'])}"
    for i, doc in enumerate(docs):
        score = bm25.score(query, i)
        palette = doc["palette"]
        ok, suggested = palette_compatible(palette, style)
        if not ok:
            continue
        bonus = 1.25 if suggested else 0.0
        if score <= 0 and bonus <= 0:
            continue
        ranked.append((score + bonus, score, palette, suggested))
    ranked.sort(key=lambda row: (-row[0], row[2]["id"]))
    if not ranked:
        raise SystemExit(f"no compatible palettes found for style '{style['id']}'")
    return ranked


def ranked_industries(brief, surface):
    docs = industry_docs()
    ranked = BM25(docs).ranked(f"{brief} {surface}")
    if not ranked:
        return None
    score, doc = ranked[0]
    return score, doc


def tradeoff(winner, runner):
    w = winner
    r = runner
    parts = []
    w_density = w["space"]["densityMultiplier"]
    r_density = r["space"]["densityMultiplier"]
    if float(w_density["max"]) < float(r_density["max"]):
        parts.append(f"sacrifices some maximum density versus `{r['id']}`")
    elif float(w_density["min"]) > float(r_density["min"]):
        parts.append(f"sacrifices compactness versus `{r['id']}`")
    w_motion = w["motion"]["durationMultiplier"]
    r_motion = r["motion"]["durationMultiplier"]
    if float(w_motion["max"]) < float(r_motion["max"]):
        parts.append("keeps motion quieter")
    elif float(w_motion["min"]) > float(r_motion["min"]):
        parts.append("accepts a more expressive motion budget")
    w_chroma = w["color"]["chromaRange"]
    r_chroma = r["color"]["chromaRange"]
    if float(w_chroma["max"]) < float(r_chroma["max"]):
        parts.append("allows less color intensity")
    elif float(w_chroma["min"]) > float(r_chroma["min"]):
        parts.append("requires more chroma and may feel less restrained")
    if w["depth"]["allowedElevationTechniques"] != r["depth"]["allowedElevationTechniques"]:
        parts.append(
            "uses "
            + "/".join(w["depth"]["allowedElevationTechniques"])
            + " depth instead of "
            + "/".join(r["depth"]["allowedElevationTechniques"])
        )
    if not parts:
        parts.append(f"chooses `{w['id']}`'s intent over `{r['id']}`'s different surface bias")
    return "; ".join(parts) + "."


def print_recommendation(brief, surface, styles, palettes, industry):
    winner = styles[0][2]
    runner = styles[1][2] if len(styles) > 1 else styles[0][2]
    palette = palettes[0][2]
    palette_total = palettes[0][0]
    palette_score = palettes[0][1]
    suggested = palettes[0][3]

    print("# Design Recommendation\n")
    print(f"Brief: {brief}")
    print(f"Surface: {surface}\n")

    print("## Top Style Candidates")
    for total, raw, style in styles[:3]:
        print(f"- {style['id']}: score {total:.2f} (BM25 {raw:.2f}) - {style['intent']}")

    print("\n## Recommended")
    print(f"- Style: {winner['id']} ({winner['name']})")
    mood_match = ", ".join(palette["moodTags"])
    relation = "suggested pairing" if suggested else "compatible pairing"
    print(f"- Palette: {palette['id']} ({palette['name']}) - mood match: {palette['mood']} / {mood_match}; {relation}; score {palette_total:.2f} (BM25 {palette_score:.2f})")
    if industry:
        score, doc = industry
        print(f"- Industry pack: references/industries/{doc['id']}.md ({doc['title']}); score {score:.2f}")
    else:
        print("- Industry pack: none detected")

    print("\n## Tradeoffs")
    print(f"- Choosing `{winner['id']}` over `{runner['id']}` {tradeoff(winner, runner)}")
    print(f"- The palette uses hue {palette['baseHue']} and chroma {palette['chroma']}; this favors `{palette['mood']}` mood over broader brand expressiveness.")


def apply_recommendation(style, palette, out_dir):
    cmd = [
        sys.executable,
        str(STYLE_APPLY),
        "apply",
        style["id"],
        "--hue",
        str(palette["baseHue"]),
    ]
    if out_dir:
        cmd += ["--out", out_dir]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)
    print("\n## Applied Tokens")
    print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)


def command_recommend(args):
    industry = ranked_industries(args.brief, args.surface)
    style_rows, _excluded = ranked_styles(args.brief, args.surface, industry)
    palette_rows = ranked_palettes(args.brief, style_rows[0][2])
    print_recommendation(args.brief, args.surface, style_rows, palette_rows, industry)
    if args.apply:
        apply_recommendation(style_rows[0][2], palette_rows[0][2], args.out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="recommend style, palette, and industry pack")
    rec.add_argument("brief")
    rec.add_argument("--surface", required=True)
    rec.add_argument("--apply", action="store_true", help="run style_apply.py with the recommended style and palette hue")
    rec.add_argument("--out", help="output directory passed to style_apply.py when --apply is used")
    rec.set_defaults(func=command_recommend)

    args = parser.parse_args()
    if args.out and not args.apply:
        parser.error("--out requires --apply")
    args.func(args)


if __name__ == "__main__":
    main()
