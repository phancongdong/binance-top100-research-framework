"""Explicit, half-open temporal study boundaries."""
from dataclasses import dataclass
from datetime import datetime, timedelta


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self):
        aware(self.start)
        aware(self.end)
        if self.start >= self.end or self.start.tzinfo != self.end.tzinfo:
            raise ValueError("invalid interval or inconsistent timezone")

    def contains(self, instant: datetime) -> bool:
        aware(instant)
        return self.start <= instant < self.end

    def mapping(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass(frozen=True)
class Fold:
    name: str
    train: Interval
    oos: Interval
    train_cutoff: datetime

    def mapping(self) -> dict:
        return {"name": self.name, "train": self.train.mapping(), "oos": self.oos.mapping(), "train_cutoff": self.train_cutoff.isoformat()}


@dataclass(frozen=True)
class StudySpec:
    study_id: str
    folds: tuple[Fold, ...]
    holdout: Interval
    purge_days: int

    def validate(self) -> None:
        if not self.study_id or not self.folds or type(self.purge_days) is not int or self.purge_days < 0:
            raise ValueError("study ID, folds and nonnegative purge are required")
        timezone = self.holdout.start.tzinfo
        names = set()
        last_oos_end = None
        for fold in self.folds:
            aware(fold.train_cutoff)
            if not fold.name or fold.name in names:
                raise ValueError("fold names must be unique")
            names.add(fold.name)
            if any(value.tzinfo != timezone for value in (fold.train.start, fold.train.end, fold.oos.start, fold.oos.end, fold.train_cutoff)):
                raise ValueError("inconsistent timezone")
            if fold.train.end > fold.train_cutoff or fold.train_cutoff + timedelta(days=self.purge_days) > fold.oos.start:
                raise ValueError("train cutoff or purge violated")
            if last_oos_end is not None and fold.oos.start < last_oos_end:
                raise ValueError("OOS folds overlap or are out of order")
            if fold.oos.end > self.holdout.start or fold.train.end > self.holdout.start:
                raise ValueError("terminal holdout overlaps training or OOS")
            last_oos_end = fold.oos.end

    def mapping(self) -> dict:
        self.validate()
        return {"study_id": self.study_id, "timezone": str(self.holdout.start.tzinfo), "folds": [fold.mapping() for fold in self.folds], "holdout": self.holdout.mapping(), "purge_days": self.purge_days}
