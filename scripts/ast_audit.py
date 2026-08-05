#!/usr/bin/env python3
"""
AST-based audit of UI code against Kinetic UX rules.

Replaces regex heuristics with real parsing via tree-sitter, so findings
carry structural context: which JSX element, which CSS rule, which selector
block, and whether a declaration sits inside a media query.

Usage:
  python ast_audit.py Component.tsx
  python ast_audit.py src/ --ext .tsx,.css,.scss --json
  python ast_audit.py Component.tsx --fail-on WARN

Install:
  pip install tree-sitter tree-sitter-language-pack --break-system-packages

Falls back to ui_audit.py (regex) automatically if tree-sitter is absent.
"""

import sys
import json
import argparse
import re
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from tree_sitter_language_pack import get_parser
    HAVE_TS = True
except ImportError:
    HAVE_TS = False

LANG_BY_EXT = {
    '.tsx': 'tsx', '.jsx': 'tsx', '.ts': 'typescript', '.js': 'javascript',
    '.css': 'css', '.scss': 'css', '.html': 'html',
}

# Elements that are interactive natively — a click handler is fine here.
NATIVE_INTERACTIVE = {'button', 'a', 'input', 'select', 'textarea',
                      'summary', 'label', 'option'}

# Layout properties that must never be transitioned/animated.
LAYOUT_PROPS = {'height', 'width', 'top', 'left', 'right', 'bottom',
                'margin', 'margin-top', 'margin-bottom', 'margin-left',
                'margin-right', 'padding', 'inset', 'block-size',
                'inline-size', 'max-height', 'min-height'}

PHYSICAL_PROPS = {'margin-left', 'margin-right', 'padding-left',
                  'padding-right', 'border-left', 'border-right',
                  'left', 'right', 'text-align'}

TOKEN_KINDS = {'color', 'space', 'radius', 'type', 'motion', 'shadow'}
BREAKPOINT_AT_RE = re.compile(r"@(media|container)\b([^{]*)\{", re.I | re.S)
BREAKPOINT_SIZE_RE = re.compile(
    r"(?:(min|max)-width\s*:\s*([0-9]*\.?[0-9]+)\s*(px|rem|em))|"
    r"(width)\s*(<=|>=|<|>)\s*([0-9]*\.?[0-9]+)\s*(px|rem|em)|"
    r"([0-9]*\.?[0-9]+)\s*(px|rem|em)\s*(<=|>=|<|>)\s*width",
    re.I)
FIXED_SIZE_RE = re.compile(r"^-?(?:\d+|\d*\.\d+)(?:px|rem|em|ch|vw|vh)$", re.I)
IMPORT_RE = re.compile(
    r"import\s+(?:(?P<what>[\s\S]*?)\s+from\s+)?['\"](?P<src>[^'\"]+)['\"]",
    re.M)
EXPORT_RE = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]*)")
CLASS_RE = re.compile(r"\.(-?[_a-zA-Z][-_a-zA-Z0-9]*)")
CLASSNAME_RE = re.compile(
    r"className\s*=\s*(?:['\"]([^'\"]+)['\"]|\{\s*['\"]([^'\"]+)['\"]\s*\})")
HTMLFOR_RE = re.compile(r"htmlFor\s*=\s*(?:['\"]([^'\"]+)['\"]|\{\s*['\"]([^'\"]+)['\"]\s*\})")
ID_RE = re.compile(r"\bid\s*=\s*(?:['\"]([^'\"]+)['\"]|\{\s*['\"]([^'\"]+)['\"]\s*\})")
COMPONENT_RE = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]*)")

try:
    from ds_search import BM25, best_value_token, color_tokens, extract_values, load_corpus
except ImportError:
    BM25 = best_value_token = color_tokens = extract_values = load_corpus = None


class Finding(dict):
    def __init__(self, rule, sev, file, line, msg, hint, ctx=""):
        super().__init__(rule=rule, severity=sev, file=str(file), line=line,
                         message=msg, hint=hint, context=ctx)


def txt(node, src):
    return src[node.start_byte:node.end_byte].decode('utf8', 'replace')


def line_of(node):
    return node.start_point[0] + 1


# ----------------------------------------------------------------- JSX / TS

def walk(node):
    yield node
    for c in node.children:
        yield from walk(c)


