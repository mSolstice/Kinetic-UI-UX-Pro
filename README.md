# Kinetic UI UX Pro

Kinetic UI UX Pro is an installable UI/UX engineering skill for designing, building, auditing, and verifying accessible, state-complete, token-conformant product interfaces.

It treats user intent, information architecture, content, motion, programmatic state, accessibility, and runtime performance as one system.

## Installation

```bash
git clone https://github.com/mSolstice/Kinetic-UI-UX-Pro.git kinetic-ui-ux-pro
cd kinetic-ui-ux-pro
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Minimum Python version: 3.9.

Optional dependencies are listed in `requirements.txt`. Without tree-sitter packages, use `scripts/ui_audit.py` as the fallback auditor.

## Four-Phase Workflow

1. **Frame**: define the job, actors, real states, and success signal before writing markup.
2. **Structure**: map the flow, hierarchy, content, empty/error states, and reverse paths.
3. **Build**: author semantic, state-complete, token-backed UI with reduced-motion and accessibility behavior.
4. **Verify**: run scripts, report measured results, and close with the receipt template when required.

The skill entry point is `SKILL.md`.

## Scripts

### `scripts/ast_audit.py`

Tree-sitter structural UI audit with JSON, SARIF, JUnit, breakpoint, design-token, project-graph, and static geometry checks.

```bash
python scripts/ast_audit.py templates/patterns --json --fail-on ERROR
python scripts/ast_audit.py src --format sarif --fail-on NONE > ui-audit.sarif
python scripts/ast_audit.py src --breakpoints
python scripts/ast_audit.py src --ds-index .ds-index/corpus.jsonl
python scripts/ast_audit.py src --intent templates/responsive-intent.md
```

### `scripts/color_tools.py`

Color conversion and contrast utilities for OKLCH, sRGB, WCAG 2.x ratio, APCA Lc, and ramp generation.

```bash
python scripts/color_tools.py ramp "oklch(0.55 0.18 265)"
```

### `scripts/component_adapt.py`

Fetches a registry component at generation time, remaps hardcoded design values to verified tokens, injects adapter conformance patches, and audits the result.

```bash
python scripts/component_adapt.py shadcn-ui:button --ds-index .ds-index/corpus.jsonl --out ./out/adapted/button
python scripts/component_adapt.py magic-ui:animated-beam --adapter magic-ui --redistribute
```

### `scripts/ds_index.py`

Builds `.ds-index/corpus.jsonl` from tokens, Style Dictionary JSON, Tailwind config/theme blocks, CSS custom properties, and component manifests.

```bash
python scripts/ds_index.py --build . --stats
```

### `scripts/ds_search.py`

Searches approved design-system tokens and reports hardcoded design-value drift.

```bash
python scripts/ds_search.py search "brand 600" --kind color --top 5
python scripts/ds_search.py match templates/component-scaffold.css
python scripts/ds_search.py drift ./src
python scripts/ds_search.py component "async combobox" --style swiss-grid --surface dashboard --license mit-only --framework react --top 5
python scripts/ds_search.py component "async combobox" --why shadcn-ui:combobox
```

### `scripts/ds_contract.py`

Persists settled design decisions in a per-project `design-system/contract.json`.

```bash
python scripts/ds_contract.py init
python scripts/ds_contract.py read
python scripts/ds_contract.py record style data-forward --rationale "Dense dashboard scanning"
python scripts/ds_contract.py validate
```

### `scripts/design_select.py`

Recommends a style, palette, and industry pack from a brief, then states the tradeoff.

```bash
python scripts/design_select.py recommend "banking dashboard with reconciled balances" --surface dashboard
python scripts/design_select.py recommend "public benefits form for shared phones" --surface form --apply --out ./out/benefits
```

### `scripts/iterate.py`

Turns fuzzy design feedback into bounded token-schema deltas and verifies the result.

```bash
python scripts/iterate.py apply "less corporate" --contract design-system/contract.json
python scripts/iterate.py apply "more breathing room" --out design-system/tokens.next.schema.json
```

### `scripts/variants.py`

Generates divergent verified design directions, merges chosen traits, and records accepted/rejected options in a project contract.

```bash
python scripts/variants.py explore --count 3 --brief "finance analytics dashboard" --surface dashboard
python scripts/variants.py merge --take v1:density --take v2:hierarchy --take v3:depth
python scripts/variants.py record v1 --contract design-system/contract.json
```

### `scripts/taste_memory.py`

Records revealed and stated taste preferences across projects at `~/.kinetic-ux/taste.json`; use `--no-memory` on profile/apply commands to disable it for a run.

Stored data: preference text, project evidence, accepted/rejected thing, reason, observation count, confidence, kind (`revealed` or `stated`), and `lastSeen`. You can inspect, edit, or delete `~/.kinetic-ux/taste.json` directly.

```bash
python scripts/taste_memory.py observe --rejected glassmorphism --reason "Too decorative for dashboards"
python scripts/taste_memory.py observe --accepted "dense layouts" --project "Ops console"
python scripts/taste_memory.py profile
python scripts/taste_memory.py apply --to design-system/tokens.schema.json --out design-system/tokens.memory.schema.json
python scripts/taste_memory.py apply --to design-system/tokens.schema.json --explicit-request "make it purple"
python scripts/taste_memory.py apply --to design-system/tokens.schema.json --no-memory
python scripts/taste_memory.py explain glass
python scripts/taste_memory.py forget glass
```

### `scripts/content_fixtures.py`

Generates realistic hostile content fixtures for text expansion, truncation, empty states, RTL strings, missing optional values, and locale-specific formatting.

```bash
python scripts/content_fixtures.py generate --shape prices --count 12 --locale de-DE
python scripts/content_fixtures.py generate --shape person-names --edge-cases-only --locale ar-SA
python scripts/content_fixtures.py generate --shape product-titles --empty-states --locale en-US
python scripts/ast_audit.py Component.tsx --fixtures --fail-on NONE
```

### `scripts/emit_files.py`

Safely writes `{ "path", "content" }` manifests or prints shell commands for CLI-agent environments.

```bash
python scripts/emit_files.py manifest.json --dry-run
python scripts/emit_files.py manifest.json --check
python scripts/emit_files.py manifest.json --shell bash
python scripts/emit_files.py manifest.json --shell powershell
```

### `scripts/font_metrics.py`

Computes font metric overrides from real font files.

```bash
python scripts/font_metrics.py path/to/font.woff2
```

### `scripts/industry_check.py`

Prints structured industry rules grouped by category and runs conservative heuristics for detectable rules.

```bash
python scripts/industry_check.py --count
python scripts/industry_check.py fintech templates/patterns/data-table.tsx
```

### `scripts/self_critique.py`

Runs structural design-quality critique and, when Playwright is available, rendered visual checks at 320, 768, and 1280px.

```bash
python scripts/self_critique.py templates/patterns --tier structural
python scripts/self_critique.py preview.html --against brutalist
```

### `scripts/handoff.py`

Creates a designer- and stakeholder-facing handoff as a single printable HTML file, or Markdown for a wiki.

```bash
python scripts/handoff.py generate --contract design-system/contract.json --out handoff/
python scripts/handoff.py generate --contract design-system/contract.json --out handoff/ --format markdown
```

### `scripts/license_check.py`

Gates non-vendorable licenses and unverified third-party code.

```bash
python scripts/license_check.py --root .
python scripts/license_check.py --root . --explain @radix-ui/colors
```

### `scripts/style_apply.py`

Applies a visual style constraint set to a brand hue and emits only verified token schemas.

```bash
python scripts/style_apply.py list
python scripts/style_apply.py explain data-forward --surface dashboard
python scripts/style_apply.py apply data-forward --hue 260
python scripts/style_apply.py apply swiss-grid --hue 260 --modifier dense --modifier bordered
python scripts/style_apply.py matrix
python scripts/style_apply.py apply data-forward --hue 260 --out ./out/data-forward
```

### `scripts/palette_search.py`

Searches 208 verified mood-organized palette seeds, previews generated ramps, pairs palettes with styles, imports Radix reference seeds, and verifies every seed.

```bash
python scripts/palette_search.py find "trustworthy dashboard"
python scripts/palette_search.py preview civic-ledger
python scripts/palette_search.py pair data-forward
python scripts/palette_search.py --import-radix-colors blue gray --out /tmp/palettes-with-radix.json
python scripts/palette_search.py verify-all
```

### `scripts/registry_sync.py`

Syncs open component registry metadata into `.registry/components.jsonl` with adapter license gates, ETags, and sanitized cache records only.

```bash
python scripts/registry_sync.py --sync shadcn-ui
python scripts/registry_sync.py --sync-all
python scripts/registry_sync.py --stats
python scripts/registry_sync.py --stale
```

### `scripts/token_gen.py`

Generates deterministic tokens, verifies WCAG/APCA contrast, imports/exports Style Dictionary, and benchmarks against Radix Colors.

```bash
python scripts/token_gen.py --init > tokens.schema.json
python scripts/token_gen.py templates/tokens.schema.json --format css
python scripts/token_gen.py templates/tokens.schema.json --format style-dictionary
python scripts/token_gen.py --import-style-dictionary tokens.sd.json --verify
python scripts/token_gen.py --import-radix-colors blue --verify
python scripts/token_gen.py templates/tokens.schema.json --compare-radix brand blue
```

### `scripts/ui_audit.py`

Regex fallback auditor when tree-sitter is unavailable.

```bash
python scripts/ui_audit.py templates/component-scaffold.tsx
```

## Templates And References

- `templates/patterns/`: state-complete TSX/CSS component scaffolds
- `templates/flows/`: pre-mapped UX flow specs
- `templates/receipt.md`: verification receipt template
- `references/`: UX, motion, i18n, framework, environment, licensing, and library adapter guidance

## Limitations

- No bundled headless browser; visual regression or runtime DOM verification runs only when the host provides Playwright and a browser binary.
- Static geometry heuristics cannot confirm rendered layout.
- Automated checks do not replace manual keyboard and screen-reader testing.
- Contrast scripts verify declared token pairs, not every computed runtime color combination.
- License checks only trust licenses read from files; missing metadata is reported as `UNVERIFIED`.

## License

MIT. See `LICENSE`.
