"""AAF Engine — Programmatic AAF builder for Pro Tools session import.

Uses pyaaf2 to construct Advanced Authoring Format files that Pro Tools
can import directly, enabling offline session building without Pro Tools
running.

Usage:
    from cli_anything.protools.utils.aaf_engine import AAFBuilder

    builder = AAFBuilder("My Session", sample_rate=48000)
    builder.add_track("DX 1")
    builder.place_clip(0, "/path/to/audio.wav", start_time=0.0)
    builder.add_marker("Scene Start", 0.0)
    builder.build("output.aaf")
"""

from __future__ import annotations

import logging
import math
import os
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import aaf2
    from aaf2.rational import AAFRational
except ImportError:
    aaf2 = None  # type: ignore[assignment]
    AAFRational = None  # type: ignore[assignment,misc]

_logger = logging.getLogger(__name__)


@dataclass
class _TrackDef:
    name: str
    track_type: str  # "audio", "aux", "master"
    format: str  # "mono", "stereo", "5.1"
    index: int = 0


@dataclass
class _ClipPlacement:
    track_index: int
    audio_file: str | None
    start_time: float  # seconds
    duration: float | None  # seconds; None => full file
    clip_name: str | None = None
    is_silence: bool = False


@dataclass
class _Marker:
    name: str
    time: float  # seconds
    color: str | None = None


_CHANNEL_COUNTS = {
    "mono": 1,
    "stereo": 2,
    "lcr": 3,
    "quad": 4,
    "5.0": 5,
    "5.1": 6,
    "7.1": 8,
}


