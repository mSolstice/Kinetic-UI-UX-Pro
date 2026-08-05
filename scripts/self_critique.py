#!/usr/bin/env python3
"""
Static and capability-gated visual design critique for generated UI.

Tier 1 is structural and always runs. Tier 2 uses Playwright only when it is
installed and a renderable HTML target is available; otherwise absence is
reported plainly and no visual claim is made.
"""

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from color_tools import parse_color, wcag_ratio
except Exception:
    parse_color = wcag_ratio = None

CODE_EXTS = {
    ".css", ".scss", ".ts", ".tsx", ".js", ".jsx",
    ".html", ".htm", ".svelte", ".vue", ".astro",
}
STYLE_DIR = Path(__file__).resolve().parents[1] / "templates" / "styles"
VISUAL_UNAVAILABLE = "Visual verification unavailable in this environment; structural critique ran instead."

CSS_BLOCK_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.S)
CSS_DECL_RE = re.compile(r"(?P<prop>[-\w]+)\s*:\s*(?P<value>[^;{}]+)")
JS_STYLE_RE = re.compile(r"(?P<prop>[A-Za-z][A-Za-z0-9_]*)\s*:\s*(?P<quote>['\"]?)(?P<value>-?\d+(?:\.\d+)?(?:px|rem|em|%)?|#[0-9a-fA-F]{3,8}|var\([^)]*\))(?P=quote)")
CLASS_RE = re.compile(r"(?:className|class)\s*=\s*(?:\{?\s*)?['\"]([^'\"]+)['\"]")
VALUE_RE = re.compile(r"(?<![\w.-])-?\d+(?:\.\d+)?(?:px|rem|em|%)?\b")
COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b|oklch\([^)]*\)|rgba?\([^)]*\)|var\(--(?:accent|brand|action)[^)]+\)", re.I)
INTERACTIVE_RE = re.compile(r"<(?:button|a|input|select|textarea|Pressable|TouchableOpacity|TouchableHighlight)\b|\b(?:onClick|onPress|role=['\"]button|className=['\"][^'\"]*\bbtn\b)", re.I)
ACCENT_RE = re.compile(r"\b(?:accent|brand|action-bg|actionBg|primary)\b|var\(--(?:accent|brand|action)", re.I)
SHADOW_RE = re.compile(r"(?:box-shadow|text-shadow)\s*:\s*([^;{}]+)|\bshadow(?:Color|Offset|Opacity|Radius)?\s*:\s*([^,\n}]+)|\bshadow-[\w/-]+")
RADIUS_RE = re.compile(r"(?:border-radius|borderRadius|radius)\s*:\s*([^;,\n}]+)|\brounded(?:-[\w/\[\].]+)?")
FONT_SIZE_RE = re.compile(r"(?:font-size|fontSize)\s*:\s*([^;,\n}]+)|\btext-\[([^\]]+)\]|\btext-(xs|sm|base|lg|xl|[2-9]xl)\b")
FONT_WEIGHT_RE = re.compile(r"(?:font-weight|fontWeight)\s*:\s*([^;,\n}]+)|\bfont-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)\b")
SPACING_PROP_RE = re.compile(r"^(?:margin|padding|gap|row-gap|column-gap|margin-(?:top|right|bottom|left|inline|block)|padding-(?:top|right|bottom|left|inline|block))$", re.I)
TYPE_SCALE_CLASSES = {
    "xs": 12.0, "sm": 14.0, "base": 16.0, "lg": 18.0, "xl": 20.0,
    "2xl": 24.0, "3xl": 30.0, "4xl": 36.0, "5xl": 48.0,
    "6xl": 60.0, "7xl": 72.0, "8xl": 96.0, "9xl": 128.0,
}
WEIGHTS = {
    "thin": 100, "extralight": 200, "light": 300, "normal": 400,
    "medium": 500, "semibold": 600, "bold": 700, "extrabold": 800,
    "black": 900,
}


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    evidence: str
    fix: str


def line_for(text, index):
    return text.count("\n", 0, max(index, 0)) + 1


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*", "", text)


def target_files(target):
    path = Path(target)
    if path.is_file():
        return [path] if path.suffix in CODE_EXTS else []
    if path.is_dir():
        return [p for p in path.rglob("*") if p.is_file() and p.suffix in CODE_EXTS]
    raise SystemExit(f"target not found: {target}")


def norm_prop(prop):
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", prop).replace("_", "-").lower()


