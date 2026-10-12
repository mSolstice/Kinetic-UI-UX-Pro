# Kinetic UI UX Pro — Production Build Blueprint

> **Archived planning document.** The repository has progressed beyond this historical build plan. Use `README.md`, `SKILL.md`, `docs/tooling.md`, and the current CI workflow as the source of truth for installation, capabilities, and release checks.

**What this was:** a step-by-step build plan for the early UI/UX system. It is retained for project history; commands and counts below are not release instructions.

**Historical state:** The initial v1 baseline was superseded by the current 2.x package and its executable verification suite.

**Read this first — the ordering rule:** Phase 0 comes before everything. Building more surface onto an unvalidated skill multiplies unverified code. If you only do three phases, do 0, 1, and 2.

---

## Conventions used below

| Symbol | Meaning |
|---|---|
| 🖥 **Terminal** | A shell. The folder is stated per step. |
| 🤖 **Codex Desktop** | An agent session with the repo open. Open the folder stated. |
| ✅ **Done when** | Objective acceptance criteria. Don't move on without it. |

**Root folder for everything:** `~/Kinetic UI UX Pro/` — referred to below as `<ROOT>`. Adjust to wherever you cloned or unzipped the package.

---

## Phase 0 — Repo hygiene and eval harness

*Nothing else matters until you can measure whether the skill triggers and whether the model actually runs the scripts.*

### Step 0.1 — Set up the repo

🖥 **Terminal**, in `<ROOT>`

```bash
git init
printf '__pycache__/\n*.pyc\n.venv/\nnode_modules/\n.DS_Store\nout/\n' > .gitignore
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
git add -A && git commit -m "v1 baseline"
```

✅ **Done when** `git log` shows one commit and `python scripts/token_gen.py templates/tokens.schema.json --verify` exits 0.

### Step 0.2 — Build the eval harness

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `codex/evals/` in this repo. Inside, add `cases.yaml` containing 12 test cases. Each case has: an `id`, a `prompt` a user would realistically type, a list of `must_load` reference files, a list of `must_run` scripts, and a list of `must_contain` strings that should appear in correct output.
>
> Cover these 12 cases: a modal dialog, a combobox with async search, a filterable data table, a multi-step checkout form, a dark-mode toggle, a dashboard card grid, a toast notification system, a settings page, an onboarding flow, a pricing page, "make this button feel better" (deliberately vague), and "build a login screen" (deliberately underspecified).
>
> Then write `codex/evals/run_evals.py` that reads `cases.yaml`, prints each case as a formatted prompt block I can paste into a fresh session, and accepts a pasted response file to score against the `must_*` criteria. Output a markdown scorecard with per-case pass/fail and an aggregate trigger rate.
>
> Do not use any network or LLM API — this is a manual-paste harness. Keep it under 200 lines.

✅ **Done when** `python codex/evals/run_evals.py --list` prints 12 formatted prompts.

### Step 0.3 — Run the baseline eval

🤖 **Codex Desktop** (or Claude with the skill installed), fresh session per case

Paste each of the 12 prompts into a *new* session with the skill installed. Save each response to `codex/evals/results/baseline/<id>.md`.

🖥 **Terminal**, in `<ROOT>`

```bash
python codex/evals/run_evals.py --score codex/evals/results/baseline --out codex/evals/baseline-scorecard.md
```

✅ **Done when** you have a scorecard with a number on it. **Record the trigger rate.** Everything after this is measured against it.

> **Why this matters:** if the skill only triggers on 5 of 12, the fix is the `description` field — not more content. Fix triggering before building features.

---

## Phase 1 — BM25 design-system matching

*The single highest-value addition. Converts "generates good tokens" into "conforms to* your *design system."*

### Step 1.1 — Corpus builder

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `scripts/ds_index.py`. It builds a searchable corpus from a design system so generated code can be matched against approved tokens instead of inventing new ones.
>
> It must ingest, in priority order: (1) `tokens.json` files produced by our `token_gen.py`, (2) Style Dictionary token JSON, (3) a `tailwind.config.js` or Tailwind v4 `@theme` block, (4) CSS custom-property declarations scraped from `.css` files, (5) a component manifest — a directory of `.tsx` files, from which it records exported component names and their prop names.
>
> Each corpus record must be a dict with: `id`, `kind` (color | space | radius | type | motion | shadow | component | prop), `name`, `value`, `aliases` (list), `source_file`, and `text` (a concatenated searchable string).
>
> Write the corpus to `.ds-index/corpus.jsonl`. Add a `--stats` flag printing counts per kind.
>
> Pure standard library plus what's already in requirements.txt. No network calls. Handle malformed input by skipping the record and logging to stderr, never crashing.

