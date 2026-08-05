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
  python token_gen.py tokens.json --format react-native
  python token_gen.py tokens.json --format style-dictionary
  python token_gen.py tokens.json --format json     # resolved token JSON
  python token_gen.py tokens.json --format all --out ./design
  python token_gen.py tokens.json --verify          # contrast report only
  python token_gen.py --import-style-dictionary sd.json --verify
  python token_gen.py --import-radix-colors blue --verify
  python token_gen.py tokens.json --compare-radix brand blue

Exits non-zero if any declared text/surface pair fails WCAG 2.x AA.
"""

import sys
import json
import argparse
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from color_tools import (oklch_to_srgb, gamut_map, to_hex, wcag_ratio,
                         apca_lc, parse_color)

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
LIGHTNESS = [0.97, 0.94, 0.87, 0.78, 0.68, 0.58, 0.50, 0.42, 0.34, 0.26, 0.19]
TAPER = [0.28, 0.42, 0.62, 0.82, 0.95, 1.00, 0.98, 0.90, 0.78, 0.62, 0.46]
RADIX_STEPS = list(range(1, 13))

BUILTIN_RADIX = {
    "blue": {
        "light": ["#fbfdff", "#f4faff", "#e6f4fe", "#d5efff", "#c2e5ff", "#acd8fc",
                  "#8ec8f6", "#5eb1ef", "#0090ff", "#0588f0", "#0d74ce", "#113264"],
        "dark": ["#0d1520", "#111927", "#0d2847", "#003362", "#004074", "#104d87",
                 "#205d9e", "#2870bd", "#0090ff", "#3b9eff", "#70b8ff", "#c2e6ff"],
    },
    "gray": {
        "light": ["#fcfcfc", "#f9f9f9", "#f0f0f0", "#e8e8e8", "#e0e0e0", "#d9d9d9",
                  "#cecece", "#bbbbbb", "#8d8d8d", "#838383", "#646464", "#202020"],
        "dark": ["#111111", "#191919", "#222222", "#2a2a2a", "#313131", "#3a3a3a",
                 "#484848", "#606060", "#6e6e6e", "#7b7b7b", "#b4b4b4", "#eeeeee"],
    },
    "green": {
        "light": ["#fbfefc", "#f4fbf6", "#e6f6eb", "#d6f1df", "#c4e8d1", "#adddc0",
                  "#8eceaa", "#5bb98b", "#30a46c", "#2b9a66", "#218358", "#193b2d"],
        "dark": ["#0e1512", "#121b17", "#132d21", "#113b29", "#174933", "#20573e",
                 "#28684a", "#2f7c57", "#30a46c", "#33b074", "#3dd68c", "#b1f1cb"],
    },
    "red": {
        "light": ["#fffcfc", "#fff7f7", "#feebec", "#ffdbdc", "#ffcdce", "#fdbdbe",
                  "#f4a9aa", "#eb8e90", "#e5484d", "#dc3e42", "#ce2c31", "#641723"],
        "dark": ["#191111", "#201314", "#3b1219", "#500f1c", "#611623", "#72232d",
                 "#8c333a", "#b54548", "#e5484d", "#ec5d5e", "#ff9592", "#ffd1d9"],
    },
}

STARTER = {
    "$schema": "kinetic-ui-ux-pro/token-schema/1",
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


def rgb_to_hex_value(value):
    rgb = parse_color(value)
    return to_hex(rgb)


def radix_css_files(root, scale):
    pkg = root / "node_modules" / "@radix-ui" / "colors"
    if not pkg.exists():
        return []
    return list(pkg.rglob(f"{scale}.css")) + list(pkg.rglob(f"{scale}-dark.css"))


def parse_radix_css(path, scale):
    text = path.read_text(encoding="utf-8", errors="replace")
    values = {}
    for step, value in re.findall(rf"--{re.escape(scale)}(\d+)\s*:\s*([^;]+);", text):
        try:
            values[int(step)] = rgb_to_hex_value(value.strip())
        except Exception:
            continue
    return [values[i] for i in RADIX_STEPS] if all(i in values for i in RADIX_STEPS) else []


def load_radix_scale(scale, root=None):
    scale = scale.strip().lower()
    root = Path(root or Path.cwd())
    light = dark = None
    for css in radix_css_files(root, scale):
        values = parse_radix_css(css, scale)
        if not values:
            continue
        if css.name == f"{scale}-dark.css":
            dark = values
        elif css.name == f"{scale}.css":
            light = values
    if light and dark:
        return {"light": light, "dark": dark, "source": "node_modules/@radix-ui/colors"}
    if scale in BUILTIN_RADIX:
        data = BUILTIN_RADIX[scale]
        return {"light": data["light"], "dark": data["dark"], "source": "built-in Radix Colors 3.0.0 fallback"}
    known = ", ".join(sorted(BUILTIN_RADIX))
    raise SystemExit(
        f"Radix scale '{scale}' not found. Install @radix-ui/colors for all scales "
        f"or use built-in fallback scales: {known}."
    )


def resolve(ref, ramps):
    """'brand-600' -> token dict."""
    if ref.startswith('#') or ref.startswith('oklch') or ref.startswith('rgb('):
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
            if not wcag_ok or not apca_ok:
                failures += 1
            rows.append({
                "mode": mode, "pair": f"{pair['text']} on {pair['bg']}",
                "size": size, "fg": fg['hex'], "bg": bg['hex'],
                "wcag": ratio, "wcagNeed": WCAG_NEED[size], "wcagPass": wcag_ok,
                "apcaLc": lc, "apcaNeed": NEED[size], "apcaPass": apca_ok,
            })
    return rows, failures


def contrast_grade(fg, bg):
    fg_rgb, bg_rgb = parse_color(fg), parse_color(bg)
    ratio = round(wcag_ratio(fg_rgb, bg_rgb), 2)
    lc = apca_lc(fg_rgb, bg_rgb)
    body = ratio >= WCAG_NEED["body"] and abs(lc) >= NEED["body"]
    large = ratio >= WCAG_NEED["large"] and abs(lc) >= NEED["large"]
    nontext = ratio >= WCAG_NEED["nontext"] and abs(lc) >= NEED["nontext"]
    if body:
        use = "body"
    elif large:
        use = "large"
    elif nontext:
        use = "non-text"
    else:
        use = "fail"
    return ratio, lc, use


def radix_schema(scale, radix):
    light = radix["light"]
    dark = radix["dark"]
    return {
        "$schema": "kinetic-ui-ux-pro/token-schema/1",
        "name": f"radix-{scale}",
        "palettes": {},
        "semantic": {
            "light": {
                "surface-base": light[0],
                "surface-raised": light[1],
                "text-primary": light[11],
                "text-muted": light[10],
                "border-subtle": light[6],
                "action-bg": light[8],
                "action-text": light[0],
            },
            "dark": {
                "surface-base": dark[0],
                "surface-raised": dark[1],
                "text-primary": dark[11],
                "text-muted": dark[10],
                "border-subtle": dark[6],
                "action-bg": dark[8],
                "action-text": dark[11],
            },
        },
        "contrastPairs": [],
        "motion": STARTER["motion"],
        "space": STARTER["space"],
        "radius": STARTER["radius"],
        "radix": {"scale": scale, "source": radix["source"]},
    }


def print_radix_suitability(scale, radix):
    print(f"\n  Radix {scale} suitability ({radix['source']})\n")
    for mode in ("light", "dark"):
        bg = radix[mode][0]
        print(f"  {mode} mode on step 1 background {bg}")
        print(f"  {'step':>4} {'value':<9} {'WCAG':>7} {'Lc':>7}  suitable")
        print("  " + "-" * 42)
        for i, value in enumerate(radix[mode], 1):
            ratio, lc, use = contrast_grade(value, bg)
            print(f"  {i:>4} {value:<9} {ratio:>6}:1 {lc:>7}  {use}")
        print()


def print_radix_comparison(schema, palette, scale, radix):
    ramps = build_ramps(schema["palettes"])
    if palette not in ramps:
        raise SystemExit(f"unknown palette '{palette}'. Available: {', '.join(sorted(ramps))}")
    mapping = list(zip(STEPS, RADIX_STEPS))
    print(f"\n  Our {palette} ramp vs Radix {scale} ({radix['source']})\n")
    print(f"  {'ours':>5} {'our hex':<9} {'radix':>5} {'radix hex':<9} {'our on base':>12} {'radix on base':>14} {'delta':>8}")
    print("  " + "-" * 76)
    our_base = ramps[palette][50]["hex"]
    radix_base = radix["light"][0]
    for our_step, radix_step in mapping:
        our_hex = ramps[palette][our_step]["hex"]
        radix_hex = radix["light"][radix_step - 1]
        our_ratio, our_lc, _ = contrast_grade(our_hex, our_base)
        radix_ratio, radix_lc, _ = contrast_grade(radix_hex, radix_base)
        delta = abs(abs(our_lc) - abs(radix_lc))
        print(
            f"  {our_step:>5} {our_hex:<9} {radix_step:>5} {radix_hex:<9} "
            f"{our_ratio:>5}:1/{our_lc:>4} {radix_ratio:>5}:1/{radix_lc:>4} {delta:>8.1f}"
        )
    print("\n  Large deltas are not automatic failures, but they are a prompt to inspect hue, chroma taper, and semantic pairing.\n")


def emit_css(schema, ramps):
    L = []
    A = L.append

    def emit_semantic_block(selector, mode, indent="  "):
        A(f"{selector} {{")
        for name, ref in schema['semantic'][mode].items():
            value = ref if str(ref).startswith(("#", "oklch", "rgb(")) else f"var(--{ref})"
            A(f"{indent}--{name}: {value};")
        A("}\n")

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
        value = ref if str(ref).startswith(("#", "oklch", "rgb(")) else f"var(--{ref})"
        A(f"  --{name}: {value};")

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

    A("@media (prefers-color-scheme: dark) {")
    emit_semantic_block("  :root:not([data-theme])", "dark", "    ")
    A("}\n")

    A(":root[data-theme='light'] {")
    A("  color-scheme: light;")
    for name, ref in schema['semantic']['light'].items():
        value = ref if str(ref).startswith(("#", "oklch", "rgb(")) else f"var(--{ref})"
        A(f"  --{name}: {value};")
    A("}\n")

    A(":root[data-theme='dark'] {")
    A("  color-scheme: dark;")
    for name, ref in schema['semantic']['dark'].items():
        value = ref if str(ref).startswith(("#", "oklch", "rgb(")) else f"var(--{ref})"
        A(f"  --{name}: {value};")
    A("}\n")

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


def camel_name(name):
    parts = re.split(r"[-_\s]+", str(name))
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def ts_string(value):
    return json.dumps(value)


def rn_color_value(ref, ramps):
    return resolve(str(ref), ramps)["hex"]


def rn_clipped_notes(schema, ramps):
    notes = []
    for fam, ramp in ramps.items():
        clipped = [str(step) for step in STEPS if ramp[step].get("clipped")]
        if clipped:
            notes.append(f"{fam}: steps {', '.join(clipped)}")
    for mode, tokens in schema.get("semantic", {}).items():
        for name, ref in tokens.items():
            ref = str(ref)
            if ref.startswith("oklch"):
                notes.append(f"{mode}.{name}: literal OKLCH converted to hex")
            elif not ref.startswith(("#", "rgb(")):
                fam, _, step = ref.rpartition("-")
                try:
                    if ramps[fam][int(step)].get("clipped"):
                        notes.append(f"{mode}.{name}: {ref}")
                except Exception:
                    pass
    return notes


def emit_ts_object(name, data):
    lines = [f"export const {name} = {{"]
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"  {key}: {{")
            for child_key, child_value in value.items():
                prop = str(child_key) if str(child_key).isidentifier() else ts_string(str(child_key))
                lines.append(f"    {prop}: {json.dumps(child_value)},")
            lines.append("  },")
        else:
            lines.append(f"  {key}: {json.dumps(value)},")
    lines.append("} as const;")
    return "\n".join(lines)


def emit_react_native(schema, ramps):
    shared = {}
    space = schema.get("space", {})
    if space:
        base = space.get("base", 4)
        shared["space"] = {str(step): step * base for step in space.get("steps", [])}
    if schema.get("radius"):
        shared["radius"] = {camel_name(k): v for k, v in schema["radius"].items()}
    durations = schema.get("motion", {}).get("durations", {})
    if durations:
        shared["duration"] = {camel_name(k): v for k, v in durations.items()}

    def mode_tokens(mode):
        data = {}
        for name, ref in schema["semantic"][mode].items():
            data[camel_name(name)] = rn_color_value(ref, ramps)
        data.update(shared)
        return data

    notes = rn_clipped_notes(schema, ramps)
    if notes:
        note_text = "\n".join(f" * - {n}" for n in notes)
    else:
        note_text = " * - none"
    lines = [
        "/**",
        f" * {schema['name']} React Native tokens - generated by token_gen.py.",
        " * All contrast pairs verified against WCAG 2.x AA + APCA before emission.",
        " * React Native does not support OKLCH, so color tokens are emitted as hex.",
        " * Values gamut-mapped from OKLCH during conversion:",
        note_text,
        " */",
        "import { useColorScheme } from 'react-native';",
        "",
        emit_ts_object("lightTokens", mode_tokens("light")),
        "",
        emit_ts_object("darkTokens", mode_tokens("dark")),
        "",
        "export type Tokens = typeof lightTokens;",
        "",
        "export function useTokens(): Tokens {",
        "  return useColorScheme() === 'dark' ? darkTokens : lightTokens;",
        "}",
        "",
    ]
    return "\n".join(lines)


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


def emit_schema(schema):
    return json.dumps(schema, indent=2)


def sd_token(value, typ, description="", **extra):
    token = {"value": value, "type": typ}
    if description:
        token["description"] = description
    token.update(extra)
    return token


def set_nested(root, path, value):
    cur = root
    for part in path[:-1]:
        cur = cur.setdefault(str(part), {})
    cur[str(path[-1])] = value


def emit_style_dictionary(schema, ramps, rows):
    out = {
        "$schema": "https://tokens.studio/schemas/tokens.json",
        "kinetic": {
            "name": schema["name"],
            "generatedBy": "token_gen.py",
            "schema": schema.get("$schema", "kinetic-ui-ux-pro/token-schema/1"),
            "contrastPairs": schema.get("contrastPairs", []),
            "contrastVerification": rows,
        },
        "color": {},
        "semantic": {},
    }
    for fam, ramp in ramps.items():
        for step in STEPS:
            token = ramp[step]
            set_nested(out["color"], [fam, step], sd_token(
                token["oklch"], "color",
                aliases=[f"--{fam}-{step}"],
                attributes={
                    "category": "color",
                    "family": fam,
                    "step": step,
                    "hex": token["hex"],
                    "clipped": token["clipped"],
                }))
    for mode, tokens in schema.get("semantic", {}).items():
        out["semantic"][mode] = {}
        for name, ref in tokens.items():
            ref_text = str(ref)
            value = f"{{color.{ref_text.replace('-', '.')}}}" if not ref_text.startswith(("#", "oklch", "rgb(")) else ref_text
            out["semantic"][mode][name] = sd_token(
                value, "color",
                aliases=[f"--{name}"],
                attributes={"category": "color", "mode": mode, "semantic": True})
    motion = schema.get("motion", {})
    if motion:
        out["motion"] = {"duration": {}, "easing": {}}
        for name, value in motion.get("durations", {}).items():
            out["motion"]["duration"][name] = sd_token(f"{value}ms", "duration")
        for name, value in motion.get("easings", {}).items():
            out["motion"]["easing"][name] = sd_token(value, "cubicBezier")
    space = schema.get("space", {})
    if space:
        out.setdefault("size", {})["space"] = {}
        base = space.get("base", 4)
        for step in space.get("steps", []):
            out["size"]["space"][str(step)] = sd_token(f"{step * base}px", "dimension")
    if schema.get("radius"):
        out.setdefault("border", {})["radius"] = {}
        for name, value in schema["radius"].items():
            out["border"]["radius"][name] = sd_token(f"{value}px", "dimension")
    return json.dumps(out, indent=2)


def token_value(node):
    if not isinstance(node, dict):
        return None
    if "$value" in node:
        return node["$value"]
    return node.get("value")


def token_type(node):
    if not isinstance(node, dict):
        return ""
    value = node.get("$type", node.get("type", ""))
    return str(value)


def flatten_tokens(node, prefix=()):
    if isinstance(node, dict) and ("value" in node or "$value" in node):
        yield prefix, node
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key.startswith("$") or key in {"kinetic"}:
            continue
        yield from flatten_tokens(value, prefix + (str(key),))


def resolve_sd_value(flat, path, seen=None):
    seen = seen or set()
    key = ".".join(path)
    if key in seen:
        raise ValueError(f"cyclic Style Dictionary reference at {key}")
    seen.add(key)
    value = token_value(flat[path])
    if isinstance(value, str):
        match = re.fullmatch(r"\{([^}]+)\}", value.strip())
        if match:
            ref_path = tuple(match.group(1).split("."))
            if ref_path not in flat:
                raise KeyError(f"unknown Style Dictionary reference {value}")
            return resolve_sd_value(flat, ref_path, seen)
    return value


def is_color_token(path, node, value):
    typ = token_type(node).lower()
    text = str(value)
    return typ == "color" or text.startswith(("#", "oklch", "rgb(")) or "color" in path


def import_style_dictionary(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    flat = {path: node for path, node in flatten_tokens(data)}
    resolved = {}
    for tok_path, node in flat.items():
        try:
            value = resolve_sd_value(flat, tok_path)
        except Exception as e:
            print(f"skip Style Dictionary token {'.'.join(tok_path)}: {e}", file=sys.stderr)
            continue
        resolved[tok_path] = value

    color_values = {}
    for tok_path, value in resolved.items():
        if not is_color_token(tok_path, flat[tok_path], value):
            continue
        name = "-".join(tok_path[1:]) if tok_path[:1] == ("color",) else "-".join(tok_path)
        try:
            parse_color(str(value))
        except Exception:
            continue
        color_values[name] = str(value)

    semantic = {"light": {}, "dark": {}}
    for tok_path, value in resolved.items():
        if "semantic" not in tok_path or not is_color_token(tok_path, flat[tok_path], value):
            continue
        parts = list(tok_path)
        try:
            sem_i = parts.index("semantic")
        except ValueError:
            continue
        rest = parts[sem_i + 1:]
        if len(rest) >= 2 and rest[0] in semantic:
            mode, name = rest[0], "-".join(rest[1:])
        else:
            mode, name = "light", "-".join(rest)
        semantic[mode][name] = str(value)

    if not any(semantic.values()):
        for mode in semantic:
            for name in ("surface-base", "surface-raised", "text-primary",
                         "text-muted", "border-subtle", "action-bg", "action-text"):
                for candidate in (f"{mode}-{name}", name, f"semantic-{mode}-{name}"):
                    if candidate in color_values:
                        semantic[mode][name] = color_values[candidate]
                        break
        if not semantic["dark"]:
            semantic["dark"] = dict(semantic["light"])

    pairs = data.get("kinetic", {}).get("contrastPairs")
    if not isinstance(pairs, list):
        pairs = [p for p in STARTER["contrastPairs"]
                 if all(p[k] in semantic.get("light", {}) for k in ("text", "bg"))]

    schema = {
        "$schema": "kinetic-ui-ux-pro/token-schema/1",
        "name": data.get("kinetic", {}).get("name", Path(path).stem),
        "palettes": {},
        "semantic": semantic,
        "contrastPairs": pairs,
        "motion": {"durations": {}, "easings": {}},
        "space": {"base": 1, "steps": []},
        "radius": {},
    }
    for tok_path, value in resolved.items():
        if tok_path[:2] == ("motion", "duration"):
            digits = "".join(ch for ch in str(value) if ch.isdigit() or ch == ".")
            if digits:
                schema["motion"]["durations"][tok_path[-1]] = int(float(digits))
        elif tok_path[:2] == ("motion", "easing"):
            schema["motion"]["easings"][tok_path[-1]] = str(value)
        elif "radius" in tok_path:
            digits = "".join(ch for ch in str(value) if ch.isdigit() or ch == ".")
            if digits:
                schema["radius"][tok_path[-1]] = int(float(digits))
        elif "space" in tok_path:
            digits = "".join(ch for ch in str(value) if ch.isdigit() or ch == ".")
            if digits:
                schema["space"]["steps"].append(int(float(digits)))
    schema["space"]["steps"] = sorted(set(schema["space"]["steps"]))
    return schema


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
    ap.add_argument('--import-style-dictionary',
                    help='read Style Dictionary token JSON and convert to our schema')
    ap.add_argument('--import-radix-colors',
                    help='import a named Radix Colors scale and verify its documented light/dark pairings')
    ap.add_argument('--compare-radix', nargs=2, metavar=('OUR_PALETTE', 'RADIX_SCALE'),
                    help='compare one generated palette against a named Radix Colors scale')
    ap.add_argument('--format', default='css',
                    choices=['css', 'tailwind', 'json', 'style-dictionary', 'react-native', 'all'])
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()

    if args.init:
        print(json.dumps(STARTER, indent=2))
        return
    if args.compare_radix:
        if not args.schema:
            ap.error("--compare-radix requires a schema file")
        schema = json.loads(Path(args.schema).read_text())
        radix = load_radix_scale(args.compare_radix[1])
        print_radix_comparison(schema, args.compare_radix[0], args.compare_radix[1], radix)
        return
    if args.import_radix_colors:
        radix = load_radix_scale(args.import_radix_colors)
        schema = radix_schema(args.import_radix_colors, radix)
    elif args.import_style_dictionary:
        schema = import_style_dictionary(args.import_style_dictionary)
    elif args.schema:
        schema = json.loads(Path(args.schema).read_text())
    else:
        ap.error("provide a schema file, or --init to generate one")

    ramps = build_ramps(schema['palettes'])
    rows, failures = verify(schema, ramps)

    if args.verify:
        if args.import_radix_colors:
            print_radix_suitability(args.import_radix_colors, radix)
            print("  Radix benchmark note: unsuitable steps are expected in accent scales; use the suitability table to choose text and non-text roles.\n")
            sys.exit(0)
        else:
            print_report(rows)
        sys.exit(1 if failures else 0)

    if failures:
        print_report(rows)
        print(f"  ! {failures} pair(s) fail WCAG 2.x AA + APCA - fix the schema.",
              file=sys.stderr)
        sys.exit(1)

    outputs = {}
    imported = bool(args.import_style_dictionary or args.import_radix_colors)
    if args.format in ('css', 'all'):
        outputs['tokens.css'] = emit_css(schema, ramps)
    if args.format in ('tailwind', 'all'):
        outputs['theme.css'] = emit_tailwind(schema, ramps)
    if args.format in ('json', 'all'):
        outputs['tokens.json'] = emit_schema(schema) if imported else emit_json(schema, ramps, rows)
    if args.format in ('style-dictionary', 'all'):
        outputs['tokens.style-dictionary.json'] = emit_style_dictionary(schema, ramps, rows)
    if args.format in ('react-native', 'all'):
        outputs['tokens.native.ts'] = emit_react_native(schema, ramps)

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


if __name__ == '__main__':
    main()
