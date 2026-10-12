#!/usr/bin/env python3
"""Produce designer-facing handoff documents from a Kinetic contract."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from token_gen import STEPS, build_ramps, resolve, verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOKEN_SCHEMA_CANDIDATES = (
    "design-system/tokens.schema.json",
    "design-system/tokens.json",
    "tokens.schema.json",
    "tokens.json",
    "templates/tokens.schema.json",
)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"could not read {path}: {exc}")


def project_root(contract_path: Path) -> Path:
    if contract_path.name == "contract.json" and contract_path.parent.name == "design-system":
        return contract_path.parent.parent
    return Path.cwd()


def find_token_schema(contract: dict, root: Path) -> tuple[Path | None, dict | None]:
    candidates = []
    raw = contract.get("tokens", {}).get("path")
    if raw:
        path = root / raw
        if path.suffix == ".json":
            candidates.append(path)
        candidates.extend([path.with_suffix(".schema.json"), path.parent / "tokens.schema.json"])
    candidates.extend(root / p for p in TOKEN_SCHEMA_CANDIDATES)
    candidates.append(ROOT / "templates" / "tokens.schema.json")
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists() and path.is_file():
            data = load_json(path)
            if isinstance(data, dict) and "palettes" in data and "semantic" in data:
                return path, data
    return None, None


def text(value) -> str:
    if value is None or value == "":
        return "not yet decided"
    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            if key in {"history", "decidedAt"}:
                continue
            parts.append(f"{human(key)}: {text(val)}")
        return "; ".join(parts) if parts else "not yet decided"
    if isinstance(value, list):
        return ", ".join(text(v) for v in value) if value else "none"
    return str(value)


def human(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    value = value.replace("_", " ").replace("-", " ")
    return " ".join(value.split()).capitalize()


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def contrast_summary(schema: dict | None):
    if not schema:
        return [], 0
    ramps = build_ramps(schema.get("palettes", {}))
    rows, failures = verify(schema, ramps)
    return rows, failures


def resolved_semantic(schema: dict | None):
    if not schema:
        return []
    ramps = build_ramps(schema.get("palettes", {}))
    rows = []
    for mode, tokens in schema.get("semantic", {}).items():
        for name, ref in tokens.items():
            try:
                token = resolve(str(ref), ramps)
                rows.append({"mode": mode, "name": name, "ref": ref, "hex": token["hex"]})
            except Exception:
                rows.append({"mode": mode, "name": name, "ref": ref, "hex": "#ffffff"})
    return rows


def type_scale(schema: dict | None):
    ratio = 1.2
    if schema:
        ratio = float(schema.get("iteration", {}).get("typeScaleRatio", ratio))
        ratio = float(schema.get("style", {}).get("constraints", {}).get("type", {}).get("scaleRatio", {}).get("max", ratio))
    base = 16
    names = ["Caption", "Body", "Lead", "Title", "Display"]
    sizes = [round(base * (ratio ** (i - 1)), 1) for i in range(len(names))]
    return list(zip(names, sizes))


def spacing_scale(schema: dict | None):
    space = (schema or {}).get("space", {})
    base = float(space.get("base", 4))
    return [(step, round(step * base, 2)) for step in space.get("steps", [0, 1, 2, 3, 4, 6, 8, 12, 16])]


def radius_tokens(schema: dict | None):
    return (schema or {}).get("radius", {"sm": 4, "md": 8, "lg": 12, "full": 9999})


def shadow_tokens(schema: dict | None):
    shadows = (schema or {}).get("shadow") or (schema or {}).get("shadows") or {}
    if shadows:
        return shadows
    depth = (schema or {}).get("style", {}).get("constraints", {}).get("depth", {}).get("allowedElevationTechniques", [])
    if "shadow" not in depth:
        return {"None": "This direction does not rely on shadows for hierarchy."}
    return {
        "Subtle": "0 8px 24px rgba(15, 23, 42, 0.12)",
        "Raised": "0 16px 48px rgba(15, 23, 42, 0.16)",
    }


def decisions(contract: dict):
    return decision_rows(contract.get("decisions", {}))


def decision_rows(entries: dict):
    out = []
    for key, entry in sorted((entries or {}).items()):
        value = entry.get("value")
        rationale = entry.get("rationale") or "This choice keeps the system consistent."
        out.append({
            "title": human(key),
            "sentence": f"We chose {text(value)} for {human(key).lower()} because {rationale.rstrip('.')}.",
            "date": entry.get("decidedAt", ""),
        })
    return out


def page_overrides(contract: dict):
    out = []
    for page_id, page in sorted((contract.get("pages", {}) or {}).items()):
        rows = decision_rows(page.get("decisions", {}) if isinstance(page, dict) else {})
        if rows:
            out.append({"page": page_id, "decisions": rows})
    return out


def components(contract: dict):
    return contract.get("components", []) or []


def audit_summary(root: Path):
    script = ROOT / "scripts" / "ast_audit.py"
    if not script.exists():
        return "Audit summary is not available yet."
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(root), "--fail-on", "NONE"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except Exception:
        return "Audit summary is not available in this environment."
    text_out = result.stdout + result.stderr
    match = re.search(r"(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\),\s+(\d+)\s+info", text_out)
    if not match:
        return "Audit ran, but the summary could not be read cleanly."
    errors, warnings, info = map(int, match.groups())
    if errors == warnings == info == 0:
        return "The automated audit found no accessibility, layout, or design-system concerns."
    pieces = []
    if errors:
        pieces.append(f"{errors} issue(s) need correction before release")
    if warnings:
        pieces.append(f"{warnings} item(s) should be reviewed")
    if info:
        pieces.append(f"{info} note(s) call for manual confirmation")
    return "The automated audit found " + ", ".join(pieces) + "."


def verification_sentence(rows, failures):
    if not rows:
        return "Contrast verification has not been run because no token schema was found."
    if failures == 0:
        return "All declared text pairs pass AA and the stricter perceptual standard."
    return f"{failures} declared contrast pair(s) need adjustment before the system is ready to hand off."


def build_model(contract_path: Path):
    contract = load_json(contract_path)
    root = project_root(contract_path)
    schema_path, schema = find_token_schema(contract, root)
    contrast_rows, failures = contrast_summary(schema)
    return {
        "contract": contract,
        "root": root,
        "schema_path": schema_path,
        "schema": schema,
        "contrast_rows": contrast_rows,
        "contrast_failures": failures,
        "semantic": resolved_semantic(schema),
        "audit": audit_summary(root),
    }


def html_document(model):
    contract = model["contract"]
    project = contract.get("project", {})
    schema = model["schema"]
    title = project.get("name") or (schema or {}).get("name") or "Design system"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} handoff</title>
<style>
  :root {{ color-scheme: light; --ink:#172033; --muted:#5f6b7a; --line:#d8dee8; --paper:#fff; --soft:#f5f7fa; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--ink); background:var(--paper); }}
  main {{ max-width:1100px; margin:0 auto; padding:48px 28px 72px; }}
  header {{ border-bottom:2px solid var(--ink); padding-bottom:24px; margin-bottom:32px; }}
  h1 {{ font-size:42px; line-height:1.05; margin:0 0 12px; }}
  h2 {{ font-size:24px; margin:40px 0 14px; padding-top:8px; }}
  h3 {{ font-size:18px; margin:22px 0 8px; }}
  p {{ margin:0 0 12px; }}
  .muted {{ color:var(--muted); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }}
  .card {{ border:1px solid var(--line); border-radius:10px; padding:16px; break-inside:avoid; background:#fff; }}
  .swatch {{ height:72px; border:1px solid rgba(0,0,0,.12); border-radius:8px; margin-bottom:10px; }}
  .specimen {{ border-left:4px solid var(--ink); padding:8px 0 8px 14px; margin:10px 0; }}
  .space-row {{ display:flex; align-items:center; gap:12px; margin:8px 0; }}
  .bar {{ height:18px; background:#172033; border-radius:2px; min-width:1px; }}
  .sample {{ width:100%; min-height:64px; background:var(--soft); border:1px solid var(--line); display:grid; place-items:center; }}
  table {{ width:100%; border-collapse:collapse; margin:12px 0 20px; }}
  th,td {{ text-align:left; border-bottom:1px solid var(--line); padding:10px 8px; vertical-align:top; }}
  th {{ font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
  ul {{ padding-left:22px; }}
  @media print {{ body {{ background:white; }} main {{ max-width:none; padding:24px; }} .card {{ break-inside:avoid; }} h2 {{ break-after:avoid; }} }}
</style>
</head>
<body>
<main>
{html_header(title, project, model)}
{html_glance(model)}
{html_decisions(contract)}
{html_page_overrides(contract)}
{html_components(contract)}
{html_rejected(contract)}
{html_verification(model)}
{html_questions(contract)}
</main>
</body>
</html>
"""


