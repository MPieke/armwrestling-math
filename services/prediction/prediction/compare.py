"""Statistically honest comparison between two experiment runs on the same
protocol. Read-only: refits nothing, writes nothing.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import psycopg

from prediction import db
from prediction.comparison_stats import PairedPrediction, compare_predictions


def compare(
    connection: psycopg.Connection,
    run_id_a: int,
    run_id_b: int,
    match_ids: list[int] | None = None,
) -> dict[str, Any]:
    run_a = _load_run(connection, run_id_a)
    run_b = _load_run(connection, run_id_b)
    if run_a["protocol_id"] != run_b["protocol_id"]:
        raise ValueError(
            f"runs {run_id_a} (protocol {run_a['protocol_id']}) and {run_id_b} "
            f"(protocol {run_b['protocol_id']}) are not on the same protocol"
        )

    pairs = _paired_predictions(connection, run_id_a, run_id_b, match_ids)
    result = compare_predictions(pairs)

    return {
        "run_a": run_a,
        "run_b": run_b,
        "protocol_id": run_a["protocol_id"],
        "match_ids_restricted": match_ids is not None,
        "match_ids": sorted(pair.match_id for pair in pairs),
        "n": result.n,
        "accuracy_a": result.accuracy_a,
        "accuracy_b": result.accuracy_b,
        "mcnemar_discordant_pairs": result.mcnemar_discordant_pairs,
        "mcnemar_p_value": result.mcnemar_p_value,
        "log_loss_diff_ci": result.log_loss_diff_ci,
        "distinguishable": result.distinguishable,
    }


def _load_run(connection: psycopg.Connection, run_id: int) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            "select protocol_id, model_family, git_dirty, status from experiment_runs where id = %s",
            (run_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"experiment run {run_id} does not exist")
    return {
        "run_id": run_id,
        "protocol_id": row[0],
        "model_family": row[1],
        "promotable": not row[2],
        "status": row[3],
    }


def _paired_predictions(
    connection: psycopg.Connection, run_id_a: int, run_id_b: int, match_ids: list[int] | None
) -> list[PairedPrediction]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select v.match_id, v.result_a = 'win' as athlete_a_won,
                   ra.p_win as p_win_a_run_a, rb.p_win as p_win_a_run_b
            from v_completed_matches v
            join run_predictions ra
                on ra.match_id = v.match_id and ra.athlete_id = v.athlete_a_id and ra.run_id = %s
            join run_predictions rb
                on rb.match_id = v.match_id and rb.athlete_id = v.athlete_a_id and rb.run_id = %s
            where %s or v.match_id = any(%s)
            order by v.match_id
            """,
            (run_id_a, run_id_b, match_ids is None, match_ids or []),
        )
        return [
            PairedPrediction(
                match_id=row[0], athlete_a_won=row[1], p_win_a_run_a=row[2], p_win_a_run_b=row[3]
            )
            for row in cursor.fetchall()
        ]


def render_comparison(comparison: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(comparison, indent=2, sort_keys=True, default=str)
    if output_format == "text":
        scope = (
            f"{len(comparison['match_ids'])} explicitly restricted matches"
            if comparison["match_ids_restricted"]
            else "all shared predictions"
        )
        ci_lower, ci_upper = comparison["log_loss_diff_ci"]
        return "\n".join(
            (
                f"run {comparison['run_a']['run_id']} ({comparison['run_a']['model_family']}, "
                f"promotable={comparison['run_a']['promotable']}) vs "
                f"run {comparison['run_b']['run_id']} ({comparison['run_b']['model_family']}, "
                f"promotable={comparison['run_b']['promotable']})",
                f"protocol {comparison['protocol_id']}, evaluated over {scope}: n={comparison['n']}",
                f"accuracy: a={comparison['accuracy_a']:.4f} b={comparison['accuracy_b']:.4f}",
                f"mcnemar discordant pairs (a-right/b-wrong, b-right/a-wrong): "
                f"{comparison['mcnemar_discordant_pairs']}, p={comparison['mcnemar_p_value']:.4f}",
                f"log-loss diff (a - b) 95% bootstrap CI: [{ci_lower:.4f}, {ci_upper:.4f}]",
                f"verdict: {'distinguishable' if comparison['distinguishable'] else 'not distinguishable'}",
            )
        )
    raise ValueError(f"unsupported format {output_format!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare two experiment runs statistically.")
    parser.add_argument("--run-a", type=int, required=True)
    parser.add_argument("--run-b", type=int, required=True)
    parser.add_argument("--match-ids", help="comma-separated match ids to restrict to")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    match_ids = [int(value) for value in args.match_ids.split(",")] if args.match_ids else None

    connection = db.connect()
    try:
        print(render_comparison(compare(connection, args.run_a, args.run_b, match_ids), args.format))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
