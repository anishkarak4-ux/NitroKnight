"""TaskFactory: seeded repeatable generation, validation filtering, and counterfactual pairing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vtf.families import get_family
from vtf.schema import Difficulty, FamilyName, TaskPackage
from vtf.validator import validate_task


class TaskFactory:
    """Orchestrates deterministic visual task generation and multi-gate validation."""

    def __init__(self, output_dir: Path | str = "outputs/dataset") -> None:
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def generate_one(
        self,
        family_name: FamilyName | str,
        difficulty: Difficulty | str,
        seed: int,
        *,
        max_retries: int = 8,
        forbidden_hashes: set[str] | None = None,
    ) -> tuple[TaskPackage, list[dict[str, Any]]]:
        """Generate and validate a single TaskPackage, retrying deterministically on gate failure."""
        family = get_family(family_name)
        diff = difficulty if isinstance(difficulty, Difficulty) else Difficulty(difficulty)
        rejected_log: list[dict[str, Any]] = []

        for attempt in range(max_retries):
            cur_seed = seed + attempt * 997
            tid = f"{family.family_name.value}_{diff.value}_s{seed}_a{attempt}" if attempt else f"{family.family_name.value}_{diff.value}_s{seed}"
            task = family.build_task(cur_seed, diff, self.images_dir, task_id=tid)
            img_path = self.output_dir / task.image_path
            dup = forbidden_hashes is not None and task.image_sha256 in forbidden_hashes
            report = validate_task(task, family, img_path)
            task.validation = report
            if report.valid and not dup:
                return task, rejected_log
            reasons = list(report.rejection_reasons)
            if dup:
                reasons.append(f"Duplicate image hash {task.image_sha256[:12]}")
            rejected_log.append(
                {
                    "task_id": task.task_id,
                    "seed": cur_seed,
                    "reasons": reasons,
                }
            )
            # Clean up failed candidate PNG
            if img_path.exists():
                img_path.unlink()

        raise RuntimeError(
            f"Failed to generate valid task for {family.family_name.value}/{diff.value} seed={seed}: {rejected_log}"
        )

    def generate_batch(
        self,
        *,
        families: list[FamilyName | str] | None = None,
        difficulties: list[Difficulty | str] | None = None,
        per_cell: int = 2,
        base_seed: int = 100,
        with_counterfactuals: bool = True,
        save_jsonl: bool = True,
    ) -> dict[str, Any]:
        """Generate a balanced, repeatable task suite across families and difficulty tiers."""
        fam_list = [f if isinstance(f, FamilyName) else FamilyName(f) for f in (families or list(FamilyName))]
        diff_list = [d if isinstance(d, Difficulty) else Difficulty(d) for d in (difficulties or list(Difficulty))]

        tasks: list[TaskPackage] = []
        rejected: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        seq = 0
        for fam in fam_list:
            family_impl = get_family(fam)
            for diff in diff_list:
                for idx in range(per_cell):
                    seed = base_seed + seq * 31
                    seq += 1
                    base_task, rej = self.generate_one(fam, diff, seed, forbidden_hashes=seen_hashes)
                    seen_hashes.add(base_task.image_sha256)
                    tasks.append(base_task)
                    rejected.extend(rej)

                    if with_counterfactuals:
                        cf_res = family_impl.make_counterfactual_spec(base_task.ground_truth_spec, seed + 17)
                        if cf_res is not None:
                            twin_spec, delta_desc = cf_res
                            twin_id = f"{base_task.task_id}_cf"
                            twin_task = family_impl.build_task(
                                seed + 17,
                                diff,
                                self.images_dir,
                                task_id=twin_id,
                                spec_override=twin_spec,
                                counterfactual_of=base_task.task_id,
                                counterfactual_delta=delta_desc,
                            )
                            twin_img = self.output_dir / twin_task.image_path
                            twin_report = validate_task(twin_task, family_impl, twin_img)
                            twin_task.validation = twin_report
                            if (
                                twin_report.valid
                                and str(twin_task.answer) != str(base_task.answer)
                                and twin_task.image_sha256 not in seen_hashes
                            ):
                                seen_hashes.add(twin_task.image_sha256)
                                tasks.append(twin_task)
                            else:
                                rej_reasons = list(twin_report.rejection_reasons)
                                if twin_task.image_sha256 in seen_hashes:
                                    rej_reasons.append("Duplicate counterfactual image hash.")
                                rejected.append(
                                    {
                                        "task_id": twin_id,
                                        "seed": seed + 17,
                                        "reasons": rej_reasons or ["Counterfactual answer matched base answer."],
                                    }
                                )
                                if twin_img.exists():
                                    twin_img.unlink()

        if save_jsonl:
            self.save_dataset(tasks, rejected)

        return {
            "output_dir": str(self.output_dir),
            "valid_tasks": len(tasks),
            "rejected_candidates": len(rejected),
            "tasks": tasks,
            "rejected": rejected,
        }

    def save_dataset(self, tasks: list[TaskPackage], rejected: list[dict[str, Any]]) -> None:
        tasks_file = self.output_dir / "tasks.jsonl"
        with tasks_file.open("w", encoding="utf-8") as f:
            for t in tasks:
                f.write(t.model_dump_json() + "\n")

        rej_file = self.output_dir / "rejected_candidates.jsonl"
        with rej_file.open("w", encoding="utf-8") as f:
            for r in rejected:
                f.write(json.dumps(r) + "\n")

        summary = {
            "valid_tasks": len(tasks),
            "rejected_candidates": len(rejected),
            "by_family": {},
            "by_difficulty": {},
            "counterfactual_pairs": sum(1 for t in tasks if t.counterfactual_of is not None),
        }
        for t in tasks:
            summary["by_family"][t.family.value] = summary["by_family"].get(t.family.value, 0) + 1
            summary["by_difficulty"][t.difficulty.value] = summary["by_difficulty"].get(t.difficulty.value, 0) + 1

        (self.output_dir / "dataset_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

    @staticmethod
    def load_tasks(dataset_dir: Path | str) -> list[TaskPackage]:
        tasks_file = Path(dataset_dir) / "tasks.jsonl"
        if not tasks_file.exists():
            return []
        tasks: list[TaskPackage] = []
        with tasks_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    tasks.append(TaskPackage.model_validate_json(line))
        return tasks
