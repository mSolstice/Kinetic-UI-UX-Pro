Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/i18n-and-input.md

Scripts run:
- scripts/ast_audit.py checkout-form/index.html

Built a multi-step checkout with a reverse path from review back to payment and shipping. The form uses `novalidate`, real labels, `autocomplete` tokens, and an error summary on failed validation while preserving entered data between steps.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Complete checkout with confidence; primary action is Place order.
- **States implemented:** default, focus-visible, loading, disabled, error, success.
- **Programmatic signalling:** field `aria-describedby`, invalid state, and focused error summary.
- **Forms:** custom validation avoids competing native bubbles while keeping semantic attributes.
