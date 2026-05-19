"""Pro Tools bounce and export operations."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class BounceController:
    """Controls Pro Tools bounce and export operations via AppleScript."""

    def __init__(self, applescript: ProToolsAppleScript | None = None):
        self._as = applescript

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError("Bounce operations require AppleScript bridge.")
        return self._as

    def bounce_to_disk(self, file_type: str = "BWF", format: str = "Interleaved",
                       bit_depth: int = 24, sample_rate: int = 48000,
                       offline: bool = True) -> dict:
        """Bounce the current session to disk.
        
        Opens the Bounce to Disk dialog via Cmd+Shift+B and attempts to 
        configure it via AppleScript dialog interaction.
        
        Args:
            file_type: "BWF", "WAV", "AIFF", "MP3"
            format: "Interleaved", "Multiple Mono"
            bit_depth: 16, 24, or 32
            sample_rate: Output sample rate
            offline: True for offline bounce (faster), False for real-time
        """
        aps = self._require_as()
        aps.bounce_to_disk(
            file_type=file_type, bounce_format=format,
            bit_depth=bit_depth, sample_rate=sample_rate,
        )
        return {
            "status": "ok",
            "action": "bounce_to_disk",
            "file_type": file_type,
            "format": format,
            "bit_depth": bit_depth,
            "sample_rate": sample_rate,
        }

    def bounce_via_menu(self) -> dict:
        """Open Bounce to Disk dialog via menu (alternative approach).
        
        Uses File > Bounce to > Disk... menu path.
        """
        aps = self._require_as()
        aps.menu_click(["File", "Bounce to", "Disk..."])
        return {"status": "ok", "action": "bounce_dialog_opened"}

    def export_clips_as_files(self) -> dict:
        """Export selected clips as individual files.
        
        Uses File > Export > Clips as Files... menu.
        """
        aps = self._require_as()
        aps.menu_click(["File", "Export", "Clips as Files..."])
        return {"status": "ok", "action": "export_clips_dialog_opened"}

    def export_selected_as_files(self, destination: str | None = None,
                                  file_type: str = "BWF",
                                  bit_depth: int = 24,
                                  sample_rate: int = 48000) -> dict:
        """Export selected clips as individual audio files.
        
        Args:
            destination: Output directory path. If None, uses default.
            file_type: "BWF", "WAV", "AIFF"
            bit_depth: 16, 24, or 32
            sample_rate: Output sample rate
        """
        aps = self._require_as()
        aps.menu_click(["File", "Export", "Clips as Files..."])
        time.sleep(1.0)
        
        # Dialog interaction would go here
        # The export dialog is complex and varies by PT version
        # For now, accept defaults and let the user handle the dialog
        
        return {
            "status": "ok",
            "action": "export_selected_as_files",
            "note": "Export dialog opened. Configure settings manually if needed.",
        }

    def print_to_send(self) -> dict:
        """Initiate a Print to Send operation (commit real-time processing).
        
        Available in Pro Tools Ultimate only.
        """
        aps = self._require_as()
        aps.menu_click(["Track", "Commit..."])
        time.sleep(0.5)
        aps.keystroke("\r")  # Accept defaults
        return {"status": "ok", "action": "print_to_send"}
