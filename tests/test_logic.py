# Copyright (c) CommunityPoke contributors.
"""Unit tests for the pure-Python parts of the mod.

These run outside the game (the game modules they touch only depend on
``funeral_mod.config``), exercising the required economy rules:

* hosting costs §764 paid by the host
* each attendee costs §63 to attend
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from funeral_mod.config import FuneralConfig
from funeral_mod.logic import (
    can_afford,
    clamp_attendees,
    dedupe_sim_ids,
    host_can_afford,
    plan_charges,
    total_cost,
)


class FakeFunds:

    def __init__(self, money):
        self.money = money


class TestRequiredFees(unittest.TestCase):
    """The mod's headline numbers from the feature request."""

    def test_host_fee_is_764(self):
        self.assertEqual(FuneralConfig.HOST_FEE, 764)

    def test_attendee_fee_is_63(self):
        self.assertEqual(FuneralConfig.ATTENDEE_FEE, 63)


class TestAffordability(unittest.TestCase):

    def test_host_can_afford_exact(self):
        self.assertTrue(host_can_afford(FakeFunds(764)))

    def test_host_cannot_afford_under_fee(self):
        self.assertFalse(host_can_afford(FakeFunds(763)))

    def test_host_cannot_afford_zero(self):
        self.assertFalse(host_can_afford(FakeFunds(0)))

    def test_can_afford_none_funds(self):
        self.assertFalse(can_afford(None, 1))


class TestCosts(unittest.TestCase):

    def test_total_cost_no_attendees(self):
        self.assertEqual(total_cost(0), 764)

    def test_total_cost_one_attendee(self):
        self.assertEqual(total_cost(1), 764 + 63)

    def test_total_cost_many_attendees(self):
        self.assertEqual(total_cost(12), 764 + 63 * 12)

    def test_total_cost_negative_attendees_clamped(self):
        self.assertEqual(total_cost(-5), 764)


class TestPlanCharges(unittest.TestCase):

    def test_all_affordable(self):
        plan = plan_charges(FakeFunds(1000), [FakeFunds(100), FakeFunds(63)])
        self.assertTrue(plan['affordable'])
        self.assertEqual(plan['host_fee'], 764)
        self.assertEqual(len(plan['affordable_attendees']), 2)
        self.assertEqual(plan['unaffordable_count'], 0)
        self.assertEqual(plan['grand_total'], 764 + 126)

    def test_unaffordable_attendee_skipped(self):
        plan = plan_charges(FakeFunds(900), [FakeFunds(10), FakeFunds(70)])
        self.assertEqual(len(plan['affordable_attendees']), 1)
        self.assertEqual(plan['unaffordable_count'], 1)
        self.assertEqual(plan['grand_total'], 764 + 63)

    def test_broke_host(self):
        plan = plan_charges(FakeFunds(1), [FakeFunds(70)])
        self.assertFalse(plan['affordable'])


class TestAttendeeLists(unittest.TestCase):

    def test_dedupe_preserves_order(self):
        self.assertEqual(dedupe_sim_ids([1, 2, 2, 3, 1]), [1, 2, 3])

    def test_clamp_to_max(self):
        ids = list(range(50))
        self.assertEqual(len(clamp_attendees(ids)), FuneralConfig.MAX_ATTENDEES)


if __name__ == '__main__':
    unittest.main()
