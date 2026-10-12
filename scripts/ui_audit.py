#!/usr/bin/env python3
"""
Static audit of generated UI code against Kinetic UI UX Pro rules.

Usage:
  python ui_audit.py Component.tsx
  python ui_audit.py src/ --ext .tsx,.jsx,.css
  python ui_audit.py Component.tsx --json

Heuristic, not a compiler. It catches the failure modes that recur in
generated UI. Findings are ERROR (fix before shipping), WARN (justify or
fix), or INFO (check by hand). Zero findings does not mean zero problems —
it means the mechanical checks passed.
"""

import re
import sys
import json
import argparse
from pathlib import Path

# (id, severity, pattern, message, hint)
RULES = [
    # --- accessibility ---------------------------------------------------
    ("a11y/ungated-hover", "WARN",
     r':hover\s*\{',
     "Hover rule found — confirm it is gated by @media (hover: hover)",
     "Hover is unavailable on touch; never make it the sole affordance."),

    ("a11y/outline-none", "ERROR",
     r'outline\s*:\s*(none|0)\b',
     "outline removed",
     "Only acceptable if a visible :focus-visible replacement exists."),

    ("a11y/positive-tabindex", "ERROR",
     r'tabindex\s*=\s*[\"\']?[1-9]',
     "Positive tabindex",
     "Breaks natural tab order. Use 0 or -1 and fix DOM order instead."),

    ("a11y/placeholder-as-label", "WARN",
     r'<input(?![^>]*aria-label)(?![^>]*id=)[^>]*placeholder=',
     "Input with placeholder but no id/aria-label",
     "Placeholders are not labels. Associate a real <label>."),

    ("a11y/div-onclick", "ERROR",
     r'<(div|span)[^>]*onClick',
     "Click handler on a non-interactive element",
     "Use <button>. Otherwise you owe role, tabindex, and key handlers."),

    ("a11y/aria-live-assertive", "WARN",
     r'aria-live\s*=\s*[\"\']assertive',
     "assertive live region",
     "Reserve for genuine interruptions; use polite/role=alert for errors."),

    ("a11y/haspopup-as-focus", "WARN",
     r'aria-haspopup',
     "aria-haspopup present — it announces, it does not manage focus",
     "Ensure real focus handling exists alongside it."),

    ("a11y/native-validation-conflict", "WARN",
     r'required(?![\s\S]{0,600}noValidate|[\s\S]{0,600}novalidate)',
     "required attribute with no novalidate nearby",
     "Native bubbles collide with custom ARIA errors. Add novalidate."),

    # --- motion ----------------------------------------------------------
    ("motion/animating-layout", "ERROR",
     r'transition\s*:[^;]*\b(height|width|top|left|right|bottom|margin|padding)\b',
     "Transitioning a layout property",
     "Animate transform/opacity/filter only; layout props thrash."),

    ("motion/no-reduced-motion", "ERROR",
     r'@keyframes(?![\s\S]*prefers-reduced-motion)',
     "Keyframes with no prefers-reduced-motion handling in the file",
     "Provide a degradation path, not a blank gate."),

    ("motion/reduced-motion-blank-gate", "WARN",
     r'prefers-reduced-motion\s*:\s*no-preference',
     "no-preference gate — confirm a fallback exists for reduce",
     "Reduce users must still receive the state-change signal."),

    ("motion/will-change-static", "WARN",
     r'will-change\s*:',
     "will-change declared — confirm it is scoped to active interaction",
     "A permanent will-change is a memory leak."),

    ("motion/js-reduced-motion", "INFO",
     r'framer-motion|motion/react',
     "Framer Motion detected",
     "CSS media queries do not reach it. Use useReducedMotion()."),

    # --- layout / CLS ----------------------------------------------------
    ("layout/img-no-dimensions", "ERROR",
     r'<img(?![^>]*(width=|aspect-ratio|className=[\"\'][^\"\']*aspect-))[^>]*>',
     "<img> without width/height or aspect-ratio",
     "Primary CLS source. Reserve the space."),

    ("layout/physical-properties", "WARN",
     r'(?<![-\w])(margin|padding)-(left|right)\s*:',
     "Physical direction property",
     "Use margin-inline-start / padding-inline-end for RTL support."),

    ("layout/destructive-truncation", "WARN",
     r'text-overflow\s*:\s*ellipsis|(?<![-\w])truncate(?![-\w])',
     "Text truncation",
     "Only if the full text is reachable elsewhere. Otherwise it is data loss."),

    ("layout/fixed-px-height-text", "INFO",
     r'height\s*:\s*\d+px',
     "Fixed pixel height — confirm it survives 40% text expansion",
     "Prefer min-height for text-bearing containers."),

    # --- state -----------------------------------------------------------
    ("state/boolean-soup", "WARN",
     r'(isLoading|loading)[\s\S]{0,200}(isError|hasError|error)\s*[,;=]',
     "Parallel boolean state flags",
     "Use a discriminated union; booleans permit impossible combinations."),

    ("state/no-disabled-on-submit", "INFO",
     r'onSubmit|handleSubmit',
     "Submit handler present",
     "Confirm double-submission is blocked at the state layer."),

    ("state/browser-storage", "ERROR",
     r'\b(localStorage|sessionStorage)\b',
     "Browser storage API",
     "Unsupported in Claude artifacts. Use in-memory state."),

    # --- performance -----------------------------------------------------
    ("perf/read-write-interleave", "WARN",
     r'getBoundingClientRect[\s\S]{0,200}\.style\.',
     "Layout read followed closely by a style write",
     "Batch all reads, then all writes. Measurement itself is fine."),

    ("perf/layout-read-in-loop", "ERROR",
     r'(for|while|forEach|map)\s*\([\s\S]{0,300}(getBoundingClientRect|offsetTop|offsetHeight|scrollTop)',
     "Layout read inside a loop",
     "Classic thrashing. Hoist the measurement out."),
]

