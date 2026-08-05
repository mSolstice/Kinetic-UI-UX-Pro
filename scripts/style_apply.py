#!/usr/bin/env python3
"""
Apply a visual style constraint set to a brand hue and emit a verified token schema.

Styles are ranges and prohibitions, not presets. This script derives concrete
schema values, verifies them with token_gen.py --verify, and retries inside the
style's own constraint ranges before emitting anything.

Usage:
  python scripts/style_apply.py list
  python scripts/style_apply.py explain data-forward --surface dashboard
  python scripts/style_apply.py apply data-forward --hue 260
  python scripts/style_apply.py apply data-forward --hue 260 --out ./out/data-forward
"""

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE_DIR = ROOT / "templates" / "styles"
MODIFIER_DIR = STYLE_DIR / "modifiers"
TOKEN_GEN = ROOT / "scripts" / "token_gen.py"
SCHEMA_ID = "kinetic-ui-ux-pro/token-schema/1"
FIXED_CONSTRAINTS = [
    "contrast-gates",
    "touch-target-minimums",
    "focus-indicator-visibility",
    "reduced-motion-support",
    "text-expansion-40-percent",
]

EASINGS = {
    "linear": "linear",
    "standard": "cubic-bezier(.2,.8,.2,1)",
    "emphasized": "cubic-bezier(.2,0,0,1)",
    "decelerate": "cubic-bezier(0,0,.2,1)",
    "accelerate": "cubic-bezier(.4,0,1,1)",
    "spring": "cubic-bezier(.34,1.56,.64,1)",
}

SEMANTIC_ATTEMPTS = [
    {
        "light": {
            "surface-base": "neutral-50",
            "surface-raised": "neutral-100",
            "text-primary": "neutral-950",
            "text-muted": "neutral-800",
            "border-subtle": "neutral-500",
            "action-bg": "brand-700",
            "action-text": "neutral-50",
        },
        "dark": {
            "surface-base": "neutral-950",
            "surface-raised": "neutral-900",
            "text-primary": "neutral-50",
            "text-muted": "neutral-100",
            "border-subtle": "neutral-500",
            "action-bg": "brand-200",
            "action-text": "neutral-950",
        },
    },
    {
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
    },
    {
        "light": {
            "surface-base": "neutral-50",
            "surface-raised": "neutral-100",
            "text-primary": "neutral-950",
            "text-muted": "neutral-900",
            "border-subtle": "neutral-700",
            "action-bg": "brand-900",
            "action-text": "neutral-50",
        },
        "dark": {
            "surface-base": "neutral-950",
            "surface-raised": "neutral-900",
            "text-primary": "neutral-50",
            "text-muted": "neutral-100",
            "border-subtle": "neutral-300",
            "action-bg": "brand-50",
            "action-text": "neutral-950",
        },
    },
    {
        "light": {
            "surface-base": "neutral-50",
            "surface-raised": "neutral-100",
            "text-primary": "neutral-950",
            "text-muted": "neutral-950",
            "border-subtle": "neutral-800",
            "action-bg": "brand-950",
            "action-text": "neutral-50",
        },
        "dark": {
            "surface-base": "neutral-950",
            "surface-raised": "neutral-900",
            "text-primary": "neutral-50",
            "text-muted": "neutral-50",
            "border-subtle": "neutral-200",
            "action-bg": "brand-50",
            "action-text": "neutral-950",
        },
    },
    {
        "light": {
            "surface-base": "neutral-50",
            "surface-raised": "neutral-50",
            "text-primary": "neutral-950",
            "text-muted": "neutral-950",
            "border-subtle": "neutral-900",
            "action-bg": "neutral-950",
            "action-text": "neutral-50",
        },
        "dark": {
            "surface-base": "neutral-950",
            "surface-raised": "neutral-950",
            "text-primary": "neutral-50",
            "text-muted": "neutral-50",
            "border-subtle": "neutral-50",
            "action-bg": "neutral-50",
            "action-text": "neutral-950",
        },
    },
]


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def midpoint(rng):
    return (float(rng["min"]) + float(rng["max"])) / 2


def slug(value):
    return value.strip().lower().replace("_", "-")


def style_files():
    return sorted(p for p in STYLE_DIR.glob("*.json") if p.name != "_schema.json")


def modifier_files():
    return sorted(p for p in MODIFIER_DIR.glob("*.json") if p.name != "_schema.json")


def load_style(name):
    wanted = slug(name)
    for path in style_files():
        if path.stem == wanted:
            return json.loads(path.read_text(encoding="utf-8")), path
    available = ", ".join(p.stem for p in style_files())
    raise SystemExit(f"unknown style '{name}'. Available styles: {available}")


