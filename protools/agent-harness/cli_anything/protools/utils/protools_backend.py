"""Backend detection for Avid Pro Tools installation and runtime state."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any


PT_BUNDLE_IDS = ("com.avid.ProTools", "com.avid.ProToolsDeveloper")

_logger = logging.getLogger(__name__)
PT_APP_PATHS = (
    Path("/Applications/Pro Tools.app"),
    Path("/Applications/Pro Tools Developer.app"),
)

INSTALL_INSTRUCTIONS = (
    "Pro Tools not found. Install from https://www.avid.com/pro-tools "
    "or ensure the app bundle is in /Applications/."
)

IAC_INSTRUCTIONS = (
    "IAC Driver not found. Enable it in Audio MIDI Setup:\n"
    "  1. Open /Applications/Utilities/Audio MIDI Setup.app\n"
    "  2. Window → Show MIDI Studio\n"
    "  3. Double-click IAC Driver\n"
    "  4. Check 'Device is online'"
)


def find_protools() -> Path:
    """Return the path to the Pro Tools app bundle, or raise RuntimeError."""
    for path in PT_APP_PATHS:
        if path.exists():
            return path
    raise RuntimeError(INSTALL_INSTRUCTIONS)


def get_protools_version() -> str:
    """Read the Pro Tools version from its Info.plist."""
    app_path = find_protools()
    bundle_id = _bundle_id_for_path(app_path)
    try:
        result = subprocess.run(
            ["defaults", "read", str(app_path / "Contents" / "Info"), "CFBundleShortVersionString"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["mdls", "-name", "kMDItemVersion", str(app_path)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for part in result.stdout.split('"'):
                if part and part[0].isdigit():
                    return part
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "unknown"


def check_protools_running() -> bool:
    """Return True if Pro Tools is currently running."""
    try:
        script = (
            'tell application "System Events" to name of every process '
            'whose background only is false'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            processes = result.stdout.strip()
            return "Pro Tools" in processes
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def check_iac_driver() -> bool:
    """Return True if the IAC Driver MIDI port is available."""
    try:
        import rtmidi
        midi_out = rtmidi.MidiOut()
        ports = midi_out.get_ports()
        del midi_out
        return any("IAC" in p for p in ports)
    except Exception as exc:
        _logger.debug("IAC Driver check failed: %s", exc)
        return False


def _list_midi_ports() -> list[str]:
    """Return a list of available MIDI output port names."""
    try:
        import rtmidi
        midi_out = rtmidi.MidiOut()
        ports = midi_out.get_ports()
        del midi_out
        return list(ports)
    except Exception as exc:
        _logger.debug("MIDI port listing failed: %s", exc)
        return []


def _bundle_id_for_path(app_path: Path) -> str:
    if "Developer" in app_path.name:
        return PT_BUNDLE_IDS[1]
    return PT_BUNDLE_IDS[0]


def get_system_info() -> dict[str, Any]:
    """Return a dict summarising Pro Tools installation and runtime state."""
    info: dict[str, Any] = {
        "pt_path": None,
        "pt_version": None,
        "pt_running": False,
        "iac_available": False,
        "midi_ports": [],
    }

    try:
        pt_path = find_protools()
        info["pt_path"] = str(pt_path)
        info["pt_version"] = get_protools_version()
    except RuntimeError:
        pass

    info["pt_running"] = check_protools_running()
    info["iac_available"] = check_iac_driver()
    info["midi_ports"] = _list_midi_ports()

    return info
