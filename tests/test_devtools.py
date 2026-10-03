# Copyright (c) CommunityPoke contributors.
"""Unit tests for the pure-Python devtools helpers.

Everything tested here runs outside the game: the debug-log file writer
(stdlib only), the debit bookkeeping records, and the formatters the
``funeral.*`` cheat commands print.
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from funeral_mod import debug_log
from funeral_mod.config import FuneralConfig
from funeral_mod.dbg import (
    DebitRecord,
    describe_event,
    format_debit_summary,
    format_funds_row,
    format_money,
    format_object_check,
    summarize_debits,
)


class FakeEvent(SimpleNamespace):
    pass


def _event(**overrides):
    base = dict(
        zone_id=7, host_sim_id=1, deceased_sim_id=2, urnstone_id=3,
        attendee_ids=(4, 5), paid_attendee_ids={4}, eulogies=1,
        host_fee=764, attendee_fee=63,
    )
    base.update(overrides)
    return FakeEvent(**base)


class TestDebugConfig(unittest.TestCase):

    def test_debug_logging_defaults_on(self):
        self.assertTrue(FuneralConfig.DEBUG_LOGGING)

    def test_log_filename(self):
        self.assertEqual(FuneralConfig.DEBUG_LOG_FILENAME,
                         'funeral_mod_debug.log')


class TestFormatMoney(unittest.TestCase):

    def test_amount(self):
        self.assertEqual(format_money(764), '§764')

    def test_none(self):
        self.assertEqual(format_money(None), '§?')

    def test_garbage(self):
        self.assertEqual(format_money('nope'), '§?')


class TestDebitRecord(unittest.TestCase):

    def test_observed_delta(self):
        r = DebitRecord(1, 'host', 764, 1000, 236, True)
        self.assertEqual(r.observed_delta, 764)
        self.assertTrue(r.verified)

    def test_delta_none_when_unreadable(self):
        r = DebitRecord(1, 'attendee', 63, None, None, True)
        self.assertIsNone(r.observed_delta)
        self.assertFalse(r.verified)

    def test_wrong_delta_not_verified(self):
        r = DebitRecord(1, 'attendee', 63, 1000, 1000, True)
        self.assertEqual(r.observed_delta, 0)
        self.assertFalse(r.verified)
        self.assertIn('delta=-§0', r.line())

    def test_line_contains_key_fields(self):
        r = DebitRecord(42, 'host', 764, 1000, 236, True, zone_id=7)
        line = r.line()
        self.assertIn('sim=42', line)
        self.assertIn('role=host', line)
        self.assertIn('want=§764', line)
        self.assertIn('funds=§1000->§236', line)
        self.assertIn('verified', line)


class TestDebitSummary(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(
            format_debit_summary([]), 'debits: none recorded yet')

    def test_mixed_records(self):
        records = [
            DebitRecord(1, 'host', 764, 2000, 1236, True),
            DebitRecord(2, 'attendee', 63, 100, 37, True),
            DebitRecord(3, 'attendee', 63, 10, 10, False),
        ]
        s = summarize_debits(records)
        self.assertEqual(s['attempted'], 3)
        self.assertEqual(s['succeeded'], 2)
        self.assertEqual(s['verified'], 2)
        self.assertEqual(s['observed_total'], 764 + 63)
        self.assertEqual(s['expected_total'], 764 + 63)
        line = format_debit_summary(records)
        self.assertIn('3 attempted', line)
        self.assertIn('2 ok', line)


class TestDescribeEvent(unittest.TestCase):

    def test_none(self):
        self.assertEqual(describe_event(None), ['funeral: none active'])

    def test_lines_cover_plan(self):
        lines = describe_event(_event())
        joined = '\n'.join(lines)
        self.assertIn('zone=7', joined)
        self.assertIn('host=1', joined)
        self.assertIn('deceased=2', joined)
        self.assertIn('attendees=2', joined)
        self.assertIn('paid=1', joined)
        self.assertIn('§764', joined)
        self.assertIn('§63', joined)
        self.assertIn('paid_ids=[4]', joined)


class TestFormatObjectCheck(unittest.TestCase):

    def test_ok_and_missing(self):
        line = format_object_check(
            'urnstone_x',
            {'PlanFuneralInteraction': True, 'GiveEulogyInteraction': False},
        )
        self.assertIn('PlanFuneralInteraction=OK', line)
        self.assertIn('GiveEulogyInteraction=MISSING', line)

    def test_empty_report(self):
        self.assertEqual(format_object_check('urn_x', {}),
                         'urn_x: no affordances recorded')


class TestFormatFundsRow(unittest.TestCase):

    def test_affordable(self):
        self.assertEqual(
            format_funds_row('attendee Jane', 5, 100, True),
            'attendee Jane (5): §100 affordable')

    def test_too_expensive(self):
        self.assertIn('TOO EXPENSIVE',
                      format_funds_row('x', 1, 0, False))


class TestDebugLogFile(unittest.TestCase):

    def setUp(self):
        self._saved = dict(debug_log._state)
        self._tmpdir = tempfile.mkdtemp()
        debug_log._state['path'] = os.path.join(
            self._tmpdir, 'funeral_mod_debug.log')
        debug_log._state['enabled'] = True
        debug_log._state['verbose'] = True
        debug_log._state['banner_written'] = False

    def tearDown(self):
        debug_log._state.clear()
        debug_log._state.update(self._saved)

    def test_writes_and_tails(self):
        debug_log.info('hello %s', 'world')
        debug_log.debug('chatter')
        lines = debug_log.tail(10)
        self.assertTrue(any('hello world' in l for l in lines))
        self.assertTrue(any('chatter' in l for l in lines))
        self.assertTrue(any('Funeral Mod' in l for l in lines))

    def test_disabled_writes_nothing(self):
        debug_log._state['enabled'] = False
        debug_log.info('nope')
        self.assertEqual(debug_log.tail(10), [])

    def test_quiet_mode_drops_debug(self):
        debug_log.set_mode('info')
        debug_log.debug('hidden')
        debug_log.info('shown')
        lines = debug_log.tail(10)
        self.assertTrue(any('shown' in l for l in lines))
        self.assertFalse(any('hidden' in l for l in lines))

    def test_set_mode_status(self):
        st = debug_log.set_mode('on')
        self.assertTrue(st['enabled'])
        self.assertTrue(st['verbose'])
        st = debug_log.set_mode('off')
        self.assertFalse(st['enabled'])


if __name__ == '__main__':
    unittest.main()