def html_header(title, project, model):
    surfaces = ", ".join(project.get("surfaceTypes") or []) or "not yet declared"
    industry = project.get("industryPack") or "not yet applied"
    tokens = model["schema_path"].relative_to(model["root"]) if model["schema_path"] and model["schema_path"].is_relative_to(model["root"]) else model["schema_path"]
    return f"""<header>
  <p class="muted">Designer and stakeholder handoff</p>
  <h1>{esc(title)}</h1>
  <p>Surfaces: {esc(surfaces)}. Industry context: {esc(industry)}.</p>
  <p class="muted">Token source: {esc(tokens or "not found")}</p>
</header>"""


def html_glance(model):
    return f"""<section>
<h2>The System At A Glance</h2>
<h3>Color</h3>
<div class="grid">{''.join(html_swatch(row) for row in model["semantic"])}</div>
<h3>Verified Contrast</h3>
{html_contrast_table(model["contrast_rows"])}
<h3>Type Scale</h3>
{''.join(html_type_specimen(name, size) for name, size in type_scale(model["schema"]))}
<h3>Spacing Scale</h3>
{''.join(html_space(step, value) for step, value in spacing_scale(model["schema"]))}
<h3>Radius And Shadow</h3>
<div class="grid">{html_radius(model["schema"])}{html_shadow(model["schema"])}</div>
</section>"""


