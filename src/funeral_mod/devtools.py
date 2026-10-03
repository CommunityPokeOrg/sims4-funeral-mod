# Copyright (c) CommunityPoke contributors.
"""Game-facing collectors behind the ``funeral.*`` debug cheat commands.

Everything that needs ``services``/tuning access lives here so that
:mod:`funeral_mod.commands` stays a thin command table.  All output goes
through the pure formatters in :mod:`funeral_mod.dbg`.
"""

import services
import sims4.log
from sims4.resources import Types

from funeral_mod import debug_log
from funeral_mod import event as funeral_event
from funeral_mod.attendees import gather_attendee_candidates
from funeral_mod.config import FuneralConfig
from funeral_mod.dbg import (
    describe_event,
    filter_debits_for_zone,
    format_debit_summary,
    format_funds_row,
    format_money,
    format_object_check,
    name_matches,
)
from funeral_mod.funds import can_afford, get_funds
from funeral_mod.interactions import (
    ConcludeFuneralInteraction,
    GiveEulogyInteraction,
    PlanFuneralInteraction,
    _find_tuned_instance_by_keywords,
)
from funeral_mod.mod_info import MOD_NAME, MOD_VERSION

logger = sims4.log.Logger('funeral_mod.devtools')

EXPECTED_FUNERAL_AFFORDANCES = (
    PlanFuneralInteraction,
    GiveEulogyInteraction,
    ConcludeFuneralInteraction,
)


def _zone_id():
    try:
        return services.current_zone_id()
    except Exception:
        return 0


def _full_name(sim_info):
    try:
        name = '{} {}'.format(sim_info.first_name, sim_info.last_name).strip()
        return name or str(getattr(sim_info, 'sim_id', '?'))
    except Exception:
        return str(getattr(sim_info, 'sim_id', '?'))


def _money(sim_info):
    return getattr(get_funds(sim_info), 'money', None)


def selected_sim_info():
    """The SimInfo of the currently selected Sim (best effort)."""
    getters = (
        lambda: services.active_sim_info(),
        lambda: services.get_first_client().active_sim.sim_info,
        lambda: services.client_manager().get_first_client().active_sim.sim_info,
    )
    for getter in getters:
        try:
            sim_info = getter()
        except Exception:
            continue
        if sim_info is not None:
            return sim_info
    return None


def _live_affordance_scan(config=FuneralConfig):
    """Re-scan the OBJECT manager right now.

    Returns ``(carriers, missing)``: ``carriers`` is the list of tuned
    object names that currently have PlanFuneralInteraction, ``missing`` is
    the list of keyword-matching objects that do NOT — i.e. urns the menu
    will not appear on.
    """
    carriers = []
    missing = []
    try:
        manager = services.get_instance_manager(Types.OBJECT)
    except Exception:
        return carriers, missing
    if manager is None:
        return carriers, missing
    for tuned in getattr(manager, 'types', {}).values():
        name = getattr(tuned, '__name__', '') or ''
        affordances = getattr(tuned, '_super_affordances', None) or ()
        has_plan = PlanFuneralInteraction in affordances
        if has_plan:
            carriers.append(name)
        looks_funeral = (
            name.lower() == config.SIM_OBJECT_NAME
            or name_matches(name, config.FUNERAL_OBJECT_NAME_KEYWORDS)
        )
        if looks_funeral and not has_plan:
            missing.append(name)
    return carriers, missing


def verify_report(config=FuneralConfig):
    """Lines for `funeral.verify` — menu registration, fees, live state."""
    lines = ['{} v{} — self-check'.format(MOD_NAME, MOD_VERSION)]

    status = debug_log.status()
    lines.append('debug log: {} (enabled={} verbose={}{})'.format(
        status['path'], status['enabled'], status['verbose'],
        ' error={}'.format(status['error']) if status.get('error') else '',
    ))

    fees_ok = (config.HOST_FEE == 764 and config.ATTENDEE_FEE == 63)
    lines.append('fees: host={} attendee={} expected=§764/§63 {}'.format(
        format_money(config.HOST_FEE), format_money(config.ATTENDEE_FEE),
        'OK' if fees_ok else 'MISMATCH',
    ))

    # --- menu registration ---------------------------------------------
    report = funeral_event.INJECTION_REPORT or {}
    lines.append('affordance injection ran: {}'.format(bool(
        funeral_event.INJECTION_DONE)))
    sim_report = report.get('sim')
    if sim_report:
        lines.append('sim object ' + format_object_check(
            sim_report.get('name', '?'), sim_report.get('affordances', {})))
    else:
        lines.append('sim object: NOT INJECTED (Plan Funeral unreachable via Sim clicks)')
    objects = report.get('objects') or []
    lines.append('funeral objects injected at load: {} (manager had {} types)'.format(
        len(objects), report.get('types_count', '?')))
    for entry in objects:
        lines.append('  ' + format_object_check(
            entry.get('name', '?'), entry.get('affordances', {})))
    phones = report.get('phones') or []
    if phones:
        for entry in phones:
            lines.append('  phone ' + format_object_check(
                entry.get('name', '?'), entry.get('affordances', {})))
    else:
        lines.append('phone objects: none matched (no phone-menu entry)')

    carriers, missing = _live_affordance_scan(config)
    lines.append('objects carrying Plan Funeral right now: {}'.format(
        sorted(carriers) if carriers else 'NONE — the pie menu cannot appear'))
    if missing:
        lines.append('keyword-matched objects MISSING the interaction: {}'.format(
            sorted(missing)))

    buff = _find_tuned_instance_by_keywords(Types.BUFF, config.MOURNING_BUFF_KEYWORDS)
    lines.append('mourning buff: {}'.format(
        getattr(buff, '__name__', None) or 'NOT FOUND (mourn mood will be skipped)'))

    # --- live funeral state --------------------------------------------
    zone_id = _zone_id()
    ev = funeral_event.get_event(zone_id)
    lines.append('zone {}:'.format(zone_id))
    lines.extend('  ' + line for line in describe_event(ev))
    lines.append(format_debit_summary(funeral_event.DEBIT_LOG))
    return lines


