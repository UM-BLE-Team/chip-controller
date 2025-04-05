# BLE Stat Experiment – Chip Controller Python

This project demonstrates an experiment using Infineon BLE modules with EZ‑Serial firmware. The Python-based controller communicates with the BLE module to update and retrieve advertising parameters in real time, and it now includes advanced chart-making functionality to generate high-resolution images of the experimental data. This updated version is designed for rapid prototyping and testing of BLE extended advertising features.

---

## Team
- Manuel Espinoza Narro
- Hamed Esmaeilzadeh
- Nhat Anh Nguyen

---

## Overview

### Real-Time Data Collection:
Continuously retrieves BLE advertising data, including both legacy payload details and extended advertising (GACP) parameters.

### Payload Customization:
Dynamically updates the manufacturer-specific payload using random data, while also allowing for extended advertising parameter display.

### Interactive Control:
Provides keyboard commands to switch between display modes (payload details and GACP parameters) and adjust advertising intervals.

### Chart Generation:
Processes CSV experiment summary files and automatically generates high-resolution charts (PNG images) that illustrate key metrics such as throughput, round duration, and packet counts.

### Robust Communication:
Leverages EZ‑Serial firmware to control Infineon’s CYW20822 module, with detailed API references provided in the accompanying documentation.

---

## Project Files

### `ble_stat_experiment.py`
Main script that runs the BLE experiment. It updates the advertising payload, reads advertising details, and displays them in real time.

### `evkit_lib.py`
Library of functions that encapsulate API commands for interacting with the BLE module (e.g., setting device name, controlling advertising, querying firmware version).

### `chart_generator.py`
Processes CSV summary files and generates high-resolution charts (PNG images), including:
- Throughput per Round
- Round Duration
- Average Throughput by Condition
- Duration vs. Total Packets
- Total Error Counts

### Documentation
- `Infineon-EZ-Serial_firmware_platform_user_guide_for_CYW20822_module-UserManual-v02_00-EN.pdf`
- `Assigned_Numbers.pdf`
- `7 API protocol reference.pdf`

---

## Prerequisites

### Hardware/Software Requirements:
- Python 3 installed on your computer
- Install pyserial:
  ```bash
  pip install pyserial
  ```
- (Optional on Windows) Install colorama:
  ```bash
  pip install colorama
  ```
- A compatible Infineon BLE module (e.g., CYW20822 with EZ‑Serial firmware) connected via serial interface
- USB-to-serial adapter if required

---

## Installation and Setup

### Connect the Device:
Connect and power the BLE module or evaluation kit (e.g., CYW920822M2P4XXI040-EVK). Identify your COM port.

### Configure the Script:
- Open `ble_stat_experiment.py`
- Adjust parameters like `payload_update_interval`, `display_refresh_rate`, and `adv_interval_ms`
- Ensure `evkit_lib.py` sends the correct commands to your module

### Chart Generation:
- After running experiments, CSV files are saved
- Run `chart_generator.py` to generate charts in the output folder (e.g., `charts_output`)

---

## Running the Experiment

### Launch:
```bash
python ble_stat_experiment.py
```
Enter the COM port number (e.g., `3` for COM3) and optionally a device name (default: `Hamed_Experiment`).

### Real-Time Operation:
- Module broadcasts with randomized manufacturer-specific payload
- Display shows either payload details or GACP parameters

### Keyboard Commands:
- `p`: Show payload details
- `g`: Show GACP parameters
- `s`: Increase advertising interval (slower rate)
- `f`: Decrease advertising interval (faster rate)
- `Ctrl+C`: Gracefully stop experiment

### Data Storage:
CSV and round summary files are saved to:
- `/storage/emulated/0/Documents/experiment_data/`
- `/storage/emulated/0/Documents/experiment_summary/`

---

## Data Collection

The experiment logs the following for each round:
- `Round`: Current round number
- `TotalPackets`: Packets received
- `Duration (s)`: Time taken for round
- `Throughput (p/s)`: Packets/second
- `Errors`: Packets that failed payload validation (should be 0 normally)

---

## Environment Considerations

### Test Conditions:
- Normal room environment
- >10 active Bluetooth devices for interference simulation

### Payload Limitations:
- Max payload size: 230 bytes
- Larger payloads will crash sender

---

