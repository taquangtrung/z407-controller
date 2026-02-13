# Logitech Z407 Controller

Control your Logitech Z407 speakers over BLE (Bluetooth Low Energy) from Linux. This application replaces the physical wireless dial remote by implementing the same BLE GATT protocol.

## Features

- **CLI control**: Volume, bass, playback, input switching, and pairing from the terminal
- **GUI**: Control panel with real-time status updates
- **Auto-reconnection**: Maintains BLE connection with exponential backoff and adapter reset
- **Bluetooth pairing**: Trigger pairing mode for phones, tablets, laptops, etc. to connect to the speaker

## Installation

### Install the Package

```bash
# Create and activate a conda environment
conda create -n z407 python=3.12 -y
conda activate z407

# Install the package from source
cd z407-controller
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
# Scan for Z407 speaker
z407 scan

# Show connection status
z407 status

# Volume control
z407 volume up              # +1 step
z407 volume up --steps 5    # +5 steps
z407 volume down            # -1 step

# Bass control
z407 bass up
z407 bass down --steps 3

# Playback
z407 play                   # Toggle play/pause
z407 next                   # Next track
z407 prev                   # Previous track

# Input switching
z407 input bluetooth
z407 input aux
z407 input usb

# Bluetooth pairing (pair any device: phone, tablet, laptop...)
z407 pair                     # 120 second pairing window
z407 pair --timeout 60        # custom timeout

# Factory reset (with confirmation)
z407 reset

# Launch GUI
z407 gui
z407                          # Default: launches GUI
```

### GUI

The control panel provides:

- **Real-time status**: Connection state with live updates
- **Volume control**: Slider and +/− buttons
- **Bass control**: +/− buttons
- **Playback**: Play/pause, next/prev track
- **Input switching**: Bluetooth / AUX / USB toggle buttons
- **Pair New Device**: One-click pairing mode
- **Factory Reset**: Confirmation-protected reset button

### Bluetooth Pairing Workflow

The Z407 speaker supports two independent Bluetooth connections:
1. **BLE (this app)**: Control channel for volume, input switching, and pairing mode
2. **BT Classic A2DP**: Audio channel for standard Bluetooth audio streaming

To pair a new audio device:

1. Launch the app: `z407` or click "Pair New Device" in the GUI
2. The speaker enters discoverable mode (LED blinks, chime plays)
3. Open Bluetooth settings on your device (phone, tablet, etc.)
4. Select "Logitech Z407" to pair
5. Audio automatically streams to the speaker

## BLE Permissions

On Linux, BLE access may require elevated permissions:

```bash
# Option 1: Add capabilities to the Python executable
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)

# Option 2: Run with sudo (not recommended for GUI)
sudo z407 scan
```

## Development

```bash
# Create and activate conda environment
conda create -n z407 python=3.12 -y
conda activate z407

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## Protocol Reference

Based on reverse engineering by [freundTech](https://github.com/freundTech/logi-z407-reverse-engineering) and [androrama](https://github.com/androrama/Logitech-Z407-Remote-Control-Web-App---Linux).

| Command       | Hex    | Description          |
|---------------|--------|----------------------|
| Bass Up       | `8000` | Increase bass        |
| Bass Down     | `8001` | Decrease bass        |
| Volume Up     | `8002` | Increase volume      |
| Volume Down   | `8003` | Decrease volume      |
| Play/Pause    | `8004` | Toggle playback      |
| Next Track    | `8005` | Next track           |
| Prev Track    | `8006` | Previous track       |
| BT Input      | `8101` | Switch to Bluetooth  |
| AUX Input     | `8102` | Switch to AUX (3.5mm)|
| USB Input     | `8103` | Switch to USB        |
| BT Pairing    | `8200` | Enter pairing mode   |
| Factory Reset | `8300` | Factory reset        |

## License

MIT
