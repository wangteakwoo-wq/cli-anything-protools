"""Pro Tools automation control — read, write, touch, latch modes."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class AutomationController:
    """Controls Pro Tools automation modes via HUI."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def set_mode(self, mode: str) -> dict:
        """Set automation mode for selected track(s).
        
        Args:
            mode: "off", "read", "touch", "latch", "write", "trim"
        """
        mode = mode.lower()
        valid = ("off", "read", "touch", "latch", "write", "trim")
        if mode not in valid:
            raise ValueError(f"Invalid automation mode '{mode}'. Valid: {valid}")
        
        if self._hui:
            self._hui.auto_mode(mode)
        elif self._as:
            self._as.keystroke("w", modifiers=["command", "option", "control"])
        return {"status": "ok", "action": "set_automation_mode", "mode": mode}

    def write_to_all(self) -> dict:
        """Write automation to all enabled parameters."""
        if self._as:
            self._as.keystroke("w", modifiers=["command", "option", "control"])
        return {"status": "ok", "action": "write_automation_all"}

    def suspend_all(self) -> dict:
        """Suspend all automation."""
        if self._hui:
            self._hui._send_switch(0x11, 0x04)  # Suspend
        elif self._as:
            self._as.menu_click(["Options", "Suspend All Automation"])
        return {"status": "ok", "action": "suspend_automation"}
