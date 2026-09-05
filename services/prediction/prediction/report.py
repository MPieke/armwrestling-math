"""Read-only reconstruction of an experiment run's persisted basis."""

from __future__ import annotations

import argparse
import json
from typing import Any

import psycopg

from prediction import db


def build_run_report(connection: psycopg.Connection, run_id: int) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select r.id, r.status, r.git_sha, r.git_dirty, r.model_family,
                   r.hyperparams, r.seed, r.metrics, r.hypothesis,
                   p.id, p.name, p.kind, p.spec,
                   fs.name, fs.version, fs.representation_kind, fs.definition, fs.definition_sha256,
                   m.cutoff_policy, m.data_summary, m.manifest_sha256,
                   rm.params
            from experiment_runs r
            join eval_protocols p on p.id = r.protocol_id
            join feature_specs fs on fs.id = r.feature_spec_id
            join run_input_manifests m on m.run_id = r.id
            left join run_models rm on rm.run_id = r.id
            where r.id = %s
            """,
            (run_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(
                f"experiment run {run_id} does not exist or has no persisted input manifest"
            )
        cursor.execute(
            """
            select f.fold_index, f.train_match_ids, f.test_match_ids,
                   array(
                       select distinct e.held_on
                       from matches m join events e on e.id = m.event_id
                       where m.id = any(f.test_match_ids)
                       order by e.held_on
                   )
            from eval_folds f
            where f.protocol_id = %s
            order by fold_index
            """,
            (row[9],),
        )
        folds = [
            {
                "fold_index": fold[0],
                "train_match_ids": fold[1],
                "test_match_ids": fold[2],
                "test_event_dates": [event_date.isoformat() for event_date in fold[3]],
            }
            for fold in cursor.fetchall()
        ]
        cursor.execute(
            """
            select rp.match_id, rp.athlete_id, rp.p_win,
                   case
                       when rp.athlete_id = v.athlete_a_id then v.result_a
                       when v.result_a = 'win' then 'loss'
                       when v.result_a = 'loss' then 'win'
                       else null
                   end as outcome
            from run_predictions rp
            left join v_completed_matches v on v.match_id = rp.match_id
            where rp.run_id = %s
            order by rp.match_id, rp.athlete_id
            """,
            (run_id,),
        )
        predictions = [
            {
                "match_id": prediction[0],
                "athlete_id": prediction[1],
                "p_win": prediction[2],
                "outcome": prediction[3],
            }
            for prediction in cursor.fetchall()
        ]

    predicted_match_ids = {prediction["match_id"] for prediction in predictions}
    for fold in folds:
        fold["predicted_match_count"] = len(
            predicted_match_ids.intersection(fold["test_match_ids"])
        )

    return {
        "run": {
            "id": row[0],
            "status": row[1],
            "git_sha": row[2],
            "git_dirty": row[3],
            "model_family": row[4],
            "hyperparams": row[5],
            "seed": row[6],
            "metrics": row[7],
            "hypothesis": row[8],
            "promotable": not row[3],
        },
        "protocol": {"id": row[9], "name": row[10], "kind": row[11], "spec": row[12]},
        "feature_schema": {
            "name": row[13],
            "version": row[14],
            "representation_kind": row[15],
            "definition": row[16],
            "definition_sha256": row[17],
        },
        "input_manifest": {
            "cutoff_policy": row[18],
            "data_summary": row[19],
            "manifest_sha256": row[20],
        },
        "model": row[21],
        "folds": folds,
        "predictions": predictions,
    }


def render_report(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, indent=2, sort_keys=True, default=str)
    if output_format == "text":
        return "\n".join(
            (
                f"run {report['run']['id']}: {report['run']['status']}",
                f"promotable: {report['run']['promotable']}",
                f"model: {report['run']['model_family']}",
                f"feature schema: {report['feature_schema']['name']}_v{report['feature_schema']['version']}",
                f"protocol: {report['protocol']['name']} ({len(report['folds'])} folds)",
                f"input manifest: {report['input_manifest']['manifest_sha256']}",
                f"predictions: {len(report['predictions'])}",
            )
        )
    raise ValueError(f"unsupported format {output_format!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inspect one persisted experiment run without refitting it."
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        print(render_report(build_run_report(connection, args.run_id), args.format))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
