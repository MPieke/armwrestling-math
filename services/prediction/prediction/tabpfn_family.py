"""TabPFN over the same point-in-time feature table logreg.py uses.

Optional dependency (`uv sync --extra tabpfn`, pulls in torch): not
white-box, a reference point only per MPI-25/26's model-ladder scope, not
a dependency of any later ticket. Import is guarded so the rest of the
prediction service works with the extra absent; MODEL_FAMILIES registers
"tabpfn" only when the import succeeds.
"""

from __future__ import annotations

from prediction.db import CompletedMatch
from prediction.logreg import column_names_for, encode_features, vocabulary_for
from prediction.point_in_time_features import build_training_table, features_for_test_match

try:
    from tabpfn import TabPFNClassifier

    TABPFN_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the extra
    TABPFN_AVAILABLE = False


class TabPFNPredictor:
    def __init__(self, model, columns: list[str], train_matches: list[CompletedMatch]):
        self._model = model
        self._columns = columns
        self._train_matches = train_matches

    def predict(self, match: CompletedMatch) -> float:
        features, _ = features_for_test_match(self._train_matches, match)
        vector = encode_features(features, self._columns)
        athlete_a_won_index = list(self._model.classes_).index(1.0)
        return float(self._model.predict_proba([vector])[0][athlete_a_won_index])

    def params(self) -> dict:
        # TabPFN is a pre-trained transformer, not a fitted coefficient
        # vector -- there is no per-feature weight to expose. The training
        # set itself is the only "fitted state," already fully visible via
        # the persisted run_feature_rows train payloads for this run.
        return {"model": "tabpfn", "training_row_count": len(self._train_matches)}


class TabPFNFamily:
    representation_kind = "tabular"

    def hyperparams(self) -> dict:
        return {}

    def fit(self, train_matches: list[CompletedMatch]) -> TabPFNPredictor:
        if not TABPFN_AVAILABLE:
            raise ImportError(
                "tabpfn is not installed; run `uv sync --extra tabpfn` to enable "
                "the tabpfn model family"
            )
        rows = build_training_table(train_matches)
        columns = column_names_for(vocabulary_for(rows))
        design_matrix = [encode_features(row.features, columns) for row in rows]
        labels = [row.label for row in rows]
        model = TabPFNClassifier()
        model.fit(design_matrix, labels)
        return TabPFNPredictor(model, columns, train_matches)
