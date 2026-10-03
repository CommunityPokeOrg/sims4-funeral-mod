# Reference tuning (not required for install)

The funeral mod is a **pure script mod**: every interaction, dialog, and
price is injected into the game at tuning-load time by
`src/funeral_mod/startup.py`, so **no `.package` file and no tuning XML is
required to install or run it.**

This directory documents what the equivalent tuning XML would look like if
the mod were built the traditional (tuning + script) way. It is provided
for reviewers and future maintainers only — the game never reads these
files, and they are intentionally **not** included in the shipped
`.ts4script`.

* `plan_funeral_interaction.xml` — the ImmediateSuperInteraction tuning an
  XML-based version would use for "Plan Funeral…".
* `sim_picker_dialog.xml` — a sketch of the `UiSimPicker` dialog tuning.
  The script builds the same dialog programmatically via
  `create_factory_wrapper(UiSimPicker, ...)`.
