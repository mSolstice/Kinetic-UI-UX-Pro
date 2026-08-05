#!/usr/bin/env python3
"""Record and apply cross-project Kinetic taste preferences."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_GEN = ROOT / "scripts" / "token_gen.py"
DEFAULT_PATH = Path.home() / ".kinetic-ux" / "taste.json"
NEVER_OVERRIDE = [
    "contrast",
    "touch targets",
    "focus visibility",
    "reduced-motion support",
]
REVEALED_ACCEPT_WEIGHT = 0.25
REVEALED_REJECT_WEIGHT = 0.35
STATED_WEIGHT = 0.10
DECAY_DAYS = 90

KNOWN_ALIASES = {
    "glassmorphism": "glass",
    "glass morphism": "glass",
    "glass-layered": "glass",
    "neumorphism": "neumorphic",
    "soft-neumorphic": "neumorphic",
    "purple gradient": "purple",
    "purple-blue gradient": "purple",
    "dense layouts": "dense",
    "density": "dense",
    "compact": "dense",
    "airy layout": "airy",
    "breathing room": "airy",
    "minimalism": "minimal",
}

PREFERENCE_OPS = {
    "prefer dense": {"space": 0.9, "note": "Starting denser than default based on taste memory - say the word if that is wrong here."},
    "avoid dense": {"space": 1.08, "note": "Starting less dense than default based on taste memory - say the word if that is wrong here."},
    "prefer airy": {"space": 1.12, "note": "Starting with more breathing room based on taste memory - say the word if that is wrong here."},
    "avoid airy": {"space": 0.94, "note": "Starting more compact than airy defaults based on taste memory - say the word if that is wrong here."},
    "prefer minimal": {"brandChroma": 0.9, "duration": 0.92, "note": "Keeping the direction quieter based on taste memory - say the word if that is wrong here."},
    "avoid minimal": {"brandChroma": 1.08, "note": "Allowing more visual character based on taste memory - say the word if that is wrong here."},
    "prefer purple": {"brandHue": 270, "note": "Allowing purple because taste memory supports it - say the word if that is wrong here."},
    "avoid purple": {"avoidHue": (250, 290, 214), "note": "Steering away from purple based on taste memory - say the word if that is wrong here."},
    "prefer glass": {"addTag": "taste-prefers-glass", "note": "Glass treatment is allowed by taste memory, but contrast and reduced-transparency still decide."},
    "avoid glass": {"addProhibition": "no-glassmorphism", "note": "Avoiding glassmorphism based on taste memory - say the word if that is wrong here."},
    "prefer neumorphic": {"addTag": "taste-prefers-neumorphic", "note": "Neumorphic treatment is allowed by taste memory, but depth cannot carry meaning alone."},
    "avoid neumorphic": {"addProhibition": "no-neumorphic-depth-cues", "note": "Avoiding neumorphic depth cues based on taste memory - say the word if that is wrong here."},
    "prefer rounded": {"radius": 1.12, "note": "Starting slightly rounder based on taste memory - say the word if that is wrong here."},
    "avoid rounded": {"radius": 0.88, "note": "Starting with sharper shapes based on taste memory - say the word if that is wrong here."},
    "prefer motion": {"duration": 1.08, "note": "Allowing a little more responsive motion based on taste memory; reduced-motion remains fixed."},
    "avoid motion": {"duration": 0.78, "note": "Starting with quieter motion based on taste memory; reduced-motion remains fixed."},
}


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def now_iso():
    return now().isoformat()


def memory_path():
    override = os.environ.get("KINETIC_TASTE_PATH")
    return Path(override).expanduser() if override else DEFAULT_PATH


def load_memory():
    path = memory_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"version": 1, "preferences": []}
    except Exception as exc:
        raise SystemExit(f"could not read {path}: {exc}")
    data.setdefault("version", 1)
    data.setdefault("preferences", [])
    apply_decay(data)
    return data


def save_memory(data):
    path = memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return now()


def apply_decay(data):
    current = now()
    for pref in data.get("preferences", []):
        last = parse_time(pref.get("lastSeen"))
        periods = int(max(0, (current - last).days) // DECAY_DAYS)
        applied = int(pref.get("decayPeriodsApplied", 0))
        pending = max(0, periods - applied)
        if pending:
            pref["confidence"] = round(float(pref.get("confidence", 0)) * (0.5 ** pending), 4)
            pref["decayPeriodsApplied"] = applied + pending


def slug(value):
    return " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())


def canonical_thing(thing):
    low = slug(thing)
    for key, value in KNOWN_ALIASES.items():
        if key in low:
            return value
    words = [w for w in low.split() if w not in {"more", "less", "very", "style", "layout", "ui"}]
    return " ".join(words[:3]) or low


def preference_for(action, thing):
    canonical = canonical_thing(thing)
    polarity = "prefer" if action == "accepted" else "avoid"
    return f"{polarity} {canonical}"


def opposite(preference):
    if preference.startswith("prefer "):
        return "avoid " + preference[len("prefer "):]
    if preference.startswith("avoid "):
        return "prefer " + preference[len("avoid "):]
    return ""


def project_name(args_project):
    if args_project:
        return args_project
    package = Path("package.json")
    if package.exists():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            if data.get("name"):
                return str(data["name"])
        except Exception:
            pass
    return Path.cwd().name


def entry_index(data, preference):
    for i, item in enumerate(data["preferences"]):
        if item.get("preference") == preference:
            return i
    return -1


def observe(data, preference, evidence, weight):
    idx = entry_index(data, preference)
    if idx < 0:
        data["preferences"].append({
            "preference": preference,
            "evidence": [],
            "observationCount": 0,
            "confidence": 0.0,
            "lastSeen": now_iso(),
            "kind": evidence["kind"],
            "decayPeriodsApplied": 0,
        })
        idx = len(data["preferences"]) - 1
    item = data["preferences"][idx]
    item["evidence"].append(evidence)
    item["observationCount"] = int(item.get("observationCount", 0)) + 1
    item["confidence"] = round(min(0.95, float(item.get("confidence", 0)) + weight), 4)
    item["lastSeen"] = evidence["at"]
    item["kind"] = strongest_kind(item.get("kind"), evidence["kind"])
    item["decayPeriodsApplied"] = 0

    counter = opposite(preference)
    cidx = entry_index(data, counter)
    if cidx >= 0:
        c = data["preferences"][cidx]
        c["confidence"] = round(max(0.0, float(c.get("confidence", 0)) - weight * 0.7), 4)
        c.setdefault("evidence", []).append(dict(evidence, counterExampleFor=preference))
        c["lastSeen"] = evidence["at"]


def strongest_kind(existing, new):
    return "revealed" if "revealed" in {existing, new} else "stated"


def cmd_observe(args):
    if bool(args.accepted) == bool(args.rejected):
        raise SystemExit("observe requires exactly one of --accepted or --rejected")
    data = load_memory()
    action = "accepted" if args.accepted else "rejected"
    thing = args.accepted or args.rejected
    kind = "stated" if args.stated else "revealed"
    weight = STATED_WEIGHT if args.stated else (REVEALED_ACCEPT_WEIGHT if action == "accepted" else REVEALED_REJECT_WEIGHT)
    preference = preference_for(action, thing)
    evidence = {
        "project": project_name(args.project),
        "action": action,
        "thing": thing,
        "reason": args.reason or "",
        "kind": kind,
        "at": now_iso(),
    }
    observe(data, preference, evidence, weight)
    save_memory(data)
    label = f"{preference} ({kind})"
    print(f"recorded {label} in {memory_path()}")


def sorted_preferences(data, include_weak=False):
    prefs = [p for p in data.get("preferences", []) if include_weak or float(p.get("confidence", 0)) > 0.02]
    return sorted(prefs, key=lambda p: (-float(p.get("confidence", 0)), p.get("preference", "")))


def cmd_profile(args):
    if args.no_memory:
        print("Taste memory disabled by --no-memory.")
        return
    data = load_memory()
    save_memory(data)
    prefs = sorted_preferences(data, args.include_weak)
    print(f"Taste memory: {memory_path()}")
    if not prefs:
        print("No active preferences recorded.")
        return
    print("| Preference | Kind | Confidence | Observations | Last seen | Evidence |")
    print("|---|---|---:|---:|---|---|")
    for p in prefs:
        ev = p.get("evidence", [])[-1] if p.get("evidence") else {}
        evidence = f"{ev.get('project', '')}: {ev.get('action', '')} {ev.get('thing', '')}"
        print(f"| {p['preference']} | {p.get('kind', 'revealed')} | {float(p.get('confidence', 0)):.2f} | {p.get('observationCount', 0)} | {p.get('lastSeen', '')[:10]} | {evidence} |")


def load_schema(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"could not read schema {path}: {exc}")
    if "palettes" not in data or "semantic" not in data:
        raise SystemExit(f"{path} does not look like a token schema")
    return data


def clamp(value, low, high):
    return max(low, min(high, value))


def apply_ops(schema, ops):
    changes = []
    palettes = schema.setdefault("palettes", {})
    if "space" in ops:
        space = schema.setdefault("space", {"base": 4})
        before = space.get("base", 4)
        after = round(clamp(float(before) * ops["space"], 1, 12), 3)
        space["base"] = after
        changes.append(("space.base", before, after))
    if "brandChroma" in ops and "brand" in palettes:
        before = palettes["brand"].get("chroma", 0)
        after = round(clamp(float(before) * ops["brandChroma"], 0.001, 0.32), 4)
        palettes["brand"]["chroma"] = after
        changes.append(("palettes.brand.chroma", before, after))
    if "duration" in ops:
        durations = schema.setdefault("motion", {}).setdefault("durations", {})
        for key, before in list(durations.items()):
            after = int(round(clamp(float(before) * ops["duration"], 50, 900)))
            if key == "reduced":
                after = min(after, 100)
            durations[key] = after
            changes.append((f"motion.durations.{key}", before, after))
    if "radius" in ops:
        for key, before in list(schema.setdefault("radius", {}).items()):
            if key == "full":
                continue
            after = int(round(clamp(float(before) * ops["radius"], 0, 32)))
            schema["radius"][key] = after
            changes.append((f"radius.{key}", before, after))
    if "brandHue" in ops and "brand" in palettes:
        before = palettes["brand"].get("hue", 0)
        after = ops["brandHue"]
        palettes["brand"]["hue"] = after
        changes.append(("palettes.brand.hue", before, after))
    if "avoidHue" in ops and "brand" in palettes:
        low, high, target = ops["avoidHue"]
        before = float(palettes["brand"].get("hue", 0)) % 360
        if low <= before <= high:
            palettes["brand"]["hue"] = target
            changes.append(("palettes.brand.hue", before, target))
    if "addProhibition" in ops:
        style = schema.setdefault("style", {})
        constraints = style.setdefault("constraints", {})
        prohibitions = constraints.setdefault("prohibitions", [])
        if ops["addProhibition"] not in prohibitions:
            prohibitions.append(ops["addProhibition"])
            changes.append(("style.constraints.prohibitions", "", ops["addProhibition"]))
    if "addTag" in ops:
        tags = schema.setdefault("tasteMemory", {}).setdefault("tags", [])
        if ops["addTag"] not in tags:
            tags.append(ops["addTag"])
            changes.append(("tasteMemory.tags", "", ops["addTag"]))
    return changes


def verify_schema(schema):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
        tmp = Path(f.name)
    try:
        return subprocess.run(
            [sys.executable, str(TOKEN_GEN), str(tmp), "--verify"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def active_ops(preferences):
    selected = []
    for pref in preferences:
        confidence = float(pref.get("confidence", 0))
        if confidence < 0.25:
            continue
        ops = PREFERENCE_OPS.get(pref.get("preference"))
        if ops:
            selected.append((confidence, pref, ops))
    return sorted(selected, key=lambda row: (-row[0], row[1]["preference"]))[:5]


def cmd_apply(args):
    schema = load_schema(args.to)
    if args.no_memory:
        print("Taste memory disabled by --no-memory.")
        emit_schema(schema, args.out)
        return
    data = load_memory()
    save_memory(data)
    selected = active_ops(sorted_preferences(data))
    if args.explicit_request:
        kept = []
        skipped = []
        for confidence, pref, ops in selected:
            if conflicts_with_current_request(pref["preference"], args.explicit_request):
                skipped.append(pref["preference"])
                evidence = {
                    "project": project_name(args.project),
                    "action": "accepted",
                    "thing": args.explicit_request,
                    "reason": "Current explicit request overrode taste memory",
                    "kind": "revealed",
                    "at": now_iso(),
                }
                observe(data, opposite(pref["preference"]), evidence, REVEALED_ACCEPT_WEIGHT)
            else:
                kept.append((confidence, pref, ops))
        if skipped:
            save_memory(data)
            print("Taste memory skipped because the current request is explicit: " + ", ".join(skipped))
        selected = kept
    if not selected:
        print("Taste memory: no active preferences above confidence threshold; schema unchanged.")
        emit_schema(schema, args.out)
        return
    base = copy.deepcopy(schema)
    updated = copy.deepcopy(schema)
    all_changes = []
    notes = []
    applied = []
    for _confidence, pref, ops in selected:
        changes = apply_ops(updated, ops)
        if changes:
            all_changes.extend(changes)
            notes.append(ops["note"])
            applied.append(pref["preference"])
    if not all_changes:
        print("Taste memory: active preferences did not map to this schema; schema unchanged.")
        emit_schema(schema, args.out)
        return
    result = verify_schema(updated)
    if result.returncode != 0:
        print("Taste memory rejected: applying preferences would break token verification.")
        print("Non-negotiables preserved: " + ", ".join(NEVER_OVERRIDE))
        print(result.stdout or result.stderr)
        raise SystemExit(1)
    updated.setdefault("tasteMemory", {})["applied"] = {
        "preferences": applied,
        "source": str(memory_path()),
        "appliedAt": now_iso(),
        "nonNegotiables": NEVER_OVERRIDE,
    }
    print(notes[0])
    print("Taste memory applied: " + ", ".join(applied))
    print("Non-negotiables preserved: " + ", ".join(NEVER_OVERRIDE))
    print_change_table(all_changes)
    emit_schema(updated, args.out)
    _ = base


def emit_schema(schema, out):
    if out:
        Path(out).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote: {out}")
    else:
        print("\n```json")
        print(json.dumps(schema, indent=2))
        print("```")


def conflicts_with_current_request(preference, request):
    request = slug(request)
    if not request:
        return False
    parts = preference.split(maxsplit=1)
    if len(parts) != 2:
        return False
    polarity, term = parts
    term = slug(term)
    if term not in request:
        return False
    if polarity == "avoid":
        return True
    negative_markers = (f"avoid {term}", f"no {term}", f"not {term}", f"without {term}", f"less {term}")
    return any(marker in request for marker in negative_markers)


def print_change_table(changes):
    print("\n| Parameter | Before | After |")
    print("|---|---:|---:|")
    for path, before, after in changes:
        print(f"| `{path}` | `{before}` | `{after}` |")


def cmd_forget(args):
    data = load_memory()
    wanted = slug(args.preference)
    before = len(data.get("preferences", []))
    data["preferences"] = [
        p for p in data.get("preferences", [])
        if slug(p.get("preference", "")) != wanted and slug(p.get("preference", "")).replace("prefer ", "").replace("avoid ", "") != wanted
    ]
    removed = before - len(data["preferences"])
    save_memory(data)
    print(f"removed {removed} preference(s) from {memory_path()}")


def cmd_explain(args):
    if args.no_memory:
        print("Taste memory disabled by --no-memory.")
        return
    data = load_memory()
    save_memory(data)
    wanted = slug(args.preference)
    matches = [
        p for p in data.get("preferences", [])
        if wanted in slug(p.get("preference", "")) or wanted == slug(p.get("preference", "")).replace("prefer ", "").replace("avoid ", "")
    ]
    if not matches:
        raise SystemExit(f"no preference found for {args.preference!r}")
    for p in sorted_preferences({"preferences": matches}, include_weak=True):
        print(f"{p['preference']} ({p.get('kind', 'revealed')}) confidence={float(p.get('confidence', 0)):.2f} observations={p.get('observationCount', 0)}")
        for ev in p.get("evidence", []):
            counter = f" counter-example for {ev['counterExampleFor']}" if ev.get("counterExampleFor") else ""
            reason = f" - {ev['reason']}" if ev.get("reason") else ""
            print(f"- {ev.get('at', '')[:10]} {ev.get('project', '')}: {ev.get('action', '')} {ev.get('thing', '')} ({ev.get('kind', '')}){counter}{reason}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    observe_cmd = sub.add_parser("observe", help="record an accepted or rejected taste signal")
    observe_cmd.add_argument("--accepted")
    observe_cmd.add_argument("--rejected")
    observe_cmd.add_argument("--reason")
    observe_cmd.add_argument("--project")
    observe_cmd.add_argument("--stated", action="store_true", help="mark as a stated preference; default is revealed behavior")
    observe_cmd.set_defaults(func=cmd_observe)

    profile_cmd = sub.add_parser("profile", help="print current taste profile sorted by confidence")
    profile_cmd.add_argument("--include-weak", action="store_true")
    profile_cmd.add_argument("--no-memory", action="store_true", help="disable reading taste memory")
    profile_cmd.set_defaults(func=cmd_profile)

    apply_cmd = sub.add_parser("apply", help="bias a token schema toward the taste profile")
    apply_cmd.add_argument("--to", required=True, help="token schema JSON to bias")
    apply_cmd.add_argument("--out", help="write the biased schema instead of only printing it")
    apply_cmd.add_argument("--no-memory", action="store_true", help="disable reading taste memory and leave the schema unchanged")
    apply_cmd.add_argument("--explicit-request", help="current user request; conflicting memory is skipped and recorded as a counter-example")
    apply_cmd.add_argument("--project", help="project name for counter-example evidence")
    apply_cmd.set_defaults(func=cmd_apply)

    forget_cmd = sub.add_parser("forget", help="remove a remembered preference")
    forget_cmd.add_argument("preference")
    forget_cmd.set_defaults(func=cmd_forget)

    explain_cmd = sub.add_parser("explain", help="show the evidence trail for a preference")
    explain_cmd.add_argument("preference")
    explain_cmd.add_argument("--no-memory", action="store_true", help="disable reading taste memory")
    explain_cmd.set_defaults(func=cmd_explain)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
