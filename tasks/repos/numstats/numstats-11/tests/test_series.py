import threading

import pytest

from numstats.running import RunningStats
from numstats.series import cumulative_sum, max_subarray_sum, moving_average, rolling_variance


def test_moving_average_basic():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_one():
    assert moving_average([1, 2, 3], 1) == [1, 2, 3]


def test_moving_average_full_window():
    assert moving_average([1, 2, 3], 3) == [2]


def test_moving_average_empty():
    with pytest.raises(ValueError):
        moving_average([], 2)


def test_moving_average_window_too_small():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)


def test_moving_average_window_too_large():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 4)


def test_rolling_variance_basic():
    assert rolling_variance([1, 2, 3, 4], 3) == pytest.approx([1.0, 1.0])


def test_rolling_variance_window_too_small():
    with pytest.raises(ValueError):
        rolling_variance([1, 2, 3], 1)


def test_cumulative_sum_basic():
    assert cumulative_sum([1, 2, 3, 4]) == [1, 3, 6, 10]


def test_cumulative_sum_empty():
    assert cumulative_sum([]) == []


def test_max_subarray_sum_basic():
    assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6


def test_max_subarray_sum_all_negative():
    assert max_subarray_sum([-3, -1, -2]) == -1


def test_max_subarray_sum_single():
    assert max_subarray_sum([5]) == 5


def test_max_subarray_sum_empty():
    with pytest.raises(ValueError):
        max_subarray_sum([])


def test_running_stats_mean():
    stats = RunningStats()
    for x in [1, 2, 3, 4]:
        stats.add(x)
    assert stats.count == 4
    assert stats.mean == pytest.approx(2.5)


def test_running_stats_variance():
    stats = RunningStats()
    for x in [1, 2, 3, 4]:
        stats.add(x)
    assert stats.variance == pytest.approx(1.6666666666666667)


def test_running_stats_empty():
    stats = RunningStats()
    assert stats.count == 0
    assert stats.variance == 0.0


def test_running_stats_add_all():
    stats = RunningStats()
    stats.add_all([1, 2, 3, 4])
    assert stats.count == 4
    assert stats.mean == pytest.approx(2.5)


def test_running_stats_concurrent_updates():
    stats = RunningStats()
    n_threads = 8
    per_thread = 2000
    barrier = threading.Barrier(n_threads)

    def worker(thread_id):
        barrier.wait()
        for i in range(per_thread):
            stats.add(float(thread_id * per_thread + i))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert stats.count == n_threads * per_thread
