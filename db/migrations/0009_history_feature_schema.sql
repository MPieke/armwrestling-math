insert into feature_specs (name, version, representation_kind, definition, definition_sha256)
values (
    'history',
    1,
    'tabular',
    '{"inputs":["v_completed_matches"],"features":["prior_rating_a","prior_rating_b","head_to_head_diff","recent_form_a","recent_form_b","win_rate_a","win_rate_b","arm","weight_class","days_since_last_match_a","days_since_last_match_b"],"missingness":"documented_defaults","version":1}',
    '92b73bff67e60dd99b1ff13874e19104e90d4da45c6b5594ee20a20134971999'
);
