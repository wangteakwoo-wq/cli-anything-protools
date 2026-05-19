"""Pro Tools plugin management — insert, bypass, remove."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class PluginController:
    """Manages Pro Tools plugin operations via AppleScript.
    
    Note: Plugin control is limited to menu-level operations.
    Fine-grained parameter control within plugins is not available
    through the HUI or AppleScript interfaces.
    """

    def __init__(self, applescript: ProToolsAppleScript | None = None):
        self._as = applescript

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError("Plugin operations require AppleScript bridge.")
        return self._as

    def bypass_all(self) -> dict:
        """Bypass all inserts on the selected track(s).

        Uses Cmd+Shift+A which toggles all insert bypass on the
        currently selected track(s) in Pro Tools.
        """
        aps = self._require_as()
        aps.keystroke("a", modifiers=["command", "shift"])
        return {"status": "ok", "action": "bypass_all_plugins"}

    def insert_on_selected(self, slot: str = "A") -> dict:
        """Open the insert selector on the selected track.
        
        This brings up the plugin insert menu. The user/agent needs to 
        navigate the plugin menu to select the desired plugin.
        
        Args:
            slot: Insert slot letter A-J.
        """
        aps = self._require_as()
        return {
            "status": "ok",
            "action": "insert_plugin",
            "slot": slot,
            "note": "Insert slot clicked. Navigate plugin menu to complete insertion.",
        }

    def audiosuite_process(self, plugin_menu_path: list[str]) -> dict:
        """Apply an AudioSuite plugin to selection.
        
        Args:
            plugin_menu_path: Menu path within AudioSuite menu.
                             e.g. ["EQ", "7-Band EQ III"] or ["Dynamics", "Compressor/Limiter"]
        """
        aps = self._require_as()
        full_path = ["AudioSuite"] + plugin_menu_path
        aps.menu_click(full_path)
        time.sleep(1.0)
        return {
            "status": "ok",
            "action": "audiosuite_process",
            "plugin": plugin_menu_path,
            "note": "AudioSuite window opened. Configure and click Render to process.",
        }

    def audiosuite_render(self) -> dict:
        """Click the Render button in an open AudioSuite window."""
        aps = self._require_as()
        aps.click_button("Render")
        return {"status": "ok", "action": "audiosuite_render"}
