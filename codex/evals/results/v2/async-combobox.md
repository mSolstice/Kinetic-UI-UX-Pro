Using Kinetic UI UX Pro.

References loaded:
- references/interaction-states.md
- references/i18n-and-input.md
- references/frameworks.md

Scripts run:
- scripts/ast_audit.py templates/customer-search-combobox.tsx

Created an async customer combobox with `AbortController`, `aria-busy`, retryable error handling, and an empty no-results state. DOM focus stays on the input while the highlighted option is exposed through `aria-activedescendant`.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Find and select a customer by name or email.
- **States implemented:** default, hover, focus-visible, loading, error, success, empty.
- **Programmatic signalling:** pre-mounted polite status/error regions and immediate `aria-busy`.
- **i18n & input:** labels, wrapping option text, keyboard navigation, no placeholder-only labeling.