def number_value(raw):
    raw = str(raw).strip().strip("'\"")
    if raw.startswith("var("):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not m:
        return None
    value = float(m.group(0))
    unit = raw[m.end():].strip().lower()
    if unit.startswith("rem") or unit.startswith("em"):
        return value * 16
    if unit.startswith("%"):
        return None
    return value


def display_num(value):
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def nearest_scale(value, scale, tol=0.75):
    if value is None or not scale:
        return True
    return min(abs(value - s) for s in scale) <= tol


def collect_token_scales(files):
    spacing = set()
    types = set(TYPE_SCALE_CLASSES.values())
    radii = set()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for value in re.findall(r"--space-[\w-]+\s*:\s*([^;]+);", text):
            parsed = number_value(value)
            if parsed is not None:
                spacing.add(parsed)
        for value in re.findall(r"--(?:font-size|text)-[\w-]+\s*:\s*([^;]+);", text):
            parsed = number_value(value)
            if parsed is not None:
                types.add(parsed)
        for value in re.findall(r"--radius-[\w-]+\s*:\s*([^;]+);", text):
            parsed = number_value(value)
            if parsed is not None:
                radii.add(parsed)
    if not spacing:
        spacing = {0, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128}
    if not radii:
        radii = {0, 2, 4, 8, 12, 16, 24, 9999}
    return sorted(spacing), sorted(types), sorted(radii)


def read_style(style_id):
    if not style_id:
        return {}
    path = STYLE_DIR / f"{style_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"could not load style '{style_id}': {exc}")


def css_rules(text):
    clean = strip_comments(text)
    return list(CSS_BLOCK_RE.finditer(clean))


def collect_metrics(files):
    metrics = {
        "spacing": [], "font_sizes": [], "weights": [], "radii": [],
        "shadows": [], "align": [], "padding_by_selector": [],
        "density_ratios": [], "accent": 0, "interactive": 0, "gradient_heroes": [],
        "colors": [],
    }
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        metrics["interactive"] += len(INTERACTIVE_RE.findall(text))
        metrics["accent"] += len(ACCENT_RE.findall(text))
        for m in COLOR_RE.finditer(text):
            metrics["colors"].append((path, line_for(text, m.start()), m.group(0)))
        for block in css_rules(text):
            selector = " ".join(block.group("selector").split())
            body = block.group("body")
            decls = [(d.group("prop").strip(), d.group("value").strip(), d.start()) for d in CSS_DECL_RE.finditer(body)]
            body_start = block.start("body")
            padding_values = []
            fixed_sizes = []
            align_values = []
            for prop, raw, rel_index in decls:
                prop_n = norm_prop(prop)
                values = VALUE_RE.findall(raw)
                if prop_n in ("width", "height", "inline-size", "block-size"):
                    parsed_size = number_value(raw)
                    if parsed_size and parsed_size > 0:
                        fixed_sizes.append(parsed_size)
                if SPACING_PROP_RE.match(prop_n):
                    for value in values:
                        parsed = number_value(value)
                        if parsed is not None:
                            metrics["spacing"].append((path, line_for(text, body_start + rel_index), value, parsed, prop_n, selector))
                            if prop_n.startswith("padding"):
                                padding_values.append(parsed)
                if prop_n == "font-size":
                    parsed = number_value(raw)
                    if parsed is not None:
                        metrics["font_sizes"].append((path, line_for(text, body_start + rel_index), raw, parsed, selector))
                if prop_n == "font-weight":
                    weight = parse_weight(raw)
                    if weight:
                        metrics["weights"].append((path, line_for(text, body_start + rel_index), raw, weight, selector))
                if prop_n == "border-radius":
                    parsed = number_value(raw)
                    if parsed is not None:
                        metrics["radii"].append((path, line_for(text, body_start + rel_index), raw, parsed, selector))
                if prop_n in ("box-shadow", "text-shadow"):
                    metrics["shadows"].append((path, line_for(text, body_start + rel_index), raw, selector))
                if prop_n in ("align-items", "justify-content", "text-align", "place-items"):
                    align_values.append((prop_n, raw))
            if len(padding_values) >= 1:
                avg_padding = sum(padding_values) / len(padding_values)
                metrics["padding_by_selector"].append((path, line_for(text, block.start()), selector, avg_padding))
                if fixed_sizes:
                    content_size = min(fixed_sizes)
                    metrics["density_ratios"].append((path, line_for(text, block.start()), selector, avg_padding / content_size))
            if mixed_alignment(align_values):
                metrics["align"].append((path, line_for(text, block.start()), selector, align_values))
            if re.search(r"\bhero\b", selector, re.I) and re.search(r"(?:linear|radial|conic)-gradient", body, re.I):
                metrics["gradient_heroes"].append((path, line_for(text, block.start()), selector))

        for m in JS_STYLE_RE.finditer(text):
            prop = norm_prop(m.group("prop"))
            raw = m.group("value")
            parsed = number_value(raw)
            line = line_for(text, m.start())
            if SPACING_PROP_RE.match(prop) and parsed is not None:
                metrics["spacing"].append((path, line, raw, parsed, prop, "inline-style"))
            if prop == "font-size" and parsed is not None:
                metrics["font_sizes"].append((path, line, raw, parsed, "inline-style"))
            if prop == "font-weight":
                weight = parse_weight(raw)
                if weight:
                    metrics["weights"].append((path, line, raw, weight, "inline-style"))
            if prop == "border-radius" and parsed is not None:
                metrics["radii"].append((path, line, raw, parsed, "inline-style"))
        for m in CLASS_RE.finditer(text):
            classes = m.group(1).split()
            line = line_for(text, m.start())
            if ("items-center" in classes or "justify-center" in classes) and any(c in classes for c in ("text-left", "text-start", "items-start", "justify-start")):
                metrics["align"].append((path, line, "className", [("class", " ".join(classes))]))
            for cls in classes:
                if cls.startswith(("p-", "px-", "py-", "pt-", "pr-", "pb-", "pl-", "m-", "mx-", "my-", "mt-", "mr-", "mb-", "ml-", "gap-", "gap-x-", "gap-y-")):
                    val = tailwind_numeric(cls)
                    if val is not None:
                        metrics["spacing"].append((path, line, cls, val, "tailwind-spacing", "className"))
                size = tailwind_font_size(cls)
                if size is not None:
                    metrics["font_sizes"].append((path, line, cls, size, "className"))
                weight = tailwind_weight(cls)
                if weight is not None:
                    metrics["weights"].append((path, line, cls, weight, "className"))
                radius = tailwind_radius(cls)
                if radius is not None:
                    metrics["radii"].append((path, line, cls, radius, "className"))
                if cls.startswith("shadow"):
                    metrics["shadows"].append((path, line, cls, "className"))
    return metrics


