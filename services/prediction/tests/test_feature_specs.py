import pytest

from prediction.feature_specs import FeatureSchema, canonical_json_sha256, require_compatible


def test_feature_schema_hash_is_stable_across_key_order():
    left = {"inputs": ["v_completed_matches"], "missingness": "explicit", "version": 1}
    right = {"version": 1, "missingness": "explicit", "inputs": ["v_completed_matches"]}

    assert canonical_json_sha256(left) == canonical_json_sha256(right)


def test_feature_schema_rejects_unsupported_model_representation_pair():
    schema = FeatureSchema(
        name="history",
        version=1,
        representation_kind="tabular",
        definition={"inputs": ["v_completed_matches"]},
    )

    with pytest.raises(ValueError, match="does not support tabular"):
        require_compatible(schema, {"rating"})
