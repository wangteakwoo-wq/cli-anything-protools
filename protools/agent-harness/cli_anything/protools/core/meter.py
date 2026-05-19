"""Pro Tools meter reading via HUI feedback."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine


class MeterController:
    """Reads Pro Tools meter levels from HUI MIDI feedback."""

    def __init__(self, hui: HUIEngine | None = None):
        self._hui = hui

    def get_levels(self) -> dict:
        """Get current meter levels for visible channels.
        
        Returns levels as 0-12 integer values per channel (HUI meter resolution).
        """
        if self._hui is None:
            return {"status": "ok", "levels": [], "note": "HUI not connected"}
        
        self._hui.process_incoming()
        levels = list(self._hui.meter_levels)
        names = list(self._hui.channel_names)
        
        channels = []
        for i, (level, name) in enumerate(zip(levels, names)):
            channels.append({
                "strip": i + 1,
                "name": name,
                "level": level,
                "db_approx": self._level_to_db_approx(level),
                "clip": level >= 12,
            })
        
        return {"status": "ok", "channels": channels, "bank": self._hui.current_bank}

    def get_peak(self) -> dict:
        """Get peak levels across all visible channels."""
        result = self.get_levels()
        if result.get("channels"):
            peak_ch = max(result["channels"], key=lambda c: c["level"])
            result["peak"] = peak_ch
        return result

    @staticmethod
    def _level_to_db_approx(level: int) -> str:
        """Approximate dB value from HUI meter level (0-12 scale)."""
        db_map = {
            0: "-inf", 1: "-50dB", 2: "-40dB", 3: "-30dB",
            4: "-24dB", 5: "-18dB", 6: "-12dB", 7: "-9dB",
            8: "-6dB", 9: "-3dB", 10: "-1dB", 11: "0dB", 12: "CLIP",
        }
        return db_map.get(level, f"?({level})")
