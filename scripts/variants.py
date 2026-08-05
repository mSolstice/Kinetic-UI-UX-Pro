#!/usr/bin/env python3
"""Generate, merge, and record divergent design directions."""

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ds_search import BM25  # noqa: E402
from palette_search import compatible as palette_compatible  # noqa: E402
from palette_search import load_palettes  # noqa: E402
from style_apply import load_modifier, load_style, compose_style, verified_schema  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VARIANT_DIR = ROOT / ".variants"
DEFAULT_SET = VARIANT_DIR / "last.json"
CONTRACT_DECISION_KEY = "variantDirection"
MIN_DISTANCE = 4.0

AXIS_PLANS = [
    {
        "axis": "density",
        "label": "dense comparison system",
        "intent": "Compresses the surface for fast scanning and repeated comparison.",
        "styles": ["technical-dense", "data-forward", "swiss-grid"],
        "modifiers": ["dense", "bordered"],
        "density": "dense",
        "hierarchy": "weight",
        "depth": "border",
        "motion": "still",
        "composition": "symmetric-grid",
        "optimizesFor": "throughput, comparability, and low motion fatigue",
        "sacrifices": "warmth, whitespace, and expressive brand moments",
    },
    {
        "axis": "hierarchy mechanism",
        "label": "scale-led narrative",
        "intent": "Uses type scale and whitespace to make the primary decision unmistakable.",
        "styles": ["editorial", "luxury-minimal", "swiss-grid"],
        "modifiers": ["airy"],
        "density": "airy",
        "hierarchy": "scale",
        "depth": "flat",
        "motion": "responsive",
        "composition": "single-column-emphasis",
        "optimizesFor": "clarity, pacing, and a memorable first read",
        "sacrifices": "information density and above-the-fold breadth",
    },
    {
        "axis": "depth strategy",
        "label": "bordered utility",
        "intent": "Separates decisions with crisp boundaries instead of decorative elevation.",
        "styles": ["high-contrast-utility", "brutalist", "data-forward"],
        "modifiers": ["bordered", "sharp"],
        "density": "balanced",
        "hierarchy": "space",
        "depth": "border",
        "motion": "still",
        "composition": "asymmetric",
        "optimizesFor": "legibility, resilience, and unambiguous state boundaries",
        "sacrifices": "softness and ambient polish",
    },
    {
        "axis": "motion budget",
        "label": "responsive causality",
        "intent": "Lets motion explain cause and continuity while keeping decoration out.",
        "styles": ["playful-rounded", "warm-organic", "glass-layered"],
        "modifiers": ["rounded"],
        "density": "balanced",
        "hierarchy": "color",
        "depth": "shadow",
        "motion": "expressive",
        "composition": "asymmetric",
        "optimizesFor": "perceived responsiveness and guided attention",
        "sacrifices": "maximum density and the quietest possible interface",
    },
    {
        "axis": "structural composition",
        "label": "asymmetric workbench",
        "intent": "Breaks the grid deliberately so primary and supporting work have different weights.",
        "styles": ["swiss-grid", "warm-organic", "data-forward"],
        "modifiers": ["duotone"],
        "density": "balanced",
        "hierarchy": "space",
        "depth": "overlap",
        "motion": "responsive",
        "composition": "asymmetric",
        "optimizesFor": "clear priority and less templated composition",
        "sacrifices": "strict regularity and easiest implementation",
    },
]

TRAIT_FIELDS = {
    "style": ("style",),
    "palette": ("palette",),
    "density": ("traits", "density"),
    "whitespaceRhythm": ("traits", "density"),
    "hierarchy": ("traits", "hierarchy"),
    "depth": ("traits", "depth"),
    "motion": ("traits", "motion"),
    "composition": ("traits", "composition"),
    "radius": ("traits", "radius"),
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value):
    return str(value).strip().lower().replace("_", "-").replace(" ", "-")


def surface_matches(surface, values):
    surface = slug(surface)
    variants = {surface, surface.rstrip("s"), surface + "s"}
    return bool(variants & {slug(v) for v in values})


