# SaaS B2B

## Primary User Goal

Users are trying to configure, operate, monitor, approve, or report on work for a team. They are often accountable to others, switching between tasks, and need evidence that changes were saved and applied to the right workspace.

## Trust Requirements

At the moment of decision, show workspace/account, role, affected users, scope, save model, billing or permission impact, current state, dependency warnings, and reversibility.

## Error Costs

High-cost mistakes include changing the wrong workspace, inviting the wrong person, exposing data through permissions, breaking an integration, or deleting shared configuration. Some actions are reversible technically but costly socially.

## Density Expectations

Medium to high density. B2B products reward scannable operational layouts, tables, filters, and clear hierarchy. Avoid landing-page composition inside repeated work surfaces.

## Motion Budget

Near-zero to low. Motion should confirm state changes, reveal dependent settings, and preserve orientation. Avoid expressive animation libraries in data-dense tools.

## Style Fit

Suitable: `technical-dense`, `data-forward`, `swiss-grid`, `high-contrast-utility`, `glass-layered` only for light marketing-adjacent dashboards with solid fallbacks.

Conflicts: `brutalist`, `playful-rounded` for admin-critical surfaces, `soft-neumorphic` for settings, and `luxury-minimal` when it hides controls.

## Often Forgotten States

- Workspace switch
- Permission-denied action
- Unsaved changes
- Save conflict
- Integration disconnected
- Billing plan limit reached
- Audit log loading or unavailable
- Empty team and first invitation

## Domain-Specific Failure Modes

- User changes settings in a personal workspace thinking it is the team workspace
- Toggle autosaves without indicating whether it applies immediately
- Integration setup lacks test connection and failure recovery
- Seat limit appears only after invite submit
- Table filters hide all records without a cleared-by-filter state
- Export action omits permission and data-scope confirmation
