"""cli-anything-protools — Agent-native CLI for Avid Pro Tools.

Entry point for the CLI. Provides subcommand groups for all Pro Tools
operations plus an interactive REPL when invoked without arguments.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from functools import wraps
from typing import Any

import click

# ---------------------------------------------------------------------------
# Lazy controller singletons — created on first use
# ---------------------------------------------------------------------------

_hui = None
_applescript = None
_transport = None
_mix = None
_session = None
_tracks = None
_edit = None
_bounce = None
_automation = None
_plugins = None
_io_routing = None
_meter = None
_markers = None
_groups = None
_navigate = None
_import_audio = None

_logger = logging.getLogger(__name__)


def _init_hui():
    global _hui
    if _hui is not None:
        return _hui
    try:
        from cli_anything.protools.utils.midi_io import MidiIO
        from cli_anything.protools.utils.hui_engine import HUIEngine
        midi = MidiIO()
        midi.open("IAC")
        _hui = HUIEngine(midi)
        _hui.start_ping_handler()
        return _hui
    except Exception as exc:
        _logger.debug("HUI/MIDI init failed: %s", exc)
        return None


def _init_applescript():
    global _applescript
    if _applescript is not None:
        return _applescript
    try:
        from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript
        _applescript = ProToolsAppleScript()
        return _applescript
    except Exception as exc:
        _logger.debug("AppleScript init failed: %s", exc)
        return None


def _get_transport():
    global _transport
    if _transport is None:
        from cli_anything.protools.core.transport import TransportController
        _transport = TransportController(hui=_init_hui(), applescript=_init_applescript())
    return _transport


def _get_mix():
    global _mix
    if _mix is None:
        from cli_anything.protools.core.mix import MixController
        _mix = MixController(hui=_init_hui())
    return _mix


def _get_session():
    global _session
    if _session is None:
        from cli_anything.protools.core.session import SessionController
        _session = SessionController(applescript=_init_applescript())
    return _session


def _get_tracks():
    global _tracks
    if _tracks is None:
        from cli_anything.protools.core.tracks import TrackController
        _tracks = TrackController(hui=_init_hui(), applescript=_init_applescript())
    return _tracks


def _get_edit():
    global _edit
    if _edit is None:
        from cli_anything.protools.core.edit import EditController
        _edit = EditController(hui=_init_hui(), applescript=_init_applescript())
    return _edit


def _get_bounce():
    global _bounce
    if _bounce is None:
        from cli_anything.protools.core.bounce import BounceController
        _bounce = BounceController(applescript=_init_applescript())
    return _bounce


def _get_automation():
    global _automation
    if _automation is None:
        from cli_anything.protools.core.automation import AutomationController
        _automation = AutomationController(hui=_init_hui(), applescript=_init_applescript())
    return _automation


def _get_plugins():
    global _plugins
    if _plugins is None:
        from cli_anything.protools.core.plugins import PluginController
        _plugins = PluginController(applescript=_init_applescript())
    return _plugins


def _get_io():
    global _io_routing
    if _io_routing is None:
        from cli_anything.protools.core.io_routing import IORoutingController
        _io_routing = IORoutingController(hui=_init_hui(), applescript=_init_applescript())
    return _io_routing


def _get_meter():
    global _meter
    if _meter is None:
        from cli_anything.protools.core.meter import MeterController
        _meter = MeterController(hui=_init_hui())
    return _meter


def _get_markers():
    global _markers
    if _markers is None:
        from cli_anything.protools.core.markers import MarkerController
        _markers = MarkerController(applescript=_init_applescript())
    return _markers


def _get_groups():
    global _groups
    if _groups is None:
        from cli_anything.protools.core.groups import GroupController
        _groups = GroupController(hui=_init_hui(), applescript=_init_applescript())
    return _groups


def _get_navigate():
    global _navigate
    if _navigate is None:
        from cli_anything.protools.core.navigate import NavigateController
        _navigate = NavigateController(hui=_init_hui(), applescript=_init_applescript())
    return _navigate


def _get_import():
    global _import_audio
    if _import_audio is None:
        from cli_anything.protools.core.import_audio import ImportController
        _import_audio = ImportController(applescript=_init_applescript())
    return _import_audio


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _output(ctx: click.Context, data: dict[str, Any]):
    """Output result as JSON or human-readable."""
    if ctx.obj.get("json_mode"):
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        action = data.get("action", "")
        status = data.get("status", "")
        if status == "ok":
            msg_parts = [f"✓ {action}"]
            for k, v in data.items():
                if k not in ("status", "action"):
                    msg_parts.append(f"  {k}: {v}")
            click.echo("\n".join(msg_parts))
        else:
            click.echo(f"✗ {action}: {data}", err=True)


# ---------------------------------------------------------------------------
# Main CLI group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format for agent consumption.")
@click.version_option("1.0.0", prog_name="cli-anything-protools")
@click.pass_context
def cli(ctx, json_mode: bool):
    """cli-anything-protools — Agent-native CLI for Avid Pro Tools.

    Control Pro Tools mixing, editing, transport, and session management
    from the command line. Designed for AI agents and automation workflows.

    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ---------------------------------------------------------------------------