def audit_jsx(src, path):
    parser = get_parser('tsx')
    tree = parser.parse(src)
    root = tree.root_node
    out = []
    text = src.decode('utf8', 'replace')

    has_aria_busy = 'aria-busy' in text
    has_reduced = 'useReducedMotion' in text or 'prefers-reduced-motion' in text
    uses_motion_lib = 'framer-motion' in text or 'motion/react' in text
    loading_state = any(k in text for k in ('loading', 'isPending', "'loading'"))

    for n in walk(root):
        # --- JSX elements -------------------------------------------------
        if n.type in ('jsx_opening_element', 'jsx_self_closing_element'):
            name_node = n.child_by_field_name('name')
            tag = txt(name_node, src) if name_node else ''
            attrs = {}
            for c in n.children:
                if c.type == 'jsx_attribute':
                    an = c.child_by_field_name('name') or (c.children[0] if c.children else None)
                    if an:
                        attrs[txt(an, src)] = c
            lower = tag.lower()

            # click handler on non-interactive element
            if 'onClick' in attrs and lower in ('div', 'span', 'li', 'section', 'p'):
                if 'role' not in attrs or 'onKeyDown' not in attrs:
                    out.append(Finding(
                        "a11y/nonsemantic-click", "ERROR", path, line_of(n),
                        f"onClick on <{tag}> without role + keyboard handler",
                        "Use <button>. Native elements carry keyboard and focus behavior.",
                        f"<{tag}>"))

            # positive tabindex
            for k in ('tabIndex', 'tabindex'):
                if k in attrs:
                    v = txt(attrs[k], src)
                    digits = ''.join(ch for ch in v if ch.isdigit() or ch == '-')
                    try:
                        if int(digits) > 0:
                            out.append(Finding(
                                "a11y/positive-tabindex", "ERROR", path, line_of(n),
                                f"Positive tabIndex on <{tag}>",
                                "Breaks natural order. Use 0 or -1 and fix DOM order.",
                                f"<{tag}>"))
                    except ValueError:
                        pass

            # img without dimensions
            if lower == 'img':
                if not ({'width', 'height'} & attrs.keys()) and 'style' not in attrs \
                        and 'aspect' not in txt(n, src):
                    out.append(Finding(
                        "layout/img-no-dimensions", "ERROR", path, line_of(n),
                        "<img> without width/height or aspect-ratio",
                        "Primary CLS source. Reserve the space.", "<img>"))

            # input labelling
            if lower == 'input':
                labelled = {'aria-label', 'aria-labelledby', 'id'} & attrs.keys()
                if 'placeholder' in attrs and not labelled:
                    out.append(Finding(
                        "a11y/placeholder-as-label", "ERROR", path, line_of(n),
                        "Input labelled only by placeholder",
                        "Placeholders vanish on focus and fail contrast. Use <label>.",
                        "<input>"))
                if 'type' in attrs and 'autoComplete' not in attrs \
                        and 'autocomplete' not in attrs:
                    out.append(Finding(
                        "a11y/missing-autocomplete", "INFO", path, line_of(n),
                        "Input without autocomplete token",
                        "autocomplete is an accessibility requirement, not a convenience.",
                        "<input>"))

            # required without novalidate anywhere
            if 'required' in attrs and 'noValidate' not in text:
                out.append(Finding(
                    "a11y/native-validation-conflict", "WARN", path, line_of(n),
                    "required present, form has no noValidate",
                    "Native bubbles collide with custom ARIA errors.",
                    f"<{tag}>"))

            # assertive live region
            if 'aria-live' in attrs and 'assertive' in txt(attrs['aria-live'], src):
                out.append(Finding(
                    "a11y/assertive-live", "WARN", path, line_of(n),
                    "assertive live region",
                    "Reserve for interruptions; use polite/role=alert for errors.",
                    f"<{tag}>"))

            # haspopup treated as focus management
            if 'aria-haspopup' in attrs:
                out.append(Finding(
                    "a11y/haspopup-not-focus", "INFO", path, line_of(n),
                    "aria-haspopup announces a popup; it manages no focus",
                    "Ensure real focus handling exists alongside it.",
                    f"<{tag}>"))

            # hand-rolled dialog
            if 'role' in attrs and 'dialog' in txt(attrs['role'], src) and lower != 'dialog':
                out.append(Finding(
                    "a11y/handrolled-dialog", "WARN", path, line_of(n),
                    f'role="dialog" on <{tag}> instead of native <dialog>',
                    "<dialog> gives focus trap, Escape, and inerting for free.",
                    f"<{tag}>"))

        # --- identifiers / calls -------------------------------------------
        if n.type == 'identifier':
            name = txt(n, src)
            if name in ('localStorage', 'sessionStorage'):
                out.append(Finding(
                    "state/browser-storage", "ERROR", path, line_of(n),
                    f"{name} is unsupported in Claude artifacts",
                    "Use in-memory state (useState/useReducer).", name))

        # layout read inside a loop body
        if n.type in ('for_statement', 'while_statement', 'call_expression'):
            body = txt(n, src)
            if n.type == 'call_expression':
                fn = n.child_by_field_name('function')
                if not fn or not any(m in txt(fn, src) for m in ('.forEach', '.map')):
                    continue
            if any(m in body for m in ('getBoundingClientRect', 'offsetTop',
                                       'offsetHeight', 'scrollTop', 'clientHeight')):
                out.append(Finding(
                    "perf/layout-read-in-loop", "ERROR", path, line_of(n),
                    "Layout read inside an iteration",
                    "Hoist all reads, then write. This is classic thrashing.",
                    "loop"))

    # --- file-level ---------------------------------------------------------
    booleans = sum(1 for kw in ('isLoading', 'isError', 'isSuccess', 'hasError')
                   if kw in text)
    if booleans >= 2 and 'status' not in text:
        out.append(Finding(
            "state/boolean-soup", "WARN", path, 1,
            f"{booleans} parallel boolean state flags, no discriminated union",
            "Booleans permit loading && error && success. Use a status union."))

    if loading_state and not has_aria_busy:
        out.append(Finding(
            "a11y/no-aria-busy", "WARN", path, 1,
            "Loading state present without aria-busy",
            "A spinner that only spins tells screen reader users nothing."))

    if uses_motion_lib and not has_reduced:
        out.append(Finding(
            "motion/no-js-reduced-motion", "ERROR", path, 1,
            "Motion library used without useReducedMotion",
            "CSS media queries do not reach Framer Motion."))

    if 'aria-live' in text or 'role="alert"' in text:
        out.append(Finding(
            "a11y/live-region-premount", "INFO", path, 1,
            "Live region present — confirm it mounts empty before content",
            "Injecting region and message together often announces nothing."))

    return out


