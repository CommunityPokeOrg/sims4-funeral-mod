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
    # What the affordance injection actually did, for `funeral.verify`:
    #   {'sim': {'name': str, 'affordances': {cls_name: present}},
    #    'objects': [{'name': str, 'affordances': {cls_name: present}}],
    #    'phones': [same shape], 'types_count': int}
    INJECTION_REPORT = {'sim': None, 'objects': [], 'phones': [],
                        'types_count': 0}
    # Every attempted household debit (dbg.DebitRecord), oldest first.
    # Capped so a long session can't grow it forever.
    DEBIT_LOG = []


_MAX_DEBIT_LOG = 200


def record_debit(record):
    """Append a dbg.DebitRecord to the session debit log."""
    DEBIT_LOG.append(record)
    if len(DEBIT_LOG) > _MAX_DEBIT_LOG:
        del DEBIT_LOG[: len(DEBIT_LOG) - _MAX_DEBIT_LOG]
    return record


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
