Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/i18n-and-input.md

Scripts run:
- scripts/ast_audit.py examples/settings-page/SettingsPage.tsx

Redesigned the settings page around one primary action: Save changes. Profile, notifications, billing, and danger zone are scan-first sections with clear labels, visible status, recoverable errors, and a success signal after save.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Adjust account settings quickly; primary action is Save changes.
- **States implemented:** default, loading, error, success, disabled.
- **Programmatic signalling:** status region and field-level descriptions.
- **Ethics:** danger actions are visually distinct and not adjacent to routine actions.
