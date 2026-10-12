---
name: kinetic-ui-ux-pro
description: Trigger ONLY for layout, CSS, visual design, frontend components, interaction states, accessibility, motion, design tokens, UI flows, microcopy, responsive behavior, or UI generation/polish, including vague prompts like "make this feel better." Do not trigger for backend-only, data-only, git-only, or documentation-only tasks unless UI guidance is requested. Kinetic UI UX Pro frames intent first, then builds interfaces where motion, state, accessibility, content, tokens, and performance are one system.
---

# Kinetic UI UX Pro for Claude Code

This is the Claude-native wrapper for the Kinetic UI UX Pro repository. The canonical workflow, rules, references, templates, and scripts live at the plugin root.

## Activation

When this skill triggers:

1. Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` completely and treat it as the canonical Kinetic UI UX Pro specification.
2. Apply the canonical instructions, with this Claude path rule: every bundled relative path in the canonical file resolves from `${CLAUDE_PLUGIN_ROOT}`, not from the user's active project.
3. Treat the user's current working directory as the project being designed, audited, or modified unless the user explicitly asks to edit this plugin repository.

## Bundled Paths

Use these path forms in Claude Code:

- References: `${CLAUDE_PLUGIN_ROOT}/references/...`
- Templates: `${CLAUDE_PLUGIN_ROOT}/templates/...`
- Scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/...`
- Requirements: `${CLAUDE_PLUGIN_ROOT}/requirements.txt`
- Receipt template: `${CLAUDE_PLUGIN_ROOT}/templates/receipt.md`

Run bundled scripts by absolute plugin path. Example:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/ast_audit.py" ./src --fail-on ERROR
python "${CLAUDE_PLUGIN_ROOT}/scripts/token_gen.py" "${CLAUDE_PLUGIN_ROOT}/templates/tokens.schema.json" --verify
python "${CLAUDE_PLUGIN_ROOT}/scripts/design_select.py" recommend "internal ops dashboard" --surface dashboard
```

If script dependencies are missing, install from the plugin root requirements file into the active Python environment:

```bash
python -m pip install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"
```

## Non-Negotiables

- Do not duplicate or reinterpret the canonical root `SKILL.md`; load and follow it.
- Do not copy third-party component source into the user's project unless the canonical license and provenance rules allow it.
- Do not invent contrast figures, token values, or audit results; run the bundled scripts where the canonical workflow requires measured output.
- Keep user-project edits in the user's project. Keep plugin edits inside `${CLAUDE_PLUGIN_ROOT}` only when the user explicitly asks to modify the plugin itself.
