#!/usr/bin/env python3
"""
Color computation for the Kinetic UI UX Pro skill.

Never estimate contrast — run this.

Usage:
  python color_tools.py contrast "#1a1a1a" "#ffffff"
  python color_tools.py contrast "oklch(0.21 0.02 265)" "oklch(0.98 0.005 265)"
  python color_tools.py ramp "oklch(0.55 0.18 265)"
  python color_tools.py convert "oklch(0.7 0.15 145)"
  python color_tools.py pair "#0d47a1" "#ffffff" --size body

Implements APCA-W3 0.1.9 constants. APCA is a WCAG 3 working draft: use it to
optimize ABOVE the WCAG 2.x AA floor, never to justify failing it.
"""

import sys
import math
import argparse
import re

# ---------------------------------------------------------------- parsing

HEX_RE = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
OKLCH_RE = re.compile(
    r'oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*([\d.]+%?)\s*)?\)',
    re.I)


def parse_color(s):
    """Return (r, g, b) floats in 0..1 sRGB from hex or oklch()."""
    s = s.strip()
    m = HEX_RE.match(s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    m = OKLCH_RE.match(s)
    if m:
        L = float(m.group(1).rstrip('%'))
        if m.group(1).endswith('%'):
            L /= 100
        return oklch_to_srgb(L, float(m.group(2)), float(m.group(3)))
    raise ValueError(f"Unrecognized color: {s!r} (use #hex or oklch(L C H))")


# ---------------------------------------------------------------- oklch

def oklch_to_srgb(L, C, H):
    """OKLCH -> gamma-encoded sRGB, unclamped (may be out of gamut)."""
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    lr = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    lg = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    lb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return tuple(gamma_encode(v) for v in (lr, lg, lb))


def gamma_encode(v):
    if v <= 0.0031308:
        return 12.92 * v
    return 1.055 * (abs(v) ** (1 / 2.4)) * (1 if v >= 0 else -1) - 0.055


def in_gamut(rgb, tol=1e-4):
    return all(-tol <= c <= 1 + tol for c in rgb)


def gamut_map(L, C, H):
    """Binary-search chroma down until the color fits sRGB. Returns (C, rgb)."""
    if in_gamut(oklch_to_srgb(L, C, H)):
        return C, oklch_to_srgb(L, C, H)
    lo, hi = 0.0, C
    for _ in range(40):
        mid = (lo + hi) / 2
        if in_gamut(oklch_to_srgb(L, mid, H)):
            lo = mid
        else:
            hi = mid
    return round(lo, 4), oklch_to_srgb(L, lo, H)


def to_hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, round(c * 255))):02x}' for c in rgb)


# ---------------------------------------------------------------- WCAG 2.x

def rel_luminance(rgb):
    def lin(c):
        c = max(0.0, min(1.0, c))
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(fg, bg):
    l1, l2 = rel_luminance(fg), rel_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- APCA

_MAIN_TRC = 2.4
_RCO, _GCO, _BCO = 0.2126729, 0.7151522, 0.0721750
_NORM_BG, _NORM_TXT = 0.56, 0.57
_REV_TXT, _REV_BG = 0.62, 0.65
_BLK_THRS, _BLK_CLMP = 0.022, 1.414
_SCALE_BOW, _SCALE_WOB = 1.14, 1.14
_LO_BOW_OFFSET, _LO_WOB_OFFSET = 0.027, 0.027
_DELTA_Y_MIN, _LO_CLIP = 0.0005, 0.1


def _apca_y(rgb):
    r, g, b = (max(0.0, min(1.0, c)) for c in rgb)
    y = (r ** _MAIN_TRC) * _RCO + (g ** _MAIN_TRC) * _GCO + (b ** _MAIN_TRC) * _BCO
    return y + (_BLK_THRS - y) ** _BLK_CLMP if y < _BLK_THRS else y


def apca_lc(text_rgb, bg_rgb):
    """Lightness contrast. Sign indicates polarity; magnitude is what you compare."""
    yt, yb = _apca_y(text_rgb), _apca_y(bg_rgb)
    if abs(yb - yt) < _DELTA_Y_MIN:
        return 0.0
    if yb > yt:  # dark text on light bg
        s = (yb ** _NORM_BG - yt ** _NORM_TXT) * _SCALE_BOW
        out = 0.0 if s < _LO_CLIP else s - _LO_BOW_OFFSET
    else:        # light text on dark bg
        s = (yb ** _REV_BG - yt ** _REV_TXT) * _SCALE_WOB
        out = 0.0 if s > -_LO_CLIP else s + _LO_WOB_OFFSET
    return round(out * 100, 1)


