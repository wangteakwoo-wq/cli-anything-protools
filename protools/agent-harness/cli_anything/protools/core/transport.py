"""Pro Tools transport control — play, stop, record, locate, loop."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class TransportController:
    """Controls Pro Tools transport via HUI protocol with AppleScript fallback."""

    def __init__(self, hui: HUIEngine | None = None, applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def play(self) -> dict:
        """Start playback."""
        if self._hui:
            self._hui.play()
        elif self._as:
            self._as.keystroke(" ")
        return {"status": "ok", "action": "play"}

    def stop(self) -> dict:
        """Stop playback/recording."""
        if self._hui:
            self._hui.stop()
        elif self._as:
            self._as.keystroke(" ")
        return {"status": "ok", "action": "stop"}

    def record(self) -> dict:
        """Enter record mode (press while playing to punch in)."""
        if self._hui:
            self._hui.record()
        elif self._as:
            self._as.key_code(111)  # F12
        return {"status": "ok", "action": "record"}

    def rewind(self) -> dict:
        """Rewind."""
        if self._hui:
            self._hui.rewind()
        return {"status": "ok", "action": "rewind"}

    def fast_forward(self) -> dict:
        """Fast forward."""
        if self._hui:
            self._hui.fast_forward()
        return {"status": "ok", "action": "fast_forward"}

    def return_to_zero(self) -> dict:
        """Return to session start."""
        if self._as:
            self._as.keystroke("\r")  # Return key
        elif self._hui:
            self._hui.stop()
            time.sleep(0.1)
            self._hui.stop()  # Double-stop = RTZ on many configurations
        return {"status": "ok", "action": "return_to_zero"}

    def go_to_end(self) -> dict:
        """Go to session end."""
        if self._as:
            self._as.keystroke("\r", modifiers=["option"])
        return {"status": "ok", "action": "go_to_end"}

    def locate(self, timecode: str) -> dict:
        """Locate to a specific timecode position (HH:MM:SS:FF format).

        Uses the numpad entry method: press numpad *, type digits, press numpad Enter.
        """
        if self._as:
            # Numpad * (key code 67) opens the locate field
            self._as.key_code(67)
            time.sleep(0.3)
            # Type each digit using numpad key codes
            numpad_keycodes = {
                "0": 82, "1": 83, "2": 84, "3": 85, "4": 86,
                "5": 87, "6": 88, "7": 89, "8": 91, "9": 92,
            }
            digits = timecode.replace(":", "").replace(";", "")
            for d in digits:
                kc = numpad_keycodes.get(d)
                if kc:
                    self._as.key_code(kc)
                    time.sleep(0.05)
            time.sleep(0.1)
            # Numpad Enter (key code 76) confirms
            self._as.key_code(76)
        return {"status": "ok", "action": "locate", "timecode": timecode}

    def loop_toggle(self) -> dict:
        """Toggle loop/cycle playback mode."""
        if self._hui:
            self._hui.cycle_toggle()
        elif self._as:
            self._as.keystroke("4", modifiers=["command"])
        return {"status": "ok", "action": "loop_toggle"}

    def online(self) -> dict:
        """Toggle online mode (for sync to external timecode)."""
        if self._hui:
            self._hui.online()
        return {"status": "ok", "action": "online"}

    def quick_punch(self) -> dict:
        """Toggle QuickPunch mode."""
        if self._hui:
            self._hui.quick_punch()
        return {"status": "ok", "action": "quick_punch"}

    def mark_in(self) -> dict:
        """Mark selection in point at current position."""
        if self._hui:
            self._hui.mark_in()
        return {"status": "ok", "action": "mark_in"}

    def mark_out(self) -> dict:
        """Mark selection out point at current position."""
        if self._hui:
            self._hui.mark_out()
        return {"status": "ok", "action": "mark_out"}

    def pre_roll_toggle(self) -> dict:
        """Toggle pre-roll."""
        if self._hui:
            self._hui._send_switch(0x0F, 0x01)
        return {"status": "ok", "action": "pre_roll_toggle"}

    def get_status(self) -> dict:
        """Get current transport status from HUI feedback."""
        result = {"status": "ok"}
        if self._hui:
            result["meter_levels"] = list(self._hui.meter_levels)
            result["channel_names"] = list(self._hui.channel_names)
            result["current_bank"] = self._hui.current_bank
        return result