# ----------------------------------------------------------------- CSS

def css_decls(root, src):
    """Yield (prop, value, node, inside_media, selector)."""
    def sel_for(block):
        p = block.parent
        if p and p.type == 'rule_set':
            s = p.child_by_field_name('selectors') or p.children[0]
            return txt(s, src).strip()
        return ''

    def in_media(node):
        p = node.parent
        while p:
            if p.type == 'media_statement':
                return txt(p, src)[:120]
            p = p.parent
        return ''

    for n in walk(root):
        if n.type == 'declaration':
            parts = txt(n, src).split(':', 1)
            if len(parts) != 2:
                continue
            prop = parts[0].strip().lower()
            val = parts[1].strip().rstrip(';')
            block = n.parent
            yield prop, val, n, in_media(n), sel_for(block)


def css_rules(root, src):
    """Yield (selector, declarations, line) for simple CSS rule blocks."""
    for n in walk(root):
        if n.type != 'rule_set':
            continue
        sel_node = n.child_by_field_name('selectors') or n.children[0]
        sel = txt(sel_node, src).strip()
        decls = {}
        lines = {}
        for d in walk(n):
            if d.type != 'declaration':
                continue
            parts = txt(d, src).split(':', 1)
            if len(parts) != 2:
                continue
            prop = parts[0].strip().lower()
            decls[prop] = parts[1].strip().rstrip(';')
            lines[prop] = line_of(d)
        if decls:
            yield sel, decls, lines, line_of(n)


def is_fixed_size(value):
    value = value.strip().lower()
    if value in ('auto', 'none', 'fit-content', 'max-content', 'min-content'):
        return False
    if value.startswith(('var(', 'calc(', 'clamp(', 'min(', 'max(')):
        return False
    return bool(FIXED_SIZE_RE.match(value))


def geometry_hint():
    return "Static heuristics only - runtime verification is required."


def selector_parts(selector):
    cleaned = re.sub(r":[-a-zA-Z0-9_()]+", "", selector)
    return [p for p in re.split(r"\s+|>|\+|~", cleaned) if p]


def positioned_ancestor_for(selector, positioned_selectors):
    parts = selector_parts(selector)
    if len(parts) < 2:
        return False
    ancestor_tokens = parts[:-1]
    for pos in positioned_selectors:
        if pos == selector:
            continue
        if any(tok in pos.split(',')[-1] for tok in ancestor_tokens):
            return True
    return False


def ancestor_candidates(selector):
    parts = selector_parts(selector)
    if len(parts) < 2:
        return []
    return parts[:-1]


def has_child_overflow(selector, rules):
    for child_sel, child_decls, _lines, _line in rules:
        if child_sel == selector:
            continue
        if not any(p.startswith('overflow') for p in child_decls):
            continue
        for part in child_sel.split(','):
            part = part.strip()
            if part.startswith(selector + ' ') or part.startswith(selector + ' >'):
                return True
    return False


def audit_static_geometry(root, src, path):
    out = []
    rules = list(css_rules(root, src))
    positioned = {sel for sel, decls, _lines, _line in rules
                  if decls.get('position', '').strip().lower()
                  in ('relative', 'absolute', 'fixed', 'sticky')}
    flex_grid = [(sel, decls) for sel, decls, _lines, _line in rules
                 if decls.get('display', '').strip().lower()
                 in ('flex', 'inline-flex', 'grid', 'inline-grid')]

    for sel, decls, lines, line in rules:
        has_overflow = any(p.startswith('overflow') for p in decls)
        child_overflow = has_child_overflow(sel, rules)
        if not has_overflow and not child_overflow \
                and decls.get('display', '').strip().lower() in (
                'flex', 'inline-flex', 'grid', 'inline-grid'):
            for prop in ('height', 'width'):
                if prop in decls and is_fixed_size(decls[prop]):
                    out.append(Finding(
                        f"layout/static-fixed-{prop}-no-overflow", "INFO", path, lines[prop],
                        f"Fixed {prop} on a {decls.get('display')} container with no overflow handling",
                        geometry_hint(), sel))

        if decls.get('position', '').strip().lower() == 'absolute' \
                and not positioned_ancestor_for(sel, positioned):
            out.append(Finding(
                "layout/static-absolute-no-positioned-ancestor", "INFO",
                path, lines.get('position', line),
                "position:absolute has no positioned ancestor selector in this file",
                geometry_hint(), sel))

        if 'z-index' in decls:
            z = decls['z-index'].strip()
            if z.isdigit() and int(z) > 100:
                out.append(Finding(
                    "layout/static-z-index-high", "INFO", path, lines['z-index'],
                    f"z-index {z} is above 100 and is not a token",
                    geometry_hint(), sel))

        if decls.get('white-space', '').strip().lower() == 'nowrap':
            fixed = [p for p in ('width', 'inline-size') if p in decls and is_fixed_size(decls[p])]
            if fixed:
                out.append(Finding(
                    "layout/static-nowrap-fixed-width", "INFO", path, lines['white-space'],
                    f"white-space: nowrap is combined with fixed {fixed[0]}",
                    geometry_hint(), sel))

        if decls.get('min-width', '').strip().lower() == 'auto':
            ancestors = ancestor_candidates(sel)
            for parent_sel, parent_decls in flex_grid:
                if any(tok in parent_sel.split(',')[-1] for tok in ancestors):
                    can_shrink = not any(p in parent_decls for p in (
                        'min-width', 'overflow', 'width', 'inline-size'))
                    if can_shrink:
                        out.append(Finding(
                            "layout/static-min-width-auto-in-shrinking-container", "INFO",
                            path, lines['min-width'],
                            "min-width:auto inside a flex/grid container that could shrink below content",
                            geometry_hint(), sel))
                        break
    return out


