# Copyright (c) CommunityPoke contributors.
"""Simoleon plumbing.

Charges are made through ``household.funds`` (a ``FamilyFunds`` instance,
part of the game's own economy system) so the usual money-change UI and
telemetry behave exactly like a normal purchase.
"""

from protocolbuffers import Consts_pb2

import sims4.log

from funeral_mod import debug_log
from funeral_mod import event as funeral_event
from funeral_mod.dbg import DebitRecord

logger = sims4.log.Logger('funeral_mod.funds')

# Reason code sent with the funds-change op so the game knows why money
# moved.  Consts_pb2.FUNDS_INTERACTION_REWARD is the enum EA uses for
# interaction-driven money changes.
REASON = getattr(Consts_pb2, 'FUNDS_INTERACTION_REWARD', 0)


def get_household(sim_info):
    """Household for a SimInfo (None-safe)."""
    if sim_info is None:
        return None
    return getattr(sim_info, 'household', None)


def get_funds(sim_info):
    """The ``FamilyFunds`` for ``sim_info``'s household."""
    household = get_household(sim_info)
    if household is None:
        return None
    return getattr(household, 'funds', None)


def can_afford(sim_info, amount):
    """True if ``sim_info``'s household can pay ``amount`` simoleons."""
    funds = get_funds(sim_info)
    if funds is None:
        return False
    try:
        return bool(funds.can_afford(amount))
    except AttributeError:
        return getattr(funds, 'money', 0) >= amount


def _read_money(funds):
    """Best-effort read of a FamilyFunds balance (None when unreadable)."""
    try:
        return getattr(funds, 'money', None)
    except Exception:
        return None


def charge(sim_info, amount, *, sim=None, role='misc', zone_id=None):
    """Debit ``amount`` simoleons from ``sim_info``'s household.

    ``sim`` is passed to ``try_remove`` purely for bookkeeping; leave it as
    the default ``None`` so NPC households are debited for real (EA skips
    debiting when it is handed an NPC Sim instance).

    Every attempt is written to the debug log and recorded as a
    :class:`funeral_mod.dbg.DebitRecord` with the household balance before
    and after, so `funeral.verify`/`funeral.plan` can confirm the money
    actually moved.  Returns True when the full amount was removed.
    """
    funds = get_funds(sim_info)
    sim_id = getattr(sim_info, 'sim_id', None)
    if funds is None or amount is None or amount <= 0:
        record = DebitRecord(sim_id, role, amount, None, None, False,
                             note='no funds or bad amount', zone_id=zone_id)
        funeral_event.record_debit(record)
        debug_log.info('%s', record.line())
        return False
    before = _read_money(funds)
    try:
        ok = bool(funds.try_remove(amount, REASON, sim))
    except Exception:
        logger.exception('failed to charge %s simoleons from household of %s', amount, sim_info)
        debug_log.exception('charge threw: sim=%s amount=%s', sim_id, amount)
        ok = False
    after = _read_money(funds)
    record = DebitRecord(sim_id, role, amount, before, after, ok,
                         zone_id=zone_id)
    funeral_event.record_debit(record)
    debug_log.info('%s', record.line())
    return ok


def charge_attendee(attendee_sim_info, amount, zone_id=None):
    """Charge one attendee's household for attending."""
    return charge(attendee_sim_info, amount, sim=None,
                  role='attendee', zone_id=zone_id)


def charge_host(host_sim_info, amount, host_sim=None, zone_id=None):
    """Charge the host's household the funeral fee."""
    return charge(host_sim_info, amount, sim=host_sim,
                  role='host', zone_id=zone_id)


def refund(sim_info, amount, sim=None, zone_id=None):
    """Give simoleons back to a household (e.g. cancelled funeral)."""
    funds = get_funds(sim_info)
    if funds is None or amount is None or amount <= 0:
        return False
    sim_id = getattr(sim_info, 'sim_id', None)
    before = _read_money(funds)
    try:
        funds.add(amount, REASON, sim)
    except Exception:
        logger.exception('failed to refund %s simoleons to household of %s', amount, sim_info)
        debug_log.exception('refund threw: sim=%s amount=%s', sim_id, amount)
        return False
    after = _read_money(funds)
    record = DebitRecord(sim_id, 'refund', amount, before, after, True,
                         zone_id=zone_id)
    funeral_event.record_debit(record)
    debug_log.info('%s', record.line())
    return True