# System info command
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def info(ctx):
    """Show Pro Tools system information and connection status."""
    from cli_anything.protools.utils.protools_backend import get_system_info
    data = get_system_info()
    _output(ctx, {"status": "ok", "action": "system_info", **data})


# ---------------------------------------------------------------------------
# Transport commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def transport(ctx):
    """Transport control — play, stop, record, locate."""
    pass


@transport.command()
@click.pass_context
def play(ctx):
    """Start playback."""
    _output(ctx, _get_transport().play())


@transport.command()
@click.pass_context
def stop(ctx):
    """Stop playback or recording."""
    _output(ctx, _get_transport().stop())


@transport.command()
@click.pass_context
def record(ctx):
    """Enter record mode."""
    _output(ctx, _get_transport().record())


@transport.command()
@click.pass_context
def rtz(ctx):
    """Return to zero (session start)."""
    _output(ctx, _get_transport().return_to_zero())


@transport.command()
@click.argument("timecode")
@click.pass_context
def locate(ctx, timecode: str):
    """Locate to timecode position (HH:MM:SS:FF)."""
    _output(ctx, _get_transport().locate(timecode))


@transport.command("loop")
@click.pass_context
def loop_toggle(ctx):
    """Toggle loop/cycle playback."""
    _output(ctx, _get_transport().loop_toggle())


@transport.command("mark-in")
@click.pass_context
def mark_in(ctx):
    """Mark selection in-point at cursor."""
    _output(ctx, _get_transport().mark_in())


@transport.command("mark-out")
@click.pass_context
def mark_out(ctx):
    """Mark selection out-point at cursor."""
    _output(ctx, _get_transport().mark_out())


# ---------------------------------------------------------------------------
# Mix commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def mix(ctx):
    """Mixer control — faders, pans, mute, solo, sends."""
    pass


@mix.command()
@click.argument("channel", type=int)
@click.argument("value", type=float)
@click.pass_context
def fader(ctx, channel: int, value: float):
    """Set channel fader (0.0 to 1.0). Channel is 1-based."""
    _output(ctx, _get_mix().set_fader(channel, value))


@mix.command("fader-db", context_settings={"ignore_unknown_options": True})
@click.argument("channel", type=int)
@click.argument("db", type=float)
@click.pass_context
def fader_db(ctx, channel: int, db: float):
    """Set channel fader by dB value (-inf to +6). Use -- before negative values."""
    _output(ctx, _get_mix().set_fader_db(channel, db))


@mix.command(context_settings={"ignore_unknown_options": True})
@click.argument("channel", type=int)
@click.argument("value", type=float)
@click.pass_context
def pan(ctx, channel: int, value: float):
    """Set pan position (-1.0 left to 1.0 right). Use -- before negative values."""
    _output(ctx, _get_mix().set_pan(channel, value))


@mix.command()
@click.argument("channel", type=int)
@click.pass_context
def mute(ctx, channel: int):
    """Toggle mute on channel."""
    _output(ctx, _get_mix().mute(channel))


@mix.command()
@click.argument("channel", type=int)
@click.pass_context
def solo(ctx, channel: int):
    """Toggle solo on channel."""
    _output(ctx, _get_mix().solo(channel))