def docs_for_styles():
    docs = []
    for path in sorted((ROOT / "templates" / "styles").glob("*.json")):
        if path.name == "_schema.json":
            continue
        style = json.loads(path.read_text(encoding="utf-8"))
        docs.append({
            "id": style["id"],
            "text": " ".join([
                style["id"], style["name"], style["intent"],
                " ".join(style.get("worksFor", [])),
                " ".join(style.get("avoidFor", [])),
                " ".join(style.get("prohibitions", [])),
            ]),
            "style": style,
        })
    return docs


def flattened_palettes():
    return load_palettes()


def pick_style(plan, brief, surface, used):
    docs = docs_for_styles()
    bm25 = BM25(docs)
    by_id = {d["id"]: d["style"] for d in docs}
    choices = []
    for sid in plan["styles"]:
        style = by_id.get(sid)
        if not style or style["id"] in used:
            continue
        if surface_matches(surface, style.get("avoidFor", [])):
            continue
        bonus = 3.0 if surface_matches(surface, style.get("worksFor", [])) else 0.0
        score = bm25.score(f"{brief} {surface} {plan['label']} {plan['axis']}", docs.index(next(d for d in docs if d["id"] == sid))) + bonus
        choices.append((score, style))
    if not choices:
        for i, doc in enumerate(docs):
            style = doc["style"]
            if style["id"] in used or surface_matches(surface, style.get("avoidFor", [])):
                continue
            choices.append((bm25.score(f"{brief} {surface} {plan['label']}", i), style))
    if not choices:
        raise SystemExit(f"no compatible unused style for axis {plan['axis']}")
    choices.sort(key=lambda row: (-row[0], row[1]["id"]))
    return choices[0][1]


def compatible_modifiers(style, wanted):
    mods = []
    for name in wanted:
        try:
            mod, _path = load_modifier(name)
            compose_style(style, mods + [mod])
            mods.append(mod)
        except SystemExit:
            continue
    return mods


def pick_palette(style, brief, plan, used):
    palettes = flattened_palettes()
    docs = [{
        "id": p["id"],
        "text": " ".join([p["id"], p["name"], p.get("mood", ""), " ".join(p.get("moodTags", [])), " ".join(p.get("suggestedStylePairings", []))]),
        "palette": p,
    } for p in palettes]
    bm25 = BM25(docs)
    ranked = []
    for i, doc in enumerate(docs):
        palette = doc["palette"]
        if palette["id"] in used:
            continue
        ok, suggested = palette_compatible(palette, style)
        if not ok:
            continue
        score = bm25.score(f"{brief} {plan['label']} {style['intent']}", i)
        score += 2.0 if suggested else 0.0
        ranked.append((score, palette))
    if not ranked:
        raise SystemExit(f"no compatible palette for style {style['id']}")
    ranked.sort(key=lambda row: (-row[0], row[1]["id"]))
    return ranked[0][1]


def variant_distance(a, b):
    score = 0.0
    traits_a, traits_b = a["traits"], b["traits"]
    for key in ("density", "hierarchy", "depth", "motion", "composition", "radius"):
        if traits_a.get(key) != traits_b.get(key):
            score += 1.0
    if a["axis"] != b["axis"]:
        score += 1.25
    if a["style"]["id"] != b["style"]["id"]:
        score += 1.0
    if abs(float(a["palette"]["baseHue"]) - float(b["palette"]["baseHue"])) >= 35:
        score += 0.75
    if abs(float(a["palette"]["chroma"]) - float(b["palette"]["chroma"])) >= 0.04:
        score += 0.5
    return score


