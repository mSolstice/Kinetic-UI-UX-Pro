# Anti-Slop Visual Defaults

Generated UI reads as generic when visible choices look like defaults that were
never decided. The fix is not more decoration; it is a narrower set of real
decisions tied to the surface, task, and design-system tokens.

## Generic Defaults And Alternatives

### Default Purple-Blue Gradient

Why it reads generic: it is the common unchosen AI/product-template backdrop,
especially when it carries no brand, state, or content meaning.

Do instead: generate a palette from `templates/palettes/`, use one restrained
accent, and let surfaces be tokenized solids. Use gradients only when the
industry, style constraint, and contrast verification justify them.

### Three-Card Feature Rows With Centered Icons

Why it reads generic: the layout usually mirrors boilerplate marketing
sections, gives all benefits equal weight, and avoids prioritizing the real
decision.

Do instead: rank features by user decision, vary width or position by priority,
and replace centered icon sameness with concrete UI states, screenshots, data,
or task-specific proof.

### Identical Border Radius Everywhere

Why it reads generic: one radius applied to buttons, cards, inputs, modals, and
media ignores scale and interaction. It feels like a global default rather than
a shape system.

Do instead: map radius to component scale and risk: smaller radii for dense
controls, medium for repeated items, larger only where the style constraint
allows softer surfaces.

### Uniform Drop Shadows At Every Elevation

Why it reads generic: the same shadow on every card claims elevation without
hierarchy. Nothing is actually closer, more important, or interactive.

Do instead: define elevation roles. Use border for base separation, shadow only
for overlays or lifted affordances, and make elevation change with state or
layer.

### Emoji As Iconography

Why it reads generic: emoji are platform-rendered, inconsistent, culturally
loaded, and often chosen because no icon decision was made.

Do instead: use the product icon system, text labels, or lucide/Radix-compatible
icons where appropriate. Reserve emoji for user-generated content or explicit
brand tone.

### Same Sans-Serif At Three Weights And Nothing Else

Why it reads generic: weight-only hierarchy often means the type system has no
contrast in size, rhythm, role, or voice.

Do instead: define a type scale with real contrast between levels, use tabular
numbers for metrics, and introduce a second family only when the style
constraint permits it and the role is clear.

### Centered Hero Text Over A Full-Bleed Gradient

Why it reads generic: it solves composition with a template rather than with
the product, place, object, or actual offer.

Do instead: make the first viewport show the real subject, state, or product
artifact. Use hierarchy, measured type, and a verified text surface rather than
gradient atmosphere.

### Equal Visual Weight Across Every Card In A Grid

Why it reads generic: equal cards imply equal importance. Most product grids
need ranking, grouping, alerts, or a primary decision.

Do instead: give the primary item more space, stronger type, earlier position,
or persistent context. Use lower weight for secondary cards and explicit empty,
error, stale, and permission states.

### Decorative Scroll Motion With No Informational Purpose

Why it reads generic: motion becomes a stock flourish instead of a state,
spatial, or causal signal.

Do instead: use motion only to preserve orientation, confirm state change, or
show relationship. If removing the motion loses no information, remove it or
reduce it to a tokenized micro transition.

## What Reads As Intentional

### Deliberate Asymmetry

Intentional layouts use asymmetry to express priority: a larger proof panel, a
narrow action rail, a dominant table, or an offset detail view. The asymmetry
must track the user's decision, not decoration.

### Type Scale With Genuine Contrast

Levels should differ by role, size, rhythm, and density, not only weight. A
dashboard metric, form label, body paragraph, and section heading should each
earn their type treatment.

### One Accent Used Sparingly

An accent works when it is reserved for action, status, selection, or brand
moments. If every icon, underline, chip, and card border uses the accent, the
system has no signal left.

### Hierarchy Through Space Rather Than Boxes

Use proximity, alignment, whitespace, and grouping before adding boxes. A box
should mean a repeated item, tool boundary, modal, or state container, not
"this needed to look designed."
