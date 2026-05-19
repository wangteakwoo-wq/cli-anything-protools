# cli-anything-protools Test Plan and Results

## Test Inventory

- `test_core.py`: Unit tests for core modules (synthetic, no Pro Tools needed)
- `test_full_e2e.py`: E2E tests (requires Pro Tools running + IAC Driver)

## Unit Tests (test_core.py)

### Backend detection
- `test_find_protools`: Verify PT app detection
- `test_get_version`: Version string parsing
- `test_system_info`: System info dict structure

### HUI Protocol
- `test_hui_fader_message`: Correct pitchbend encoding
- `test_hui_switch_message`: Zone+port two-message protocol
- `test_hui_transport_zones`: Transport zone/port values
- `test_hui_bank_navigation`: Bank left/right messages

### AppleScript Bridge
- `test_keystroke_generation`: Correct osascript command building
- `test_menu_path_generation`: Nested menu AppleScript
- `test_modifier_encoding`: Modifier key mapping

### AAF Engine
- `test_aaf_builder_creation`: Builder initialization
- `test_add_tracks`: Track addition
- `test_place_clip`: Clip placement
- `test_timecode_conversion`: TC string to seconds and back
- `test_build_from_template`: Template-based build

### Controller Logic
- `test_transport_play_stop`: TransportController logic
- `test_mix_fader_range`: Fader value clamping
- `test_mix_bank_calculation`: Bank/strip resolution
- `test_edit_operations`: Edit command routing
- `test_session_operations`: Session controller logic

## E2E Tests (test_full_e2e.py)

Requires Pro Tools running with HUI configured on IAC Driver.

### Transport E2E
- Play/stop round-trip
- Locate to timecode
- Loop toggle

### Mix E2E
- Set fader and read back meter
- Mute/solo toggle
- Bank navigation

### CLI Subprocess Tests
- `cli-anything-protools --help` returns 0
- `cli-anything-protools --json info` returns valid JSON
- `cli-anything-protools transport play` executes without error

## Test Results

Tests pending execution. Run with:

```bash
cd protools/agent-harness
python3 -m pytest cli_anything/protools/tests/ -v
```
