# Changelog

## [Unreleased]

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
