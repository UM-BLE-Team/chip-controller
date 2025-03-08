# BLE Stat Experiment

This project demonstrates an experiment using Infineon BLE modules with EZ-Serial firmware. The experiment is implemented in Python and shows how to retrieve, update, and display BLE advertisement parameters, including both legacy payload details and extended advertising (GACP) parameters.

---

## Overview

- **Real-Time Display:** Continuously updating display of advertising data.
- **Payload Customization:** Random updates to the manufacturer-specific payload.
- **Extended Advertising Parameters:** Ability to switch the display between raw payload details and extended advertising (GACP) parameters.
- **Interactive Control:** Keyboard inputs to switch display modes and adjust the advertising interval.

Designed for rapid prototyping with Infineon’s CYW20822 module, this project uses EZ-Serial firmware (see [Infineon EZ-Serial firmware platform user guide for CYW20822 module](&#8203;:contentReference[oaicite:0]{index=0})) for detailed command and configuration information.

---

## Project Files

- **ble_stat_experiment.py**  
  The main Python script that runs the experiment. It updates the BLE advertising payload at regular intervals, reads advertising details, and displays them in real time.

- **evkit_lib.py**  
  A library of functions that wrap API commands to interact with the BLE module (e.g., setting device name, starting/stopping advertising, querying firmware version).

- **Infineon-EZ-Serial_firmware_platform_user_guide_for_CYW20822_module-UserManual-v02_00-EN.pdf**  
  The official user guide for the EZ-Serial firmware platform, containing detailed hardware, API, and command usage information.

- **Assigned_Numbers.pdf**  
  A document listing Bluetooth® assigned numbers and identifiers for reference when working with BLE protocols.

- **7 API protocol reference.pdf**  
  A comprehensive reference covering the API protocol used by the EZ-Serial firmware, including text and binary modes, data types, command structure, and error codes.

---

## Prerequisites

- **Hardware/Software Requirements:**
    - A computer with Python 3 installed.
    - The `pyserial` package for serial communication.  
      Install via:
      ```
      pip install pyserial
      ```
    - *(Optional for Windows)* The `colorama` package for proper terminal clearing.  
      Install via:
      ```
      pip install colorama
      ```
    - A compatible Infineon BLE module (e.g., CYW20822 module with EZ-Serial firmware) connected via a serial interface.
    - A USB-to-serial adapter if not using the built-in evaluation kit.

---

## Setup

1. **Connect the Device:**
    - Ensure your Infineon BLE module or evaluation kit (e.g., CYW920822M2P4XXI040-EVK) is properly connected to your computer.
    - Identify the COM port assigned to the device.

2. **Configure the Script:**
    - Open `ble_stat_experiment.py` in your favorite code editor.
    - Review the experiment parameters at the top of the file:
        - `payload_update_interval`: Frequency (in seconds) for payload updates.
        - `display_refresh_rate`: Display refresh rate (in Hz).
        - `adv_interval_ms`: Initial advertising interval in milliseconds.
        - `adv_interval_jump_amount`: Step amount (in ms) for increasing or decreasing the advertising interval via keyboard input.

---

## Running the Experiment

1. **Launch the Script:**
    - Execute the following command in your terminal:
      ```
      python ble_stat_experiment.py
      ```

2. **Provide Input:**
    - Enter the COM port number when prompted (e.g., if the device is on COM3, enter `3`).
    - Enter a device name or press Enter to use the default (`Hamed_Experiment`).

3. **Experiment Behavior:**
    - After initialization, the device starts broadcasting BLE advertisements with a random manufacturer-specific payload.
    - The display updates in real time with either:
        - **Payload Details:** Raw advertisement payload broken down into fields.
        - **GACP Details:** Extended advertising parameters (if supported by the firmware).
    - **Keyboard Commands:**
        - **p:** Switch to payload details display.
        - **g:** Switch to GACP (extended advertising parameters) display.
        - **s:** Increase the advertising interval (lowers transmission rate).
        - **f:** Decrease the advertising interval (increases transmission rate).
    - Press **Ctrl+C** to gracefully stop the experiment.

---

## Technical Details

### Advertising Parameters

- **Legacy & Extended Advertising:**  
  Supports both legacy advertising and extended advertising configurations.

- **Extended Advertising Parameters Include:**
    - **Advertising Mode (P):**
        - `0` = Legacy (factory default)
        - `1` = Extended
        - `2` = Periodic
    - **Discovery Mode (M):**
        - `0` = Non-discoverable/broadcast-only
        - `1` = General discovery (factory default)
    - Additional parameters such as Advertising Type (T), Primary PHY (H), Interval (I), etc., are configured via EZ-Serial API commands (see `extended_adv_config` in `evkit_lib.py`).

### API Protocol

- **Communication:**  
  Uses a set of API commands (in both text and binary formats) to interact with the BLE module.
- **Reference Documentation:**  
  Detailed information on API commands, responses, and error codes is available in:
    - [Infineon EZ-Serial firmware platform user guide for CYW20822 module](&#8203;:contentReference[oaicite:1]{index=1})
    - [7 API protocol reference.pdf](&#8203;:contentReference[oaicite:2]{index=2})

### Error Handling

- Functions in `evkit_lib.py` return a tuple in the format `(success, error_code, response)`.
- Detailed error codes and their meanings are documented in the API protocol reference.

---

## Troubleshooting

- **No Data Displayed:**  
  Verify that the correct COM port is entered and that the BLE module is powered on.

- **Communication Issues:**  
  Check your serial connection and ensure the serial settings (baud rate, etc.) match the device's factory defaults.

- **Advertising Issues:**  
  If extended advertising commands return errors, ensure your module’s firmware is version 1.3 or newer.

---

## License

This project is provided as-is without any warranties. Refer to the related Infineon and Bluetooth SIG documents for legal and licensing information regarding EZ-Serial firmware and Bluetooth specifications.

---