✅ **Done when** `python scripts/ds_index.py --build ./my-design-system --stats` prints non-zero counts.

### Step 1.2 — The BM25 engine

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `scripts/ds_search.py` implementing BM25 Okapi from scratch — no external search library. Constants k1=1.5, b=0.75.
>
> Tokenization must be design-system aware: split camelCase, kebab-case, and snake_case into constituent words, lowercase everything, and keep numeric suffixes as their own token so `brand-600` yields `brand`, `600`, and `brand-600`.
>
> Three commands:
> - `search "<query>" --kind <kind> --top 5` — ranked matches with scores
> - `match <file>` — extract every hardcoded color, spacing value, radius, duration, and font-size from a CSS or TSX file, then for each one report the nearest approved token and a verdict: EXACT, NEAR (score above threshold), or UNMATCHED
> - `drift <dir>` — run `match` across a directory and output a drift report: which hardcoded values recur most, ranked by frequency
>
> For color matching specifically, do not rely on BM25 alone. Compute perceptual distance in OKLab using our existing `color_tools.py`, and report the nearest token by ΔE alongside the BM25 name match. A hex that is visually identical to an approved token must be flagged EXACT even if its name shares no words.
>
> Exit non-zero if `match` finds any UNMATCHED value, so it can gate CI.

✅ **Done when** you can run `python scripts/ds_search.py match templates/component-scaffold.css` and it reports token coverage. Test it deliberately: add `color: #ff0000` to a scratch file and confirm it reports UNMATCHED.

### Step 1.3 — Wire drift detection into the audit

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add a `--ds-index <path>` flag to `scripts/ast_audit.py`. When supplied, load the corpus and emit a new finding class `ds/token-drift` at WARN severity for every hardcoded design value in the audited file that has an approved token available.
>
> The finding message must name the specific token that should have been used, for example: "hardcoded #3059c6 — use var(--brand-700)".
>
> Do not fire this rule inside the token definition file itself, and do not fire it for values inside `@supports not (color: oklch(...))` fallback blocks, since those are intentionally literal.

✅ **Done when** auditing a file with a hardcoded brand color names the correct replacement token.

### Step 1.4 — Update the skill to use it

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Update `SKILL.md`. In the scripts list, add `ds_search.py` and `ds_index.py` with one-line descriptions. In Phase 3 section 5, add a rule: before writing any color, spacing, radius, or duration value, search the design-system index for an approved token; only introduce a new value if the search returns UNMATCHED, and say so explicitly in the receipt. Add a `**Design-system conformance:**` line to the receipt template in `templates/receipt.md`.
>
> Keep SKILL.md under 130 lines. Cut redundancy elsewhere if needed.

✅ **Done when** SKILL.md is still under 130 lines and mentions the index in both the script list and Phase 3.

---

## Phase 2 — Enhanced AST parsing

*v1 parses TSX and CSS. This closes the remaining structural blind spots.*

### Step 2.1 — Cross-file resolution

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Upgrade `scripts/ast_audit.py` from single-file to project-aware. Add a first pass that builds a module graph across the target directory: for each file, record its imports, its exported component names, and which CSS files it imports.
>
> This enables three findings that single-file analysis cannot produce:
> - `a11y/orphan-label` — a `<label htmlFor="x">` where no element with `id="x"` exists in the same component tree
> - `a11y/unreachable-focus` — a focus-trap or modal component imported but never given a return-focus target
> - `ds/class-not-defined` — a `className` string referencing a CSS class defined in no imported stylesheet
>
> Keep single-file mode working exactly as it does now when the target is a file rather than a directory.

✅ **Done when** `python scripts/ast_audit.py ./src` reports at least one cross-file finding on a project that has one, and single-file behavior is unchanged.

