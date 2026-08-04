# Host Environments

Output shape must adapt to the host. The same UI answer should not look the
same in a terminal agent, an IDE, a chat artifact, and CI.

## Environments

### CLI agents

Examples: Claude Code, Codex CLI.

Emit file diffs, discrete patches, and concise receipts. Never paste large
inline source dumps when the host can write files. Use workspace-relative paths
in instructions and receipts.

When a file must be created by the user, provide copy-pasteable shell commands:

```sh
mkdir -p src/components
cat > src/components/Modal.tsx <<'EOF'
// file contents
EOF
```

For Windows, include a PowerShell variant:

```powershell
New-Item -ItemType Directory -Force src/components | Out-Null
@'
// file contents
'@ | Set-Content src/components/Modal.tsx
```

### IDE extensions

Emit import-ready modular file trees aligned to the existing project
conventions. Match the framework, file naming, styling approach, token system,
and component boundaries already present.

Prefer multiple small files over one pasted blob when the IDE can apply them.
Show imports exactly as they should appear from the destination file.

### Web and mobile chat

Emit self-contained runnable blocks with zero-config imports and no filesystem
assumptions. The user may have only the message transcript, so the artifact must
stand on its own.

Do not assume a project root, dependency installation, or writable files. In
Claude artifacts, browser storage APIs such as `localStorage` and
`sessionStorage` are unavailable; use in-memory state instead.

### CI and headless

Emit machine-readable output only. Prefer SARIF, JUnit XML, JSON, or stable
line-oriented text over prose.

Use exit codes as the primary signal: `0` for pass, non-zero for blocking
failure. Human explanation belongs in structured fields, logs, or uploaded
artifacts.

## Detection Checklist

Evaluate signals in order:

1. **Filesystem tool present.** If the agent can read or write files, assume a
   CLI-agent or IDE workflow unless stronger signals say otherwise.
2. **`package.json` in context.** If the project manifest is visible, align
   output to that project rather than emitting a generic runnable block.
3. **Request mentions a path.** A path such as `src/App.tsx`,
   `.github/workflows/ui-audit.yml`, or `templates/` means file-aware output is
   expected.
4. **Prior turns show file operations.** If previous messages include patches,
   commits, tests, or file edits, continue in file-aware mode.

If filesystem tools, paths, manifests, or prior file operations exist, use
file-aware output. If none exist and detection is ambiguous, assume chat:
emitting a file tree into a chat is a worse failure than emitting a runnable
block into an IDE.

## Output Matrix

| Environment | Preferred output shape | Path convention | Write files? | Receipt verbosity |
| --- | --- | --- | --- | --- |
| CLI agents | File diffs, patches, short receipts, heredoc creation commands when needed | Workspace-relative paths | Yes, when tools allow; otherwise provide shell and PowerShell creation commands | Concise: files changed, commands run, result |
| IDE extensions | Import-ready modular file tree matching local conventions | Project-relative import paths and existing aliases | Yes, or emit files in apply-ready sections | Moderate: integration notes and changed modules |
| Web and mobile chat | Self-contained runnable block with zero-config imports | No filesystem assumptions | No | Higher: assumptions, usage, and constraints inline |
| CI and headless | SARIF, JUnit XML, JSON, or stable machine text | Repository-relative artifact URIs | Write artifacts only | Minimal: exit code and structured fields over prose |
