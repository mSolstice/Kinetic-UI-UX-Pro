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
```

### `scripts/color_tools.py`

Color conversion and contrast utilities for OKLCH, sRGB, WCAG 2.x ratio, APCA Lc, and ramp generation.

```bash
python scripts/color_tools.py ramp "oklch(0.55 0.18 265)"
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

### `scripts/license_check.py`

Gates non-vendorable licenses and unverified third-party code.

```bash
python scripts/license_check.py --root .
python scripts/license_check.py --root . --explain @radix-ui/colors
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

- No headless browser, so no visual regression or runtime DOM verification.
- Static geometry heuristics cannot confirm rendered layout.
- Automated checks do not replace manual keyboard and screen-reader testing.
- Contrast scripts verify declared token pairs, not every computed runtime color combination.
- License checks only trust licenses read from files; missing metadata is reported as `UNVERIFIED`.

## License

MIT. See `LICENSE`.
