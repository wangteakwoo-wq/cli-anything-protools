"""AppleScript/osascript bridge for controlling Pro Tools through macOS System Events.

Pro Tools lacks a native AppleScript dictionary. All automation is achieved
via System Events—keyboard shortcuts, menu clicks, and dialog interaction.
"""

from __future__ import annotations

import subprocess
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _esc_apple(s: str) -> str:
    """Escape a string for safe embedding in an AppleScript double-quoted literal."""
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
         .replace("\t", "\\t")
    )


class ProToolsAppleScript:
    """Drive Pro Tools via osascript and System Events."""

    def __init__(self, app_name: str | None = None) -> None:
        if app_name:
            self.app_name = app_name
        else:
            self.app_name = self._detect_app()

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_app() -> str:
        for name in ("Pro Tools Developer", "Pro Tools"):
            script = (
                f'tell application "System Events" to '
                f'(name of processes) contains "{name}"'
            )
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.stdout.strip() == "true":
                    return name
            except subprocess.TimeoutExpired:
                continue

        for name in ("Pro Tools Developer", "Pro Tools"):
            script = (
                'tell application "Finder" to exists '
                '(application file id "com.avid.ProTools" of folder '
                '"Applications" of startup disk)'
            )
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.stdout.strip() == "true":
                    return name
            except subprocess.TimeoutExpired:
                continue

        return "Pro Tools"

    def _run_osascript(self, script: str, timeout: float = 30) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("osascript timed out") from exc

        if result.returncode != 0:
            raise RuntimeError(
                f"osascript failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Calibration (New Tracks popups)
    # ------------------------------------------------------------------

    @staticmethod
    def _calibration_path() -> Path:
        return Path.home() / ".cli-anything-protools" / "new-tracks-popup-map.json"

    def _load_calibration(self) -> dict:
        path = self._calibration_path()
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("Calibration load failed: %s", exc)
            return {}

    def _save_calibration(self, data: dict) -> None:
        path = self._calibration_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _norm_label(s: str) -> str:
        return "".join(s.lower().split())

    def _popup_selected_name(self, window_name: str, popup_index: int) -> str:
        escaped_win = _esc_apple(window_name)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f'    tell window "{escaped_win}"\n'
            f'      return name of pop up button {popup_index}\n'
            '    end tell\n'
            '  end tell\n'
            'end tell'
        )
        return self._run_osascript(script)

    def _new_tracks_popup_indices(self) -> dict[str, int]:
        """Detect popup indices in the New Tracks dialog by their current labels.

        Different PT versions/configs may add extra popups (e.g. Folder type),
        shifting indices. We detect by reading the visible popup button names.
        """
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            '    tell window "New Tracks"\n'
            '      set n to count of pop up buttons\n'
            '      set out to {}\n'
            '      repeat with i from 1 to n\n'
            '        set end of out to (i as string) & ":" & (name of pop up button i)\n'
            '      end repeat\n'
            '      set AppleScript\'s text item delimiters to "||"\n'
            '      return out as text\n'
            '    end tell\n'
            '  end tell\n'
            'end tell'
        )
        raw = self._run_osascript(script)
        parts = [p for p in raw.split("||") if p]
        labels: list[tuple[int, str]] = []
        for p in parts:
            try:
                idx_s, name = p.split(":", 1)
                labels.append((int(idx_s), name.strip()))
            except Exception as exc:
                logger.debug("Skipping unparseable popup entry '%s': %s", p, exc)
                continue

        def _find(pred) -> int | None:
            for i, name in labels:
                if pred(name):
                    return i
            return None

        # Heuristics based on common visible labels
        fmt_idx = _find(lambda s: s in ("Mono", "Stereo", "LCR", "Quad") or s.startswith("5.") or s.startswith("7.") or "Ambisonics" in s)
        type_idx = _find(lambda s: "Track" in s or s in ("Aux Input", "Master Fader", "VCA Master", "MIDI Track", "Instrument Track", "Video Track", "Audio Track", "Routing Folder"))
        time_idx = _find(lambda s: s in ("Samples", "Ticks"))

        # Fallbacks: assume rightmost is timebase, one before is type, one before is format
        if time_idx is None and labels:
            time_idx = max(i for i, _ in labels)
        if fmt_idx is None and labels:
            fmt_idx = min(i for i, _ in labels if i != time_idx) if time_idx else labels[0][0]
        if type_idx is None and labels:
            # pick something not fmt/time
            candidates = [i for i, _ in labels if i not in (fmt_idx, time_idx)]
            if candidates:
                type_idx = candidates[-1]

        return {"format": int(fmt_idx or 1), "type": int(type_idx or 2), "timebase": int(time_idx or 3)}

    def calibrate_new_tracks_popups(self, *, max_format: int = 30, max_type: int = 15) -> dict:
        """Probe actual popup ordering for this Pro Tools version and save it.

        Returns dict with keys: format_list, type_list.
        """
        self._ensure_frontmost()
        time.sleep(0.3)

        # Open New Tracks dialog
        self.keystroke("n", ["command", "shift"])
        if not self.wait_for_window("New Tracks", timeout=10.0):
            raise RuntimeError("New Tracks dialog did not appear")
        time.sleep(0.4)

        def _probe_popup_fast(popup_index: int, max_items: int) -> list[str]:
            """Enumerate popup items with ONE osascript call.

            Uses a stable strategy: for each i, reopen popup, go to top,
            move down i steps, select, then read the popup's displayed name.
            This avoids relying on the popup highlighting the current selection.
            """
            script = (
                'tell application "System Events"\n'
                f'  tell process "{self.app_name}"\n'
                '    tell window "New Tracks"\n'
                '      set itemList to {}\n'
                f'      set maxItems to {int(max_items)}\n'
                '      repeat with i from 0 to (maxItems - 1)\n'
                f'        tell pop up button {int(popup_index)} to perform action "AXPress"\n'
                '        repeat 50 times\n'
                '          key code 126\n'
                '        end repeat\n'
                '        if i > 0 then\n'
                '          repeat i times\n'
                '            key code 125\n'
                '          end repeat\n'
                '        end if\n'
                '        key code 36\n'
                '        delay 0.08\n'
                f'        set v to (name of pop up button {int(popup_index)})\n'
                '        if v is in itemList then exit repeat\n'
                '        set end of itemList to v\n'
                '      end repeat\n'
                '      set AppleScript\'s text item delimiters to "||"\n'
                '      return itemList as text\n'
                '    end tell\n'
                '  end tell\n'
                'end tell'
            )
            out = self._run_osascript(script, timeout=120)
            if not out:
                return []
            return [s for s in out.split("||") if s]

        idxs = self._new_tracks_popup_indices()
        format_list = _probe_popup_fast(idxs["format"], max_format)
        type_list = _probe_popup_fast(idxs["type"], max_type)

        # Close dialog (Esc)
        self.key_code(53, ensure_frontmost=False)
        time.sleep(0.2)

        payload = {
            "format_list": format_list,
            "type_list": type_list,
            "saved_at": int(time.time()),
        }
        self._save_calibration(payload)
        return payload

    def _ensure_frontmost(self, timeout: float = 15) -> None:
        """Bring Pro Tools to front. Uses longer timeout in case PT is busy."""
        self._run_osascript(f'tell application "{self.app_name}" to activate', timeout=timeout)
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    @staticmethod
    def _modifier_clause(modifiers: list[str] | None) -> str:
        if not modifiers:
            return ""
        parts = [f"{m} down" for m in modifiers]
        return " using {" + ", ".join(parts) + "}"

    def keystroke(self, key: str, modifiers: list[str] | None = None) -> None:
        if key == "\r" or key == "\n":
            self.key_code(36, modifiers=modifiers)
            return
        self._ensure_frontmost()
        mod = self._modifier_clause(modifiers)
        escaped_key = _esc_apple(key)
        script = (
            'tell application "System Events"\n'
            f'  keystroke "{escaped_key}"{mod}\n'
            "end tell"
        )
        self._run_osascript(script)

    def key_code(self, code: int, modifiers: list[str] | None = None, *, ensure_frontmost: bool = True) -> None:
        if ensure_frontmost:
            self._ensure_frontmost()
        mod = self._modifier_clause(modifiers)
        # 发给 Pro Tools 进程，否则按键会落到前台应用（如终端）
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f"    key code {code}{mod}\n"
            "  end tell\n"
            "end tell"
        )
        self._run_osascript(script)

    # ------------------------------------------------------------------
    # Menu navigation
    # ------------------------------------------------------------------

    def menu_click(self, menu_path: list[str]) -> None:
        self._ensure_frontmost()
        if len(menu_path) < 2:
            raise ValueError("menu_path must have at least [menu, item]")
        script = self._build_menu_click_script(menu_path)
        self._run_osascript(script)

    def menu_click_with_delay(
        self, menu_path: list[str], delay: float = 0.3
    ) -> None:
        self._ensure_frontmost()
        if len(menu_path) < 2:
            raise ValueError("menu_path must have at least [menu, item]")
        script = self._build_menu_click_script(menu_path, delay=delay)
        self._run_osascript(script)

    def _build_menu_click_script(
        self, menu_path: list[str], delay: float | None = None
    ) -> str:
        app = self.app_name
        parts = [
            'tell application "System Events"',
            f'  tell process "{app}"',
            "    tell menu bar 1",
        ]

        indent = "      "
        for i, item in enumerate(menu_path):
            escaped = _esc_apple(item)
            if i == 0:
                parts.append(f'{indent}tell menu bar item "{escaped}"')
                parts.append(f"{indent}  click")
                if delay:
                    parts.append(f"{indent}  delay {delay}")
                parts.append(f'{indent}  tell menu "{escaped}"')
            elif i == len(menu_path) - 1:
                parts.append(f'{indent}    click menu item "{escaped}"')
            else:
                parts.append(f'{indent}    tell menu item "{escaped}"')
                parts.append(f"{indent}      click")
                if delay:
                    parts.append(f"{indent}      delay {delay}")
                parts.append(f'{indent}      tell menu "{escaped}"')

        for i in range(len(menu_path) - 1, 0, -1):
            if i == len(menu_path) - 1:
                continue
            parts.append(f"{indent}      end tell")
            parts.append(f"{indent}    end tell")
        parts.append(f"{indent}  end tell")
        parts.append(f"{indent}end tell")

        parts.append("    end tell")
        parts.append("  end tell")
        parts.append("end tell")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Dialog interaction
    # ------------------------------------------------------------------

    def click_button(self, button_name: str, *, also_try: list[str] | None = None) -> None:
        """Click a button by name. Use also_try for localized names (e.g. ['创建'] for 'Create')."""
        self._ensure_frontmost()
        names_to_try = [button_name] + (also_try or [])
        last_err = None
        for name in names_to_try:
            escaped = _esc_apple(name)
            script = (
                'tell application "System Events"\n'
                f'  tell process "{self.app_name}"\n'
                f'    click button "{escaped}" of front window\n'
                "  end tell\n"
                "end tell"
            )
            try:
                self._run_osascript(script)
                return
            except RuntimeError as e:
                last_err = e
        if last_err:
            raise last_err

    def set_text_field(self, field_index: int, value: str) -> None:
        self._ensure_frontmost()
        escaped = _esc_apple(value)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f"    set value of text field {field_index} of front window"
            f' to "{escaped}"\n'
            "  end tell\n"
            "end tell"
        )
        self._run_osascript(script)

    def select_popup_menu(self, popup_index: int, value: str) -> None:
        self._ensure_frontmost()
        escaped = _esc_apple(value)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f"    tell pop up button {popup_index} of front window\n"
            "      click\n"
            "      delay 0.2\n"
            f'      click menu item "{escaped}" of menu 1\n'
            "    end tell\n"
            "  end tell\n"
            "end tell"
        )
        self._run_osascript(script)

    def wait_for_window(self, window_name: str, timeout: float = 10.0) -> bool:
        escaped = _esc_apple(window_name)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            script = (
                'tell application "System Events"\n'
                f'  tell process "{self.app_name}"\n'
                f'    exists window "{escaped}"\n'
                "  end tell\n"
                "end tell"
            )
            try:
                result = self._run_osascript(script)
                if result == "true":
                    return True
            except RuntimeError:
                pass
            time.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    # High-level Pro Tools operations
    # ------------------------------------------------------------------

    def _clipboard_paste(self, text: str) -> None:
        """Set macOS clipboard and paste into the focused field.

        Pro Tools Dashboard uses a custom UI framework (JUCE) whose text
        fields ignore ``set value`` and ``keystroke``. The only reliable
        way to enter text is via the system clipboard + Cmd-V.
        """
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        time.sleep(0.1)
        self._ensure_frontmost()
        time.sleep(0.2)
        self.keystroke("a", ["command"])
        time.sleep(0.1)
        self.keystroke("v", ["command"])
        time.sleep(0.3)

    def new_session(
        self,
        name: str,
        sample_rate: int = 48000,
        bit_depth: int = 24,
        file_type: str = "BWF",
    ) -> None:
        self._ensure_frontmost()
        time.sleep(0.5)

        self.keystroke("n", ["command"])
        time.sleep(3.0)

        # PT 2021+ opens Dashboard (CREATE / RECENT / PROJECTS tabs).
        # The Dashboard name field is a JUCE custom control that only
        # accepts input via clipboard paste.
        has_dashboard = self.wait_for_window("Dashboard", timeout=5.0)

        if has_dashboard:
            # Activate text field, paste name, configure settings, click Create
            script = (
                'tell application "System Events"\n'
                f'  tell process "{self.app_name}"\n'
                '    tell text field "Name:" of window "Dashboard"\n'
                '      perform action "AXPress"\n'
                '    end tell\n'
                '  end tell\n'
                'end tell'
            )
            self._run_osascript(script)
            time.sleep(0.3)
            self._clipboard_paste(name)
            time.sleep(0.3)

            # Select file type
            type_map = {"BWF": "BWF (.WAV)", "WAV": "BWF (.WAV)", "AIFF": "AIFF"}
            type_label = type_map.get(file_type, file_type)
            self._dashboard_set_popup("File Type:", type_label)

            # Select sample rate
            rate_map = {
                44100: "44.1 kHz", 48000: "48 kHz",
                88200: "88.2 kHz", 96000: "96 kHz",
            }
            rate_label = rate_map.get(sample_rate, f"{sample_rate / 1000:.1f} kHz")
            self._dashboard_set_popup("Sample Rate:", rate_label)

            # Select bit depth
            depth_map = {16: "16-bit", 24: "24-bit", 32: "32-bit"}
            depth_label = depth_map.get(bit_depth, f"{bit_depth}-bit")
            self._dashboard_set_popup("Bit Depth:", depth_label)

            # Use Default location to avoid extra save dialog
            script = (
                'tell application "System Events"\n'
                f'  tell process "{self.app_name}"\n'
                '    tell window "Dashboard"\n'
                '      click radio button "Default location"\n'
                '      delay 0.3\n'
                '      click button "Create"\n'
                '    end tell\n'
                '  end tell\n'
                'end tell'
            )
            self._run_osascript(script)
        else:
            # Fallback for older PT versions with a plain New Session dialog
            self._clipboard_paste(name)
            time.sleep(0.3)
            self.keystroke("\r")

    def _dashboard_set_popup(self, label: str, value: str) -> None:
        """Select a value in a Dashboard popup button identified by label."""
        escaped_label = _esc_apple(label)
        escaped_value = _esc_apple(value)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f'    tell window "Dashboard"\n'
            f'      set allPopups to every pop up button\n'
            f'      repeat with p in allPopups\n'
            f'        try\n'
            f'          if description of p contains "{escaped_label}" then\n'
            f'            click p\n'
            f'            delay 0.2\n'
            f'            click menu item "{escaped_value}" of menu 1 of p\n'
            f'            delay 0.2\n'
            f'          end if\n'
            f'        end try\n'
            f'      end repeat\n'
            f'    end tell\n'
            f'  end tell\n'
            'end tell'
        )
        try:
            self._run_osascript(script)
        except RuntimeError as exc:
            logger.debug("Dashboard popup set failed for %s=%s: %s", label, value, exc)

    def open_session(self, path: str) -> None:
        self.keystroke("o", ["command"])
        if not self.wait_for_window("Open Session", timeout=10.0):
            raise RuntimeError("Open Session dialog did not appear")
        time.sleep(0.5)

        self.keystroke("g", ["command", "shift"])
        time.sleep(0.5)
        self._clipboard_paste(path)
        time.sleep(0.3)
        self.keystroke("\r")  # Confirm Go To Folder
        time.sleep(0.5)
        self.keystroke("\r")  # Confirm Open (click the Open button)

    def save_session(self) -> None:
        self.keystroke("s", ["command"])

    def save_session_as(self, path: str) -> None:
        self.keystroke("s", ["command", "shift"])
        time.sleep(1.0)
        self._clipboard_paste(path)
        time.sleep(0.3)
        self.keystroke("\r")

    def close_session(self) -> None:
        self.keystroke("w", ["command", "shift"])

    def new_track(
        self,
        count: int = 1,
        track_type: str = "Audio",
        track_format: str = "Mono",
        timebase: str = "Samples",
    ) -> None:
        """Create new tracks via the New Tracks dialog.

        Pro Tools uses custom JUCE popup controls that don't expose standard
        macOS menu items, so we navigate with arrow keys from a known baseline.
        """
        self.keystroke("n", ["command", "shift"])
        if not self.wait_for_window("New Tracks", timeout=10.0):
            raise RuntimeError("New Tracks dialog did not appear")
        time.sleep(0.5)

        # Set track count via clipboard paste (JUCE text field)
        self._clipboard_paste(str(count))
        time.sleep(0.2)

        # Track type popup ordering (discovered empirically):
        # NOTE: PT 某些版本/配置下，类型列表最上面会多两个 Folder 选项：
        # 1) Routing Folder 2) Basic Folder
        # 然后才是 Audio/Aux/.../Video Track。
        #
        # Index here is "down-arrow steps from the TOP item".
        type_order = {
            # Folder options (when present)
            "Routing Folder": 0, "routing_folder": 0, "routing folder": 0,
            "Basic Folder": 1, "basic_folder": 1, "basic folder": 1,

            # Track types
            "Audio": 2, "Audio Track": 2, "audio": 2, "audio track": 2,
            "Aux": 3, "Aux Input": 3, "aux": 3, "aux input": 3,
            "Master": 4, "Master Fader": 4, "master": 4, "master fader": 4,
            "VCA": 5, "VCA Master": 5, "vca": 5, "vca master": 5,
            "MIDI": 6, "MIDI Track": 6, "midi": 6, "midi track": 6,
            "Instrument": 7, "Instrument Track": 7, "instrument": 7, "instrument track": 7,
            "Video": 8, "Video Track": 8, "video": 8, "video track": 8,
        }
        _type_key = track_type.strip()
        type_idx = type_order.get(_type_key, type_order.get(_type_key.lower(), type_order.get(_type_key.title(), 0)))

        # Format popup ordering:
        # Mono(0), Stereo(1), LCR(2), Quad(3), LCRS(4), 5.0(5), 5.1(6), 7.0(7), ...
        format_order = {
            "Mono": 0, "Stereo": 1, "LCR": 2, "Quad": 3, "LCRS": 4,
            "5.0": 5, "5.1": 6, "7.0": 7, "7.1": 8, "7.0.2": 9,
            "7.1.2": 10, "7.1.4": 11,
        }
        _fmt_key = track_format.strip()
        format_idx = format_order.get(_fmt_key, format_order.get(_fmt_key.title(), 0))

        # Prefer calibrated list if available (varies by PT version / config)
        cal = self._load_calibration()
        fmt_list = cal.get("format_list") if isinstance(cal, dict) else None
        if isinstance(fmt_list, list) and fmt_list:
            want = self._norm_label(_fmt_key)
            found = None
            for i, label in enumerate(fmt_list):
                nl = self._norm_label(str(label))
                if nl == want or nl.startswith(want) or want.startswith(nl):
                    found = i
                    break
            if found is not None:
                format_idx = int(found)

        idxs = self._new_tracks_popup_indices()

        if type_idx > 0:
            self._navigate_popup_by_index("New Tracks", idxs["type"], type_idx)
            time.sleep(0.3)

        if format_idx > 0 and _type_key.lower() not in ("vca", "vca master", "video", "video track",
                                                         "midi", "midi track"):
            self._navigate_popup_by_index("New Tracks", idxs["format"], format_idx)
            time.sleep(0.3)

        self.click_button("Create", also_try=["创建"])

    def _navigate_popup(self, window_name: str, popup_name: str, steps: int) -> None:
        """Open a popup button by name and press down-arrow `steps` times, then Enter."""
        escaped_win = _esc_apple(window_name)
        escaped_popup = _esc_apple(popup_name)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f'    tell pop up button "{escaped_popup}" of window "{escaped_win}"\n'
            '      perform action "AXPress"\n'
            '    end tell\n'
            '  end tell\n'
            'end tell'
        )
        self._run_osascript(script)
        time.sleep(0.8)
        self._navigate_popup_arrow_steps(steps)

    def _navigate_popup_by_index(self, window_name: str, popup_index: int, steps: int) -> None:
        """Open popup by index (1-based: 1=format, 2=type, 3=timebase) and press down `steps` times."""
        escaped_win = _esc_apple(window_name)
        script = (
            'tell application "System Events"\n'
            f'  tell process "{self.app_name}"\n'
            f'    tell window "{escaped_win}"\n'
            f'      tell pop up button {popup_index}\n'
            '        perform action "AXPress"\n'
            '      end tell\n'
            '    end tell\n'
            '  end tell\n'
            'end tell'
        )
        self._run_osascript(script)
        time.sleep(0.4)
        # Pro Tools 会记住上次选项；为保证 steps 基于“列表顶部”计算，先回到顶部再下移
        self._navigate_popup_arrow_to_top(max_up=30)
        time.sleep(0.1)
        self._navigate_popup_arrow_steps(steps)

    def _navigate_popup_arrow_to_top(self, max_up: int = 30) -> None:
        """Press up-arrow many times to reach the first item in an open popup."""
        # Up arrow key code = 126
        for _ in range(max_up):
            self.key_code(126, ensure_frontmost=False)
            time.sleep(0.05)

    def _navigate_popup_arrow_steps(self, steps: int) -> None:
        """Press down-arrow `steps` times then Return (no activate)."""
        for _ in range(steps):
            self.key_code(125, ensure_frontmost=False)
            time.sleep(0.15)
        self.key_code(36, ensure_frontmost=False)
        time.sleep(0.3)

    def import_audio(self, file_path: str) -> None:
        self.keystroke("i", ["command", "shift"])
        if not self.wait_for_window("Import Audio", timeout=10.0):
            raise RuntimeError("Import Audio dialog did not appear")
        time.sleep(0.5)

        self.keystroke("g", ["command", "shift"])
        time.sleep(0.5)
        self._clipboard_paste(file_path)
        time.sleep(0.3)
        self.keystroke("\r")
        time.sleep(0.5)

        self.click_button("Open")
        time.sleep(0.3)
        self.click_button("Done")

    def bounce_to_disk(
        self,
        file_type: str = "BWF",
        bounce_format: str = "Interleaved",
        bit_depth: int = 24,
        sample_rate: int = 48000,
    ) -> None:
        self.keystroke("b", ["command", "shift"])
        if not self.wait_for_window("Bounce Mix", timeout=10.0):
            if not self.wait_for_window("Bounce to Disk", timeout=5.0):
                raise RuntimeError("Bounce dialog did not appear")
        time.sleep(0.5)

        type_map = {"BWF": "BWF (.WAV)", "WAV": "BWF (.WAV)", "AIFF": "AIFF", "MP3": "MP3"}
        type_label = type_map.get(file_type, file_type)
        self.select_popup_menu(1, type_label)
        time.sleep(0.2)

        self.select_popup_menu(2, bounce_format)
        time.sleep(0.2)

        depth_map = {16: "16 Bit", 24: "24 Bit", 32: "32 Bit Float"}
        depth_label = depth_map.get(bit_depth, f"{bit_depth} Bit")
        self.select_popup_menu(3, depth_label)
        time.sleep(0.2)

        rate_map = {44100: "44100", 48000: "48000", 88200: "88200", 96000: "96000"}
        rate_label = rate_map.get(sample_rate, str(sample_rate))
        self.select_popup_menu(4, rate_label)
        time.sleep(0.2)

        self.click_button("Bounce")

    def select_all(self) -> None:
        self.keystroke("a", ["command"])

    def undo(self) -> None:
        self.keystroke("z", ["command"])

    def redo(self) -> None:
        self.keystroke("z", ["command", "shift"])

    def consolidate(self) -> None:
        self.keystroke("3", ["option", "shift"])
