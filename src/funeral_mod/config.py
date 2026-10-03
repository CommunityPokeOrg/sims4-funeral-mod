# Copyright (c) CommunityPoke contributors.
"""Tweakable configuration for the Funeral Mod.

These are plain constants on purpose: The Sims 4 cannot ship custom tuning
XML without a .package file, so script-side constants are the simplest and
most reliable "configuration file" the mod can offer.  Advanced users can
edit this file inside the .ts4script archive (it is a normal zip) and the
game will pick the new values up on the next launch.
"""


class FuneralConfig:
    """Values that control the funeral economy and flow.

    All prices are in Simoleons (§).
    """

    # Simoleons charged to the hosting household when a funeral is planned.
    # Required feature value: 764
    HOST_FEE = 764

    # Simoleons charged per invited attendee when the funeral is confirmed.
    # Each attendee's own household is charged (the host household is charged
    # again for any invited household member, since they share funds).
    # Required feature value: 63
    ATTENDEE_FEE = 63

    # Hard cap on how many Sims may be invited to one funeral.
    MAX_ATTENDEES = 12

    # If True, attendees whose household cannot afford ``ATTENDEE_FEE`` are
    # shown in the picker but disabled, matching the game's own behaviour for
    # unaffordable purchases.  If False, unaffordable Sims are hidden entirely.
    SHOW_UNAFFORDABLE_ATTENDEES = True

    # If True, attending Sims physically travel/spawn onto the lot where the
    # funeral is held (uses the same SimSpawner path as the game's own
    # "summon" cheat).  If False, the funeral only applies to Sims already on
    # the lot plus the standard moodlet/notification flow.
    SUMMON_ATTENDEES = True

    # Substrings matched (case-insensitively) against tuned object names to
    # find urns, urnstones, gravestones and tombstones to put the "Plan
    # Funeral" pie menu entry on.  'urnstone' is the game's internal term for
    # both urns and gravestones.
    FUNERAL_OBJECT_NAME_KEYWORDS = (
        'urnstone',
        'urn',
        'gravestone',
        'tombstone',
        'headstone',
        'grave',
    )

    # The tuned name of the Sim object.  The "Plan Funeral" interaction is
    # also added here so it is reachable by clicking a Sim.
    SIM_OBJECT_NAME = 'sim'

    # Substrings matched (case-insensitively) against tuned buff names to
    # find the mourning/sad moodlet applied to attendees.  The first buff
    # that matches any keyword wins.
    MOURNING_BUFF_KEYWORDS = (
        'mourn',
        'sad',
    )

    # Substrings matched (case-insensitively) against tuned interaction names
    # when looking for an existing "mourn" style affordance to push on
    # attendees.  The first match wins; if none is found the mod quietly
    # skips that flavour step.
    MOURN_INTERACTION_KEYWORDS = (
        'mourn',
        'grieve',
    )

    # --- Debugging -----------------------------------------------------
    # Write funeral_mod_debug.log next to the .ts4script in the Mods folder
    # (cwd/temp fallback).  Toggle at runtime with `funeral.debug on|off`.
    DEBUG_LOGGING = True

    # Also write debug-chatter lines (menu visibility tests, picker rows,
    # summon attempts).  Toggle with `funeral.debug verbose` / `... info`.
    DEBUG_VERBOSE = True

    # Name of the debug log file created beside the mod / in cwd.
    DEBUG_LOG_FILENAME = 'funeral_mod_debug.log'
