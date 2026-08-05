#!/usr/bin/env python3
"""Apply fuzzy design feedback as verified token-schema deltas."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ds_search import BM25  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOKEN_GEN = ROOT / "scripts" / "token_gen.py"
SCHEMA_CANDIDATES = (
    "design-system/tokens.schema.json",
    "design-system/tokens.json",
    "tokens.schema.json",
    "tokens.json",
    "templates/tokens.schema.json",
)
NEVER = [
    "contrast gates",
    "touch targets",
    "focus visibility",
    "reduced-motion support",
    "semantic structure",
]


VOCAB = [
    {
        "id": "less-corporate",
        "phrases": ["less corporate", "make it less corporate", "less enterprise"],
        "deltas": [
            "radius +1 step",
            "neutral hue +8deg toward warmth",
            "display tracking +0.01em",
            "type scale ratio +0.06",
            "ease-out replaces generic ease-in-out",
            "less border reliance",
        ],
        "ops": {"radius": 1.15, "neutralHue": 8, "typeScale": 0.06, "tracking": 0.01, "easingOut": "cubic-bezier(.16,1,.3,1)"},
    },
    {
        "id": "more-corporate",
        "phrases": ["more corporate", "more enterprise", "more formal"],
        "deltas": ["radius -1 step", "neutral hue -6deg", "type scale ratio -0.04", "standard easing", "more divider reliance"],
        "ops": {"radius": 0.88, "neutralHue": -6, "typeScale": -0.04, "easingOut": "cubic-bezier(.2,.8,.2,1)"},
    },
    {
        "id": "more-breathing-room",
        "phrases": ["more breathing room", "less cramped", "more spacious", "give it air"],
        "deltas": ["spacing scale x1.25", "line-height +0.1", "section padding +2 steps", "font size unchanged"],
        "ops": {"space": 1.25, "lineHeight": 0.1, "sectionPaddingSteps": 2},
    },
    {
        "id": "more-compact",
        "phrases": ["less breathing room", "more compact", "denser", "less spacious"],
        "deltas": ["spacing scale x0.85", "line-height -0.05", "section padding -1 step", "touch targets stay >=44"],
        "ops": {"space": 0.85, "lineHeight": -0.05, "sectionPaddingSteps": -1},
    },
    {
        "id": "more-depth",
        "phrases": ["more depth", "less flat", "needs depth"],
        "deltas": ["shadow/elevation +1 layer", "surface contrast +1 step", "overlap only for hierarchy"],
        "ops": {"depth": 1, "surfaceRaised": "neutral-100"},
    },
    {
        "id": "flatter",
        "phrases": ["flatter", "less depth", "too dimensional"],
        "deltas": ["shadow/elevation -1 layer", "replace elevation with spacing/border", "remove overlap"],
        "ops": {"depth": -1, "surfaceRaised": "surface-base"},
    },
    {
        "id": "more-restrained",
        "phrases": ["too loud", "more restrained", "calmer", "less shouty"],
        "deltas": ["brand chroma x0.8", "saturated surfaces limited", "duration unchanged", "weight ceiling -1 step"],
        "ops": {"brandChroma": 0.8, "weightCeiling": -50},
    },
    {
        "id": "less-restrained",
        "phrases": ["too restrained", "more loud", "more energy", "more expressive"],
        "deltas": ["brand chroma x1.14", "one stronger action role", "weight ceiling +1 step"],
        "ops": {"brandChroma": 1.14, "weightCeiling": 50},
    },
    {
        "id": "warmer",
        "phrases": ["too cold", "warmer", "make it warmer"],
        "deltas": ["neutral hue +8deg", "neutral chroma cap held low", "semantic warning/error unchanged"],
        "ops": {"neutralHue": 8, "neutralChroma": 0.95},
    },
    {
        "id": "colder",
        "phrases": ["too warm", "cooler", "make it colder"],
        "deltas": ["neutral hue -8deg", "warm accent chroma x0.9", "semantic warning/error unchanged"],
        "ops": {"neutralHue": -8, "brandChroma": 0.9},
    },
    {
        "id": "more-distinctive",
        "phrases": ["too generic", "more distinctive", "less template", "less default"],
        "deltas": ["brand hue +16deg", "type scale +0.05", "radius contrast +1 step", "only one distinctive axis per pass"],
        "ops": {"brandHue": 16, "typeScale": 0.05, "radius": 1.1},
    },
    {
        "id": "more-familiar",
        "phrases": ["too distinctive", "more familiar", "less weird"],
        "deltas": ["brand hue -8deg toward current baseline", "radius contrast -1 step", "standard ease-out"],
        "ops": {"brandHue": -8, "radius": 0.92, "easingOut": "cubic-bezier(.2,.8,.2,1)"},
    },
    {
        "id": "lighter",
        "phrases": ["too heavy", "make it lighter", "less heavy"],
        "deltas": ["weight ceiling -1 step", "shadow -1 level", "border weight -1 step", "whitespace +10%"],
        "ops": {"weightCeiling": -50, "depth": -1, "space": 1.1},
    },
    {
        "id": "heavier",
        "phrases": ["too light", "more weight", "make it heavier"],
        "deltas": ["weight ceiling +1 step", "border contrast +1 step", "text-muted one darker token"],
        "ops": {"weightCeiling": 50, "borderSubtle": "neutral-600"},
    },
    {
        "id": "more-playful",
        "phrases": ["more playful", "too serious", "more fun"],
        "deltas": ["radius x1.2", "brand chroma x1.1", "spring permitted for low-risk feedback", "type scale +0.04"],
        "ops": {"radius": 1.2, "brandChroma": 1.1, "typeScale": 0.04, "easingOut": "cubic-bezier(.34,1.56,.64,1)"},
    },
    {
        "id": "more-serious",
        "phrases": ["more serious", "too playful", "less fun"],
        "deltas": ["radius x0.85", "brand chroma x0.88", "standard/decelerate easing", "type scale -0.03"],
        "ops": {"radius": 0.85, "brandChroma": 0.88, "typeScale": -0.03, "easingOut": "cubic-bezier(0,0,.2,1)"},
    },
    {
        "id": "more-current",
        "phrases": ["dated", "feels dated", "more current", "modernize"],
        "deltas": ["remove glossy effects", "shadow tokenized only", "ease-out motion", "improve density hierarchy"],
        "ops": {"depth": -1, "easingOut": "cubic-bezier(.16,1,.3,1)", "typeScale": 0.03},
    },
    {
        "id": "more-timeless",
        "phrases": ["too current", "too trendy", "more timeless"],
        "deltas": ["remove trend effects", "radius contrast -1 step", "durations x0.9", "neutral palette steadier"],
        "ops": {"radius": 0.92, "duration": 0.9, "brandChroma": 0.94},
    },
    {
        "id": "more-focused",
        "phrases": ["too busy", "more focused", "simpler", "reduce clutter"],
        "deltas": ["accent roles reduced", "group spacing +1 step", "decorative motion removed", "card chrome reduced"],
        "ops": {"space": 1.12, "brandChroma": 0.9, "duration": 0.85, "depth": -1},
    },
    {
        "id": "less-focused",
        "phrases": ["too focused", "needs more context", "more information"],
        "deltas": ["restore secondary information layer", "group spacing -10%", "muted metadata treatment"],
        "ops": {"space": 0.9, "borderSubtle": "neutral-500"},
    },
    {
        "id": "more-premium",
        "phrases": ["looks cheap", "more premium", "make it premium", "less cheap"],
        "deltas": ["borders -1 step", "whitespace +15%", "accent usage lower but stronger", "local motion +10%"],
        "ops": {"space": 1.15, "brandChroma": 0.92, "duration": 1.1, "depth": -1},
    },
    {
        "id": "less-premium",
        "phrases": ["too premium", "more approachable", "less luxe"],
        "deltas": ["whitespace -10%", "radius +1 step", "brand chroma +8%", "motion duration -5%"],
        "ops": {"space": 0.9, "radius": 1.1, "brandChroma": 1.08, "duration": 0.95},
    },
    {
        "id": "snappier",
        "phrases": ["too slow", "snappier", "make it faster", "slow"],
        "deltas": ["durations x0.8", "micro cap 100ms", "local cap 200ms", "decelerate/ease-out"],
        "ops": {"duration": 0.8, "capMicro": 100, "capLocal": 200, "easingOut": "cubic-bezier(0,0,.2,1)"},
    },
    {
        "id": "more-deliberate-motion",
        "phrases": ["too snappy", "more deliberate", "slower motion"],
        "deltas": ["durations x1.15", "local cap 280ms", "reduced stays under 100ms"],
        "ops": {"duration": 1.15, "capLocal": 280},
    },
    {
        "id": "less-motion",
        "phrases": ["too much motion", "less motion", "motion is too much"],
        "deltas": ["decorative motion removed", "durations x0.75", "travel distance -50%", "opacity/state signals kept"],
        "ops": {"duration": 0.75, "motionTravel": 0.5},
    },
    {
        "id": "more-motion",
        "phrases": ["lifeless", "needs motion", "too static"],
        "deltas": ["one stateful motion cue added", "local duration x1.1", "spring only for reversible low-risk feedback"],
        "ops": {"duration": 1.1, "easingOut": "cubic-bezier(.34,1.56,.64,1)"},
    },
]


def clamp(value, low, high):
    return max(low, min(high, value))


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"could not read {path}: {e}")


def find_schema(contract):
    token_path = contract.get("tokens", {}).get("path")
    candidates = []
    if token_path:
        path = Path(token_path)
        if path.suffix == ".json":
            candidates.append(path)
        candidates += [path.with_suffix(".schema.json"), path.parent / "tokens.schema.json"]
    candidates += [Path(p) for p in SCHEMA_CANDIDATES]
    for path in candidates:
        if path.exists():
            data = load_json(path)
            if "palettes" in data and "semantic" in data:
                return path, data
    raise SystemExit("no token schema found; expected design-system/tokens.schema.json or a JSON token path in the contract")


def docs():
    rows = []
    for entry in VOCAB:
        text = " ".join(entry["phrases"] + entry["deltas"])
        rows.append({"id": entry["id"], "kind": "iteration", "text": text, "entry": entry})
    return rows


def lookup(phrase):
    wanted = phrase.strip().lower()
    for entry in VOCAB:
        if wanted in [p.lower() for p in entry["phrases"]]:
            return entry
    ranked = BM25(docs()).ranked(phrase)
    return None, ranked[:3]


def set_semantic(schema, name, value):
    for mode in ("light", "dark"):
        if name in schema.get("semantic", {}).get(mode, {}):
            schema["semantic"][mode][name] = value


def ensure_iteration(schema):
    return schema.setdefault("iteration", {
        "typeScaleRatio": 1.2,
        "displayTrackingEm": 0,
        "lineHeight": 1.45,
        "sectionPaddingSteps": 0,
        "depthLevel": 1,
        "motionTravelMultiplier": 1,
        "weightCeiling": 700,
        "borderReliance": "normal",
    })


def apply_ops(schema, ops):
    changed = []
    meta = ensure_iteration(schema)
    palettes = schema.setdefault("palettes", {})
    if "neutralHue" in ops and "neutral" in palettes:
        before = palettes["neutral"].get("hue", 0)
        after = round((float(before) + ops["neutralHue"]) % 360, 3)
        palettes["neutral"]["hue"] = after
        changed.append(("palettes.neutral.hue", before, after, f"{ops['neutralHue']}deg"))
    if "brandHue" in ops and "brand" in palettes:
        before = palettes["brand"].get("hue", 0)
        after = round((float(before) + ops["brandHue"]) % 360, 3)
        palettes["brand"]["hue"] = after
        changed.append(("palettes.brand.hue", before, after, f"{ops['brandHue']}deg"))
    for key, fam in (("brandChroma", "brand"), ("neutralChroma", "neutral")):
        if key in ops and fam in palettes:
            before = palettes[fam].get("chroma", 0)
            after = round(clamp(float(before) * ops[key], 0.001, 0.32), 4)
            palettes[fam]["chroma"] = after
            changed.append((f"palettes.{fam}.chroma", before, after, f"x{ops[key]}"))
    if "space" in ops:
        space = schema.setdefault("space", {"base": 4, "steps": [0, 1, 2, 3, 4, 6, 8]})
        before = space.get("base", 4)
        after = round(clamp(float(before) * ops["space"], 1, 12), 3)
        space["base"] = after
        changed.append(("space.base", before, after, f"x{ops['space']}"))
    if "radius" in ops:
        for key, before in list(schema.setdefault("radius", {}).items()):
            if key == "full":
                continue
            after = int(round(clamp(float(before) * ops["radius"], 0, 32)))
            schema["radius"][key] = after
            changed.append((f"radius.{key}", before, after, f"x{ops['radius']}"))
    if "duration" in ops:
        durations = schema.setdefault("motion", {}).setdefault("durations", {})
        for key, before in list(durations.items()):
            after = int(round(clamp(float(before) * ops["duration"], 50, 900)))
            if key == "micro" and "capMicro" in ops:
                after = min(after, int(ops["capMicro"]))
            if key == "local" and "capLocal" in ops:
                after = min(after, int(ops["capLocal"]))
            if key == "reduced":
                after = min(after, 100)
            durations[key] = after
            changed.append((f"motion.durations.{key}", before, after, f"x{ops['duration']}"))
    if "easingOut" in ops:
        easings = schema.setdefault("motion", {}).setdefault("easings", {})
        before = easings.get("out", "")
        easings["out"] = ops["easingOut"]
        changed.append(("motion.easings.out", before, ops["easingOut"], "replace"))
    for key, field, low, high in (
        ("typeScale", "typeScaleRatio", 1.05, 1.5),
        ("tracking", "displayTrackingEm", -0.02, 0.04),
        ("lineHeight", "lineHeight", 1.2, 1.8),
        ("sectionPaddingSteps", "sectionPaddingSteps", -4, 6),
        ("depth", "depthLevel", 0, 4),
        ("motionTravel", "motionTravelMultiplier", 0, 1.5),
        ("weightCeiling", "weightCeiling", 400, 900),
    ):
        if key in ops:
            before = meta.get(field, 0)
            after = round(clamp(float(before) + float(ops[key]), low, high), 4)
            if field in ("sectionPaddingSteps", "depthLevel", "weightCeiling"):
                after = int(round(after))
            meta[field] = after
            changed.append((f"iteration.{field}", before, after, f"+{ops[key]}"))
    if "borderSubtle" in ops:
        before = schema.get("semantic", {}).get("light", {}).get("border-subtle", "")
        set_semantic(schema, "border-subtle", ops["borderSubtle"])
        changed.append(("semantic.*.border-subtle", before, ops["borderSubtle"], "set"))
    if "surfaceRaised" in ops:
        before = schema.get("semantic", {}).get("light", {}).get("surface-raised", "")
        if ops["surfaceRaised"] == "surface-base":
            for mode in ("light", "dark"):
                sem = schema.get("semantic", {}).get(mode, {})
                sem["surface-raised"] = sem.get("surface-base", sem.get("surface-raised", ""))
        else:
            set_semantic(schema, "surface-raised", ops["surfaceRaised"])
        changed.append(("semantic.*.surface-raised", before, ops["surfaceRaised"], "set"))
    return changed


def verify_schema(schema):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
        tmp = Path(f.name)
    try:
        return subprocess.run(
            [sys.executable, str(TOKEN_GEN), str(tmp), "--verify"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def first_failing_delta(schema, entry):
    trial = copy.deepcopy(schema)
    for key, value in entry["ops"].items():
        apply_ops(trial, {key: value})
        got = verify_schema(trial)
        if got.returncode != 0:
            return key, got.stdout + got.stderr
    return "combined deltas", ""


def print_table(changes):
    print("| Parameter | Before | After | Delta |")
    print("|---|---:|---:|---|")
    for path, before, after, delta in changes:
        print(f"| `{path}` | `{before}` | `{after}` | {delta} |")


def cmd_apply(args):
    got = lookup(args.feedback)
    if isinstance(got, tuple):
        _none, ranked = got
        print("Unrecognized feedback. Closest entries:")
        for score, doc in ranked:
            print(f"- {doc['id']} ({score:.2f}): {', '.join(doc['entry']['phrases'][:3])}")
        raise SystemExit(2)
    entry = got
    contract = load_json(args.contract)
    schema_path, schema = find_schema(contract)
    base_result = verify_schema(schema)
    if base_result.returncode != 0:
        print(f"Rejected iteration: current schema fails contrast before applying `{entry['id']}`.")
        print("Fix the existing token schema first; no iteration deltas were applied.")
        print(base_result.stdout or base_result.stderr)
        raise SystemExit(1)
    updated = copy.deepcopy(schema)
    changes = apply_ops(updated, entry["ops"])
    result = verify_schema(updated)
    if result.returncode != 0:
        culprit, detail = first_failing_delta(schema, entry)
        print(f"Rejected iteration: `{entry['id']}` breaks contrast verification.")
        print(f"Likely failing delta: {culprit}")
        print(detail or result.stdout or result.stderr)
        raise SystemExit(1)
    print(f"Iteration: {entry['id']}")
    print(f"Schema: {schema_path}")
    print(f"Never changes: {', '.join(NEVER)}\n")
    print_table(changes)
    print("\nVerification: PASS (`token_gen.py --verify`)")
    if args.out:
        Path(args.out).write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote: {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("feedback")
    apply.add_argument("--contract", default="design-system/contract.json")
    apply.add_argument("--out", help="write the updated token schema")
    apply.set_defaults(func=cmd_apply)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