def _get_wav_duration(filepath: str) -> float:
    """Read the duration of a WAV file in seconds."""
    with wave.open(filepath, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            raise ValueError(f"WAV file has 0 sample rate: {filepath}")
        return frames / rate


def _get_wav_params(filepath: str) -> dict[str, int]:
    """Read WAV parameters needed for AAF essence descriptors."""
    with wave.open(filepath, "rb") as wf:
        return {
            "channels": wf.getnchannels(),
            "sample_rate": wf.getframerate(),
            "bit_depth": wf.getsampwidth() * 8,
            "num_frames": wf.getnframes(),
        }


class AAFBuilder:
    """Builds AAF files for Pro Tools import using pyaaf2.

    The builder accumulates track definitions, clip placements, and markers,
    then serialises everything into a valid AAF when ``build()`` is called.
    """

    def __init__(
        self,
        name: str = "Untitled",
        sample_rate: int = 48000,
        bit_depth: int = 24,
        timecode_fps: float = 24.0,
    ) -> None:
        self.name = name
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.timecode_fps = timecode_fps

        self.tracks: list[_TrackDef] = []
        self.clips: list[_ClipPlacement] = []
        self.markers: list[_Marker] = []

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def add_track(
        self,
        name: str,
        track_type: str = "audio",
        format: str = "mono",
    ) -> int:
        """Add a single track definition and return its index."""
        track_type = track_type.lower()
        if track_type not in ("audio", "aux", "master"):
            raise ValueError(
                f"Invalid track_type '{track_type}'; "
                "expected 'audio', 'aux', or 'master'"
            )
        fmt = format.lower()
        if fmt not in _CHANNEL_COUNTS:
            raise ValueError(
                f"Unknown format '{format}'; "
                f"expected one of {list(_CHANNEL_COUNTS)}"
            )
        idx = len(self.tracks)
        self.tracks.append(_TrackDef(name=name, track_type=track_type, format=fmt, index=idx))
        return idx

    def add_tracks(
        self,
        names: list[str],
        track_type: str = "audio",
        format: str = "mono",
    ) -> list[int]:
        """Add multiple tracks with the same type/format. Returns indices."""
        return [self.add_track(n, track_type, format) for n in names]

    # ------------------------------------------------------------------
    # Clip / media management
    # ------------------------------------------------------------------

    def place_clip(
        self,
        track_index: int,
        audio_file: str,
        start_time: float,
        duration: float | None = None,
        clip_name: str | None = None,
    ) -> None:
        """Place an audio file reference on a track at *start_time* (seconds).

        If *duration* is ``None`` the full file duration is used (requires
        the file to be a readable WAV at build time).
        """
        if track_index < 0 or track_index >= len(self.tracks):
            raise IndexError(
                f"track_index {track_index} out of range "
                f"(0..{len(self.tracks) - 1})"
            )
        self.clips.append(
            _ClipPlacement(
                track_index=track_index,
                audio_file=audio_file,
                start_time=start_time,
                duration=duration,
                clip_name=clip_name,
            )
        )

    def place_silence(
        self,
        track_index: int,
        start_time: float,
        duration: float,
    ) -> None:
        """Place an explicit silence gap on a track."""
        if track_index < 0 or track_index >= len(self.tracks):
            raise IndexError(
                f"track_index {track_index} out of range "
                f"(0..{len(self.tracks) - 1})"
            )
        self.clips.append(
            _ClipPlacement(
                track_index=track_index,
                audio_file=None,
                start_time=start_time,
                duration=duration,
                is_silence=True,
            )
        )

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------

    def add_marker(
        self,
        name: str,
        time: float,
        color: str | None = None,
    ) -> None:
        """Add a named marker at the given time (seconds)."""
        self.markers.append(_Marker(name=name, time=time, color=color))

    # ------------------------------------------------------------------
    # Build / export
    # ------------------------------------------------------------------

    def build(self, output_path: str) -> None:
        """Serialise the accumulated session into an AAF file on disk.

        Raises ``RuntimeError`` if pyaaf2 is not installed.
        """
        if aaf2 is None:
            raise RuntimeError(
                "pyaaf2 is required to build AAF files. "
                "Install it with: pip install pyaaf2"
            )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        edit_rate = AAFRational(self.sample_rate, 1)

        with aaf2.open(str(output), "w") as f:
            comp_mob = f.create.CompositionMob(self.name)
            comp_mob.usage = "Usage_TopLevel"

            # --- Timecode track ------------------------------------------
            tc_slot = comp_mob.create_timeline_slot(
                edit_rate=AAFRational(int(self.timecode_fps), 1),
            )
            tc = f.create.Timecode(
                fps=int(self.timecode_fps),
                drop=False,
            )
            tc.start = 0
            tc.length = self.seconds_to_edit_units(86400)  # 24h max
            tc_slot.segment = tc
            tc_slot.slot_id = 1
            tc_slot.name = "TC 1"
            # TODO: Non-integer frame rates (23.976, 29.97) need drop-frame
            # handling and rational edit rates for full correctness.

            slot_id = 2  # start after TC slot

            # Group clips by track for sequencing
            clips_by_track: dict[int, list[_ClipPlacement]] = {}
            for clip in self.clips:
                clips_by_track.setdefault(clip.track_index, []).append(clip)

            master_mobs: dict[str, Any] = {}

            for track_def in self.tracks:
                channel_count = _CHANNEL_COUNTS.get(track_def.format, 1)

                for ch in range(channel_count):
                    timeline_slot = comp_mob.create_timeline_slot(
                        edit_rate=edit_rate,
                    )
                    if channel_count == 1:
                        timeline_slot.name = track_def.name
                    else:
                        timeline_slot.name = f"{track_def.name}_{ch + 1}"
                    timeline_slot.slot_id = slot_id
                    slot_id += 1

                    sequence = f.create.Sequence(media_kind="sound")

                    track_clips = clips_by_track.get(track_def.index, [])
                    track_clips.sort(key=lambda c: c.start_time)

                    cursor = 0  # current position in edit units

                    for clip in track_clips:
                        clip_start_eu = self.seconds_to_edit_units(clip.start_time)

                        # Fill gap before this clip
                        if clip_start_eu > cursor:
                            gap_len = clip_start_eu - cursor
                            filler = f.create.Filler(media_kind="sound", length=gap_len)
                            sequence.components.append(filler)
                            cursor = clip_start_eu

                        if clip.is_silence:
                            dur_eu = self.seconds_to_edit_units(clip.duration or 0.0)
                            if dur_eu > 0:
                                filler = f.create.Filler(media_kind="sound", length=dur_eu)
                                sequence.components.append(filler)
                                cursor += dur_eu
                            continue

                        # Resolve duration
                        audio_path = clip.audio_file or ""
                        if clip.duration is not None:
                            dur_seconds = clip.duration
                        elif os.path.isfile(audio_path):
                            try:
                                dur_seconds = _get_wav_duration(audio_path)
                            except Exception as exc:
                                _logger.warning("Could not read WAV duration for %s: %s", audio_path, exc)
                                dur_seconds = 1.0
                        else:
                            dur_seconds = 1.0

                        dur_eu = self.seconds_to_edit_units(dur_seconds)
                        if dur_eu <= 0:
                            continue

                        # Create or reuse MasterMob for this audio file
                        master_mob = self._ensure_master_mob(
                            f, master_mobs, audio_path, clip.clip_name, edit_rate
                        )

                        # Only place on first channel of the source for now
                        # TODO: Multi-channel clip placement — interleaved
                        # files should fan out across channels properly.
                        source_slot_id = 1
                        if ch < len(master_mob.slots):
                            source_slot_id = master_mob.slots[ch].slot_id

                        source_clip = f.create.SourceClip(
                            media_kind="sound",
                            length=dur_eu,
                        )
                        source_clip.mob = master_mob
                        source_clip.slot_id = source_slot_id
                        source_clip.start = 0

                        sequence.components.append(source_clip)
                        cursor += dur_eu

                    if not sequence.components:
                        filler = f.create.Filler(media_kind="sound", length=0)
                        sequence.components.append(filler)

                    timeline_slot.segment = sequence

            # --- Markers --------------------------------------------------
            # TODO: Pro Tools markers in AAF can be represented as
            # CommentMarker objects in a separate event track. The exact
            # schema depends on the AAF version and Pro Tools expectations.
            # For now we store markers as DescriptiveMarker objects in an
            # EventMobSlot on the CompositionMob.
            if self.markers:
                try:
                    event_slot = comp_mob.create_event_slot(
                        edit_rate=edit_rate,
                    )
                    event_slot.slot_id = slot_id
                    slot_id += 1

                    marker_seq = f.create.Sequence(media_kind="descriptive")
                    for marker in sorted(self.markers, key=lambda m: m.time):
                        position_eu = self.seconds_to_edit_units(marker.time)
                        dm = f.create.DescriptiveMarker()
                        dm.position = position_eu
                        dm.length = 0
                        dm["CommentMarkerUser"] = marker.name
                        # TODO: Marker colour mapping — Pro Tools uses a
                        # specific colour palette index that needs mapping
                        # from human-readable names.
                        marker_seq.components.append(dm)

                    event_slot.segment = marker_seq
                except Exception as exc:
                    # Marker creation is non-critical; degrade gracefully
                    _logger.warning("Marker creation failed: %s", exc)

            f.content.mobs.append(comp_mob)
            # TODO: Embedded essence — currently all audio files are
            # external references. Supporting embedded essence would
            # require reading file data into EssenceData objects.

    def _ensure_master_mob(
        self,
        f: Any,
        cache: dict[str, Any],
        audio_path: str,
        clip_name: str | None,
        edit_rate: Any,
    ) -> Any:
        """Return (and cache) a MasterMob + SourceMob pair for *audio_path*."""
        cache_key = audio_path or f"_clip_{clip_name}"
        if cache_key in cache:
            return cache[cache_key]

        display_name = clip_name or Path(audio_path).stem if audio_path else "Unknown"

        master_mob = f.create.MasterMob(display_name)
        source_mob = f.create.SourceMob()

        # Essence descriptor
        if os.path.isfile(audio_path):
            try:
                params = _get_wav_params(audio_path)
            except Exception as exc:
                _logger.warning("Could not read WAV params for %s: %s", audio_path, exc)
                params = {
                    "channels": 1,
                    "sample_rate": self.sample_rate,
                    "bit_depth": self.bit_depth,
                    "num_frames": self.sample_rate,
                }
        else:
            params = {
                "channels": 1,
                "sample_rate": self.sample_rate,
                "bit_depth": self.bit_depth,
                "num_frames": self.sample_rate,
            }

        desc = f.create.PCMDescriptor()
        desc["AverageBPS"] = (
            params["sample_rate"] * params["channels"] * (params["bit_depth"] // 8)
        )
        desc["BlockAlign"] = params["channels"] * (params["bit_depth"] // 8)
        desc["QuantizationBits"] = params["bit_depth"]
        desc["AudioSamplingRate"] = AAFRational(params["sample_rate"], 1)
        desc["Channels"] = params["channels"]
        desc["SampleRate"] = AAFRational(params["sample_rate"], 1)
        desc["Length"] = params["num_frames"]
        # TODO: Set ContainerFormat and CodecID for full compatibility
        # with different Pro Tools import scenarios.

        source_mob.descriptor = desc

        # Create matching slots on source and master mobs
        for ch in range(params["channels"]):
            s_slot = source_mob.create_timeline_slot(edit_rate=edit_rate)
            s_slot.slot_id = ch + 1

            source_clip_ref = f.create.SourceClip(media_kind="sound", length=params["num_frames"])
            s_slot.segment = source_clip_ref

            m_slot = master_mob.create_timeline_slot(edit_rate=edit_rate)
            m_slot.slot_id = ch + 1

            master_ref = f.create.SourceClip(media_kind="sound", length=params["num_frames"])
            master_ref.mob = source_mob
            master_ref.slot_id = ch + 1
            master_ref.start = 0
            m_slot.segment = master_ref

        # Set network locator so Pro Tools can find the original file
        if audio_path and os.path.isfile(audio_path):
            loc = f.create.NetworkLocator()
            loc["URLString"] = Path(audio_path).resolve().as_uri()
            desc["Locator"] = [loc]

        f.content.mobs.append(source_mob)
        f.content.mobs.append(master_mob)

        cache[cache_key] = master_mob
        return master_mob

    def build_from_template(self, template: dict, output_path: str) -> None:
        """Build an AAF from a declarative template dictionary.

        Template schema::

            {
                "name": str,
                "sample_rate": int,
                "bit_depth": int,
                "fps": float,
                "tracks": [{"name": str, "type": str, "format": str}, ...],
                "clips": [{"track": int, "file": str, "start": float,
                           "duration": float | None, "clip_name": str | None}, ...],
                "markers": [{"name": str, "time": float, "color": str | None}, ...],
            }
        """
        self.name = template.get("name", self.name)
        self.sample_rate = template.get("sample_rate", self.sample_rate)
        self.bit_depth = template.get("bit_depth", self.bit_depth)
        self.timecode_fps = template.get("fps", self.timecode_fps)

        self.tracks.clear()
        self.clips.clear()
        self.markers.clear()

        for t in template.get("tracks", []):
            self.add_track(
                name=t["name"],
                track_type=t.get("type", "audio"),
                format=t.get("format", "mono"),
            )

        for c in template.get("clips", []):
            self.place_clip(
                track_index=c["track"],
                audio_file=c["file"],
                start_time=c["start"],
                duration=c.get("duration"),
                clip_name=c.get("clip_name"),
            )

        for m in template.get("markers", []):
            self.add_marker(
                name=m["name"],
                time=m["time"],
                color=m.get("color"),
            )

        self.build(output_path)

    # ------------------------------------------------------------------
    # Utility conversions
    # ------------------------------------------------------------------

    def seconds_to_edit_units(self, seconds: float) -> int:
        """Convert a time in seconds to AAF edit units (samples)."""
        return int(round(seconds * self.sample_rate))

    def timecode_to_seconds(
        self,
        timecode: str,
        fps: float | None = None,
    ) -> float:
        """Convert ``"HH:MM:SS:FF"`` timecode to seconds.

        Uses ``self.timecode_fps`` when *fps* is not supplied.
        """
        fps = fps or self.timecode_fps
        parts = timecode.strip().split(":")
        if len(parts) != 4:
            raise ValueError(
                f"Expected timecode format HH:MM:SS:FF, got '{timecode}'"
            )
        try:
            hours, minutes, secs, frames = (int(p) for p in parts)
        except ValueError as exc:
            raise ValueError(
                f"Non-integer component in timecode '{timecode}'"
            ) from exc

        if not (0 <= minutes < 60 and 0 <= secs < 60):
            raise ValueError(f"Out-of-range minutes/seconds in '{timecode}'")
        if frames < 0 or frames >= math.ceil(fps):
            raise ValueError(
                f"Frame value {frames} out of range for {fps} fps"
            )
        total_seconds = hours * 3600.0 + minutes * 60.0 + secs + frames / fps
        return total_seconds

    def seconds_to_timecode(
        self,
        seconds: float,
        fps: float | None = None,
    ) -> str:
        """Convert seconds to ``"HH:MM:SS:FF"`` timecode string.

        Uses ``self.timecode_fps`` when *fps* is not supplied.
        """
        fps = fps or self.timecode_fps
        if seconds < 0:
            raise ValueError("Cannot convert negative seconds to timecode")

        total_frames = int(round(seconds * fps))
        frames_per_second = int(math.ceil(fps))

        ff = total_frames % frames_per_second
        remaining = total_frames // frames_per_second
        ss = remaining % 60
        remaining //= 60
        mm = remaining % 60
        hh = remaining // 60

        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