@mix.command("rec-arm")
@click.argument("channel", type=int)
@click.pass_context
def rec_arm(ctx, channel: int):
    """Toggle record arm on channel."""
    _output(ctx, _get_mix().rec_arm(channel))


@mix.command("select")
@click.argument("channel", type=int)
@click.pass_context
def mix_select(ctx, channel: int):
    """Select a channel strip."""
    _output(ctx, _get_mix().select(channel))


@mix.command("bank-left")
@click.pass_context
def bank_left(ctx):
    """Bank left (previous 8 channels)."""
    _output(ctx, _get_mix().bank_left())


@mix.command("bank-right")
@click.pass_context
def bank_right(ctx):
    """Bank right (next 8 channels)."""
    _output(ctx, _get_mix().bank_right())


@mix.command("go-to")
@click.argument("channel", type=int)
@click.pass_context
def go_to_channel(ctx, channel: int):
    """Navigate to channel by auto-banking."""
    _output(ctx, _get_mix().go_to_channel(channel))


@mix.command("meters")
@click.pass_context
def meters(ctx):
    """Read current meter levels."""
    _output(ctx, _get_mix().get_meters())


@mix.command("assign-pan")
@click.pass_context
def assign_pan(ctx):
    """Set V-Pot mode to Pan."""
    _output(ctx, _get_mix().assign_pan())


@mix.command("assign-send")
@click.argument("letter")
@click.pass_context
def assign_send(ctx, letter: str):
    """Set V-Pot mode to Send (A-E)."""
    _output(ctx, _get_mix().assign_send(letter))


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def session(ctx):
    """Session management — new, open, save, close, import."""
    pass


@session.command("new")
@click.option("-n", "--name", required=True, help="Session name.")
@click.option("--sr", "--sample-rate", "sample_rate", type=int, default=48000, help="Sample rate.")
@click.option("--bd", "--bit-depth", "bit_depth", type=int, default=24, help="Bit depth.")
@click.option("--file-type", type=click.Choice(["BWF", "AIFF"]), default="BWF")
@click.pass_context
def session_new(ctx, name, sample_rate, bit_depth, file_type):
    """Create a new Pro Tools session."""
    _output(ctx, _get_session().new_session(name, sample_rate=sample_rate,
                                             bit_depth=bit_depth, file_type=file_type))


@session.command("open")
@click.argument("path")
@click.pass_context
def session_open(ctx, path):
    """Open a Pro Tools session file (.ptx/.ptf)."""
    _output(ctx, _get_session().open_session(path))


@session.command("save")
@click.pass_context
def session_save(ctx):
    """Save current session."""
    _output(ctx, _get_session().save_session())


@session.command("save-as")
@click.argument("path")
@click.pass_context
def session_save_as(ctx, path):
    """Save session to new location."""
    _output(ctx, _get_session().save_session_as(path))


@session.command("close")
@click.pass_context
def session_close(ctx):
    """Close current session."""
    _output(ctx, _get_session().close_session())


@session.command("import-aaf")
@click.argument("path")
@click.pass_context
def session_import_aaf(ctx, path):
    """Import an AAF file into Pro Tools."""
    _output(ctx, _get_session().import_aaf(path))


@session.command("info")
@click.pass_context
def session_info(ctx):
    """Show current session info."""
    _output(ctx, _get_session().get_info())


# ---------------------------------------------------------------------------
# Track commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def track(ctx):
    """Track management — new, delete, select, rename."""
    pass


@track.command("new")
@click.option("-c", "--count", type=int, default=1, help="Number of tracks.")
@click.option("-t", "--type", "track_type", default="audio",
              type=click.Choice(["audio", "aux", "master", "vca", "midi", "instrument", "video"]))
@click.option(
    "-f",
    "--format",
    "fmt",
    default="mono",
    type=str,
    help='Track format (channel width), e.g. "mono", "stereo", "5.1", "7.1", "9.1.6".',
)
@click.option("-n", "--name", default=None, help="Track name.")
@click.pass_context
def track_new(ctx, count, track_type, fmt, name):
    """Create new track(s)."""
    _output(ctx, _get_tracks().new_track(count=count, track_type=track_type,
                                          format=fmt, name=name))


