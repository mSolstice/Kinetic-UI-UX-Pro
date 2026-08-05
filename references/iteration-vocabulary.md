# Iteration Vocabulary

Use this lookup when feedback is fuzzy. Apply bounded deltas to the current design contract or token schema; do not restart from the base rules.

Every entry keeps these fixed: contrast gates, touch targets, focus visibility, reduced-motion support, semantic structure.

| Phrase people say | Parameter deltas | Never changes |
|---|---|---|
| Less corporate | Raise radius one step; warm neutrals +5 to +12 deg toward orange; loosen display tracking +0.01em; raise type scale ratio one notch, max +0.06; replace ease-in-out with custom ease-out; reduce border reliance in favor of spacing separation. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More corporate | Lower radius one step; cool neutrals -4 to -8 deg; tighten display tracking -0.005em to 0; reduce type scale ratio one notch, max -0.04; use standard easing; increase border/subtle-divider reliance one level. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More characterful | Add one distinctive type or shape move only; raise accent chroma 8-15%; allow one asymmetric spacing pattern per view; increase radius contrast between small and large components by one step. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Less characterful | Remove decorative asymmetry; reduce accent chroma 8-15%; normalize radius contrast by one step; keep one type family unless brand requires two. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More breathing room | Increase spacing scale multiplier 1.25x; raise line-height +0.1; increase section padding two spacing steps; widen card/grid gaps one step. Do not increase font size. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Less breathing room | Decrease spacing scale multiplier 0.85x; reduce line-height -0.05 minimum 1.25; reduce section padding one spacing step; keep target size at or above 44. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Less cramped | Increase spacing scale multiplier 1.2x; raise line-height +0.08; add one extra gap step between groups; preserve content hierarchy. Do not enlarge body text. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More compact | Decrease spacing multiplier 0.85x; use denser grouping; reduce section padding one step; keep line-height at least 1.25 and touch targets at least 44. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More depth | Add one elevation layer; raise shadow token one level or border contrast one step; allow overlap only on non-critical surfaces; keep depth non-informational unless labelled. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Flatter | Remove one shadow layer; lower shadow opacity/blur one level; replace elevation with spacing or subtle border; remove overlap unless it communicates hierarchy. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too loud | Reduce accent chroma 15-25%; reduce saturated surface use to one role; lower type weight ceiling one step; shorten motion travel while keeping timing. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too restrained | Raise accent chroma 10-18%; permit one stronger action/background role; increase type weight ceiling one step; add one purposeful motion cue. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too cold | Rotate neutrals +5 to +12 deg toward orange; slightly lower neutral chroma cap if gray becomes tinted; use warmer success/warning support only where semantic. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too warm | Rotate neutrals -5 to -12 deg away from orange; reduce warm accent chroma 8-12%; keep error/warning semantics unchanged. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too generic | Pick one axis to differentiate: type contrast +0.05 ratio, shape contrast +1 radius step, or accent hue shift 12-20 deg. Do not change all three at once. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More familiar | Reduce distinctive axis by one step; align radius and spacing to platform defaults; keep accent hue stable; simplify motion to standard ease-out. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too heavy | Reduce font weight ceiling one step; lower shadow opacity/blur one step; reduce border weight one step; increase whitespace +10% if density permits. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too light | Increase font weight ceiling one step; strengthen border contrast one step; raise text-muted contrast by one token step; avoid adding heavy shadows first. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More playful | Increase radius multiplier 1.2x; raise accent chroma 8-14%; permit spring easing for non-critical feedback; widen display type ratio +0.04. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More serious | Decrease radius multiplier 0.85x; reduce accent chroma 8-14%; use standard/decelerate easing; reduce display type ratio -0.03. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Dated | Remove glossy gradients and heavy shadows; reduce border radius uniformity; use tokenized shadows only; replace ease-in-out with modern ease-out; improve density hierarchy. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too current | Remove trend-specific effects; lower radius contrast one step; reduce motion duration 10%; keep palette more neutral and durable. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too busy | Reduce accent roles to one primary and one semantic; increase group spacing one step; lower card border/shadow count; remove decorative motion. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too focused | Restore one secondary information layer; decrease group spacing 10%; add muted metadata treatment; keep primary action dominant. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Looks cheap | Reduce saturated backgrounds; lower shadow blur/spread one level; increase whitespace 10-20%; use fewer weights; make accent rarer and stronger. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More premium | Reduce visible borders one step; increase whitespace 15%; lower accent usage but raise its contrast; slow local motion 10%; use quieter surfaces. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too slow | Multiply durations by 0.8; cap micro at 100ms and local at 200ms; use decelerate/ease-out; remove queued animations. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| More deliberate motion | Multiply durations by 1.15, cap local at 280ms; increase easing contrast; keep reduced-motion equivalents under 100ms. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Too much motion | Remove decorative scroll motion; multiply durations by 0.75; reduce travel distance 50%; keep opacity/state-change signals. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |
| Lifeless | Add one stateful motion cue; multiply local duration by 1.1; permit spring only for reversible, low-risk feedback; preserve reduced-motion fallback. | Contrast gates; touch targets; focus visibility; reduced-motion support; semantic structure. |

## Compound And Contradictory Feedback

Compound feedback is common: "more premium but friendlier," "less corporate but still serious," "more playful but less loud." Resolve it by identifying the primary axis before changing tokens.

When two requests pull opposite directions, ask which matters more instead of averaging them into mush. "Premium" usually lowers chroma, increases whitespace, and reduces borders; "friendlier" often increases radius and warmth. A coherent answer might choose premium density/contrast while allowing friendlier radius, but only after the user names the priority.

Apply at most two axes per iteration. More than that becomes a redesign and should update the project contract with a new decision rather than silently mutating taste.
