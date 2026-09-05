"""Read-only explanation of the persisted inputs for one prediction."""

from __future__ import annotations

import argparse
import json
from typing import Any

import psycopg

from prediction import db


def build_prediction_explanation(
    connection: psycopg.Connection, run_id: int, match_id: int
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select fold_index, payload, payload_sha256
            from run_feature_rows
            where run_id = %s and match_id = %s and role = 'test'
            order by fold_index
            """,
            (run_id, match_id),
        )
        test_inputs = [
            {"fold_index": row[0], "payload": row[1], "payload_sha256": row[2]}
            for row in cursor.fetchall()
        ]
        if not test_inputs:
            raise ValueError(f"run {run_id} has no persisted test input for match {match_id}")
        cursor.execute(
            """
            select athlete_id, p_win
            from run_predictions
            where run_id = %s and match_id = %s
            order by athlete_id
            """,
            (run_id, match_id),
        )
        predictions = [{"athlete_id": row[0], "p_win": row[1]} for row in cursor.fetchall()]

    return {
        "run_id": run_id,
        "match_id": match_id,
        "test_inputs": test_inputs,
        "predictions": predictions,
    }


def render_explanation(explanation: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(explanation, indent=2, sort_keys=True, default=str)
    if output_format == "text":
        return "\n".join(
            (
                f"run {explanation['run_id']}, match {explanation['match_id']}",
                f"persisted test inputs: {len(explanation['test_inputs'])}",
                f"recorded predictions: {len(explanation['predictions'])}",
            )
        )
    raise ValueError(f"unsupported format {output_format!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inspect one persisted prediction without refitting a model."
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        print(
            render_explanation(
                build_prediction_explanation(connection, args.run_id, args.match_id), args.format
            )
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
