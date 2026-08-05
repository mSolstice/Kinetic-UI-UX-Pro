# Responsive Intent Spec

Use this before implementation when responsive behavior changes. This is not a visual QA checklist; it states what the design is supposed to become at each size so audits and reviews have something concrete to compare against.

Removal must be justified. "Hidden on mobile" is not enough. If content disappears at a breakpoint, name why it is secondary or name the alternate path where the same content remains available.

## Breakpoint: mobile

- query: `(max-width: 47.99rem)`
- navigation: Bottom tab bar using `.mobile-tabs`; secondary destinations move into `.more-menu`.
- primary content: Main content becomes one column; summary precedes detail; long tables become card rows.
- persist: `.primary-summary`, `.critical-status`, `.primary-action`, `.filters-summary`
- remove: `.desktop-sidebar` because secondary navigation is available through `.more-menu`.
- tap changes: Hover-only row actions become visible icon buttons; tooltips become disclosure text.
- primary action: Full-width sticky action at the block end using `.primary-action`.

## Breakpoint: tablet

- query: `(min-width: 48rem) and (max-width: 63.99rem)`
- navigation: Collapsible sidebar using `.tablet-nav`; top-level destinations remain visible.
- primary content: Two-column composition when the secondary panel supports the primary task; otherwise one wide content column.
- persist: `.primary-summary`, `.critical-status`, `.filters`, `.primary-action`
- remove: `.dense-metadata` because it is secondary and remains available in `.details-panel`.
- tap changes: Hover affordances keep an always-visible tap target.
- primary action: Inline action in the header plus repeated action after long forms.

## Breakpoint: desktop

- query: `(min-width: 64rem)`
- navigation: Persistent sidebar using `.desktop-sidebar`.
- primary content: Grid, split-pane, or table layout may be used when comparison speed matters.
- persist: `.desktop-sidebar`, `.filters`, `.primary-summary`, `.critical-status`, `.primary-action`
- remove: None.
- tap changes: Hover may enhance affordances only when a focus-visible and tap equivalent exists.
- primary action: Header-aligned action near the page title using `.primary-action`.
