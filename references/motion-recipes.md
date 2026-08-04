# Motion Recipes

Use these only when motion carries state, causality, or spatial relationship. Every recipe includes an explicit reduced-motion path; never hide the signal entirely.

## 1. FLIP layout animation

**When to use it:** Reordering, expanding, or moving existing elements when users need to understand where the object went.

**Framer Motion**

```tsx
import { motion, useReducedMotion } from 'framer-motion';

function SortableCard({ id, children }: { id: string; children: React.ReactNode }) {
  const reduced = useReducedMotion();
  return (
    <motion.li
      layout={reduced ? false : 'position'}
      layoutId={reduced ? undefined : id}
      transition={reduced ? { duration: 0.09 } : { type: 'spring', stiffness: 420, damping: 34 }}
    >
      {children}
    </motion.li>
  );
}
```

**Vanilla CSS / JS**

```js
// Correct FLIP batching: all reads first, then all writes.
const before = new Map(items.map((el) => [el, el.getBoundingClientRect()]));

applyNewOrder(); // DOM mutation only; no measurement inside.

const after = new Map(items.map((el) => [el, el.getBoundingClientRect()]));

items.forEach((el) => {
  const first = before.get(el);
  const last = after.get(el);
  const dx = first.left - last.left;
  const dy = first.top - last.top;
  el.style.transform = `translate(${dx}px, ${dy}px)`;
  el.style.transition = 'transform var(--duration-local) var(--ease-out)';
});

requestAnimationFrame(() => {
  items.forEach((el) => {
    el.style.transform = 'translate(0, 0)';
  });
});
```

**Reduced-motion degradation:** Disable spatial movement and use `opacity var(--duration-local) var(--ease-linear)` or an instant reorder with a short status message.

**Performance note:** FLIP requires measurement. The safe rule is reads first, writes second. Never interleave `getBoundingClientRect()` with style writes inside a loop.

## 2. Shared-element transition

**When to use it:** Moving from a list/card view into detail when the same object persists across views.

**Framer Motion**

```tsx
const reduced = useReducedMotion();

<motion.article
  layoutId={reduced ? undefined : `project-${project.id}`}
  transition={reduced ? { duration: 0.09 } : { duration: 0.32, ease: [0.2, 0.8, 0.2, 1] }}
>
  {project.name}
</motion.article>
```

**Vanilla CSS / View Transitions**

```css
@view-transition {
  navigation: auto;
}

.project-card {
  view-transition-name: var(--project-transition-name);
}

::view-transition-old(project),
::view-transition-new(project) {
  animation-duration: var(--duration-view);
  animation-timing-function: var(--ease-out);
}
```

```js
document.startViewTransition(() => {
  renderProjectDetail(projectId);
});
```

**Reduced-motion degradation:** Remove shared `layoutId` / `view-transition-name`; crossfade root content under `--duration-view`.

**Performance note:** Shared-element names must be unique in one document. Duplicate `view-transition-name` values silently break the transition.

## 3. Staggered list entry

**When to use it:** A new set of related items appears and order matters, such as search results or notification history.

**Framer Motion**

```tsx
const reduced = useReducedMotion();

<motion.ul
  initial={false}
  animate="show"
  variants={{
    show: { transition: { staggerChildren: reduced ? 0 : 0.035 } },
  }}
>
  {items.map((item) => (
    <motion.li
      key={item.id}
      variants={{
        show: reduced
          ? { opacity: 1, transition: { duration: 0.09 } }
          : { opacity: 1, y: 0, transition: { duration: 0.18 } },
      }}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
    />
  ))}
</motion.ul>
```

**Vanilla CSS / View Transitions**

```css
.result {
  animation: result-enter var(--duration-local) var(--ease-out) both;
  animation-delay: calc(var(--item-index) * var(--duration-micro));
}

@keyframes result-enter {
  from { opacity: 0; transform: translateY(var(--motion-distance-sm)); }
  to { opacity: 1; transform: translateY(0); }
}
```