def normalized_css_value(value):
    return re.sub(r"\s+", " ", value.strip().lower())


def is_tokenized_value(value):
    return "var(" in value or value.strip().lower().startswith(("inherit", "unset"))


def audit_slop(root, src, path):
    out = []
    rules = list(css_rules(root, src))
    radius = []
    shadows = []
    weights = {}

    for sel, decls, lines, line in rules:
        for prop, val in decls.items():
            low_val = normalized_css_value(val)
            if prop.endswith("border-radius") or prop == "border-radius":
                if low_val and not is_tokenized_value(low_val):
                    radius.append((low_val, sel, lines.get(prop, line)))
            if prop == "box-shadow":
                if low_val and low_val != "none" and not is_tokenized_value(low_val):
                    shadows.append((low_val, sel, lines.get(prop, line)))
            if prop == "font-weight":
                if low_val and not is_tokenized_value(low_val):
                    weights.setdefault(low_val, (sel, lines.get(prop, line)))
            if prop in ("background", "background-image") and "gradient(" in low_val:
                if re.search(r"(?:^|[-_\s.])hero(?:$|[-_\s.#:[{])", sel, re.I):
                    out.append(Finding(
                        "slop/hero-gradient-background", "INFO", path, lines.get(prop, line),
                        "Hero selector uses a gradient background",
                        "Default full-bleed hero gradients read generic unless the gradient is an intentional, verified brand/content surface.",
                        sel))

    if len(radius) >= 4:
        unique = {v for v, _sel, _line in radius}
        if len(unique) == 1:
            val, sel, line = radius[0]
            out.append(Finding(
                "slop/uniform-radius", "INFO", path, line,
                f"Same literal radius value appears across {len(radius)} rules",
                "Radius should vary by component scale and role; use radius tokens intentionally rather than one repeated default.",
                f"{val} in {sel}"))

    shadow_counts = {}
    for val, sel, line in shadows:
        shadow_counts.setdefault(val, []).append((sel, line))
    for val, uses in shadow_counts.items():
        selectors = {sel for sel, _line in uses}
        if len(selectors) >= 3:
            first_sel, first_line = uses[0]
            out.append(Finding(
                "slop/repeated-shadow", "INFO", path, first_line,
                f"Identical shadow value appears on {len(selectors)} selectors",
                "Elevation should map to layer/state; repeated literal shadows flatten hierarchy.",
                f"{val} in {first_sel}"))

    if len(weights) > 3:
        first_weight = sorted(weights)[0]
        sel, line = weights[first_weight]
        out.append(Finding(
            "slop/too-many-font-weights", "INFO", path, line,
            f"{len(weights)} literal font weights declared in one file",
            "Use a deliberate type scale with role contrast; too many weights often substitute for hierarchy.",
            ", ".join(sorted(weights))))

    return out


def audit_css(src, path):
    parser = get_parser('css')
    root = parser.parse(src).root_node
    out = []
    text = src.decode('utf8', 'replace')

    has_focus_visible = ':focus-visible' in text
    has_reduced_block = 'prefers-reduced-motion' in text
    has_motion = False

    for prop, val, node, media, sel in css_decls(root, src):
        ln = line_of(node)
        reduced_ctx = 'prefers-reduced-motion' in media

        if prop in ('transition', 'transition-property', 'animation'):
            has_motion = True
            for lp in LAYOUT_PROPS:
                # word-boundary-ish check on the value
                tokens = [t.strip() for t in val.replace(',', ' ').split()]
                if lp in tokens:
                    out.append(Finding(
                        "motion/animating-layout", "ERROR", path, ln,
                        f"Transitioning layout property '{lp}'",
                        "Animate transform/opacity/filter only.",
                        sel or prop))
                    break

        if prop == 'outline' and val.strip() in ('none', '0') and not has_focus_visible:
            out.append(Finding(
                "a11y/outline-none", "ERROR", path, ln,
                "outline removed with no :focus-visible replacement in file",
                "Keyboard users lose the focus indicator.", sel))

        if prop in PHYSICAL_PROPS and prop != 'text-align':
            out.append(Finding(
                "i18n/physical-property", "WARN", path, ln,
                f"Physical property '{prop}'",
                "Use logical equivalents (margin-inline-start) for RTL.", sel))

        if prop == 'text-overflow' and 'ellipsis' in val:
            out.append(Finding(
                "i18n/destructive-truncation", "WARN", path, ln,
                "Text truncation",
                "Permitted only if full text is reachable elsewhere.", sel))

        if prop == 'will-change' and not reduced_ctx:
            in_interactive = any(k in sel for k in (':hover', ':active', ':focus'))
            if not in_interactive:
                out.append(Finding(
                    "motion/will-change-static", "WARN", path, ln,
                    "will-change outside an interaction state",
                    "Permanent will-change is a memory leak.", sel))

        if prop == 'height' and val.endswith('px') and not reduced_ctx:
            out.append(Finding(
                "i18n/fixed-height", "INFO", path, ln,
                "Fixed pixel height — confirm 40% text expansion survives",
                "Prefer min-block-size on text-bearing containers.", sel))

    # selector-level checks
    for n in walk(root):
        if n.type == 'rule_set':
            s = n.child_by_field_name('selectors') or n.children[0]
            sel = txt(s, src).strip()
            if ':hover' in sel:
                has_motion = has_motion or True
                anc, found_media, is_reset = n.parent, False, False
                while anc:
                    if anc.type == 'media_statement':
                        mt = txt(anc, src)[:120]
                        if 'hover' in mt and 'prefers' not in mt:
                            found_media = True
                            break
                        # resets inside preference queries are not affordances
                        if any(k in mt for k in ('prefers-reduced-motion',
                                                 'prefers-contrast',
                                                 'prefers-reduced-transparency',
                                                 'forced-colors')):
                            is_reset = True
                            break
                    anc = anc.parent
                if not found_media and not is_reset:
                    out.append(Finding(
                        "a11y/ungated-hover", "WARN", path, line_of(n),
                        "Hover rule not gated by @media (hover: hover)",
                        "Hover is unavailable on touch.", sel))

    if '@keyframes' in text:
        has_motion = True
    if has_motion and not has_reduced_block:
        out.append(Finding(
            "motion/no-reduced-motion", "ERROR", path, 1,
            "Motion declared but prefers-reduced-motion never appears",
            "Provide a degradation path: crossfade under 100ms, transform: none."))
    if ':hover' in text and not has_focus_visible:
        out.append(Finding(
            "a11y/no-focus-visible", "ERROR", path, 1,
            "File styles :hover but never :focus-visible",
            "Keyboard users get no equivalent affordance."))
    if 'forced-colors' not in text and ('border' in text or 'box-shadow' in text):
        out.append(Finding(
            "a11y/no-forced-colors", "INFO", path, 1,
            "No forced-colors handling",
            "Custom fills are overridden; structure must survive on borders."))

    return out + audit_static_geometry(root, src, path) + audit_slop(root, src, path)