COMPILED = [(i, s, re.compile(p, re.I | re.M), m, h) for i, s, p, m, h in RULES]

SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


def audit_text(text, path):
    findings = []
    for rid, sev, rx, msg, hint in COMPILED:
        for m in rx.finditer(text):
            line = text[:m.start()].count('\n') + 1
            findings.append({
                "file": str(path), "line": line, "rule": rid,
                "severity": sev, "message": msg, "hint": hint,
                "snippet": text.splitlines()[line - 1].strip()[:90]
                if line <= len(text.splitlines()) else "",
            })
    findings += audit_file_level(text, path)
    return findings


def audit_file_level(text, path):
    """Checks that need whole-file context, not regex proximity."""
    out = []

    def add(rule, sev, msg, hint, line=1):
        out.append({"file": str(path), "line": line, "rule": rule,
                    "severity": sev, "message": msg, "hint": hint,
                    "snippet": ""})

    has_hover = re.search(r':hover\s*[,{]', text)
    if has_hover and ':focus-visible' not in text:
        add("a11y/no-focus-visible", "ERROR",
            "File styles :hover but never :focus-visible",
            "Keyboard users get no equivalent affordance.",
            text[:has_hover.start()].count('\n') + 1)

    if re.search(r'\btransition\b|\banimation\b|@keyframes', text) \
            and 'prefers-reduced-motion' not in text:
        add("motion/no-reduced-motion-file", "ERROR",
            "Motion declared but prefers-reduced-motion never appears",
            "Provide a degradation path: crossfade or instant swap under 100ms.")

    if re.search(r'aria-live|role\s*=\s*[\"\']alert', text) \
            and not re.search(r'aria-live[\s\S]{0,300}(\?|&&|:)', text):
        add("a11y/live-region-premount", "INFO",
            "Live region present — confirm it is mounted empty before content",
            "Injecting region and message together often announces nothing.")

    if 'aria-busy' not in text and re.search(r'loading|isPending|status', text, re.I):
        add("a11y/no-aria-busy", "WARN",
            "Loading state without aria-busy",
            "A spinner that only spins tells screen reader users nothing.")

    return out


def collect(target, exts):
    p = Path(target)
    if p.is_file():
        return [p]
    return [f for f in p.rglob('*') if f.is_file() and f.suffix in exts]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target')
    ap.add_argument('--ext', default='.tsx,.jsx,.ts,.js,.css,.html,.svelte,.vue')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fail-on', default='ERROR',
                    choices=['ERROR', 'WARN', 'INFO', 'NONE'])
    args = ap.parse_args()

    exts = set(e if e.startswith('.') else '.' + e
               for e in args.ext.split(','))
    files = collect(args.target, exts)
    if not files:
        print(f"No matching files under {args.target}")
        sys.exit(0)

    all_findings = []
    for f in files:
        try:
            all_findings += audit_text(f.read_text(errors='replace'), f)
        except Exception as e:
            print(f"skip {f}: {e}", file=sys.stderr)

    all_findings.sort(key=lambda x: (SEV_ORDER[x['severity']], x['file'], x['line']))

    if args.json:
        print(json.dumps(all_findings, indent=2))
    else:
        counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
        for f in all_findings:
            counts[f['severity']] += 1
        print(f"\n  Kinetic UI UX Pro audit — {len(files)} file(s)\n")
        if not all_findings:
            print("  No mechanical findings. Hand-check the items the linter"
                  "\n  cannot see: flow, hierarchy, microcopy, focus return,"
                  "\n  empty states, and computed contrast.\n")
        for f in all_findings:
            print(f"  [{f['severity']:<5}] {f['file']}:{f['line']}  {f['rule']}")
            print(f"          {f['message']}")
            if f['snippet']:
                print(f"          > {f['snippet']}")
            print(f"          → {f['hint']}\n")
        print(f"  {counts['ERROR']} error(s), {counts['WARN']} warning(s), "
              f"{counts['INFO']} info\n")

    if args.fail_on != 'NONE':
        threshold = SEV_ORDER[args.fail_on]
        if any(SEV_ORDER[f['severity']] <= threshold for f in all_findings):
            sys.exit(1)


if __name__ == '__main__':
    main()
