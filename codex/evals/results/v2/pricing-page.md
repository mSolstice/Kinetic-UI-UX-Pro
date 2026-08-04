Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/color-and-type.md
- references/interaction-states.md

Scripts run:
- scripts/color_tools.py contrast "#1a1a1a" "#ffffff" --size body
- scripts/ast_audit.py examples/pricing-page/index.html

Built a pricing page with three plans, monthly/yearly switching, FAQ disclosures, clear upgrade and downgrade paths, and no dark patterns. The primary action is visually clear, downgrade is available without asymmetric friction, and contrast is checked.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Compare plans and choose or change one.
- **States implemented:** selected billing period, FAQ expanded/collapsed, disabled unavailable action.
- **Color & contrast:** contrast checked with `scripts/color_tools.py`.
- **Ethics:** no dark patterns, no fake urgency, no hidden downgrade.
