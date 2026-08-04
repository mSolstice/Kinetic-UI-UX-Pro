# UX Foundations

Read this during Phase 1 and 2. It governs *what* gets built and *why*; the other references govern how.

## Contents
1. Intent capture
2. Flows and information architecture
3. Cognitive load
4. Heuristic checklist
5. Content design and microcopy
6. Edge and failure states
7. Ethical patterns
8. Onboarding and first-run
9. Trust, consent, and destructive actions
10. Success metrics

---

## 1. Intent capture

Most UI requests are solutions in disguise. "Add a filter dropdown" is a proposed answer; the job might be "I can't find last week's failed orders." Design against the job, not the proposal.

**Reframe once, briefly, then build.** Ask what the user is trying to accomplish, then confirm the reframing in a sentence — don't run a discovery workshop over a button.

Batch clarifying questions into a single round. Prefer 2–3 questions with concrete options over open-ended interrogation. If the user doesn't answer, state your assumptions explicitly and build on them; a working artifact with named assumptions beats a stalled conversation.

**Signals that the stated request hides a different problem:**
- A request for more controls, filters, or settings → the default is wrong
- A request for a tooltip or help text → the label or affordance is unclear
- A request for a confirmation dialog → the action is not undoable, and should be
- A request to "make it pop" → hierarchy is flat, not colors dull

## 2. Flows and information architecture

Sketch the flow in text before any layout. Minimum viable flow spec:

```
Entry → [state] → action → [state] → outcome
                    ↓ failure
                  [recovery path]
```

Every step needs: what the user sees, what they can do, what happens on failure, and how they get back. A flow with no reverse path is incomplete.

**Structural rules:**
- **One primary action per view.** If two actions have equal weight, the hierarchy is undecided. Secondary and tertiary actions must be visually and semantically subordinate.
- **Depth over breadth for choice, breadth over depth for navigation.** People scan wide menus faster than they traverse deep ones, but they make better decisions from short lists.
- **Match the user's mental model, not the database schema.** Grouping by table structure is the most common IA failure in generated UI.
- **Preserve context across steps.** Multi-step flows must show position, allow reverse navigation, and never silently discard entered data.
- **Deep-linkable state.** Filters, tabs, and steps belong in the URL where the platform allows it — otherwise sharing and back-button both break.

## 3. Cognitive load

- **Progressive disclosure.** Show what is needed now; defer the rest behind an affordance. A long scroll is not disclosure.
- **Recognition over recall.** Never require memory of something the interface could display. Show the selected filter, not just the filter button.
- **Chunk decisions.** Break long forms by meaning, not arbitrary count. Ask for related things together.
- **Sensible defaults do the work.** Every field with a reasonable default should have it pre-filled. The best form is one already answered.
- **Reduce choice at the point of action.** Move rarely-used options into a secondary surface rather than presenting everything at equal weight.

## 4. Heuristic checklist

Run against the built interface before finishing:

- [ ] **Visibility of system status** — the user always knows what is happening and whether it worked
- [ ] **Match to real world** — language is the user's, not the system's; no internal jargon or error codes as primary text
- [ ] **User control and freedom** — clear exits, undo where possible, cancel on anything long-running
- [ ] **Consistency** — same concept, same word, same component, everywhere
- [ ] **Error prevention** — constrain input, disable impossible actions, confirm only genuinely destructive ones
- [ ] **Recognition over recall** — options visible rather than remembered
- [ ] **Flexibility** — shortcuts for repeat users without penalizing novices
- [ ] **Aesthetic and minimalist** — nothing competing with the primary action
- [ ] **Error recovery** — messages say what happened, why, and the next step
- [ ] **Help in context** — assistance where the confusion occurs, not in a separate doc

## 5. Content design and microcopy

**Write the words before the layout.** Lorem ipsum conceals broken hierarchy and unrealistic text lengths.

- **Buttons state the outcome**, not the mechanism: "Send invite," not "Submit." Never "OK" for a consequential action.
- **Labels are nouns the user recognizes.** If a label needs a tooltip, rewrite the label.
- **Placeholders are not labels.** They vanish on focus, fail contrast, and break screen readers.
- **Errors have three parts:** what happened, why, what to do next. "Invalid input" has none of them.
- **Blame the system, never the user.** "We couldn't reach the server" over "You entered an invalid request."
- **Empty states are onboarding.** State what belongs here, why it's empty, and give the action that fills it.
- **Numbers and dates get formatted for locale**, and relative time ("2 hours ago") needs an absolute value available on hover or via `<time datetime>`.

## 6. Edge and failure states

Design these *before* the populated happy path. Every data-driven view needs:

| Condition | Requirement |
|---|---|
| Empty (never had data) | Explanation + primary action to create |
| Cleared (had data, now filtered out) | Distinguish from empty; offer to reset filters |
| Loading | Skeleton matching final geometry; not a centered spinner over blank space |
| Partial | Show what arrived; indicate what's still coming |
| Slow | After ~5s, acknowledge and offer cancel |
| Error | Cause + retry, not a stack trace |
| Offline | Detect, communicate, queue if possible |
| Stale | Mark data as outdated rather than silently showing old values |
| Overflow | Long strings, huge numbers, 500-row lists, missing avatars |
| Permission-denied | Explain the restriction; don't render a control that will fail |

**Test data must be hostile.** Names with diacritics and CJK characters, one-character and 200-character strings, zero and negative and enormous numbers, null fields, and a single-item list.

## 7. Ethical patterns

Refuse to implement, and offer an honest alternative:

- **Confirmshaming** — "No thanks, I hate saving money"
- **Asymmetric friction** — one click to subscribe, five screens to cancel
- **Forced continuity** — trials that convert silently
- **Disguised ads** — promotional content styled as native content
- **Preselected upsells** — opt-outs checked by default
- **Fake urgency and scarcity** — invented countdowns and "3 left" counters
- **Roach motel** — easy in, obstructed out
- **Misdirection** — visual weight steering toward the choice that benefits the business

The test: would the user be annoyed if they understood exactly what the interface was doing? If yes, it's a dark pattern.

## 8. Onboarding and first-run

- **Show value before asking for anything.** Defer account creation, permissions, and configuration until the user has seen why they'd bother.
- **Prefer doing over telling.** A pre-populated example beats a five-slide tour.
- **Request permissions in context**, at the moment they're needed, with the reason stated.
- **Make every tour skippable and resumable.** A modal the user cannot dismiss is a trap.
- **Empty states carry onboarding weight** — they're seen by everyone, unlike a tour that's dismissed once.

## 9. Trust, consent, and destructive actions

- **Undo beats confirm.** A dialog interrupts everyone to prevent a rare mistake; undo costs nothing until needed.
- **Confirm only the genuinely irreversible**, and make the confirmation specific — name the object, and require typing its name for high-stakes deletion.
- **Destructive actions are visually distinct** and never adjacent to the primary action.
- **Consent is granular and reversible**, defaults are opt-out, and rejecting is as easy as accepting.
- **Show what data is used and why**, at the point of collection.
- **Autosave communicates itself** — silent saving is as anxiety-producing as silent loss.

## 10. Success metrics

Name at least one observable signal before building:

- **Task success rate** — can they complete it unaided
- **Time to first value** — how long until the product does something useful
- **Error rate and recovery rate** — how often things fail and whether users get out
- **Drop-off point** — which step loses people
- **Repeat usage** — do they come back to the feature

If no plausible metric would move, question whether the thing should be built.
