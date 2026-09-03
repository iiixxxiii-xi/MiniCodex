import pytest

import numstats
from numstats.descriptive import mean, median, mode, percentile, stdev, variance


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


def test_mean_basic():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_single():
    assert mean([7]) == 7


def test_mean_all_negative():
    assert mean([-1, -2, -3]) == -2


def test_median_empty():
    with pytest.raises(ValueError):
        median([])


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_median_even_two():
    assert median([10, 20]) == 15


def test_median_single():
    assert median([5]) == 5


def test_median_unsorted():
    assert median([4, 1, 3, 2]) == 2.5


def test_mode_empty():
    with pytest.raises(ValueError):
        mode([])


def test_mode_basic():
    assert mode([1, 2, 2, 3]) == 2


def test_mode_single():
    assert mode([9]) == 9


def test_mode_ties_smallest():
    assert mode([3, 1, 3, 1]) == 1


def test_variance_empty():
    with pytest.raises(ValueError):
        variance([])


def test_variance_sample():
    assert variance([1, 2, 3, 4]) == pytest.approx(1.6666666666666667)


def test_variance_population():
    assert variance([1, 2, 3, 4], sample=False) == pytest.approx(1.25)


def test_variance_single_sample_raises():
    with pytest.raises(ValueError):
        variance([5])


def test_stdev_sample():
    assert stdev([1, 2, 3, 4]) == pytest.approx(1.2909944487358056)


def test_percentile_empty():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_percentile_p0():
    assert percentile([3, 1, 2, 4], 0) == 1


def test_percentile_p100():
    assert percentile([3, 1, 2, 4], 100) == 4


def test_percentile_median():
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)


def test_percentile_single():
    assert percentile([42], 99) == 42


def test_percentile_out_of_range():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 101)


def test_api_mean():
    assert numstats.mean([1, 2, 3, 4]) == 2.5


def test_api_stdev():
    assert numstats.stdev([1, 2, 3, 4]) == pytest.approx(1.2909944487358056)


def test_api_running_stats():
    stats = numstats.RunningStats()
    stats.add_all([1, 2, 3, 4])
    assert stats.mean == pytest.approx(2.5)
