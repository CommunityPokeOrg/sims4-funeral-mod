# Copyright (c) CommunityPoke contributors.
"""Runtime state for an in-progress funeral.

Script zip modules get reloaded when a zone loads, so the active-funeral
registry lives inside ``sims4.reload.protected`` to survive those reloads.
"""

import sims4.log
import sims4.reload

logger = sims4.log.Logger('funeral_mod.event')

with sims4.reload.protected(globals()):
    # zone_id -> FuneralEvent.  At most one active funeral per zone.
    ACTIVE_FUNERALS = {}
    # Survives reload too; injected only once per game session.
    INJECTION_DONE = False


class FuneralEvent:
    """One planned/ongoing funeral."""

    def __init__(self, *, zone_id, host_sim_id, deceased_sim_id, urnstone_id, attendee_ids, host_fee, attendee_fee):
        self.zone_id = zone_id
        self.host_sim_id = host_sim_id
        self.deceased_sim_id = deceased_sim_id
        self.urnstone_id = urnstone_id
        self.attendee_ids = tuple(attendee_ids)
        self.host_fee = host_fee
        self.attendee_fee = attendee_fee
        self.eulogies = 0
        self.paid_attendee_ids = set()

    @property
    def attendee_count(self):
        return len(self.attendee_ids)

    def record_eulogy(self, sim_id):
        self.eulogies += 1


def get_event(zone_id):
    return ACTIVE_FUNERALS.get(zone_id)


def has_active_funeral(zone_id):
    return get_event(zone_id) is not None


def start_event(event):
    ACTIVE_FUNERALS[event.zone_id] = event


def end_event(zone_id):
    return ACTIVE_FUNERALS.pop(zone_id, None)


def is_host(event, sim_id):
    return event is not None and event.host_sim_id == sim_id


def is_attendee(event, sim_id):
    return event is not None and sim_id in event.attendee_ids
