"""Pro Tools navigation — zoom, window management, cursor movement."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class NavigateController:
    """Controls Pro Tools navigation, zoom, and window management."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def zoom_in(self) -> dict:
        """Zoom in horizontally. Cmd+Option+T (or Cmd+])"""
        if self._as:
            self._as.keystroke("]", modifiers=["command"])
        return {"status": "ok", "action": "zoom_in"}

    def zoom_out(self) -> dict:
        """Zoom out horizontally. Cmd+["""
        if self._as:
            self._as.keystroke("[", modifiers=["command"])
        return {"status": "ok", "action": "zoom_out"}

    def zoom_to_selection(self) -> dict:
        """Zoom to fit current selection. Option+E"""
        if self._as:
            self._as.keystroke("e", modifiers=["option"])
        return {"status": "ok", "action": "zoom_to_selection"}

    def zoom_to_fill(self) -> dict:
        """Zoom to fill entire session. Cmd+Option+E"""
        if self._as:
            self._as.keystroke("e", modifiers=["command", "option"])
        return {"status": "ok", "action": "zoom_to_fill"}

    def toggle_mix_window(self) -> dict:
        """Toggle Mix window. Cmd+="""
        if self._hui:
            self._hui.mix_window()
        elif self._as:
            self._as.keystroke("=", modifiers=["command"])
        return {"status": "ok", "action": "toggle_mix_window"}

    def toggle_edit_window(self) -> dict:
        """Toggle Edit window. = key"""
        if self._hui:
            self._hui.edit_window()
        elif self._as:
            self._as.keystroke("=")
        return {"status": "ok", "action": "toggle_edit_window"}

    def cursor_up(self) -> dict:
        """Move cursor/selection up."""
        if self._hui:
            self._hui.cursor_up()
        return {"status": "ok", "action": "cursor_up"}

    def cursor_down(self) -> dict:
        """Move cursor/selection down."""
        if self._hui:
            self._hui.cursor_down()
        return {"status": "ok", "action": "cursor_down"}

    def cursor_left(self) -> dict:
        """Move cursor/selection left."""
        if self._hui:
            self._hui.cursor_left()
        return {"status": "ok", "action": "cursor_left"}

    def cursor_right(self) -> dict:
        """Move cursor/selection right."""
        if self._hui:
            self._hui.cursor_right()
        return {"status": "ok", "action": "cursor_right"}

    def scrub(self) -> dict:
        """Enter scrub mode."""
        if self._hui:
            self._hui.scrub()
        return {"status": "ok", "action": "scrub"}

    def shuttle(self) -> dict:
        """Enter shuttle mode."""
        if self._hui:
            self._hui.shuttle()
        return {"status": "ok", "action": "shuttle"}

    def zoom_toggle(self) -> dict:
        """Toggle zoom mode for navigation keys."""
        if self._hui:
            self._hui.zoom_toggle()
        return {"status": "ok", "action": "zoom_toggle"}
