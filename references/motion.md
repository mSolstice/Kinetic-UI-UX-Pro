# Motion, Degradation & Vestibular Safety

## Motion earns its place

Animate to communicate a state change, a spatial relationship, or causality. Decorative motion on every element is fatiguing and is itself an accessibility problem. "Never let anything appear without animating" is not the goal — purposeful motion is.

**Duration guidance:** micro-feedback 100–150ms · local transitions 200–300ms · full-view transitions 300–500ms · anything beyond ~500ms needs a reason. Ease-out for entrances, ease-in for exits, spring for direct manipulation.

## Degradation path, not a blank gate

Wrapping motion in `prefers-reduced-motion: no-preference` and providing nothing else strips the state-change signal from the users who most need clarity. Specify the reduced path:

- Replace translation, scale, and spatial movement with opacity crossfade or an instant swap
- Keep reduced-path durations under ~100ms
- Preserve the *information* the motion carried; remove only the spatial travel

```css
.panel { transition: transform 280ms cubic-bezier(.2,.8,.2,1), opacity 280ms; }

@media (prefers-reduced-motion: reduce) {
  .panel { transition: opacity 90ms linear; transform: none; }
}
```

## The JavaScript path

A CSS media query does not reach Framer Motion or JS-driven timelines.

```tsx
const reduced = useReducedMotion();
<motion.div
  layoutId={reduced ? undefined : 'card'}
  transition={reduced ? { duration: 0.09 } : { type: 'spring', stiffness: 300, damping: 30 }}
/>
```

Vanilla equivalent: `matchMedia('(prefers-reduced-motion: reduce)')`, and listen for changes — the preference can flip mid-session.

## High-risk patterns

Parallax, scroll-driven position animation, auto-advancing carousels, and large-area zoom are primary vestibular triggers.

- Gate them behind reduced-motion with a static fallback
- Carousels need a visible pause control and must never auto-advance content being read
- Avoid motion covering large screen areas or moving against scroll direction

## Rendering safety

Animate `transform`, `opacity`, `filter`. Never `height`, `width`, `top`, `margin`.

For height changes: animate a wrapper's `transform: scaleY()` with counter-scaled content, use `grid-template-rows: 0fr → 1fr`, or accept a discrete change. `interpolate-size: allow-keywords` where support permits.

`will-change` applies only during active interaction and is removed after. A permanent `will-change` is a memory leak, not an optimization.

## Layout animation and measurement

FLIP, Framer Motion `layoutId`, and shared-element transitions legitimately require `getBoundingClientRect()`. Do not ban measurement — batch it.

```js
// correct: all reads, then all writes
const rects = els.map(el => el.getBoundingClientRect());
els.forEach((el, i) => { el.style.transform = compute(rects[i]); });
```

Interleaving read → write → read within a frame causes thrashing. Measurement alone does not.

## View Transitions

```css
@view-transition { navigation: auto; }
::view-transition-old(root) { animation-duration: 200ms; }

@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(root),
  ::view-transition-new(root) { animation: none; }
}
```

Assign `view-transition-name` only to elements that persist across the transition. Duplicate names in one document break the transition silently.
