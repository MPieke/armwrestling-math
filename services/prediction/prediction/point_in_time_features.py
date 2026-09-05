"""Tier B's inner temporal loop: one feature row per match, computed only
from state built out of strictly earlier matches.

The failure mode this guards against is invisible if you're not looking
for it: computing e.g. "head_to_head_diff as of the fold cutoff" once for
the whole training window, then reusing that single number for every
training row, still only uses information from "before the fold cutoff" --
just not from before *that specific row*. A March training example would
then see its own June rematch. build_training_table instead threads a
running state through train_matches (already chronological) exactly like
elo.fit threads its ratings dict: a row's features come from state as of
the previous match, and only then does that match get folded into state.

Feature values are left in their raw representation (numeric floats,
"left"/"right" and weight-class strings as-is) rather than pre-encoded --
encoding (one-hot, embeddings, whatever a given model needs) is that
model's concern, not this builder's, so the same table can feed logreg.py,
tabpfn.py, or a future model without re-deriving anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prediction import elo
from prediction.db import CompletedMatch
from prediction.folds import Fold

RECENT_FORM_WINDOW = 5
DEFAULT_WIN_RATE = 0.5
DEFAULT_HEAD_TO_HEAD_DIFF = 0.0
DEBUT_DAYS_SINCE_LAST_MATCH = -1.0


@dataclass(frozen=True)
class FeatureRow:
    match_id: int
    label: float
    features: dict[str, float | str]
    provenance: dict[str, list[int]]


def _pair_key(athlete_a_id: int, athlete_b_id: int) -> tuple[int, int]:
    return (athlete_a_id, athlete_b_id) if athlete_a_id < athlete_b_id else (athlete_b_id, athlete_a_id)


@dataclass
class _RunningState:
    ratings: dict[int, float] = field(default_factory=dict)
    match_ids_by_athlete: dict[int, list[int]] = field(default_factory=dict)
    last_scheduled_at: dict[int, object] = field(default_factory=dict)
    pair_wins: dict[tuple[int, int], dict[int, int]] = field(default_factory=dict)
    pair_match_ids: dict[tuple[int, int], list[int]] = field(default_factory=dict)
    _results: dict[int, list[float]] = field(default_factory=dict)

    def features_for(
        self, match: CompletedMatch, default_ratings: dict[int, float] | None
    ) -> tuple[dict[str, float | str], dict[str, list[int]]]:
        a, b = match.athlete_a_id, match.athlete_b_id
        features = {
            "prior_rating_a": self._prior_rating(a, default_ratings),
            "prior_rating_b": self._prior_rating(b, default_ratings),
            "head_to_head_diff": self._head_to_head_diff(a, b),
            "recent_form_a": self._recent_form(a),
            "recent_form_b": self._recent_form(b),
            "win_rate_a": self._win_rate(a),
            "win_rate_b": self._win_rate(b),
            "arm": match.arm,
            "weight_class": match.weight_class,
            "days_since_last_match_a": self._days_since_last(a, match.scheduled_at),
            "days_since_last_match_b": self._days_since_last(b, match.scheduled_at),
        }
        provenance = {
            "prior_rating_a": list(self.match_ids_by_athlete.get(a, [])),
            "prior_rating_b": list(self.match_ids_by_athlete.get(b, [])),
            "head_to_head": list(self.pair_match_ids.get(_pair_key(a, b), [])),
            "recent_form_a": self.match_ids_by_athlete.get(a, [])[-RECENT_FORM_WINDOW:],
            "recent_form_b": self.match_ids_by_athlete.get(b, [])[-RECENT_FORM_WINDOW:],
            "win_rate_a": list(self.match_ids_by_athlete.get(a, [])),
            "win_rate_b": list(self.match_ids_by_athlete.get(b, [])),
            "last_match_a": self.match_ids_by_athlete.get(a, [])[-1:],
            "last_match_b": self.match_ids_by_athlete.get(b, [])[-1:],
        }
        return features, provenance

    def _prior_rating(self, athlete_id: int, default_ratings: dict[int, float] | None) -> float:
        if athlete_id in self.ratings:
            return self.ratings[athlete_id]
        if default_ratings and athlete_id in default_ratings:
            return default_ratings[athlete_id]
        return elo.DEFAULT_RATING

    def _head_to_head_diff(self, athlete_a_id: int, athlete_b_id: int) -> float:
        pair = self.pair_wins.get(_pair_key(athlete_a_id, athlete_b_id))
        if pair is None:
            return DEFAULT_HEAD_TO_HEAD_DIFF
        return float(pair.get(athlete_a_id, 0) - pair.get(athlete_b_id, 0))

    def _recent_form(self, athlete_id: int) -> float:
        match_ids = self.match_ids_by_athlete.get(athlete_id)
        if not match_ids:
            return DEFAULT_WIN_RATE
        window = self._results_for(athlete_id)[-RECENT_FORM_WINDOW:]
        return sum(window) / len(window)

    def _win_rate(self, athlete_id: int) -> float:
        results = self._results_for(athlete_id)
        if not results:
            return DEFAULT_WIN_RATE
        return sum(results) / len(results)

    def _results_for(self, athlete_id: int) -> list[float]:
        return self._results.get(athlete_id, [])

    def _days_since_last(self, athlete_id: int, scheduled_at) -> float:
        last = self.last_scheduled_at.get(athlete_id)
        if last is None:
            return DEBUT_DAYS_SINCE_LAST_MATCH
        return (scheduled_at - last).total_seconds() / 86400.0

    def update(self, match: CompletedMatch) -> None:
        a, b = match.athlete_a_id, match.athlete_b_id
        a_won = match.result_a == "win"

        self.ratings = elo.step(self.ratings, elo.MatchResult(a, b, a_won))

        self._results.setdefault(a, []).append(1.0 if a_won else 0.0)
        self._results.setdefault(b, []).append(0.0 if a_won else 1.0)
        self.match_ids_by_athlete.setdefault(a, []).append(match.match_id)
        self.match_ids_by_athlete.setdefault(b, []).append(match.match_id)
        self.last_scheduled_at[a] = match.scheduled_at
        self.last_scheduled_at[b] = match.scheduled_at

        pair = _pair_key(a, b)
        wins = self.pair_wins.setdefault(pair, {})
        winner = a if a_won else b
        wins[winner] = wins.get(winner, 0) + 1
        self.pair_match_ids.setdefault(pair, []).append(match.match_id)


def build_training_table(
    train_matches: list[CompletedMatch],
    default_ratings: dict[int, float] | None = None,
) -> list[FeatureRow]:
    """train_matches must already be chronological (db.list_completed_matches'
    ordering, sliced by fold membership). One row per match, in order."""
    state = _RunningState()
    rows = []
    for match in train_matches:
        features, provenance = state.features_for(match, default_ratings)
        rows.append(
            FeatureRow(
                match_id=match.match_id,
                label=1.0 if match.result_a == "win" else 0.0,
                features=features,
                provenance=provenance,
            )
        )
        state.update(match)
    return rows


def history_v1_fold_payloads(
    fold: Fold,
    matches_by_id: dict[int, CompletedMatch],
    default_ratings: dict[int, float] | None = None,
) -> dict[tuple[int, str], dict]:
    """One persisted run_feature_rows payload per (match_id, role) in this
    fold, for the 'history_v1' tabular feature schema. Train payloads are
    exactly what LogRegFamily.fit trains on; the test payload is the same
    state-as-of-cutoff computation predict() uses -- persisting either
    doesn't require refitting to explain later."""
    train_matches = [matches_by_id[match_id] for match_id in fold.train_match_ids]
    payloads: dict[tuple[int, str], dict] = {}
    for row in build_training_table(train_matches, default_ratings):
        payloads[(row.match_id, "train")] = {
            "features": row.features,
            "label": row.label,
            "provenance": row.provenance,
        }
    for match_id in fold.test_match_ids:
        test_match = matches_by_id[match_id]
        features, provenance = features_for_test_match(train_matches, test_match, default_ratings)
        payloads[(match_id, "test")] = {
            "features": features,
            "scheduled_at": test_match.scheduled_at.isoformat(),
            "provenance": provenance,
        }
    return payloads


def features_for_test_match(
    train_matches: list[CompletedMatch],
    test_match: CompletedMatch,
    default_ratings: dict[int, float] | None = None,
) -> tuple[dict[str, float | str], dict[str, list[int]]]:
    """The state after every train_matches (i.e. as of the fold cutoff),
    applied to test_match without updating state afterward -- the same
    quantity elo.fit's final ratings dict represents, generalized to a
    full feature vector."""
    state = _RunningState()
    for match in train_matches:
        state.update(match)
    return state.features_for(test_match, default_ratings)