APCA_TIERS = [
    (90, "body text / small text"),
    (75, "large text, subheads (~24px normal or 19px bold)"),
    (60, "headlines (~36px+)"),
    (45, "large bold display (~48px+)"),
    (30, "absolute floor — non-text, disabled states only"),
]


def apca_verdict(lc, size='body'):
    need = {'body': 90, 'large': 75, 'headline': 60,
            'display': 45, 'nontext': 30}.get(size, 90)
    a = abs(lc)
    return need, a >= need


# ---------------------------------------------------------------- commands

def cmd_contrast(args):
    fg, bg = parse_color(args.fg), parse_color(args.bg)
    ratio = wcag_ratio(fg, bg)
    lc = apca_lc(fg, bg)
    need, ok = apca_verdict(lc, args.size)

    print(f"\n  foreground {to_hex(fg)}   background {to_hex(bg)}")
    print(f"  polarity   {'light text on dark' if lc < 0 else 'dark text on light'}")
    print("\n  WCAG 2.x (legal floor — must pass)")
    print(f"    ratio            {ratio:.2f}:1")
    print(f"    AA normal 4.5:1  {'PASS' if ratio >= 4.5 else 'FAIL'}")
    print(f"    AA large  3.0:1  {'PASS' if ratio >= 3.0 else 'FAIL'}")
    print(f"    AAA       7.0:1  {'PASS' if ratio >= 7.0 else 'FAIL'}")
    print("\n  APCA (optimization target above the floor)")
    print(f"    Lc               {lc}")
    print(f"    needs for {args.size:<8} {need}   {'PASS' if ok else 'FAIL'}")
    if ratio < 4.5:
        print("\n  ! WCAG 2.x AA fails. Fix this before considering APCA.")
    print()


def cmd_convert(args):
    rgb = parse_color(args.color)
    m = OKLCH_RE.match(args.color.strip())
    print(f"\n  hex        {to_hex(rgb)}")
    print(f"  in gamut   {'yes' if in_gamut(rgb) else 'NO — clipping'}")
    if m and not in_gamut(rgb):
        L = float(m.group(1).rstrip('%'))
        if m.group(1).endswith('%'):
            L /= 100
        c2, rgb2 = gamut_map(L, float(m.group(2)), float(m.group(3)))
        print(f"  mapped     oklch({L} {c2} {m.group(3)})  ->  {to_hex(rgb2)}")
    print()


def cmd_ramp(args):
    m = OKLCH_RE.match(args.color.strip())
    if not m:
        print("ramp requires an oklch() input, e.g. 'oklch(0.55 0.18 265)'")
        sys.exit(1)
    C, H = float(m.group(2)), float(m.group(3))
    steps = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
    lightness = [0.97, 0.94, 0.87, 0.78, 0.68, 0.58,
                 0.50, 0.42, 0.34, 0.26, 0.19]
    # taper chroma at the extremes so the ramp stays in gamut and neutral-ish
    taper = [0.28, 0.42, 0.62, 0.82, 0.95, 1.0, 0.98, 0.9, 0.78, 0.62, 0.46]

    print(f"\n  /* ramp from hue {H}, base chroma {C} */")
    white, black = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)
    for step, L, t in zip(steps, lightness, taper):
        c_req = round(C * t, 4)
        c_fit, rgb = gamut_map(L, c_req, H)
        flag = "  (chroma reduced to fit sRGB)" if c_fit < c_req - 1e-3 else ""
        lc_w = abs(apca_lc(white, rgb))
        lc_b = abs(apca_lc(black, rgb))
        print(f"  --brand-{step:<4}: oklch({L} {c_fit} {H});"
              f"  /* {to_hex(rgb)}  Lc vs white {lc_w:5.1f} | vs black {lc_b:5.1f}{flag} */")
    print("\n  Body text needs Lc >= 90. Pick the text color whose Lc against"
          "\n  your surface clears that, then re-check with `contrast`.\n")


def cmd_pair(args):
    return cmd_contrast(args)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('contrast', help='WCAG 2.x + APCA for a fg/bg pair')
    c.add_argument('fg')
    c.add_argument('bg')
    c.add_argument('--size', default='body',
                   choices=['body', 'large', 'headline', 'display', 'nontext'])
    c.set_defaults(func=cmd_contrast)

    v = sub.add_parser('convert', help='OKLCH -> hex, with gamut check')
    v.add_argument('color')
    v.set_defaults(func=cmd_convert)

    r = sub.add_parser('ramp', help='generate a gamut-safe OKLCH scale')
    r.add_argument('color')
    r.set_defaults(func=cmd_ramp)

    pr = sub.add_parser('pair', help='alias for contrast')
    pr.add_argument('fg')
    pr.add_argument('bg')
    pr.add_argument('--size', default='body',
                    choices=['body', 'large', 'headline', 'display', 'nontext'])
    pr.set_defaults(func=cmd_pair)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
