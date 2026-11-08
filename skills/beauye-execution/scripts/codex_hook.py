#!/usr/bin/env python3
"""Optional Codex adapter; installation and global hook settings stay with the host.

The adapter never executes a tool payload. Stop can request one continuation per
task only when the recorded environment and observation sources support doing so.
Unknown browser/tool availability produces nonblocking context instead.
"""

from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
from typing import Any

from verification import check_task


_SUPPORTED_EVENTS = {"PreToolUse", "PostToolUse", "Stop"}
_WRITE_TOOLS = {"apply_patch", "edit", "write", "multi_edit", "multiedit"}
_SHELL_TOOLS = {"bash", "exec_command", "shell_command", "shell"}
_APP_SUFFIXES = {
    ".astro", ".avif", ".css", ".gif", ".html", ".ico", ".jpeg", ".jpg",
    ".js", ".json", ".jsx", ".less", ".mdx", ".mjs", ".cjs", ".png",
    ".sass", ".scss", ".svelte", ".svg", ".ts", ".tsx", ".vue", ".webp",
    ".yaml", ".yml",
}
_EXCLUDED_DIRS = {".beauye", ".git", "node_modules", "__pycache__"}
_ROOT_OUTPUT_DIRS = {"build", "dist"}
_READ_ONLY_PROGRAMS = {"cat", "head", "tail", "ls", "pwd", "rg", "grep", "find", "wc", "stat", "file"}


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _load_task(task_dir: Path) -> dict[str, Any]:
    task = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    if not isinstance(task, dict):
        raise ValueError("Task metadata must be an object.")
    root = task.get("project_root")
    if not isinstance(root, str) or not Path(root).is_absolute() or not Path(root).is_dir():
        raise ValueError("Task project root is unavailable.")
    return task


def _tool_name(event: dict[str, Any]) -> str:
    name = event.get("tool_name", "")
    if not isinstance(name, str):
        return ""
    return re.split(r"[./:]", name)[-1].lower()


def _event_cwd(event: dict[str, Any], tool_input: Any, root: Path) -> Path:
    cwd = tool_input.get("workdir") if isinstance(tool_input, dict) else None
    if not cwd and isinstance(tool_input, dict):
        cwd = tool_input.get("cwd")
    cwd = cwd or event.get("cwd") or str(root)
    if not isinstance(cwd, str):
        return root
    path = Path(cwd)
    return (path if path.is_absolute() else root / path).resolve()