def build_variant(index, plan, brief, surface, used_styles, used_palettes):
    style = pick_style(plan, brief, surface, used_styles)
    modifiers = compatible_modifiers(style, plan["modifiers"])
    composed = compose_style(style, modifiers)
    palette = pick_palette(composed, brief, plan, used_palettes)
    schema, attempts, _report = verified_schema(composed, palette["baseHue"])
    schema["name"] = f"variant-{index}-{slug(plan['label'])}"
    schema.setdefault("variant", {})
    schema["variant"] = {
        "axis": plan["axis"],
        "intent": plan["intent"],
        "palette": palette["id"],
        "optimizesFor": plan["optimizesFor"],
        "sacrifices": plan["sacrifices"],
    }
    used_styles.add(style["id"])
    used_palettes.add(palette["id"])
    return {
        "id": f"v{index}",
        "axis": plan["axis"],
        "label": plan["label"],
        "intent": plan["intent"],
        "style": {"id": composed["id"], "name": composed["name"], "modifiers": [m["id"] for m in modifiers]},
        "palette": palette,
        "traits": {
            "density": plan["density"],
            "hierarchy": plan["hierarchy"],
            "depth": plan["depth"],
            "motion": plan["motion"],
            "composition": plan["composition"],
            "radius": radius_trait(composed),
        },
        "optimizesFor": plan["optimizesFor"],
        "sacrifices": plan["sacrifices"],
        "verification": {"verifiedBy": "token_gen.py --verify", "attempts": attempts, "result": "PASS"},
        "tokenSchema": schema,
    }


def radius_trait(style):
    rng = style["shape"]["radiusMultiplierRange"]
    hi = float(rng["max"])
    if hi <= 0.5:
        return "sharp"
    if hi >= 1.75:
        return "rounded"
    return "moderate"


def generate_variants(count, brief, surface):
    if count < 2:
        raise SystemExit("--count must be at least 2; one option is a recommendation, not exploration")
    if count > len(AXIS_PLANS):
        raise SystemExit(f"--count may not exceed {len(AXIS_PLANS)}")
    best = None
    best_min = -1
    for rotation in range(len(AXIS_PLANS)):
        plans = AXIS_PLANS[rotation:] + AXIS_PLANS[:rotation]
        used_styles, used_palettes, variants = set(), set(), []
        try:
            for i, plan in enumerate(plans[:count], 1):
                variants.append(build_variant(i, plan, brief, surface, used_styles, used_palettes))
        except SystemExit:
            continue
        distances = pairwise_distances(variants)
        min_dist = min(distances.values()) if distances else 999
        if min_dist >= MIN_DISTANCE:
            return variants, distances
        if min_dist > best_min:
            best, best_min = (variants, distances), min_dist
    if best:
        raise SystemExit(f"could not generate sufficiently divergent variants; closest pair scored {best_min:.2f}, threshold {MIN_DISTANCE}")
    raise SystemExit("could not generate variants from available compatible styles and palettes")


def pairwise_distances(variants):
    out = {}
    for i, a in enumerate(variants):
        for b in variants[i + 1:]:
            out[f"{a['id']}:{b['id']}"] = round(variant_distance(a, b), 2)
    return out


def save_variant_set(data, path=DEFAULT_SET):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_variant_set(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"variant set not found: {path}. Run explore first or pass --from.")


def print_explore(data):
    print("# Variant Exploration\n")
    print(f"Brief: {data['brief']}")
    print(f"Surface: {data['surface']}")
    print(f"Divergence threshold: {data['divergenceThreshold']}")
    print("Pairwise distances: " + ", ".join(f"{k}={v}" for k, v in data["distances"].items()))
    for variant in data["variants"]:
        print(f"\n## {variant['id']} - {variant['label']}")
        print(f"- Axis: {variant['axis']}")
        print(f"- Intent: {variant['intent']}")
        print(f"- Style: {variant['style']['id']}")
        print(f"- Palette: {variant['palette']['id']}")
        print(f"- Optimizes for: {variant['optimizesFor']}")
        print(f"- Sacrifices: {variant['sacrifices']}")
        print(f"- Verification: {variant['verification']['result']} in {variant['verification']['attempts']} attempt(s)")
        print("\n```json")
        print(json.dumps(variant["tokenSchema"], indent=2))
        print("```")
    print(f"\nSaved: {DEFAULT_SET.relative_to(ROOT)}")


