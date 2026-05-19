"""Pro Tools session management — new, open, save, close, import."""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript
    from cli_anything.protools.utils.aaf_engine import AAFBuilder


class SessionController:
    """Manages Pro Tools sessions via AppleScript and AAF."""

    def __init__(self, applescript: ProToolsAppleScript | None = None):
        self._as = applescript
        self._current_session: dict | None = None

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError(
                "Session operations require AppleScript bridge.\n"
                "Pro Tools must be running on this Mac."
            )
        return self._as

    def new_session(self, name: str, path: str | None = None,
                    sample_rate: int = 48000, bit_depth: int = 24,
                    file_type: str = "BWF",
                    io_settings: str | None = None) -> dict:
        """Create a new Pro Tools session.
        
        Args:
            name: Session name.
            path: Directory to save in. Defaults to ~/Documents.
            sample_rate: 44100, 48000, 88200, 96000, etc.
            bit_depth: 16 or 24.
            file_type: "BWF" or "AIFF".
            io_settings: Optional I/O settings preset name.
        """
        aps = self._require_as()
        aps.new_session(name, sample_rate=sample_rate, bit_depth=bit_depth,
                       file_type=file_type)
        
        self._current_session = {
            "name": name,
            "sample_rate": sample_rate,
            "bit_depth": bit_depth,
            "file_type": file_type,
            "path": path or str(Path.home() / "Documents" / name),
        }
        return {"status": "ok", "action": "new_session", "session": self._current_session}

    def open_session(self, path: str) -> dict:
        """Open an existing Pro Tools session.
        
        Args:
            path: Full path to .ptx or .ptf file.
        """
        aps = self._require_as()
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Session file not found: {path}")
        
        aps.open_session(path)
        name = Path(path).stem
        self._current_session = {
            "name": name,
            "path": str(Path(path).parent),
            "file": path,
        }
        return {"status": "ok", "action": "open_session", "session": self._current_session}

    def save_session(self) -> dict:
        """Save the current session (Cmd+S)."""
        aps = self._require_as()
        aps.save_session()
        return {"status": "ok", "action": "save_session"}

    def save_session_as(self, path: str) -> dict:
        """Save the current session to a new location."""
        aps = self._require_as()
        path = os.path.expanduser(path)
        aps.save_session_as(path)
        if self._current_session:
            self._current_session["path"] = str(Path(path).parent)
            self._current_session["file"] = path
        return {"status": "ok", "action": "save_session_as", "path": path}

    def close_session(self) -> dict:
        """Close the current session."""
        aps = self._require_as()
        aps.close_session()
        self._current_session = None
        return {"status": "ok", "action": "close_session"}

    def import_aaf(self, aaf_path: str) -> dict:
        """Import an AAF file into Pro Tools.

        Uses File > Import > Session Data... menu path.
        """
        aps = self._require_as()
        aaf_path = os.path.expanduser(aaf_path)
        if not os.path.exists(aaf_path):
            raise FileNotFoundError(f"AAF file not found: {aaf_path}")

        # Use the import session data menu path
        aps.menu_click(["File", "Import", "Session Data..."])
        time.sleep(1.0)
        # Use clipboard paste for the file path (handles special characters)
        aps.keystroke("g", modifiers=["command", "shift"])  # Go to folder
        time.sleep(0.5)
        aps._clipboard_paste(aaf_path)
        time.sleep(0.3)
        aps.keystroke("\r")  # Confirm file selection
        time.sleep(1.0)
        aps.keystroke("\r")  # Accept import settings dialog

        return {"status": "ok", "action": "import_aaf", "path": aaf_path}

    def build_and_import_aaf(self, template: dict, output_path: str | None = None) -> dict:
        """Build an AAF from a template and import it into Pro Tools.
        
        Args:
            template: AAF template dict (see AAFBuilder.build_from_template).
            output_path: Where to save the AAF. Defaults to /tmp/cli-anything-protools-import.aaf
        """
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        
        if output_path is None:
            output_path = "/tmp/cli-anything-protools-import.aaf"
        
        builder = AAFBuilder(
            name=template.get("name", "Import"),
            sample_rate=template.get("sample_rate", 48000),
            bit_depth=template.get("bit_depth", 24),
            timecode_fps=template.get("fps", 24.0),
        )
        builder.build_from_template(template, output_path)
        
        result = self.import_aaf(output_path)
        result["aaf_path"] = output_path
        result["action"] = "build_and_import_aaf"
        return result

    def get_info(self) -> dict:
        """Get info about the current session."""
        return {
            "status": "ok",
            "session": self._current_session,
        }