### Step 2.2 — Media query and breakpoint analysis

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add a breakpoint analyzer to `scripts/ast_audit.py`. Parse every `@media` and `@container` query in the CSS files and build a table of declared breakpoints.
>
> Emit findings for: overlapping ranges that could both match and produce ambiguous cascade; gaps between breakpoints where no rule applies; breakpoints below 320px, which we do not support; more than six distinct breakpoints, which signals ad-hoc rather than systematic responsive design; and any `min-width` expressed in `px` rather than `rem`, which breaks under browser zoom.
>
> Add a `--breakpoints` flag that prints the breakpoint table alone as a readable report.

✅ **Done when** `--breakpoints` prints a table and flags a deliberately overlapping pair you add for testing.

### Step 2.3 — Static overlap and clipping heuristics

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add static geometry heuristics to `scripts/ast_audit.py`. We cannot run a browser, so this is deliberately conservative — flag only patterns that are near-certainly wrong, and mark every finding INFO with a note that runtime verification is required.
>
> Detect: fixed `height` or `width` on a container whose children have no overflow handling; `position: absolute` without a positioned ancestor in the same file; a `z-index` above 100 that is not defined as a token; `white-space: nowrap` combined with a fixed width; and a grid or flex child with `min-width: auto` inside a container that could shrink below its content.
>
> Add a header line to this output stating plainly: "Static heuristics only — these cannot confirm actual rendered layout. Verify in a browser."

✅ **Done when** the section prints with its disclaimer and catches a deliberately clipped fixed-height container.

### Step 2.4 — Machine-readable output for CI

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add two output formats to `scripts/ast_audit.py`: `--format sarif` producing valid SARIF 2.1.0 for GitHub code scanning, and `--format junit` producing JUnit XML for generic CI.
>
> Then create `.github/workflows/ui-audit.yml` that on pull request runs the AST audit in SARIF mode and uploads the result, runs `token_gen.py --verify` and fails the build on non-zero exit, and runs `ds_search.py drift ./src` as a non-blocking informational step.

✅ **Done when** the SARIF output validates against the schema and the workflow file is syntactically valid YAML.

---

## Phase 3 — Environment compatibility matrix

*From your requirements: the skill must adapt output shape to where it runs.*

### Step 3.1 — Environment detection reference

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `references/environments.md`. It defines how output adapts per host environment, and how to detect which one we're in.
>
> Cover four environments. **CLI agents** (Claude Code, Codex CLI): emit file diffs and discrete patches, never large inline dumps; use workspace-relative paths; provide copy-pasteable heredoc file creation, with a PowerShell variant for Windows. **IDE extensions:** emit import-ready modular file trees aligned to existing project conventions. **Web and mobile chat:** emit self-contained runnable blocks with zero-config imports and no filesystem assumptions; note that browser storage APIs are unavailable in Claude artifacts. **CI and headless:** emit machine-readable output only, exit codes over prose.
>
> For detection, give an ordered checklist of signals: presence of a filesystem tool, presence of `package.json` in context, whether the request mentions a path, and whether prior turns show file operations. State the default when detection is ambiguous — assume chat, because emitting a file tree into a chat is a worse failure than emitting a runnable block into an IDE.
>
> Add a table mapping each environment to: preferred output shape, path convention, whether to write files, and receipt verbosity.

✅ **Done when** the file has the four environments, the detection checklist, and the mapping table.

### Step 3.2 — Cross-platform file emission helper

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `scripts/emit_files.py`. It takes a JSON manifest of `{path, content}` objects and writes them, with `--dry-run`, `--shell bash|powershell` to instead *print* the equivalent file-creation commands rather than writing, and `--check` to verify the manifest would not overwrite existing files.
>
> Path handling must be safe: reject absolute paths and any path containing `..`, and create parent directories as needed. This is what the skill uses when a CLI environment is detected.

✅ **Done when** `--shell powershell --dry-run` prints valid PowerShell and the traversal guard rejects `../etc/passwd`.

### Step 3.3 — Wire into SKILL.md

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add a short "Environment adaptation" subsection to Phase 1 of `SKILL.md` — four lines maximum, pointing at `references/environments.md` for detail. Add `references/environments.md` to the reference table with a one-line trigger description.

✅ **Done when** SKILL.md is still under 130 lines.

---