def find_variant(data, vid):
    for variant in data["variants"]:
        if variant["id"] == vid:
            return variant
    raise SystemExit(f"unknown variant id '{vid}'")


def parse_take(raw):
    if ":" not in raw:
        raise SystemExit(f"invalid --take '{raw}', expected <variant>:<trait>")
    vid, trait = raw.split(":", 1)
    trait = trait.strip()
    if trait not in TRAIT_FIELDS:
        raise SystemExit(f"unknown trait '{trait}'. Available: {', '.join(sorted(TRAIT_FIELDS))}")
    return vid.strip(), trait


def merge_variants(args):
    data = load_variant_set(args.from_file)
    takes = [parse_take(t) for t in args.take]
    if len(takes) < 2:
        raise SystemExit("merge requires at least two --take entries")
    chosen = [(find_variant(data, vid), trait) for vid, trait in takes]
    contradictions = contradictory_traits(chosen)
    if contradictions:
        raise SystemExit("contradictory merge refused:\n- " + "\n- ".join(contradictions))
    base = copy.deepcopy(chosen[0][0])
    schema = copy.deepcopy(base["tokenSchema"])
    final_traits = copy.deepcopy(base["traits"])
    provenance = []
    for variant, trait in chosen:
        apply_trait(schema, final_traits, variant, trait)
        provenance.append(f"{trait} from {variant['id']}")
    palette = merged_palette(chosen, base)
    ok, _suggested = palette_compatible(palette, style_for_compat(schema))
    if not ok:
        raise SystemExit(
            "contradictory merge refused:\n"
            f"- palette {palette['id']} is outside the color constraints of style {schema.get('style', {}).get('id')}"
        )
    result = verify_merged(schema)
    final = {
        "id": "merged-direction",
        "brief": data["brief"],
        "surface": data["surface"],
        "traits": final_traits,
        "provenance": provenance,
        "palette": palette["id"],
        "verification": {"verifiedBy": "token_gen.py --verify", "result": "PASS"},
        "tokenSchema": schema,
    }
    print("# Merged Direction\n")
    print("- " + "\n- ".join(provenance))
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    print("\n```json")
    print(json.dumps(final, indent=2))
    print("```")


def contradictory_traits(chosen):
    values = {}
    problems = []
    for variant, trait in chosen:
        family = "density" if trait in ("density", "whitespaceRhythm") else trait
        if trait == "style":
            value = variant["style"]["id"]
        elif trait == "palette":
            value = variant["palette"]["id"]
        else:
            value = variant["traits"].get(family)
        if family in values and values[family] != value:
            problems.append(f"{family} takes both {values[family]} and {value}")
        values[family] = value
    density_values = {v["traits"]["density"] for v, t in chosen if t in ("density", "whitespaceRhythm")}
    if {"dense", "airy"} <= density_values:
        problems.append("dense density contradicts airy whitespace rhythm")
    motion_values = {v["traits"]["motion"] for v, t in chosen if t == "motion"}
    if {"still", "expressive"} <= motion_values:
        problems.append("still motion contradicts expressive motion")
    depth_values = {v["traits"]["depth"] for v, t in chosen if t == "depth"}
    if "flat" in depth_values and (depth_values - {"flat"}):
        problems.append("flat depth cannot merge with border, shadow, or overlap depth")
    return problems


def apply_trait(schema, final_traits, variant, trait):
    source = variant["tokenSchema"]
    if trait == "style":
        schema["style"] = copy.deepcopy(source.get("style", {}))
        schema["name"] = f"merged-{slug(variant['style']['id'])}"
    elif trait == "palette":
        schema["palettes"] = copy.deepcopy(source["palettes"])
        schema["semantic"] = copy.deepcopy(source["semantic"])
    elif trait in ("density", "whitespaceRhythm"):
        schema["space"] = copy.deepcopy(source["space"])
        final_traits["density"] = variant["traits"]["density"]
    elif trait == "motion":
        schema["motion"] = copy.deepcopy(source["motion"])
        final_traits["motion"] = variant["traits"]["motion"]
    elif trait == "radius":
        schema["radius"] = copy.deepcopy(source["radius"])
        final_traits["radius"] = variant["traits"]["radius"]
    elif trait in ("hierarchy", "depth", "composition"):
        final_traits[trait] = variant["traits"][trait]
    schema.setdefault("variantMerge", {}).setdefault("takes", []).append({"variant": variant["id"], "trait": trait})