def tailwind_numeric(cls):
    if "[" in cls and "]" in cls:
        return number_value(cls[cls.find("[") + 1:cls.rfind("]")])
    _, _, value = cls.rpartition("-")
    try:
        return float(value.replace("/", ".")) * 4
    except ValueError:
        return None


def tailwind_font_size(cls):
    if cls.startswith("text-[") and cls.endswith("]"):
        return number_value(cls[6:-1])
    if cls.startswith("text-"):
        return TYPE_SCALE_CLASSES.get(cls[5:])
    return None


def tailwind_weight(cls):
    if cls.startswith("font-"):
        return WEIGHTS.get(cls[5:])
    return None


def tailwind_radius(cls):
    values = {"rounded-none": 0, "rounded-sm": 2, "rounded": 4, "rounded-md": 6,
              "rounded-lg": 8, "rounded-xl": 12, "rounded-2xl": 16, "rounded-3xl": 24,
              "rounded-full": 9999}
    if cls.startswith("rounded-[") and cls.endswith("]"):
        return number_value(cls[9:-1])
    return values.get(cls)


def parse_weight(raw):
    raw = str(raw).strip().strip("'\"")
    if raw.isdigit():
        return int(raw)
    return WEIGHTS.get(raw.replace("font-", "").lower())


def mixed_alignment(values):
    if len(values) < 2:
        return False
    text = " ".join(f"{p}:{v}" for p, v in values).lower()
    centered = any(v in text for v in ("center", "middle"))
    startish = any(v in text for v in ("left", "start", "flex-start"))
    return centered and startish


def unique_numbers(rows, index=3):
    return sorted({round(float(row[index]), 3) for row in rows})


def cite(rows, limit=5):
    bits = []
    for row in rows[:limit]:
        bits.append(f"{Path(row[0]).name}:{row[1]} {row[2]}")
    return ", ".join(bits)


