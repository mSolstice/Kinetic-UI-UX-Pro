Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/motion.md

Scripts run:
- scripts/ast_audit.py templates/delete-project-confirmation-modal.tsx

Built a reusable destructive confirmation modal using native `<dialog>`. The flow keeps one primary destructive action, supports `Escape`, blocks double submission while deleting, and restores focus return to the opener after close.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Safely delete a saved project; primary action is Delete project.
- **States implemented:** default, focus-visible, active, loading, disabled, error, success.
- **Programmatic signalling:** `aria-busy`, pre-mounted alert region, native dialog focus handling.
- **Motion degradation:** reduced-motion path preserves state change without spatial travel.