def merged_palette(chosen, base):
    for variant, trait in reversed(chosen):
        if trait == "palette":
            return variant["palette"]
    return base["palette"]


def style_for_compat(schema):
    style = schema.get("style", {})
    constraints = style.get("constraints", {})
    return {
        "id": style.get("id", ""),
        "color": constraints.get("color", {"chromaRange": {"min": 0, "max": 1}, "hueRelationshipRules": ["monochrome", "analogous", "complementary"]}),
    }


def verify_merged(schema):
    import tempfile
    import subprocess

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tokens.schema.json"
        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "token_gen.py"), str(path), "--verify"],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise SystemExit("merged direction failed token verification:\n" + result.stdout + result.stderr)
    return result


def record_variant(args):
    data = load_variant_set(args.from_file)
    chosen = find_variant(data, args.variant_id)
    contract_path = Path(args.contract)
    if not contract_path.exists():
        raise SystemExit(f"contract not found: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    decision = {
        "value": {
            "variantId": chosen["id"],
            "axis": chosen["axis"],
            "style": chosen["style"],
            "palette": chosen["palette"]["id"],
            "traits": chosen["traits"],
            "optimizesFor": chosen["optimizesFor"],
            "sacrifices": chosen["sacrifices"],
        },
        "rationale": f"Chosen from variant exploration for: {data['brief']}",
        "decidedAt": now_iso(),
    }
    decisions = contract.setdefault("decisions", {})
    if CONTRACT_DECISION_KEY in decisions:
        old = decisions[CONTRACT_DECISION_KEY]
        history = list(old.get("history", []))
        history.append({k: v for k, v in old.items() if k != "history"})
        decision["history"] = history
    decisions[CONTRACT_DECISION_KEY] = decision
    for variant in data["variants"]:
        if variant["id"] == chosen["id"]:
            continue
        contract.setdefault("rejected", []).append({
            "thing": f"variant {variant['id']} - {variant['label']}",
            "reason": f"Rejected in favor of {chosen['id']}; sacrificed {variant['sacrifices']}",
            "rejectedAt": now_iso(),
        })
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"recorded {chosen['id']} and {len(data['variants']) - 1} rejection(s) in {contract_path}")


def command_explore(args):
    variants, distances = generate_variants(args.count, args.brief, args.surface)
    data = {
        "brief": args.brief,
        "surface": args.surface,
        "createdAt": now_iso(),
        "divergenceThreshold": MIN_DISTANCE,
        "distances": distances,
        "variants": variants,
    }
    save_variant_set(data)
    print_explore(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    explore = sub.add_parser("explore", help="generate divergent verified design directions")
    explore.add_argument("--count", type=int, default=3)
    explore.add_argument("--brief", required=True)
    explore.add_argument("--surface", required=True)
    explore.set_defaults(func=command_explore)

    merge = sub.add_parser("merge", help="compose a final direction from chosen variant traits")
    merge.add_argument("--take", action="append", required=True, help="<variant>:<trait>, e.g. v1:density")
    merge.add_argument("--from", dest="from_file", default=str(DEFAULT_SET))
    merge.set_defaults(func=merge_variants)

    record = sub.add_parser("record", help="write the chosen and rejected variants to a contract")
    record.add_argument("variant_id")
    record.add_argument("--contract", required=True)
    record.add_argument("--from", dest="from_file", default=str(DEFAULT_SET))
    record.set_defaults(func=record_variant)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
