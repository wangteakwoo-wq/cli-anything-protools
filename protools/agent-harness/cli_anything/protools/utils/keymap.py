"""Pro Tools keyboard shortcut mappings.

Default shortcuts for Pro Tools on macOS.
These correspond to the standard keyboard shortcuts, not custom mappings.
"""

# fmt: off

SHORTCUTS: dict[str, dict] = {
    # Transport
    "play":              {"key": " ", "modifiers": []},
    "stop":              {"key": " ", "modifiers": []},
    "record":            {"key": "F12", "code": 111, "modifiers": []},
    "return_to_zero":    {"key": "return", "modifiers": []},
    "go_to_end":         {"key": "return", "modifiers": ["option"]},

    # Edit operations
    "cut":                      {"key": "x", "modifiers": ["command"]},
    "copy":                     {"key": "c", "modifiers": ["command"]},
    "paste":                    {"key": "v", "modifiers": ["command"]},
    "undo":                     {"key": "z", "modifiers": ["command"]},
    "redo":                     {"key": "z", "modifiers": ["command", "shift"]},
    "select_all":               {"key": "a", "modifiers": ["command"]},
    "separate_clip":            {"key": "b", "modifiers": []},
    "heal_separation":          {"key": "b", "modifiers": ["command"]},
    "consolidate":              {"key": "3", "modifiers": ["option", "shift"]},
    "duplicate":                {"key": "d", "modifiers": ["command"]},
    "trim_start_to_insertion":  {"key": "a", "modifiers": ["option"]},
    "trim_end_to_insertion":    {"key": "s", "modifiers": ["option"]},

    # Navigation
    "tab_forward":              {"key": "tab", "code": 48, "modifiers": []},
    "tab_backward":             {"key": "tab", "code": 48, "modifiers": ["option"]},
    "tab_to_transient_toggle":  {"key": "tab", "code": 48, "modifiers": ["command"]},
    "nudge_forward":            {"key": "+", "modifiers": []},
    "nudge_backward":           {"key": "-", "modifiers": []},

    # Zoom
    "zoom_in_horizontal":   {"key": "t", "modifiers": ["command", "option"]},
    "zoom_out_horizontal":  {"key": "r", "modifiers": ["command", "option"]},
    "zoom_to_selection":    {"key": "e", "modifiers": ["option"]},
    "zoom_to_fill":         {"key": "e", "modifiers": ["command", "option"]},

    # Fades
    "fade_in":    {"key": "d", "modifiers": []},
    "fade_out":   {"key": "g", "modifiers": []},
    "crossfade":  {"key": "f", "modifiers": ["command"]},
    "batch_fades": {"key": "f", "modifiers": ["command", "option"]},

    # Session / File
    "save":          {"key": "s", "modifiers": ["command"]},
    "save_as":       {"key": "s", "modifiers": ["command", "shift"]},
    "new_session":   {"key": "n", "modifiers": ["command"]},
    "open_session":  {"key": "o", "modifiers": ["command"]},
    "close_session": {"key": "w", "modifiers": ["command", "shift"]},
    "import_audio":  {"key": "i", "modifiers": ["command", "shift"]},
    "bounce_to_disk": {"key": "b", "modifiers": ["command", "shift"]},

    # Track operations
    "new_track":            {"key": "n", "modifiers": ["command", "shift"]},
    "delete_track":         {"key": "delete", "code": 51, "modifiers": ["command"]},
    "group_create":         {"key": "g", "modifiers": ["command"]},
    "group_enable_toggle":  {"key": "g", "modifiers": ["command", "shift"]},

    # Window views
    "toggle_mix_window":  {"key": "=", "modifiers": ["command"]},
    "toggle_edit_window": {"key": "=", "modifiers": []},

    # Memory Locations
    "new_memory_location":    {"key": "enter", "modifiers": []},
    "memory_location_window": {"key": "5", "modifiers": ["command"]},

    # Automation
    "automation_write_all": {"key": "w", "modifiers": ["command", "option", "control"]},

    # Misc
    "spot_dialog": {"key": "h", "modifiers": ["option"]},
}

# fmt: on

MENU_PATHS: dict[str, list[str]] = {
    "new_session":            ["File", "New Session..."],
    "open_session":           ["File", "Open Session..."],
    "save_session":           ["File", "Save"],
    "save_session_as":        ["File", "Save As..."],
    "close_session":          ["File", "Close Session"],
    "import_audio":           ["File", "Import", "Audio..."],
    "import_session_data":    ["File", "Import", "Session Data..."],
    "bounce_to_disk":         ["File", "Bounce to", "Disk..."],
    "export_clips_as_files":  ["File", "Export", "Clips as Files..."],

    "new_track":       ["Track", "New..."],
    "delete_track":    ["Track", "Delete"],
    "duplicate_track": ["Track", "Duplicate..."],
    "split_into_mono": ["Track", "Split into Mono"],
    "make_inactive":   ["Track", "Make Inactive"],
    "make_active":     ["Track", "Make Active"],

    "group_create":  ["Track", "Group", "Create..."],
    "group_modify":  ["Track", "Group", "Modify..."],
    "group_delete":  ["Track", "Group", "Delete..."],

    "memory_location_new": ["Window", "Memory Locations"],

    "strip_silence": ["Edit", "Strip Silence"],
    "fades_create":  ["Edit", "Fades", "Create..."],
    "fades_batch":   ["Edit", "Fades", "Batch..."],
}

TRACK_TYPES: dict[str, str] = {
    "audio":          "Audio Track",
    "aux":            "Aux Input",
    "master":         "Master Fader",
    "vca":            "VCA Master",
    "midi":           "MIDI Track",
    "instrument":     "Instrument Track",
    "video":          "Video Track",
    "routing_folder": "Routing Folder",
}

TRACK_FORMATS: dict[str, str] = {
    "mono":       "Mono",
    "stereo":     "Stereo",
    "5.1":        "5.1",
    "7.1":        "7.1",
    "7.1.2":      "7.1.2",
    "7.1.4":      "7.1.4 (Atmos)",
    "ambisonics": "Ambisonics",
}

AUTOMATION_MODES: dict[str, str] = {
    "off":   "Off",
    "read":  "Read",
    "touch": "Touch",
    "latch": "Latch",
    "write": "Write",
    "trim":  "Trim",
}
