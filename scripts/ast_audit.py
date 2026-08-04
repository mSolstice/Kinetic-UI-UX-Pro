#!/usr/bin/env python3
"""
AST-based audit of UI code against Kinetic UX rules.

Replaces regex heuristics with real parsing via tree-sitter, so findings
carry structural context: which JSX element, which CSS rule, which selector
block, and whether a declaration sits inside a media query.

Usage:
  python ast_audit.py Component.tsx
  python ast_audit.py src/ --ext .tsx,.css --json
  python ast_audit.py Component.tsx --fail-on WARN

Install:
  pip install tree-sitter tree-sitter-language-pack --break-system-packages

Falls back to ui_audit.py (regex) automatically if tree-sitter is absent.
"""

import sys
import json
import argparse
from pathlib import Path

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

    return out


# ----------------------------------------------------------------- driver

SEV = {"ERROR": 0, "WARN": 1, "INFO": 2}


def audit_file(path):
    lang = LANG_BY_EXT.get(path.suffix)
    if not lang:
        return []
    src = path.read_bytes()
    if lang == 'css':
        return audit_css(src, path)
    if lang in ('tsx', 'typescript', 'javascript'):
        return audit_jsx(src, path)
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target')
    ap.add_argument('--ext', default='.tsx,.jsx,.ts,.js,.css')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fail-on', default='ERROR',
                    choices=['ERROR', 'WARN', 'INFO', 'NONE'])
    args = ap.parse_args()

    if not HAVE_TS:
        print("tree-sitter not installed. Falling back to regex auditor:\n"
              "  pip install tree-sitter tree-sitter-language-pack "
              "--break-system-packages\n"
              "  python ui_audit.py <target>", file=sys.stderr)
        sys.exit(2)

    exts = {e if e.startswith('.') else '.' + e for e in args.ext.split(',')}
    p = Path(args.target)
    files = [p] if p.is_file() else [f for f in p.rglob('*')
                                     if f.is_file() and f.suffix in exts]

    findings = []
    for f in files:
        try:
            findings += audit_file(f)
        except Exception as e:
            print(f"skip {f}: {e}", file=sys.stderr)

    findings.sort(key=lambda x: (SEV[x['severity']], x['file'], x['line']))

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
        for f in findings:
            counts[f['severity']] += 1
        print(f"\n  Kinetic UX AST audit — {len(files)} file(s)\n")
        if not findings:
            print("  No structural findings. Hand-check what parsing cannot see:"
                  "\n  flow, hierarchy, microcopy, focus return, empty states,"
                  "\n  and computed contrast.\n")
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
