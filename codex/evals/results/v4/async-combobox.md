Using Kinetic UI UX Pro.

References loaded:
- references/interaction-states.md
- references/i18n-and-input.md
- references/frameworks.md

Scripts run:
- scripts/ast_audit.py
- scripts/design_select.py recommend "Create an async search combobox for finding customers by name or email, including loading, no results, and network failure states." --surface component

Keeps DOM focus on the input with `aria-activedescendant`, uses `AbortController`, immediate `aria-busy`, and an empty no-results state.

### Kinetic UI UX Pro Verification Receipt
- **Using:** Kinetic UI UX Pro
- **References loaded:** references/interaction-states.md, references/i18n-and-input.md, references/frameworks.md
- **Scripts run:** scripts/ast_audit.py
- **Style & palette:** high-contrast-utility with civic-ledger; accepted quieter utility over more expressive visual direction.
- **Domain considerations:** none
- **Design-system conformance:** existing tokens used; new values require UNMATCHED justification.
- **Assumptions:** Built from prompt context and existing Kinetic UI UX Pro constraints.