def load_modifier(name):
    wanted = slug(name)
    for path in modifier_files():
        if path.stem == wanted:
            data = json.loads(path.read_text(encoding="utf-8"))
            validate_modifier_contract(data)
            return data, path
    available = ", ".join(p.stem for p in modifier_files())
    raise SystemExit(f"unknown modifier '{name}'. Available modifiers: {available}")


def load_modifiers(names):
    mods = []
    seen = set()
    for name in names or []:
        modifier, _path = load_modifier(name)
        if modifier["id"] in seen:
            continue
        seen.add(modifier["id"])
        mods.append(modifier)
    return sorted(mods, key=lambda m: (int(m.get("order", 999)), m["id"]))


def validate_modifier_contract(modifier):
    cannot = modifier.get("cannotOverride", [])
    if sorted(cannot) != sorted(FIXED_CONSTRAINTS):
        raise SystemExit(
            f"modifier {modifier.get('id', '<unknown>')} may not change non-negotiables; "
            f"expected {', '.join(FIXED_CONSTRAINTS)}"
        )


def get_path(data, dotted):
    cur = data
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def set_path(data, dotted, value):
    cur = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


def transform_range(current, spec):
    lo, hi = float(current["min"]), float(current["max"])
    if "multiply" in spec:
        factor = float(spec["multiply"])
        lo *= factor
        hi *= factor
    if "multiplyMin" in spec:
        lo *= float(spec["multiplyMin"])
    if "multiplyMax" in spec:
        hi *= float(spec["multiplyMax"])
    if "minFloor" in spec:
        lo = max(lo, float(spec["minFloor"]))
    if "maxCeiling" in spec:
        hi = min(hi, float(spec["maxCeiling"]))
    if lo > hi:
        mid = (lo + hi) / 2
        lo = hi = mid
    return {
        "min": int(lo) if lo.is_integer() else round(lo, 4),
        "max": int(hi) if hi.is_integer() else round(hi, 4),
    }


def apply_modifier_transform(style, modifier):
    transform = modifier.get("transform", {})
    for dotted, value in transform.get("set", {}).items():
        set_path(style, dotted, copy.deepcopy(value))
    for dotted, value in transform.get("setValues", {}).items():
        set_path(style, dotted, copy.deepcopy(value))
    for dotted, spec in transform.get("ranges", {}).items():
        set_path(style, dotted, transform_range(get_path(style, dotted), spec))
    for item in transform.get("addProhibitions", []):
        if item not in style["prohibitions"]:
            style["prohibitions"].append(item)


def modifier_conflicts(style, modifiers):
    problems = []
    ids = [m["id"] for m in modifiers]
    for modifier in modifiers:
        incompatible = modifier.get("incompatibleWith", {})
        if style["id"] in incompatible.get("baseStyles", []):
            problems.append(f"{modifier['id']} conflicts with base style {style['id']}")
        for other in incompatible.get("modifiers", []):
            if other in ids:
                problems.append(f"{modifier['id']} conflicts with modifier {other}")
    return sorted(set(problems))


def compose_style(style, modifiers):
    composed = copy.deepcopy(style)
    problems = modifier_conflicts(composed, modifiers)
    if problems:
        raise SystemExit("invalid style modifier combination:\n- " + "\n- ".join(problems))
    for modifier in modifiers:
        apply_modifier_transform(composed, modifier)
    if modifiers:
        composed["id"] = composed["id"] + "--" + "--".join(m["id"] for m in modifiers)
        composed["name"] = composed["name"] + " + " + " + ".join(m["name"] for m in modifiers)
        composed.setdefault("modifiers", [])
        composed["modifiers"] = [{
            "id": m["id"],
            "name": m["name"],
            "touches": m["touches"],
            "transform": m["transform"],
            "cannotOverride": m["cannotOverride"],
        } for m in modifiers]
    return composed


def related_hue(hue, rules):
    if "analogous" in rules:
        return (hue + 32) % 360
    if "complementary" in rules:
        return (hue + 180) % 360
    return hue


def derived_chroma(style, attempt):
    rng = style["color"]["chromaRange"]
    lo, hi = float(rng["min"]), float(rng["max"])
    if hi <= 0:
        return 0
    factors = [0.72, 0.58, 0.44, 0.32, 0.22]
    return round(clamp(hi * factors[attempt], lo, hi), 4)


def derived_neutral_chroma(style, attempt):
    rng = style["color"]["chromaRange"]
    lo, hi = float(rng["min"]), float(rng["max"])
    cap = min(0.018, hi)
    factors = [0.55, 0.45, 0.35, 0.25, 0.15]
    return round(clamp(cap * factors[attempt], lo, cap), 4)