def html_swatch(row):
    return f"""<div class="card">
  <div class="swatch" style="background:{esc(row['hex'])}"></div>
  <strong>{esc(human(row['name']))}</strong>
  <p class="muted">{esc(row['mode'])} - {esc(row['ref'])} - {esc(row['hex'])}</p>
</div>"""


def html_contrast_table(rows):
    if not rows:
        return "<p class=\"muted\">No contrast pairs were found in the token schema.</p>"
    trs = []
    for row in rows:
        status = "Passes" if row.get("wcagPass") and row.get("apcaPass") else "Needs work"
        trs.append(
            f"<tr><td>{esc(row.get('mode'))}</td><td>{esc(row.get('pair'))}</td>"
            f"<td>{esc(status)}</td><td>{esc(row.get('wcag'))}:1</td><td>{esc(row.get('apcaLc'))}</td></tr>"
        )
    return "<table><thead><tr><th>Mode</th><th>Pair</th><th>Status</th><th>AA</th><th>Perceptual</th></tr></thead><tbody>" + "".join(trs) + "</tbody></table>"


def html_type_specimen(name, size):
    return f"""<div class="specimen">
  <div class="muted">{esc(name)} - {esc(size)}px</div>
  <div style="font-size:{esc(size)}px">The interface stays legible under real content pressure.</div>
</div>"""


