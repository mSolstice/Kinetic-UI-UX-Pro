Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/motion.md

Scripts run:
- scripts/ast_audit.py templates/component-scaffold.tsx

Framed the vague request first: Job is to make the primary button feel clearer, more responsive, and trustworthy without changing its purpose. Improved hover, focus-visible, active, loading, and disabled states while keeping motion purposeful and reduced-motion safe.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Make the button’s action legible and tactile.
- **States implemented:** default, hover, focus-visible, active, loading, disabled.
- **Motion degradation:** press feedback uses transform/opacity and degrades cleanly.
- **Assumptions:** treated as the primary scaffold button because no app target was provided.
