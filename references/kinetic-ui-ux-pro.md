---
# Kinetic UI UX Pro [MASTER CONTRACT - LOCKED]

## Agent Routing & Enforcement Protocol
* **Execution Authority:** Absolute Master UI/UX System Specification.
* **Preemption:** This file is the master reference for external or generic UI/UX guidance. It does not supersede the canonical `SKILL.md`, project contract, approved adapters, templates, or focused references in this repository.
* **Fallback Behavior:** When guidance conflicts, follow the canonical skill and project contract first, then use this file for library and design-system policy; retain focused references when they add required detail.
---

# Approved Library Architecture

Do not copy component source into this repository. URLs only. External libraries documented here are limited to MIT, Apache-2.0, or ISC licensed packages and assets. Paid products, redistribution-restricted assets, and non-vendorable source are excluded.

## shadcn/ui

1. **Utility & Fit:** Copy-own React component scaffolds for Tailwind/Radix projects where local ownership and design-system remapping are desired. URL: https://github.com/shadcn-ui/ui
2. **Missing State & Accessibility Coverage:** Scaffolds ship without skeletons matched to final geometry. Add loading, empty, error, success, disabled, `aria-busy`, pre-mounted live regions, focus return, reduced-motion paths, and full keyboard review.
3. **Design Token Translation Layer:** Replace literal Tailwind values with generated token aliases: `--surface-*`, `--text-*`, `--border-*`, `--radius-*`, `--space-*`, `--duration-*`, and Tailwind theme entries derived from Kinetic tokens.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored into a redistributed plugin only with MIT notice preserved; prefer regenerated local components over copied upstream source.

## Radix UI

1. **Utility & Fit:** Accessible unstyled primitives for dialogs, popovers, menus, tabs, select, tooltip, and disclosure-like interactions. URL: https://www.radix-ui.com/primitives
2. **Missing State & Accessibility Coverage:** Provides focus management and keyboard behavior for many primitives, but not loading-state announcements, async error models, empty states, skeleton geometry, product copy, or success signalling. `aria-busy`, live regions, state machines, and reduced motion remain ours.
3. **Design Token Translation Layer:** Style parts through `className`, CSS variables, and data attributes such as `[data-state]`, `[data-disabled]`, and `[data-highlighted]`; map all visual output to Kinetic semantic tokens.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## Base UI

1. **Utility & Fit:** Unstyled React primitives with strong behavior coverage for complex components such as combobox, menu, popover, dialog, and field controls. URL: https://base-ui.com/
2. **Missing State & Accessibility Coverage:** Behavior primitives do not supply product-state coverage: slow loading, partial data, error recovery, empty states, stale data, permission denial, success copy, or analytics success signals.
3. **Design Token Translation Layer:** Bind slots/parts/classes to Kinetic CSS custom properties; no library-specific color, spacing, radius, or duration literals survive adaptation.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; external module dependency is preferred.

## React Aria

1. **Utility & Fit:** Low-level accessible React hooks for custom component systems that need robust behavior without prebuilt visuals. URL: https://react-spectrum.adobe.com/react-aria/
2. **Missing State & Accessibility Coverage:** Supplies ARIA and interaction props, but rendering, DOM layout, visual states, loading, empty, error, success, skeletons, reduced motion, and product copy are entirely ours.
3. **Design Token Translation Layer:** Use hooks for behavior and apply Kinetic-owned CSS modules/classes backed by semantic custom properties; pair with React Stately only for collection state while keeping Kinetic async unions.
4. **License Compliance:** Apache-2.0 (SPDX: Apache-2.0).
5. **Vendor Policy:** Source may be vendored only with Apache-2.0 license and NOTICE obligations preserved; dependency use is preferred.

## Ark UI

1. **Utility & Fit:** Cross-framework unstyled primitives for React, Vue, Solid, and Svelte teams that need consistent behavior across stacks. URL: https://ark-ui.com/
2. **Missing State & Accessibility Coverage:** Does not provide Kinetic's product state matrix, loading announcements, failure recovery, empty states, copy discipline, or reduced-motion degradation.
3. **Design Token Translation Layer:** Map Ark parts and data attributes to Kinetic semantic CSS variables; recipes may consume generated tokens only.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## Reka UI