def structural_findings(files, style):
    spacing_scale, type_scale, radius_scale = collect_token_scales(files)
    metrics = collect_metrics(files)
    findings = []

    spacing_values = unique_numbers(metrics["spacing"])
    off_spacing = [r for r in metrics["spacing"] if not nearest_scale(r[3], spacing_scale)]
    if len(spacing_values) > 8 or off_spacing:
        outliers = ", ".join(sorted({r[2] for r in off_spacing})[:8]) or "none"
        findings.append(Finding(
            "WARN", "critique/spacing-rhythm", str(files[0]), 1,
            f"{len(spacing_values)} distinct spacing values found; scale defines {len(spacing_scale)}; outliers: {outliers}.",
            "Snap margins, padding, and gaps to the spacing scale; keep ad-hoc one-offs documented as exceptions."
        ))

    type_values = unique_numbers(metrics["font_sizes"], 3)
    off_type = [r for r in metrics["font_sizes"] if not nearest_scale(r[3], type_scale)]
    if off_type:
        findings.append(Finding(
            "WARN", "critique/type-rhythm", str(off_type[0][0]), off_type[0][1],
            f"{len(type_values)} distinct font sizes found; off-scale sizes include {', '.join(sorted({r[2] for r in off_type})[:8])}.",
            "Use the type scale tokens or add a verified type token before introducing another size."
        ))

    weights = unique_numbers(metrics["weights"], 3)
    if len(weights) > 4:
        findings.append(Finding(
            "INFO", "critique/type-weight-sprawl", str(metrics["weights"][0][0]), metrics["weights"][0][1],
            f"{len(weights)} distinct font weights found: {', '.join(display_num(w) for w in weights)}.",
            "Limit routine UI to a small weight set, usually body, emphasis, and heading/display."
        ))

    if len(type_values) >= 2:
        ratio = max(type_values) / max(min(v for v in type_values if v > 0), 1)
        if ratio < 2.5:
            findings.append(Finding(
                "INFO", "critique/hierarchy-flatness", str(files[0]), 1,
                f"Largest font size is only {ratio:.2f}x the smallest; hierarchy may read flat.",
                "Increase the heading/display token or reduce supporting copy size before adding boxes or borders."
            ))
    if len(weights) >= 2 and max(weights) - min(weights) < 300:
        findings.append(Finding(
            "INFO", "critique/weight-flatness", str(files[0]), 1,
            f"Font-weight spread is {int(max(weights) - min(weights))}; typographic emphasis may be too even.",
            "Create hierarchy with one stronger display/emphasis weight rather than adding more colors."
        ))

    for path, line, selector, align_values in metrics["align"][:8]:
        findings.append(Finding(
            "INFO", "critique/alignment-drift", str(path), line,
            f"Mixed centered and start alignment in {selector}: {align_values}.",
            "Choose one alignment axis for the container, then make exceptions deliberate and isolated."
        ))

    density = density_findings(metrics["density_ratios"], metrics["padding_by_selector"])
    findings.extend(density)

    radius_values = unique_numbers(metrics["radii"], 3)
    if len(radius_values) > 3:
        findings.append(Finding(
            "INFO", "critique/radius-consistency", str(metrics["radii"][0][0]), metrics["radii"][0][1],
            f"{len(radius_values)} distinct radius values found: {', '.join(display_num(v) for v in radius_values[:8])}.",
            "Map radii to small, medium, and large roles; avoid reusing the same shape logic at every scale."
        ))

    shadow_values = sorted({str(row[2]).strip() for row in metrics["shadows"]})
    depth_allowed = style.get("depth", {}).get("allowedElevationTechniques", [])
    if "shadow" not in depth_allowed and shadow_values and style:
        findings.append(Finding(
            "WARN", "critique/style-depth-mismatch", str(metrics["shadows"][0][0]), metrics["shadows"][0][1],
            f"Style '{style.get('id')}' does not allow shadow depth, but shadows were found: {', '.join(shadow_values[:4])}.",
            "Use the style's allowed elevation technique instead, such as border or overlap."
        ))
    elif len(shadow_values) > 3:
        findings.append(Finding(
            "INFO", "critique/shadow-consistency", str(metrics["shadows"][0][0]), metrics["shadows"][0][1],
            f"{len(shadow_values)} distinct shadow definitions found.",
            "Collapse shadows to elevation roles; remove shadows that are decorative rather than structural."
        ))

    radius_max = style.get("shape", {}).get("radiusMultiplierRange", {}).get("max")
    if radius_max is not None and radius_max <= 0.5:
        rounded = [r for r in metrics["radii"] if r[3] not in (0, 9999) and r[3] > 8]
        if rounded:
            findings.append(Finding(
                "WARN", "critique/style-radius-mismatch", str(rounded[0][0]), rounded[0][1],
                f"Style '{style.get('id')}' caps radius low, but {rounded[0][2]} appears.",
                "Lower radii to the style range or choose a softer style/modifier deliberately."
            ))

    if metrics["interactive"] and metrics["accent"] / metrics["interactive"] > 0.2:
        pct = metrics["accent"] / metrics["interactive"] * 100
        findings.append(Finding(
            "INFO", "critique/accent-overuse", str(files[0]), 1,
            f"Accent appears {metrics['accent']} times across {metrics['interactive']} detected interactive elements ({pct:.0f}%).",
            "Reserve accent for the primary action and active state; move secondary actions to neutral tokens."
        ))

    for path, line, selector in metrics["gradient_heroes"]:
        findings.append(Finding(
            "INFO", "critique/hero-gradient-default", str(path), line,
            f"Hero selector '{selector}' uses a gradient background.",
            "Use a product/state-revealing image or a deliberate tokenized surface instead of a default gradient hero."
        ))

    if not findings:
        findings.append(Finding(
            "PASS", "critique/structural", str(files[0]) if files else ".", 1,
            "No structural design-quality issues detected by static critique.",
            "Still verify rendered layout and keyboard/screen-reader behavior where possible."
        ))
    return findings