@track.command("calibrate")
@click.option("--max-format", default=30, type=int, help="Max items to probe for format popup.")
@click.option("--max-type", default=15, type=int, help="Max items to probe for type popup.")
@click.pass_context
def track_calibrate(ctx, max_format, max_type):
    """Calibrate New Tracks popup ordering for this Pro Tools version."""
    aps = _init_applescript()
    result = aps.calibrate_new_tracks_popups(max_format=max_format, max_type=max_type)
    _output(ctx, {"status": "ok", "action": "track_calibrate", **result})


@track.command("delete")
@click.pass_context
def track_delete(ctx):
    """Delete selected track(s)."""
    _output(ctx, _get_tracks().delete_selected())


@track.command("duplicate")
@click.pass_context
def track_duplicate(ctx):
    """Duplicate selected track(s)."""
    _output(ctx, _get_tracks().duplicate_selected())


@track.command("select")
@click.argument("channel", type=int)
@click.pass_context
def track_select(ctx, channel):
    """Select track by channel number (1-based)."""
    _output(ctx, _get_tracks().select_by_hui(channel))


@track.command("rename")
@click.argument("name")
@click.pass_context
def track_rename(ctx, name):
    """Rename selected track."""
    _output(ctx, _get_tracks().rename_selected(name))


@track.command("names")
@click.pass_context
def track_names(ctx):
    """Read channel names from HUI."""
    _output(ctx, _get_tracks().get_channel_names())


@track.command("inactive")
@click.pass_context
def track_inactive(ctx):
    """Make selected track(s) inactive."""
    _output(ctx, _get_tracks().make_inactive())


@track.command("active")
@click.pass_context
def track_active(ctx):
    """Make selected track(s) active."""
    _output(ctx, _get_tracks().make_active())


@track.command("split-mono")
@click.pass_context
def track_split_mono(ctx):
    """Split selected multichannel track into mono."""
    _output(ctx, _get_tracks().split_into_mono())


# ---------------------------------------------------------------------------
# Edit commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def edit(ctx):
    """Editing — cut, copy, paste, separate, fades, nudge."""
    pass


@edit.command()
@click.pass_context
def cut(ctx):
    """Cut selection."""
    _output(ctx, _get_edit().cut())


@edit.command()
@click.pass_context
def copy(ctx):
    """Copy selection."""
    _output(ctx, _get_edit().copy())


@edit.command()
@click.pass_context
def paste(ctx):
    """Paste at cursor."""
    _output(ctx, _get_edit().paste())


@edit.command("delete")
@click.pass_context
def edit_delete(ctx):
    """Delete selection."""
    _output(ctx, _get_edit().delete())


@edit.command()
@click.pass_context
def separate(ctx):
    """Separate (split) clip at cursor."""
    _output(ctx, _get_edit().separate())


@edit.command("heal")
@click.pass_context
def heal(ctx):
    """Heal clip separation."""
    _output(ctx, _get_edit().heal_separation())


@edit.command()
@click.pass_context
def undo(ctx):
    """Undo last action."""
    _output(ctx, _get_edit().undo())


@edit.command()
@click.pass_context
def redo(ctx):
    """Redo."""
    _output(ctx, _get_edit().redo())


@edit.command()
@click.pass_context
def consolidate(ctx):
    """Consolidate selection."""
    _output(ctx, _get_edit().consolidate())


@edit.command("select-all")
@click.pass_context
def edit_select_all(ctx):
    """Select all."""
    _output(ctx, _get_edit().select_all())


@edit.command("fade-in")
@click.pass_context
def fade_in(ctx):
    """Create fade-in."""
    _output(ctx, _get_edit().fade_in())


@edit.command("fade-out")
@click.pass_context
def fade_out(ctx):
    """Create fade-out."""
    _output(ctx, _get_edit().fade_out())


@edit.command("crossfade")
@click.pass_context
def crossfade(ctx):
    """Create crossfade."""
    _output(ctx, _get_edit().crossfade())


@edit.command("nudge-fwd")
@click.option("-n", "--count", type=int, default=1)
@click.pass_context
def nudge_fwd(ctx, count):
    """Nudge selection forward."""
    _output(ctx, _get_edit().nudge_forward_n(count))


@edit.command("nudge-bwd")
@click.option("-n", "--count", type=int, default=1)
@click.pass_context
def nudge_bwd(ctx, count):
    """Nudge selection backward."""
    _output(ctx, _get_edit().nudge_backward_n(count))


