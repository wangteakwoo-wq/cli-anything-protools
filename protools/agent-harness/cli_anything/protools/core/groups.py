"""Pro Tools group management — create, modify, enable, disable groups."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class GroupController:
    """Manages Pro Tools edit/mix groups."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def create(self, name: str | None = None, group_type: str = "edit_mix") -> dict:
        """Create a new group from selected tracks.
        
        Args:
            name: Group name. If None, uses Pro Tools default.
            group_type: "edit", "mix", or "edit_mix".
        """
        if self._hui:
            self._hui.group_create()
        elif self._as:
            self._as.keystroke("g", modifiers=["command"])
        
        time.sleep(0.5)
        if name and self._as:
            self._as.keystroke("a", modifiers=["command"])
            time.sleep(0.1)
            self._as.keystroke(name)
        
        if self._as:
            time.sleep(0.1)
            self._as.keystroke("\r")
        
        return {"status": "ok", "action": "create_group", "name": name, "type": group_type}

    def modify(self) -> dict:
        """Open the Modify Group dialog for the current group."""
        if self._as:
            self._as.menu_click(["Track", "Group", "Modify..."])
        return {"status": "ok", "action": "modify_group"}

    def delete(self) -> dict:
        """Delete the current group."""
        if self._as:
            self._as.menu_click(["Track", "Group", "Delete..."])
            time.sleep(0.3)
            self._as.keystroke("\r")
        return {"status": "ok", "action": "delete_group"}

    def enable_toggle(self) -> dict:
        """Toggle group enable/disable. Cmd+Shift+G"""
        if self._as:
            self._as.keystroke("g", modifiers=["command", "shift"])
        return {"status": "ok", "action": "toggle_group"}

    def suspend_all(self) -> dict:
        """Suspend all groups."""
        if self._hui:
            self._hui._send_switch(0x11, 0x04)  # Suspend zone
        elif self._as:
            self._as.keystroke("g", modifiers=["command", "shift", "option"])
        return {"status": "ok", "action": "suspend_all_groups"}