# --------------------------------------------------------- breakpoints

def width_to_px(value, unit):
    value = float(value)
    unit = unit.lower()
    if unit == 'px':
        return value
    if unit in ('rem', 'em'):
        return value * 16
    return value


def fmt_px(value):
    if value is None:
        return "none"
    if value == float('inf'):
        return "infinity"
    return str(int(value)) if value == int(value) else f"{value:.2f}"


def parse_breakpoint_query(query):
    lower = None
    upper = None
    distinct = []
    min_px_units = []
    for m in BREAKPOINT_SIZE_RE.finditer(query):
        if m.group(1):
            bound, value, unit = m.group(1).lower(), m.group(2), m.group(3)
            px = width_to_px(value, unit)
            distinct.append(px)
            if bound == 'min':
                lower = px if lower is None else max(lower, px)
                if unit.lower() == 'px':
                    min_px_units.append(f"{value}px")
            else:
                upper = px if upper is None else min(upper, px)
            continue
        if m.group(4):
            op, value, unit = m.group(5), m.group(6), m.group(7)
            px = width_to_px(value, unit)
            distinct.append(px)
            if op in ('>=', '>'):
                lower = px if lower is None else max(lower, px)
                if unit.lower() == 'px':
                    min_px_units.append(f"{value}px")
            else:
                upper = px if upper is None else min(upper, px)
            continue
        value, unit, op = m.group(8), m.group(9), m.group(10)
        px = width_to_px(value, unit)
        distinct.append(px)
        if op in ('<=', '<'):
            lower = px if lower is None else max(lower, px)
            if unit.lower() == 'px':
                min_px_units.append(f"{value}px")
        else:
            upper = px if upper is None else min(upper, px)
    return lower, upper, distinct, min_px_units


def collect_breakpoints(files):
    rows = []
    for path in files:
        if path.suffix not in ('.css', '.scss'):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"skip breakpoints {path}: {e}", file=sys.stderr)
            continue
        for m in BREAKPOINT_AT_RE.finditer(text):
            try:
                query = " ".join(m.group(2).strip().split())
                lower, upper, distinct, min_px_units = parse_breakpoint_query(query)
                if not distinct:
                    continue
                rows.append({
                    'file': path,
                    'line': line_for_offset(text, m.start()),
                    'kind': m.group(1).lower(),
                    'query': query,
                    'min_px': lower,
                    'max_px': upper,
                    'distinct': distinct,
                    'min_px_units': min_px_units,
                })
            except Exception as e:
                print(f"skip breakpoint query {path}:{line_for_offset(text, m.start())}: {e}",
                      file=sys.stderr)
    rows.sort(key=lambda r: (r['min_px'] if r['min_px'] is not None else 0,
                             r['max_px'] if r['max_px'] is not None else float('inf'),
                             str(r['file']), r['line']))
    return rows


def breakpoint_interval(row):
    lower = row['min_px'] if row['min_px'] is not None else 0
    upper = row['max_px'] if row['max_px'] is not None else float('inf')
    return lower, upper