def derived_motion(style):
    multiplier = midpoint(style["motion"]["durationMultiplier"])
    easings = style["motion"]["permittedEasingFamilies"]
    preferred = next((e for e in easings if e in EASINGS), "standard")
    secondary = next((e for e in easings if e != preferred and e in EASINGS), preferred)
    spring = "spring" if "spring" in easings else preferred
    return {
        "durations": {
            "micro": round(120 * multiplier),
            "local": round(240 * multiplier),
            "view": round(400 * multiplier),
            "reduced": min(90, round(100 * min(1, multiplier))),
        },
        "easings": {
            "out": EASINGS[preferred],
            "in": EASINGS[secondary],
            "spring": EASINGS[spring],
        },
    }


def derived_space(style):
    density = midpoint(style["space"]["densityMultiplier"])
    base = max(2, round(4 * density))
    return {
        "base": base,
        "steps": [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32],
        "densityMultiplier": round(density, 3),
        "whitespaceToContentRatioTarget": style["space"]["whitespaceToContentRatioTarget"],
    }


def derived_radius(style):
    scale = midpoint(style["shape"]["radiusMultiplierRange"])
    return {
        "sm": max(0, round(4 * scale)),
        "md": max(0, round(8 * scale)),
        "lg": max(0, round(12 * scale)),
        "full": 9999,
        "borderWeightRange": style["shape"]["borderWeightRange"],
    }


def build_schema(style, hue, attempt):
    hue = float(hue) % 360
    chroma = derived_chroma(style, attempt)
    neutral_chroma = derived_neutral_chroma(style, attempt)
    accent_hue = related_hue(hue, style["color"]["hueRelationshipRules"])
    semantic = SEMANTIC_ATTEMPTS[attempt]
    return {
        "$schema": SCHEMA_ID,
        "name": f"{style['id']}-{int(round(hue))}",
        "palettes": {
            "brand": {"hue": hue, "chroma": chroma},
            "neutral": {"hue": hue, "chroma": neutral_chroma},
            "danger": {"hue": 27, "chroma": min(0.19, max(0.12, chroma))},
            "success": {"hue": 150, "chroma": min(0.16, max(0.1, chroma * 0.9))},
            "accent": {"hue": accent_hue, "chroma": chroma},
        },
        "semantic": semantic,
        "contrastPairs": [
            {"text": "text-primary", "bg": "surface-base", "size": "body"},
            {"text": "text-muted", "bg": "surface-base", "size": "body"},
            {"text": "action-text", "bg": "action-bg", "size": "large"},
            {"text": "border-subtle", "bg": "surface-base", "size": "nontext"},
        ],
        "motion": derived_motion(style),
        "space": derived_space(style),
        "radius": derived_radius(style),
        "style": {
            "id": style["id"],
            "name": style["name"],
            "intent": style["intent"],
            "modifiers": style.get("modifiers", []),
            "constraints": {
                "color": style["color"],
                "type": style["type"],
                "space": style["space"],
                "shape": style["shape"],
                "depth": style["depth"],
                "motion": style["motion"],
                "prohibitions": style["prohibitions"],
                "mayNotRelax": style["constraints"]["mayNotRelax"],
            },
            "accessibilityWarnings": style.get("accessibilityWarnings", []),
            "fallbacks": style.get("fallbacks", []),
            "derivation": {
                "attempt": attempt + 1,
                "brandHue": hue,
                "brandChroma": chroma,
                "neutralChroma": neutral_chroma,
                "accentHue": accent_hue,
            },
        },
    }


def verify_schema(schema):
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


def verified_schema(style, hue):
    failures = []
    for attempt in range(5):
        schema = build_schema(style, hue, attempt)
        result = verify_schema(schema)
        if result.returncode == 0:
            return schema, attempt + 1, result.stdout
        failures.append((attempt + 1, result.stdout, result.stderr))
    why = impossible_reason(style, failures)
    raise SystemExit(why)


def impossible_reason(style, failures):
    last_stdout = failures[-1][1].strip()
    last_stderr = failures[-1][2].strip()
    return (
        "style constraints made contrast verification impossible after 5 attempts\n"
        f"style: {style['id']}\n"
        "likely constraint: color.chromaRange combined with fixed contrast-gates "
        "could not produce passing semantic action/text/border pairs inside the style ranges\n"
        f"last token_gen.py --verify stdout:\n{last_stdout}\n"
        f"last stderr:\n{last_stderr}"
    )


