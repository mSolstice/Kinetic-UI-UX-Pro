# React Native Translation

Use this when the target is React Native, Expo, or mobile app UI. About 60% of the doctrine ports unchanged; the other 40% changes because native accessibility, layout, motion, and input are not the DOM.

## Translation Table

| Web concept | Native equivalent | Note |
|---|---|---|
| `aria-label` | `accessibilityLabel` | Required on icon-only and custom touch controls. |
| `role` | `accessibilityRole` | Use native roles such as `button`, `link`, `image`, `header`, `tab`, `switch`, `checkbox`. |
| `aria-busy` | `accessibilityState={{ busy: true }}` | Pair with visible loading state and state-machine status. |
| Live regions | `AccessibilityInfo.announceForAccessibility()` | No persistent DOM live region exists; announce sparingly after state changes. |
| `prefers-reduced-motion` | `AccessibilityInfo.isReduceMotionEnabled()` | Check before `Animated`, Reanimated, layout, gesture, or navigation motion. |
| Focus management | `AccessibilityInfo.setAccessibilityFocus(ref)` | Use after route changes, dialogs, error summaries, and modal close/return flows. |
| CSS | `StyleSheet.create()` | Keep tokens in JS/TS modules; avoid inline object literals for reusable surfaces. |
| `rem` | Density-independent pixels | React Native numbers map to dp/pt-like units, not CSS px/rem. |
| `:hover` | No equivalent | Do not design essential affordance through hover on mobile. |
| `<button>` | `Pressable` or platform component | Must add label, role, state, target size, and feedback. |
| `<img alt="">` | `<Image accessible={false}>` | Decorative images must be explicitly hidden; meaningful images need `accessibilityLabel`. |
| `@media` width queries | `useWindowDimensions()` | Avoid one-time `Dimensions.get('window')` for layout. |
| `position: sticky` | No direct equivalent | Use navigation/header patterns native to the platform. |

## Native-Only Obligations

**Safe area:** screens need `SafeAreaView` or `useSafeAreaInsets()` when content approaches the status bar, notch, home indicator, or gesture edges.

**Keyboard avoidance:** forms need `KeyboardAvoidingView`, scroll-to-focused-field behavior, visible submit actions, and preserved error text while the keyboard is open.

**Platform divergence:** iOS and Android differ in back behavior, text rendering, switch controls, shadows/elevation, haptics, date pickers, and accessibility focus. Verify both; do not assume parity.

**Gestures:** touch gestures need cancellation, velocity thresholds, conflict handling with scroll, and Android back gesture behavior. A gesture cannot be the only path to a destructive or critical action.

**List virtualization:** use `FlatList`, `SectionList`, or equivalent for real lists. This is correctness, not polish: unvirtualized lists drop frames, lose scroll position, and can break assistive navigation.

## What Ports Unchanged

- Nine-state matrix: default, hover-equivalent feedback where available, focus/accessibility focus, active/pressed, loading, disabled, error, success, empty.
- Discriminated unions: one `status`, not parallel booleans.
- Empty and error states: explain absence, recovery, and next action.
- Contrast math: WCAG 2.x AA and APCA still apply to native colors.
- Motion earns its place: motion must communicate state, causality, or spatial relationship.
- Token discipline: colors, spacing, radius, and duration still come from verified tokens.

## What Does Not Port

- ARIA names do not exist; use React Native accessibility props.
- DOM focus and tab order do not exist; use accessibility focus and platform navigation patterns.
- CSS cascade, selectors, pseudo-classes, `rem`, `@media (hover)`, forced colors, and browser font-loading behavior do not apply.
- Hover affordance disappears; pressed, disabled, selected, checked, and focus feedback must carry the interaction model.
- Browser layout verification does not prove mobile correctness; test on iOS and Android, with screen readers, rotation, split-screen, large text, keyboard, and safe-area variants.
