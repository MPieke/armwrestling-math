"""Composition root: fit Elo per fold against a rolling-origin protocol,
record predictions and metrics in the experiment ledger.

Mirrors services/importer's separation between orchestration and pure
logic: this module is the only one that opens a connection and commits;
elo.py, folds.py, and metrics.py stay pure and are unit-tested without it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import psycopg

from prediction import db, elo
from prediction.folds import Fold, generate_rolling_origin
from prediction.metrics import ScoredPrediction, compute_metrics

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]


def is_promotable(*, git_dirty: bool) -> bool:
    """A run from a dirty working tree isn't reproducible and must never be
    treated as a promotion candidate."""
    return not git_dirty


def get_git_info(repo_root: Path) -> tuple[str, bool]:
    sha = _run_git(repo_root, "rev-parse", "HEAD").strip()
    dirty = bool(_run_git(repo_root, "status", "--porcelain").strip())
    return sha, dirty


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, check=True
    )
    return result.stdout


def get_or_create_rolling_origin_protocol(
    connection: psycopg.Connection, name: str, min_training_events: int
) -> int:
    """Idempotent: returns the existing protocol's id if `name` is already
    seeded, otherwise generates and materializes its folds now. Lockbox
    events (any event referenced by a lockbox protocol's folds) are excluded
    automatically so a rolling-origin protocol can never be seeded to
    include them."""
    with connection.cursor() as cursor:
        cursor.execute("select id from eval_protocols where name = %s", (name,))
        row = cursor.fetchone()
    if row is not None:
        return row[0]

    excluded_event_ids = _lockbox_event_ids(connection)
    events = db.list_events(connection)
    matches = db.list_completed_matches(connection)
    folds = generate_rolling_origin(
        events, matches, min_training_events, excluded_event_ids=excluded_event_ids
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "insert into eval_protocols (name, kind) values (%s, 'rolling_origin') returning id",
            (name,),
        )
        (protocol_id,) = cursor.fetchone()
        for fold in folds:
            cursor.execute(
                """
                insert into eval_folds (protocol_id, fold_index, train_match_ids, test_match_ids)
                values (%s, %s, %s, %s)
                """,
                (protocol_id, fold.fold_index, fold.train_match_ids, fold.test_match_ids),
            )
    connection.commit()
    return protocol_id


def _lockbox_event_ids(connection: psycopg.Connection) -> frozenset[int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select distinct m.event_id
            from eval_folds f
            join eval_protocols p on p.id = f.protocol_id
            join matches m on m.id = any(f.test_match_ids || f.train_match_ids)
            where p.kind like 'lockbox%%'
            """
        )
        return frozenset(row[0] for row in cursor.fetchall())


def run_baseline(
    connection: psycopg.Connection,
    protocol_id: int,
    *,
    model_family: str = "elo",
    k_factor: float = elo.DEFAULT_K_FACTOR,
    seed: int = 0,
    repo_root: Path = DEFAULT_REPO_ROOT,
) -> int:
    git_sha, git_dirty = get_git_info(repo_root)
    hyperparams = {"k_factor": k_factor}

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into experiment_runs (git_sha, git_dirty, protocol_id, model_family, hyperparams, seed, status)
            values (%s, %s, %s, %s, %s, %s, 'running')
            returning id
            """,
            (git_sha, git_dirty, protocol_id, model_family, json.dumps(hyperparams), seed),
        )
        (run_id,) = cursor.fetchone()
    connection.commit()

    try:
        folds = _load_folds(connection, protocol_id)
        matches_by_id = {match.match_id: match for match in db.list_completed_matches(connection)}
        scored, final_ratings = _fit_predict_and_record(connection, run_id, folds, matches_by_id, k_factor)
        metrics = compute_metrics(scored)
        _complete_run(connection, run_id, metrics, final_ratings)
        connection.commit()
    except Exception as error:
        connection.rollback()
        _fail_run(connection, run_id, str(error))
        connection.commit()
        raise
    return run_id


def _load_folds(connection: psycopg.Connection, protocol_id: int) -> list[Fold]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select fold_index, train_match_ids, test_match_ids
            from eval_folds where protocol_id = %s order by fold_index
            """,
            (protocol_id,),
        )
        return [
            Fold(fold_index=row[0], train_match_ids=row[1], test_match_ids=row[2])
            for row in cursor.fetchall()
        ]


def _fit_predict_and_record(
    connection: psycopg.Connection,
    run_id: int,
    folds: list[Fold],
    matches_by_id: dict[int, db.CompletedMatch],
    k_factor: float,
) -> tuple[list[ScoredPrediction], dict[int, float]]:
    scored: list[ScoredPrediction] = []
    ratings: dict[int, float] = {}
    for fold in folds:
        train_matches = [_to_match_result(matches_by_id[mid]) for mid in fold.train_match_ids]
        ratings = elo.fit(train_matches, k_factor=k_factor)
        for match_id in fold.test_match_ids:
            match = matches_by_id[match_id]
            rating_a = ratings.get(match.athlete_a_id, elo.DEFAULT_RATING)
            rating_b = ratings.get(match.athlete_b_id, elo.DEFAULT_RATING)
            p_win_a = elo.predict(rating_a, rating_b)
            _record_prediction(connection, run_id, match_id, match.athlete_a_id, p_win_a)
            _record_prediction(connection, run_id, match_id, match.athlete_b_id, 1.0 - p_win_a)
            scored.append(ScoredPrediction(p_win_a=p_win_a, athlete_a_won=match.result_a == "win"))
    return scored, ratings


def _to_match_result(match: db.CompletedMatch) -> elo.MatchResult:
    return elo.MatchResult(
        athlete_a_id=match.athlete_a_id,
        athlete_b_id=match.athlete_b_id,
        athlete_a_won=match.result_a == "win",
    )


def _record_prediction(
    connection: psycopg.Connection, run_id: int, match_id: int, athlete_id: int, p_win: float
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into run_predictions (run_id, match_id, athlete_id, p_win) values (%s, %s, %s, %s)",
            (run_id, match_id, athlete_id, p_win),
        )


def _complete_run(
    connection: psycopg.Connection, run_id: int, metrics: dict, ratings: dict[int, float]
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "update experiment_runs set status = 'completed', finished_at = now(), metrics = %s where id = %s",
            (json.dumps(metrics), run_id),
        )
        cursor.execute(
            "insert into run_models (run_id, params) values (%s, %s)",
            (run_id, json.dumps({str(athlete_id): rating for athlete_id, rating in ratings.items()})),
        )


def _fail_run(connection: psycopg.Connection, run_id: int, error_message: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "update experiment_runs set status = 'failed', finished_at = now(), error_message = %s where id = %s",
            (error_message, run_id),
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Elo baseline against a rolling-origin protocol.")
    parser.add_argument("--protocol-name", required=True)
    parser.add_argument("--min-training-events", type=int, required=True)
    parser.add_argument("--k-factor", type=float, default=elo.DEFAULT_K_FACTOR)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        protocol_id = get_or_create_rolling_origin_protocol(
            connection, args.protocol_name, args.min_training_events
        )
        run_id = run_baseline(connection, protocol_id, k_factor=args.k_factor, seed=args.seed)
        print(f"experiment run {run_id} completed against protocol {args.protocol_name!r}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
