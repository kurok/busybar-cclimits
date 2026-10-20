# Changelog

## [Unreleased]

- CI runs the app against the BUSY Bar emulator too (`tests/emulator`): every
  sample drawing, the runner's clear-on-new-ids, giving way to a higher
  priority and taking the screen back, the service, `test` and `app.py`.

- Up to three rows, the third set in the 4-pixel tiny font, and per-model
  windows (`seven_day_fable`, `seven_day_opus`, `seven_day_sonnet`, any
  `seven_day_<model>`), labelled FB, OP, SN.

- `snapshot` draws sample states on the bar and saves what it shows.
- A refused draw says what holds the bar instead of the bar's error text.
- Previews in the README and `preview.gif`, from `scripts/render_previews.py`.

## [0.1.0] - 2026-10-20

First release.

- The 5-hour and weekly windows as bars, green, yellow from 75% and red from
  90%, with a live countdown to the 5-hour reset and the weekly percentage.
- The limits come from Claude Code's own status line input: `statusline`
  stores them and runs your status line command after; `hook install` and
  `hook uninstall` put it in Claude Code's settings and take it out again.
- `[display]` settings: one or two rows of `five_hour`, `seven_day` or
  `spend_limit`, the text beside each bar, `show = "with_claude"`,
  thresholds and colours.
- Priority 50, re-sent every minute, with `display_until` on every element.
- `init`, `status`, `test`, `demo`, `run`, `install` (launchd / systemd,
  `--auto-update`), `restart`, `uninstall`; `app.py` for the gallery.