def html_space(step, value):
    width = min(420, max(1, value * 3))
    return f"""<div class="space-row"><code>{esc(step)}</code><div class="bar" style="width:{esc(width)}px"></div><span>{esc(value)}px</span></div>"""


def html_radius(schema):
    cards = []
    for name, value in radius_tokens(schema).items():
        radius = "999px" if str(name) == "full" else f"{value}px"
        cards.append(f"<div class=\"card\"><div class=\"sample\" style=\"border-radius:{esc(radius)}\">{esc(human(name))}</div><p class=\"muted\">{esc(radius)}</p></div>")
    return "".join(cards)


def html_shadow(schema):
    cards = []
    for name, value in shadow_tokens(schema).items():
        shadow = value if str(value).startswith("0 ") else "none"
        cards.append(f"<div class=\"card\"><div class=\"sample\" style=\"box-shadow:{esc(shadow)}\">{esc(human(name))}</div><p class=\"muted\">{esc(value)}</p></div>")
    return "".join(cards)


def html_decisions(contract):
    rows = decisions(contract)
    if not rows:
        return "<section><h2>Decisions And Rationale</h2><p>No decisions have been recorded yet.</p></section>"
    items = "".join(f"<div class=\"card\"><h3>{esc(r['title'])}</h3><p>{esc(r['sentence'])}</p><p class=\"muted\">Decided {esc(r['date'][:10] or 'date not recorded')}</p></div>" for r in rows)
    return f"<section><h2>Decisions And Rationale</h2><div class=\"grid\">{items}</div></section>"


def html_page_overrides(contract):
    pages = page_overrides(contract)
    if not pages:
        return ""
    sections = []
    for page in pages:
        items = "".join(
            f"<li><strong>{esc(row['title'])}</strong>: {esc(row['sentence'])}</li>"
            for row in page["decisions"]
        )
        sections.append(f"<h3>{esc(human(page['page']))}</h3><ul>{items}</ul>")
    return "<section><h2>Page-Specific Overrides</h2>" + "".join(sections) + "</section>"


def html_components(contract):
    comps = components(contract)
    if not comps:
        return "<section><h2>Component Inventory</h2><p>No components have been recorded yet. Use this section to track what exists, which states are covered, and what remains.</p></section>"
    rows = []
    for comp in comps:
        states = comp.get("states") or comp.get("statesCovered") or comp.get("stateCoverage") or []
        remaining = comp.get("remaining") or comp.get("remainingToBuild") or comp.get("todo") or "nothing recorded"
        rows.append(f"<tr><td>{esc(comp.get('name', 'Unnamed component'))}</td><td>{esc(text(states))}</td><td>{esc(text(remaining))}</td></tr>")
    return "<section><h2>Component Inventory</h2><table><thead><tr><th>Component</th><th>States covered</th><th>Still to build</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>"


def html_rejected(contract):
    rejected = contract.get("rejected", []) or []
    if not rejected:
        return "<section><h2>What Was Rejected And Why</h2><p>No rejected directions have been recorded yet.</p></section>"
    items = "".join(f"<li><strong>{esc(item.get('thing', 'Rejected direction'))}</strong>: {esc(item.get('reason', 'No reason recorded'))}</li>" for item in rejected)
    return f"<section><h2>What Was Rejected And Why</h2><ul>{items}</ul></section>"


def html_verification(model):
    sentence = verification_sentence(model["contrast_rows"], model["contrast_failures"])
    return f"""<section>
<h2>Verification Summary</h2>
<p>{esc(sentence)}</p>
<p>{esc(model["audit"])}</p>
</section>"""


def html_questions(contract):
    questions = contract.get("openQuestions", []) or []
    if not questions:
        return "<section><h2>Open Questions</h2><p>No open questions are recorded. The next review can focus on execution and polish.</p></section>"
    items = "".join(f"<li>{esc(q)} <span class=\"muted\">Owner: product/design lead.</span></li>" for q in questions)
    return f"<section><h2>Open Questions</h2><ul>{items}</ul></section>"


