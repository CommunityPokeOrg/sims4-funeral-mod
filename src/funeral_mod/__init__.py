# Copyright (c) CommunityPoke contributors.
"""Funeral Mod — plan and host funerals for deceased Sims.

Top-level package for the script mod.  The game's script loader imports
modules eagerly from the .ts4script archive; importing this package runs
:mod:`funeral_mod.startup` which hooks tuning-load and registers the cheat
commands, wiring everything up without any .package file.
"""

from funeral_mod.mod_info import MOD_NAME, MOD_VERSION

# Import side effects: registering the tuning-load callback and cheat
# commands.  Kept defensive so a failure in one module never stops the game
# from booting the rest of the mod — and so the package remains importable
# in a plain-Python test environment with no ``sims4`` module present.
def _report_import_failure(what, exc):
    try:
        import sims4.log
        sims4.log.Logger('funeral_mod').exception('%s failed', what)
    except Exception:
        # Outside the game (unit tests) there is no sims4.log.
        import traceback
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    try:
        # The file log imports nothing from the game, so it is the most
        # reliable place to surface an init failure.
        from funeral_mod import debug_log
        debug_log.exception('import failure: %s', what)
    except Exception:
        pass


try:
    import funeral_mod.startup  # noqa: F401
except Exception as _exc:
    _report_import_failure('startup hook registration', _exc)

try:
    import funeral_mod.commands  # noqa: F401
except Exception as _exc:
    _report_import_failure('command registration', _exc)

try:
    from funeral_mod import debug_log as _debug_log
    _debug_log.info('%s v%s package initialized', MOD_NAME, MOD_VERSION)
except Exception:
    pass

__all__ = ('MOD_NAME', 'MOD_VERSION')
