# Copyright (c) CommunityPoke contributors.
"""Small injection helpers, modelled on the pattern every major script mod
uses (TURBODRIVER's injector / Lot51's core library).

* ``inject_to`` wraps an existing function so our code runs around it.
* ``add_affordances`` appends super-affordances to a tuned object's
  ``_super_affordances`` set so they show up in the pie menu.
* ``on_load_complete`` registers a callback fired once an instance manager
  finishes loading tuning.
"""

import functools
import inspect

from services import get_instance_manager

import sims4.log

logger = sims4.log.Logger('funeral_mod.injection')

DEFAULT_SA_KEY = '_super_affordances'


def _merge_list(original_list, new_items, list_type=None):
    if list_type is None:
        list_type = type(original_list) if original_list is not None else type(new_items)
    build_list = list(original_list) if original_list is not None else []
    for item in new_items:
        if item not in build_list:
            build_list.append(item)
    return list_type(build_list)


def add_affordances(tuned_object, interactions, key=DEFAULT_SA_KEY):
    """Append affordances onto a tuned object class or component.

    ``tuned_object`` is usually a tuned object *class* (the thing the OBJECT
    instance manager holds in ``.types``); the game iterates its
    ``_super_affordances`` when building pie menus, so mutating the class
    list adds our interaction to every object of that type.
    """
    original = getattr(tuned_object, key, None)
    merged = _merge_list(original, tuple(interactions))
    setattr(tuned_object, key, merged)


def is_flexmethod(target_function):
    """Detect EA's ``@flexmethod`` wrapper (a functools.partial with cls/inst)."""
    if type(target_function) is functools.partial:
        spec = inspect.getfullargspec(target_function.func)
        return len(spec.args) >= 2 and spec.args[0] == 'cls' and spec.args[1] == 'inst'
    return False


def inject_to(target_object, target_function_name):
    """Decorator: replace ``target_function_name`` on ``target_object``.

    The decorated function receives the original callable as its first
    argument, then all original args.  Handles plain functions, classmethods,
    staticmethods, properties and flexmethods.
    """

    def _wrap_target(target_function, new_function):

        @functools.wraps(target_function)
        def _wrapped_func(*args, **kwargs):
            if is_flexmethod(target_function):
                def new_flex_function(original, *nargs, **nkwargs):
                    cls = original.args[0]
                    inst = next((narg for narg in nargs if type(narg) is cls), None)
                    if inst is not None:
                        nargs = list(nargs)
                        nargs.remove(inst)
                    return new_function(original.func, cls, inst, *nargs, **nkwargs)
                return new_flex_function(target_function, *args, **kwargs)
            return new_function(target_function, *args, **kwargs)

        if type(target_function) is staticmethod:
            return staticmethod(_wrapped_func)
        if inspect.ismethod(target_function):
            return classmethod(_wrapped_func)
        if type(target_function) is property:
            return property(_wrapped_func)
        return _wrapped_func

    def _inject(new_function):
        target_function = getattr(target_object, target_function_name)
        setattr(target_object, target_function_name, _wrap_target(target_function, new_function))
        return new_function

    return _inject


def on_load_complete(manager_type):
    """Run ``function(manager)`` once the instance manager finishes loading.

    Same pattern as Frank's ``on_load_complete`` used by Lot51 — this is the
    safe point to mutate tuned instances (e.g. append super affordances).

    If the manager already finished loading before this callback was
    registered (script mods can init late in the load sequence), the
    callback is run immediately instead of never firing — a missed
    registration otherwise disables every injected interaction silently.
    """

    def wrapper(function):

        def safe_function(manager, *_, **__):
            try:
                function(manager)
            except Exception:
                logger.exception('on_load_complete callback failed for manager %s', manager_type)

        try:
            manager = get_instance_manager(manager_type)
        except Exception:
            logger.exception('instance manager %s unavailable at registration', manager_type)
            return
        manager.add_on_load_complete(safe_function)
        if getattr(manager, 'types', None):
            # Tuning already loaded — the callback list will not fire again
            # for this pass, so run it now.
            logger.info('manager %s already loaded; running injection immediately', manager_type)
            safe_function(manager)

    return wrapper
