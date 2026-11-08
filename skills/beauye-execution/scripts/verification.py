"""Task records and conservative evidence checks; never execute project commands."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = 1
RULE_VERSION = 1
MODES = {"implement", "review", "design"}
PHASES = {"before-write", "after-edit", "delivery"}
SATISFIED = {"passed", "not_applicable"}
ENV_KEYS = ("runtime", "data", "roles")
# Generic output names may also be real source paths (for example src/build).
# Only known technical metadata/caches are ignored throughout the source tree.
EXCLUDED_DIRS = {
    ".git", ".beauye", "node_modules", "__pycache__", ".cache",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
ROOT_GENERATED_DIRS = {
    "dist", "build", "env", "venv", ".env", ".venv", "coverage", ".coverage", "htmlcov",
    ".next", ".nuxt", ".vite", ".svelte-kit", ".astro", ".vercel", ".output",
    ".turbo", ".parcel-cache", ".tox", ".nox",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif"}


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _identifier(value, label):
    _require(
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value) is not None,
        f"{label} must be a safe identifier (letters, digits, '.', '_' or '-'; max 80).",
    )


def _read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON {path}: {exc}") from None
    _require(isinstance(data, dict), f"{path} must contain a JSON object.")
    return data


def _root(path):
    try:
        root = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as exc:
        raise ValueError(f"Cannot resolve project directory: {exc}") from None
    _require(root.is_dir(), f"Project root is not a directory: {root}")
    return root


def snapshot_project(root):
    """Hash sorted paths and contents, including dirty/untracked input files.

    Known metadata/caches are excluded at any depth; conventional output names
    are excluded only at the project root. Links are hashed by target text and
    never traversed, so external targets are not implicitly added to the scope.
    """
    root = _root(root)
    digest = hashlib.sha256(b"beauye-project-v1\0")

    def excluded(path):
        return path.name in EXCLUDED_DIRS or (path.parent == root and path.name in ROOT_GENERATED_DIRS)

    def visit(directory):
        try:
            before = directory.stat()
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
            for path in entries:
                relative = path.relative_to(root).as_posix()
                encoded_name = relative.encode()
                if path.is_symlink():
                    if not excluded(path):
                        target = os.readlink(path).encode()
                        digest.update(b"L" + len(encoded_name).to_bytes(8, "big") + encoded_name)
                        digest.update(len(target).to_bytes(8, "big") + target)
                    continue
                if path.is_dir():
                    if not excluded(path) and not (path / "pyvenv.cfg").is_file():
                        visit(path)
                    continue
                _require(path.is_file(), f"Unsupported project input: {path}")
                initial = path.stat()
                file_digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        file_digest.update(chunk)
                digest.update(b"F" + len(encoded_name).to_bytes(8, "big") + encoded_name)
                digest.update(initial.st_size.to_bytes(8, "big") + file_digest.digest())
                final = path.stat()
                _require(
                    (initial.st_ino, initial.st_size, initial.st_mtime_ns)
                    == (final.st_ino, final.st_size, final.st_mtime_ns),
                    f"Input changed during snapshot; retry: {path}",
                )
            after = directory.stat()
            _require(before.st_mtime_ns == after.st_mtime_ns,
                     f"Directory changed during snapshot; retry: {directory}")
        except (OSError, UnicodeError, RuntimeError) as exc:
            raise ValueError(f"Cannot snapshot {directory}: {exc}") from None

    visit(root)
    return digest.hexdigest()


def _plan_snapshot(task_dir, declared_path):
    """Read plan identity once; an unavailable plan remains a readiness finding."""
    if declared_path is None:
        return {"state": "absent"}, "", "Declare a prepared page plan."
    path = Path(declared_path)
    if not path.is_absolute():
        path = task_dir / path
    try:
        if not path.is_file():
            return {"state": "missing"}, "", f"Prepared page plan is unavailable: {path}"
        content = path.read_bytes()
        text = content.decode("utf-8")
    except (OSError, ValueError) as exc:
        return {"state": "unreadable"}, "", f"Cannot read the prepared page plan: {exc}"
    return {"state": "present", "sha256": hashlib.sha256(content).hexdigest()}, text, None


def _checking_fingerprint(task, project_fingerprint, plan_identity):
    """Bind observations to both actual inputs and the exact checking contract.

    Records live outside the input snapshot; binding their relevant fields here
    prevents a route, scope, role or command change from reusing old observations.
    """
    fields = (
        "schema_version", "task_id", "project_root", "mode", "rule_version", "change_scope",
        "review_scope", "plan_path", "desktop_viewport", "environment", "page_inventory", "project_checks",
    )
    # A path alone misses design-intent edits inside the generated task directory.
    contract = {"task": {field: task[field] for field in fields}, "plan": plan_identity}
    encoded = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(b"beauye-checking-contract-v1\0")
    digest.update(project_fingerprint.encode("ascii") + b"\0" + encoded)
    return digest.hexdigest()


def _discover_checks(root):
    package_path = root / "package.json"
    if not package_path.is_file():
        return []
    package = _read_json(package_path)
    scripts = package.get("scripts", {})
    _require(isinstance(scripts, dict), "package.json scripts must be an object.")
    manager = str(package.get("packageManager", "")).split("@", 1)[0]
    if manager not in {"npm", "pnpm", "yarn", "bun"}:
        manager = "npm"
        for filename, candidate in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
                                    ("bun.lock", "bun"), ("bun.lockb", "bun")):
            if (root / filename).is_file():
                manager = candidate
                break
    names = [name for name in ("lint", "typecheck", "type-check", "check-types", "build", "test")
             if _nonempty(scripts.get(name))]
    aliases = {"typecheck", "type-check", "check-types"}
    selected = []
    for name in names:
        if name in aliases and any(previous in aliases for previous in selected):
            continue
        selected.append(name)
    return [{"id": name, "command": [manager, "run", name], "required": True}
            for name in selected]


def initialize_task(root, task_id, mode, plan_path=None):
    """Create an intentionally incomplete task; never overwrite an existing task."""
    root = _root(root)
    _identifier(task_id, "task_id")
    _require(isinstance(mode, str) and mode in MODES, f"mode must be one of {sorted(MODES)}.")
    supplied_plan = None
    if plan_path is not None:
        try:
            supplied_plan = Path(plan_path).expanduser().resolve(strict=True)
        except (OSError, RuntimeError, TypeError) as exc:
            raise ValueError(f"Cannot resolve plan: {exc}") from None
        _require(supplied_plan.is_file(), f"Plan is not a file: {supplied_plan}")
    checks = _discover_checks(root)
    parent = root
    try:
        for name in (".beauye", "tasks"):
            parent = parent / name
            _require(not parent.is_symlink(), f"Task directory cannot traverse a symlink: {parent}")
            parent.mkdir(exist_ok=True)
        task_dir = parent / task_id
        _require(not task_dir.exists() and not task_dir.is_symlink(),
                 f"Task already exists; choose another id or resume it: {task_dir}")
        task_dir.mkdir()
        (task_dir / "observations").mkdir()
        if supplied_plan is None:
            (task_dir / "plan.md").write_text(
                "<!-- beauye:needs-plan -->\n\nDescribe the page purpose, content relationships, "
                "layout, visual choices, interactions, states and viewport variants.\n",
                encoding="utf-8",
            )
        task = {
            "schema_version": SCHEMA_VERSION, "task_id": task_id, "mode": mode,
            "project_root": str(root), "rule_version": RULE_VERSION,
            "change_scope": {"paths": [], "source": None},
            "review_scope": {"kind": "full", "source": "Beauye default: full page review baseline."},
            "plan_path": str(supplied_plan) if supplied_plan else "plan.md",
            "desktop_viewport": [1440, 900],
            "environment": {key: None for key in ENV_KEYS},
            "page_inventory": {
                "complete": False, "sources": {key: None for key in ("routes", "navigation", "permissions")},
                "pages": [],
            },
            "project_checks": checks,
        }
        (task_dir / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
        return task_dir
    except OSError as exc:
        raise ValueError(f"Cannot initialize task: {exc}") from None


def _strings(value, label, allow_empty=False, unique=True):
    _require(isinstance(value, list) and (allow_empty or bool(value))
             and all(_nonempty(item) for item in value), f"{label} must be a list of nonempty strings.")
    if unique:
        _require(len(value) == len(set(value)), f"{label} contains duplicates.")


def _viewport(value, label):
    _require(isinstance(value, list) and len(value) == 2
             and all(type(item) is int and item > 0 for item in value),
             f"{label} must be [positive width, positive height].")


def _environment(value, label):
    _require(isinstance(value, dict) and all(key in value for key in ENV_KEYS),
             f"{label} must contain runtime, data and roles.")
    _require(all(value[key] is None or isinstance(value[key], str) for key in ENV_KEYS),
             f"{label} values must be strings or null.")


def _validate_task(task):
    required = {"schema_version", "task_id", "mode", "project_root", "rule_version", "change_scope",
                "review_scope", "plan_path", "desktop_viewport", "environment", "page_inventory", "project_checks"}
    _require(required <= task.keys(), f"task.json missing fields: {sorted(required - task.keys())}")
    _require(type(task["schema_version"]) is int and task["schema_version"] == SCHEMA_VERSION,
             "Unsupported task schema_version.")
    _require(type(task["rule_version"]) is int and task["rule_version"] == RULE_VERSION,
             "Unsupported rule_version.")
    _identifier(task["task_id"], "task_id")
    _require(isinstance(task["mode"], str) and task["mode"] in MODES, "Invalid task mode.")
    _require(_nonempty(task["project_root"]) and Path(task["project_root"]).is_absolute(),
             "project_root must be an absolute directory.")
    root = _root(task["project_root"])
    change = task["change_scope"]
    _require(isinstance(change, dict) and {"paths", "source"} <= change.keys(), "Invalid change_scope.")
    _strings(change["paths"], "change_scope.paths", allow_empty=True)
    _require(all(not Path(path).is_absolute() and ".." not in Path(path).parts for path in change["paths"]),
             "change_scope paths must stay relative to the project.")
    _require(change["source"] is None or isinstance(change["source"], str), "Invalid change_scope.source.")
    review = task["review_scope"]
    _require(isinstance(review, dict) and {"kind", "source"} <= review.keys()
             and isinstance(review["kind"], str) and review["kind"] in {"full", "limited"}, "Invalid review_scope.")
    _require(review["source"] is None or isinstance(review["source"], str), "Invalid review_scope.source.")
    _require(task["plan_path"] is None or _nonempty(task["plan_path"]), "Invalid plan_path.")
    _viewport(task["desktop_viewport"], "desktop_viewport")
    _environment(task["environment"], "environment")
    inventory = task["page_inventory"]
    _require(isinstance(inventory, dict) and {"complete", "sources", "pages"} <= inventory.keys()
             and type(inventory["complete"]) is bool, "Invalid page_inventory.")
    _require(isinstance(inventory["sources"], dict)
             and {"routes", "navigation", "permissions"} <= inventory["sources"].keys(),
             "Inventory sources must include routes, navigation and permissions.")
    _require(all(value is None or isinstance(value, str) for value in inventory["sources"].values()),
             "Inventory source notes must be strings or null.")
    _require(isinstance(inventory["pages"], list), "page_inventory.pages must be a list.")
    page_ids = set()
    for page in inventory["pages"]:
        _require(isinstance(page, dict) and {"id", "route", "roles", "affected", "mobile",
                 "screenshot_required", "states", "interactions"} <= page.keys(), "Invalid page record.")
        _require(_nonempty(page["id"]) and page["id"] not in page_ids, "Page ids must be nonempty and unique.")
        page_ids.add(page["id"])
        _require(_nonempty(page["route"]), "Page route must be nonempty.")
        _strings(page["roles"], "page.roles")
        _strings(page["states"], "page.states")
        _require("default" in page["states"], "Every page must include the default state.")
        _strings(page["interactions"], "page.interactions", allow_empty=True)
        _require(all(type(page[key]) is bool for key in ("affected", "mobile", "screenshot_required")),
                 "Page affected/mobile/screenshot_required must be booleans.")
    _require(isinstance(task["project_checks"], list), "project_checks must be a list.")
    check_ids = set()
    for check in task["project_checks"]:
        _require(isinstance(check, dict) and {"id", "command", "required"} <= check.keys(), "Invalid project check.")
        _require(_nonempty(check["id"]) and check["id"] not in check_ids, "Project check ids must be unique.")
        check_ids.add(check["id"])
        _strings(check["command"], "project check command", unique=False)
        _require(type(check["required"]) is bool, "Project check required must be boolean.")
    return root


def _load_observations(task_dir, task):
    observations_dir = task_dir / "observations"
    if not observations_dir.exists():
        return []
    _require(observations_dir.is_dir() and not observations_dir.is_symlink(),
             "observations must be a directory, not a symlink.")
    observations, ids = [], set()
    for path in sorted(observations_dir.glob("*.json")):
        _require(not path.is_symlink(), f"Observation cannot be a symlink: {path}")
        item = _read_json(path)
        fields = {"schema_version", "id", "task_id", "kind", "result", "origin", "fingerprint",
                  "environment", "action", "expected", "actual", "artifacts"}
        _require(fields <= item.keys(), f"{path.name} missing fields: {sorted(fields - item.keys())}")
        _require(type(item["schema_version"]) is int and item["schema_version"] == SCHEMA_VERSION,
                 f"{path.name}: unsupported observation schema_version.")
        _identifier(item["id"], f"{path.name}: observation id")
        _require(item["id"] not in ids, f"Duplicate observation id: {item['id']}")
        ids.add(item["id"])
        _require(item["task_id"] == task["task_id"], f"{path.name}: task_id mismatch.")
        _require(isinstance(item["kind"], str) and item["kind"] in {"visual", "interaction", "project"}, f"{path.name}: invalid observation kind.")
        _require(isinstance(item["result"], str) and item["result"] in {"passed", "issue", "unverified", "not_applicable"},
                 f"{path.name}: invalid result.")
        _require(isinstance(item["origin"], dict) and isinstance(item["origin"].get("kind"), str)
                 and item["origin"]["kind"] in {"tool", "human", "agent"}
                 and _nonempty(item["origin"].get("reference")), f"{path.name}: invalid origin.")
        _require(all(_nonempty(item[key]) for key in ("fingerprint", "action", "expected", "actual")),
                 f"{path.name}: fingerprint, action, expected and actual must be nonempty.")
        _environment(item["environment"], f"{path.name}: environment")
        _strings(item["artifacts"], f"{path.name}: artifacts", allow_empty=True)
        if item["kind"] == "project":
            _require(_nonempty(item.get("check_id")) and type(item.get("exit_code")) is int,
                     f"{path.name}: project requires check_id and integer exit_code.")
            _strings(item.get("command"), f"{path.name}: command", unique=False)
        else:
            subject = item.get("subject")
            _require(isinstance(subject, dict) and all(_nonempty(subject.get(key))
                     for key in ("page_id", "role", "state", "data_condition")),
                     f"{path.name}: invalid page subject.")
            _viewport(subject.get("viewport"), f"{path.name}: viewport")
            if item["kind"] == "interaction":
                page = next((p for p in task["page_inventory"]["pages"] if p["id"] == subject["page_id"]), None)
                _require(page is not None and item.get("check_id") in page["interactions"],
                         f"{path.name}: interaction check_id must be configured for its page.")
        observations.append(item)
    return observations


def _part(value):
    return quote(str(value), safe="-_~.")


def _evidence_requirements(task):
    requirements = []
    for page in task["page_inventory"]["pages"]:
        viewports = [task["desktop_viewport"]]
        if page["affected"]:
            viewports += [[1440, 900], [1280, 800]]
            if page["mobile"]:
                viewports += [[390, 844]]
        viewports = list(dict.fromkeys(tuple(viewport) for viewport in viewports))
        for role in page["roles"]:
            prefix = f"{_part(page['id'])}:{_part(role)}"
            common = {"page_id": page["id"], "role": role, "viewports": viewports, "states": page["states"],
                      "screenshot_required": page["screenshot_required"]}
            for viewport in viewports:
                requirements.append({**common, "id": f"visual:{prefix}:{viewport[0]}x{viewport[1]}:default",
                                     "kind": "visual", "viewport": viewport, "state": "default"})
            for state in page["states"]:
                if state != "default":
                    requirements.append({**common, "id": f"state:{prefix}:{_part(state)}", "kind": "state", "state": state})
            for check_id in page["interactions"]:
                requirements.append({**common, "id": f"interaction:{prefix}:{_part(check_id)}",
                                     "kind": "interaction", "check_id": check_id})
    for check in task["project_checks"]:
        if check["required"]:
            requirements.append({"id": f"project:{_part(check['id'])}", "kind": "project",
                                 "check_id": check["id"], "command": check["command"]})
    return sorted(requirements, key=lambda requirement: requirement["id"])


def _matches(requirement, observation):
    kind = requirement["kind"]
    if kind == "project":
        return observation["kind"] == "project" and observation["check_id"] == requirement["check_id"]
    if observation["kind"] == "project":
        return False
    subject = observation["subject"]
    if subject["page_id"] != requirement["page_id"] or subject["role"] != requirement["role"]:
        return False
    if subject["state"] not in requirement["states"]:
        return False
    if tuple(subject["viewport"]) not in requirement["viewports"]:
        return False
    if kind == "visual":
        return (observation["kind"] == "visual" and subject["state"] == "default"
                and tuple(subject["viewport"]) == requirement["viewport"])
    if kind == "state":
        return subject["state"] == requirement["state"]
    return observation["kind"] == "interaction" and observation["check_id"] == requirement["check_id"]


def _observation_status(item, requirement, task, fingerprint, task_dir):
    if item["fingerprint"] != fingerprint:
        return "stale", "evidence_stale", "Project inputs or the task checking contract changed after this observation."
    if not all(_nonempty(task["environment"][key]) and _nonempty(item["environment"][key]) for key in ENV_KEYS):
        return "unverified", "environment_unknown", "Current or observed runtime/data/roles are unknown."
    if any(task["environment"][key] != item["environment"][key] for key in ENV_KEYS):
        return "stale", "environment_changed", "Observed runtime/data/roles differ from current conditions."
    if item["origin"]["kind"] == "agent":
        return "unverified", "agent_attestation", "Agent attestation cannot count as performed tool or human observation."
    if requirement["kind"] == "project":
        if item["origin"]["kind"] != "tool" or item["command"] != requirement["command"]:
            return "unverified", "project_command_unverified", "Project evidence needs tool origin and the exact configured command."
        if item["exit_code"] != 0:
            return "issue", "observation_issue", "The configured project command exited with a nonzero status."
    if item["result"] == "issue":
        return "issue", "observation_issue", item["actual"]
    if item["result"] == "unverified":
        return "unverified", "observation_unverified", item["actual"]
    artifacts = []
    for artifact in item["artifacts"]:
        path = Path(artifact)
        if not path.is_absolute():
            path = task_dir / path
        try:
            if not path.is_file():
                return "unverified", "artifact_missing", f"Referenced artifact is unavailable: {artifact}"
            with path.open("rb") as stream:
                stream.read(1)
        except OSError:
            return "unverified", "artifact_missing", f"Referenced artifact is unreadable: {artifact}"
        artifacts.append(path)
    if item["result"] == "not_applicable":
        if requirement["kind"] == "visual":
            return "unverified", "default_view_unverified", "A required default page view must actually be observed; N/A cannot satisfy it."
        return "not_applicable", None, item["actual"]
    if requirement["kind"] == "project" and not artifacts:
        return "unverified", "project_log_missing", "Passed project evidence requires an actual log artifact."
    if (item["kind"] == "visual" and requirement.get("screenshot_required")
            and not any(path.suffix.lower() in IMAGE_SUFFIXES for path in artifacts)):
        return "unverified", "screenshot_missing", "This page requires a screenshot artifact for visual evidence."
    return "passed", None, item["actual"]


def check_task(task_dir, phase):
    """Derive readiness from task records and present inputs, without running tools."""
    _require(isinstance(phase, str) and phase in PHASES, f"phase must be one of {sorted(PHASES)}.")
    try:
        task_dir = Path(task_dir).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as exc:
        raise ValueError(f"Cannot resolve task directory: {exc}") from None
    _require(task_dir.is_dir(), "task-dir must be a directory.")
    task = _read_json(task_dir / "task.json")
    root = _validate_task(task)
    project_fingerprint = snapshot_project(root)
    plan_identity, plan_text, plan_problem = _plan_snapshot(task_dir, task["plan_path"])
    fingerprint = _checking_fingerprint(task, project_fingerprint, plan_identity)
    observations = _load_observations(task_dir, task)
    requirements, findings = [], []

    def prerequisite(identifier, passed, message, code, unknown=False):
        status = "passed" if passed else ("unverified" if unknown else "missing")
        requirements.append({"id": identifier, "kind": "precondition", "status": status})
        if not passed:
            findings.append({"code": code, "message": message, "subject": identifier})

    change = task["change_scope"]
    prerequisite("scope:change", _nonempty(change["source"]) and
                 (bool(change["paths"]) or task["mode"] in {"review", "design"}),
                 "Declare intended change paths and their source; review/design may explicitly declare no source changes.",
                 "change_scope_missing")
    review = task["review_scope"]
    explicit = _nonempty(review["source"])
    if explicit and review["kind"] == "limited":
        source = review["source"].lower()
        explicit = any(marker in source for marker in ("user", "explicit", "用户", "明确", "当前请求"))
    prerequisite("scope:review", explicit,
                 "Review scope needs provenance; limited review must explicitly identify the user's limitation.",
                 "review_scope_missing")
    if task["mode"] in {"implement", "design"}:
        prerequisite("plan", bool(plan_text.strip()) and "<!-- beauye:needs-plan -->" not in plan_text,
                     plan_problem or "Prepare a nonempty page plan and remove the needs-plan sentinel.", "plan_missing")
    evidence_requirements = []
    if phase != "before-write" and task["mode"] != "design":
        inventory = task["page_inventory"]
        prerequisite("inventory:complete", inventory["complete"] and bool(inventory["pages"]),
                     "Explicitly complete a nonempty page inventory, including hidden detail/edit pages.",
                     "inventory_incomplete")
        prerequisite("inventory:sources", all(_nonempty(inventory["sources"][key])
                     for key in ("routes", "navigation", "permissions")),
                     "Record how routes, navigation and permissions support the page inventory.", "inventory_sources_missing")
        prerequisite("environment", all(_nonempty(task["environment"][key]) for key in ENV_KEYS),
                     "Declare current runtime, representative data and role conditions.", "environment_unknown", unknown=True)
        evidence_requirements = _evidence_requirements(task)
        rank = {"issue": 0, "passed": 1, "not_applicable": 2, "unverified": 3, "stale": 4}
        for requirement in evidence_requirements:
            matches = [item for item in observations if _matches(requirement, item)]
            classified = [(_observation_status(item, requirement, task, fingerprint, task_dir), item)
                          for item in matches]
            if classified:
                classified.sort(key=lambda pair: (rank[pair[0][0]], pair[1]["id"]))
                (status, code, message), selected = classified[0]
                requirement.update(status=status, evidence=[item["id"] for _, item in classified])
            else:
                status, code, message = "missing", "evidence_missing", "No matching observation has been recorded."
                requirement.update(status=status, evidence=[])
            if status not in SATISFIED:
                findings.append({"code": code, "message": message, "subject": requirement["id"]})
            requirements.append(requirement)
    coverage = {"required": len(evidence_requirements), "passed": 0, "issues": 0, "missing": 0,
                "stale": 0, "unverified": 0, "not_applicable": 0}
    for requirement in evidence_requirements:
        key = "issues" if requirement["status"] == "issue" else requirement["status"]
        coverage[key] += 1
    ready = not findings
    full_review = (ready and phase == "delivery" and task["mode"] != "design"
                   and review["kind"] == "full" and task["page_inventory"]["complete"]
                   and bool(task["page_inventory"]["pages"])
                   and all(item["status"] == "passed" for item in evidence_requirements if item["kind"] == "visual"))
    return {
        "schema_version": SCHEMA_VERSION, "task_id": task["task_id"], "phase": phase,
        "status": "ready" if ready else "needs_work", "fingerprint": fingerprint,
        "project_fingerprint": project_fingerprint,
        "requirements": requirements, "findings": findings, "coverage": coverage,
        "can_claim_full_review": bool(full_review), "exit_code": 0 if ready else 1,
        "limitations": [
            "The checker validates declared source associations, not the authenticity of external tool events or aesthetic judgment.",
            "Whole-project input fingerprints do not independently detect external runtime, data or role changes; declare current environment conditions.",
            "Symlink targets are not traversed; linked external inputs require separate declared conditions and observation.",
        ],
    }
