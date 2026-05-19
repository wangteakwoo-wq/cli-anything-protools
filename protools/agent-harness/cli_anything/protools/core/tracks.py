"""Pro Tools track management — create, delete, select, configure tracks."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class TrackController:
    """Manages Pro Tools tracks via AppleScript and HUI."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def new_track(self, count: int = 1, track_type: str = "audio",
                  format: str = "mono", timebase: str = "samples",
                  name: str | None = None) -> dict:
        """Create new tracks via Track > New... dialog.
        
        Args:
            count: Number of tracks to create.
            track_type: "audio", "aux", "master", "vca", "midi", "instrument", "routing_folder"
            format: "mono", "stereo", "5.1", "7.1", "7.1.2", "7.1.4"
            timebase: "samples" or "ticks"
            name: Optional name for the track(s).
        """
        if self._as is None:
            raise RuntimeError("Track creation requires AppleScript bridge.")
        
        self._as.new_track(count=count, track_type=track_type,
                          track_format=format, timebase=timebase)
        
        # If a name is provided, rename the track(s) after creation
        if name and count == 1:
            time.sleep(0.5)
            self.rename_selected(name)
        
        return {
            "status": "ok",
            "action": "new_track",
            "count": count,
            "type": track_type,
            "format": format,
            "name": name,
        }

    def new_tracks_batch(self, tracks: list[dict]) -> dict:
        """Create multiple tracks with different configurations.
        
        Args:
            tracks: List of dicts with keys: count, type, format, name.
                   Example: [
                       {"count": 4, "type": "audio", "format": "mono", "name": "DX"},
                       {"count": 2, "type": "audio", "format": "stereo", "name": "MX"},
                       {"count": 1, "type": "aux", "format": "5.1", "name": "DX Stem"},
                       {"count": 1, "type": "master", "format": "5.1", "name": "Master"},
                   ]
        """
        results = []
        for spec in tracks:
            result = self.new_track(
                count=spec.get("count", 1),
                track_type=spec.get("type", "audio"),
                format=spec.get("format", "mono"),
                name=spec.get("name"),
            )
            results.append(result)
            time.sleep(0.5)
        
        return {"status": "ok", "action": "new_tracks_batch", "created": results}

    def delete_selected(self) -> dict:
        """Delete currently selected track(s)."""
        if self._as is None:
            raise RuntimeError("Track deletion requires AppleScript bridge.")
        self._as.menu_click(["Track", "Delete"])
        time.sleep(1.0)
        # Pro Tools may not show a confirmation dialog for track deletion
        # (it deletes immediately), or the dialog button may vary.
        try:
            self._as.click_button("Delete")
        except RuntimeError:
            try:
                self._as.click_button("OK")
            except RuntimeError:
                pass
        return {"status": "ok", "action": "delete_track"}

    def duplicate_selected(self) -> dict:
        """Duplicate currently selected track(s)."""
        if self._as is None:
            raise RuntimeError("Track duplication requires AppleScript bridge.")
        self._as.menu_click(["Track", "Duplicate..."])
        time.sleep(0.5)
        self._as.keystroke("\r")  # Accept defaults
        return {"status": "ok", "action": "duplicate_track"}

    def select_by_hui(self, channel: int) -> dict:
        """Select a track via HUI channel select button.

        Args:
            channel: Channel number (1-based).
        """
        if self._hui is None:
            raise RuntimeError("Track selection via HUI requires MIDI connection.")
        strip = self._hui.navigate_to_channel(channel)
        self._hui.select(strip)
        return {"status": "ok", "action": "select_track", "channel": channel}

    def rename_selected(self, name: str) -> dict:
        """Rename the currently selected track by double-clicking the name area.
        
        This works by using the keyboard shortcut for track rename if available,
        or by sending the name characters via AppleScript.
        """
        if self._as is None:
            raise RuntimeError("Track rename requires AppleScript bridge.")
        # In Pro Tools, you can double-click the track name to rename
        # Via keyboard: after selecting a track, use Cmd+Option+R or 
        # simply use the HUI scribble strip area
        # Simplest approach: use AppleScript to interact with the track name field
        # This is one of the more fragile operations
        self._as.keystroke("r", modifiers=["command", "option"])
        time.sleep(0.3)
        self._as.keystroke("a", modifiers=["command"])  # Select all text
        time.sleep(0.1)
        self._as.keystroke(name)
        time.sleep(0.1)
        self._as.keystroke("\r")
        return {"status": "ok", "action": "rename_track", "name": name}

    def make_inactive(self) -> dict:
        """Make selected track(s) inactive."""
        if self._as is None:
            raise RuntimeError("Requires AppleScript bridge.")
        self._as.menu_click(["Track", "Make Inactive"])
        return {"status": "ok", "action": "make_inactive"}

    def make_active(self) -> dict:
        """Make selected track(s) active."""
        if self._as is None:
            raise RuntimeError("Requires AppleScript bridge.")
        self._as.menu_click(["Track", "Make Active"])
        return {"status": "ok", "action": "make_active"}

    def split_into_mono(self) -> dict:
        """Split selected stereo/multichannel track into mono tracks."""
        if self._as is None:
            raise RuntimeError("Requires AppleScript bridge.")
        self._as.menu_click(["Track", "Split into Mono"])
        return {"status": "ok", "action": "split_into_mono"}

    def get_channel_names(self) -> dict:
        """Read channel names from HUI scribble strip feedback."""
        if self._hui is None:
            return {"status": "ok", "channel_names": [], "note": "HUI not connected"}
        self._hui.process_incoming()
        return {
            "status": "ok",
            "channel_names": list(self._hui.channel_names),
            "bank": self._hui.current_bank,
        }
