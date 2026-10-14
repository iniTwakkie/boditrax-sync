"""Metric map sanity tests."""

from __future__ import annotations

from boditrax_sync.metrics import METRIC_COLUMNS, METRIC_UNITS, METRICS


def test_names_unique_and_non_empty() -> None:
    names = [name for _, (name, _) in METRICS.items()]
    assert len(names) == len(set(names))
    for name, unit in METRICS.values():
        assert name and unit


def test_units_map_consistent() -> None:
    assert METRIC_UNITS["BodyWeight"] == "kg"
    assert METRIC_UNITS["VisceralFatRating"] == "rating"
    assert len(METRIC_UNITS) == len(METRICS)


def test_columns_follow_metric_id_order() -> None:
    assert METRIC_COLUMNS == [name for _, (name, _) in sorted(METRICS.items())]
    assert METRIC_COLUMNS[0] == "BodyWeight"
    assert METRIC_COLUMNS[-1] == "BoditraxScore"