def audit_breakpoints(rows):
    out = []
    distinct = sorted({round(v, 4) for r in rows for v in r['distinct']})
    for r in rows:
        low_values = [v for v in r['distinct'] if v < 320]
        if low_values:
            out.append(Finding(
                "responsive/breakpoint-below-320", "ERROR", r['file'], r['line'],
                f"Breakpoint declared below 320px ({fmt_px(min(low_values))}px)",
                "The supported floor is 320px; remove this breakpoint or raise it.",
                r['query']))
        for raw in r['min_px_units']:
            out.append(Finding(
                "responsive/min-width-px", "WARN", r['file'], r['line'],
                f"min-width breakpoint uses px ({raw})",
                "Use rem so browser zoom shifts breakpoints with readable text.",
                r['query']))
    if len(distinct) > 6 and rows:
        first = rows[0]
        out.append(Finding(
            "responsive/too-many-breakpoints", "WARN", first['file'], first['line'],
            f"{len(distinct)} distinct breakpoints declared",
            "Use a systematic responsive scale with six or fewer breakpoints.",
            ", ".join(fmt_px(v) for v in distinct)))
    bounded = [r for r in rows if r['min_px'] is not None or r['max_px'] is not None]
    for i, left in enumerate(bounded):
        a0, a1 = breakpoint_interval(left)
        if a1 == float('inf'):
            continue
        for right in bounded[i + 1:]:
            b0, b1 = breakpoint_interval(right)
            if b1 == float('inf'):
                continue
            if max(a0, b0) < min(a1, b1):
                out.append(Finding(
                    "responsive/overlapping-breakpoints", "WARN", right['file'], right['line'],
                    "Breakpoint range overlaps another query and both can match",
                    f"Clarify the range or cascade order. Overlaps {left['file']}:{left['line']}.",
                    f"{left['query']} <> {right['query']}"))
    finite = [(breakpoint_interval(r)[0], breakpoint_interval(r)[1], r) for r in bounded]
    finite.sort(key=lambda item: (item[0], item[1], str(item[2]['file']), item[2]['line'], item[2]['query']))
    coverage_end = 320
    for lower, upper, row in finite:
        if lower > coverage_end:
            out.append(Finding(
                "responsive/breakpoint-gap", "WARN", row['file'], row['line'],
                f"No breakpoint rule covers {fmt_px(coverage_end)}px to {fmt_px(lower)}px",
                "Make the responsive bands contiguous or rely on explicit base styles.",
                row['query']))
        coverage_end = max(coverage_end, upper)
        if coverage_end == float('inf'):
            break
    return out


def print_breakpoint_report(rows):
    print("\n  Kinetic UX breakpoint table\n")
    if not rows:
        print("  No @media or @container width breakpoints found.\n")
        return
    header = ("kind", "range px", "file:line", "query")
    print(f"  {header[0]:<10} {header[1]:<22} {header[2]:<32} {header[3]}")
    print(f"  {'-' * 10} {'-' * 22} {'-' * 32} {'-' * 40}")
    for r in rows:
        lower, upper = breakpoint_interval(r)
        loc = f"{rel_path(r['file'])}:{r['line']}"
        rng = f"{fmt_px(lower)} - {fmt_px(upper)}"
        print(f"  {r['kind']:<10} {rng:<22} {loc:<32} {r['query']}")
    distinct = sorted({round(v, 4) for r in rows for v in r['distinct']})
    print(f"\n  Distinct breakpoints: {', '.join(fmt_px(v) + 'px' for v in distinct)}")
    print(f"  Count: {len(distinct)}\n")


# ----------------------------------------------------------------- driver

SEV = {"ERROR": 0, "WARN": 1, "INFO": 2}
SARIF_LEVEL = {"ERROR": "error", "WARN": "warning", "INFO": "note"}


def rel_path(path):
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def sarif_uri(path):
    return rel_path(Path(path)).replace("\\", "/")


def format_sarif(findings):
    rules = {}
    results = []
    for f in findings:
        rule_id = f['rule']
        rules.setdefault(rule_id, {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": rule_id},
            "help": {"text": f.get('hint') or ""},
            "defaultConfiguration": {
                "level": SARIF_LEVEL.get(f['severity'], "warning")
            },
        })
        message = f"{f['message']} {f['hint']}".strip()
        result = {
            "ruleId": rule_id,
            "level": SARIF_LEVEL.get(f['severity'], "warning"),
            "message": {"text": message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": sarif_uri(f['file'])},
                    "region": {"startLine": max(1, int(f.get('line') or 1))}
                }
            }],
        }
        if f.get('context'):
            result["properties"] = {"context": f['context']}
        results.append(result)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Kinetic UI UX Pro AST Audit",
                    "informationUri": "https://github.com/",
                    "rules": sorted(rules.values(), key=lambda r: r["id"]),
                }
            },
            "results": results,
        }]
    }


def format_junit(findings, files):
    suite = ET.Element("testsuite", {
        "name": "kinetic-ui-ux-pro.ast-audit",
        "tests": str(len(findings)),
        "failures": str(sum(1 for f in findings if f['severity'] == 'ERROR')),
        "errors": "0",
        "skipped": "0",
    })
    if not findings:
        ET.SubElement(suite, "testcase", {
            "classname": "ast_audit",
            "name": f"no findings across {len(files)} file(s)",
        })
        suite.set("tests", "1")
    for f in findings:
        case = ET.SubElement(suite, "testcase", {
            "classname": f"ast_audit.{f['rule'].replace('/', '.')}",
            "name": f"{rel_path(Path(f['file']))}:{f['line']}",
            "file": rel_path(Path(f['file'])),
            "line": str(f['line']),
        })
        text = f"{f['severity']} {f['rule']}: {f['message']}\n{f['hint']}"
        if f['severity'] == 'ERROR':
            failure = ET.SubElement(case, "failure", {
                "message": f['message'],
                "type": f['rule'],
            })
            failure.text = text
        else:
            prop = ET.SubElement(case, "system-out")
            prop.text = text
    return ET.tostring(suite, encoding="unicode", xml_declaration=True)