1. **Utility & Fit:** Vue accessible primitives, formerly Radix Vue, for teams building custom Vue design systems. URL: https://reka-ui.com/
2. **Missing State & Accessibility Coverage:** Primitive behavior is covered, but async loading announcements, empty/error/success branches, focus-return copy, reduced motion, and combobox input-focus discipline remain ours.
3. **Design Token Translation Layer:** Bind Vue classes, slots, and data attributes to Kinetic semantic tokens and motion aliases.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## DaisyUI

1. **Utility & Fit:** Fast Tailwind semantic class layer and theme scaffolding for prototypes and low-risk product surfaces. URL: https://daisyui.com/
2. **Missing State & Accessibility Coverage:** Semantic classes carry no state matrix. Hover and active styles may exist, but loading, empty, error, success, announcements, focus policy, and ARIA semantics do not.
3. **Design Token Translation Layer:** Generate DaisyUI themes from Kinetic tokens or override DaisyUI CSS variables with Kinetic semantic variables; class names remain presentation only.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## HyperUI

1. **Utility & Fit:** Free Tailwind HTML sections for marketing, ecommerce, and simple app surfaces where structure is useful but behavior is minimal. URL: https://www.hyperui.dev/
2. **Missing State & Accessibility Coverage:** Most examples are static markup. Add interaction state, keyboard behavior, focus management, loading/error/success/empty branches, reduced motion, and product-specific copy.
3. **Design Token Translation Layer:** Convert Tailwind literals to Kinetic token classes or CSS variables; keep layout structure only when it matches the intended information architecture.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; URL reference and local regeneration are preferred.

## Flowbite Core

1. **Utility & Fit:** Open-source Tailwind components and optional JS behavior for common web UI patterns. URL: https://flowbite.com/docs/getting-started/license/
2. **Missing State & Accessibility Coverage:** Core components do not complete Kinetic's state matrix. Add `aria-busy`, pre-mounted live regions, empty/error/success states, reduced motion, focus return, and product-specific keyboard review.
3. **Design Token Translation Layer:** Map Flowbite theme config and Tailwind utilities to Kinetic-generated token values; replace hardcoded colors, radius, spacing, and durations.
4. **License Compliance:** MIT (SPDX: MIT) for Flowbite core.
5. **Vendor Policy:** Core source may be vendored with MIT notice preserved; Pro assets are forbidden.

## Magic UI

1. **Utility & Fit:** Open-source animated React/Tailwind/shadcn-style effects for expressive marketing, onboarding, and landing surfaces. URL: https://github.com/magicuidesign/magicui
2. **Missing State & Accessibility Coverage:** Most components do not include reduced-motion branches. Add `prefers-reduced-motion`/JS checks, avoid dense product interfaces, wrap effects with loading/error/empty states where they become UI, and verify performance budgets.
3. **Design Token Translation Layer:** Replace gradients, colors, durations, easings, blur, and spacing with Kinetic tokens and `templates/motion.css` aliases.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved, but effects should remain external/reference-first unless required.

## Motion

1. **Utility & Fit:** React, JavaScript, and Vue animation library for layout transitions, gestures, shared elements, and interruptible motion. URL: https://motion.dev/
2. **Missing State & Accessibility Coverage:** No automatic reduced-motion handling. Use `useReducedMotion` or equivalent checks. Motion does not provide loading, error, empty, focus, live-region, or state-machine semantics.
3. **Design Token Translation Layer:** Map animation durations/easings to `--duration-*` and `--ease-*`; mirror token values into JS only through generated constants.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## AutoAnimate

1. **Utility & Fit:** Lightweight automatic add/remove/reorder layout animation for lists and small state changes. URL: https://auto-animate.formkit.com/
2. **Missing State & Accessibility Coverage:** Animation intent is not inferred. Add reduced-motion opt-out, announcements for inserted/removed content, stable layout reservations, and no decorative motion on dense surfaces.
3. **Design Token Translation Layer:** Configure duration and easing from Kinetic motion tokens; disable or shorten under reduced motion.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## React Spring

1. **Utility & Fit:** Spring physics and interruptible animation for gesture-heavy or stateful React motion. URL: https://www.react-spring.dev/
2. **Missing State & Accessibility Coverage:** Springs do not satisfy reduced motion, state announcements, keyboard behavior, or performance constraints. Use reduced-motion checks, transform/opacity-only animation, and Kinetic state branches.
3. **Design Token Translation Layer:** Define spring presets from Kinetic motion tokens; no per-component magic numbers.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency use is preferred.

