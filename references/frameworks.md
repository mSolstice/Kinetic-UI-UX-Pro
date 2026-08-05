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

`scripts/ast_audit.py` now enforces Svelte transition reduced-motion handling, `on:click` on non-interactive elements, and `{#await}` without `{:catch}`.

## Vue

`<Transition>` and `<TransitionGroup>` for choreography. `useMediaQuery` composable for reduced motion. Prefer a `state` ref holding a union over multiple booleans.

`scripts/ast_audit.py` now enforces Vue transition reduced-motion handling, `@click` on non-interactive elements, `v-html`, and multiple boolean refs that should be one status union.

## Astro

Astro islands make static UI cheap and interactive UI explicit. Keep non-interactive surfaces server-rendered; hydrate only the smallest island that owns state. Every hydrated island still needs the full state matrix because partial hydration does not remove loading, empty, error, disabled, or focus-return obligations.

`scripts/ast_audit.py` now flags likely unnecessary `client:load` hydration and global selectors inside scoped `<style>` blocks that appear to need `is:global`.

## Universal checks regardless of stack

- Focus returns to the trigger on overlay close
- Live regions pre-exist in the DOM before content arrives
- `aria-busy` fires immediately; only the visual spinner is delayed
- Skeletons match final geometry
- Reads batched before writes in any layout animation
