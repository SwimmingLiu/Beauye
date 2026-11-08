#!/usr/bin/env python3
"""Portable entry point for Beauye task initialization and evidence checks."""

from __future__ import annotations

import argparse
import json
import sys

from verification import MODES, PHASES, SCHEMA_VERSION, check_task, initialize_task


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = JsonArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    init = subparsers.add_parser("init", help="Create an intentionally incomplete per-task record.")
    init.add_argument("--project", required=True)
    init.add_argument("--task", required=True)
    init.add_argument("--mode", choices=sorted(MODES), required=True)
    init.add_argument("--plan")
    check = subparsers.add_parser("check", help="Check records and freshness without running project commands.")
    check.add_argument("--task-dir", required=True)
    check.add_argument("--phase", choices=sorted(PHASES), required=True)
    try:
        args = parser.parse_args(argv)
        if args.action == "init":
            directory = initialize_task(args.project, args.task, args.mode, args.plan)
            report = {"schema_version": SCHEMA_VERSION, "status": "initialized",
                      "task_dir": str(directory), "message": "Task starts incomplete; prepare its scope and plan."}
            code = 0
        else:
            report = check_task(args.task_dir, args.phase)
            code = report["exit_code"]
    except (ValueError, OSError, TypeError) as exc:
        report = {"schema_version": SCHEMA_VERSION, "status": "needs_work", "exit_code": 2,
                  "error": {"code": "invalid_contract", "message": str(exc)}}
        code = 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
