# Copyright (c) CommunityPoke contributors.
"""Cheat-console commands, mostly for debugging and automated testing.

Open the cheat console (Ctrl+Shift+C) and type:

    funeral.status          – report whether a funeral is active and dump its data
    funeral.prices          – print the configured fees
    funeral.end             – conclude the active funeral in this zone
"""

from sims4.commands import Command, CommandType, Output

import services

from funeral_mod import event as funeral_event
from funeral_mod.config import FuneralConfig
from funeral_mod.mod_info import MOD_NAME, MOD_VERSION


@Command('funeral.prices', command_type=CommandType.Live)
def _funeral_prices(_connection=None):
    output = Output(_connection)
    output('{} v{} — host fee: §{}, attendee fee: §{}, max attendees: {}'.format(
        MOD_NAME, MOD_VERSION,
        FuneralConfig.HOST_FEE, FuneralConfig.ATTENDEE_FEE,
        FuneralConfig.MAX_ATTENDEES,
    ))
    return True


@Command('funeral.status', command_type=CommandType.Live)
def _funeral_status(_connection=None):
    output = Output(_connection)
    try:
        zone_id = services.current_zone_id()
    except Exception:
        zone_id = 0
    ev = funeral_event.get_event(zone_id)
    if ev is None:
        output('funeral: none active in zone {}'.format(zone_id))
        return True
    output(
        'funeral: host={} deceased={} urnstone={} attendees={} eulogies={} host_fee=§{} attendee_fee=§{}'.format(
            ev.host_sim_id, ev.deceased_sim_id, ev.urnstone_id,
            list(ev.attendee_ids), ev.eulogies, ev.host_fee, ev.attendee_fee,
        )
    )
    return True


@Command('funeral.end', command_type=CommandType.Live)
def _funeral_end(_connection=None):
    output = Output(_connection)
    try:
        zone_id = services.current_zone_id()
    except Exception:
        zone_id = 0
    if funeral_event.end_event(zone_id) is None:
        output('funeral: none active to end')
        return False
    output('funeral: ended')
    return True
