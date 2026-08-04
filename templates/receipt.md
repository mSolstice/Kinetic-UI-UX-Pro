# Verification Receipt

Tiers are definitional, not a judgment call. Do not self-classify downward to skip the checklist.

- **Trivial — omit.** Only single-property CSS changes, static text edits, or leaf-node style tweaks.
- **Standard — required.** Any structural layout change, or any component with **even one** state transition, click handler, or conditional render.
- **Full — complete.** Async state plus motion, or custom color systems, or forms.

Report only what exists. An incomplete honest receipt is correct; a complete invented one is a failure.

---

### Kinetic UX Verification Receipt

- **Job & primary action:** [what this solves; the single primary action]
- **States implemented:** [which of the nine; note deliberate omissions and why]
- **Programmatic signalling:** [aria-busy timing, live region type + pre-mount, focus return target]
- **Motion degradation:** [reduced-motion fallback behavior, JS-side handling, forced-colors survival]
- **Color & contrast:** [token pairs; WCAG 2.x AA result; APCA Lc — mark COMPUTED or TARGET]
- **i18n & input:** [logical properties, expansion headroom, truncation justification if any, target sizes]
- **Performance:** [CLS mitigations, read/write batching, font fallback strategy]
- **Audit:** [`ui_audit.py` result — errors/warnings, or "not run"]
- **Assumptions:** [anything built on unconfirmed premises]

---

**Contrast reporting rule:** write `COMPUTED` only when `color_tools.py` produced the number. Otherwise write `TARGET Lc ≈ 90 (unverified)`. Never present an estimate as a measurement.