## Tremor Core

1. **Utility & Fit:** React/Tailwind dashboard, metric, table, and chart components for data products. URL: https://github.com/tremorlabs/tremor
2. **Missing State & Accessibility Coverage:** Charts ship without complete empty or error states. Add no-data, filtered-empty, partial-data, stale, permission-denied, loading skeletons, accessible chart summaries, and non-color-only encodings.
3. **Design Token Translation Layer:** Replace chart colors and Tailwind values with Kinetic semantic chart tokens and verified color ramps.
4. **License Compliance:** Apache-2.0 (SPDX: Apache-2.0).
5. **Vendor Policy:** Source may be vendored only with Apache-2.0 license and NOTICE obligations preserved; dependency or local regeneration is preferred.

## Style Dictionary

1. **Utility & Fit:** Cross-platform token transformation pipeline for teams with existing design-token infrastructure. URL: https://amzn.github.io/style-dictionary/
2. **Missing State & Accessibility Coverage:** It transforms token files; it does not validate UX state coverage, contrast pair intent, naming quality, component conformance, or runtime behavior.
3. **Design Token Translation Layer:** Kinetic tokens can emit Style Dictionary JSON or import Style Dictionary JSON, but Kinetic semantic token names remain canonical.
4. **License Compliance:** Apache-2.0 (SPDX: Apache-2.0).
5. **Vendor Policy:** Source may be vendored only with Apache-2.0 license and NOTICE obligations preserved; should usually remain a dev dependency.

## Lucide

1. **Utility & Fit:** Consistent open-source icons across React, Vue, Svelte, Angular, static SVG, and design-system docs. URL: https://lucide.dev/
2. **Missing State & Accessibility Coverage:** Icons are not labels. Add accessible names or `aria-hidden`, preserve text for ambiguous actions, maintain 44px targets, and never use icon-only destructive actions without clear copy.
3. **Design Token Translation Layer:** Bind icon size, stroke width, and color to Kinetic icon tokens/custom properties.
4. **License Compliance:** ISC (SPDX: ISC), with MIT notices for Feather-derived icons.
5. **Vendor Policy:** Source may be vendored with ISC and applicable MIT notices preserved; dependency use is preferred.

## Radix Colors

1. **Utility & Fit:** Perceptually designed color scales and aliases for token seeding and palette benchmarking. URL: https://www.radix-ui.com/colors
2. **Missing State & Accessibility Coverage:** Color scales do not replace semantic token naming, dark-mode pair checks, WCAG/APCA verification, or product-state feedback.
3. **Design Token Translation Layer:** Use as primitive seeds; final output maps to Kinetic `--surface-*`, `--text-*`, `--border-*`, action, danger, success, and chart tokens.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency or generated token extraction is preferred.

## Open Props

1. **Utility & Fit:** Broad CSS custom-property primitives for sizes, typography, shadows, easings, gradients, and media-query helpers. URL: https://open-props.style/
2. **Missing State & Accessibility Coverage:** Primitive tokens are not a product design system. Kinetic still enforces semantic mapping, state matrix, contrast gates, reduced motion, density, and drift checks.
3. **Design Token Translation Layer:** Alias Open Props into Kinetic semantic variables or ingest primitives into `.ds-index`; components consume Kinetic tokens only.
4. **License Compliance:** MIT (SPDX: MIT).
5. **Vendor Policy:** Source may be vendored with MIT notice preserved; dependency or selective token ingestion is preferred.

# Deliberately Excluded

* **Aceternity Pro:** Paid and redistribution-prohibited; do not vendor source, templates, or assets. URL: https://ui.aceternity.com/
* **Flowbite Pro:** Paid and redistribution-prohibited; only Flowbite core MIT assets are allowed. URL: https://flowbite.com/pro/
* **Tailwind Plus:** Paid and redistribution-prohibited; do not vendor components, templates, or derivative libraries. URL: https://tailwindcss.com/plus

# Free but not MIT

* **GSAP:** Uses the GreenSock Standard License rather than MIT/Apache-2.0/ISC; redistribution and certain commercial uses have license-specific limits. Reference by URL only and never vendor into the codebase. URL: https://gsap.com/licensing/
* **Preline:** Free distribution includes additional Preline UI license/fair-use terms beyond plain MIT-style permissive use. Reference by URL only and never vendor into the codebase. URL: https://preline.co/