def density_findings(ratio_rows, padding_rows):
    findings = []
    for rows, label in ((ratio_rows, "padding-to-size ratio"), (padding_rows, "padding")):
        groups = grouped_by_selector_base(rows)
        for items in groups.values():
            if len(items) < 3:
                continue
            vals = [i[3] for i in items if i[3] > 0]
            if len(vals) < 2:
                continue
            diverges = max(vals) / min(vals) >= 2.5
            if label == "padding-to-size ratio":
                diverges = diverges or max(vals) - min(vals) >= 0.18
            if diverges:
                first = items[0]
                suffix = "" if label == "padding" else " of fixed container size"
                evidence = ", ".join(f"{i[2]}={display_num(i[3] * (100 if label != 'padding' else 1))}{'%' if label != 'padding' else 'px'}" for i in items[:5])
                findings.append(Finding(
                    "INFO", "critique/density-consistency", str(first[0]), first[1],
                    f"Sibling container {label}{suffix} diverges sharply: {evidence}.",
                    "Normalize container density by role, then vary hierarchy with content and type."
                ))
                return findings
    return findings


def grouped_by_selector_base(rows):
    groups = {}
    for path, line, selector, padding in rows:
        key = re.sub(r"[:.#\[][\w-]+.*$", "", selector.split()[0]).strip() or selector.split()[0]
        groups.setdefault(key, []).append((path, line, selector, padding))
    return groups


def render_target(target):
    path = Path(target)
    if path.is_file() and path.suffix in (".html", ".htm"):
        return path.resolve().as_uri()
    if path.is_dir():
        for name in ("index.html", "preview.html"):
            candidate = path / name
            if candidate.exists():
                return candidate.resolve().as_uri()
    return None


def rgba_tuple(css_color):
    nums = [float(n) for n in re.findall(r"[\d.]+", css_color or "")]
    if len(nums) >= 3:
        return tuple(max(0, min(255, nums[i])) / 255 for i in range(3))
    return None