## Phase 4 — Templates and scaffolds

*The seven patterns where implementations most reliably go wrong.*

### Step 4.1 — Pattern scaffolds

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `templates/patterns/`. Add seven scaffolds, each as a `.tsx` file plus a companion `.css`: `combobox`, `modal`, `data-table`, `multi-step-form`, `toast-queue`, `command-palette`, `virtual-list`.
>
> Every scaffold must implement the full state matrix from `references/interaction-states.md` — default, hover, focus-visible, active, loading, disabled, error, success, empty — plus a reduced-motion degradation path, and must reference only CSS custom properties, never hardcoded values.
>
> Pattern-specific requirements: the combobox keeps DOM focus on the input and uses `aria-activedescendant`, never moving focus into the listbox. The modal uses native `<dialog>`. The data-table handles sort, filter, empty, cleared-by-filter, and overflow states distinctly. The toast queue caps concurrent toasts and never uses assertive live regions for non-urgent messages. The virtual list reserves scroll height to keep CLS at zero.
>
> Add `templates/patterns/README.md` with a table: pattern, when to use it, the specific failure mode it prevents, and its accessibility contract.
>
> After writing each one, run `python scripts/ast_audit.py` against it and fix every ERROR before moving to the next.

✅ **Done when** `python scripts/ast_audit.py templates/patterns --fail-on ERROR` exits 0.

### Step 4.2 — Flow templates

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `templates/flows/` with five pre-mapped flow specs as markdown, following the format in `templates/ux-brief.md`: `auth`, `checkout`, `onboarding`, `search-refine`, `destructive-delete`.
>
> Each must map every state including the failure branches, and each must have a reverse path from every step. For each flow list the specific edge cases that are usually missed — for auth that includes account-exists-with-different-provider, expired reset link, and rate-limited retry; for checkout it includes payment declined mid-flow, cart item going out of stock between steps, and address validation failure.
>
> These are specs, not code. No implementation.

✅ **Done when** all five exist and each has an explicit failure branch per step.

### Step 4.3 — Motion tokens and recipes

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `templates/motion.css` defining a complete motion token layer: a duration scale, named easing curves, and — for each duration token — a paired reduced-motion value, all inside a `@media (prefers-reduced-motion: reduce)` override so switching is automatic.
>
> Then create `references/motion-recipes.md` with six worked recipes: FLIP layout animation, shared-element transition, staggered list entry, gesture-driven drag, scroll-linked reveal, and skeleton-to-content swap.
>
> Each recipe needs: when to use it, the implementation in both Framer Motion and vanilla CSS/View Transitions, its explicit reduced-motion degradation, and its performance note. For FLIP specifically, show the correct read-then-write batching — all `getBoundingClientRect` calls first, then all style writes — since this is the pattern people get wrong.

✅ **Done when** all six recipes have both implementations and a stated degradation path.

### Step 4.4 — Surface-specific reference

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `references/patterns-by-surface.md` covering five surfaces: dashboard, settings, feed, wizard, editor.
>
> For each, document the known information-architecture failure modes, the states that are usually forgotten, the appropriate motion budget — dashboards get near-zero, marketing pages get more — and the density and hierarchy guidance.
>
> Include an explicit rule carried over from the asset library: do not use expressive animation libraries in data-dense product interfaces. Reserve them for marketing surfaces, onboarding, and landing pages.

✅ **Done when** all five surfaces have all four sections.

---

## Phase 5 — Third-party library integration

**⚠️ Legal note before you start.** The asset library you provided spans multiple licenses. shadcn/ui and Radix are MIT and freely vendorable. Others are not — some are free-to-use-but-not-redistribute, and at least one requires a paid license for commercial templates. **Do not vendor component source into this repo.** Reference by URL and document the license per entry. Your own source document says to verify licensing before copying anything; that instruction is correct and load-bearing.

### Step 5.1 — Adapters, not copies

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `references/library-adapters.md`. For each of shadcn/ui, Radix UI, DaisyUI, Flowbite, Motion, and Style Dictionary, document: what it is good for, what it does *not* solve that our skill must still enforce, how our token layer maps onto its theming system, and its license with a note on whether source may be vendored.
>
> Critically, for each library list the accessibility gaps our skill must still cover on top of it. Radix gives focus management but not loading-state announcement. DaisyUI's semantic classes carry no state matrix. Motion has no automatic reduced-motion handling.
>
> Do not copy any component source into this repository. Reference by URL only.

