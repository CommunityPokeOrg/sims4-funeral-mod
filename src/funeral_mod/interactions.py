# Copyright (c) CommunityPoke contributors.
"""The funeral pie-menu interactions.

All interactions are ``ImmediateSuperInteraction`` subclasses defined purely
in script (no tuning XML).  They are appended onto the ``_super_affordances``
of urnstone/tombstone object tunings and the Sim tuning by
:mod:`funeral_mod.startup`.
"""

from event_testing.results import TestResult
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.resources import Types

import services
import sims4.log

from funeral_mod.attendees import (
    build_picker,
    charge_attendees,
    collect_picked_sim_ids,
    gather_attendee_candidates,
)
from funeral_mod.config import FuneralConfig
from funeral_mod import event as funeral_event
from funeral_mod.funds import can_afford, charge_host, refund
from funeral_mod.localize import localized_factory
from funeral_mod.notifications import show_notification

logger = sims4.log.Logger('funeral_mod.interactions')


def _zone_id():
    try:
        return services.current_zone_id()
    except Exception:
        return 0


def _deceased_sim_info(target):
    """The SimInfo of the dead Sim stored in an urnstone/gravestone."""
    if target is None:
        return None
    try:
        return target.get_stored_sim_info()
    except AttributeError:
        return None
    except Exception:
        logger.exception('failed reading stored sim info from %s', target)
        return None


def _deceased_name(sim_info):
    if sim_info is None:
        return 'the deceased'
    try:
        return '{} {}'.format(sim_info.first_name, sim_info.last_name).strip() or 'the deceased'
    except Exception:
        return 'the deceased'


def _find_tuned_instance_by_keywords(manager_type, keywords):
    """First tuned instance whose name contains any keyword."""
    manager = services.get_instance_manager(manager_type)
    if manager is None:
        return None
    for tuned in getattr(manager, 'types', {}).values():
        name = getattr(tuned, '__name__', '') or ''
        lowered = name.lower()
        if any(keyword in lowered for keyword in keywords):
            return tuned
    return None


def _summon_attendee(sim_id):
    """Bring an off-lot Sim onto the lot (same path as `sims.summon_sim_to_zone`)."""
    try:
        import sims.sim_spawner
        sims.sim_spawner.SimSpawner.load_sim(sim_id)
        return True
    except Exception:
        logger.exception('failed to summon sim %s', sim_id)
        return False


def _apply_mourning_buff(sim_info, config):
    buff = _find_tuned_instance_by_keywords(Types.BUFF, config.MOURNING_BUFF_KEYWORDS)
    if buff is None:
        return False
    try:
        sim_info.add_buff(buff)
        return True
    except Exception:
        logger.exception('failed applying mourning buff to %s', sim_info)
        return False


class PlanFuneralInteraction(ImmediateSuperInteraction):
    """Plan and host a funeral for a dead Sim.

    Appears on urns/gravestones and on Sims.  Charges ``HOST_FEE`` to the
    host's household, then ``ATTENDEE_FEE`` to each invited attendee's
    household, summons the guests, and opens the funeral.
    """

    INSTANCE_SUBCLASSES_ONLY = True

    visible = True
    display_name = localized_factory('Plan Funeral…')
    display_tooltip = localized_factory(
        'Host a funeral for the Sim resting here. '
        'Costs §764 to host; each attendee pays §63 to attend.'
    )
    allow_autonomous = False

    @classmethod
    def _get_host_fee(cls, config):
        return config.HOST_FEE

    @classmethod
    def _test(cls, target, context, config=FuneralConfig, **kwargs):
        sim = getattr(context, 'sim', None)
        if sim is None:
            return TestResult(False, 'Funerals need a Sim host.')
        sim_info = getattr(sim, 'sim_info', None)
        if sim_info is None:
            return TestResult(False, 'Funerals need a Sim host.')

        zone_id = _zone_id()
        if funeral_event.has_active_funeral(zone_id):
            return TestResult(False, 'A funeral is already in progress.')

        if not can_afford(sim_info, config.HOST_FEE):
            return TestResult(
                False,
                'Hosting a funeral costs §{}. You cannot afford it.'.format(config.HOST_FEE),
            )
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline, config=FuneralConfig):
        host_sim = self.sim
        host_info = getattr(host_sim, 'sim_info', None)
        if host_info is None:
            return False

        zone_id = _zone_id()
        if funeral_event.has_active_funeral(zone_id):
            return False

        deceased_info = _deceased_sim_info(self.target)
        deceased_name = _deceased_name(deceased_info)

        rows = gather_attendee_candidates(host_info, config)
        if not rows:
            # Nobody to invite: still allow a private funeral for the fee.
            self._start_funeral(zone_id, host_info, deceased_info, deceased_name, [])
            return True

        dialog = build_picker(host_sim, rows, config)
        if dialog is None:
            # Picker failed to build: degrade to a private funeral rather
            # than doing nothing at all.
            logger.warn('attendee picker unavailable; running private funeral')
            self._start_funeral(zone_id, host_info, deceased_info, deceased_name, [])
            return True

        attendee_map = {sim_info.sim_id: sim_info for (sim_info, _affordable) in rows}

        def on_response(picker_dialog):
            if not getattr(picker_dialog, 'accepted', False):
                return
            picked_ids = collect_picked_sim_ids(picker_dialog)
            picked_infos = [attendee_map[sim_id] for sim_id in picked_ids if sim_id in attendee_map]
            self._start_funeral(zone_id, host_info, deceased_info, deceased_name, picked_infos)

        try:
            dialog.show_dialog(on_response=on_response)
        except Exception:
            logger.exception('failed to show attendee picker')
            return False
        return True

    def _start_funeral(self, zone_id, host_info, deceased_info, deceased_name, attendee_infos, config=FuneralConfig):
        # Host fee first; abort cleanly if the charge fails.
        if not charge_host(host_info, config.HOST_FEE, host_sim=self.sim):
            show_notification(host_info, 'The funeral could not be paid for.', title='Funeral')
            return

        paid_ids = charge_attendees(attendee_infos, config)

        ev = funeral_event.FuneralEvent(
            zone_id=zone_id,
            host_sim_id=host_info.sim_id,
            deceased_sim_id=getattr(deceased_info, 'sim_id', None),
            urnstone_id=getattr(self.target, 'id', None),
            attendee_ids=[getattr(info, 'sim_id', None) for info in attendee_infos],
            host_fee=config.HOST_FEE,
            attendee_fee=config.ATTENDEE_FEE,
        )
        ev.paid_attendee_ids.update(paid_ids)
        funeral_event.start_event(ev)

        if config.SUMMON_ATTENDEES:
            for sim_id in ev.attendee_ids:
                _summon_attendee(sim_id)

        _apply_mourning_buff(host_info, config)
        for info in attendee_infos:
            _apply_mourning_buff(info, config)

        if attendee_infos:
            message = 'Funeral for {} has begun. {} mourner(s) attending (§{} each).'.format(
                deceased_name, len(attendee_infos), config.ATTENDEE_FEE,
            )
        else:
            message = 'A private funeral for {} has begun.'.format(deceased_name)
        show_notification(host_info, message, title='Funeral')