@edit.command("tab-fwd")
@click.pass_context
def tab_fwd(ctx):
    """Tab to next boundary/transient."""
    _output(ctx, _get_edit().tab_forward())


@edit.command("tab-bwd")
@click.pass_context
def tab_bwd(ctx):
    """Tab to previous boundary/transient."""
    _output(ctx, _get_edit().tab_backward())


@edit.command("tab-transient")
@click.pass_context
def tab_transient(ctx):
    """Toggle Tab to Transient mode."""
    _output(ctx, _get_edit().tab_to_transient_toggle())


@edit.command("trim-start")
@click.pass_context
def trim_start(ctx):
    """Trim clip start to cursor."""
    _output(ctx, _get_edit().trim_start_to_cursor())


@edit.command("trim-end")
@click.pass_context
def trim_end(ctx):
    """Trim clip end to cursor."""
    _output(ctx, _get_edit().trim_end_to_cursor())


@edit.command("strip-silence")
@click.pass_context
def strip_silence(ctx):
    """Open Strip Silence dialog."""
    _output(ctx, _get_edit().strip_silence())


@edit.command("spot")
@click.pass_context
def spot(ctx):
    """Open Spot dialog."""
    _output(ctx, _get_edit().spot_dialog())


# ---------------------------------------------------------------------------
# Bounce / Export commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def bounce(ctx):
    """Bounce and export operations."""
    pass


@bounce.command("disk")
@click.option("--file-type", type=click.Choice(["BWF", "WAV", "AIFF", "MP3"]), default="BWF")
@click.option("--format", "fmt", type=click.Choice(["Interleaved", "Multiple Mono"]),
              default="Interleaved")
@click.option("--bit-depth", type=click.Choice(["16", "24", "32"]), default="24")
@click.option("--sr", type=int, default=48000, help="Sample rate.")
@click.pass_context
def bounce_disk(ctx, file_type, fmt, bit_depth, sr):
    """Bounce to disk."""
    _output(ctx, _get_bounce().bounce_to_disk(
        file_type=file_type, format=fmt,
        bit_depth=int(bit_depth), sample_rate=sr))


@bounce.command("clips")
@click.pass_context
def bounce_clips(ctx):
    """Export selected clips as files."""
    _output(ctx, _get_bounce().export_clips_as_files())


@bounce.command("commit")
@click.pass_context
def bounce_commit(ctx):
    """Commit / Print to Send (Ultimate only)."""
    _output(ctx, _get_bounce().print_to_send())


# ---------------------------------------------------------------------------
# Automation commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def automation(ctx):
    """Automation mode control."""
    pass


@automation.command("mode")
@click.argument("mode", type=click.Choice(["off", "read", "touch", "latch", "write", "trim"]))
@click.pass_context
def auto_mode(ctx, mode):
    """Set automation mode for selected track."""
    _output(ctx, _get_automation().set_mode(mode))


@automation.command("suspend")
@click.pass_context
def auto_suspend(ctx):
    """Suspend all automation."""
    _output(ctx, _get_automation().suspend_all())


# ---------------------------------------------------------------------------
# Plugin commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def plugin(ctx):
    """Plugin operations."""
    pass


@plugin.command("bypass-all")
@click.pass_context
def plugin_bypass_all(ctx):
    """Bypass all plugins on selected track."""
    _output(ctx, _get_plugins().bypass_all())


@plugin.command("audiosuite")
@click.argument("menu_path", nargs=-1)
@click.pass_context
def plugin_audiosuite(ctx, menu_path):
    """Open AudioSuite plugin by menu path (e.g., EQ '7-Band EQ III')."""
    _output(ctx, _get_plugins().audiosuite_process(list(menu_path)))


@plugin.command("render")
@click.pass_context
def plugin_render(ctx):
    """Click Render in open AudioSuite window."""
    _output(ctx, _get_plugins().audiosuite_render())


# ---------------------------------------------------------------------------
# I/O Routing commands
# ---------------------------------------------------------------------------

@cli.group("io")
@click.pass_context
def io_cmd(ctx):
    """I/O routing control."""
    pass


