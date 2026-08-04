#!/usr/bin/env python3
"""
Deterministic design-token generation from a JSON schema.

Same input always produces the same output. No text generation, no guessing:
ramps are computed in OKLCH, gamut-mapped to sRGB, and every semantic pair is
contrast-verified against WCAG 2.x AA and APCA before emission.

Usage:
  python token_gen.py --init > tokens.json          # write a starter schema
  python token_gen.py tokens.json --format css      # CSS custom properties
  python token_gen.py tokens.json --format tailwind # tailwind v4 @theme
  python token_gen.py tokens.json --format json     # resolved token JSON
  python token_gen.py tokens.json --format all --out ./design
  python token_gen.py tokens.json --verify          # contrast report only

Exits non-zero if any declared text/surface pair fails WCAG 2.x AA.
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from color_tools import (oklch_to_srgb, gamut_map, to_hex, wcag_ratio,
                         apca_lc, parse_color)

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
LIGHTNESS = [0.97, 0.94, 0.87, 0.78, 0.68, 0.58, 0.50, 0.42, 0.34, 0.26, 0.19]
TAPER = [0.28, 0.42, 0.62, 0.82, 0.95, 1.00, 0.98, 0.90, 0.78, 0.62, 0.46]

STARTER = {
    "$schema": "kinetic-ux/token-schema/1",
    "name": "acme",
    "palettes": {
        "brand": {"hue": 265, "chroma": 0.18},
        "neutral": {"hue": 265, "chroma": 0.012},
        "danger": {"hue": 27, "chroma": 0.19},
        "success": {"hue": 150, "chroma": 0.15}
    },
    "semantic": {
        "light": {
            "surface-base": "neutral-50",
            "surface-raised": "neutral-50",
            "text-primary": "neutral-900",
            "text-muted": "neutral-800",
            "border-subtle": "neutral-500",
            "action-bg": "brand-700",
            "action-text": "neutral-50"
        },
        "dark": {
            "surface-base": "neutral-950",
            "surface-raised": "neutral-900",
            "text-primary": "neutral-50",
            "text-muted": "neutral-100",
            "border-subtle": "neutral-500",
            "action-bg": "brand-200",
            "action-text": "neutral-950"
        }
    },
    "contrastPairs": [
        {"text": "text-primary", "bg": "surface-base", "size": "body"},
        {"text": "text-muted", "bg": "surface-base", "size": "body"},
        {"text": "action-text", "bg": "action-bg", "size": "large"},
        {"text": "border-subtle", "bg": "surface-base", "size": "nontext"}
    ],
    "motion": {
        "durations": {"micro": 120, "local": 240, "view": 400, "reduced": 90},
        "easings": {
            "out": "cubic-bezier(.2,.8,.2,1)",
            "in": "cubic-bezier(.4,0,1,1)",
            "spring": "cubic-bezier(.34,1.56,.64,1)"
        }
    },
    "space": {"base": 4, "steps": [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32]},
    "radius": {"sm": 4, "md": 8, "lg": 12, "full": 9999}
}


def build_ramps(palettes):
    ramps = {}
    for name, cfg in palettes.items():
        hue, chroma = float(cfg['hue']), float(cfg['chroma'])
        ramp = {}
        for step, L, t in zip(STEPS, LIGHTNESS, TAPER):
            c_req = round(chroma * t, 4)
            c_fit, rgb = gamut_map(L, c_req, hue)
            ramp[step] = {
                "oklch": f"oklch({L} {c_fit} {hue})",
                "hex": to_hex(rgb), "rgb": rgb,
                "L": L, "C": c_fit, "H": hue,
                "clipped": c_fit < c_req - 1e-3,
            }
        ramps[name] = ramp
    return ramps


def resolve(ref, ramps):
    """'brand-600' -> token dict."""
    if ref.startswith('#') or ref.startswith('oklch'):
        rgb = parse_color(ref)
        return {"oklch": ref, "hex": to_hex(rgb), "rgb": rgb, "clipped": False}
    fam, _, step = ref.rpartition('-')
    if fam not in ramps:
        raise KeyError(f"unknown palette '{fam}' in reference '{ref}'")
    try:
        return ramps[fam][int(step)]
    except (ValueError, KeyError):
        raise KeyError(f"unknown step '{step}' in reference '{ref}'")


NEED = {'body': 90, 'large': 75, 'headline': 60, 'display': 45, 'nontext': 30}
WCAG_NEED = {'body': 4.5, 'large': 3.0, 'headline': 3.0,
             'display': 3.0, 'nontext': 3.0}


def verify(schema, ramps):
    rows, failures = [], 0
    for mode, tokens in schema['semantic'].items():
        for pair in schema.get('contrastPairs', []):
            try:
                fg = resolve(tokens[pair['text']], ramps)
                bg = resolve(tokens[pair['bg']], ramps)
            except KeyError as e:
                rows.append({"mode": mode, "pair": f"{pair['text']}/{pair['bg']}",
                             "error": str(e)})
                failures += 1
                continue
            size = pair.get('size', 'body')
            ratio = round(wcag_ratio(fg['rgb'], bg['rgb']), 2)
            lc = apca_lc(fg['rgb'], bg['rgb'])
            wcag_ok = ratio >= WCAG_NEED[size]
            apca_ok = abs(lc) >= NEED[size]
            if not wcag_ok:
                failures += 1
            rows.append({
                "mode": mode, "pair": f"{pair['text']} on {pair['bg']}",
                "size": size, "fg": fg['hex'], "bg": bg['hex'],
                "wcag": ratio, "wcagNeed": WCAG_NEED[size], "wcagPass": wcag_ok,
                "apcaLc": lc, "apcaNeed": NEED[size], "apcaPass": apca_ok,
            })
    return rows, failures


def emit_css(schema, ramps):
    L = []
    A = L.append
    A(f"/* {schema['name']} design tokens — generated by token_gen.py")
    A("   Deterministic: same schema always yields this file.")
    A("   All contrast pairs verified against WCAG 2.x AA + APCA. */\n")

    A("@supports not (color: oklch(0 0 0)) {\n  :root {")
    for fam, ramp in ramps.items():
        for step in STEPS:
            A(f"    --{fam}-{step}: {ramp[step]['hex']};")
    A("  }\n}\n")

    A(":root {\n  color-scheme: light dark;\n")
    A("  /* primitives */")
    for fam, ramp in ramps.items():
        for step in STEPS:
            t = ramp[step]
            note = "  /* chroma reduced to fit sRGB */" if t['clipped'] else ""
            A(f"  --{fam}-{step}: {t['oklch']};{note}")
    A("\n  /* semantic — reference these in components, never primitives */")
    for name, ref in schema['semantic']['light'].items():
        A(f"  --{name}: var(--{ref});")

    m = schema.get('motion', {})
    if m:
        A("\n  /* motion */")
        for k, v in m.get('durations', {}).items():
            A(f"  --dur-{k}: {v}ms;")
        for k, v in m.get('easings', {}).items():
            A(f"  --ease-{k}: {v};")

    sp = schema.get('space', {})
    if sp:
        A("\n  /* space */")
        for s in sp.get('steps', []):
            A(f"  --space-{s}: {s * sp.get('base', 4)}px;")

    for k, v in schema.get('radius', {}).items():
        A(f"  --radius-{k}: {v}px;")
    A("}\n")

    A("@media (prefers-color-scheme: dark) {\n  :root {")
    for name, ref in schema['semantic']['dark'].items():
        A(f"    --{name}: var(--{ref});")
    A("  }\n}\n")

    A("@media (prefers-contrast: more) {")
    A("  :root { --border-subtle: var(--text-primary); }")
    A("}\n")
    A("@media (prefers-reduced-transparency: reduce) {")
    A("  :root { --surface-raised: var(--surface-base); }")
    A("}\n")
    A("@media (forced-colors: active) {")
    A("  /* fills overridden by UA — structure survives on borders */")
    A("  :focus-visible { outline: 2px solid Highlight; outline-offset: 2px; }")
    A("}\n")
    A("@media (prefers-reduced-motion: reduce) {")
    A("  :root { --dur-micro: var(--dur-reduced); --dur-local: var(--dur-reduced);")
    A("          --dur-view: var(--dur-reduced); }")
    A("}")
    return "\n".join(L)


def emit_tailwind(schema, ramps):
    L = [f"/* {schema['name']} — Tailwind v4 @theme, generated */", "@theme {"]
    for fam, ramp in ramps.items():
        for step in STEPS:
            L.append(f"  --color-{fam}-{step}: {ramp[step]['oklch']};")
    L.append("")
    for name in schema['semantic']['light']:
        L.append(f"  --color-{name}: var(--{name});")
    for k, v in schema.get('motion', {}).get('durations', {}).items():
        L.append(f"  --animate-duration-{k}: {v}ms;")
    for k, v in schema.get('radius', {}).items():
        L.append(f"  --radius-{k}: {v}px;")
    L.append("}")
    return "\n".join(L)


def emit_json(schema, ramps, rows):
    return json.dumps({
        "name": schema['name'],
        "generatedBy": "token_gen.py",
        "primitives": {f: {s: {"oklch": r[s]['oklch'], "hex": r[s]['hex'],
                               "clipped": r[s]['clipped']} for s in STEPS}
                       for f, r in ramps.items()},
        "semantic": schema['semantic'],
        "motion": schema.get('motion', {}),
        "space": schema.get('space', {}),
        "radius": schema.get('radius', {}),
        "contrastVerification": rows,
    }, indent=2)


def print_report(rows):
    print(f"\n  Contrast verification ({len(rows)} pairs)\n")
    print(f"  {'mode':<6} {'pair':<34} {'WCAG':>7}  {'':<4} {'Lc':>6}  ")
    print("  " + "-" * 68)
    for r in rows:
        if 'error' in r:
            print(f"  {r['mode']:<6} {r['pair']:<34}  ERROR {r['error']}")
            continue
        wf = "PASS" if r['wcagPass'] else "FAIL"
        af = "pass" if r['apcaPass'] else "fail"
        print(f"  {r['mode']:<6} {r['pair']:<34} {r['wcag']:>6}:1 {wf:<5}"
              f" {r['apcaLc']:>6} {af}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('schema', nargs='?')
    ap.add_argument('--init', action='store_true')
    ap.add_argument('--format', default='css',
                    choices=['css', 'tailwind', 'json', 'all'])
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()

    if args.init:
        print(json.dumps(STARTER, indent=2))
        return
    if not args.schema:
        ap.error("provide a schema file, or --init to generate one")

    schema = json.loads(Path(args.schema).read_text())
    ramps = build_ramps(schema['palettes'])
    rows, failures = verify(schema, ramps)

    if args.verify:
        print_report(rows)
        sys.exit(1 if failures else 0)

    outputs = {}
    if args.format in ('css', 'all'):
        outputs['tokens.css'] = emit_css(schema, ramps)
    if args.format in ('tailwind', 'all'):
        outputs['theme.css'] = emit_tailwind(schema, ramps)
    if args.format in ('json', 'all'):
        outputs['tokens.json'] = emit_json(schema, ramps, rows)

    if args.out:
        d = Path(args.out)
        d.mkdir(parents=True, exist_ok=True)
        for fn, body in outputs.items():
            (d / fn).write_text(body)
            print(f"  wrote {d / fn}")
        print_report(rows)
    else:
        for body in outputs.values():
            print(body)

    if failures:
        print(f"  ! {failures} pair(s) fail WCAG 2.x AA — fix the schema.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
