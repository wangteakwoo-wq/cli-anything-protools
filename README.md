# cli-anything-protools

Agent-native CLI for controlling Avid Pro Tools from the command line. Designed for AI assistants (Claude, GPT, etc.) and automation workflows.

## Features

- **Transport control** — play, stop, record, locate, loop
- **Mixer control** — faders, pan, mute, solo, sends, metering
- **Session management** — create, open, save, close sessions
- **Track management** — create, delete, rename, duplicate tracks
- **Editing** — cut, copy, paste, separate, fades, nudge, consolidate
- **Bounce / Export** — bounce to disk, export clips
- **Automation** — read, touch, latch, write modes
- **AAF Builder** — generate AAF files from JSON templates
- **Interactive REPL** — tab-completion, history, help system

## Control Architecture

| Layer | Mechanism | Capabilities |
|-------|-----------|-------------|
| HUI/MIDI | IAC virtual MIDI | Faders, pan, mute, solo, transport, meters |
| AppleScript | System Events UI automation | Menus, dialogs, keyboard shortcuts |
| AAF | Offline file generation | Session structure from JSON templates |

## Requirements

- **macOS** (uses AppleScript and IAC Driver)
- **Avid Pro Tools** (Ultimate / Studio / Artist)
- **Python** 3.10+

## Install

```bash
cd cli-anything-protools
python3 -m venv .venv
source .venv/bin/activate
pip install -e protools/agent-harness/
```

## Quick Start

```bash
# Verify installation
cli-anything-protools info

# Transport
cli-anything-protools transport play
cli-anything-protools transport stop

# Mixer
cli-anything-protools mix fader 1 0.75
cli-anything-protools mix mute 2
cli-anything-protools mix meters

# Session
cli-anything-protools session new -n "My Session"
cli-anything-protools session save

# Tracks
cli-anything-protools track new -t audio -f stereo -n "Guitars"

# Build AAF from template
cli-anything-protools build-aaf template.json -o output.aaf
```

## First-Time Setup

1. **Enable IAC Driver** — Audio MIDI Setup → IAC Driver → check "Device is online"
2. **Configure HUI in Pro Tools** — Setup → Peripherals → MIDI Controllers → Type: HUI → IAC Driver Bus 1
3. **Grant Accessibility** — System Settings → Privacy & Security → Accessibility → enable Terminal/Cursor

## Project Structure

```
protools/agent-harness/
├── setup.py                          # Package config
├── PROTOOLS.md                       # Architecture docs
└── cli_anything/protools/
    ├── protools_cli.py               # CLI entry point + REPL
    ├── core/                         # Business logic
    │   ├── transport.py              # Play, stop, record, locate
    │   ├── mix.py                    # Faders, pan, mute, solo
    │   ├── session.py                # Session CRUD
    │   ├── tracks.py                 # Track management
    │   ├── edit.py                   # Cut, paste, fades
    │   ├── bounce.py                 # Export operations
    │   └── ...
    ├── utils/                        # Protocol engines
    │   ├── applescript_bridge.py     # macOS UI automation
    │   ├── hui_engine.py            # HUI/MIDI protocol
    │   ├── midi_io.py               # MIDI I/O wrapper
    │   ├── aaf_engine.py            # AAF file builder
    │   └── ...
    └── tests/
        └── test_core.py
```

## License

MIT
