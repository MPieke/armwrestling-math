"""Tier B: sklearn LogisticRegression over the point-in-time feature table.

Encoding is this model's concern, not point_in_time_features.py's: numeric
features are used as-is; arm and weight_class are one-hot encoded against a
vocabulary fixed from the fold's own training rows, so a category never
seen in training becomes an all-zero indicator at test time rather than
raising (a fold that has never seen "Open category" simply can't have
learned a weight for it).
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression

from prediction.db import CompletedMatch
from prediction.point_in_time_features import (
    FeatureRow,
    build_training_table,
    features_for_test_match,
)

NUMERIC_FEATURES = [
    "prior_rating_a",
    "prior_rating_b",
    "head_to_head_diff",
    "recent_form_a",
    "recent_form_b",
    "win_rate_a",
    "win_rate_b",
    "days_since_last_match_a",
    "days_since_last_match_b",
]
CATEGORICAL_FEATURES = ["arm", "weight_class"]


def vocabulary_for(rows: list[FeatureRow]) -> dict[str, list[str]]:
    seen: dict[str, set[str]] = {name: set() for name in CATEGORICAL_FEATURES}
    for row in rows:
        for name in CATEGORICAL_FEATURES:
            seen[name].add(row.features[name])
    return {name: sorted(values) for name, values in seen.items()}


def column_names_for(
    vocabulary: dict[str, list[str]], numeric_features: list[str] = NUMERIC_FEATURES
) -> list[str]:
    """numeric_features defaults to Tier B's own set; evidence_model.py
    passes an extended list so the same one-hot encoding logic doesn't get
    re-derived for Tier C's additional evidence columns."""
    columns = list(numeric_features)
    for name in CATEGORICAL_FEATURES:
        columns.extend(f"{name}={value}" for value in vocabulary[name])
    return columns


def encode_features(
    features: dict, columns: list[str], numeric_features: list[str] = NUMERIC_FEATURES
) -> list[float]:
    vector = []
    for column in columns:
        if column in numeric_features:
            vector.append(float(features[column]))
        else:
            name, _, value = column.partition("=")
            vector.append(1.0 if features.get(name) == value else 0.0)
    return vector


class _ConstantPredictor:
    """A fold's training set had only one outcome class -- LogisticRegression
    cannot fit a boundary from it. An uninformative 0.5 is the honest
    prediction until there's a mixed-outcome fold to learn from, not an
    error (small real-data folds are exactly where this happens)."""

    def predict(self, match: CompletedMatch) -> float:
        return 0.5

    def params(self) -> dict:
        return {"degenerate_single_class_fold": True}


class LogRegPredictor:
    def __init__(
        self,
        model: LogisticRegression,
        columns: list[str],
        train_matches: list[CompletedMatch],
        default_ratings: dict[int, float] | None,
    ):
        self._model = model
        self._columns = columns
        self._train_matches = train_matches
        self._default_ratings = default_ratings

    def predict(self, match: CompletedMatch) -> float:
        features, _ = features_for_test_match(self._train_matches, match, self._default_ratings)
        vector = encode_features(features, self._columns)
        athlete_a_won_index = list(self._model.classes_).index(1.0)
        return float(self._model.predict_proba([vector])[0][athlete_a_won_index])

    def params(self) -> dict:
        weights = {
            column: float(weight)
            for column, weight in zip(self._columns, self._model.coef_[0])
        }
        weights["intercept"] = float(self._model.intercept_[0])
        return weights


class LogRegFamily:
    representation_kind = "tabular"

    def __init__(self, default_ratings: dict[int, float] | None = None):
        self._default_ratings = default_ratings

    def hyperparams(self) -> dict:
        return {}

    def fit(self, train_matches: list[CompletedMatch]) -> "LogRegPredictor | _ConstantPredictor":
        rows = build_training_table(train_matches, self._default_ratings)
        labels = [row.label for row in rows]
        if len(set(labels)) < 2:
            return _ConstantPredictor()

        columns = column_names_for(vocabulary_for(rows))
        design_matrix = [encode_features(row.features, columns) for row in rows]
        model = LogisticRegression(max_iter=1000)
        model.fit(design_matrix, labels)
        return LogRegPredictor(model, columns, train_matches, self._default_ratings)
