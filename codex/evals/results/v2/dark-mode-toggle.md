Using Kinetic UI UX Pro.

References loaded:
- references/color-and-type.md
- references/i18n-and-input.md
- references/frameworks.md

Scripts run:
- scripts/token_gen.py templates/tokens.schema.json --verify
- scripts/color_tools.py contrast "oklch(0.96 0.005 265)" "oklch(0.16 0.012 265)"
- scripts/ast_audit.py templates/theme-toggle.tsx

Added a dark-mode toggle strategy with `color-scheme`, explicit light/dark tokens, system preference fallback, forced-colors support, and a before first paint bootstrap so the app avoids theme flash.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Change theme preference without flash; primary action is toggle theme.
- **Color & contrast:** WCAG checked with generated tokens and `scripts/color_tools.py`.
- **Programmatic signalling:** native button state reflects the selected theme.
- **Performance:** theme resolves before first paint.
