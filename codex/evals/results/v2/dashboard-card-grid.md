Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/color-and-type.md
- references/i18n-and-input.md

Scripts run:
- scripts/token_gen.py templates/tokens.schema.json --verify
- scripts/ast_audit.py templates/product-metric-grid.tsx

Created a responsive dashboard card grid with container queries, stable skeleton geometry to protect CLS, empty metric states, and long labels that tolerate 40% text expansion without destructive truncation.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Scan product metrics quickly; primary action is inspect metric details.
- **States implemented:** loading, success, empty, error.
- **Layout:** container-responsive grid and reserved skeleton dimensions.
- **i18n:** `Intl.NumberFormat`, wrapping labels, logical properties.
