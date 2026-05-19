"""Pro Tools audio import operations."""

from __future__ import annotations
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class ImportController:
    """Controls Pro Tools audio import operations via AppleScript."""

    def __init__(self, applescript: ProToolsAppleScript | None = None):
        self._as = applescript

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError("Import operations require AppleScript bridge.")
        return self._as

    def import_audio(self, file_path: str) -> dict:
        """Import an audio file. Uses Cmd+Shift+I shortcut.
        
        Args:
            file_path: Path to audio file (WAV, AIFF, MP3, etc.)
        """
        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        aps = self._require_as()
        aps.import_audio(file_path)
        return {"status": "ok", "action": "import_audio", "file": file_path}

    def import_session_data(self, session_path: str) -> dict:
        """Import session data from another Pro Tools session.

        Uses File > Import > Session Data... menu.
        """
        session_path = os.path.expanduser(session_path)
        if not os.path.exists(session_path):
            raise FileNotFoundError(f"Session file not found: {session_path}")

        aps = self._require_as()
        aps.menu_click(["File", "Import", "Session Data..."])
        time.sleep(1.0)
        aps.keystroke("g", modifiers=["command", "shift"])
        time.sleep(0.5)
        aps._clipboard_paste(session_path)
        time.sleep(0.3)
        aps.keystroke("\r")

        return {"status": "ok", "action": "import_session_data", "path": session_path}

    def import_audio_to_track(self, file_path: str, track_name: str | None = None) -> dict:
        """Import audio file and place it on a specific track.
        
        This first imports the audio, then if a track name is specified,
        attempts to use the Workspace browser approach.
        """
        result = self.import_audio(file_path)
        if track_name:
            result["target_track"] = track_name
            result["note"] = "Audio imported. May need manual placement on target track."
        return result
