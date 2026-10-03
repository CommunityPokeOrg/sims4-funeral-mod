# Copyright (c) CommunityPoke contributors.
"""Append-only file logger for in-game debugging.

Writes ``funeral_mod_debug.log`` next to the ``.ts4script`` inside the Mods
folder (falling back to the game working directory, then the temp dir), so
testers can attach a concrete file to a bug report instead of describing
what they saw.  All IO is wrapped — a read-only install can never crash the
mod, it just disables the file log.

Controlled at runtime by the ``funeral.debug`` cheat:

    funeral.debug on|verbose   – enable file logging incl. debug chatter
    funeral.debug info         – file logging, lifecycle events only
    funeral.debug off          – disable file logging
    funeral.debug              – print current status
"""

import os
import time
import traceback

from funeral_mod.config import FuneralConfig
from funeral_mod.mod_info import MOD_NAME, MOD_VERSION

_state = {
    'enabled': FuneralConfig.DEBUG_LOGGING,
    'verbose': FuneralConfig.DEBUG_VERBOSE,
    'path': None,
    'banner_written': False,
    'error': None,
}


def _candidate_dirs():
    # Inside the game, __file__ for a module in a .ts4script looks like
    #   .../Mods/CommunityPoke_FuneralMod.ts4script/funeral_mod/debug_log.py
    # so three dirnames up lands in the Mods folder.
    try:
        yield os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        pass
    try:
        yield os.getcwd()
    except Exception:
        pass
    try:
        import tempfile
        yield tempfile.gettempdir()
    except Exception:
        pass


def _resolve_path():
    """Pick the first writable directory for the log file (cached)."""
    if _state['path'] is not None:
        return _state['path']
    filename = FuneralConfig.DEBUG_LOG_FILENAME
    for directory in _candidate_dirs():
        candidate = os.path.join(directory, filename)
        try:
            with open(candidate, 'a'):
                pass
        except Exception:
            continue
        _state['path'] = candidate
        return candidate
    _state['error'] = 'no writable location for {}'.format(filename)
    return None


def _stamp():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def _write(level, msg):
    if not _state['enabled']:
        return
    path = _resolve_path()
    if path is None:
        return
    try:
        with open(path, 'a') as fh:
            if not _state['banner_written']:
                fh.write('==== {} v{} debug log ====\n'.format(MOD_NAME, MOD_VERSION))
                _state['banner_written'] = True
            fh.write('{} [{}] {}\n'.format(_stamp(), level, msg))
    except Exception as exc:
        # Stop retrying every call; funeral.debug reports the error.
        _state['error'] = repr(exc)
        _state['enabled'] = False


def info(msg, *args):
    """Always-on lifecycle logging (charges, injection, funeral start/end)."""
    if args:
        msg = msg % args
    _write('INFO', msg)


def debug(msg, *args):
    """Verbose logging (menu tests, picker rows, summon attempts)."""
    if not _state['verbose']:
        return
    if args:
        msg = msg % args
    _write('DEBUG', msg)


def exception(msg, *args):
    if args:
        msg = msg % args
    _write('ERROR', '{}\n{}'.format(msg, traceback.format_exc()))


def set_mode(mode):
    """'on'/'verbose' -> enabled+verbose, 'info' -> enabled, 'off' -> disabled."""
    mode = (mode or '').strip().lower()
    if mode in ('on', 'verbose', 'debug'):
        _state['enabled'] = True
        _state['verbose'] = True
    elif mode == 'info':
        _state['enabled'] = True
        _state['verbose'] = False
    elif mode in ('off', 'none', 'disable'):
        _state['enabled'] = False
    return status()


def status():
    """Snapshot for `funeral.debug` output (pure-ish; resolves path lazily)."""
    path = _state['path']
    if path is None and _state['enabled']:
        path = _resolve_path()
    return {
        'enabled': _state['enabled'],
        'verbose': _state['verbose'],
        'path': path or '<unwritable: {}>'.format(_state.get('error')),
        'error': _state.get('error'),
    }


def tail(max_lines=40, path=None):
    """Last ``max_lines`` lines of the log file ([] if it does not exist)."""
    path = path or _state['path'] or _resolve_path()
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, 'rb') as fh:
            text = fh.read().decode('utf-8', 'replace')
    except Exception:
        return []
    return text.splitlines()[-max_lines:]