def plan_lines():
    """Lines for `funeral.plan` — active funeral plus its debits."""
    zone_id = _zone_id()
    ev = funeral_event.get_event(zone_id)
    lines = describe_event(ev)
    debits = filter_debits_for_zone(funeral_event.DEBIT_LOG, zone_id)
    lines.append(format_debit_summary(debits))
    for record in debits[-15:]:
        lines.append('  ' + record.line())
    return lines


def money_lines(config=FuneralConfig):
    """Lines for `funeral.money` — household funds of host/attendees."""
    lines = []
    sim_info = selected_sim_info()
    if sim_info is None:
        return ['no selected Sim (click a Sim first)']
    lines.append(format_funds_row(
        'selected ' + _full_name(sim_info), getattr(sim_info, 'sim_id', None),
        _money(sim_info), can_afford(sim_info, config.HOST_FEE)))
    ev = funeral_event.get_event(_zone_id())
    if ev is None:
        return lines
    try:
        manager = services.sim_info_manager()
    except Exception:
        manager = None
    if manager is None:
        return lines
    ids = [ev.host_sim_id] + [sid for sid in ev.attendee_ids
                              if sid != ev.host_sim_id]
    for sim_id in ids:
        if sim_id is None:
            continue
        try:
            info = manager.get(sim_id)
        except Exception:
            info = None
        if info is None:
            lines.append('  attendee id {}: sim info unavailable'.format(sim_id))
            continue
        role = 'host' if sim_id == ev.host_sim_id else 'attendee'
        paid = sim_id in (ev.paid_attendee_ids or ())
        label = '  {} {}'.format(role, _full_name(info))
        row = format_funds_row(label, sim_id, _money(info),
                               can_afford(info, config.ATTENDEE_FEE))
        if role == 'attendee':
            row += ' paid={}'.format(paid)
        lines.append(row)
    return lines


def objects_lines(keyword=''):
    """Lines for `funeral.objects <keyword>` — scan tuned object names.

    With no keyword, lists every OBJECT tuning name containing
    'urn'/'grave'/'sim'/'phone' and whether it carries Plan Funeral.
    With a keyword, lists every name containing it.
    """
    try:
        manager = services.get_instance_manager(Types.OBJECT)
    except Exception as exc:
        return ['OBJECT instance manager unavailable: {!r}'.format(exc)]
    if manager is None:
        return ['OBJECT instance manager is None']
    keyword = (keyword or '').strip().lower()
    default_keywords = ('urn', 'grave', 'tomb', 'sim', 'phone')
    rows = []
    for tuned in getattr(manager, 'types', {}).values():
        name = getattr(tuned, '__name__', '') or ''
        if keyword:
            hit = keyword in name.lower()
        else:
            hit = name_matches(name, default_keywords)
        if not hit:
            continue
        affordances = getattr(tuned, '_super_affordances', None) or ()
        ours = [a.__name__ for a in EXPECTED_FUNERAL_AFFORDANCES
                if a in affordances]
        rows.append((name, ours))
    total = len(getattr(manager, 'types', {}) or {})
    header = 'OBJECT manager: {} tuned types, {} match{}'.format(
        total, len(rows),
        'ing {!r}'.format(keyword) if keyword else 'ing funeral-ish names')
    lines = [header]
    if not rows:
        lines.append('  (no names matched — try `funeral.objects <word>`)')
        return lines
    for name, ours in sorted(rows)[:60]:
        marker = ' <- carries {}'.format(','.join(ours)) if ours else ''
        lines.append('  {}{}'.format(name, marker))
    if len(rows) > 60:
        lines.append('  ...and {} more'.format(len(rows) - 60))
    return lines


def attendee_lines(config=FuneralConfig):
    """Lines for `funeral.attendees` — dry-run of the invite picker."""
    sim_info = selected_sim_info()
    if sim_info is None:
        return ['no selected Sim (click a Sim first)']
    rows = gather_attendee_candidates(sim_info, config)
    lines = ['attendee candidates for {}: {} row(s)'.format(
        _full_name(sim_info), len(rows))]
    for (info, affordable) in rows:
        lines.append('  ' + format_funds_row(
            _full_name(info), getattr(info, 'sim_id', None),
            _money(info), affordable))
    if not rows:
        lines.append('  (nobody to invite — a private funeral would run)')
    return lines
