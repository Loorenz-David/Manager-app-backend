from beyo_manager.domain.analytics.estimation import (
    TimeEstimationStrategy,
    estimate_fill,
    iqr_trimmed_mean,
    mean,
    median,
    resolve,
)


def test_mean_empty_and_known_sample():
    assert mean([]) == 0.0
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_median_empty_single_and_even_sample():
    assert median([]) == 0.0
    assert median([7.0]) == 7.0
    assert median([1.0, 5.0, 9.0, 13.0]) == 7.0


def test_iqr_trimmed_mean_removes_tukey_outlier():
    assert iqr_trimmed_mean([]) == 0.0
    assert iqr_trimmed_mean([7.0]) == 7.0
    assert iqr_trimmed_mean([9.0, 10.0, 10.0, 11.0, 100.0]) == 10.0


def test_strategy_resolution_and_fill():
    assert resolve("median") == TimeEstimationStrategy.MEDIAN
    assert resolve(TimeEstimationStrategy.IQR) == TimeEstimationStrategy.IQR
    assert estimate_fill(3, 12.5) == 37.5
