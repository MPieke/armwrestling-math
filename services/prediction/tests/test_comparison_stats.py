from prediction.comparison_stats import (
    PairedPrediction,
    compare_predictions,
    mcnemar_exact_p_value,
    paired_log_loss_bootstrap_ci,
)


def _pair(match_id, athlete_a_won, p_a, p_b):
    return PairedPrediction(
        match_id=match_id, athlete_a_won=athlete_a_won, p_win_a_run_a=p_a, p_win_a_run_b=p_b
    )


def test_identical_predictions_are_not_distinguishable():
    pairs = [_pair(i, i % 2 == 0, 0.7 if i % 2 == 0 else 0.3, 0.7 if i % 2 == 0 else 0.3) for i in range(20)]

    result = compare_predictions(pairs)

    assert result.mcnemar_discordant_pairs == (0, 0)
    assert result.mcnemar_p_value == 1.0
    ci_lower, ci_upper = result.log_loss_diff_ci
    assert ci_lower <= 0.0 <= ci_upper
    assert result.distinguishable is False


def test_a_consistently_right_b_consistently_wrong_is_distinguishable():
    pairs = [_pair(i, True, 0.95, 0.05) for i in range(30)]

    result = compare_predictions(pairs)

    assert result.accuracy_a == 1.0
    assert result.accuracy_b == 0.0
    assert result.mcnemar_discordant_pairs == (30, 0)
    assert result.mcnemar_p_value < 0.01
    ci_lower, ci_upper = result.log_loss_diff_ci
    assert ci_upper < 0.0  # a's log-loss is reliably lower (better) than b's
    assert result.distinguishable is True


def _noisy_pairs(count):
    # Alternates a strong and a weak win for A over B so the per-pair
    # log-loss diff has real variance -- a constant diff has zero bootstrap
    # spread regardless of n, which wouldn't exercise resampling at all.
    return [_pair(i, True, 0.9 if i % 2 == 0 else 0.55, 0.5) for i in range(count)]


def test_bootstrap_ci_narrows_as_sample_size_grows_at_a_fixed_effect_size():
    small_ci = paired_log_loss_bootstrap_ci(_noisy_pairs(10), seed=1)
    large_ci = paired_log_loss_bootstrap_ci(_noisy_pairs(200), seed=1)

    assert (large_ci[1] - large_ci[0]) < (small_ci[1] - small_ci[0])


def test_mcnemar_is_symmetric_and_maximal_at_a_perfect_split():
    assert mcnemar_exact_p_value(0, 0) == 1.0
    assert mcnemar_exact_p_value(5, 5) == 1.0
    assert mcnemar_exact_p_value(10, 0) == mcnemar_exact_p_value(0, 10)


def test_compare_predictions_on_empty_pairs_is_not_an_error():
    result = compare_predictions([])

    assert result.n == 0
    assert result.distinguishable is False
