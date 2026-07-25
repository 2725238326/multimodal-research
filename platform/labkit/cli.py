#!/usr/bin/env python3
"""labkit CLI — register ideas/experiments/runs and run offline analyses.

Runs three ways (all resolve the registry from the package location, not cwd):
    python platform/labkit/cli.py <cmd> ...
    cd platform && python -m labkit.cli <cmd> ...
    PYTHONPATH=platform python -m labkit.cli <cmd> ...

Core commands use the standard library only, so an agent or training script can
log a run without installing anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Bootstrap: ensure platform/ is importable as the parent of the labkit package,
# so `import labkit...` works even when this file is executed directly.
_PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLATFORM_DIR not in sys.path:
    sys.path.insert(0, _PLATFORM_DIR)

from labkit import schema  # noqa: E402
from labkit.store import Store  # noqa: E402


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------- #
# idea
# --------------------------------------------------------------------------- #

def cmd_idea(args, store: Store) -> int:
    if args.action == "list":
        for idea in store.list("ideas"):
            print(f"[{idea.slot:9}] {idea.status:9} {idea.id}  {idea.title}")
        return 0
    if args.action == "show":
        _print(store.load_raw("ideas", args.id))
        return 0
    if args.action == "new":
        idea = schema.Idea(
            id=args.id or schema.content_id("idea", args.title),
            title=args.title,
            slot=args.slot,
            status=args.status,
            thesis=args.thesis or "",
            detail=args.detail or "",
        )
        store.save(idea)
        print(idea.id)
        return 0
    return 2


# --------------------------------------------------------------------------- #
# experiment
# --------------------------------------------------------------------------- #

def cmd_exp(args, store: Store) -> int:
    if args.action == "list":
        for exp in store.list("experiments"):
            print(f"[{exp.track:12}] {exp.status:10} {exp.id}  {exp.title}")
        return 0
    if args.action == "show":
        _print(store.load_raw("experiments", args.id))
        return 0
    if args.action == "new":
        exp = schema.Experiment(
            id=args.id or schema.content_id("exp", args.title),
            title=args.title,
            idea_id=args.idea or "",
            question=args.question or "",
            hypothesis=args.hypothesis or "",
            track=args.track,
            status=args.status,
            primary_metric=args.primary_metric or "",
            go_threshold=args.go or "",
            no_go_threshold=args.no_go or "",
        )
        store.save(exp)
        if exp.idea_id and store.exists("ideas", exp.idea_id):
            store.link_experiment_to_idea(exp.id, exp.idea_id)
        print(exp.id)
        return 0
    return 2


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #

def cmd_run(args, store: Store) -> int:
    if args.action == "list":
        for run in store.list("runs"):
            print(f"[{run.verdict:9}] {run.id}  (exp={run.experiment_id})  {run.title}")
        return 0
    if args.action == "show":
        _print(store.load_raw("runs", args.id))
        return 0
    if args.action == "new":
        run = schema.Run(
            id=args.id or schema.content_id("run", args.title or args.experiment),
            experiment_id=args.experiment,
            title=args.title or "",
            commit=args.commit or "",
            seed=args.seed,
            device=args.device or "",
            command=args.command or "",
        )
        store.save(run)
        if store.exists("experiments", args.experiment):
            store.link_run_to_experiment(run.id, args.experiment)
        print(run.id)
        return 0
    if args.action == "log":
        run = store.load("runs", args.id)
        if args.metric:
            name, _, value = args.metric.partition("=")
            ci = [float(args.ci[0]), float(args.ci[1])] if args.ci else None
            run.metrics[name] = schema.Metric(value=float(value), ci95=ci, unit=args.unit or "")
        store.save(run)
        print(run.id)
        return 0
    if args.action == "verdict":
        run = store.load("runs", args.id)
        run.verdict = args.value
        run.verdict_reason = args.reason or ""
        store.save(run)
        print(f"{run.id}: {run.verdict}")
        return 0
    return 2


# --------------------------------------------------------------------------- #
# analyze / validate / export
# --------------------------------------------------------------------------- #

def cmd_analyze(args, store: Store) -> int:
    if args.which == "flip-identifiability":
        from labkit.analyses import flip_identifiability

        flip_identifiability.main()
        return 0
    print(f"unknown analysis: {args.which}", file=sys.stderr)
    return 2


def cmd_validate(args, store: Store) -> int:
    problems = store.validate_all()
    if not problems:
        counts = {f: len(store.list_raw(f)) for f in store.export()}
        print("registry OK:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        return 0
    print("registry problems:", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    return 1


def cmd_export(args, store: Store) -> int:
    payload = store.export()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="labkit", description="research experiment registry")
    sub = p.add_subparsers(dest="entity", required=True)

    pi = sub.add_parser("idea").add_subparsers(dest="action", required=True)
    for act in ("list",):
        pi.add_parser(act)
    for act in ("show",):
        sp = pi.add_parser(act)
        sp.add_argument("id")
    spn = pi.add_parser("new")
    spn.add_argument("title")
    spn.add_argument("--id")
    spn.add_argument("--slot", default="pool", choices=schema.IDEA_SLOTS)
    spn.add_argument("--status", default="proposed", choices=schema.IDEA_STATUSES)
    spn.add_argument("--thesis")
    spn.add_argument("--detail")

    pe = sub.add_parser("exp").add_subparsers(dest="action", required=True)
    pe.add_parser("list")
    sp = pe.add_parser("show")
    sp.add_argument("id")
    spn = pe.add_parser("new")
    spn.add_argument("title")
    spn.add_argument("--id")
    spn.add_argument("--idea")
    spn.add_argument("--question")
    spn.add_argument("--hypothesis")
    spn.add_argument("--track", default="exploratory", choices=schema.EXPERIMENT_TRACKS)
    spn.add_argument("--status", default="planned", choices=schema.EXPERIMENT_STATUSES)
    spn.add_argument("--primary-metric", dest="primary_metric")
    spn.add_argument("--go")
    spn.add_argument("--no-go", dest="no_go")

    pr = sub.add_parser("run").add_subparsers(dest="action", required=True)
    pr.add_parser("list")
    sp = pr.add_parser("show")
    sp.add_argument("id")
    spn = pr.add_parser("new")
    spn.add_argument("--experiment", required=True)
    spn.add_argument("--id")
    spn.add_argument("--title")
    spn.add_argument("--commit")
    spn.add_argument("--seed", type=int)
    spn.add_argument("--device")
    spn.add_argument("--command")
    spl = pr.add_parser("log")
    spl.add_argument("id")
    spl.add_argument("--metric", help="name=value")
    spl.add_argument("--ci", nargs=2, metavar=("LO", "HI"))
    spl.add_argument("--unit")
    spv = pr.add_parser("verdict")
    spv.add_argument("id")
    spv.add_argument("value", choices=schema.RUN_VERDICTS)
    spv.add_argument("--reason")

    pa = sub.add_parser("analyze")
    pa.add_argument("which")

    sub.add_parser("validate")

    px = sub.add_parser("export")
    px.add_argument("--output", "-o")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store()
    dispatch = {
        "idea": cmd_idea,
        "exp": cmd_exp,
        "run": cmd_run,
        "analyze": cmd_analyze,
        "validate": cmd_validate,
        "export": cmd_export,
    }
    return dispatch[args.entity](args, store)


if __name__ == "__main__":
    raise SystemExit(main())
