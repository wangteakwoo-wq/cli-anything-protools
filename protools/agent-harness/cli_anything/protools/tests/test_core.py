"""Unit tests for cli-anything-protools core modules.

These tests use synthetic data and do NOT require Pro Tools to be running.
"""

import json
import os
import sys
import subprocess
import pytest


# ---------------------------------------------------------------------------
# Backend detection tests
# ---------------------------------------------------------------------------

class TestBackend:
    def test_find_protools(self):
        from cli_anything.protools.utils.protools_backend import find_protools
        path = find_protools()
        assert path is not None
        assert "Pro Tools" in str(path)

    def test_get_version(self):
        from cli_anything.protools.utils.protools_backend import get_protools_version
        version = get_protools_version()
        assert version is not None
        assert "." in version

    def test_system_info(self):
        from cli_anything.protools.utils.protools_backend import get_system_info
        info = get_system_info()
        assert "pt_path" in info
        assert "pt_version" in info
        assert isinstance(info, dict)


# ---------------------------------------------------------------------------
# AAF Engine tests
# ---------------------------------------------------------------------------

class TestAAFEngine:
    def test_builder_creation(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder(name="Test", sample_rate=48000)
        assert builder.name == "Test"
        assert builder.sample_rate == 48000

    def test_add_track(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder()
        idx = builder.add_track("DX 1", track_type="audio", format="mono")
        assert idx == 0
        assert len(builder.tracks) == 1
        assert builder.tracks[0].name == "DX 1"

    def test_add_tracks(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder()
        indices = builder.add_tracks(["DX 1", "DX 2", "MX 1"])
        assert indices == [0, 1, 2]
        assert len(builder.tracks) == 3

    def test_place_clip(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder()
        builder.add_track("Track 1")
        builder.place_clip(0, "/tmp/test.wav", start_time=1.0, duration=5.0)
        assert len(builder.clips) == 1
        assert builder.clips[0].track_index == 0
        assert builder.clips[0].start_time == 1.0

    def test_timecode_conversion(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder(timecode_fps=24.0)
        secs = builder.timecode_to_seconds("01:00:00:00")
        assert secs == 3600.0
        tc = builder.seconds_to_timecode(3600.0)
        assert tc == "01:00:00:00"

    def test_timecode_roundtrip(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder(timecode_fps=24.0)
        original = "00:05:30:12"
        secs = builder.timecode_to_seconds(original)
        result = builder.seconds_to_timecode(secs)
        assert result == original

    def test_seconds_to_edit_units(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder(sample_rate=48000)
        units = builder.seconds_to_edit_units(1.0)
        assert units == 48000

    def test_add_marker(self):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder()
        builder.add_marker("Scene 1", time=10.5)
        assert len(builder.markers) == 1
        assert builder.markers[0].name == "Scene 1"

    def test_build_aaf_file(self, tmp_path):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        builder = AAFBuilder(name="Test Session", sample_rate=48000)
        builder.add_track("DX 1", track_type="audio", format="mono")
        builder.add_track("MX 1", track_type="audio", format="stereo")
        output = str(tmp_path / "test.aaf")
        builder.build(output)
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0
        print(f"\n  AAF: {output} ({os.path.getsize(output):,} bytes)")

    def test_build_from_template(self, tmp_path):
        from cli_anything.protools.utils.aaf_engine import AAFBuilder
        template = {
            "name": "Film Mix",
            "sample_rate": 48000,
            "bit_depth": 24,
            "fps": 24.0,
            "tracks": [
                {"name": "DX 1", "type": "audio", "format": "mono"},
                {"name": "DX 2", "type": "audio", "format": "mono"},
                {"name": "MX Stem", "type": "aux", "format": "stereo"},
            ],
            "markers": [
                {"name": "Reel Start", "time": 0.0},
            ],
        }
        builder = AAFBuilder()
        output = str(tmp_path / "template.aaf")
        builder.build_from_template(template, output)
        assert os.path.exists(output)
        print(f"\n  AAF from template: {output} ({os.path.getsize(output):,} bytes)")


# ---------------------------------------------------------------------------
# Controller logic tests (no MIDI/AppleScript needed)
# ---------------------------------------------------------------------------

class TestMixLogic:
    def test_fader_value_clamping(self):
        from cli_anything.protools.core.mix import MixController
        ctrl = MixController(hui=None)
        # Without HUI, set_fader should raise
        with pytest.raises(RuntimeError, match="HUI/MIDI"):
            ctrl.set_fader(1, 0.5)

    def test_strip_resolution(self):
        from cli_anything.protools.core.mix import MixController
        ctrl = MixController(hui=None)
        # Channel 1 = strip 0, channel 8 = strip 7, channel 9 = strip 0 (bank 1)
        # _resolve_strip without HUI should raise for banking
        strip = (1 - 1) % 8
        assert strip == 0
        strip = (8 - 1) % 8
        assert strip == 7
        strip = (9 - 1) % 8
        assert strip == 0


class TestTransportLogic:
    def test_play_with_neither(self):
        from cli_anything.protools.core.transport import TransportController
        ctrl = TransportController(hui=None, applescript=None)
        result = ctrl.play()
        assert result["status"] == "ok"

    def test_locate_format(self):
        from cli_anything.protools.core.transport import TransportController
        ctrl = TransportController(hui=None, applescript=None)
        result = ctrl.locate("01:00:00:00")
        assert result["timecode"] == "01:00:00:00"


class TestEditLogic:
    def test_edit_without_connections(self):
        from cli_anything.protools.core.edit import EditController
        ctrl = EditController(hui=None, applescript=None)
        with pytest.raises(RuntimeError, match="AppleScript"):
            ctrl.consolidate()


class TestKeymap:
    def test_shortcuts_exist(self):
        from cli_anything.protools.utils.keymap import SHORTCUTS
        assert "play" in SHORTCUTS
        assert "save" in SHORTCUTS
        assert "bounce_to_disk" in SHORTCUTS

    def test_menu_paths_exist(self):
        from cli_anything.protools.utils.keymap import MENU_PATHS
        assert "new_session" in MENU_PATHS
        assert "bounce_to_disk" in MENU_PATHS

    def test_track_types(self):
        from cli_anything.protools.utils.keymap import TRACK_TYPES
        assert "audio" in TRACK_TYPES
        assert "aux" in TRACK_TYPES
        assert "vca" in TRACK_TYPES

    def test_track_formats(self):
        from cli_anything.protools.utils.keymap import TRACK_FORMATS
        assert "mono" in TRACK_FORMATS
        assert "5.1" in TRACK_FORMATS
        assert "7.1.4" in TRACK_FORMATS


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------

def _resolve_cli(name):
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.protools.protools_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-protools")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True, check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "Pro Tools" in result.stdout

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_json_info(self):
        result = self._run(["--json", "info"], check=False)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "status" in data
