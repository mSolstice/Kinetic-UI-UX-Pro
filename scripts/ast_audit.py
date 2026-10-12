#!/usr/bin/env python3
"""
AST-based audit of UI code against Kinetic UI UX Pro rules.

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
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from tree_sitter_language_pack import get_parser
    HAVE_TS = True
except ImportError:
    HAVE_TS = False

LANG_BY_EXT = {
    '.tsx': 'tsx', '.jsx': 'tsx', '.ts': 'typescript', '.js': 'javascript',
    '.css': 'css', '.scss': 'css', '.html': 'html', '.htm': 'html',
    '.svelte': 'svelte', '.vue': 'vue', '.astro': 'astro',
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

NATIVE_IMPORT_RE = re.compile(r"from\s+['\"](?:react-native|expo(?:/[^'\"]*)?)['\"]|require\(\s*['\"](?:react-native|expo(?:/[^'\"]*)?)['\"]\s*\)")
NATIVE_INTERACTIVE = {'Pressable', 'TouchableOpacity', 'TouchableHighlight',
                      'TouchableWithoutFeedback'}
NATIVE_STATE_ATTRS = {'disabled', 'selected', 'checked'}
NATIVE_SUPPRESS_RULES = {
    'a11y/ungated-hover',
    'a11y/no-forced-colors',
    'i18n/physical-property',
    'layout/img-no-dimensions',
}
NATIVE_SIZE_PROPS = {'width', 'height', 'minWidth', 'minHeight'}
NATIVE_TOKEN_PROPS = {
    'color', 'backgroundColor', 'borderColor', 'shadowColor',
    'width', 'height', 'minWidth', 'minHeight', 'maxWidth', 'maxHeight',
    'margin', 'marginTop', 'marginRight', 'marginBottom', 'marginLeft',
    'marginHorizontal', 'marginVertical',
    'padding', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'paddingHorizontal', 'paddingVertical', 'gap', 'rowGap', 'columnGap',
    'top', 'right', 'bottom', 'left',
    'borderRadius', 'borderTopLeftRadius', 'borderTopRightRadius',
    'borderBottomLeftRadius', 'borderBottomRightRadius',
}
RN_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RN_RGB_RE = re.compile(r"rgba?\([^)]+\)", re.I)
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
    from ds_search import (
        BM25, best_value_token, color_tokens, extract_values, load_corpus,
        scan_value,
    )
except ImportError:
    BM25 = best_value_token = color_tokens = extract_values = load_corpus = scan_value = None


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


def jsx_attrs(node, src):
    attrs = {}
    for c in node.children:
        if c.type == 'jsx_attribute':
            an = c.child_by_field_name('name') or (c.children[0] if c.children else None)
            if an:
                attrs[txt(an, src)] = c
    return attrs


def audit_jsx(src, path, platform='web', ds=None):
    parser = get_parser('tsx')
    tree = parser.parse(src)
    root = tree.root_node
    out = []
    text = src.decode('utf8', 'replace')
    native = platform == 'native'

    has_aria_busy = 'aria-busy' in text
    has_reduced = 'useReducedMotion' in text or 'prefers-reduced-motion' in text
    uses_motion_lib = 'framer-motion' in text or 'motion/react' in text
    loading_state = any(k in text for k in ('loading', 'isPending', "'loading'"))

    for n in walk(root):
        # --- JSX elements -------------------------------------------------
        if n.type in ('jsx_opening_element', 'jsx_self_closing_element'):
            name_node = n.child_by_field_name('name')
            tag = txt(name_node, src) if name_node else ''
            attrs = jsx_attrs(n, src)
            lower = tag.lower()

            # click handler on non-interactive element
            if not native and 'onClick' in attrs and lower in ('div', 'span', 'li', 'section', 'p'):
                if 'role' not in attrs or 'onKeyDown' not in attrs:
                    out.append(Finding(
                        "a11y/nonsemantic-click", "ERROR", path, line_of(n),
                        f"onClick on <{tag}> without role + keyboard handler",
                        "Use <button>. Native elements carry keyboard and focus behavior.",
                        f"<{tag}>"))

            # positive tabindex
            if not native:
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
            if not native and lower == 'img':
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

            if native:
                out += audit_native_element(n, src, path, tag, attrs)

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

    if not native and uses_motion_lib and not has_reduced:
        out.append(Finding(
            "motion/no-js-reduced-motion", "ERROR", path, 1,
            "Motion library used without useReducedMotion",
            "CSS media queries do not reach Framer Motion."))

    if 'aria-live' in text or 'role="alert"' in text:
        out.append(Finding(
            "a11y/live-region-premount", "INFO", path, 1,
            "Live region present — confirm it mounts empty before content",
            "Injecting region and message together often announces nothing."))

    if native:
        out += audit_native_file(src, path, ds)

    return out


# ------------------------------------------------------------ React Native

def jsx_attr_raw(attrs, name, src):
    node = attrs.get(name)
    return txt(node, src) if node else ''


def jsx_attr_has_false(attrs, name, src):
    raw = jsx_attr_raw(attrs, name, src).replace(' ', '').lower()
    return raw in (f'{name.lower()}={{false}}', f'{name.lower()}="false"', f"{name.lower()}='false'")


def native_style_ref(style_raw):
    m = re.search(r"styles\.([A-Za-z_$][\w$]*)", style_raw)
    return m.group(1) if m else ''


def native_inline_style_props(style_raw):
    if '{{' not in style_raw:
        return {}
    props = {}
    for m in re.finditer(r"([A-Za-z_$][\w$]*)\s*:\s*(['\"][^'\"]+['\"]|-?\d*\.?\d+)", style_raw):
        raw = m.group(2).strip().strip("'\"")
        props[m.group(1)] = raw
    return props


def parse_native_stylesheets(text):
    styles = {}
    for m in re.finditer(r"StyleSheet\.create\s*\(", text):
        start = text.find('{', m.end())
        if start < 0:
            continue
        end = find_matching_brace(text, start - 1)
        body = text[start + 1:end - 1]
        for sm in re.finditer(r"([A-Za-z_$][\w$]*)\s*:\s*\{([^{}]*)\}", body, re.S):
            props = {}
            style_start = start + 1 + sm.start()
            for pm in re.finditer(r"([A-Za-z_$][\w$]*)\s*:\s*([^,\n}]+)", sm.group(2)):
                prop = pm.group(1)
                raw = pm.group(2).strip().strip("'\"")
                line = line_for_offset(text, style_start + pm.start())
                props[prop] = (raw, line)
            styles[sm.group(1)] = props
    return styles


def native_declared_size(style_props):
    sizes = {}
    for prop in NATIVE_SIZE_PROPS:
        raw = style_props.get(prop)
        if not raw:
            continue
        value = raw[0] if isinstance(raw, tuple) else raw
        if re.fullmatch(r"-?\d*\.?\d+", str(value)):
            sizes[prop] = float(value)
    return sizes


def native_style_props_for(attrs, src, style_map):
    style_raw = jsx_attr_raw(attrs, 'style', src)
    props = native_inline_style_props(style_raw)
    ref = native_style_ref(style_raw)
    if ref and ref in style_map:
        for prop, (value, _line) in style_map[ref].items():
            props.setdefault(prop, value)
    return props


def audit_native_element(node, src, path, tag, attrs):
    out = []
    text = src.decode('utf8', 'replace')
    style_map = parse_native_stylesheets(text)
    is_native_interactive = tag in NATIVE_INTERACTIVE
    is_custom_interactive = tag[:1].isupper() and 'onPress' in attrs and tag not in NATIVE_INTERACTIVE
    is_interactive = is_native_interactive or is_custom_interactive

    if is_native_interactive and 'accessibilityLabel' not in attrs:
        out.append(Finding(
            "native/a11y-missing-label", "ERROR", path, line_of(node),
            f"<{tag}> missing accessibilityLabel",
            "Native touch controls need an accessible name independent of visible layout.",
            f"<{tag}>"))

    if is_custom_interactive and 'accessibilityRole' not in attrs:
        out.append(Finding(
            "native/a11y-missing-role", "ERROR", path, line_of(node),
            f"Custom interactive <{tag}> missing accessibilityRole",
            "Custom pressable components must expose their role to assistive tech.",
            f"<{tag}>"))

    if is_interactive and NATIVE_STATE_ATTRS.intersection(attrs) and 'accessibilityState' not in attrs:
        states = ", ".join(sorted(NATIVE_STATE_ATTRS.intersection(attrs)))
        out.append(Finding(
            "native/a11y-missing-state", "ERROR", path, line_of(node),
            f"<{tag}> has {states} state but no accessibilityState",
            "Mirror disabled, selected, and checked state through accessibilityState.",
            f"<{tag}>"))

    if tag == 'Image':
        decorative = jsx_attr_has_false(attrs, 'accessible', src) or \
            'accessibilityElementsHidden' in attrs or \
            'importantForAccessibility' in attrs and 'no-hide-descendants' in jsx_attr_raw(attrs, 'importantForAccessibility', src)
        if not decorative and ('accessible' not in attrs or 'accessibilityLabel' not in attrs):
            out.append(Finding(
                "native/a11y-image-label", "ERROR", path, line_of(node),
                "<Image> missing accessible + accessibilityLabel",
                "Mark decorative images hidden, or provide accessible={true} and accessibilityLabel.",
                "<Image>"))

    if is_interactive:
        props = native_style_props_for(attrs, src, style_map)
        sizes = native_declared_size(props)
        small = {prop: val for prop, val in sizes.items() if val < 44}
        if small:
            detail = ", ".join(f"{k}: {int(v) if v == int(v) else v}" for k, v in sorted(small.items()))
            out.append(Finding(
                "native/touch-target-small", "ERROR", path, line_of(node),
                f"<{tag}> touch target below 44 ({detail})",
                "Both iOS and Android require at least 44pt/dp touch targets.",
                f"<{tag}>"))
            if 'hitSlop' not in attrs:
                out.append(Finding(
                    "native/touch-target-missing-hitslop", "ERROR", path, line_of(node),
                    f"<{tag}> small touch target missing hitSlop",
                    "Add hitSlop when visual bounds are smaller than the platform target.",
                    f"<{tag}>"))

    return out


def native_token_kind(prop, value):
    if RN_HEX_RE.search(value) or RN_RGB_RE.search(value):
        return "color"
    if "radius" in prop.lower():
        return "radius"
    if prop in NATIVE_TOKEN_PROPS and re.fullmatch(r"-?\d*\.?\d+", value):
        return "space"
    return None


def audit_native_stylesheet_token_drift(path, ds, style_map):
    if not ds or not best_value_token:
        return []
    out = []
    for style_name, props in style_map.items():
        for prop, (value, line) in props.items():
            if prop not in NATIVE_TOKEN_PROPS or 'tokens.' in value or 'var(' in value:
                continue
            kind = native_token_kind(prop, value)
            if not kind:
                continue
            verdict, doc, score, note = best_value_token(
                {'kind': kind, 'value': value, 'property': prop},
                ds['corpus'], ds['bm25'], ds['color_tokens'])
            if verdict not in ('EXACT', 'NEAR') or not doc:
                continue
            token = doc['name']
            out.append(Finding(
                "ds/token-drift", "WARN", path, line,
                f"hardcoded {value} - use token {token}",
                f"Approved native {kind} token found ({verdict}; {note}).",
                f"{style_name}.{prop}"))
    return out


def audit_native_file(src, path, ds=None):
    text = src.decode('utf8', 'replace')
    out = []
    style_map = parse_native_stylesheets(text)

    uses_native_motion = any(k in text for k in ('Animated.', 'Reanimated', 'useSharedValue', 'withTiming', 'withSpring'))
    if uses_native_motion and 'AccessibilityInfo.isReduceMotionEnabled' not in text:
        out.append(Finding(
            "native/motion-no-reduced-motion", "ERROR", path, 1,
            "Native animation used without AccessibilityInfo.isReduceMotionEnabled",
            "Check reduce motion before running Animated or Reanimated transitions."))

    for m in re.finditer(r"(Animated\.\w+\s*\([^)]*(?:transform|opacity)[\s\S]{0,240}?useNativeDriver\s*:\s*false|useNativeDriver\s*:\s*false[\s\S]{0,240}?(?:transform|opacity))", text):
        out.append(Finding(
            "native/motion-js-driver", "ERROR", path, line_for_offset(text, m.start()),
            "Transform/opacity animation uses useNativeDriver: false",
            "Transform and opacity animations should run on the native thread.",
            "useNativeDriver: false"))

    for m in re.finditer(r"Dimensions\.get\s*\(\s*['\"]window['\"]\s*\)", text):
        if not any(k in text for k in ('Dimensions.addEventListener', 'useWindowDimensions')):
            out.append(Finding(
                "native/layout-dimensions-static", "WARN", path, line_for_offset(text, m.start()),
                "Dimensions.get('window') used for layout without a change listener",
                "Use useWindowDimensions or subscribe to dimension changes for rotation and split-screen.",
                "Dimensions.get('window')"))

    for m in re.finditer(r"<ScrollView\b[\s\S]{0,1600}?\.\s*(?:map|forEach)\s*\(", text):
        out.append(Finding(
            "native/layout-scrollview-list", "WARN", path, line_for_offset(text, m.start()),
            "<ScrollView> renders a list",
            "Use <FlatList> for virtualized native lists.",
            "<ScrollView>"))

    screen_like = re.search(r"export\s+(?:default\s+)?function\s+[A-Z][\w]*Screen\b|function\s+Screen\b|const\s+[A-Z][\w]*Screen\s*=", text)
    near_edges = re.search(r"<View\b|flex\s*:\s*1|position\s*:\s*['\"]absolute['\"]|top\s*:\s*0", text)
    has_safe_area = any(k in text for k in ('SafeAreaView', 'useSafeAreaInsets', 'safe-area-context'))
    if screen_like and near_edges and not has_safe_area:
        out.append(Finding(
            "native/layout-missing-safe-area", "WARN", path, 1,
            "Screen-like component has edge content without SafeAreaView or safe-area insets",
            "Respect notches, status bars, and gesture areas with SafeAreaView/useSafeAreaInsets."))

    out += audit_native_stylesheet_token_drift(path, ds, style_map)
    return out


# ----------------------------------------------------------------- HTML

def html_attrs(start_tag, src):
    attrs = {}
    for c in start_tag.children:
        if c.type not in ('attribute', 'directive_attribute'):
            continue
        name_node = None
        value_node = None
        directive_name = ''
        directive_arg = ''
        for part in c.children:
            if part.type == 'attribute_name':
                name_node = part
            elif part.type == 'directive_name':
                directive_name = txt(part, src)
            elif part.type == 'directive_argument':
                directive_arg = txt(part, src)
            elif part.type in ('quoted_attribute_value', 'attribute_value'):
                value_node = part
        if not name_node:
            if directive_name == '@' and directive_arg:
                name = f"@{directive_arg}".lower()
            elif directive_name and directive_arg:
                name = f"{directive_name}:{directive_arg}".lower()
            elif directive_name:
                name = directive_name.lower()
            else:
                continue
        else:
            name = txt(name_node, src).lower()
        value = ''
        if value_node:
            value_text = txt(value_node, src).strip()
            if (value_text.startswith('"') and value_text.endswith('"')) or \
                    (value_text.startswith("'") and value_text.endswith("'")):
                value_text = value_text[1:-1]
            value = value_text
        attrs[name] = {'node': c, 'value': value}
    return attrs


def html_attr_value(attrs, name):
    item = attrs.get(name.lower())
    return item['value'] if item else ''


def offset_findings(findings, line_offset):
    for f in findings:
        f['line'] = max(1, int(f.get('line') or 1) + line_offset)
    return findings


def audit_inline_style(style_text, path, line):
    out = []
    if not scan_value:
        return out
    found = []
    for decl in style_text.split(';'):
        if ':' not in decl:
            continue
        prop, raw = decl.split(':', 1)
        try:
            scan_value(found, path, line, prop.strip(), raw.strip())
        except Exception as e:
            print(f"skip inline style value {path}:{line}: {e}", file=sys.stderr)
    seen = set()
    for item in found:
        key = (item['property'], item['value'])
        if key in seen:
            continue
        seen.add(key)
        out.append(Finding(
            "ds/inline-style-token-drift", "WARN", path, item['line'],
            f"inline style contains hardcoded {item['value']}",
            "Move design values to verified CSS custom properties or approved tokens.",
            item['property']))
    return out


def tag_name_for(node, src):
    name_node = next((c for c in node.children if c.type == 'tag_name'), None)
    return txt(name_node, src) if name_node else ''


def has_reduced_motion_handling(text):
    return any(k in text for k in (
        'prefers-reduced-motion', 'useReducedMotion', 'reducedMotion',
        'matchMedia("(prefers-reduced-motion', "matchMedia('(prefers-reduced-motion",
        '$app/environment',
    ))


def audit_html_element_rules(root, src, path, full_document=False):
    out = []
    text = src.decode('utf8', 'replace')
    label_targets = set()
    has_html = False
    html_has_lang = False
    has_doctype = False
    has_novalidate = False

    for n in walk(root):
        if n.type == 'doctype':
            has_doctype = True
        if n.type not in ('start_tag', 'self_closing_tag'):
            continue
        tag = tag_name_for(n, src).lower()
        attrs = html_attrs(n, src)
        if tag == 'html':
            has_html = True
            html_has_lang = bool(html_attr_value(attrs, 'lang').strip())
        if 'novalidate' in attrs:
            has_novalidate = True
        if tag == 'label' and 'for' in attrs:
            label_targets.add(html_attr_value(attrs, 'for'))

    for n in walk(root):
        if n.type in ('start_tag', 'self_closing_tag'):
            tag = tag_name_for(n, src).lower()
            attrs = html_attrs(n, src)

            if 'onclick' in attrs and tag in ('div', 'span', 'li', 'section', 'p'):
                if 'role' not in attrs or 'onkeydown' not in attrs:
                    out.append(Finding(
                        "a11y/nonsemantic-click", "ERROR", path, line_of(n),
                        f"onclick on <{tag}> without role + keyboard handler",
                        "Use <button>. Native elements carry keyboard and focus behavior.",
                        f"<{tag}>"))

            if 'tabindex' in attrs:
                try:
                    if int(html_attr_value(attrs, 'tabindex')) > 0:
                        out.append(Finding(
                            "a11y/positive-tabindex", "ERROR", path, line_of(n),
                            f"Positive tabindex on <{tag}>",
                            "Breaks natural order. Use 0 or -1 and fix DOM order.",
                            f"<{tag}>"))
                except ValueError:
                    pass

            if tag == 'img':
                if 'alt' not in attrs:
                    out.append(Finding(
                        "a11y/img-missing-alt", "ERROR", path, line_of(n),
                        "<img> missing alt attribute",
                        "Use meaningful alt text, or alt=\"\" for decorative images.",
                        "<img>"))
                if not ({'width', 'height'} & attrs.keys()) and 'style' not in attrs \
                        and 'aspect' not in txt(n, src):
                    out.append(Finding(
                        "layout/img-no-dimensions", "ERROR", path, line_of(n),
                        "<img> without width/height or aspect-ratio",
                        "Primary CLS source. Reserve the space.", "<img>"))

            if tag == 'input':
                input_id = html_attr_value(attrs, 'id')
                labelled = {'aria-label', 'aria-labelledby'} & attrs.keys()
                labelled = labelled or (input_id and input_id in label_targets)
                if 'placeholder' in attrs and not labelled:
                    out.append(Finding(
                        "a11y/placeholder-as-label", "ERROR", path, line_of(n),
                        "Input labelled only by placeholder",
                        "Placeholders vanish on focus and fail contrast. Use <label>.",
                        "<input>"))
                if 'type' in attrs and 'autocomplete' not in attrs:
                    out.append(Finding(
                        "a11y/missing-autocomplete", "INFO", path, line_of(n),
                        "Input without autocomplete token",
                        "autocomplete is an accessibility requirement, not a convenience.",
                        "<input>"))

            if 'required' in attrs and not has_novalidate:
                out.append(Finding(
                    "a11y/native-validation-conflict", "WARN", path, line_of(n),
                    "required present, form has no novalidate",
                    "Native bubbles collide with custom ARIA errors.",
                    f"<{tag}>"))

            if html_attr_value(attrs, 'aria-live').lower() == 'assertive':
                out.append(Finding(
                    "a11y/assertive-live", "WARN", path, line_of(n),
                    "assertive live region",
                    "Reserve for interruptions; use polite/role=alert for errors.",
                    f"<{tag}>"))

            if 'aria-haspopup' in attrs:
                out.append(Finding(
                    "a11y/haspopup-not-focus", "INFO", path, line_of(n),
                    "aria-haspopup announces a popup; it manages no focus",
                    "Ensure real focus handling exists alongside it.",
                    f"<{tag}>"))

            if html_attr_value(attrs, 'role').lower() == 'dialog' and tag != 'dialog':
                out.append(Finding(
                    "a11y/handrolled-dialog", "WARN", path, line_of(n),
                    f'role="dialog" on <{tag}> instead of native <dialog>',
                    "<dialog> gives focus trap, Escape, and inerting for free.",
                    f"<{tag}>"))

            href = html_attr_value(attrs, 'href').strip().lower()
            if tag == 'a' and ('href' not in attrs or href in ('', '#', 'javascript:void(0)')):
                out.append(Finding(
                    "a11y/anchor-button-substitute", "ERROR", path, line_of(n),
                    "<a> used without a real href",
                    "Use <button> for actions and <a href> only for navigation.",
                    "<a>"))

            if 'style' in attrs:
                out += audit_inline_style(html_attr_value(attrs, 'style'), path, line_of(attrs['style']['node']))

    if full_document and (has_html or has_doctype) and not html_has_lang:
        out.append(Finding(
            "a11y/html-missing-lang", "ERROR", path, 1,
            "Full HTML document missing <html lang>",
            "Declare the document language so assistive tech chooses the right voice.",
            "<html>"))

    if 'aria-live' in text or 'role="alert"' in text or "role='alert'" in text:
        out.append(Finding(
            "a11y/live-region-premount", "INFO", path, 1,
            "Live region present - confirm it mounts empty before content",
            "Injecting region and message together often announces nothing."))

    return out


def raw_child(node):
    return next((c for c in node.children if c.type in ('raw_text', 'frontmatter_js_block')), None)


def audit_html(src, path):
    parser = get_parser('html')
    root = parser.parse(src).root_node
    out = audit_html_element_rules(root, src, path, full_document=True)

    for n in walk(root):
        if n.type in ('style_element', 'script_element'):
            raw = next((c for c in n.children if c.type == 'raw_text'), None)
            if not raw:
                continue
            embedded = src[raw.start_byte:raw.end_byte]
            line_offset = line_of(raw) - 1
            try:
                if n.type == 'style_element':
                    out += offset_findings(audit_css(embedded, path), line_offset)
                else:
                    out += offset_findings(audit_jsx(embedded, path), line_offset)
            except Exception as e:
                print(f"skip embedded {n.type} {path}:{line_of(raw)}: {e}", file=sys.stderr)

    return out


# ---------------------------------------------------------- SFC frameworks

def audit_sfc(src, path, lang):
    parser = get_parser(lang)
    root = parser.parse(src).root_node
    out = []
    text = src.decode('utf8', 'replace')
    reduced = has_reduced_motion_handling(text)

    out += audit_html_element_rules(root, src, path, full_document=False)

    for n in walk(root):
        if n.type == 'style_element':
            raw = raw_child(n)
            if not raw:
                continue
            embedded = src[raw.start_byte:raw.end_byte]
            try:
                out += offset_findings(audit_css(embedded, path), line_of(raw) - 1)
            except Exception as e:
                print(f"skip embedded style {path}:{line_of(raw)}: {e}", file=sys.stderr)
        elif n.type == 'script_element':
            raw = raw_child(n)
            if not raw:
                continue
            embedded = src[raw.start_byte:raw.end_byte]
            try:
                script_findings = offset_findings(audit_jsx(embedded, path), line_of(raw) - 1)
                if lang == 'vue':
                    script_findings = [
                        f for f in script_findings
                        if f.get('rule') != 'state/boolean-soup'
                    ]
                out += script_findings
            except Exception as e:
                print(f"skip embedded script {path}:{line_of(raw)}: {e}", file=sys.stderr)
        elif lang == 'astro' and n.type == 'frontmatter':
            raw = raw_child(n)
            if not raw:
                continue
            embedded = src[raw.start_byte:raw.end_byte]
            try:
                out += offset_findings(audit_jsx(embedded, path), line_of(raw) - 1)
            except Exception as e:
                print(f"skip frontmatter script {path}:{line_of(raw)}: {e}", file=sys.stderr)

    if lang == 'svelte':
        out += audit_svelte_rules(root, src, path, text, reduced)
    elif lang == 'vue':
        out += audit_vue_rules(root, src, path, text, reduced)
    elif lang == 'astro':
        out += audit_astro_rules(root, src, path)
    return out


def audit_svelte_rules(root, src, path, text, reduced):
    out = []
    first_motion_directive = None
    for n in walk(root):
        if n.type == 'start_tag':
            tag = tag_name_for(n, src).lower()
            attrs = html_attrs(n, src)
            for name, item in attrs.items():
                if name.startswith(('transition:', 'in:', 'out:', 'animate:')) and not first_motion_directive:
                    first_motion_directive = (name, item['node'])
            if 'on:click' in attrs and tag in ('div', 'span', 'li', 'section', 'p'):
                if 'role' not in attrs or 'on:keydown' not in attrs:
                    out.append(Finding(
                        "a11y/svelte-nonsemantic-click", "ERROR", path, line_of(n),
                        f"on:click on <{tag}> without role + keyboard handler",
                        "Use <button>. Native elements carry keyboard and focus behavior.",
                        f"<{tag}>"))
        if n.type == 'await_statement':
            if 'catch' not in {c.type for c in walk(n)}:
                out.append(Finding(
                    "state/svelte-await-no-catch", "ERROR", path, line_of(n),
                    "{#await} block has no {:catch} branch",
                    "Async UI needs an explicit error state, not just loading and success.",
                    "{#await}"))
    if first_motion_directive and not reduced:
        name, node = first_motion_directive
        out.append(Finding(
            "motion/svelte-no-reduced-motion", "ERROR", path, line_of(node),
            f"Svelte {name} directive used without reduced-motion handling",
            "Gate transition:, in:, out:, and animate: with prefers-reduced-motion logic.",
            name))
    return out


def audit_vue_rules(root, src, path, text, reduced):
    out = []
    first_transition = None
    for n in walk(root):
        if n.type in ('start_tag', 'self_closing_tag'):
            tag = tag_name_for(n, src)
            lower = tag.lower()
            attrs = html_attrs(n, src)
            if tag in ('Transition', 'TransitionGroup') and not first_transition:
                first_transition = n
            if any(k in attrs for k in ('@click', 'v-on:click')) and lower in ('div', 'span', 'li', 'section', 'p'):
                if 'role' not in attrs or not any(k in attrs for k in ('@keydown', 'v-on:keydown', 'onkeydown')):
                    out.append(Finding(
                        "a11y/vue-nonsemantic-click", "ERROR", path, line_of(n),
                        f"@click on <{lower}> without role + keyboard handler",
                        "Use <button>. Native elements carry keyboard and focus behavior.",
                        f"<{lower}>"))
            if 'v-html' in attrs:
                out.append(Finding(
                    "security/vue-v-html", "ERROR", path, line_of(n),
                    "v-html bypasses Vue escaping",
                    "Render trusted, sanitized HTML only; prefer text binding for user content.",
                    f"<{lower}>"))
    if first_transition and not reduced:
        out.append(Finding(
            "motion/vue-no-reduced-motion", "ERROR", path, line_of(first_transition),
            "Vue <Transition> used without reduced-motion handling",
            "Gate <Transition>/<TransitionGroup> with prefers-reduced-motion logic.",
            tag_name_for(first_transition, src)))

    refs = re.findall(r"\b(?:const|let|var)\s+(isLoading|isPending|isError|hasError|isSuccess)\s*=\s*ref\s*\(", text)
    if len(set(refs)) >= 2 and 'status' not in text:
        first_ref = re.search(r"\b(?:const|let|var)\s+(?:isLoading|isPending|isError|hasError|isSuccess)\s*=\s*ref\s*\(", text)
        out.append(Finding(
            "state/boolean-soup", "WARN", path, 1,
            f"{len(set(refs))} Vue boolean refs, no status union",
            "Booleans permit loading && error && success. Use one status ref/union."))
        if first_ref:
            out[-1]['line'] = line_for_offset(text, first_ref.start())
    return out


def audit_astro_rules(root, src, path):
    out = []
    for n in walk(root):
        if n.type in ('start_tag', 'self_closing_tag'):
            tag = tag_name_for(n, src)
            attrs = html_attrs(n, src)
            if 'client:load' in attrs and tag[:1].isupper():
                out.append(Finding(
                    "perf/astro-client-load-static", "INFO", path, line_of(n),
                    f"<{tag}> uses client:load hydration",
                    "Astro islands should stay static unless immediate client interactivity is required.",
                    f"<{tag}>"))
        if n.type == 'style_element':
            start = next((c for c in n.children if c.type == 'start_tag'), None)
            attrs = html_attrs(start, src) if start else {}
            raw = raw_child(n)
            style_text = txt(raw, src) if raw else ''
            global_intent = re.search(r"(^|[,{]\s*)(html|body|:root|\*|\[data-theme)", style_text, re.M)
            if global_intent and 'is:global' not in attrs:
                out.append(Finding(
                    "css/astro-global-style-scope", "WARN", path, line_of(n),
                    "<style> appears to target global selectors without is:global",
                    "Astro scopes component styles by default; add is:global only when global styling is intentional.",
                    "<style>"))
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
    by_file = defaultdict(list)
    for row in bounded:
        by_file[row['file']].append(row)
    for file_rows in by_file.values():
        for i, left in enumerate(file_rows):
            a0, a1 = breakpoint_interval(left)
            if a1 == float('inf'):
                continue
            for right in file_rows[i + 1:]:
                b0, b1 = breakpoint_interval(right)
                if b1 == float('inf'):
                    continue
                if max(a0, b0) < min(a1, b1):
                    out.append(Finding(
                        "responsive/overlapping-breakpoints", "WARN", right['file'], right['line'],
                        "Breakpoint range overlaps another query and both can match",
                        f"Clarify the range or cascade order. Overlaps {left['file']}:{left['line']}.",
                        f"{left['query']} <> {right['query']}"))
        finite = [(breakpoint_interval(r)[0], breakpoint_interval(r)[1], r) for r in file_rows]
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
    print("\n  Kinetic UI UX Pro breakpoint table\n")
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


# ------------------------------------------------------ responsive intent

INTENT_FIELDS = {
    'query': ('query', 'breakpoint'),
    'navigation': ('navigation', 'nav'),
    'primary_content': ('primary content', 'content reflow', 'reflow'),
    'persist': ('persist', 'must persist', 'kept'),
    'remove': ('remove', 'removed', 'deprioritized', 'hidden'),
    'tap_changes': ('tap changes', 'tap-based', 'hover to tap'),
    'primary_action': ('primary action', 'action'),
}
REMOVAL_REASON_RE = re.compile(
    r"\b(because|reason|secondary|available through|available in|moved to|via|path|drawer|menu|details?|disclosure)\b",
    re.I)
NAV_PATTERNS = {
    'bottom tabs': (r"bottom[-_\s]?tabs?", r"tablist", r"mobile[-_\s]?tabs?"),
    'tab bar': (r"tab[-_\s]?bar", r"tablist", r"mobile[-_\s]?tabs?"),
    'drawer': (r"drawer", r"sheet", r"aria-expanded", r"menu"),
    'collapsible sidebar': (r"collapsible[-_\s]?sidebar", r"sidebar", r"aria-expanded"),
    'persistent sidebar': (r"persistent[-_\s]?sidebar", r"desktop[-_\s]?sidebar", r"<aside\b"),
    'sidebar': (r"sidebar", r"<aside\b", r"side[-_\s]?nav"),
    'top nav': (r"top[-_\s]?nav", r"<nav\b", r"<header\b"),
    'breadcrumb': (r"breadcrumb", r"aria-label=['\"]breadcrumb"),
    'rail': (r"\brail\b", r"nav[-_\s]?rail"),
}


def intent_field_for(label):
    key = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
    for field, aliases in INTENT_FIELDS.items():
        if key in aliases:
            return field
    return None


def parse_responsive_intent(path):
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    sections = []
    current = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        heading = re.match(r"^#{2,4}\s+(?:Breakpoint:\s*)?(.+?)\s*$", raw, re.I)
        if heading and 'responsive intent' not in heading.group(1).lower():
            if current:
                sections.append(current)
            title = heading.group(1).strip()
            current = {
                'name': title,
                'line': lineno,
                'fields': {field: [] for field in INTENT_FIELDS},
            }
            query = re.search(r"(\([^)]*width[^)]*\))", title, re.I)
            if query:
                current['fields']['query'].append((query.group(1), lineno))
            continue
        if not current:
            continue
        bullet = re.match(r"^\s*[-*]\s*([^:]+):\s*(.+?)\s*$", raw)
        if not bullet:
            continue
        field = intent_field_for(bullet.group(1))
        if field:
            current['fields'][field].append((bullet.group(2).strip(), lineno))
    if current:
        sections.append(current)
    return sections


def split_intent_items(values):
    items = []
    for value, line in values:
        if value.strip().lower().rstrip('.') in ('none', 'n/a', 'na'):
            continue
        for part in re.split(r",|;", value):
            item = part.strip()
            if item:
                items.append((item, line))
    return items


def normalize_selector_token(value):
    value = re.sub(r"`", "", value.strip())
    value = re.split(r"\s+(?:because|why|reason)\b", value, 1, flags=re.I)[0]
    return value.strip().rstrip('.')


def selector_mentions(selector, item):
    token = normalize_selector_token(item)
    if not token:
        return False
    if token.startswith(('.', '#', '[')):
        return token in selector
    low_selector = selector.lower()
    low_token = re.sub(r"[^a-z0-9_-]+", " ", token.lower()).strip()
    if not low_token:
        return False
    variants = {low_token, low_token.replace(" ", "-"), low_token.replace(" ", "_")}
    return any(v in low_selector for v in variants)


def collect_source_text(files):
    chunks = []
    for path in files:
        if path.suffix not in LANG_BY_EXT:
            continue
        try:
            chunks.append(path.read_text(encoding='utf-8', errors='replace')[:200000])
        except Exception:
            pass
    return "\n".join(chunks)


def collect_hidden_selectors(files):
    hidden = []
    block_re = re.compile(r"([^{}@]+)\{([^{}]*(?:display\s*:\s*none|visibility\s*:\s*hidden|content-visibility\s*:\s*hidden)[^{}]*)\}", re.I | re.S)
    for path in files:
        if path.suffix not in ('.css', '.scss'):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for media in BREAKPOINT_AT_RE.finditer(text):
            brace = text.find('{', media.end() - 1)
            if brace < 0:
                continue
            end = find_matching_brace(text, brace)
            body = text[brace + 1:end - 1]
            query = " ".join(media.group(2).strip().split())
            for m in block_re.finditer(body):
                selector = " ".join(m.group(1).strip().split())
                hidden.append({
                    'file': path,
                    'line': line_for_offset(text, brace + 1 + m.start()),
                    'selector': selector,
                    'query': query,
                    'distinct': parse_breakpoint_query(query)[2],
                })
    return hidden


def breakpoint_declared(intent_query, breakpoint_rows):
    try:
        _lower, _upper, values, _px_units = parse_breakpoint_query(intent_query)
    except Exception:
        return False
    if not values:
        return True
    code_values = [value for row in breakpoint_rows for value in row['distinct']]
    return all(any(abs(value - code) < 0.5 for code in code_values) for value in values)


def intent_query_overlaps_hidden(intent_query, hidden):
    try:
        _lower, _upper, values, _px_units = parse_breakpoint_query(intent_query)
    except Exception:
        return True
    if not values or not hidden.get('distinct'):
        return True
    return any(abs(value - other) < 0.5 for value in values for other in hidden['distinct'])


def nav_pattern_matches(intent_text, source_text):
    low = intent_text.lower()
    for label, patterns in NAV_PATTERNS.items():
        if label in low:
            return any(re.search(pattern, source_text, re.I) for pattern in patterns)
    selectors = re.findall(r"[.#][A-Za-z_][\w-]*", intent_text)
    if selectors:
        return any(selector in source_text for selector in selectors)
    return True


def audit_responsive_intent(intent_path, files, breakpoint_rows):
    try:
        sections = parse_responsive_intent(intent_path)
    except Exception as e:
        return [Finding(
            "responsive/intent-unreadable", "ERROR", intent_path, 1,
            f"Could not read responsive intent spec: {e}",
            "Use templates/responsive-intent.md as the structure.",
            "responsive intent")]
    out = []
    source_text = collect_source_text(files)
    hidden = collect_hidden_selectors(files)
    intent_file = Path(intent_path)
    if not sections:
        return [Finding(
            "responsive/intent-empty", "ERROR", intent_file, 1,
            "Responsive intent spec has no breakpoint sections",
            "Declare at least one `## Breakpoint:` section with a query and behavior fields.",
            "responsive intent")]

    for section in sections:
        fields = section['fields']
        for field in ('query', 'navigation', 'primary_content', 'tap_changes', 'primary_action'):
            if not fields[field]:
                out.append(Finding(
                    "responsive/intent-missing-field", "WARN", intent_file, section['line'],
                    f"{section['name']} has no {field.replace('_', ' ')} decision",
                    "Each breakpoint should state nav, reflow, tap behavior, and primary action intent.",
                    section['name']))
        queries = [value for value, _line in fields['query']]
        for query, line in fields['query']:
            if not breakpoint_declared(query, breakpoint_rows):
                out.append(Finding(
                    "responsive/intent-breakpoint-absent", "WARN", intent_file, line,
                    f"Spec declares breakpoint {query}, but audited CSS does not",
                    "Either implement the declared breakpoint or revise the intent spec.",
                    section['name']))
        for value, line in fields['navigation']:
            if not nav_pattern_matches(value, source_text):
                out.append(Finding(
                    "responsive/intent-nav-mismatch", "WARN", intent_file, line,
                    f"Navigation intent not found in implementation: {value}",
                    "Use a declared class/pattern in the component or update the intent.",
                    section['name']))
        for item, line in split_intent_items(fields['remove']):
            if not REMOVAL_REASON_RE.search(item):
                out.append(Finding(
                    "responsive/intent-removal-unjustified", "WARN", intent_file, line,
                    f"Removal is not justified: {item}",
                    "Hidden content needs a reason or a named alternate path.",
                    section['name']))
        for item, line in split_intent_items(fields['persist']):
            for hidden_item in hidden:
                if queries and not any(intent_query_overlaps_hidden(q, hidden_item) for q in queries):
                    continue
                if selector_mentions(hidden_item['selector'], item):
                    out.append(Finding(
                        "responsive/intent-persist-hidden", "WARN", hidden_item['file'], hidden_item['line'],
                        f"{item} is declared to persist at {section['name']} but is hidden in CSS",
                        f"Spec says it should remain available; hidden under {hidden_item['query']}.",
                        hidden_item['selector']))
                    break
    return out


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


CONTENT_SHAPES = {
    "person-names": re.compile(r"\b(customer|user|person|people|assignee|owner|recipient|fullName|firstName|lastName|displayName)\b", re.I),
    "company-names": re.compile(r"\b(company|account|organization|orgName|vendor|supplier|client)\b", re.I),
    "product-titles": re.compile(r"\b(product|item|sku|title|catalog|variant)\b", re.I),
    "addresses": re.compile(r"\b(address|street|city|postal|zipcode|zipCode|delivery|shipping|billing)\b", re.I),
    "email-addresses": re.compile(r"\b(email|e-mail|mailTo|contactEmail)\b", re.I),
    "prices": re.compile(r"\b(price|amount|total|subtotal|currency|discount|tax|fee|balance|payment)\b", re.I),
    "dates": re.compile(r"\b(date|createdAt|updatedAt|deadline|scheduled|expires|dueDate)\b", re.I),
    "durations": re.compile(r"\b(duration|eta|timeLeft|processingTime)\b", re.I),
    "file-names": re.compile(r"\b(fileName|filename|attachmentName|uploadedFile|downloadName|\.pdf|\.csv|\.xlsx)\b", re.I),
    "paragraph-body-copy": re.compile(r"\b(description|summary|notes|message|details|comment)\b", re.I),
}
FIXTURE_EVIDENCE_RE = re.compile(
    r"content_fixtures|edge-cases-only|edgeCasesOnly|hostile|forty-percent|40%",
    re.I)


def nearby_fixture_text(path):
    chunks = []
    roots = [path.parent]
    for name in ("tests", "__tests__", "fixtures"):
        candidate = path.parent / name
        if candidate.exists():
            roots.append(candidate)
    for root in roots:
        try:
            files = list(root.rglob("*")) if root.is_dir() else []
        except Exception:
            continue
        for f in files[:200]:
            if f.is_file() and f.suffix in ('.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.html'):
                try:
                    chunks.append(f.read_text(encoding='utf-8', errors='replace')[:8000])
                except Exception:
                    pass
    return "\n".join(chunks)


def fixture_surface_text(text):
    chunks = []
    attr_names = (
        'aria-label', 'aria-labelledby', 'placeholder', 'title', 'alt',
        'label', 'name', 'id', 'htmlFor', 'for'
    )
    attr_alt = "|".join(re.escape(name) for name in attr_names)
    for m in re.finditer(rf"\b(?:{attr_alt})\s*=\s*(?:{{\s*)?['\"]([^'\"]+)['\"]", text, re.I):
        chunks.append(m.group(1))
    for m in re.finditer(r">\s*([^<>{}\n][^<>{}]*?)\s*<", text):
        visible = re.sub(r"\s+", " ", m.group(1)).strip()
        if visible:
            chunks.append(visible)
    data_keys = (
        'name', 'fullName', 'firstName', 'lastName', 'displayName',
        'email', 'company', 'account', 'organization', 'title', 'product',
        'address', 'city', 'postalCode', 'zipCode', 'price', 'amount',
        'total', 'date', 'dueDate', 'duration', 'fileName', 'attachmentName',
        'description', 'summary', 'message', 'notes'
    )
    data_alt = "|".join(re.escape(key) for key in data_keys)
    for m in re.finditer(rf"\b({data_alt})\b\s*[:=]", text):
        chunks.append(m.group(1))
    return "\n".join(chunks)


def audit_content_fixtures(path):
    if path.suffix not in ('.tsx', '.jsx', '.ts', '.js', '.html', '.htm', '.svelte', '.vue', '.astro'):
        return []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"skip content fixtures {path}: {e}", file=sys.stderr)
        return []
    surface = fixture_surface_text(text)
    shapes = sorted(shape for shape, pattern in CONTENT_SHAPES.items()
                    if pattern.search(surface))
    evidence_text = text + "\n" + nearby_fixture_text(path)
    has_edge_set = bool(FIXTURE_EVIDENCE_RE.search(evidence_text))
    if not shapes:
        return [Finding(
            "content/fixtures-coverage", "INFO", path, 1,
            "No obvious dynamic content shapes detected",
            "If this component renders user or product content, test it with scripts/content_fixtures.py --edge-cases-only.",
            "content fixtures")]
    status = "edge fixture evidence found" if has_edge_set else "no edge fixture evidence found"
    return [Finding(
        "content/fixtures-coverage", "INFO", path, 1,
        f"Likely content shapes: {', '.join(shapes)}; {status}",
        "Run scripts/content_fixtures.py generate for these shapes, including --edge-cases-only and --empty-states, before visual approval.",
        "content fixtures")]


def detect_platform(src, requested):
    if requested in ('web', 'native'):
        return requested
    text = src.decode('utf8', 'replace')
    return 'native' if NATIVE_IMPORT_RE.search(text) else 'web'


def suppress_native_web_rules(findings):
    return [f for f in findings if f.get('rule') not in NATIVE_SUPPRESS_RULES]


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
        if path.suffix == '.js' and not node['css_imports']:
            for css_path, classes in css_classes.items():
                if css_path.parent == path.parent:
                    imported_classes.update(classes)
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


def audit_file(path, ds=None, platform='auto'):
    lang = LANG_BY_EXT.get(path.suffix)
    if not lang:
        return []
    src = path.read_bytes()
    active_platform = detect_platform(src, platform)
    out = []
    if lang == 'css':
        out = audit_css(src, path)
    elif lang == 'html':
        out = audit_html(src, path)
    elif lang in ('svelte', 'vue', 'astro'):
        out = audit_sfc(src, path, lang)
    elif lang in ('tsx', 'typescript', 'javascript'):
        out = audit_jsx(src, path, active_platform, ds)
    if active_platform != 'native':
        out += audit_token_drift(path, ds)
    if active_platform == 'native':
        out = suppress_native_web_rules(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target')
    ap.add_argument('--ext', default='.tsx,.jsx,.ts,.js,.css,.scss,.html,.htm,.svelte,.vue,.astro')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--format', default='text',
                    choices=['text', 'json', 'sarif', 'junit'],
                    help='output format; --json is kept as an alias for --format json')
    ap.add_argument('--ds-index',
                    help='path to .ds-index/corpus.jsonl for token drift warnings')
    ap.add_argument('--breakpoints', action='store_true',
                    help='print only the CSS breakpoint table')
    ap.add_argument('--platform', default='auto',
                    choices=['web', 'native', 'auto'],
                    help='web, native, or auto-detect React Native/Expo imports')
    ap.add_argument('--fixtures', action='store_true',
                    help='report likely rendered content shapes and edge-fixture coverage')
    ap.add_argument('--intent',
                    help='responsive intent markdown spec to compare against audited CSS/markup')
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
    if args.intent:
        findings += audit_responsive_intent(Path(args.intent), files, breakpoint_rows)
    for f in files:
        try:
            findings += audit_file(f, ds, args.platform)
            if args.fixtures:
                findings += audit_content_fixtures(f)
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
        print(f"\n  Kinetic UI UX Pro AST audit — {len(files)} file(s)\n")
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