class GiveEulogyInteraction(ImmediateSuperInteraction):
    """A mourner speaks about the deceased during an active funeral."""

    INSTANCE_SUBCLASSES_ONLY = True

    visible = True
    display_name = localized_factory('Give Eulogy')
    display_tooltip = localized_factory('Say a few words in honour of the deceased.')
    allow_autonomous = False

    @classmethod
    def _test(cls, target, context, **kwargs):
        sim = getattr(context, 'sim', None)
        sim_info = getattr(sim, 'sim_info', None)
        if sim_info is None:
            return TestResult(False)
        ev = funeral_event.get_event(_zone_id())
        if ev is None:
            return TestResult(False, 'There is no funeral in progress.')
        if not funeral_event.is_attendee(ev, sim_info.sim_id) and not funeral_event.is_host(ev, sim_info.sim_id):
            return TestResult(False, 'Only funeral attendees can give a eulogy.')
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline, config=FuneralConfig):
        sim_info = getattr(self.sim, 'sim_info', None)
        if sim_info is None:
            return False
        ev = funeral_event.get_event(_zone_id())
        if ev is None:
            return False
        ev.record_eulogy(sim_info.sim_id)
        _apply_mourning_buff(sim_info, config)
        name = _deceased_name(_deceased_sim_info(self.target))
        try:
            speaker = '{}'.format(sim_info.first_name)
        except Exception:
            speaker = 'A mourner'
        show_notification(
            sim_info,
            '{} gave a eulogy for {}.'.format(speaker, name),
            title='Funeral',
        )
        return True


class ConcludeFuneralInteraction(ImmediateSuperInteraction):
    """End an active funeral and show a summary."""

    INSTANCE_SUBCLASSES_ONLY = True

    visible = True
    display_name = localized_factory('Conclude Funeral')
    display_tooltip = localized_factory('End the funeral service.')
    allow_autonomous = False

    @classmethod
    def _test(cls, target, context, **kwargs):
        sim = getattr(context, 'sim', None)
        sim_info = getattr(sim, 'sim_info', None)
        if sim_info is None:
            return TestResult(False)
        ev = funeral_event.get_event(_zone_id())
        if ev is None:
            return TestResult(False, 'There is no funeral in progress.')
        if not funeral_event.is_host(ev, sim_info.sim_id):
            return TestResult(False, 'Only the host can conclude the funeral.')
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline, config=FuneralConfig):
        sim_info = getattr(self.sim, 'sim_info', None)
        ev = funeral_event.get_event(_zone_id())
        if ev is None:
            return False
        funeral_event.end_event(ev.zone_id)
        name = 'the deceased'
        if ev.deceased_sim_id is not None:
            try:
                deceased = services.sim_info_manager().get(ev.deceased_sim_id)
                name = _deceased_name(deceased)
            except Exception:
                pass
        if sim_info is not None:
            show_notification(
                sim_info,
                'The funeral for {} has concluded. {} eulogy(ies) were given by {} attendee(s).'.format(
                    name, ev.eulogies, ev.attendee_count,
                ),
                title='Funeral',
            )
        return True
