Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/i18n-and-input.md

Scripts run:
- scripts/ast_audit.py examples/saas-onboarding-flow/index.html

Created an onboarding flow that follows the rule to show value before asking for setup: invite teammates, connect a data source, or take a skippable path and resume later. Permission requests are contextual, failures are retryable, and the empty state explains what appears after setup.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Reach first useful workspace state; primary action is Continue setup.
- **States implemented:** empty state, loading, error, partial, success.
- **Programmatic signalling:** progress and errors are announced without trapping focus.
- **Control:** skip and reverse paths are available.
