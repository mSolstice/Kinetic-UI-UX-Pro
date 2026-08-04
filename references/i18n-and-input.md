# Layout, Input, i18n & Forms

## Logical properties only

`margin-inline-start`, `padding-block`, `inset-inline-start`, `border-inline-end` — never `left`/`right`. This makes RTL work without a second stylesheet.

Also logical: `text-align: start/end`, `float: inline-start`. For icons that indicate direction (chevrons, arrows), flip with `[dir="rtl"] & { scale: -1 1; }` — the glyph's meaning is directional even when the property isn't.

## Text expansion

Layouts must absorb ~40% string growth from translation without clipping or breaking. German, Finnish, and Russian routinely exceed English by 30–40%; CJK runs shorter but taller.

Asymmetric grids and tight compositions fail here first — pressure-test them specifically with long strings, not lorem ipsum.

## No destructive truncation

Clipping expanded text with `text-overflow: ellipsis` or `overflow: hidden` satisfies the layout visually while deleting the information. That is an internationalization failure, not a fix.

Primary content, labels, buttons, nav items, and error messages must wrap, scale, or grow their container.

Truncation is permitted **only when the full text remains reachable**: a `line-clamp` preview whose complete text is one interaction away, or a value paired with a tooltip or expander.

This constrains *text*, not the property — `overflow: hidden` remains correct for scroll containers, radius clipping, and decorative layers.

## Fluid range

- Verify down to 320px without horizontal scroll
- Support 200% text zoom without loss of function
- Container queries over viewport queries for component-level responsiveness
- `min()`/`max()`/`clamp()` over breakpoint cascades where the layout is genuinely fluid

## Pointer and touch

- Hover is unavailable on touch: every hover affordance needs a non-hover equivalent, and hover styling is gated behind `@media (hover: hover)`
- Interactive targets ≥44×44px, with ≥8px spacing between adjacent targets
- `env(safe-area-inset-*)` on fixed and bottom-anchored elements
- `touch-action` declared where custom gestures exist, so scrolling isn't hijacked
- No hover-only disclosure of essential content

## Formatting

Use `Intl` for numbers, currency, and dates — never hand-rolled formatting. Relative time ("2 hours ago") needs an absolute value available via `<time datetime="...">` or a title attribute.

Names, addresses, and phone numbers do not have universal structure. Prefer a single flexible field over rigid first/middle/last where the data permits.

## Forms

- Every input has a programmatically associated `<label>`. Placeholders are not labels — they vanish on focus, fail contrast, and break screen readers
- Attach help and validation text with `aria-describedby`; mark invalid fields `aria-invalid`
- Include `autocomplete` tokens — they are an accessibility requirement, not a convenience
- Validate on blur and on submit, never on every keystroke
- On failed submit, move focus to the error summary or first invalid field

**Never run native validation bubbles alongside custom ARIA errors.** The browser tooltip and the live region announce competing messages and fight for focus. When custom validation takes over, add `novalidate` to the form but **keep** `required`, `type`, and `pattern` in the markup — they carry semantics and provide the no-JS fallback.

## Progressive enhancement

Where the stack permits, forms submit without JavaScript and are enhanced by it. A form inert until hydration is broken during the window that matters most.

**Theme flash.** Resolve the theme before first paint — a blocking inline script or a server-set attribute — never in a post-hydration effect. Dark-mode FOUC is a visible correctness bug.

**View transitions across boundaries** must degrade cleanly rather than half-running when server and client disagree.
