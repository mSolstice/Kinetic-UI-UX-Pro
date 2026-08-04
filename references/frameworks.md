# Framework Adapters

The doctrine is stack-agnostic. Author with semantic HTML and platform CSS first, then map. Only the animation and state syntax changes.

## React / Next.js

**State** — discriminated unions, never parallel booleans:

```tsx
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Item[] }
  | { status: 'error'; message: string };
```

**Motion** — Framer Motion `layoutId` for shared elements; `useReducedMotion()` for the JS path (CSS queries don't reach it).

**Async safety** — `AbortController` on unmount and supersede; a late response must not overwrite newer state. `useId()` for label/describedby wiring. Never `useEffect` for theme resolution.

**Server components** — keep interactive state in client components; don't force a whole tree client-side for one handler. Verify view transitions degrade across the boundary.

**No `<form>` in Claude artifacts** — use `onClick` handlers. No `localStorage`/`sessionStorage` — in-memory state only.

## Vanilla / Tailwind v4

**Tokens** — `@theme` for design tokens; CSS custom properties for runtime-varying values. Tailwind v4 reads native `@media` and container queries directly.

**Motion** — `@starting-style` for entry animation, View Transitions API for cross-view choreography, `transition-behavior: allow-discrete` for `display` transitions.

**Utilities that need care:** `truncate` is destructive truncation — see i18n-and-input.md. `ml-*`/`mr-*` are physical; prefer `ms-*`/`me-*`. Arbitrary values bypass token discipline — use sparingly.

**Focus** — `focus-visible:` variant, not `focus:`, so mouse users don't get rings.

## Svelte

Transitions are built in (`transition:fade`), but they do not read `prefers-reduced-motion` automatically — gate them. Stores hold the state machine; keep the union shape. `{#await}` blocks map cleanly to the loading/success/error trio.

## Vue

`<Transition>` and `<TransitionGroup>` for choreography. `useMediaQuery` composable for reduced motion. Prefer a `state` ref holding a union over multiple booleans.

## Universal checks regardless of stack

- Focus returns to the trigger on overlay close
- Live regions pre-exist in the DOM before content arrives
- `aria-busy` fires immediately; only the visual spinner is delayed
- Skeletons match final geometry
- Reads batched before writes in any layout animation
