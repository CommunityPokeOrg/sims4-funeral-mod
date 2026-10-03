# Copyright (c) CommunityPoke contributors.
"""Pure-Python funeral economy/session logic.

Everything in this module is deliberately free of imports from the game's
``sims4``/``services`` modules so it can be unit tested outside the game.
The game-facing layer in :mod:`funeral_mod.interactions` and
:mod:`funeral_mod.event` calls into these helpers with real Sim objects.
"""

from funeral_mod.config import FuneralConfig


def host_can_afford(funds, config=FuneralConfig):
    """True when a household funds-like object can pay the host fee."""
    return can_afford(funds, config.HOST_FEE)


def can_afford(funds, amount):
    """``funds`` is anything with ``money`` or a ``can_afford()`` method."""
    if funds is None:
        return False
    checker = getattr(funds, 'can_afford', None)
    if callable(checker):
        try:
            return bool(checker(amount))
        except Exception:
            pass
    money = getattr(funds, 'money', None)
    return money is not None and money >= amount


def total_cost(num_attendees, config=FuneralConfig):
    """The total Simoleons that move for a funeral of ``num_attendees``.

    = host fee + attendee fees.  Attendee fees leave the *attendees'*
    households (the host's fee leaves the host's household), so this helper
    is only for reporting/summaries, not for a single debit.
    """
    return config.HOST_FEE + config.ATTENDEE_FEE * max(0, int(num_attendees))


def clamp_attendees(candidates, config=FuneralConfig):
    """Enforce ``MAX_ATTENDEES`` on a candidate list (keeps first N)."""
    return list(candidates)[: max(0, config.MAX_ATTENDEES)]


def dedupe_sim_ids(sim_ids):
    """De-duplicate sim ids while preserving order."""
    seen = set()
    result = []
    for sim_id in sim_ids:
        if sim_id in seen:
            continue
        seen.add(sim_id)
        result.append(sim_id)
    return result


def plan_charges(host_funds, attendee_funds_list, config=FuneralConfig):
    """Work out what a funeral would charge before anything is debited.

    Returns a dict:
      affordable            - host can pay the fee
      host_fee              - amount to debit from the host household
      affordable_attendees  - list of attendee funds that can be charged
      unaffordable_count    - how many attendees could not pay
      total_attendee_fees   - total simoleons charged to attendees
      grand_total           - host fee + total attendee fees
    """
    affordable_attendees = [f for f in attendee_funds_list if can_afford(f, config.ATTENDEE_FEE)]
    total_attendee_fees = config.ATTENDEE_FEE * len(affordable_attendees)
    return {
        'affordable': can_afford(host_funds, config.HOST_FEE),
        'host_fee': config.HOST_FEE,
        'affordable_attendees': affordable_attendees,
        'unaffordable_count': len(attendee_funds_list) - len(affordable_attendees),
        'total_attendee_fees': total_attendee_fees,
        'grand_total': config.HOST_FEE + total_attendee_fees,
    }
