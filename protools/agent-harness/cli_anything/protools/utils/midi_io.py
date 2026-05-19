"""MIDI I/O wrapper around python-rtmidi for Pro Tools communication."""
from __future__ import annotations

import time
from typing import Self

import rtmidi


IAC_ENABLE_INSTRUCTIONS = (
    "No MIDI port matching the pattern was found. "
    "If you need IAC Driver, enable it in Audio MIDI Setup:\n"
    "  1. Open /Applications/Utilities/Audio MIDI Setup.app\n"
    "  2. Window → Show MIDI Studio\n"
    "  3. Double-click IAC Driver\n"
    "  4. Check 'Device is online'"
)


class MidiIO:
    """Manage MIDI input and output ports for Pro Tools communication."""

    def __init__(self) -> None:
        self._midi_in: rtmidi.MidiIn | None = None
        self._midi_out: rtmidi.MidiOut | None = None
        self._in_port: int | None = None
        self._out_port: int | None = None

    @classmethod
    def list_ports(cls) -> dict[str, list[str]]:
        """Enumerate available MIDI input and output ports."""
        midi_in = rtmidi.MidiIn()
        midi_out = rtmidi.MidiOut()
        result = {
            "input": list(midi_in.get_ports()),
            "output": list(midi_out.get_ports()),
        }
        del midi_in, midi_out
        return result

    def open(self, port_name_pattern: str = "IAC") -> None:
        """Open the first input and output ports whose names contain *port_name_pattern*."""
        self.close()

        self._midi_in = rtmidi.MidiIn()
        self._midi_out = rtmidi.MidiOut()

        in_port = self._find_port(self._midi_in.get_ports(), port_name_pattern)
        out_port = self._find_port(self._midi_out.get_ports(), port_name_pattern)

        if in_port is None or out_port is None:
            self.close()
            raise RuntimeError(
                f"No MIDI port matching '{port_name_pattern}'. {IAC_ENABLE_INSTRUCTIONS}"
            )

        self._midi_in.open_port(in_port)
        self._midi_out.open_port(out_port)
        self._in_port = in_port
        self._out_port = out_port

    def send(self, message: list[int] | bytes | bytearray) -> None:
        """Send a raw MIDI message (list of ints or bytes)."""
        if self._midi_out is None:
            raise RuntimeError("MIDI output port is not open. Call open() first.")
        self._midi_out.send_message(list(message))

    def send_cc(self, channel: int, cc: int, value: int) -> None:
        """Send a Control Change message."""
        self.send([0xB0 | (channel & 0x0F), cc & 0x7F, value & 0x7F])

    def send_note_on(self, channel: int, note: int, velocity: int) -> None:
        """Send a Note On message."""
        self.send([0x90 | (channel & 0x0F), note & 0x7F, velocity & 0x7F])

    def send_note_off(self, channel: int, note: int, velocity: int = 0) -> None:
        """Send a Note Off message."""
        self.send([0x80 | (channel & 0x0F), note & 0x7F, velocity & 0x7F])

    def send_pitchbend(self, channel: int, value: int) -> None:
        """Send a Pitch Bend message. Value 0-16383 (14-bit)."""
        lsb = value & 0x7F
        msb = (value >> 7) & 0x7F
        self.send([0xE0 | (channel & 0x0F), lsb, msb])

    def receive(self, timeout: float = 0.0) -> tuple[list[int], float] | None:
        """Poll for an incoming MIDI message (non-blocking by default).

        Returns a (message, delta_time) tuple, or None if no message is available.
        If *timeout* > 0, blocks up to that many seconds waiting for a message.
        """
        if self._midi_in is None:
            raise RuntimeError("MIDI input port is not open. Call open() first.")

        if timeout <= 0:
            msg = self._midi_in.get_message()
            return msg if msg else None

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = self._midi_in.get_message()
            if msg:
                return msg
            time.sleep(0.001)
        return None

    def close(self) -> None:
        """Close open MIDI ports and release resources."""
        if self._midi_in is not None:
            self._midi_in.close_port()
            del self._midi_in
            self._midi_in = None
        if self._midi_out is not None:
            self._midi_out.close_port()
            del self._midi_out
            self._midi_out = None
        self._in_port = None
        self._out_port = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _find_port(port_names: list[str], pattern: str) -> int | None:
        for idx, name in enumerate(port_names):
            if pattern in name:
                return idx
        return None