@io_cmd.command("setup")
@click.pass_context
def io_setup(ctx):
    """Open I/O Setup dialog."""
    _output(ctx, _get_io().open_io_setup())


@io_cmd.command("output")
@click.pass_context
def io_output(ctx):
    """Switch V-Pot to output assignment."""
    _output(ctx, _get_io().assign_output())


@io_cmd.command("input")
@click.pass_context
def io_input(ctx):
    """Switch V-Pot to input assignment."""
    _output(ctx, _get_io().assign_input())


@io_cmd.command("send")
@click.argument("letter")
@click.pass_context
def io_send(ctx, letter):
    """Switch V-Pot to send assignment (A-E)."""
    _output(ctx, _get_io().assign_send(letter))


# ---------------------------------------------------------------------------
# Meter commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def meter(ctx):
    """Meter level reading."""
    pass


@meter.command("levels")
@click.pass_context
def meter_levels(ctx):
    """Read current meter levels."""
    _output(ctx, _get_meter().get_levels())


@meter.command("peak")
@click.pass_context
def meter_peak(ctx):
    """Read peak meter levels."""
    _output(ctx, _get_meter().get_peak())


# ---------------------------------------------------------------------------
# Marker / Memory Location commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def marker(ctx):
    """Marker / Memory Location management."""
    pass


@marker.command("new")
@click.option("-n", "--name", default=None, help="Marker name.")
@click.pass_context
def marker_new(ctx, name):
    """Create marker at current position."""
    _output(ctx, _get_markers().create(name))


@marker.command("recall")
@click.argument("number", type=int)
@click.pass_context
def marker_recall(ctx, number):
    """Recall (jump to) marker by number."""
    _output(ctx, _get_markers().recall(number))


@marker.command("window")
@click.pass_context
def marker_window(ctx):
    """Show Memory Locations window."""
    _output(ctx, _get_markers().show_window())


# ---------------------------------------------------------------------------
# Group commands
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def group(ctx):
    """Edit/Mix group management."""
    pass


@group.command("new")
@click.option("-n", "--name", default=None, help="Group name.")
@click.pass_context
def group_new(ctx, name):
    """Create group from selected tracks."""
    _output(ctx, _get_groups().create(name))


@group.command("modify")
@click.pass_context
def group_modify(ctx):
    """Modify current group."""
    _output(ctx, _get_groups().modify())


@group.command("delete")
@click.pass_context
def group_delete(ctx):
    """Delete current group."""
    _output(ctx, _get_groups().delete())


@group.command("toggle")
@click.pass_context
def group_toggle(ctx):
    """Toggle group enable/disable."""
    _output(ctx, _get_groups().enable_toggle())


@group.command("suspend")
@click.pass_context
def group_suspend(ctx):
    """Suspend all groups."""
    _output(ctx, _get_groups().suspend_all())


# ---------------------------------------------------------------------------
# Navigate commands
# ---------------------------------------------------------------------------

@cli.group("nav")
@click.pass_context
def nav(ctx):
    """Navigation — zoom, windows, cursor."""
    pass


@nav.command("zoom-in")
@click.pass_context
def nav_zoom_in(ctx):
    """Zoom in."""
    _output(ctx, _get_navigate().zoom_in())


@nav.command("zoom-out")
@click.pass_context
def nav_zoom_out(ctx):
    """Zoom out."""
    _output(ctx, _get_navigate().zoom_out())


@nav.command("zoom-selection")
@click.pass_context
def nav_zoom_sel(ctx):
    """Zoom to selection."""
    _output(ctx, _get_navigate().zoom_to_selection())


@nav.command("zoom-fill")
@click.pass_context
def nav_zoom_fill(ctx):
    """Zoom to fill session."""
    _output(ctx, _get_navigate().zoom_to_fill())


@nav.command("mix-window")
@click.pass_context
def nav_mix(ctx):
    """Toggle Mix window."""
    _output(ctx, _get_navigate().toggle_mix_window())


@nav.command("edit-window")
@click.pass_context
def nav_edit(ctx):
    """Toggle Edit window."""
    _output(ctx, _get_navigate().toggle_edit_window())


@nav.command("scrub")
@click.pass_context
def nav_scrub(ctx):
    """Enter scrub mode."""
    _output(ctx, _get_navigate().scrub())


