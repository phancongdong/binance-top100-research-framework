"""Point-in-time input checks; provider historical authenticity remains external."""
from dataclasses import dataclass
from datetime import datetime

from .spec import aware


@dataclass(frozen=True)
class Listing:
    symbol: str
    effective_from: datetime
    available_at: datetime
    effective_to: datetime | None = None
    end_available_at: datetime | None = None


@dataclass(frozen=True)
class RankSnapshot:
    effective_from: datetime
    available_at: datetime
    ranked: tuple[str, ...]


@dataclass(frozen=True)
class Revision:
    key: str
    effective_from: datetime
    available_at: datetime
    effective_to: datetime
    value: object

    @staticmethod
    def as_of(records: list["Revision"], key: str, instant: datetime) -> object:
        aware(instant)
        for record in records:
            for value in (record.effective_from, record.available_at, record.effective_to):
                aware(value)
            if record.effective_to <= record.effective_from:
                raise ValueError("invalid revision interval")
        eligible = [record for record in records if record.key == key and record.effective_from <= instant < record.effective_to and record.available_at <= instant]
        if not eligible:
            raise ValueError("no available revision at decision time")
        ranked = sorted(eligible, key=lambda record: (record.available_at, record.effective_from), reverse=True)
        if len(ranked) > 1 and (ranked[0].available_at, ranked[0].effective_from) == (ranked[1].available_at, ranked[1].effective_from):
            raise ValueError("ambiguous revision")
        return ranked[0].value


def eligible_members(instant: datetime, listings: list[Listing], snapshots: list[RankSnapshot], top_n: int = 100) -> tuple[str, ...]:
    aware(instant)
    if type(top_n) is not int or not 1 <= top_n <= 100:
        raise ValueError("top_n must be in 1..100")
    if len({item.symbol for item in listings}) != len(listings):
        raise ValueError("ambiguous listing records")
    for item in listings:
        aware(item.effective_from)
        aware(item.available_at)
        if item.effective_to is not None:
            aware(item.effective_to)
            if item.end_available_at is None:
                raise ValueError("delisting availability required")
            aware(item.end_available_at)
            if item.effective_to <= item.effective_from:
                raise ValueError("invalid listing interval")
            if item.effective_to <= instant < item.end_available_at:
                raise ValueError("delisting information unavailable at decision time")
        elif item.end_available_at is not None:
            raise ValueError("delisting availability without effective end")
    for snapshot in snapshots:
        aware(snapshot.effective_from)
        aware(snapshot.available_at)
    eligible = [snapshot for snapshot in snapshots if snapshot.available_at <= instant and snapshot.effective_from <= instant]
    if not eligible:
        raise ValueError("no historically available rank snapshot")
    ranked = sorted(eligible, key=lambda item: (item.effective_from, item.available_at), reverse=True)
    if len(ranked) > 1 and (ranked[0].effective_from, ranked[0].available_at) == (ranked[1].effective_from, ranked[1].available_at):
        raise ValueError("ambiguous rank snapshot")
    snapshot = ranked[0]
    if not snapshot.ranked or len(set(snapshot.ranked)) != len(snapshot.ranked):
        raise ValueError("invalid rank snapshot")
    available = {item.symbol for item in listings if item.effective_from <= instant and item.available_at <= instant and (item.effective_to is None or instant < item.effective_to)}
    return tuple(symbol for symbol in snapshot.ranked[:top_n] if symbol in available)
