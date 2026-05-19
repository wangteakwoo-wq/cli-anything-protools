"""HUI (Human User Interface) protocol engine for controlling Avid Pro Tools via MIDI."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator, Literal

if TYPE_CHECKING:
    from cli_anything.protools.utils.midi_io import MidiIO

logger = logging.getLogger(__name__)

ZONE_CHANNEL_STRIP_BASE = 0x00  # 0x00-0x07 per strip
ZONE_KEYBOARD = 0x08
ZONE_WINDOW = 0x09
ZONE_BANK = 0x0A
ZONE_ASSIGN1 = 0x0B
ZONE_ASSIGN2 = 0x0C
ZONE_CURSOR = 0x0D
ZONE_TRANSPORT = 0x0E
ZONE_TRANSPORT2 = 0x0F
ZONE_AUTOMATION = 0x10
ZONE_STATUS = 0x11
ZONE_EDIT = 0x12
ZONE_UTILITY = 0x13

PORT_FADER_TOUCH = 0x00
PORT_SELECT = 0x01
PORT_MUTE = 0x02
PORT_SOLO = 0x03
PORT_AUTO = 0x04
PORT_VSEL = 0x05
PORT_INSERT = 0x06
PORT_REC_RDY = 0x07

MODIFIER_MAP: dict[str, tuple[int, int]] = {
    "ctrl": (ZONE_KEYBOARD, 0x00),
    "cmd": (ZONE_KEYBOARD, 0x00),
    "shift": (ZONE_KEYBOARD, 0x01),
    "option": (ZONE_KEYBOARD, 0x03),
    "alt": (ZONE_KEYBOARD, 0x03),
    "cmd_right": (ZONE_KEYBOARD, 0x04),
    "ctrl_right": (ZONE_KEYBOARD, 0x04),
}

AUTOMATION_MODE_MAP: dict[str, int] = {
    "read": 0x00,
    "latch": 0x01,
    "touch": 0x02,
    "write": 0x03,
    "off": 0x04,
    "trim": 0x05,
}

SEND_LETTER_MAP: dict[str, int] = {
    "A": 0x07,
    "B": 0x06,
    "C": 0x05,
    "D": 0x04,
    "E": 0x03,
}

CC_ZONE_SELECT = 0x0F
CC_VPOT_BASE = 0x10  # CC 16-23
CC_VPOT_LED_BASE = 0x30  # CC 48-55 (feedback from PT)
CC_METER_BASE = 0x00

HUI_SYSEX_HEADER = bytes([0xF0, 0x00, 0x00, 0x66, 0x05, 0x00])
SCRIBBLE_STRIP_ID = 0x10
TIMECODE_DISPLAY_ID = 0x11

NUM_STRIPS = 8
FADER_MAX = 16383
PITCHBEND_CENTER = 0  # not used; HUI pitchbend is 0-16383 absolute


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class HUIEngine:
    """Controls Avid Pro Tools via the HUI (Mackie) MIDI protocol."""

    def __init__(self, midi: MidiIO) -> None:
        self._midi = midi
        self._lock = threading.Lock()

        self.fader_positions: list[float] = [0.0] * NUM_STRIPS
        self.meter_levels: list[int] = [0] * NUM_STRIPS
        self.channel_names: list[str] = ["    "] * NUM_STRIPS
        self.current_bank: int = 0

        self._ping_thread: threading.Thread | None = None
        self._ping_stop = threading.Event()

    # ── Low-level protocol ──────────────────────────────────────────

    def _send_switch(self, zone: int, port: int, press: bool = True) -> None:
        velocity = 0x7F if press else 0x00
        self._midi.send_cc(channel=0, cc=CC_ZONE_SELECT, value=zone)
        self._midi.send_note_on(channel=0, note=port, velocity=velocity)

    def _press_and_release(self, zone: int, port: int) -> None:
        self._send_switch(zone, port, press=True)
        self._send_switch(zone, port, press=False)

    # ── Transport ───────────────────────────────────────────────────

    def play(self) -> None:
        self._press_and_release(ZONE_TRANSPORT, 0x04)

    def stop(self) -> None:
        self._press_and_release(ZONE_TRANSPORT, 0x03)

    def record(self) -> None:
        self._press_and_release(ZONE_TRANSPORT, 0x05)

    def rewind(self) -> None:
        self._press_and_release(ZONE_TRANSPORT, 0x01)

    def fast_forward(self) -> None:
        self._press_and_release(ZONE_TRANSPORT, 0x02)

    def cycle_toggle(self) -> None:
        self._press_and_release(ZONE_TRANSPORT2, 0x05)

    def online(self) -> None:
        self._press_and_release(ZONE_TRANSPORT2, 0x04)

    def quick_punch(self) -> None:
        self._press_and_release(ZONE_TRANSPORT2, 0x06)

    # ── Faders ──────────────────────────────────────────────────────

    def set_fader(self, strip: int, value: float) -> None:
        self._validate_strip(strip)
        value = _clamp(value, 0.0, 1.0)
        pitch = int(value * FADER_MAX)
        self._midi.send_pitchbend(channel=strip, value=pitch)
        with self._lock:
            self.fader_positions[strip] = value

    def touch_fader(self, strip: int) -> None:
        self._validate_strip(strip)
        self._send_switch(ZONE_CHANNEL_STRIP_BASE + strip, PORT_FADER_TOUCH, press=True)

    def release_fader(self, strip: int) -> None:
        self._validate_strip(strip)
        self._send_switch(ZONE_CHANNEL_STRIP_BASE + strip, PORT_FADER_TOUCH, press=False)

    # ── Channel operations ──────────────────────────────────────────

    def select(self, strip: int) -> None:
        self._validate_strip(strip)
        self._press_and_release(ZONE_CHANNEL_STRIP_BASE + strip, PORT_SELECT)

    def mute(self, strip: int) -> None:
        self._validate_strip(strip)
        self._press_and_release(ZONE_CHANNEL_STRIP_BASE + strip, PORT_MUTE)

    def solo(self, strip: int) -> None:
        self._validate_strip(strip)
        self._press_and_release(ZONE_CHANNEL_STRIP_BASE + strip, PORT_SOLO)

    def rec_arm(self, strip: int) -> None:
        self._validate_strip(strip)
        self._press_and_release(ZONE_CHANNEL_STRIP_BASE + strip, PORT_REC_RDY)

    def bank_left(self) -> None:
        self._press_and_release(ZONE_BANK, 0x02)

    def bank_right(self) -> None:
        self._press_and_release(ZONE_BANK, 0x03)

    def channel_left(self) -> None:
        self._press_and_release(ZONE_BANK, 0x00)

    def channel_right(self) -> None:
        self._press_and_release(ZONE_BANK, 0x01)

    def navigate_to_channel(self, channel: int) -> int:
        """Navigate to a 1-based channel by banking, return the 0-based strip index.

        Updates ``current_bank`` to reflect the new bank position.
        """
        if channel < 1:
            raise ValueError(f"Channel must be >= 1, got {channel}")
        target_bank = (channel - 1) // 8
        diff = target_bank - self.current_bank
        if diff > 0:
            for _ in range(diff):
                self.bank_right()
        elif diff < 0:
            for _ in range(abs(diff)):
                self.bank_left()
        self.current_bank = target_bank
        return (channel - 1) % 8

    # ── V-Pot ───────────────────────────────────────────────────────

    def vpot_turn(self, strip: int, delta: int) -> None:
        """Turn V-Pot encoder. Positive delta = clockwise, negative = counter-clockwise."""
        self._validate_strip(strip)
        if delta == 0:
            return
        if delta > 0:
            value = min(delta, 63)
        else:
            value = 64 + min(abs(delta), 63)
        self._midi.send_cc(channel=0, cc=CC_VPOT_BASE + strip, value=value)

    def vpot_press(self, strip: int) -> None:
        self._validate_strip(strip)
        self._press_and_release(ZONE_CHANNEL_STRIP_BASE + strip, PORT_VSEL)

    # ── Automation ──────────────────────────────────────────────────

    def auto_mode(self, mode: Literal["read", "write", "touch", "latch", "off", "trim"]) -> None:
        port = AUTOMATION_MODE_MAP.get(mode)
        if port is None:
            raise ValueError(f"Unknown automation mode: {mode!r}. "
                             f"Valid modes: {list(AUTOMATION_MODE_MAP)}")
        self._press_and_release(ZONE_AUTOMATION, port)

    # ── Navigation / Cursor ─────────────────────────────────────────

    def cursor_up(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x04)

    def cursor_down(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x00)

    def cursor_left(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x01)

    def cursor_right(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x03)

    def zoom_toggle(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x02)

    def scrub(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x06)

    def shuttle(self) -> None:
        self._press_and_release(ZONE_CURSOR, 0x07)

    # ── Edit functions ──────────────────────────────────────────────

    def cut(self) -> None:
        self._press_and_release(ZONE_EDIT, 0x01)

    def copy(self) -> None:
        self._press_and_release(ZONE_EDIT, 0x03)

    def paste(self) -> None:
        self._press_and_release(ZONE_EDIT, 0x04)

    def delete(self) -> None:
        self._press_and_release(ZONE_EDIT, 0x02)

    def separate(self) -> None:
        self._press_and_release(ZONE_EDIT, 0x05)

    def undo(self) -> None:
        self._press_and_release(ZONE_UTILITY, 0x01)

    def save(self) -> None:
        self._press_and_release(ZONE_UTILITY, 0x00)

    # ── Modifiers ───────────────────────────────────────────────────

    def _press_modifier(self, name: str) -> None:
        zone, port = self._resolve_modifier(name)
        self._send_switch(zone, port, press=True)

    def _release_modifier(self, name: str) -> None:
        zone, port = self._resolve_modifier(name)
        self._send_switch(zone, port, press=False)

    @contextmanager
    def modifier(self, name: str) -> Iterator[None]:
        """Hold a modifier key for the duration of the context block."""
        self._press_modifier(name)
        try:
            yield
        finally:
            self._release_modifier(name)

    # ── Window ──────────────────────────────────────────────────────

    def mix_window(self) -> None:
        self._press_and_release(ZONE_UTILITY, 0x06)

    def edit_window(self) -> None:
        self._press_and_release(ZONE_UTILITY, 0x07)

    # ── Assign ──────────────────────────────────────────────────────

    def assign_pan(self) -> None:
        self._press_and_release(ZONE_ASSIGN1, 0x02)

    def assign_send(self, letter: Literal["A", "B", "C", "D", "E"]) -> None:
        port = SEND_LETTER_MAP.get(letter)
        if port is None:
            raise ValueError(f"Invalid send letter: {letter!r}. Must be A-E.")
        self._press_and_release(ZONE_ASSIGN1, port)

    def assign_input(self) -> None:
        self._press_and_release(ZONE_ASSIGN1, 0x01)

    def assign_output(self) -> None:
        self._press_and_release(ZONE_ASSIGN1, 0x00)

    # ── Status / Group ──────────────────────────────────────────────

    def group_create(self) -> None:
        self._press_and_release(ZONE_STATUS, 0x02)

    def group_suspend(self) -> None:
        self._press_and_release(ZONE_STATUS, 0x04)

    # ── Utility marks ──────────────────────────────────────────────

    def mark_in(self) -> None:
        self._press_and_release(ZONE_TRANSPORT2, 0x02)

    def mark_out(self) -> None:
        self._press_and_release(ZONE_TRANSPORT2, 0x03)

    # ── Ping / Keep-alive ───────────────────────────────────────────

    def handle_ping(self, message: tuple[int, ...] | list[int] | bytes) -> None:
        """Respond to a Pro Tools keep-alive ping (CC#0 val 0 on ch 0)."""
        logger.debug("Ping received (%d bytes), responding", len(message))
        self._midi.send_cc(channel=0, cc=0x00, value=0x00)

    def start_ping_handler(self) -> None:
        if self._ping_thread is not None and self._ping_thread.is_alive():
            return
        self._ping_stop.clear()
        self._ping_thread = threading.Thread(
            target=self._ping_loop, daemon=True, name="hui-ping"
        )
        self._ping_thread.start()
        logger.info("HUI ping handler started")

    def stop_ping_handler(self) -> None:
        self._ping_stop.set()
        if self._ping_thread is not None:
            self._ping_thread.join(timeout=5.0)
            self._ping_thread = None
        logger.info("HUI ping handler stopped")

    def _ping_loop(self) -> None:
        while not self._ping_stop.is_set():
            try:
                result = self._midi.receive(timeout=0.25)
                if result is None:
                    continue
                # python-rtmidi returns (message_list, delta_time)
                msg, _dt = result
                if self._is_ping(msg):
                    self.handle_ping(msg)
                else:
                    self._dispatch_incoming(msg)
            except (OSError, ValueError):
                logger.exception("Error in ping handler loop")

    # ── Incoming message processing ─────────────────────────────────

    def process_incoming(self) -> None:
        """Poll and dispatch all pending incoming MIDI messages from Pro Tools."""
        while True:
            result = self._midi.receive(timeout=0.0)
            if result is None:
                break
            msg, _dt = result
            if self._is_ping(msg):
                self.handle_ping(msg)
            else:
                self._dispatch_incoming(msg)

    def _dispatch_incoming(self, msg: tuple[int, ...] | list[int] | bytes) -> None:
        if not msg:
            return

        status = msg[0]
        msg_type = status & 0xF0
        channel = status & 0x0F

        if msg_type == 0xB0 and channel == 0 and len(msg) >= 3:
            self._handle_cc(msg[1], msg[2])
        elif msg_type == 0xE0 and len(msg) >= 3:
            self._handle_pitchbend(channel, msg[1], msg[2])
        elif status == 0xF0:
            self._handle_sysex(msg)

    def _handle_cc(self, cc: int, value: int) -> None:
        if CC_METER_BASE <= cc <= CC_METER_BASE + 7:
            strip = cc - CC_METER_BASE
            level = value & 0x0F
            with self._lock:
                self.meter_levels[strip] = level
        elif CC_VPOT_LED_BASE <= cc <= CC_VPOT_LED_BASE + 7:
            logger.debug("V-Pot LED update: strip=%d value=0x%02X", cc - CC_VPOT_LED_BASE, value)

    def _handle_pitchbend(self, channel: int, lsb: int, msb: int) -> None:
        if 0 <= channel < NUM_STRIPS:
            raw = (msb << 7) | lsb
            position = raw / FADER_MAX if FADER_MAX else 0.0
            with self._lock:
                self.fader_positions[channel] = position

    def _handle_sysex(self, msg: tuple[int, ...] | list[int] | bytes) -> None:
        data = bytes(msg)
        if not data.startswith(HUI_SYSEX_HEADER):
            return

        payload = data[len(HUI_SYSEX_HEADER):]
        if not payload:
            return

        msg_id = payload[0]
        if msg_id == SCRIBBLE_STRIP_ID and len(payload) >= 6:
            zone = payload[1]
            if 0 <= zone < NUM_STRIPS:
                text_bytes = payload[2:6]
                text = bytes(text_bytes).decode("ascii", errors="replace")
                with self._lock:
                    self.channel_names[zone] = text
        elif msg_id == TIMECODE_DISPLAY_ID:
            logger.debug("Timecode display update: %s", payload[1:].hex())

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _is_ping(msg: tuple[int, ...] | list[int] | bytes) -> bool:
        if len(msg) < 3:
            return False
        return (msg[0] & 0xF0) == 0xB0 and (msg[0] & 0x0F) == 0 and msg[1] == 0x00 and msg[2] == 0x00

    @staticmethod
    def _validate_strip(strip: int) -> None:
        if not 0 <= strip < NUM_STRIPS:
            raise ValueError(f"Strip must be 0-{NUM_STRIPS - 1}, got {strip}")

    @staticmethod
    def _resolve_modifier(name: str) -> tuple[int, int]:
        key = name.lower()
        result = MODIFIER_MAP.get(key)
        if result is None:
            raise ValueError(f"Unknown modifier: {name!r}. "
                             f"Valid modifiers: {list(MODIFIER_MAP)}")
        return result
