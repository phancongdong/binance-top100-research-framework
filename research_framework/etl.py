"""Finite synthetic bar audit and complete-bucket aggregation."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from .spec import Interval, aware


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class BarAudit:
    count: int
    declared_gaps: tuple[datetime, ...]


def audit_bars(bars: list[Bar], frequency: timedelta, coverage: Interval, declared_gaps: tuple[datetime, ...] = ()) -> BarAudit:
    if frequency <= timedelta(0) or (coverage.end - coverage.start) % frequency or not bars:
        raise ValueError("invalid frequency, coverage or empty bars")
    gaps = set(declared_gaps)
    if len(gaps) != len(declared_gaps) or any(not coverage.contains(gap) or (gap - coverage.start) % frequency for gap in gaps):
        raise ValueError("invalid declared gap")
    previous = None
    observed = set()
    for bar in bars:
        aware(bar.time)
        if not coverage.contains(bar.time) or (bar.time - coverage.start) % frequency or (previous is not None and bar.time <= previous):
            raise ValueError("bar order, uniqueness or alignment violated")
        values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if not all(type(value) in (int, float) and isfinite(value) for value in values) or min(values[:4]) <= 0 or bar.volume < 0 or bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close):
            raise ValueError("bar geometry or finite-value check failed")
        observed.add(bar.time)
        previous = bar.time
    expected = {coverage.start + frequency * index for index in range((coverage.end - coverage.start) // frequency)}
    if observed & gaps or expected - observed != gaps:
        raise ValueError("unaccounted gap, extra bar or declared gap has a bar")
    return BarAudit(len(bars), tuple(sorted(gaps)))


def aggregate_bars(bars: list[Bar], source: timedelta, target: timedelta) -> list[Bar]:
    if not bars or source <= timedelta(0) or target <= source or target % source:
        raise ValueError("invalid bucket sizes")
    count = target // source
    if len(bars) % count:
        raise ValueError("partial bucket")
    audit_bars(bars, source, Interval(bars[0].time, bars[-1].time + source))
    epoch = datetime(1970, 1, 1, tzinfo=bars[0].time.tzinfo)
    if (bars[0].time - epoch) % target:
        raise ValueError("unaligned bucket")
    result = []
    for index in range(0, len(bars), count):
        bucket = bars[index:index + count]
        result.append(Bar(bucket[0].time, bucket[0].open, max(bar.high for bar in bucket), min(bar.low for bar in bucket), bucket[-1].close, sum(bar.volume for bar in bucket)))
    return result
