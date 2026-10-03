# Copyright (c) CommunityPoke contributors.
"""Wire the funeral interactions into the game.

Runs once the OBJECT instance manager has loaded tuning: finds every tuned
object whose name looks like an urn/gravestone and the Sim object, and
appends the funeral super-affordances onto their ``_super_affordances`` so
they appear in the pie menu — no .package/tuning XML required.
"""

from sims4.resources import Types

import sims4.log

from funeral_mod import event as funeral_event
from funeral_mod.config import FuneralConfig
from funeral_mod.injection import add_affordances, on_load_complete
from funeral_mod.interactions import (
    ConcludeFuneralInteraction,
    GiveEulogyInteraction,
    PlanFuneralInteraction,
)

logger = sims4.log.Logger('funeral_mod.startup')

URNSTONE_AFFORDANCES = (
    PlanFuneralInteraction,
    GiveEulogyInteraction,
    ConcludeFuneralInteraction,
)
SIM_AFFORDANCES = (
    PlanFuneralInteraction,
    ConcludeFuneralInteraction,
)


def _is_funeral_object(tuned_object, config=FuneralConfig):
    name = getattr(tuned_object, '__name__', '') or ''
    lowered = name.lower()
    return any(keyword in lowered for keyword in config.FUNERAL_OBJECT_NAME_KEYWORDS)


@on_load_complete(Types.OBJECT)
def _inject_funeral_affordances(object_manager, config=FuneralConfig):
    if funeral_event.INJECTION_DONE:
        return
    funeral_event.INJECTION_DONE = True

    matched_objects = []
    sim_injected = False
    for tuned_object in getattr(object_manager, 'types', {}).values():
        name = getattr(tuned_object, '__name__', '') or ''
        try:
            if name.lower() == config.SIM_OBJECT_NAME:
                add_affordances(tuned_object, SIM_AFFORDANCES)
                sim_injected = True
            elif _is_funeral_object(tuned_object, config):
                add_affordances(tuned_object, URNSTONE_AFFORDANCES)
                matched_objects.append(name)
        except Exception:
            logger.exception('failed injecting funeral affordances into %s', name)

    if not sim_injected:
        logger.warn('could not find the Sim object tuning to inject into')
    if not matched_objects:
        logger.warn('no urnstone/gravestone tunings matched the configured keywords')
    else:
        logger.info('injected funeral interactions into: %s', matched_objects)
