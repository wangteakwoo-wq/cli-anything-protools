"""Pro Tools I/O routing control."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class IORoutingController:
    """Controls Pro Tools I/O routing via HUI assign buttons and AppleScript."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def open_io_setup(self) -> dict:
        """Open the I/O Setup dialog. Setup > I/O..."""
        if self._as:
            self._as.menu_click(["Setup", "I/O..."])
        return {"status": "ok", "action": "open_io_setup"}

    def assign_output(self, channel: int | None = None) -> dict:
        """Switch V-Pot assignment to Output routing view.
        
        In this mode, turning V-Pots cycles through output assignments.
        """
        if self._hui:
            self._hui.assign_output()
        return {"status": "ok", "action": "assign_output"}

    def assign_input(self, channel: int | None = None) -> dict:
        """Switch V-Pot assignment to Input routing view."""
        if self._hui:
            self._hui.assign_input()
        return {"status": "ok", "action": "assign_input"}

    def assign_send(self, letter: str = "A") -> dict:
        """Switch V-Pot assignment to Send routing view.
        
        Args:
            letter: Send slot A through E.
        """
        if self._hui:
            self._hui.assign_send(letter.upper())
        return {"status": "ok", "action": "assign_send", "send": letter.upper()}

    def import_io_settings(self) -> dict:
        """Import I/O settings from a .pio file. Setup > I/O... then Import."""
        if self._as:
            self._as.menu_click(["Setup", "I/O..."])
            time.sleep(1.0)
            self._as.click_button("Import Settings")
        return {"status": "ok", "action": "import_io_settings"}
