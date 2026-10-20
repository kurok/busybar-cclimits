"""
The drawing: one or two rows on the 72x16 front panel, each a label, a bar
of how much of a limit is used, and beside it the time to its reset or the
percentage.

    5H ████████░░░░░░░░ 1:42:10      the 5-hour window and a live countdown
    WK ███░░░░░░░░░░░░░     38%      the weekly window and how much is used

Once a reset is under 10 hours away the time is the bar's own countdown
element, which ticks on the device; further out it is text (21h, 3d4h)
redrawn when it changes. A window whose reset time has passed is drawn
empty, with `--` for the time, until Claude Code reports a new one.

Element ids stay the same from one drawing to the next so that a redraw
updates in place; the bar keeps every element an application drew until it
is cleared, so the service clears first whenever the set of ids changes.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Protocol

from busylib import types
from busylib.exceptions import BusyBarAPIError
from pydantic import BaseModel, Field

from .config import Colors, DisplayConfig, Row
from .limits import Feed, Window, duration

WIDTH = 72
BAR_HEIGHT = 5
# Where the bar starts when there are labels: two small-font glyphs (W is 5
# pixels wide) and a gap.
BAR_X = 12
GAP = 1
# Room on the right for the longest thing each text mode draws: the
# countdown's "9:59:59" in its superscript font, or "100%" / "6d23h" in small.
RIGHT_WIDTH = {"time": 28, "percent": 17, "none": 0}
COUNTDOWN_UNDER = 10 * 3600
# The rows' glyph tops. Small text anchored top_left at y lands on rows
# y+2..y+6, and the countdown anchored at the bottom on y-9..y-5 (both
# measured on firmware 1.2.4), so a row is 5 pixels from its top.
ROW_TOPS = {1: (6,), 2: (2, 10)}
SMALL_OFFSET = 2
COUNTDOWN_OFFSET = 9
DRAW_PATH = "/api/display/draw"

Element = Annotated[
    types.TextElement | types.CountdownElement | types.RectangleElement,
    Field(discriminator="type"),
]


class Drawing(BaseModel):
    """The body of POST /api/display/draw."""

    application_name: str = Field(min_length=1, max_length=32)
    priority: int = Field(ge=1, le=100)
    elements: list[Element] = Field(min_length=1)

    def payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class Bar(Protocol):
    async def api_request(self, method: str, path: str, **kwargs: Any) -> Any: ...

    async def display_clear(self, **kwargs: Any) -> Any: ...


async def send(bar: Bar, drawing: Drawing) -> None:
    await bar.api_request("POST", DRAW_PATH, json_payload=drawing.payload())


async def clear(bar: Bar, application_name: str) -> None:
    """Remove this app's drawing, and only this app's."""
    try:
        await bar.display_clear(application_name=application_name)
    except BusyBarAPIError as error:
        # 400: this app has nothing on the screen - another app owns it.
        if error.status_code != 400:
            raise


def bar_color(used: float, display: DisplayConfig) -> str:
    colors = display.colors
    if used >= display.critical_at:
        return colors.critical
    if used >= display.warn_at:
        return colors.warn
    return colors.ok


def fill_width(used: float, width: int) -> int:
    """Pixels lit for `used` percent: none only at 0, all only at 100."""
    if used <= 0:
        return 0
    if used >= 100:
        return width
    return min(width - 1, max(1, round(used / 100 * width)))


def _small(element_id: str, text: str, x: int, top: int, align: str, color: str) -> Any:
    return types.TextElement(
        id=element_id, text=text, font="small", x=x, y=top - SMALL_OFFSET, align=align, color=color
    )


def _rect(element_id: str, x: int, top: int, width: int, color: str) -> Any:
    return types.RectangleElement(
        id=element_id,
        x=x,
        y=top,
        width=width,
        height=BAR_HEIGHT,
        fill="solid",
        fill_colors=[color],
        border_width=0,
        align="top_left",
    )


def _beside(
    n: int, row: Row, window: Window | None, now: float, top: int, colors: Colors
) -> Any | None:
    if row.text == "none":
        return None
    if window is None or (row.text == "time" and not window.running):
        return _small(f"cc{n}_text", "--", WIDTH, top, "top_right", colors.idle)
    if row.text == "percent":
        return _small(f"cc{n}_text", f"{window.used:.0f}%", WIDTH, top, "top_right", colors.text)
    left = window.left(now) or 0.0
    if left > COUNTDOWN_UNDER:
        return _small(f"cc{n}_text", duration(left), WIDTH, top, "top_right", colors.text)
    return types.CountdownElement(
        id=f"cc{n}_clock",
        timestamp=str(window.resets_at),
        direction="time_left",
        show_hours="when_non_zero",
        color=colors.text,
        x=WIDTH,
        y=top + COUNTDOWN_OFFSET,
        align="bottom_right",
    )


def elements(feed: Feed, now: float, display: DisplayConfig) -> list[Any]:
    windows = feed.at(now)
    rows = display.rows
    colors = display.colors
    labelled = any(row.shown_label for row in rows)
    x = BAR_X if labelled else 0
    right = max(RIGHT_WIDTH[row.text] for row in rows)
    width = WIDTH - x - right - (GAP if right else 0)
    drawn: list[Any] = []
    for n, (row, top) in enumerate(zip(rows, ROW_TOPS[len(rows)], strict=True)):
        window = windows.get(row.window)
        used = window.used if window is not None else 0.0
        if row.shown_label:
            drawn.append(_small(f"cc{n}_label", row.shown_label, 0, top, "top_left", colors.label))
        drawn.append(_rect(f"cc{n}_track", x, top, width, colors.track))
        lit = fill_width(used, width)
        # Always there, so the ids do not change at 0%: an unlit fill is one track pixel.
        drawn.append(
            _rect(
                f"cc{n}_fill",
                x,
                top,
                max(lit, 1),
                bar_color(used, display) if lit else colors.track,
            )
        )
        if (beside := _beside(n, row, window, now, top, colors)) is not None:
            drawn.append(beside)
    return drawn


def visible(feed: Feed | None, now: float, display: DisplayConfig) -> bool:
    """Whether the limits belong on the bar now; see `[display] show`."""
    if feed is None or not any(row.window in feed.windows for row in display.rows):
        return False
    if display.show == "always":
        return True
    if feed.seen_at is not None and now - feed.seen_at <= display.idle_minutes * 60:
        return True
    windows = feed.at(now)
    return any(
        (w := windows.get(row.window)) is not None and w.running and w.used >= display.keep_above
        for row in display.rows
    )


def drawing(elements: list[Any], until: float, application_name: str, priority: int) -> Drawing:
    """The request for `elements`, each taken down by the bar itself at `until`."""
    stamp = str(int(until))
    return Drawing(
        application_name=application_name,
        priority=priority,
        elements=[element.model_copy(update={"display_until": stamp}) for element in elements],
    )


def key(elements: list[Any]) -> str:
    """What a drawing shows, to tell whether it changed."""
    return json.dumps(
        [element.model_dump(mode="json", exclude_none=True) for element in elements],
        sort_keys=True,
    )
