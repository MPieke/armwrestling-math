"""Tier C: LogReg over Tier B's point-in-time features plus the fixed v1
evidence encoding (evidence.py), stacked as three extra numeric columns.
Reuses logreg.py's one-hot encoding helpers rather than re-deriving them --
the only new concern here is where the extra columns come from.

evidence_by_match_id is precomputed once by run_baseline.py (the only
module with a database connection) and passed in at construction time, so
this family's fit()/predict() stay pure over already-fetched data, exactly
like every other ModelFamily.
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression

from prediction.db import CompletedMatch
from prediction.logreg import (
    NUMERIC_FEATURES,
    _ConstantPredictor,
    column_names_for,
    encode_features,
    vocabulary_for,
)
from prediction.folds import Fold
from prediction.point_in_time_features import (
    build_training_table,
    features_for_test_match,
    history_v1_fold_payloads,
)

EVIDENCE_NUMERIC_FEATURES = NUMERIC_FEATURES + [
    "evidence_count",
    "recent_injury_flag",
    "technique_advantage_flag",
]


def _with_evidence(features: dict, evidence: dict) -> dict:
    merged = dict(features)
    merged["evidence_count"] = float(evidence["evidence_count"])
    merged["recent_injury_flag"] = 1.0 if evidence["recent_injury_flag"] else 0.0
    merged["technique_advantage_flag"] = 1.0 if evidence["technique_advantage_flag"] else 0.0
    return merged


def evidence_v1_fold_payloads(
    fold: Fold, matches_by_id: dict[int, CompletedMatch], evidence_by_match_id: dict[int, dict]
) -> dict[tuple[int, str], dict]:
    """history_v1's payload plus the evidence dict for that match, so
    explain-prediction can show the encoded evidence contribution and the
    plain history features from the same persisted row."""
    payloads = history_v1_fold_payloads(fold, matches_by_id)
    for match_id, _role in payloads:
        payloads[(match_id, _role)]["evidence"] = evidence_by_match_id[match_id]
    return payloads


class EvidenceV1Predictor:
    def __init__(
        self,
        model: LogisticRegression,
        columns: list[str],
        train_matches: list[CompletedMatch],
        evidence_by_match_id: dict[int, dict],
    ):
        self._model = model
        self._columns = columns
        self._train_matches = train_matches
        self.evidence_by_match_id = evidence_by_match_id

    def predict(self, match: CompletedMatch) -> float:
        features, _ = features_for_test_match(self._train_matches, match)
        features = _with_evidence(features, self.evidence_by_match_id[match.match_id])
        vector = encode_features(features, self._columns, EVIDENCE_NUMERIC_FEATURES)
        athlete_a_won_index = list(self._model.classes_).index(1.0)
        return float(self._model.predict_proba([vector])[0][athlete_a_won_index])

    def params(self) -> dict:
        weights = {column: float(weight) for column, weight in zip(self._columns, self._model.coef_[0])}
        weights["intercept"] = float(self._model.intercept_[0])
        return weights


class EvidenceV1Family:
    representation_kind = "tabular"

    def __init__(self, evidence_by_match_id: dict[int, dict], evidence_model: str, evidence_prompt_version: str):
        self.evidence_by_match_id = evidence_by_match_id
        self.evidence_model = evidence_model
        self.evidence_prompt_version = evidence_prompt_version

    def hyperparams(self) -> dict:
        return {"evidence_model": self.evidence_model, "evidence_prompt_version": self.evidence_prompt_version}

    def fit(self, train_matches: list[CompletedMatch]) -> "EvidenceV1Predictor | _ConstantPredictor":
        rows = build_training_table(train_matches)
        labels = [row.label for row in rows]
        if len(set(labels)) < 2:
            return _ConstantPredictor()

        columns = column_names_for(vocabulary_for(rows), EVIDENCE_NUMERIC_FEATURES)
        design_matrix = [
            encode_features(
                _with_evidence(row.features, self.evidence_by_match_id[row.match_id]),
                columns,
                EVIDENCE_NUMERIC_FEATURES,
            )
            for row in rows
        ]
        model = LogisticRegression(max_iter=1000)
        model.fit(design_matrix, labels)
        return EvidenceV1Predictor(model, columns, train_matches, self.evidence_by_match_id)
