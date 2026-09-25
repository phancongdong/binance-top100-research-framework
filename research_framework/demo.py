"""Tiny deterministic fixture; no provider, strategy or investment metrics."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .artifacts import canonical_hash, file_hash
from .etl import Bar, audit_bars
from .pit import Listing, RankSnapshot, Revision, eligible_members
from .spec import Fold, Interval, StudySpec
from .workflow import Workflow


def moment(day: int) -> datetime:
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def fixture() -> tuple[StudySpec, dict]:
    spec = StudySpec("synthetic-example", (Fold("example", Interval(moment(1), moment(3)), Interval(moment(4), moment(5)), moment(3)),), Interval(moment(6), moment(8)), 1)
    source = {"listed": ["SAMPLE_A", "SAMPLE_B"], "rank_snapshot_available_at": moment(2).isoformat(), "bar_count": 4}
    return spec, source


class SyntheticAdapter:
    def __init__(self, spec: StudySpec, source: dict):
        self.spec = spec
        self.source = source

    def execute(self, phase: str, context: dict) -> dict:
        if phase == "RESERVE_HOLDOUT":
            return {"accepted": True, "holdout": self.spec.holdout.mapping(), "reservation": "synthetic_only"}
        if phase == "FREEZE_SPEC":
            self.spec.validate()
            return {"accepted": True, "spec": self.spec.mapping()}
        if phase == "SOURCE_AUDIT":
            listings = [Listing("SAMPLE_A", moment(1), moment(1)), Listing("SAMPLE_B", moment(1), moment(3))]
            snapshot = [RankSnapshot(moment(2), moment(2), ("SAMPLE_A", "SAMPLE_B"))]
            selected = eligible_members(moment(2), listings, snapshot)
            if selected != ("SAMPLE_A",):
                raise ValueError("synthetic source PIT check failed")
            return {"accepted": True, "synthetic_record_count": len(selected), "source_hash": canonical_hash(self.source)}
        if phase == "ETL_AUDIT":
            hour = timedelta(hours=1)
            bars = [Bar(moment(1) + hour * index, 2, 3, 1, 2, 4) for index in range(self.source["bar_count"])]
            audited = audit_bars(bars, hour, Interval(moment(1), moment(1) + hour * len(bars)))
            return {"accepted": True, "synthetic_record_count": audited.count, "declared_gap_count": len(audited.declared_gaps)}
        if phase == "TRAIN":
            return {"accepted": True, "synthetic_record_count": 2}
        if phase == "LOCK":
            return {"accepted": True, "locked_synthetic_record_count": 2}
        if phase in ("OOS", "PIT", "HOLDOUT"):
            if not context["locked_hash"]:
                raise ValueError("no immutable selection lock")
            if phase == "PIT" and Revision.as_of([Revision("SAMPLE_A", moment(2), moment(2), moment(5), 1), Revision("SAMPLE_A", moment(2), moment(4), moment(5), 2)], "SAMPLE_A", moment(3)) != 1:
                raise ValueError("future revision visible")
            if phase == "HOLDOUT":
                rows = tuple("reserved" for _ in range(1))
                return {"accepted": True, "synthetic_record_count": len(rows), "lock_artifact_hash": context["locked_hash"], "opened_once": True}
            return {"accepted": True, "synthetic_record_count": 1, "lock_artifact_hash": context["locked_hash"]}
        if phase == "FINALIZE":
            return {"accepted": True, "classification": "SYNTHETIC_WORKFLOW_DEMO", "research_authority": "NONE"}
        raise ValueError("unknown phase")


def demo_workflow(output: Path) -> Workflow:
    spec, source = fixture()
    package = Path(__file__).parent
    code_hash = canonical_hash({path.name: file_hash(path) for path in sorted(package.glob("*.py"))})
    return Workflow(output, canonical_hash(spec.mapping()), code_hash, canonical_hash(source), SyntheticAdapter(spec, source))
