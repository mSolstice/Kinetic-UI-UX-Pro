Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/i18n-and-input.md

Scripts run:
- scripts/ast_audit.py login-screen/index.html

Built the login screen with explicit assumptions: returning SaaS users, email/password auth, password reset, and no SSO provider specified. The form uses labels, `autocomplete` tokens, recoverable error copy, loading state, and one primary sign-in action.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Sign in and recover from errors; primary action is Sign in.
- **States implemented:** default, loading, disabled, error, success.
- **Programmatic signalling:** field errors are attached with `aria-describedby`.
- **Assumptions:** email/password login, no MFA or social sign-in unless requested.
