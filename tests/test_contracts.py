import math
import unittest
from datetime import datetime, timezone

from research_framework.spec import Fold, Interval, StudySpec
from research_framework.pit import Listing, RankSnapshot, Revision, eligible_members
from research_framework.etl import Bar, audit_bars, aggregate_bars


def at(day):
    return datetime(2024, 1, day, tzinfo=timezone.utc)


class ContractTests(unittest.TestCase):
    def test_disjoint_and_purged(self):
        StudySpec("synthetic", (Fold("a", Interval(at(1), at(3)), Interval(at(4), at(5)), at(3)),), Interval(at(6), at(8)), 1).validate()
        with self.assertRaises(ValueError):
            StudySpec("x", (Fold("a", Interval(at(1), at(3)), Interval(at(3), at(5)), at(3)),), Interval(at(6), at(8)), 1).validate()
        with self.assertRaises(ValueError):
            StudySpec("x", (Fold("a", Interval(at(1), at(3)), Interval(at(4), at(7)), at(3)),), Interval(at(6), at(8)), 1).validate()
        with self.assertRaises(ValueError):
            Interval(datetime(2024, 1, 1), at(2))

    def test_pit_availability_revision_listing_and_rank(self):
        listings = [Listing("ALPHA", at(1), at(1)), Listing("BETA", at(1), at(4))]
        ranks = [RankSnapshot(at(2), at(2), ("ALPHA", "BETA")), RankSnapshot(at(3), at(5), ("BETA", "ALPHA"))]
        self.assertEqual(eligible_members(at(3), listings, ranks, top_n=1), ("ALPHA",))
        self.assertEqual(eligible_members(at(5), listings, ranks, top_n=1), ("BETA",))
        value = [Revision("ALPHA", at(2), at(2), at(5), 1), Revision("ALPHA", at(2), at(4), at(5), 2)]
        self.assertEqual(Revision.as_of(value, "ALPHA", at(3)), 1)
        self.assertEqual(Revision.as_of(value, "ALPHA", at(4)), 2)
        self.assertEqual(eligible_members(at(5), [Listing("ALPHA", at(1), at(1), at(4), at(4)), Listing("BETA", at(1), at(4))], ranks, 2), ("BETA",))
        with self.assertRaises(ValueError):
            eligible_members(at(5), [Listing("ALPHA", at(1), at(1), at(4), at(6))], ranks, 2)
        with self.assertRaises(ValueError):
            eligible_members(at(3), listings, ranks + [RankSnapshot(at(2), at(2), ("BETA", "ALPHA"))], 1)
        with self.assertRaises(ValueError):
            Revision.as_of(value + [Revision("ALPHA", at(2), at(4), at(5), 3)], "ALPHA", at(4))
        with self.assertRaises(ValueError):
            eligible_members(at(3), [Listing("ALPHA", datetime(2024, 1, 1), at(1))], ranks, 1)

    def test_bars_and_strict_buckets(self):
        from datetime import timedelta
        hour = timedelta(hours=1)
        bars = [Bar(at(1) + hour * index, 2, 3, 1, 2, 4) for index in range(4)]
        self.assertEqual(audit_bars(bars, hour, Interval(at(1), at(1) + hour * 4)).count, 4)
        self.assertEqual(len(aggregate_bars(bars, hour, hour * 2)), 2)
        with self.assertRaises(ValueError):
            audit_bars(bars[:1] + bars[:1], hour, Interval(at(1), at(1) + hour * 2))
        with self.assertRaises(ValueError):
            audit_bars(bars[:1] + bars[2:], hour, Interval(at(1), at(1) + hour * 4))
        with self.assertRaises(ValueError):
            audit_bars([Bar(at(1), 2, 3, 1, 2, math.nan)], hour, Interval(at(1), at(1) + hour))
        with self.assertRaises(ValueError):
            aggregate_bars(bars[:3], hour, hour * 2)
        with self.assertRaises(ValueError):
            aggregate_bars(bars, timedelta(0), hour * 2)
        with self.assertRaises(ValueError):
            audit_bars([Bar(at(1), True, 3, 1, 2, 4)], hour, Interval(at(1), at(1) + hour))
        with self.assertRaises(ValueError):
            audit_bars([Bar(at(1), 0, 3, 0, 2, 4)], hour, Interval(at(1), at(1) + hour))
