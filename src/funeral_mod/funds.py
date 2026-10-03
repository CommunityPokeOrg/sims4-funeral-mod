# Copyright (c) CommunityPoke contributors.
"""Simoleon plumbing.

Charges are made through ``household.funds`` (a ``FamilyFunds`` instance,
part of the game's own economy system) so the usual money-change UI and
telemetry behave exactly like a normal purchase.
"""

from protocolbuffers import Consts_pb2

import sims4.log

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


def charge(sim_info, amount, *, sim=None):
    """Debit ``amount`` simoleons from ``sim_info``'s household.

    ``sim`` is passed to ``try_remove`` purely for bookkeeping; leave it as
    the default ``None`` so NPC households are debited for real (EA skips
    debiting when it is handed an NPC Sim instance).

    Returns True when the full amount was removed.
    """
    funds = get_funds(sim_info)
    if funds is None or amount is None or amount <= 0:
        return False
    try:
        return bool(funds.try_remove(amount, REASON, sim))
    except Exception:
        logger.exception('failed to charge %s simoleons from household of %s', amount, sim_info)
        return False


def charge_attendee(attendee_sim_info, amount):
    """Charge one attendee's household for attending."""
    return charge(attendee_sim_info, amount, sim=None)


def charge_host(host_sim_info, amount, host_sim=None):
    """Charge the host's household the funeral fee."""
    return charge(host_sim_info, amount, sim=host_sim)


def refund(sim_info, amount, sim=None):
    """Give simoleons back to a household (e.g. cancelled funeral)."""
    funds = get_funds(sim_info)
    if funds is None or amount is None or amount <= 0:
        return False
    try:
        funds.add(amount, REASON, sim)
        return True
    except Exception:
        logger.exception('failed to refund %s simoleons to household of %s', amount, sim_info)
        return False
