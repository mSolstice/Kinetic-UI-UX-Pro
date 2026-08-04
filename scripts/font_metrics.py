#!/usr/bin/env python3
"""
Compute real @font-face override values from a font file.

Font geometry CANNOT be recalled from memory. A wrong size-adjust produces
MORE layout shift than no override. Either run this, use next/font or
Fontaine, or omit the overrides entirely — never invent the numbers.

Usage:
  python font_metrics.py Inter-Regular.woff2
  python font_metrics.py Inter-Regular.woff2 --fallback "Arial"

Requires fontTools:  pip install fonttools brotli --break-system-packages
"""

import sys
import argparse

# Published metrics for common system fallbacks (unitsPerEm-normalized).
# Source values are stable across OS versions for these specific faces.
FALLBACKS = {
    "Arial":            {"ascent": 0.9052, "descent": 0.2119, "lineGap": 0.0333, "avgWidth": 0.5262},
    "Helvetica":        {"ascent": 0.7700, "descent": 0.2300, "lineGap": 0.0000, "avgWidth": 0.5271},
    "Times New Roman":  {"ascent": 0.8911, "descent": 0.2158, "lineGap": 0.0000, "avgWidth": 0.4560},
    "Georgia":          {"ascent": 0.9170, "descent": 0.2190, "lineGap": 0.0000, "avgWidth": 0.5121},
    "Verdana":          {"ascent": 1.0050, "descent": 0.2100, "lineGap": 0.0000, "avgWidth": 0.5637},
    "Courier New":      {"ascent": 0.8329, "descent": 0.3002, "lineGap": 0.0000, "avgWidth": 0.6000},
}


def read_metrics(path):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("fontTools not installed.\n"
              "  pip install fonttools brotli --break-system-packages\n"
              "Alternative: use next/font, Fontaine, or Capsize.\n"
              "Do NOT guess these values.", file=sys.stderr)
        sys.exit(2)

    f = TTFont(path, lazy=True)
    upm = f['head'].unitsPerEm
    hhea = f['hhea']
    ascent, descent, gap = hhea.ascent, abs(hhea.descent), hhea.lineGap

    # OS/2 typo metrics are preferred when USE_TYPO_METRICS (bit 7) is set
    if 'OS/2' in f:
        os2 = f['OS/2']
        if getattr(os2, 'fsSelection', 0) & (1 << 7):
            ascent, descent, gap = (os2.sTypoAscender,
                                    abs(os2.sTypoDescender),
                                    os2.sTypoLineGap)
        avg = getattr(os2, 'xAvgCharWidth', 0) / upm
    else:
        avg = 0

    name = "unknown"
    for rec in f['name'].names:
        if rec.nameID == 1:
            try:
                name = rec.toUnicode()
                break
            except Exception:
                pass

    return {
        "family": name, "upm": upm,
        "ascent": ascent / upm, "descent": descent / upm,
        "lineGap": gap / upm, "avgWidth": avg,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('font')
    ap.add_argument('--fallback', default='Arial', choices=list(FALLBACKS))
    args = ap.parse_args()

    m = read_metrics(args.font)
    fb = FALLBACKS[args.fallback]

    if m['avgWidth'] and fb['avgWidth']:
        size_adjust = m['avgWidth'] / fb['avgWidth']
    else:
        size_adjust = 1.0
        print("  ! xAvgCharWidth unavailable; size-adjust left at 100%.\n"
              "    Verify visually or use Fontaine.\n", file=sys.stderr)

    # overrides are expressed relative to the adjusted em
    asc = m['ascent'] / size_adjust
    desc = m['descent'] / size_adjust
    gap = m['lineGap'] / size_adjust

    print(f"\n/* {m['family']} — computed from {args.font} (upm {m['upm']}) */")
    print(f"@font-face {{")
    print(f"  font-family: '{args.fallback} Fallback';")
    print(f"  src: local('{args.fallback}');")
    print(f"  size-adjust: {size_adjust * 100:.2f}%;")
    print(f"  ascent-override: {asc * 100:.2f}%;")
    print(f"  descent-override: {desc * 100:.2f}%;")
    print(f"  line-gap-override: {gap * 100:.2f}%;")
    print(f"}}\n")
    print(f"body {{ font-family: '{m['family']}', '{args.fallback} Fallback', sans-serif; }}\n")


if __name__ == '__main__':
    main()
