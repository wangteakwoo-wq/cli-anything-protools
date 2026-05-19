# cli-anything-protools

Agent-native CLI for controlling Avid Pro Tools from the command line.

## Prerequisites

- **macOS** (required for AppleScript and IAC Driver)
- **Pro Tools** installed (Ultimate, Studio, or Artist)
- **Python 3.10+**
- **IAC Driver enabled** (see Setup below)

## Installation

```bash
cd protools/agent-harness
pip install -e .
```

Verify:

```bash
which cli-anything-protools
cli-anything-protools --help
```

## Setup: IAC Driver

The IAC Driver is macOS's built-in virtual MIDI interface. It must be enabled:

1. Open **Audio MIDI Setup** (in /Applications/Utilities/)
2. Show MIDI Studio (Window > Show MIDI Studio)
3. Double-click **IAC Driver**
4. Check **"Device is online"**
5. Click Apply

## Setup: Pro Tools HUI Controller

In Pro Tools:

1. Go to **Setup > Peripherals > MIDI Controllers**
2. Set Type: **HUI**
3. Receive From: **IAC Driver Bus 1**
4. Send To: **IAC Driver Bus 1**
5. Click OK

## Quick Start

```bash
# Enter interactive REPL
cli-anything-protools

# Or use subcommands directly
cli-anything-protools transport play
cli-anything-protools transport stop
cli-anything-protools mix fader 1 0.775        # Set ch1 to ~0dB
cli-anything-protools mix mute 3               # Toggle mute on ch3
cli-anything-protools session save
cli-anything-protools edit separate             # Split clip at cursor
cli-anything-protools bounce disk --file-type BWF --bit-depth 24

# JSON output for agents
cli-anything-protools --json transport play
cli-anything-protools --json mix meters
cli-anything-protools --json info
```

## Command Groups

| Group | Description |
|-------|-------------|
| `transport` | Play, stop, record, locate, loop |
| `mix` | Faders, pans, mute, solo, sends, banking |
| `session` | New, open, save, close, import AAF |
| `track` | New, delete, select, rename, configure |
| `edit` | Cut, copy, paste, separate, fades, nudge |
| `bounce` | Bounce to disk, export clips |
| `automation` | Mode control (read/write/touch/latch) |
| `plugin` | AudioSuite, bypass |
| `io` | I/O routing, send assignment |
| `meter` | Level reading |
| `marker` | Memory Locations |
| `group` | Edit/Mix groups |
| `nav` | Zoom, windows, cursor |
| `import` | Audio and session data |
| `build-aaf` | Build AAF from JSON template |

## Control Layers

This CLI uses three complementary control interfaces:

1. **HUI/MIDI** — Real-time mixer and transport control via IAC Driver
2. **AppleScript** — Menu navigation and keyboard shortcuts via System Events
3. **AAF** — Offline session building via pyaaf2

## Limitations

- Pro Tools must be running for real-time control
- HUI controls 8 channels at a time (auto-banking for higher channels)
- AppleScript requires Pro Tools to be the frontmost application
- Plugin parameter control is not available (insert/bypass only)
- Cannot read session file (.ptx) contents directly
