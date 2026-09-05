from prediction.metrics import ScoredPrediction, compute_metrics, wilson_interval


def test_compute_metrics_on_empty_predictions_returns_none_rather_than_dividing_by_zero():
    metrics = compute_metrics([])
    assert metrics == {"n": 0, "accuracy": None, "log_loss": None, "brier_score": None}


def test_compute_metrics_perfect_predictions_score_maximally():
    predictions = [
        ScoredPrediction(p_win_a=0.99, athlete_a_won=True),
        ScoredPrediction(p_win_a=0.01, athlete_a_won=False),
    ]
    metrics = compute_metrics(predictions)
    assert metrics["accuracy"] == 1.0
    assert metrics["log_loss"] < 0.02
    assert metrics["brier_score"] < 0.001


def test_compute_metrics_confidently_wrong_predictions_score_worst():
    predictions = [
        ScoredPrediction(p_win_a=0.99, athlete_a_won=False),
        ScoredPrediction(p_win_a=0.01, athlete_a_won=True),
    ]
    metrics = compute_metrics(predictions)
    assert metrics["accuracy"] == 0.0
    assert metrics["log_loss"] > 4.0
    assert metrics["brier_score"] > 0.9


def test_wilson_interval_widens_at_small_sample_sizes():
    small_lower, small_upper = wilson_interval(successes=6, n=10)
    large_lower, large_upper = wilson_interval(successes=600, n=1000)
    assert (small_upper - small_lower) > (large_upper - large_lower)


def test_wilson_interval_of_zero_samples_is_degenerate_not_an_error():
    assert wilson_interval(successes=0, n=0) == (0.0, 0.0)