def run_token_gen(schema_path, out_dir):
    result = subprocess.run(
        [sys.executable, str(TOKEN_GEN), str(schema_path), "--format", "css", "--out", str(out_dir)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout)
    return result.stdout


def command_apply(args):
    style, _path = load_style(args.style)
    modifiers = load_modifiers(args.modifier)
    style = compose_style(style, modifiers)
    schema, attempts, report = verified_schema(style, args.hue)
    schema["style"]["verification"] = {
        "verifiedBy": "token_gen.py --verify",
        "attempts": attempts,
        "result": "PASS",
    }
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        schema_path = out / "tokens.schema.json"
        schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        run_token_gen(schema_path, out)
        print(f"wrote {schema_path}")
        print(f"wrote {out / 'tokens.css'}")
        print(f"verified in {attempts} attempt(s)")
    else:
        print(json.dumps(schema, indent=2))
        print(f"verified in {attempts} attempt(s)", file=sys.stderr)
        if args.show_verify_report:
            print(report, file=sys.stderr)


def command_list(_args):
    for path in style_files():
        style = json.loads(path.read_text(encoding="utf-8"))
        print(f"{style['id']:<24} {style['intent']}")
    if modifier_files():
        print("\nModifiers:")
        for path in modifier_files():
            modifier = json.loads(path.read_text(encoding="utf-8"))
            print(f"{modifier['id']:<24} {modifier['intent']}")


def surface_match(surface, values):
    surface = slug(surface)
    return surface in {slug(v) for v in values}


def command_explain(args):
    style, _path = load_style(args.style)
    modifiers = load_modifiers(args.modifier)
    if modifiers:
        style = compose_style(style, modifiers)
    print(f"{style['name']} ({style['id']})")
    print(style["intent"])
    if args.surface:
        if surface_match(args.surface, style["worksFor"]):
            print(f"Suitability for {args.surface}: YES")
            print("Reason: the surface appears in worksFor.")
        elif surface_match(args.surface, style["avoidFor"]):
            print(f"Suitability for {args.surface}: NO")
            print("Reason: the surface appears in avoidFor.")
        else:
            print(f"Suitability for {args.surface}: CONDITIONAL")
            print("Reason: the surface is not explicitly covered; check density, state, and accessibility risks before applying.")
    print("Works for: " + ", ".join(style["worksFor"]))
    print("Avoid for: " + ", ".join(style["avoidFor"]))
    if style.get("accessibilityWarnings"):
        print("Accessibility warnings:")
        for warning in style["accessibilityWarnings"]:
            print(f"- Risk: {warning['risk']}")
            print(f"  Mitigation: {warning['mitigation']}")
    if style.get("fallbacks"):
        print("Fallbacks:")
        for fallback in style["fallbacks"]:
            print(f"- {fallback['condition']}: {fallback['response']}")
    print("Prohibitions: " + ", ".join(style["prohibitions"]))
    if style.get("modifiers"):
        print("Modifiers: " + ", ".join(m["id"] for m in style["modifiers"]))


def command_matrix(args):
    styles = [(json.loads(path.read_text(encoding="utf-8")), path) for path in style_files()]
    modifiers = [(json.loads(path.read_text(encoding="utf-8")), path) for path in modifier_files()]
    valid = 0
    invalid = 0
    for style, _style_path in styles:
        for modifier, _modifier_path in modifiers:
            validate_modifier_contract(modifier)
            problems = modifier_conflicts(style, [modifier])
            verdict = "INVALID" if problems else "VALID"
            if problems:
                invalid += 1
            else:
                valid += 1
            reason = "; ".join(problems) if problems else "compatible"
            print(f"{style['id']:<24} x {modifier['id']:<10} {verdict:<7} {reason}")
    print(f"\nValid combinations: {valid}")
    print(f"Invalid combinations: {invalid}")
    if args.require_over is not None and valid <= args.require_over:
        raise SystemExit(f"valid combination count {valid} did not exceed {args.require_over}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    apply_cmd = sub.add_parser("apply", help="derive and verify tokens from a style")
    apply_cmd.add_argument("style")
    apply_cmd.add_argument("--hue", required=True, type=float)
    apply_cmd.add_argument("--modifier", action="append", default=[], help="compose a style modifier; repeatable")
    apply_cmd.add_argument("--out")
    apply_cmd.add_argument("--show-verify-report", action="store_true")
    apply_cmd.set_defaults(func=command_apply)

    list_cmd = sub.add_parser("list", help="list available styles")
    list_cmd.set_defaults(func=command_list)

    explain_cmd = sub.add_parser("explain", help="explain style suitability for a surface")
    explain_cmd.add_argument("style")
    explain_cmd.add_argument("--surface")
    explain_cmd.add_argument("--modifier", action="append", default=[])
    explain_cmd.set_defaults(func=command_explain)

    matrix_cmd = sub.add_parser("matrix", help="print base style x modifier compatibility")
    matrix_cmd.add_argument("--require-over", type=int)
    matrix_cmd.set_defaults(func=command_matrix)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
