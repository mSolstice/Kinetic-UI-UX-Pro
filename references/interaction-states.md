# Interaction States, Focus & Overlays

## The state matrix

Every interactive component ships every applicable state. This is the single most common defect in generated UI — a button with hover and nothing else.

| State | Requirement |
|---|---|
| Default | Baseline resting appearance |
| Hover | Gated behind `@media (hover: hover)`; never the sole affordance |
| Focus-visible | `:focus-visible` indicator that survives forced-colors mode |
| Active | Distinct pressed feedback, ≤100ms |
| Loading | Blocks re-entry; announced programmatically |
| Disabled | Prefer `aria-disabled` where the control must stay focusable and explain why |
| Error | Recoverable, described, announced |
| Success | Confirmed, then cleared — not permanent chrome |
| Empty | Zero-data view with an action, never a blank container |

## Native before ARIA

Use the platform element first. `<dialog>` provides focus trapping, `Escape` handling, and background inerting for free; re-implementing those with `div`s is where most modal accessibility defects originate.

| Need | Use | Not |
|---|---|---|
| Modal | `<dialog>` | `div` + `role="dialog"` |
| Button | `<button>` | `div` + `onClick` |
| Expand/collapse | `<details>` / `<summary>` | custom state + ARIA |
| Tooltip/menu | Popover API | absolutely-positioned div |
| Progress | `<progress>` | styled div |

ARIA supplements the platform; it never substitutes for it. The first rule of ARIA remains: don't use ARIA if a native element will do.

## Programmatic signalling

**Loading.** `aria-busy="true"` on the container the moment the request starts — the programmatic signal is never delayed. The ~200ms delay before showing a spinner and the ~400ms minimum display duration apply to the *visual only*.

**Errors.** The live region must already exist in the DOM, empty, before the message arrives. Injecting region and content together commonly announces nothing. Use `role="alert"` or `aria-live="polite"` for form errors; reserve `assertive` for genuine interruptions.

Choose **either** a live-region announcement **or** a focus shift to an error summary. Both together double-announce.

**Focus return.** Every overlay, drawer, and menu returns focus to the element that opened it. Losing focus to `<body>` strands keyboard and screen reader users at the top of the document.

## Overlay nesting

Focus traps leak because the inner overlay was portaled to `document.body`, landing outside the parent's subtree — not because of nesting itself.

1. Render nested popovers, menus, and dropdowns **inside** the dialog's DOM subtree, or promote them to the top layer via the Popover API or a nested `<dialog>`, which the browser sequences correctly.
2. **Comboboxes and autocompletes: focus never enters the listbox.** Keep DOM focus on the input; track the highlighted option with `aria-activedescendant`. This removes the "trapped inside the dropdown" failure at its source rather than managing it.
3. `aria-haspopup` announces that a popup exists. It manages no focus and traps nothing — never treat it as the mechanism.
4. `Escape` dismisses only the innermost layer; it must not close the parent dialog.

## State machine integrity

Model state as a discriminated union, not parallel booleans:

```ts
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Item[] }
  | { status: 'error'; message: string; retry: () => void };
```

`loading && error && success` must be unrepresentable. Booleans permit it; unions don't.

- Block double-submission at the state layer, not with a visual disable alone.
- Animations interruptible from current position, never queued — a user who clicks twice must not wait out the first transition.
- Cancel in-flight requests on unmount and on supersede; a late response must not overwrite newer state.

## Skeletons

A skeleton whose height, width, aspect-ratio, or grid span differs from resolved content *causes* the layout shift it was meant to prevent. Match dimensions exactly, or reserve space with `min-height` and render nothing.

Prefer a skeleton over a centered spinner for content regions — it communicates structure and reserves space simultaneously.