def markdown_document(model):
    contract = model["contract"]
    project = contract.get("project", {})
    schema = model["schema"]
    title = project.get("name") or (schema or {}).get("name") or "Design system"
    lines = [f"# {title} Handoff", "", "Designer and stakeholder summary.", ""]
    lines.append("## The System At A Glance")
    lines.append("")
    lines.append("### Color")
    for row in model["semantic"]:
        lines.append(f"- **{human(row['name'])}** ({row['mode']}): `{row['ref']}` / `{row['hex']}`")
    lines.append("")
    lines.append("### Verified Contrast")
    lines.append(verification_sentence(model["contrast_rows"], model["contrast_failures"]))
    for row in model["contrast_rows"]:
        status = "passes" if row.get("wcagPass") and row.get("apcaPass") else "needs work"
        lines.append(f"- {row.get('mode')} {row.get('pair')}: {status} ({row.get('wcag')}:1, perceptual {row.get('apcaLc')})")
    lines.append("")
    lines.append("### Type Scale")
    for name, size in type_scale(model["schema"]):
        lines.append(f"- {name}: {size}px")
    lines.append("")
    lines.append("### Spacing Scale")
    for step, value in spacing_scale(model["schema"]):
        lines.append(f"- Step {step}: {value}px")
    lines.append("")
    lines.append("### Radius And Shadow")
    for name, value in radius_tokens(model["schema"]).items():
        lines.append(f"- Radius {human(name)}: {value}px")
    for name, value in shadow_tokens(model["schema"]).items():
        lines.append(f"- Shadow {human(name)}: {value}")
    lines.extend(["", "## Decisions And Rationale"])
    if decisions(contract):
        for row in decisions(contract):
            lines.append(f"- {row['sentence']}")
    else:
        lines.append("No decisions have been recorded yet.")
    if page_overrides(contract):
        lines.extend(["", "## Page-Specific Overrides"])
        for page in page_overrides(contract):
            lines.extend(["", f"### {human(page['page'])}"])
            for row in page["decisions"]:
                lines.append(f"- {row['sentence']}")
    lines.extend(["", "## Component Inventory"])
    if components(contract):
        for comp in components(contract):
            states = comp.get("states") or comp.get("statesCovered") or comp.get("stateCoverage") or []
            remaining = comp.get("remaining") or comp.get("remainingToBuild") or comp.get("todo") or "nothing recorded"
            lines.append(f"- **{comp.get('name', 'Unnamed component')}**: states covered: {text(states)}; still to build: {text(remaining)}")
    else:
        lines.append("No components have been recorded yet.")
    lines.extend(["", "## What Was Rejected And Why"])
    rejected = contract.get("rejected", []) or []
    if rejected:
        for item in rejected:
            lines.append(f"- **{item.get('thing', 'Rejected direction')}**: {item.get('reason', 'No reason recorded')}")
    else:
        lines.append("No rejected directions have been recorded yet.")
    lines.extend(["", "## Verification Summary", verification_sentence(model["contrast_rows"], model["contrast_failures"]), model["audit"], "", "## Open Questions"])
    questions = contract.get("openQuestions", []) or []
    if questions:
        for q in questions:
            lines.append(f"- {q} Owner: product/design lead.")
    else:
        lines.append("No open questions are recorded.")
    return "\n".join(lines) + "\n"


def command_generate(args):
    contract_path = Path(args.contract)
    model = build_model(contract_path)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.format == "html":
        path = out / "index.html"
        path.write_text(html_document(model), encoding="utf-8")
    else:
        path = out / "handoff.md"
        path.write_text(markdown_document(model), encoding="utf-8")
    print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate handoff HTML or Markdown")
    gen.add_argument("--contract", default="design-system/contract.json")
    gen.add_argument("--out", default="handoff/")
    gen.add_argument("--format", choices=["html", "markdown"], default="html")
    gen.set_defaults(func=command_generate)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
