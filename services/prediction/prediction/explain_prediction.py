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
        for test_input in test_inputs:
            test_input["fold_cutoff"] = _fold_cutoff(cursor, run_id, test_input["fold_index"])
            test_input["defaulted_features"] = sorted(
                feature_name
                for feature_name, source_match_ids in test_input["payload"]
                .get("provenance", {})
                .items()
                if not source_match_ids
            )
        cursor.execute(
            """
            select rp.athlete_id, rp.p_win,
                   case
                       when rp.athlete_id = v.athlete_a_id then v.result_a
                       when v.result_a = 'win' then 'loss'
                       when v.result_a = 'loss' then 'win'
                       else null
                   end as outcome
            from run_predictions rp
            left join v_completed_matches v on v.match_id = rp.match_id
            where rp.run_id = %s and rp.match_id = %s
            order by rp.athlete_id
            """,
            (run_id, match_id),
        )
        predictions = [
            {"athlete_id": row[0], "p_win": row[1], "outcome": row[2]}
            for row in cursor.fetchall()
        ]

    return {
        "run_id": run_id,
        "match_id": match_id,
        "test_inputs": test_inputs,
        "predictions": predictions,
    }


def _fold_cutoff(cursor, run_id: int, fold_index: int) -> str | None:
    """The latest scheduled_at among this fold's training matches -- the
    point-in-time boundary every persisted feature value must respect. None
    for a fold with no training matches (the first eligible fold)."""
    cursor.execute(
        """
        select max(m.scheduled_at)
        from run_feature_rows f
        join matches m on m.id = f.match_id
        where f.run_id = %s and f.fold_index = %s and f.role = 'train'
        """,
        (run_id, fold_index),
    )
    (cutoff,) = cursor.fetchone()
    return cutoff.isoformat() if cutoff is not None else None


def render_explanation(explanation: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(explanation, indent=2, sort_keys=True, default=str)
    if output_format == "text":
        lines = [f"run {explanation['run_id']}, match {explanation['match_id']}"]
        for prediction in explanation["predictions"]:
            lines.append(
                f"  athlete {prediction['athlete_id']}: p_win={prediction['p_win']:.4f} "
                f"outcome={prediction['outcome']}"
            )
        for test_input in explanation["test_inputs"]:
            lines.append(
                f"fold {test_input['fold_index']} cutoff: {test_input['fold_cutoff']}"
            )
            features = test_input["payload"].get("features")
            if features:
                lines.append("  features:")
                for name in sorted(features):
                    lines.append(f"    {name} = {features[name]}")
            if test_input["defaulted_features"]:
                lines.append(f"  defaulted (no source record): {test_input['defaulted_features']}")
        return "\n".join(lines)
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