✅ **Done when** every entry has a license column and a "still must enforce" section.

### Step 5.2 — Style Dictionary bridge

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Add `--format style-dictionary` to `scripts/token_gen.py`, emitting our tokens in Style Dictionary's expected JSON structure so they can be consumed by existing pipelines.
>
> Also add an `--import-style-dictionary <file>` flag doing the reverse: read a Style Dictionary token file and convert it into our schema format, running full contrast verification on the imported palette and reporting any pair that fails.
>
> This is the interoperability bridge — teams with existing tokens can verify them against our dual contrast gate without rebuilding.

✅ **Done when** a round trip — export then re-import — produces an equivalent schema and the verification report runs on imported tokens.

---

## Phase 6 — Packaging and release

### Step 6.1 — Plugin manifest

🤖 **Codex Desktop**, folder `<ROOT>`

> **Prompt:**
> Create `plugin.json` declaring this as an installable plugin: name, version 2.0.0, description, the skill entry point, the script list with their optional dependencies, and the minimum Python version. Add a `LICENSE` file — MIT unless you tell me otherwise — and a `README.md` covering installation, the four-phase workflow, every script with an example invocation, and an explicit limitations section.
>
> The limitations section must state plainly: no headless browser, so no visual regression or runtime DOM verification; static geometry heuristics cannot confirm rendered layout; and automated checks do not replace manual keyboard and screen-reader testing.

✅ **Done when** `plugin.json` parses and README documents every script.

### Step 6.2 — Re-run evals and compare

🖥 **Terminal**, in `<ROOT>`

Repeat Step 0.3 with the same 12 cases into `codex/evals/results/v2/`, then:

```bash
python codex/evals/run_evals.py --score codex/evals/results/v2 --compare codex/evals/baseline-scorecard.md
```

✅ **Done when** you have a delta. **If the trigger rate dropped, the skill got worse.** More content can hurt — that's what the comparison is for.

### Step 6.3 — Ship

🖥 **Terminal**, in `<ROOT>`

```bash
python scripts/ast_audit.py . --fail-on ERROR
python scripts/token_gen.py templates/tokens.schema.json --verify
git add -A && git commit -m "v2: BM25, enhanced AST, environments, patterns"
git tag v2.0.0
cd .. && zip -r Kinetic-UI-UX-Pro-v2.zip "Kinetic UI UX Pro" -x '*/.venv/*' '*/__pycache__/*' '*/.git/*' '*/codex/evals/results/*' '*/design-system/contract.json'
```

✅ **Done when** both checks exit 0 and the zip excludes the venv.

---

## Build order summary

| Phase | Effort | Value | Skippable? |
|---|---|---|---|
| 0 · Evals | Low | **Critical** | No — everything else is unmeasured without it |
| 1 · BM25 | High | **Highest** | No — this is the enterprise differentiator |
| 2 · AST | Medium | High | Steps 2.3–2.4 yes, 2.1–2.2 no |
| 3 · Environments | Low | Medium | Yes, if you only target one host |
| 4 · Templates | Medium | High | Partially — 4.1 and 4.3 matter most |
| 5 · Libraries | Low | Medium | Yes, but read the license note regardless |
| 6 · Packaging | Low | Medium | Only if you're not distributing |

**Minimum viable v2:** Phases 0, 1, 2.1–2.2, 4.1, 4.3. That's the BM25 engine, project-aware parsing, the seven pattern scaffolds, and the motion layer — measured before and after.

---

## What this still will not do

State these limits honestly in your README rather than discovering them in production:

- **No headless browser.** No visual regression, no runtime DOM inspection, no computed cascade. Playwright's browser binaries download from CDNs that sandboxed environments typically block. In CI with open network, add it as a separate optional step.
- **No layout engine.** The geometry heuristics in Step 2.3 are pattern-matching, not computation. Only a browser knows what actually rendered.
- **Automation is not testing.** Every automated a11y tool combined catches a minority of real accessibility defects. Manual keyboard and screen-reader passes stay mandatory — your own source document says this, and it's right.
