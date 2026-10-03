# Copyright (c) CommunityPoke contributors.
"""Attendee discovery and the invitation picker dialog.

Candidate attendees are:
  * Sims in the host's relationship tracker (Sims they have met), and
  * Sims in the host's household, and
  * Sims currently instanced on the lot.

Dead Sims (ghosts), infants/toddlers filter-free (kept simple), and the host
themselves are excluded.
"""

from ui.ui_dialog_picker import SimPickerRow, UiDialogObjectPicker, UiSimPicker

import services
import sims4.log

from funeral_mod.config import FuneralConfig
from funeral_mod.factories import create_factory_wrapper
from funeral_mod.funds import can_afford, charge_attendee
from funeral_mod.localize import localized, localized_factory
from funeral_mod.logic import dedupe_sim_ids

logger = sims4.log.Logger('funeral_mod.attendees')


def _is_living(sim_info):
    """Exclude ghosts/dead sims from being funeral guests."""
    try:
        death_tracker = getattr(sim_info, 'death_tracker', None)
        if death_tracker is not None and death_tracker.is_ghost():
            return False
    except Exception:
        pass
    try:
        if sim_info.is_ghost:
            return False
    except Exception:
        pass
    return True


def _iter_household_sim_infos(sim_info):
    household = getattr(sim_info, 'household', None)
    if household is None:
        return
    for member in getattr(household, 'sim_infos', ()):
        yield member


def _iter_relationship_sim_infos(sim_info):
    try:
        yield from services.relationship_service().get_target_sim_infos(sim_info.sim_id)
    except Exception:
        logger.exception('failed to enumerate relationships for %s', sim_info)


def _iter_instanced_sim_infos():
    sim_manager = services.sim_info_manager()
    try:
        for sim in sim_manager.instanced_sims_gen():
            sim_info = getattr(sim, 'sim_info', None)
            if sim_info is not None:
                yield sim_info
    except Exception:
        logger.exception('failed to enumerate instanced sims')


def gather_attendee_candidates(host_sim_info, config=FuneralConfig):
    """Return ``[(sim_info, affordable), ...]`` rows for the invite picker."""
    seen_ids = {host_sim_info.sim_id}
    rows = []

    def add(sim_info):
        if sim_info is None:
            return
        sim_id = getattr(sim_info, 'sim_id', None)
        if sim_id is None or sim_id in seen_ids:
            return
        seen_ids.add(sim_id)
        if not _is_living(sim_info):
            return
        affordable = can_afford(sim_info, config.ATTENDEE_FEE)
        if not affordable and not config.SHOW_UNAFFORDABLE_ATTENDEES:
            return
        rows.append((sim_info, affordable))

    for sim_info in _iter_household_sim_infos(host_sim_info):
        add(sim_info)
    for sim_info in _iter_relationship_sim_infos(host_sim_info):
        add(sim_info)
    for sim_info in _iter_instanced_sim_infos():
        add(sim_info)

    return rows[: config.MAX_ATTENDEES]


def build_picker(owner_sim, rows, config=FuneralConfig):
    """Construct the multi-select Sim picker for invites.

    Returns a UiSimPicker dialog ready to ``show_dialog()``, or None if the
    dialog could not be constructed in this game version.
    """
    try:
        max_sel = create_factory_wrapper(
            UiDialogObjectPicker._MaxSelectableStatic,
            number_selectable=max(1, config.MAX_ATTENDEES),
        )
        factory = create_factory_wrapper(
            UiSimPicker,
            title=localized_factory('Invite Mourners'),
            text=localized_factory(
                'Choose who attends the funeral. Each attendee pays §{} to attend.'.format(config.ATTENDEE_FEE)
            ),
            min_selectable=0,
            max_selectable=max_sel,
        )
    except Exception:
        logger.exception('failed to build UiSimPicker factory')
        return None

    try:
        dialog = factory(owner_sim)
    except Exception:
        logger.exception('failed to instantiate UiSimPicker')
        return None

    for (sim_info, affordable) in rows:
        try:
            row = SimPickerRow(
                sim_id=sim_info.sim_id,
                tag=sim_info.sim_id,
            )
            if not affordable:
                row.is_enable = False
                row.row_tooltip = localized(
                    'Their household cannot afford §{} to attend.'.format(config.ATTENDEE_FEE)
                )
            dialog.add_row(row)
        except Exception:
            logger.exception('failed to add picker row for %s', sim_info)
    return dialog


def collect_picked_sim_ids(dialog):
    """Extract picked attendee sim ids from a responded picker dialog."""
    try:
        return dedupe_sim_ids(dialog.get_result_tags())
    except Exception:
        logger.exception('failed to read picker results')
        return []


def charge_attendees(attendee_infos, config=FuneralConfig, zone_id=None):
    """Charge every attendee's household ``ATTENDEE_FEE``.

    Returns the list of sim_ids that were actually charged.  NPC households
    are debited for real (we pass ``sim=None`` to ``try_remove`` so the NPC
    free-pass in EA's funds code does not apply).
    """
    paid = []
    for sim_info in attendee_infos:
        if charge_attendee(sim_info, config.ATTENDEE_FEE, zone_id=zone_id):
            paid.append(getattr(sim_info, 'sim_id', None))
    return [sim_id for sim_id in paid if sim_id is not None]