**Reduced-motion degradation:** Set `animation-delay: 0ms`; animate opacity only under `--duration-local`.

**Performance note:** Keep staggers short. Long cascades delay content and create interaction latency.

## 4. Gesture-driven drag

**When to use it:** Direct manipulation where the element follows the user's pointer, such as reordering, sliders, or dismissible cards.

**Framer Motion**

```tsx
const reduced = useReducedMotion();

<motion.div
  drag={reduced ? false : 'x'}
  dragConstraints={{ left: 0, right: 0 }}
  whileDrag={reduced ? undefined : { scale: 1.02 }}
  transition={reduced ? { duration: 0.09 } : { type: 'spring', stiffness: 500, damping: 36 }}
/>
```

**Vanilla CSS / JS**

```css
.drag-item {
  touch-action: pan-y;
  transform: translateX(var(--drag-x, 0));
  transition: transform var(--duration-micro) var(--ease-drag);
  will-change: transform;
}

.drag-item[data-dragging='true'] {
  transition-duration: var(--duration-instant);
}
```

```js
item.addEventListener('pointermove', (event) => {
  if (!item.hasPointerCapture(event.pointerId)) return;
  item.style.setProperty('--drag-x', `${event.clientX - startX}px`);
});
```

**Reduced-motion degradation:** Disable free drag travel; expose discrete controls such as Move left, Move right, Dismiss.

**Performance note:** Write only `transform` during drag. Add `will-change` while dragging and remove it on release.

## 5. Scroll-linked reveal

**When to use it:** Low-priority progressive disclosure as content enters view, never for essential information.

**Framer Motion**

```tsx
const reduced = useReducedMotion();

<motion.section
  initial={reduced ? { opacity: 1 } : { opacity: 0, y: 16 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, amount: 0.25 }}
  transition={{ duration: reduced ? 0.09 : 0.24 }}
/>
```

**Vanilla CSS / View Timelines**

```css
.reveal {
  animation: reveal-in var(--duration-local) var(--ease-out) both;
  animation-timeline: view();
  animation-range: entry 0% cover 30%;
}

@keyframes reveal-in {
  from { opacity: 0; transform: translateY(var(--motion-distance-md)); }
  to { opacity: 1; transform: translateY(0); }
}
```

**Reduced-motion degradation:** Render content visible immediately, or use a short opacity-only fade. Do not parallax or move against scroll.

**Performance note:** Scroll-linked effects can trigger vestibular discomfort and main-thread pressure. Avoid large fixed backgrounds and layout properties.

## 6. Skeleton-to-content swap

**When to use it:** Loading content with known final geometry, especially cards, rows, tables, and media slots.

**Framer Motion**

```tsx
const reduced = useReducedMotion();

<AnimatePresence mode="wait" initial={false}>
  {loading ? (
    <motion.div key="skeleton" exit={{ opacity: 0 }} transition={{ duration: reduced ? 0.09 : 0.16 }} />
  ) : (
    <motion.article key="content" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: reduced ? 0.09 : 0.18 }} />
  )}
</AnimatePresence>
```

**Vanilla CSS / View Transitions**

```css
.content-slot {
  min-block-size: var(--reserved-content-block-size);
  contain-intrinsic-size: auto var(--reserved-content-block-size);
}

.skeleton {
  animation: shimmer var(--duration-slow) var(--ease-linear) infinite;
}

@keyframes shimmer {
  to { background-position: var(--skeleton-shimmer-end); }
}
```

```js
document.startViewTransition(() => {
  slot.replaceChildren(renderLoadedContent());
});
```

**Reduced-motion degradation:** Stop shimmer; keep the skeleton static and crossfade to content under `--duration-local`.

**Performance note:** Skeleton geometry must match final content or reserve the same block size. A mismatched skeleton causes the CLS it was meant to prevent.
