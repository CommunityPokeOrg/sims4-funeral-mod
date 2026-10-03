# Copyright (c) CommunityPoke contributors.
"""Build ``TunableFactoryWrapper``s by hand.

Normally the tuning system produces factory wrappers from XML.  Script-only
mods need the same wrappers to spawn dialogs/pickers, so this reproduces the
``create_factory_wrapper`` helper from Lot51's core library.
"""

from sims4.tuning.tunable import TunableFactory


def create_factory_wrapper(cls, locked_args=None, **tuned_values):
    """Create a callable factory wrapper for ``cls``.

    ``cls`` may be a ``HasTunableFactory`` subclass (e.g.
    ``UiDialogNotification`` / ``UiSimPicker``) or a ``TunableFactory``
    subclass.  Any FACTORY_TUNABLES not given in ``tuned_values`` fall back
    to the tunable's default.  Calling the returned wrapper builds the real
    object, e.g. ``factory(owner, resolver)``.
    """
    locked_args = locked_args or {}
    if isinstance(cls, type) and issubclass(cls, TunableFactory):
        factory = cls(locked_args=locked_args)
    elif hasattr(cls, 'TunableFactory'):
        factory = cls.TunableFactory(locked_args=locked_args)
    else:
        raise ValueError('Unable to detect TunableFactory on cls: {}'.format(cls))

    leftovers = set(factory.tunable_items.keys()) - tuned_values.keys()
    for name in leftovers:
        template = factory.tunable_items[name]
        tuned_values[name] = template.default
    return factory._create_dict(tuned_values, factory.locked_args)