@nav.command("shuttle")
@click.pass_context
def nav_shuttle(ctx):
    """Enter shuttle mode."""
    _output(ctx, _get_navigate().shuttle())


# ---------------------------------------------------------------------------
# Import commands
# ---------------------------------------------------------------------------

@cli.group("import")
@click.pass_context
def import_cmd(ctx):
    """Import audio and session data."""
    pass


@import_cmd.command("audio")
@click.argument("path")
@click.pass_context
def import_audio_cmd(ctx, path):
    """Import audio file."""
    _output(ctx, _get_import().import_audio(path))


@import_cmd.command("session-data")
@click.argument("path")
@click.pass_context
def import_session_data(ctx, path):
    """Import session data from another Pro Tools session."""
    _output(ctx, _get_import().import_session_data(path))


# ---------------------------------------------------------------------------
# AAF build command
# ---------------------------------------------------------------------------

@cli.command("build-aaf")
@click.argument("template_json")
@click.option("-o", "--output", "output_path", default=None, help="Output AAF path.")
@click.pass_context
def build_aaf(ctx, template_json: str, output_path: str | None):
    """Build an AAF file from a JSON template file.

    TEMPLATE_JSON is a path to a JSON file describing the session structure.
    """
    import os
    template_json = os.path.expanduser(template_json)
    with open(template_json) as f:
        template = json.load(f)

    from cli_anything.protools.utils.aaf_engine import AAFBuilder
    if output_path is None:
        output_path = template_json.rsplit(".", 1)[0] + ".aaf"

    builder = AAFBuilder(
        name=template.get("name", "Untitled"),
        sample_rate=template.get("sample_rate", 48000),
        bit_depth=template.get("bit_depth", 24),
        timecode_fps=template.get("fps", 24.0),
    )
    builder.build_from_template(template, output_path)
    _output(ctx, {"status": "ok", "action": "build_aaf", "output": output_path})


# ---------------------------------------------------------------------------
# REPL command
# ---------------------------------------------------------------------------

@cli.command(hidden=True)
@click.pass_context
def repl(ctx):
    """Enter interactive REPL mode."""
    from cli_anything.protools.utils.repl_skin import ReplSkin

    skin = ReplSkin("protools", version="1.0.0")
    skin.print_banner()

    # Show connection status
    hui = _init_hui()
    aps = _init_applescript()
    if hui:
        skin.success("HUI/MIDI connected via IAC Driver")
    else:
        skin.warning("HUI/MIDI not available (IAC Driver not found or not configured)")
    if aps:
        skin.success("AppleScript bridge ready")
    else:
        skin.warning("AppleScript bridge not available")

    skin.info("Type 'help' for commands, 'quit' to exit")
    print()

    pt_session = skin.create_prompt_session()

    commands_help = {
        "transport play/stop/record/rtz/locate TC": "Transport control",
        "mix fader CH VAL / mute CH / solo CH": "Mixer control",
        "session new -n NAME / open PATH / save": "Session management",
        "track new -t TYPE -f FORMAT -n NAME": "Track management",
        "edit cut/copy/paste/separate/undo": "Editing operations",
        "bounce disk / clips": "Export and bounce",
        "automation mode MODE": "Automation control",
        "marker new -n NAME / recall NUM": "Marker management",
        "group new / toggle / suspend": "Group management",
        "nav zoom-in / mix-window / edit-window": "Navigation",
        "import audio PATH": "Import audio",
        "build-aaf TEMPLATE.json": "Build AAF from template",
        "info": "System information",
        "help": "Show this help",
        "quit / exit": "Exit REPL",
    }

    while True:
        try:
            line = skin.get_input(pt_session, project_name="Pro Tools")
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            if line.lower() == "help":
                skin.help(commands_help)
                continue

            # Parse and execute via Click
            args = line.split()
            try:
                cli.main(args=args, standalone_mode=False, obj=ctx.obj)
            except click.exceptions.UsageError as e:
                skin.error(str(e))
            except SystemExit:
                pass
            except Exception as e:
                skin.error(f"{type(e).__name__}: {e}")

        except (KeyboardInterrupt, EOFError):
            break

    # Cleanup
    if hui:
        hui.stop_ping_handler()
        hui._midi.close()

    skin.print_goodbye()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
