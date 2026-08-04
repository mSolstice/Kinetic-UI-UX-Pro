# Color, Contrast & Typography

## The dual gate — order matters

1. **WCAG 2.x AA is the floor and is non-negotiable.** 4.5:1 body text, 3:1 large text and non-text UI. ADA, Section 508, and EN 301 549 all reference WCAG 2.x. A design failing it is non-conformant regardless of appearance.
2. **APCA is the optimization target above that floor.** A WCAG 3 working draft that models perception better, especially for thin weights and dark backgrounds. Use it to choose between options that already clear WCAG 2.x — never to justify one that doesn't.

**APCA tiers (|Lc|):** ~90 body · ~75 large text and subheads · ~60 headlines · ~45 large bold display · ~30 absolute floor for non-text and disabled.

APCA is polarity-sensitive — light-on-dark and dark-on-light are not interchangeable. Validate each direction separately.

## Never state a number you did not compute

```bash
python scripts/color_tools.py contrast "#1a1a1a" "#ffffff" --size body
python scripts/color_tools.py ramp "oklch(0.55 0.18 265)"
python scripts/color_tools.py convert "oklch(0.7 0.35 145)"
```

If a score cannot be computed, name the token pair and the intended tier ("body text targeting Lc ≈ 90") and mark it a target. A fabricated Lc is worse than none.

## OKLCH generation

Build ramps in `oklch()` for uniform perceptual lightness across surfaces. Two constraints follow:

- **Gamut.** OKLCH easily produces out-of-sRGB values that clip unpredictably. Reduce chroma until the color fits, or run `color_tools.py ramp`, which does it automatically and reports where chroma was cut.
- **Fallback.** Where legacy support is in scope, wrap in `@supports (color: oklch(0 0 0))` with an sRGB fallback declared first.

Semantic naming over literal: `--surface-raised`, `--text-muted`, `--border-interactive-focus` — not `--blue-500` used directly in components.

## Preference queries

| Query | Requirement |
|---|---|
| `prefers-reduced-motion` | See motion.md — degradation, not removal |
| `prefers-contrast: more` | Strengthen borders, increase text weight, raise contrast |
| `prefers-reduced-transparency` | Replace glass, blur, translucent overlays with solid surfaces |
| `forced-colors: active` | Custom fills are overridden by the UA — structure must survive on semantic borders and outlines. Verify focus indicators remain visible |
| `color-scheme` | Declare it so form controls and scrollbars match the theme |

Forced-colors is where token-driven systems fail hardest. Use `border` rather than `box-shadow` for structural separation, and test that interactive boundaries remain perceivable.

## Typography

- Body text 16px minimum; line-height 1.5+ for body, 1.1–1.25 for display
- Measure 45–75 characters; enforce with `max-inline-size: 65ch`
- Fluid type via `clamp()`, but keep a rem-based term so 200% zoom still works
- Never justify text on the web; ragged right beats rivers

## Font-loading CLS

Web fonts are a top real-world source of layout shift.

**Never invent `size-adjust` or `ascent-override` values.** Precise font geometry cannot be recalled, and a wrong `size-adjust` produces *more* shift than no override. Generate them:

```bash
python scripts/font_metrics.py Inter-Regular.woff2 --fallback Arial
```

Or use `next/font`, Fontaine, or Capsize. Choose `font-display` deliberately — `optional` where shift matters more than fidelity, `swap` where the typeface is the brand. Preload only fonts used above the fold.
