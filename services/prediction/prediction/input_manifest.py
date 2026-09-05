"""Immutable, model-facing inputs persisted for one experiment run."""

from __future__ import annotations

from collections import Counter
import json
from typing import Callable, Iterable

import psycopg

from prediction import db
from prediction.feature_specs import FeatureSchema, canonical_json_sha256
from prediction.folds import Fold

FoldPayloadBuilder = Callable[[Fold, dict[int, "db.CompletedMatch"]], dict[tuple[int, str], dict]]


def outcomes_elo_payload(match: db.CompletedMatch, *, role: str) -> dict:
    payload = {
        "match_id": match.match_id,
        "scheduled_at": match.scheduled_at.isoformat(),
        "arm": match.arm,
        "athlete_a_id": match.athlete_a_id,
        "athlete_b_id": match.athlete_b_id,
        "missingness": "not_applicable",
    }
    if role == "train":
        payload["athlete_a_won"] = match.result_a == "win"
    return payload


def outcomes_elo_fold_payloads(
    fold: Fold, matches_by_id: dict[int, db.CompletedMatch]
) -> dict[tuple[int, str], dict]:
    payloads: dict[tuple[int, str], dict] = {}
    for role, match_ids in (("train", fold.train_match_ids), ("test", fold.test_match_ids)):
        for match_id in match_ids:
            payloads[(match_id, role)] = outcomes_elo_payload(matches_by_id[match_id], role=role)
    return payloads


def persist_inputs(
    connection: psycopg.Connection,
    run_id: int,
    folds: Iterable[Fold],
    matches_by_id: dict[int, db.CompletedMatch],
    build_fold_payloads: FoldPayloadBuilder = outcomes_elo_fold_payloads,
) -> None:
    rows: list[tuple[int, int, str, dict]] = []
    for fold in folds:
        for (match_id, role), payload in build_fold_payloads(fold, matches_by_id).items():
            rows.append((fold.fold_index, match_id, role, payload))

    with connection.cursor() as cursor:
        for fold_index, match_id, role, payload in rows:
            cursor.execute(
                """
                insert into run_feature_rows (run_id, fold_index, match_id, role, payload, payload_sha256)
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    fold_index,
                    match_id,
                    role,
                    json.dumps(payload),
                    canonical_json_sha256(payload),
                ),
            )
        manifest = {
            "folds": [
                {
                    "fold_index": fold.fold_index,
                    "train_match_ids": fold.train_match_ids,
                    "test_match_ids": fold.test_match_ids,
                }
                for fold in folds
            ],
            "row_hashes": [canonical_json_sha256(payload) for _, _, _, payload in rows],
        }
        cursor.execute(
            """
            insert into run_input_manifests (run_id, cutoff_policy, data_summary, manifest_sha256)
            values (%s, %s, %s, %s)
            """,
            (
                run_id,
                json.dumps({"rule": "strictly_prior_match_state", "source": "v_completed_matches"}),
                json.dumps(
                    {
                        "feature_rows": len(rows),
                        "roles": dict(Counter(role for _, _, role, _ in rows)),
                    }
                ),
                canonical_json_sha256(manifest),
            ),
        )


def get_feature_spec(
    connection: psycopg.Connection, name: str, version: int
) -> tuple[int, FeatureSchema]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, name, version, representation_kind, definition
            from feature_specs
            where name = %s and version = %s
            """,
            (name, version),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"unknown feature schema {name}_v{version}")
    return row[0], FeatureSchema(
        name=row[1], version=row[2], representation_kind=row[3], definition=row[4]
    )
