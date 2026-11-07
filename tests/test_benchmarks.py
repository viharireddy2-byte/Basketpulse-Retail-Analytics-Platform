import pytest

from benchmarks.bench import fmt_bytes, percentile, render_markdown, summarise
from benchmarks.estimate import pruning_fraction


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([10, 20], 50) == 15
    assert percentile([7], 95) == 7


def test_percentile_empty_raises():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_fmt_bytes():
    assert fmt_bytes(512) == "512 B"
    assert fmt_bytes(1024 ** 3 * 2.5) == "2.5 GB"


def _rows():
    mk = lambda v, t, b: dict(query="q1", variant=v, elapsed_s=t, bytes_billed=b, slot_ms=100)
    return ([mk("flat_unpartitioned", 4.0, 1000)] * 3 + [mk("flat_partitioned", 2.0, 100)] * 3
            + [mk("nested_part_clustered", 1.0, 10)] * 3)


def test_summarise_speedup_and_reduction_against_baseline():
    rows = {r["variant"]: r for r in summarise(_rows())}
    assert rows["flat_unpartitioned"]["speedup_x"] == 1
    assert rows["flat_partitioned"]["bytes_reduction_x"] == 10
    assert rows["nested_part_clustered"]["speedup_x"] == 4
    assert rows["nested_part_clustered"]["bytes_reduction_x"] == 100


def test_markdown_contains_all_layouts():
    meta = dict(run_at="2026-01-01T00:00:00+00:00", project="p", location="US", runs=3, transactions=10, line_items=60)
    md = render_markdown(meta, summarise(_rows()))
    assert md.count("| q1 |") == 3 and "100.0x" in md


def test_pruning_fraction_bounds():
    assert pruning_fraction(7, 730) == pytest.approx(7 / 730)
    assert pruning_fraction(1000, 730) == 1.0
    with pytest.raises(ValueError):
        pruning_fraction(7, 0)
