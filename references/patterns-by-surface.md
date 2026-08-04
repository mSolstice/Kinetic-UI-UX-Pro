# Patterns By Surface

Surface type determines density, hierarchy, and motion. Do not apply a landing-page treatment to an operational tool.

**Animation rule:** do not use expressive animation libraries in data-dense product interfaces. Reserve them for marketing surfaces, onboarding, and landing pages. Product work surfaces need fast, quiet state signalling, not choreographed delight.

## Dashboard

**Information-architecture failure modes**
- Treating every metric as equally important
- Grouping by data source instead of user decision
- Hiding freshness, scope, or filter context
- Mixing alerts, trends, and vanity metrics in one visual weight
- Making cards navigate unpredictably: some drill down, some open modals, some do nothing

**Usually forgotten states**
- Stale data and last-updated timestamp
- Partial data when one service fails
- Empty account with no metrics yet
- Permission-denied metric panels
- Overflow from long labels, large numbers, many segments
- Cleared state when filters remove all cards

**Motion budget**
Near-zero. Use micro feedback only: focus, hover, loading shimmer, and small opacity changes under `--duration-micro`. Avoid expressive libraries, parallax, large-area transitions, and decorative count-up effects.

**Density and hierarchy**
High density, strict hierarchy. Put decision-critical metrics first, group by user question, and show comparison context directly beside the number. Use compact tables and charts with visible filters; avoid oversized hero cards unless one metric truly drives the workflow.

## Settings

**Information-architecture failure modes**
- Organizing by internal systems instead of user mental model
- Mixing personal, workspace, billing, and security settings without boundaries
- Hiding destructive or irreversible changes beside routine toggles
- Saving silently when the risk requires confirmation, or requiring Save for instant-safe toggles
- Labels that describe implementation rather than outcome

**Usually forgotten states**
- Unsaved changes
- Saved confirmation
- Permission-denied controls
- Loading current configuration
- Stale setting changed elsewhere
- Validation error and dependency conflicts
- Empty integration/account connection

**Motion budget**
Very low. Use instant or micro transitions for toggles, validation, and section disclosure. No expressive animation libraries. Any motion must clarify persistence: saving, saved, failed, or reverted.

**Density and hierarchy**
Medium density with clear grouping. Each setting needs label, consequence, current value, and save model. Put dangerous actions in a separate destructive zone. Prefer tabs or side navigation when categories are stable; use accordions only when users rarely need cross-section comparison.

## Feed

**Information-architecture failure modes**
- Confusing chronological, ranked, and grouped ordering
- Losing the user's position after refresh or detail navigation
- Mixing content types without visible type labels
- Infinite scroll with no recovery, no landmarks, and no pagination fallback
- Treating ads, recommendations, and user-requested content with identical hierarchy

**Usually forgotten states**
- First-run empty feed
- End of feed
- New items available while user is mid-scroll
- Offline cached feed
- Stale posts or deleted items
- Muted/blocked/permission-denied content
- Overflow from long text, media failures, and missing avatars

**Motion budget**
Low to medium. Use small entry transitions and position-preserving updates only when they protect orientation. Avoid large scroll-linked effects in product feeds. Marketing feeds can use more motion, but content readability wins.

**Density and hierarchy**
Variable density. Put source, time, type, and primary action in predictable positions. Cards should support scanning without becoming isolated posters. Preserve reading position, expose filters/sort, and avoid surprise inserts above the viewport.

## Wizard

**Information-architecture failure modes**
- Steps based on arbitrary count rather than meaning
- No reverse path, or back discards entered data
- Hidden dependencies between earlier and later answers
- Progress indicator that lies about branching or optional steps
- Asking for permissions or complex data before explaining value

**Usually forgotten states**
- Partial completion and resumable draft
- Step-level validation error
- Cross-step dependency error
- Slow save between steps
- Offline draft queue
- Permission-denied step
- Empty optional step
- Stale invitation, quote, or setup session

**Motion budget**
Medium for onboarding and marketing-adjacent setup; low for operational wizards. Use short directional motion only to reinforce step progression. Reduced motion must become opacity or instant step swap. Avoid expressive libraries except in onboarding or landing-page contexts.

**Density and hierarchy**
Low to medium density. One primary action per step. Show progress, current step purpose, reversible navigation, and what will happen next. Keep review steps dense enough for comparison, but keep input steps focused.

## Editor

**Information-architecture failure modes**
- Toolbars organized by implementation rather than editing task
- Properties panels that hide the selected object's current state
- Destructive actions too close to frequent actions
- No distinction between selection, focus, hover, and editing mode
- Autosave without visible save, sync, conflict, and version state

**Usually forgotten states**
- No selection
- Multi-selection with mixed values
- Invalid selection for a tool
- Saving, saved, offline, conflict, and stale version
- Locked object or permission-denied edit
- Overflow from long document names and dense layer lists
- Empty canvas or empty document

**Motion budget**
Low for the editing surface; medium only for previewing the thing being authored. Tool feedback should be immediate and mostly non-spatial. Do not use expressive animation libraries for the editor chrome. If the editor creates animations, separate playback controls from interface motion.

**Density and hierarchy**
High density with mode clarity. Keep the canvas/work area dominant, tools predictable, and inspectors close to selection. Use icons where conventional, labels where consequences matter, and persistent status for save/sync/conflict. Avoid decorative cards inside the work surface.
