"""Pro Tools marker / Memory Location management."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class MarkerController:
    """Manages Pro Tools Memory Locations / Markers via AppleScript."""

    def __init__(self, applescript: ProToolsAppleScript | None = None):
        self._as = applescript

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError("Marker operations require AppleScript bridge.")
        return self._as

    def create(self, name: str | None = None) -> dict:
        """Create a new Memory Location at the current cursor position.
        
        Uses numpad Enter to open the New Memory Location dialog,
        then types the name if provided.
        """
        aps = self._require_as()
        # Numpad Enter opens New Memory Location dialog
        aps.key_code(76)  # Numpad Enter
        time.sleep(0.5)
        if name:
            aps.keystroke("a", modifiers=["command"])
            time.sleep(0.1)
            aps.keystroke(name)
        time.sleep(0.1)
        aps.keystroke("\r")  # Confirm
        return {"status": "ok", "action": "create_marker", "name": name}

    def recall(self, number: int) -> dict:
        """Recall (jump to) a Memory Location by number.
        
        Uses numpad: type the number then press numpad period (.) to recall.
        """
        aps = self._require_as()
        # Type the memory location number on the numpad
        for digit in str(number):
            aps.keystroke(digit)
            time.sleep(0.05)
        aps.keystroke(".")  # Numpad period to recall
        return {"status": "ok", "action": "recall_marker", "number": number}

    def show_window(self) -> dict:
        """Show the Memory Locations window. Cmd+5"""
        aps = self._require_as()
        aps.keystroke("5", modifiers=["command"])
        return {"status": "ok", "action": "show_memory_locations_window"}

    def delete_all(self) -> dict:
        """Delete all Memory Locations (via Memory Locations window menu)."""
        aps = self._require_as()
        self.show_window()
        time.sleep(0.5)
        return {
            "status": "ok",
            "action": "delete_all_markers",
            "note": "Memory Locations window opened. Use its menu to delete.",
        }
