# Kinetic UI UX Pro Tooling

This page is the human-facing command catalog for the deterministic tools bundled with Kinetic UI UX Pro. The root README describes the product and workflow; this page describes the executable surface.

Run commands from the repository root with an activated Python environment unless a host wrapper resolves them from its plugin root.

## Design Direction and Memory

| Script | Purpose |
| --- | --- |
| `scripts/design_select.py` | Rank compatible style, palette, and industry candidates from a brief and state the tradeoff. |
| `scripts/style_apply.py` | Compose a style and modifiers, derive concrete tokens, and retry verification inside the constraint ranges. |
| `scripts/palette_search.py` | Search 208 palette seeds by mood, preview semantic contrast, pair with styles, and verify all seeds. |
| `scripts/variants.py` | Generate mechanically divergent directions, merge coherent traits, and record accepted/rejected variants. |
| `scripts/iterate.py` | Translate fuzzy feedback into bounded token deltas and reject changes that break verification. |
| `scripts/ds_contract.py` | Persist project decisions, page overrides, token hashes, component inventory, rejections, and open questions. |
| `scripts/taste_memory.py` | Record stated and revealed preferences with confidence decay; never override the current request. |

```bash
python scripts/design_select.py recommend "internal operations dashboard" --surface dashboard
python scripts/style_apply.py apply data-forward --hue 250 --modifier dense --out ./out/system
python scripts/palette_search.py find "restrained trustworthy financial product"
python scripts/variants.py explore --count 3 --brief "member onboarding" --surface wizard
python scripts/iterate.py apply "more breathing room" --contract design-system/contract.json
python scripts/ds_contract.py record density compact --page analytics --rationale "Analysts need faster scanning"
python scripts/ds_contract.py read --page analytics
python scripts/ds_contract.py validate
python scripts/taste_memory.py profile
```

## Tokens and Design-System Search

| Script | Purpose |
| --- | --- |
| `scripts/token_gen.py` | Generate CSS, Tailwind, JSON, Style Dictionary, or React Native tokens and verify contrast. |
| `scripts/color_tools.py` | Convert OKLCH/sRGB, gamut-map colors, calculate WCAG/APCA, and generate ramps. |
| `scripts/ds_index.py` | Build a searchable corpus from token files, Tailwind themes, CSS variables, and components. |
| `scripts/ds_search.py` | Search approved values, match hardcoded values, report drift, and find registry components. |
| `scripts/font_metrics.py` | Calculate real font metric overrides from a font file. |

```bash
python scripts/token_gen.py templates/tokens.schema.json --format all --out ./out/tokens
python scripts/token_gen.py templates/tokens.schema.json --verify
python scripts/token_gen.py --import-style-dictionary tokens.sd.json --verify
python scripts/token_gen.py --import-radix-colors blue --verify
python scripts/ds_index.py --build . --stats
python scripts/ds_search.py search "brand 600" --kind color --top 5
python scripts/ds_search.py match src/Button.tsx
python scripts/ds_search.py drift ./src
```

## Components, Registries, and Content

| Script | Purpose |
| --- | --- |
| `scripts/registry_sync.py` | Sync metadata-only registry records with license gates, ETags, and offline cache fallback. |
| `scripts/component_adapt.py` | Fetch a permitted component into a temporary directory, remap tokens, patch state gaps, and audit it. |
| `scripts/content_fixtures.py` | Generate hostile localized data, long strings, optional nulls, RTL samples, prices, and empty-state copy. |
| `scripts/emit_files.py` | Safely write a JSON file manifest or print Bash/PowerShell creation commands. |

```bash
python scripts/registry_sync.py --sync-all --stats
python scripts/ds_search.py component "async combobox" --style swiss-grid --surface dashboard --license mit-only --framework react --top 5
python scripts/component_adapt.py shadcn-ui:button --ds-index .ds-index/corpus.jsonl --out ./out/button
python scripts/content_fixtures.py generate --shape prices --count 12 --locale de-DE
python scripts/content_fixtures.py generate --shape person-names --edge-cases-only --locale ar-SA
python scripts/emit_files.py manifest.json --check
```

## Audit and Verification

| Script | Purpose |
| --- | --- |
| `scripts/ast_audit.py` | Tree-sitter project audit with token drift, breakpoints, responsive intent, fixtures, native mode, SARIF, and JUnit. |
| `scripts/ui_audit.py` | Regex fallback audit when tree-sitter is unavailable. |
| `scripts/self_critique.py` | Structural design critique plus capability-gated Playwright visual checks. |
| `scripts/industry_check.py` | Print industry rules and run conservative checks for detectable rules. |
| `scripts/license_check.py` | Fail on unverified or non-allowlisted dependency and vendored-source licenses. |

```bash
python scripts/ast_audit.py ./templates --fail-on ERROR
python scripts/ast_audit.py ./src --format sarif --fail-on NONE > ui-audit.sarif
python scripts/ast_audit.py ./src --platform auto --ds-index .ds-index/corpus.jsonl
python scripts/ast_audit.py ./src --intent templates/responsive-intent.md
python scripts/self_critique.py ./src --against data-forward
python scripts/industry_check.py fintech ./src/TransferForm.tsx
python scripts/license_check.py --root .
```

## Delivery

| Script | Purpose |
| --- | --- |
| `scripts/handoff.py` | Turn the design contract into a printable, plain-language HTML or Markdown handoff. |

```bash
python scripts/handoff.py generate --contract design-system/contract.json --out handoff/
python scripts/handoff.py generate --contract design-system/contract.json --out handoff/ --format markdown
```

## Verification Recipes

Verify all built-in palette seeds:

```bash
python scripts/palette_search.py verify-all
```

Inspect the style/modifier compatibility matrix:

```bash
python scripts/style_apply.py matrix
```

Run the repository's high-signal local checks:

```bash
python -m py_compile scripts/*.py codex/evals/run_evals.py
python scripts/token_gen.py templates/tokens.schema.json --verify
python scripts/palette_search.py verify-all
python scripts/industry_check.py --count
python scripts/ast_audit.py templates/ --fail-on ERROR
```

Run the manual-paste behavior evaluation harness:

```bash
python codex/evals/run_evals.py --list
python codex/evals/run_evals.py --score codex/evals/results/v5 --compare codex/evals/baseline-scorecard.md
```

## Optional Dependencies

Most tools use the Python standard library. `requirements.txt` adds:

- `tree-sitter` and `tree-sitter-language-pack` for structural parsing.
- `fonttools` and `brotli` for real font metrics and WOFF2 support.
- Playwright is optional and intentionally not bundled; visual critique reports when it is unavailable.
