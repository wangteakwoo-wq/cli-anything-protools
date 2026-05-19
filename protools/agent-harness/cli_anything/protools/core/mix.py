"""Pro Tools mixing control — faders, pans, mute, solo, sends, banks."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine


def _require_hui(hui: HUIEngine | None) -> HUIEngine:
    if hui is None:
        raise RuntimeError(
            "Mix operations require HUI/MIDI connection.\n"
            "Ensure IAC Driver is enabled and Pro Tools is configured with HUI controller."
        )
    return hui


class MixController:
    """Controls Pro Tools mixer via HUI protocol."""

    def __init__(self, hui: HUIEngine | None = None):
        self._hui = hui

    def set_fader(self, channel: int, value: float) -> dict:
        """Set a channel fader level.

        Args:
            channel: Channel number (1-based, will auto-bank if > 8).
            value: Fader level 0.0 (−∞) to 1.0 (unity/+6dB).
                   Common values: 0.0=-inf, 0.707≈-3dB, 0.775≈0dB, 1.0=+6dB
        """
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        value = max(0.0, min(1.0, value))
        hui.set_fader(strip, value)
        return {"status": "ok", "action": "set_fader", "channel": channel, "value": value}

    def set_fader_db(self, channel: int, db: float) -> dict:
        """Set fader by dB value. Range: -inf to +6.

        Approximate mapping (Pro Tools fader is not perfectly linear):
            +6dB  = 1.0
             0dB  = 0.775 (about 12700 / 16383)
            -6dB  = 0.6
           -12dB  = 0.45
           -18dB  = 0.33
           -30dB  = 0.2
           -50dB  = 0.1
           -inf   = 0.0
        """
        if db <= -90:
            value = 0.0
        elif db >= 6:
            value = 1.0
        else:
            # Attempt a reasonable approximation of the Pro Tools fader curve
            # This is a piecewise approximation, not exact
            normalized_db = (db + 90) / 96  # 0 to 1 range for -90 to +6
            value = normalized_db ** 0.5  # Square root curve approximation
            value = max(0.0, min(1.0, value))
        return self.set_fader(channel, value)

    def set_pan(self, channel: int, value: float) -> dict:
        """Set channel pan position.

        Args:
            channel: Channel number (1-based).
            value: Pan position -1.0 (full left) to 1.0 (full right). 0.0 = center.
        """
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        hui.assign_pan()
        time.sleep(0.05)
        # Reset to full left first (63 counter-clockwise steps), then set target
        hui.vpot_turn(strip, -63)
        time.sleep(0.1)
        # Map -1.0..1.0 to 0..126 steps from full left
        steps = int((value + 1.0) / 2.0 * 126)
        steps = max(0, min(126, steps))
        if steps > 0:
            hui.vpot_turn(strip, steps)
        return {"status": "ok", "action": "set_pan", "channel": channel, "value": value}

    def mute(self, channel: int) -> dict:
        """Toggle mute on a channel."""
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        hui.mute(strip)
        return {"status": "ok", "action": "mute", "channel": channel}

    def solo(self, channel: int) -> dict:
        """Toggle solo on a channel."""
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        hui.solo(strip)
        return {"status": "ok", "action": "solo", "channel": channel}

    def select(self, channel: int) -> dict:
        """Select a channel strip."""
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        hui.select(strip)
        return {"status": "ok", "action": "select", "channel": channel}

    def rec_arm(self, channel: int) -> dict:
        """Toggle record arm on a channel."""
        hui = _require_hui(self._hui)
        strip = self._resolve_strip(channel)
        hui.rec_arm(strip)
        return {"status": "ok", "action": "rec_arm", "channel": channel}

    def bank_left(self) -> dict:
        """Bank left (previous 8 channels)."""
        hui = _require_hui(self._hui)
        hui.bank_left()
        hui.current_bank = max(0, hui.current_bank - 1)
        return {"status": "ok", "action": "bank_left"}

    def bank_right(self) -> dict:
        """Bank right (next 8 channels)."""
        hui = _require_hui(self._hui)
        hui.bank_right()
        hui.current_bank += 1
        return {"status": "ok", "action": "bank_right"}

    def channel_left(self) -> dict:
        """Scroll one channel left."""
        hui = _require_hui(self._hui)
        hui.channel_left()
        return {"status": "ok", "action": "channel_left"}

    def channel_right(self) -> dict:
        """Scroll one channel right."""
        hui = _require_hui(self._hui)
        hui.channel_right()
        return {"status": "ok", "action": "channel_right"}

    def go_to_channel(self, channel: int) -> dict:
        """Navigate to a specific channel by banking.

        Args:
            channel: Target channel number (1-based).
        """
        hui = _require_hui(self._hui)
        strip = hui.navigate_to_channel(channel)
        return {"status": "ok", "action": "go_to_channel", "channel": channel, "bank": hui.current_bank}

    def assign_send(self, letter: str) -> dict:
        """Switch V-Pot assignment to a send (A-E)."""
        hui = _require_hui(self._hui)
        hui.assign_send(letter.upper())
        return {"status": "ok", "action": "assign_send", "send": letter.upper()}

    def assign_pan(self) -> dict:
        """Switch V-Pot assignment to pan."""
        hui = _require_hui(self._hui)
        hui.assign_pan()
        return {"status": "ok", "action": "assign_pan"}

    def assign_input(self) -> dict:
        """Switch V-Pot assignment to input."""
        hui = _require_hui(self._hui)
        hui.assign_input()
        return {"status": "ok", "action": "assign_input"}

    def assign_output(self) -> dict:
        """Switch V-Pot assignment to output."""
        hui = _require_hui(self._hui)
        hui.assign_output()
        return {"status": "ok", "action": "assign_output"}

    def get_meters(self) -> dict:
        """Get current meter levels from HUI feedback."""
        hui = _require_hui(self._hui)
        hui.process_incoming()
        return {
            "status": "ok",
            "meters": list(hui.meter_levels),
            "channel_names": list(hui.channel_names),
            "fader_positions": list(hui.fader_positions),
            "bank": hui.current_bank,
        }

    def _resolve_strip(self, channel: int) -> int:
        """Convert 1-based channel number to 0-based strip index, auto-banking if needed."""
        if channel < 1:
            raise ValueError(f"Channel must be >= 1, got {channel}")
        if self._hui:
            return self._hui.navigate_to_channel(channel)
        return (channel - 1) % 8