def fallback_line_ranges(text):
    ranges = []
    for m in re.finditer(r'@supports\s+not\s*\(\s*color\s*:\s*oklch\(', text, re.I):
        brace = text.find('{', m.end())
        if brace < 0:
            continue
        depth, end = 0, brace
        for i in range(brace, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        start_line = text[:m.start()].count('\n') + 1
        end_line = text[:end].count('\n') + 1
        ranges.append((start_line, end_line))
    return ranges


def in_ranges(line, ranges):
    return any(start <= line <= end for start, end in ranges)


def load_ds_index(path):
    if not path:
        return None
    if not load_corpus:
        print("skip design-system index: ds_search.py could not be imported",
              file=sys.stderr)
        return None
    corpus = load_corpus(Path(path))
    token_sources = {r.get('source_file') for r in corpus
                     if r.get('kind') in TOKEN_KINDS}
    return {
        'corpus': corpus,
        'bm25': BM25(corpus),
        'color_tokens': color_tokens(corpus),
        'token_sources': token_sources,
    }


def audit_token_drift(path, ds):
    if not ds or not extract_values:
        return []
    if rel_path(path) in ds['token_sources']:
        return []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
        values = extract_values(path)
    except Exception as e:
        print(f"skip token drift {path}: {e}", file=sys.stderr)
        return []
    fallback_ranges = fallback_line_ranges(text) if path.suffix in ('.css', '.scss') else []
    out = []
    for item in values:
        if in_ranges(item['line'], fallback_ranges):
            continue
        verdict, doc, score, note = best_value_token(
            item, ds['corpus'], ds['bm25'], ds['color_tokens'])
        if verdict not in ('EXACT', 'NEAR') or not doc:
            continue
        token = doc['name']
        out.append(Finding(
            "ds/token-drift", "WARN", path, item['line'],
            f"hardcoded {item['value']} - use var(--{token})",
            f"Approved {item['kind']} token found ({verdict}; {note}).",
            item['property']))
    return out


def line_for_offset(text, offset):
    return text[:offset].count('\n') + 1


def resolve_import(path, source):
    if not source.startswith('.'):
        return None
    base = (path.parent / source).resolve()
    candidates = [base]
    if base.suffix == '':
        candidates += [base.with_suffix(s) for s in ('.tsx', '.ts', '.jsx', '.js', '.css')]
        candidates += [base / f"index{s}" for s in ('.tsx', '.ts', '.jsx', '.js', '.css')]
    for c in candidates:
        if c.exists():
            return c
    return base


def imported_names(spec):
    names = set()
    spec = (spec or '').strip()
    if not spec:
        return names
    first = spec.split(',', 1)[0].strip()
    if first and first not in ('{', '*') and not first.startswith('{'):
        names.add(first)
    for block in re.findall(r"\{([^}]+)\}", spec, re.S):
        for part in block.split(','):
            name = part.strip().split(' as ')[-1].strip()
            if name:
                names.add(name)
    ns = re.search(r"\*\s+as\s+([A-Za-z_$][\w$]*)", spec)
    if ns:
        names.add(ns.group(1))
    return names


def jsx_tag_used(text, name):
    return re.search(rf"<{re.escape(name)}(?:\s|/|>)", text) is not None


def find_matching_brace(text, start):
    brace = text.find('{', start)
    if brace < 0:
        return len(text)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def component_ranges(text):
    ranges = []
    for m in COMPONENT_RE.finditer(text):
        ranges.append((m.group(1), m.start(), find_matching_brace(text, m.end())))
    return ranges


def component_at(ranges, offset):
    for name, start, end in ranges:
        if start <= offset <= end:
            return name
    return "__file__"


def graph_file(path, root):
    text = path.read_text(encoding='utf-8', errors='replace')
    ranges = component_ranges(text)
    node = {
        'path': path,
        'imports': [],
        'css_imports': [],
        'exports': set(EXPORT_RE.findall(text)),
        'classes': set(),
        'class_uses': [],
        'ids': {},
        'labels': [],
        'modal_imports': [],
        'text': text,
    }
    if path.suffix in ('.css', '.scss'):
        node['classes'] = set(CLASS_RE.findall(text))
        return node
    if path.suffix not in ('.tsx', '.jsx', '.ts', '.js'):
        return node
    for m in IMPORT_RE.finditer(text):
        src = m.group('src')
        target = resolve_import(path, src)
        names = imported_names(m.group('what'))
        node['imports'].append({'source': src, 'target': target, 'names': names})
        if src.endswith(('.css', '.scss')) and target:
            node['css_imports'].append(target)
        for name in names:
            if re.search(r"(modal|dialog|focus.?trap)", f"{name} {src}", re.I):
                node['modal_imports'].append((name, line_for_offset(text, m.start())))
    for m in CLASSNAME_RE.finditer(text):
        raw = m.group(1) or m.group(2) or ''
        for cls in raw.split():
            if cls and not any(ch in cls for ch in '{}$:'):
                node['class_uses'].append((cls, line_for_offset(text, m.start())))
    for m in ID_RE.finditer(text):
        comp = component_at(ranges, m.start())
        node['ids'].setdefault(comp, set()).add(m.group(1) or m.group(2))
    for m in HTMLFOR_RE.finditer(text):
        comp = component_at(ranges, m.start())
        node['labels'].append((m.group(1) or m.group(2),
                               line_for_offset(text, m.start()), comp))
    return node


def build_project_graph(files):
    root = Path.cwd().resolve()
    graph = {}
    for f in files:
        try:
            graph[f.resolve()] = graph_file(f.resolve(), root)
        except Exception as e:
            print(f"skip graph {f}: {e}", file=sys.stderr)
    return graph


def audit_project_graph(graph):
    out = []
    css_classes = {path: node['classes'] for path, node in graph.items()
                   if path.suffix in ('.css', '.scss')}
    for path, node in graph.items():
        if path.suffix not in ('.tsx', '.jsx', '.ts', '.js'):
            continue
        for html_for, line, comp in node['labels']:
            ids = node['ids'].get(comp, set())
            if html_for and html_for not in ids:
                out.append(Finding(
                    "a11y/orphan-label", "ERROR", path, line,
                    f'<label htmlFor="{html_for}"> has no matching id in this component tree',
                    "Add a control with the same id or fix the htmlFor target.",
                    html_for))
        imported_classes = set()
        for css in node['css_imports']:
            imported_classes.update(css_classes.get(css.resolve(), set()))
        for cls, line in node['class_uses']:
            if cls not in imported_classes:
                out.append(Finding(
                    "ds/class-not-defined", "WARN", path, line,
                    f'className "{cls}" is not defined in an imported stylesheet',
                    "Import the stylesheet that defines it or use an approved component/token class.",
                    cls))
        for name, line in node['modal_imports']:
            if not jsx_tag_used(node['text'], name):
                continue
            tag = re.search(rf"<{re.escape(name)}(?P<attrs>[^>]*)>", node['text'], re.S)
            attrs = tag.group('attrs') if tag else ''
            if not re.search(r"(returnFocus|finalFocus|triggerRef|openerRef|returnTo)", attrs):
                out.append(Finding(
                    "a11y/unreachable-focus", "WARN", path, line,
                    f"Imported modal/focus component <{name}> has no return-focus target",
                    "Pass a trigger/opener/final focus ref so focus returns after close.",
                    name))
    return out


def audit_file(path, ds=None):
    lang = LANG_BY_EXT.get(path.suffix)
    if not lang:
        return []
    src = path.read_bytes()
    out = []
    if lang == 'css':
        out = audit_css(src, path)
    elif lang in ('tsx', 'typescript', 'javascript'):
        out = audit_jsx(src, path)
    return out + audit_token_drift(path, ds)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target')
    ap.add_argument('--ext', default='.tsx,.jsx,.ts,.js,.css,.scss')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--format', default='text',
                    choices=['text', 'json', 'sarif', 'junit'],
                    help='output format; --json is kept as an alias for --format json')
    ap.add_argument('--ds-index',
                    help='path to .ds-index/corpus.jsonl for token drift warnings')
    ap.add_argument('--breakpoints', action='store_true',
                    help='print only the CSS breakpoint table')
    ap.add_argument('--fail-on', default='ERROR',
                    choices=['ERROR', 'WARN', 'INFO', 'NONE'])
    args = ap.parse_args()
    output_format = 'json' if args.json else args.format

    if not HAVE_TS:
        print("tree-sitter not installed. Falling back to regex auditor:\n"
              "  pip install tree-sitter tree-sitter-language-pack "
              "--break-system-packages\n"
              "  python ui_audit.py <target>", file=sys.stderr)
        sys.exit(2)

    exts = {e if e.startswith('.') else '.' + e for e in args.ext.split(',')}
    p = Path(args.target)
    is_project = p.is_dir()
    files = [p] if p.is_file() else [f for f in p.rglob('*')
                                     if f.is_file() and f.suffix in exts]
    ds = load_ds_index(args.ds_index)
    graph = build_project_graph(files) if is_project else None
    breakpoint_rows = collect_breakpoints(files)

    if args.breakpoints:
        print_breakpoint_report(breakpoint_rows)
        return

    findings = audit_project_graph(graph) if graph else []
    findings += audit_breakpoints(breakpoint_rows)
    for f in files:
        try:
            findings += audit_file(f, ds)
        except Exception as e:
            print(f"skip {f}: {e}", file=sys.stderr)

    findings.sort(key=lambda x: (SEV[x['severity']], x['file'], x['line']))

    if output_format == 'json':
        print(json.dumps(findings, indent=2))
    elif output_format == 'sarif':
        print(json.dumps(format_sarif(findings), indent=2))
    elif output_format == 'junit':
        print(format_junit(findings, files))
    else:
        counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
        for f in findings:
            counts[f['severity']] += 1
        print(f"\n  Kinetic UX AST audit — {len(files)} file(s)\n")
        if not findings:
            print("  No structural findings. Hand-check what parsing cannot see:"
                  "\n  flow, hierarchy, microcopy, focus return, empty states,"
                  "\n  and computed contrast.\n")
        if any(f['rule'].startswith('layout/static-') for f in findings):
            print("  Static heuristics only — these cannot confirm actual rendered layout. Verify in a browser.\n")
        for f in findings:
            ctx = f" ({f['context']})" if f['context'] else ""
            print(f"  [{f['severity']:<5}] {f['file']}:{f['line']}{ctx}  {f['rule']}")
            print(f"          {f['message']}")
            print(f"          → {f['hint']}\n")
        print(f"  {counts['ERROR']} error(s), {counts['WARN']} warning(s), "
              f"{counts['INFO']} info\n")

    if args.fail_on != 'NONE' and any(
            SEV[f['severity']] <= SEV[args.fail_on] for f in findings):
        sys.exit(1)


if __name__ == '__main__':
    main()
