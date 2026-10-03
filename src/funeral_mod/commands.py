# Copyright (c) CommunityPoke contributors.
"""Cheat-console commands, mostly for debugging and automated testing.

Open the cheat console (Ctrl+Shift+C) and type:

    funeral.status          – report whether a funeral is active and dump its data
    funeral.prices          – print the configured fees
    funeral.end             – conclude the active funeral in this zone
    funeral.verify          – self-check: menu registration, fees, buff, debits
    funeral.plan            – dump the active funeral incl. paid attendee ids
    funeral.money           – household funds of selected Sim + host/attendees
    funeral.attendees       – dry-run of the invite picker for the selected Sim
    funeral.objects [word]  – scan tuned object names; shows which carry Plan Funeral
    funeral.debug on|info|off – toggle the funeral_mod_debug.log file
    funeral.log             – print the tail of the debug log file
"""

from sims4.commands import Command, CommandType, Output

import services

from funeral_mod import debug_log
from funeral_mod import devtools
from funeral_mod import event as funeral_event
from funeral_mod.config import FuneralConfig
from funeral_mod.dbg import describe_event, format_debit_summary
from funeral_mod.mod_info import MOD_NAME, MOD_VERSION


def _zone_id():
    try:
        return services.current_zone_id()
    except Exception:
        return 0


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
    zone_id = _zone_id()
    ev = funeral_event.get_event(zone_id)
    if ev is None:
        output('funeral: none active in zone {}'.format(zone_id))
    else:
        for line in describe_event(ev):
            output(line)
    output(format_debit_summary(funeral_event.DEBIT_LOG))
    return True


@Command('funeral.end', command_type=CommandType.Live)
def _funeral_end(_connection=None):
    output = Output(_connection)
    zone_id = _zone_id()
    if funeral_event.end_event(zone_id) is None:
        output('funeral: none active to end')
        return False
    debug_log.info('funeral.end: forced end in zone %s', zone_id)
    output('funeral: ended')
    return True


@Command('funeral.verify', command_type=CommandType.Live)
def _funeral_verify(_connection=None):
    output = Output(_connection)
    try:
        for line in devtools.verify_report():
            output(line)
    except Exception as exc:
        output('funeral.verify failed: {!r}'.format(exc))
        return False
    return True


@Command('funeral.plan', command_type=CommandType.Live)
def _funeral_plan(_connection=None):
    output = Output(_connection)
    try:
        for line in devtools.plan_lines():
            output(line)
    except Exception as exc:
        output('funeral.plan failed: {!r}'.format(exc))
        return False
    return True


@Command('funeral.money', command_type=CommandType.Live)
def _funeral_money(_connection=None):
    output = Output(_connection)
    try:
        for line in devtools.money_lines():
            output(line)
    except Exception as exc:
        output('funeral.money failed: {!r}'.format(exc))
        return False
    return True


@Command('funeral.objects', command_type=CommandType.Live)
def _funeral_objects(keyword: str = '', _connection=None):
    output = Output(_connection)
    try:
        for line in devtools.objects_lines(keyword):
            output(line)
    except Exception as exc:
        output('funeral.objects failed: {!r}'.format(exc))
        return False
    return True


@Command('funeral.attendees', command_type=CommandType.Live)
def _funeral_attendees(_connection=None):
    output = Output(_connection)
    try:
        for line in devtools.attendee_lines():
            output(line)
    except Exception as exc:
        output('funeral.attendees failed: {!r}'.format(exc))
        return False
    return True


@Command('funeral.debug', command_type=CommandType.Live)
def _funeral_debug(mode: str = 'status', _connection=None):
    output = Output(_connection)
    mode = (mode or 'status').strip().lower()
    if mode in ('on', 'verbose', 'debug', 'info', 'off', 'none', 'disable'):
        debug_log.set_mode(mode)
    status = debug_log.status()
    output('debug log: {} (enabled={} verbose={})'.format(
        status['path'], status['enabled'], status['verbose']))
    if status.get('error'):
        output('log error: {}'.format(status['error']))
    if mode not in ('status', ''):
        output('mode set: {}'.format(mode))
    return True


@Command('funeral.log', command_type=CommandType.Live)
def _funeral_log(_connection=None):
    output = Output(_connection)
    status = debug_log.status()
    lines = debug_log.tail(30)
    if not lines:
        output('no log lines yet ({})'.format(status['path']))
        return True
    output('--- {} (last {}) ---'.format(status['path'], len(lines)))
    for line in lines:
        output(line)
    return True
