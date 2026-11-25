"""Command-line interface for Visual Task Factory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from vtf.benchmark import run_benchmark
from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.mutation import run_mutation_suite, save_mutation_report
from vtf.validator import validate_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vtf",
        description="Visual Task Factory — generate, validate, and benchmark visual AI tasks.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="Generate a validated visual task dataset")
    p_gen.add_argument("--out", default="outputs/demo_suite", help="Output dataset directory")
    p_gen.add_argument("--per-cell", type=int, default=2, help="Tasks per (family x difficulty)")
    p_gen.add_argument("--seed", type=int, default=42, help="Base deterministic random seed")
    p_gen.add_argument(
        "--families",
        default="charts,spatial_inventory,logic_circuits,structured_docs,blueprints_gauges",
        help="Comma-separated families",
    )
    p_gen.add_argument("--no-counterfactuals", action="store_true", help="Disable twin pairs")

    p_val = sub.add_parser("validate", help="Re-run 5-gate validation on an existing dataset")
    p_val.add_argument("--dataset", default="outputs/demo_suite", help="Dataset directory")

    p_eval = sub.add_parser("evaluate", help="Benchmark VLM(s) and/or baselines on a dataset")
    p_eval.add_argument("--dataset", default="outputs/demo_suite", help="Dataset directory")
    p_eval.add_argument(
        "--models",
        default="blind_prior,pixel_heuristic,oracle",
        help="Comma-separated evaluator specs (e.g. gemini:gemini-3.5-flash-lite,ollama_blind:mistral:latest)",
    )
    p_eval.add_argument("--limit", type=int, default=None, help="Optional max tasks to evaluate")
    p_eval.add_argument("--no-cache", action="store_true", help="Ignore prediction cache")
    p_eval.add_argument("--verbose", action="store_true", help="Print per-task progress")

    p_blind = sub.add_parser("audit-blind", help="Run real text-only LLM anti-shortcut audit (no images)")
    p_blind.add_argument("--dataset", default="outputs/demo_suite", help="Dataset directory")
    p_blind.add_argument("--model", default="mistral:latest", help="Local Ollama model name")
    p_blind.add_argument("--limit", type=int, default=None, help="Optional max tasks")

    p_srv = sub.add_parser("serve", help="Launch interactive Visual Task Factory Studio UI")
    p_srv.add_argument("--dataset", default="outputs/demo_suite", help="Default dataset directory")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8000)

    p_mut = sub.add_parser("mutate", help="Run mutation testing to verify validator fault detection")
    p_mut.add_argument("--out", default=None, help="Optional JSON file path to save mutation report")

    args = parser.parse_args(argv)

    if args.cmd == "generate":
        fams = [f.strip() for f in args.families.split(",") if f.strip()]
        factory = TaskFactory(args.out)
        res = factory.generate_batch(
            families=fams,
            per_cell=args.per_cell,
            base_seed=args.seed,
            with_counterfactuals=not args.no_counterfactuals,
        )
        print(
            json.dumps(
                {
                    "output_dir": res["output_dir"],
                    "valid_tasks": res["valid_tasks"],
                    "rejected_candidates": res["rejected_candidates"],
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "validate":
        ds_dir = Path(args.dataset)
        tasks = TaskFactory.load_tasks(ds_dir)
        passed = 0
        failed = 0
        for t in tasks:
            rep = validate_task(t, get_family(t.family), ds_dir / t.image_path)
            if rep.valid:
                passed += 1
            else:
                failed += 1
                print(f"INVALID {t.task_id}: {rep.rejection_reasons}")
        print(json.dumps({"total": len(tasks), "passed": passed, "failed": failed}, indent=2))
        return 0 if failed == 0 else 1

    if args.cmd == "evaluate":
        specs = [m.strip() for m in args.models.split(",") if m.strip()]
        summary = run_benchmark(
            args.dataset,
            specs,
            limit=args.limit,
            verbose=args.verbose,
            use_cache=not args.no_cache,
        )
        print(
            json.dumps(
                {
                    "valid_tasks": summary.valid_tasks,
                    "overall_accuracy": summary.overall_accuracy,
                    "counterfactual_consistency": summary.counterfactual_consistency,
                    "hallucination_rate": summary.hallucination_rate,
                    "report_markdown": str(Path(args.dataset) / "benchmark_report.md"),
                    "report_html": str(Path(args.dataset) / "benchmark_report.html"),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "audit-blind":
        summary = run_benchmark(
            args.dataset,
            [f"ollama_blind:{args.model}"],
            limit=args.limit,
            verbose=True,
        )
        print(json.dumps({"blind_llm_accuracy": summary.overall_accuracy}, indent=2))
        return 0

    if args.cmd == "serve":
        import os

        os.environ["VTF_DATASET_DIR"] = str(Path(args.dataset).resolve())
        uvicorn.run("vtf.server:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.cmd == "mutate":
        rep = save_mutation_report(args.out) if args.out else run_mutation_suite()
        print(json.dumps(rep, indent=2))
        return 0 if rep["all_killed"] else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
