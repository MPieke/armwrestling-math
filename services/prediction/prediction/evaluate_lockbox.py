"""Operator CLI for consulting a lockbox protocol.

The lockbox is a scarce, non-renewable-within-a-session resource: each call
either records one more consultation against it (the ordinary run_baseline
machinery, applied to a lockbox protocol_id) or, with --dry-run, proves
every guard passes and shows what would be evaluated without spending one.
Refuses outright on a dirty working tree -- stricter than the ordinary dev
path, which merely records git_dirty and lets a human judge later. Spending
a lockbox consultation on an unreproducible run is a worse mistake than
flagging one after the fact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import psycopg

from prediction import db, elo
from prediction.run_baseline import DEFAULT_REPO_ROOT, get_git_info, run_baseline


def evaluate_lockbox(
    connection: psycopg.Connection,
    protocol_name: str,
    *,
    model_family: str = "elo",
    k_factor: float = elo.DEFAULT_K_FACTOR,
    seed: int = 0,
    feature_schema: str = "outcomes_elo_v1",
    dry_run: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
) -> dict[str, Any]:
    _, git_dirty = get_git_info(repo_root)
    if git_dirty:
        raise RuntimeError(
            "refusing to evaluate a lockbox from a dirty working tree -- "
            "commit or stash first; a lockbox consultation must be reproducible"
        )

    protocol_id, kind = _load_protocol(connection, protocol_name)
    if not kind.startswith("lockbox"):
        raise ValueError(f"protocol {protocol_name!r} is kind {kind!r}, not a lockbox")

    consultations_before = _consultation_count(connection, protocol_id)
    train_count, test_count = _fold_membership_counts(connection, protocol_id)
    result: dict[str, Any] = {
        "protocol_id": protocol_id,
        "protocol_name": protocol_name,
        "protocol_kind": kind,
        "train_match_count": train_count,
        "test_match_count": test_count,
        "consultations_before": consultations_before,
        "dry_run": dry_run,
        "run_id": None,
        "consultations_after": consultations_before,
    }
    if dry_run:
        return result

    run_id = run_baseline(
        connection,
        protocol_id,
        model_family=model_family,
        k_factor=k_factor,
        seed=seed,
        feature_schema=feature_schema,
        repo_root=repo_root,
    )
    result["run_id"] = run_id
    result["consultations_after"] = consultations_before + 1
    return result


def _load_protocol(connection: psycopg.Connection, protocol_name: str) -> tuple[int, str]:
    with connection.cursor() as cursor:
        cursor.execute("select id, kind from eval_protocols where name = %s", (protocol_name,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"unknown protocol {protocol_name!r}")
    return row[0], row[1]


def _consultation_count(connection: psycopg.Connection, protocol_id: int) -> int:
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from experiment_runs where protocol_id = %s", (protocol_id,))
        return cursor.fetchone()[0]


def _fold_membership_counts(connection: psycopg.Connection, protocol_id: int) -> tuple[int, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select coalesce(sum(array_length(train_match_ids, 1)), 0),
                   coalesce(sum(array_length(test_match_ids, 1)), 0)
            from eval_folds where protocol_id = %s
            """,
            (protocol_id,),
        )
        return cursor.fetchone()


def render_evaluation(result: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True, default=str)
    if output_format == "text":
        lines = [
            f"protocol {result['protocol_name']!r} ({result['protocol_kind']}): "
            f"{result['train_match_count']} train / {result['test_match_count']} test matches",
            f"consultations before: {result['consultations_before']}",
        ]
        if result["dry_run"]:
            lines.append("dry run: no run recorded, no consultation spent")
        else:
            lines.append(f"run {result['run_id']} completed")
            lines.append(f"consultations after: {result['consultations_after']}")
        return "\n".join(lines)
    raise ValueError(f"unsupported format {output_format!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate a model against a lockbox protocol.")
    parser.add_argument("--protocol-name", required=True)
    parser.add_argument("--model-family", default="elo")
    parser.add_argument("--k-factor", type=float, default=elo.DEFAULT_K_FACTOR)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--feature-schema", default="outcomes_elo_v1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        result = evaluate_lockbox(
            connection,
            args.protocol_name,
            model_family=args.model_family,
            k_factor=args.k_factor,
            seed=args.seed,
            feature_schema=args.feature_schema,
            dry_run=args.dry_run,
        )
        print(render_evaluation(result, args.format))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
