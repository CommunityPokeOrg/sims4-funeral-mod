# Funeral Mod for The Sims 4

When a Sim dies, another Sim — in the same household **or any other
household** — can plan and host a funeral for them at their urn or
gravestone.

* **Hosting a funeral costs §764**, charged to the host Sim's household.
* **Each attendee pays §63 to attend**, charged to *their own* household
  (so guests from other households pay for themselves).
* Attendees outside the host household are summoned to the lot, given a
  mourning buff, and anyone (host or guest) can **Give Eulogy**; the host
  **Concludes the Funeral** when it's over.

Requested by **Sam Crafts (@samblal)** in the community Discord.

---

## Installation

1. Build or download `CommunityPoke_FuneralMod.ts4script` (see
   [Building](#building) — CI also produces it as a workflow artifact on
   every push).
2. Drop the `.ts4script` file into your `Documents\Electronic Arts\The
   Sims 4\Mods` folder (or `~/Documents/...` on macOS). **Keep it as a zip —
   do not extract it.**
3. In game options → Game Options → Other, enable **Script Mods Allowed**
   (and Mods Allowed). Restart the game.
4. No `.package` file is needed or provided — everything is injected by
   script. The XML in `tuning/` is reference documentation only and is not
   loaded by the game.

### Requirements

* The Sims 4 (any patch that runs script mods; developed against the
  current game API surface as of October 2026).
* Script mods enabled in game options.
* No other mod dependencies (does **not** require XML Injector, MCCC,
  S4CL, etc.).

## How it works

The mod is a pure Python script mod (`.ts4script` = a zip of `.pyc`
bytecode compiled for the game's embedded Python 3.7). All English text is
generated at runtime via `LocalizationHelperTuning.get_raw_text`, so no
string-table (STBL) package is needed.

### The flow

1. **Plan Funeral…** — click any **urn or gravestone** (the game's
   internal name is *urnstone*; the mod also accepts keywords
   `gravestone`, `tombstone`, `headstone`) while the deceased Sim's
   remains are on the lot. Can also be reached by clicking a living Sim if
   an urnstone exists on the zone (the interaction is injected on both).
   * Available only if the host's household can afford **§764** and no
     funeral is already running on that lot.
2. **Invite Mourners** — a sim-picker dialog lists the deceased's
   household members and relationship contacts that are alive. Each row
   shows whether that Sim's household can afford the **§63** attendance
   fee; Sims who can't afford it are shown but can't be selected
   (configurable). Picking nobody is allowed — a private funeral still
   happens.
3. **Charges** — on confirmation the host household is charged §764 and
   each selected attendee's own household is charged §63. If any charge
   fails the mod skips that attendee rather than blocking the funeral.
4. **During the funeral** — attendees from other lots are summoned via
   `SimSpawner.load_sim`, mourners receive a sadness/mourning buff if one
   is found in tuning, and **Give Eulogy** (on the urnstone) becomes
   available to the host and attendees.
5. **Conclude Funeral** — the host ends the event from the urnstone or
   their own Sim menu; a summary notification reports how many mourners
   attended and how many eulogies were given.

### Cheat / debug commands

With TestingCheats enabled:

* `funeral.prices` — print the configured fees.
* `funeral.status` — print whether a funeral is active on this lot and
  who the host/deceased are.
* `funeral.end` — force-end the active funeral on this lot (if any).

## Configuration options

All settings live in `src/funeral_mod/config.py` as class attributes on
`FuneralConfig`. To change them, edit the file and rebuild the
`.ts4script` (there is no in-game settings UI).

| Option | Default | Meaning |
|---|---|---|
| `HOST_FEE` | `764` | § charged to the host's household |
| `ATTENDEE_FEE` | `63` | § charged to each attendee's own household |
| `MAX_ATTENDEES` | `12` | Cap on invited guests |
| `SHOW_UNAFFORDABLE_ATTENDEES` | `True` | Show broke guests in the picker (greyed out); `False` hides them |
| `SUMMON_ATTENDEES` | `True` | Teleport off-lot guests onto the lot |
| `FUNERAL_OBJECT_NAME_KEYWORDS` | urn/gravestone keywords | Tuned-object class names that get the interactions |
| `MOURNING_BUFF_KEYWORDS` | `('mourn', 'sad')` | Buff names searched for the mourning mood |
| `MOURN_INTERACTION_KEYWORDS` | `('mourn', 'grieve')` | Reserved for future use |

## Building

```bash
# With Python 3.7 (recommended — produces game-matching .pyc):
docker run --rm -v "$PWD":/work -w /work python:3.7-slim \
    python tools/build_ts4script.py

# Or with any Python 3 (falls back to .py sources inside the zip,
# which the game compiles on import):
python3 tools/build_ts4script.py
```

Output: `build/CommunityPoke_FuneralMod.ts4script`

## Tests

```bash
python3 -m unittest discover -s tests -v
```

15 unit tests cover the pure-Python economy logic (the §764/§63 rules,
affordability, charge planning, attendee dedup/capping) — everything that
can be tested without the game. `tests/test_logic.py` doubles as a spec
for the required pricing. `python -m compileall -q src` gates the source
to Python 3.7-compatible syntax in CI.

## What could NOT be tested without the game

This mod was built and verified against the **decompiled Sims 4 Python
API** (funds, `UiSimPicker`, `ImmediateSuperInteraction`, `Ghost`
urnstones, `SimSpawner`, tuned-object injection) plus established
community patterns (TURBODRIVER/Lot51 injection). **No in-game testing was
performed** — there is no Sims 4 install available in the build
environment. Concretely unverified:

* Whether the interaction actually appears on urns/gravestones/Sims in
  the pie menu (the keyword matching on tuned object names may need
  tweaking for specific packs/CC urnstones).
* Whether `UiSimPicker` renders exactly as tuned and returns the expected
  result tags.
* Real money debit for **other** households relies on
  `FamilyFunds.try_remove(..., sim=None)` debiting that household — the
  decompiled code says it does, but it's untested live.
* Summoning, mourning buffs, and notification timing during an actual
  play session.
* Behavior when the host travels/moves during a funeral (zone reloads
  are guarded by `sims4.reload.protected`, but not exercised).

If you test in-game, please report findings as a GitHub issue — good or
bad.

## Repository layout

```
src/funeral_mod/     mod source (Python 3.7-compatible)
tests/               unittest suite for pure logic
tools/build_ts4script.py   packaging script
tuning/              reference XML (documentation only, not loaded by game)
.github/workflows/   CI: syntax gate, tests, package, artifact
build/               built .ts4script (git-ignored)
```

## License / attribution

Built by the community for Sam Crafts. Free to use, modify, and share.
