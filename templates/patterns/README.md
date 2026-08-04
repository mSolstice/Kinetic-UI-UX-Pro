# Pattern Scaffolds

Each scaffold ships the full interaction state matrix: default, hover, focus-visible, active, loading, disabled, error, success, and empty. CSS uses custom properties for design values so generated implementations can bind to the active design system.

| Pattern | When to use it | Failure mode it prevents | Accessibility contract |
| --- | --- | --- | --- |
| `combobox` | Search or choose from a medium list where typing narrows options. | Focus getting trapped inside a custom option list. | DOM focus stays on the input; highlighted option is exposed with `aria-activedescendant`; listbox never receives focus. |
| `modal` | Interruptive work that must be completed or dismissed before returning. | Hand-rolled dialogs that leak focus or strand the user after close. | Uses native `<dialog>`, labels the dialog, provides polite status/error regions, and returns focus to the opener. |
| `data-table` | Compare and scan structured records with sorting and filtering. | Treating empty data, filtered-empty data, overflow, and sort state as the same condition. | Sort controls are buttons, filter input is labelled, table has a caption, overflow region is keyboard focusable. |
| `multi-step-form` | Break a high-friction form into meaningful progressive steps. | Losing context or submitting impossible partial state. | Uses `noValidate`, labelled inputs, visible step position, polite errors, and state-layer submission blocking. |
| `toast-queue` | Confirm background results without stealing focus. | Alert spam, assertive announcements for non-urgent messages, and unlimited toast stacking. | Uses polite `role="status"` for normal messages, caps concurrent toasts, and keeps dismiss controls native. |
| `command-palette` | Fast keyboard access to global actions. | Moving focus into command options and losing Escape/return-focus behavior. | Uses native `<dialog>`, keeps focus on the search input, tracks the active command with `aria-activedescendant`, and returns focus to the opener. |
| `virtual-list` | Render long lists while preserving scroll performance. | Layout shift from rows appearing before scroll height is reserved. | Reserves total scroll height up front, exposes a focusable viewport, and keeps row geometry stable for CLS zero. |
