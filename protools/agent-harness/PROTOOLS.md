# Pro Tools: Project-Specific Analysis & SOP

## Architecture Summary

Pro Tools is Avid's professional digital audio workstation. Unlike most
CLI-Anything targets, Pro Tools has NO native scripting API, CLI, or
AppleScript dictionary. This harness uses a three-layer hybrid approach.

```
┌─────────────────────────────────────────────────────────┐
│                   Pro Tools GUI                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │   Edit   │ │   Mix    │ │Transport │ │ Plug-Ins  │  │
│  │  Window  │ │  Window  │ │   Bar    │ │  Windows  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       │             │            │              │        │
│  ┌────┴─────────────┴────────────┴──────────────┴────┐  │
│  │             Avid Audio Engine (AAE)               │  │
│  │    HDX/Native, real-time mix, plugin hosting      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
          ▲              ▲                ▲
          │              │                │
   ┌──────┴────┐  ┌──────┴──────┐  ┌─────┴──────┐
   │   Layer 1 │  │   Layer 2   │  │  Layer 3   │
   │ HUI/MIDI  │  │ AppleScript │  │    AAF     │
   │(real-time)│  │  (menus/KB) │  │ (offline)  │
   └───────────┘  └─────────────┘  └────────────┘
```

## Control Layer 1: HUI/MIDI Protocol

The primary real-time control interface. HUI (Human User Interface) is
a MIDI-based protocol originally designed for Mackie's HUI control surface.
Pro Tools has built-in support via `Controllers/HUI.bundle`.

### Connection path
Python (python-rtmidi) → IAC Driver (virtual MIDI) → Pro Tools HUI controller

### Capabilities
- 8 channel faders (pitchbend, 14-bit resolution)
- 8 V-Pots (rotary encoders for pan/send/routing)
- Channel mute, solo, select, record arm
- Transport: play, stop, record, rewind, fast-forward
- Automation mode switching
- Bank/channel navigation
- Meter level feedback
- Scribble strip (track name) feedback
- Keep-alive ping protocol

### Limitations
- 8 channels visible at a time (requires banking)
- V-Pot has limited resolution for precise panning
- Meter feedback is low-resolution (0-12 scale)
- Cannot read session structure or track count

## Control Layer 2: AppleScript / System Events

Used for operations not available via MIDI: menus, dialogs, keyboard shortcuts.
Pro Tools has NO AppleScript dictionary — all interaction is through System Events.

### Connection path
Python (subprocess) → osascript → System Events → Pro Tools GUI

### Capabilities
- File operations: new/open/save/close session
- Track creation and configuration via dialogs
- Bounce to Disk via dialog interaction
- Import audio, session data
- Edit operations via keyboard shortcuts
- Plugin insertion/bypass via menus
- Memory Location creation
- Group management

### Limitations
- Pro Tools must be the frontmost application
- Fragile: depends on exact menu text and dialog layouts
- Slow: each AppleScript call has overhead
- Cannot read UI state reliably
- May break with Pro Tools version updates

## Control Layer 3: AAF (Advanced Authoring Format)

Offline session building using pyaaf2. Creates standard AAF files that
Pro Tools can import via File > Import > Session Data.

### Connection path
Python (pyaaf2) → AAF file → Pro Tools Import

### Capabilities
- Programmatic session structure creation
- Track definitions with names and types
- Audio clip placement on timeline
- Marker/memory location creation
- Timecode-accurate positioning

### Limitations
- One-way: cannot read from Pro Tools sessions
- Import only (not real-time control)
- Some AAF features not supported by Pro Tools
- External audio references only (no embedded essence)

## Backend: Pro Tools (Hard Dependency)

Pro Tools is the rendering engine and MUST be installed. The CLI is a
structured command-line interface TO Pro Tools, not a replacement.

### Detected installation
- Path: /Applications/Pro Tools.app (v21.10.0.67)
- Path: /Applications/Pro Tools Developer.app (v25.6.0.11)
- Bundle IDs: com.avid.ProTools, com.avid.ProToolsDeveloper
- EUCON installed, HUI.bundle present
- MIDI drivers: EuphonixMIDI, MADIfaceUSB3

## Command Groups (14 total)

| Group | Layer | Commands |
|-------|-------|----------|
| transport | HUI+AS | play, stop, record, rtz, locate, loop, mark-in/out |
| mix | HUI | fader, fader-db, pan, mute, solo, rec-arm, bank, meters |
| session | AS+AAF | new, open, save, save-as, close, import-aaf, info |
| track | AS+HUI | new, delete, duplicate, select, rename, names, inactive |
| edit | AS+HUI | cut, copy, paste, separate, undo, redo, fades, nudge, tab |
| bounce | AS | disk, clips, commit |
| automation | HUI | mode (off/read/touch/latch/write/trim), suspend |
| plugin | AS | bypass-all, audiosuite, render |
| io | HUI+AS | setup, output, input, send |
| meter | HUI | levels, peak |
| marker | AS | new, recall, window |
| group | HUI+AS | new, modify, delete, toggle, suspend |
| nav | HUI+AS | zoom-in/out, zoom-selection, mix/edit-window, scrub |
| import | AS | audio, session-data |

## Setup Requirements

1. IAC Driver enabled in Audio MIDI Setup
2. Pro Tools HUI controller configured on IAC Driver Bus 1
3. Python virtual environment with dependencies installed
4. Pro Tools running (for real-time operations)

## Test Coverage

- 25 unit tests (synthetic data, no Pro Tools needed)
- Backend detection, AAF building, controller logic, CLI subprocess tests
- E2E tests require Pro Tools running with HUI configured
