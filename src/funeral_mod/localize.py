# Copyright (c) CommunityPoke contributors.
"""Localization helpers.

The mod ships no STBL (string table) resource, so every string is produced
with ``LocalizationHelperTuning.get_raw_text`` — the same trick used by
other script-only mods for plain English text.
"""

from sims4.localization import LocalizationHelperTuning


def localized(text):
    """Return a LocalizedString containing raw English ``text``."""
    return LocalizationHelperTuning.get_raw_text(text)


def localized_factory(text):
    """Return a zero-arg factory producing the localized ``text``.

    Dialog/interaction tunables expect factories they call with tokens, not
    pre-baked strings, so this wraps ``localized`` in a callable that ignores
    whatever tokens get passed in.
    """
    return lambda *_, **__: localized(text)