def _write_paths(tool_input: Any) -> list[str]:
    if isinstance(tool_input, str):
        patch = tool_input
        paths: list[str] = []
    elif isinstance(tool_input, dict):
        paths = [tool_input[key] for key in ("file_path", "path", "filename")
                 if isinstance(tool_input.get(key), str)]
        patch = tool_input.get("patch", tool_input.get("input", ""))
        edits = tool_input.get("edits", [])
        if isinstance(edits, list):
            for edit in edits:
                if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
                    paths.append(edit["file_path"])
    else:
        return []
    if isinstance(patch, str):
        paths.extend(re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", patch, re.MULTILINE))
    return paths


def _app_write(path: Path, root: Path, task_dir: Path) -> bool:
    if not _inside(path, root) or _inside(path, task_dir):
        return False
    relative = path.relative_to(root)
    if any(part in _EXCLUDED_DIRS for part in relative.parts):
        return False
    # Root output directories are generated; src/build and src/dist may be real inputs.
    if relative.parts and relative.parts[0] in _ROOT_OUTPUT_DIRS:
        return False
    return (path.suffix.lower() in _APP_SUFFIXES
            or path.name in {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb"}
            or path.name == ".env" or path.name.startswith(".env."))


def _declared_plan(task: dict[str, Any], task_dir: Path) -> Path | None:
    value = task.get("plan_path")
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else task_dir / path).resolve()


def _matches_scope(path: Path, root: Path, patterns: list[str]) -> bool:
    """Match project-relative scope with explicit, segment-based semantics.

    Literal files match exactly. Existing directories and trailing '/' include
    descendants. '*', '?' and '[]' stay in one segment; '**' spans zero or more.
    """
    parts = path.relative_to(root).parts

    def matches(values: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
        if not pattern:
            return not values
        if pattern[0] == "**":
            return matches(values, pattern[1:]) or bool(values) and matches(values[1:], pattern)
        return bool(values) and fnmatchcase(values[0], pattern[0]) and matches(values[1:], pattern[1:])

    for value in patterns:
        pattern = PurePosixPath(value).parts
        if value.endswith("/") or (root / value).is_dir():
            pattern += ("**",)
        if matches(parts, pattern):
            return True
    return False


def _write_scope_failure(task: dict[str, Any], targets: list[Path]) -> str | None:
    if task["mode"] == "review":
        return "Review mode does not authorize application source writes."
    if task["mode"] == "design":
        return "Design mode authorizes the declared plan and task records; application implementation writes require an implementation task."
    root = Path(task["project_root"]).resolve()
    if not all(_matches_scope(path, root, task["change_scope"]["paths"]) for path in targets):
        return "An application write is outside change_scope.paths. Scope changes require corresponding user authorization."
    return None


def _shell_is_read_only(command: str) -> bool:
    # This narrow allowlist avoids treating a speculative shell parse as enforcement.
    if re.search(r"[;\n|&<>]", command):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    if words and Path(words[0]).name == "rtk":
        words = words[1:]
        if words and words[0] == "proxy":
            words = words[1:]
    if not words:
        return True
    program = Path(words[0]).name
    if program == "find" and any(word in {"-exec", "-execdir", "-delete", "-ok", "-okdir"} for word in words):
        return False
    if program in _READ_ONLY_PROGRAMS:
        return True
    return program == "git" and len(words) > 1 and words[1] in {"status", "diff", "show", "log", "ls-files", "rev-parse"}


def _relevance(event: dict[str, Any], task: dict[str, Any], task_dir: Path) -> tuple[str, list[Path]] | None:
    root = Path(task["project_root"]).resolve()
    tool_input = event.get("tool_input", {})
    cwd = _event_cwd(event, tool_input, root)
    name = _tool_name(event)
    if name in _WRITE_TOOLS:
        targets = []
        plan = _declared_plan(task, task_dir) if task.get("mode") in ("implement", "design") else None
        for value in _write_paths(tool_input):
            path = Path(value)
            path = (path if path.is_absolute() else cwd / path).resolve()
            # Preparing the exact plan must remain possible before its readiness gate.
            if path != plan and _app_write(path, root, task_dir):
                targets.append(path)
        if targets:
            return "write", targets
        return None
    if name not in _SHELL_TOOLS or not _inside(cwd, root) or _inside(cwd, task_dir):
        return None
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command", tool_input.get("cmd"))
    if not isinstance(command, str) or _shell_is_read_only(command):
        return None
    return "shell", []


def _context(event_name: str, message: str) -> dict[str, Any]:
    if event_name in {"PreToolUse", "PostToolUse"}:
        return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
    return {"systemMessage": message}


def _deny_write(message: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                    "permissionDecisionReason": message}}


def _summary(report: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for requirement in report.get("requirements", []):
        if isinstance(requirement, dict):
            status = requirement.get("status")
            if status in {"issue", "missing", "stale", "unverified"}:
                counts[status] = counts.get(status, 0) + 1
    detail = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    return f"Beauye {report.get('phase', 'check')}: {report.get('status', 'unverified')}" + (f" ({detail})." if detail else ".")


def _usable_browser_source(task_dir: Path, task: dict[str, Any]) -> bool:
    environment = task.get("environment")
    if not isinstance(environment, dict) or any(not isinstance(environment.get(key), str) or not environment[key].strip()
                                                for key in ("runtime", "data", "roles")):
        return False
    for path in (task_dir / "observations").glob("*.json"):
        try:
            observation = json.loads(path.read_text(encoding="utf-8"))
            origin = observation.get("origin", {})
            if (observation.get("kind") not in {"visual", "interaction"}
                    or observation.get("result") not in {"passed", "issue"}
                    or not isinstance(origin, dict) or origin.get("kind") not in {"tool", "human"}
                    or not isinstance(origin.get("reference"), str) or not origin["reference"].strip()
                    or observation.get("environment") != environment):
                continue
            if not all(isinstance(observation.get(key), str) and observation[key].strip()
                       for key in ("action", "expected", "actual")):
                continue
            artifacts = observation.get("artifacts", [])
            if not isinstance(artifacts, list):
                continue
            if all(isinstance(value, str) and (Path(value) if Path(value).is_absolute() else task_dir / value).is_file()
                   for value in artifacts):
                return True
        except (OSError, ValueError, AttributeError, TypeError):
            continue
    return False


def _claim_continuation(task_dir: Path) -> bool:
    adapter_dir = task_dir / "adapter"
    try:
        adapter_dir.mkdir(exist_ok=True)
        if adapter_dir.resolve().parent != task_dir.resolve():
            return False
        # A task-wide exclusive marker bounds continuation across changing fingerprints.
        descriptor = os.open(adapter_dir / "stop-continuation-used", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as marker:
            marker.write("One automatic Stop continuation has been requested.\n")
        return True
    except OSError:
        return False


def handle_event(event: Any, task_dir: Path | None) -> dict[str, Any]:
    """Return supported hook JSON without running commands from the event."""
    if not isinstance(event, dict) or task_dir is None:
        return {}
    event_name = event.get("hook_event_name")
    if not isinstance(event_name, str) or event_name not in _SUPPORTED_EVENTS:
        return {}
    if event_name == "Stop" and event.get("stop_hook_active"):
        return {}
    task_dir = task_dir.resolve()
    try:
        task = _load_task(task_dir)
    except (OSError, ValueError):
        return _context(event_name, "Beauye verification is unverified because the task record is unavailable or invalid.")
    try:
        root = Path(task["project_root"]).resolve()
        if event_name == "Stop" and not _inside(_event_cwd(event, {}, root), root):
            return {}
        relevance = None if event_name == "Stop" else _relevance(event, task, task_dir)
    except (OSError, ValueError, RuntimeError):
        # Malformed event paths are not permission to block unrelated host work.
        return {}
    if event_name != "Stop" and relevance is None:
        return {}
    phase = {"PreToolUse": "before-write", "PostToolUse": "after-edit", "Stop": "delivery"}[event_name]
    try:
        report = check_task(task_dir, phase)
    except (OSError, ValueError):
        return _context(event_name, "Beauye verification is unverified because the check could not read a valid task contract.")
    if event_name == "PreToolUse" and relevance is not None and relevance[0] == "write":
        # Readiness alone never authorized the actual paths; every patch target matters.
        scope_failure = _write_scope_failure(task, relevance[1])
        if scope_failure:
            return _deny_write(scope_failure)
    summary = _summary(report)
    if report.get("status") == "ready":
        return {} if event_name != "PostToolUse" else _context(event_name, summary)
    if event_name == "PreToolUse":
        if relevance is not None and relevance[0] == "write":
            return _deny_write(summary + " Prepare the declared scope and page plan, then retry the authorized change.")
        return _context(event_name, summary + " Shell effects are not reliably inferable; no command was executed by this adapter.")
    if event_name == "PostToolUse":
        return _context(event_name, summary + " Recheck affected evidence against the current implementation; this notification does not undo changes.")
    actionable = any(isinstance(item, dict) and item.get("status") in {"missing", "stale", "issue"}
                     for item in report.get("requirements", []))
    feasible = task.get("mode") == "design" or _usable_browser_source(task_dir, task)
    if actionable and feasible and _claim_continuation(task_dir):
        return {"decision": "block", "reason": summary + " Continue the authorized task once to address actionable gaps. Preserve unavailable checks as unverified and do not claim full coverage."}
    return _context(event_name, summary + " Automatic continuation is unavailable or already used; report the remaining gaps with their actual verification status.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", help="Task directory; defaults to BEAUYE_TASK_DIR. Missing configuration is nonblocking.")
    args = parser.parse_args(argv)
    task_value = args.task_dir or os.environ.get("BEAUYE_TASK_DIR")
    try:
        event = json.load(sys.stdin)
    except (OSError, ValueError):
        event = None
    output = handle_event(event, Path(task_value) if task_value else None)
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
