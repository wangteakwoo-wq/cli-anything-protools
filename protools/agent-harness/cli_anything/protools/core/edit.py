"""Pro Tools editing operations — cut, copy, paste, separate, fades, nudge, consolidate."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli_anything.protools.utils.hui_engine import HUIEngine
    from cli_anything.protools.utils.applescript_bridge import ProToolsAppleScript


class EditController:
    """Controls Pro Tools editing via HUI and AppleScript keyboard shortcuts."""

    def __init__(self, hui: HUIEngine | None = None,
                 applescript: ProToolsAppleScript | None = None):
        self._hui = hui
        self._as = applescript

    def _require_as(self) -> ProToolsAppleScript:
        if self._as is None:
            raise RuntimeError("Edit operations require AppleScript bridge.")
        return self._as

    def cut(self) -> dict:
        """Cut selection to clipboard."""
        if self._hui:
            self._hui.cut()
        else:
            self._require_as().keystroke("x", modifiers=["command"])
        return {"status": "ok", "action": "cut"}

    def copy(self) -> dict:
        """Copy selection to clipboard."""
        if self._hui:
            self._hui.copy()
        else:
            self._require_as().keystroke("c", modifiers=["command"])
        return {"status": "ok", "action": "copy"}

    def paste(self) -> dict:
        """Paste from clipboard at current position."""
        if self._hui:
            self._hui.paste()
        else:
            self._require_as().keystroke("v", modifiers=["command"])
        return {"status": "ok", "action": "paste"}

    def delete(self) -> dict:
        """Delete selection (remove without adding to clipboard)."""
        if self._hui:
            self._hui.delete()
        else:
            self._require_as().key_code(51)  # Delete key
        return {"status": "ok", "action": "delete"}

    def separate(self) -> dict:
        """Separate (split) clip at selection or insertion point. Key: B"""
        if self._hui:
            self._hui.separate()
        else:
            self._require_as().keystroke("b")
        return {"status": "ok", "action": "separate"}

    def heal_separation(self) -> dict:
        """Heal a clip separation. Cmd+B"""
        self._require_as().keystroke("b", modifiers=["command"])
        return {"status": "ok", "action": "heal_separation"}

    def select_all(self) -> dict:
        """Select all clips on all tracks. Cmd+A"""
        self._require_as().keystroke("a", modifiers=["command"])
        return {"status": "ok", "action": "select_all"}

    def undo(self) -> dict:
        """Undo last action."""
        if self._hui:
            self._hui.undo()
        else:
            self._require_as().keystroke("z", modifiers=["command"])
        return {"status": "ok", "action": "undo"}

    def redo(self) -> dict:
        """Redo last undone action."""
        self._require_as().keystroke("z", modifiers=["command", "shift"])
        return {"status": "ok", "action": "redo"}

    def duplicate(self) -> dict:
        """Duplicate selection. Cmd+D"""
        self._require_as().keystroke("d", modifiers=["command"])
        return {"status": "ok", "action": "duplicate"}

    def consolidate(self) -> dict:
        """Consolidate selection into a single clip. Option+Shift+3"""
        self._require_as().keystroke("3", modifiers=["option", "shift"])
        return {"status": "ok", "action": "consolidate"}

    def fade_in(self) -> dict:
        """Create fade-in on selection. D key with selection."""
        self._require_as().keystroke("d")
        return {"status": "ok", "action": "fade_in"}

    def fade_out(self) -> dict:
        """Create fade-out on selection. G key with selection."""
        self._require_as().keystroke("g")
        return {"status": "ok", "action": "fade_out"}

    def crossfade(self) -> dict:
        """Create crossfade at edit point. Cmd+F"""
        self._require_as().keystroke("f", modifiers=["command"])
        return {"status": "ok", "action": "crossfade"}

    def batch_fades(self) -> dict:
        """Open batch fades dialog. Cmd+Option+F"""
        self._require_as().keystroke("f", modifiers=["command", "option"])
        return {"status": "ok", "action": "batch_fades"}

    def nudge_forward(self) -> dict:
        """Nudge selection forward by nudge value. Numpad +"""
        self._require_as().keystroke("+")
        return {"status": "ok", "action": "nudge_forward"}

    def nudge_backward(self) -> dict:
        """Nudge selection backward by nudge value. Numpad -"""
        self._require_as().keystroke("-")
        return {"status": "ok", "action": "nudge_backward"}

    def nudge_forward_n(self, count: int = 1) -> dict:
        """Nudge forward by count steps."""
        aps = self._require_as()
        for _ in range(count):
            aps.keystroke("+")
            time.sleep(0.05)
        return {"status": "ok", "action": "nudge_forward", "count": count}

    def nudge_backward_n(self, count: int = 1) -> dict:
        """Nudge backward by count steps."""
        aps = self._require_as()
        for _ in range(count):
            aps.keystroke("-")
            time.sleep(0.05)
        return {"status": "ok", "action": "nudge_backward", "count": count}

    def tab_to_transient_toggle(self) -> dict:
        """Toggle Tab to Transient mode. Cmd+Tab (in some configs)."""
        self._require_as().key_code(48, modifiers=["command"])
        return {"status": "ok", "action": "tab_to_transient_toggle"}

    def tab_forward(self) -> dict:
        """Tab to next clip boundary or transient."""
        self._require_as().key_code(48)  # Tab
        return {"status": "ok", "action": "tab_forward"}

    def tab_backward(self) -> dict:
        """Tab to previous clip boundary or transient. Option+Tab"""
        self._require_as().key_code(48, modifiers=["option"])
        return {"status": "ok", "action": "tab_backward"}

    def trim_start_to_cursor(self) -> dict:
        """Trim clip start to cursor position. Option+A"""
        self._require_as().keystroke("a", modifiers=["option"])
        return {"status": "ok", "action": "trim_start_to_cursor"}

    def trim_end_to_cursor(self) -> dict:
        """Trim clip end to cursor position. Option+S"""
        self._require_as().keystroke("s", modifiers=["option"])
        return {"status": "ok", "action": "trim_end_to_cursor"}

    def strip_silence(self) -> dict:
        """Open Strip Silence dialog."""
        self._require_as().menu_click(["Edit", "Strip Silence"])
        return {"status": "ok", "action": "strip_silence"}

    def spot_dialog(self) -> dict:
        """Open Spot dialog for precise clip placement. Option+H"""
        self._require_as().keystroke("h", modifiers=["option"])
        return {"status": "ok", "action": "spot_dialog"}
