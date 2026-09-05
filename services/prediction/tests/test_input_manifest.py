import pytest


@pytest.mark.integration
def test_completed_run_inputs_are_immutable(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into feature_specs (name, version, representation_kind, definition, definition_sha256)
            values ('outcomes_elo', 1, 'rating', '{}', repeat('a', 64)) returning id
            """
        )
        (feature_spec_id,) = cursor.fetchone()
        cursor.execute("insert into eval_protocols (name, kind) values ('protocol', 'rolling_origin') returning id")
        (protocol_id,) = cursor.fetchone()
        cursor.execute(
            """
            insert into experiment_runs (git_sha, git_dirty, protocol_id, feature_spec_id, model_family, hyperparams, seed, status)
            values (repeat('a', 40), false, %s, %s, 'elo', '{}', 0, 'completed') returning id
            """,
            (protocol_id, feature_spec_id),
        )
        (run_id,) = cursor.fetchone()
        cursor.execute(
            """
            insert into run_input_manifests (run_id, cutoff_policy, data_summary, manifest_sha256)
            values (%s, '{}', '{}', repeat('b', 64))
            """,
            (run_id,),
        )
        with pytest.raises(Exception):
            cursor.execute("update run_input_manifests set data_summary = '{\"changed\":true}' where run_id = %s", (run_id,))
    connection.rollback()