def run_visual(target, style):
    url = render_target(target)
    if not url:
        print(VISUAL_UNAVAILABLE)
        return None
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print(VISUAL_UNAVAILABLE)
        return None
    findings = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            for width in (320, 768, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(url, wait_until="networkidle")
                screenshot = Path(tempfile.gettempdir()) / f"kinetic-self-critique-{width}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                findings.extend(visual_dom_findings(page, width, style))
            browser.close()
    except Exception:
        print(VISUAL_UNAVAILABLE)
        return None
    return findings or [Finding("PASS", "critique/visual", str(target), 1,
                                "Rendered at 320, 768, and 1280px with no detectable overlap, clipping, or rendered contrast failure.",
                                "Keep screenshots for manual review when visual direction matters.")]


def visual_dom_findings(page, width, style):
    raw = page.evaluate(
        """() => {
          const els = [...document.querySelectorAll('body *')].filter(el => {
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);
            return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none';
          });
          const rects = els.map((el, i) => {
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);
            return {
              i, tag: el.tagName.toLowerCase(), text: (el.innerText || '').trim().slice(0, 60),
              left: r.left, top: r.top, right: r.right, bottom: r.bottom,
              width: r.width, height: r.height,
              scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,
              scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,
              color: s.color, background: nearestBg(el),
              fontSize: parseFloat(s.fontSize || '16'), fontWeight: parseFloat(s.fontWeight || '400'),
              boxShadow: s.boxShadow
            };
          });
          function nearestBg(el) {
            let n = el;
            while (n) {
              const bg = getComputedStyle(n).backgroundColor;
              if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return bg;
              n = n.parentElement;
            }
            return getComputedStyle(document.body).backgroundColor || 'rgb(255,255,255)';
          }
          return rects;
        }"""
    )
    findings = []
    for item in raw:
        if item["text"] and (item["scrollWidth"] > item["clientWidth"] + 1 or item["scrollHeight"] > item["clientHeight"] + 1):
            findings.append(Finding("ERROR", "critique/visual-text-clipped", f"viewport:{width}", 1,
                                    f"{item['tag']} text appears clipped at {width}px: {item['text']!r}.",
                                    "Allow wrapping, increase the container, or reduce label length without losing information."))
        if item["text"] and parse_color and wcag_ratio:
            fg = rgba_tuple(item["color"])
            bg = rgba_tuple(item["background"])
            if fg and bg:
                ratio = wcag_ratio(fg, bg)
                need = 3.0 if item["fontSize"] >= 24 or (item["fontSize"] >= 18.66 and item["fontWeight"] >= 700) else 4.5
                if ratio < need:
                    findings.append(Finding("ERROR", "critique/visual-contrast", f"viewport:{width}", 1,
                                            f"Rendered contrast is {ratio:.2f}:1 for {item['tag']} text {item['text']!r}.",
                                            "Change the foreground/background token pair; verify with color_tools.py after adjustment."))
    for a in raw:
        for b in raw:
            if a["i"] >= b["i"]:
                continue
            overlap = max(0, min(a["right"], b["right"]) - max(a["left"], b["left"])) * max(0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]))
            smaller = max(1, min(a["width"] * a["height"], b["width"] * b["height"]))
            if overlap / smaller > 0.75 and a["text"] and b["text"] and a["text"] not in b["text"] and b["text"] not in a["text"]:
                findings.append(Finding("ERROR", "critique/visual-overlap", f"viewport:{width}", 1,
                                        f"Possible overlap between {a['tag']} {a['text']!r} and {b['tag']} {b['text']!r}.",
                                        "Inspect the layout at this viewport; add stable sizing, wrapping, or spacing constraints."))
                return findings
    if style and "shadow" not in style.get("depth", {}).get("allowedElevationTechniques", []):
        shadowed = [i for i in raw if i.get("boxShadow") and i["boxShadow"] != "none"]
        if shadowed:
            findings.append(Finding("WARN", "critique/visual-style-depth", f"viewport:{width}", 1,
                                    f"Rendered shadow appears, but style '{style.get('id')}' does not allow shadow depth.",
                                    "Use the style's allowed depth method or change the style contract."))
    return findings


def print_report(target, structural, visual, style_id):
    print("# Self Critique")
    print(f"Target: {target}")
    if style_id:
        print(f"Against style: {style_id}")
    print()
    print("| Severity | Rule | Location | Evidence | Suggested fix |")
    print("|---|---|---|---|---|")
    for f in structural + visual:
        location = f"{f.file}:{f.line}"
        print(f"| {f.severity} | `{f.rule}` | `{location}` | {escape_md(f.evidence)} | {escape_md(f.fix)} |")


def escape_md(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def main():
    ap = argparse.ArgumentParser(description="Critique UI code structurally and, when possible, visually.")
    ap.add_argument("target", help="file or directory to critique")
    ap.add_argument("--tier", choices=["structural", "visual", "all"], default="all")
    ap.add_argument("--against", help="style id from templates/styles to evaluate against")
    args = ap.parse_args()

    style = read_style(args.against)
    files = target_files(args.target)
    if not files:
        raise SystemExit("no supported UI files found")
    structural = structural_findings(files, style) if args.tier in ("structural", "all") else []
    visual = run_visual(args.target, style) if args.tier in ("visual", "all") else []
    if visual is None and args.tier == "visual":
        return
    if visual is None:
        visual = []
    print_report(args.target, structural, visual, args.against)

    if any(f.severity == "ERROR" for f in structural + visual):
        sys.exit(1)


if __name__ == "__main__":
    main()
