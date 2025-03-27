#!/usr/bin/env python3
import time
import random
import sys
import os
import threading
from evkit_lib import (
    init_device,
    set_smart_manufacturer_payload,
    get_adv_payload_details,
    get_gacp,
    print_adv_payload_details,  # legacy payload display, not used directly now
    close_device,
    ADType, get_gacp_details, set_adv_interval
)




# Experiment parameters
payload_update_interval = 6  # seconds between payload updates
display_refresh_rate = 100    # display refresh rate in Hz
adv_interval_ms = 20  # starting value (must be between 20 and 10240)
adv_interval_jump_amount = 500 #the ms amount of up or down by keyboard input








# Global cache for display text and its lock
display_lock = threading.Lock()
cached_display_text = "No data yet"

# Global variable to select display mode ("payload" or "gacp")
display_mode = "payload"

# Global event to signal threads to stop.
stop_event = threading.Event()

def clear_screen():
    """Clear the terminal screen in a cross-platform manner."""
    if os.name == 'nt':
        try:
            import colorama
            colorama.init()
        except ImportError:
            pass
        os.system('cls')
    else:
        if sys.stdout.isatty():
            sys.stdout.write("\033[H\033[J")
            sys.stdout.flush()
        else:
            print("\n" * 100)









def format_interval(hex_value: str) -> str:
    try:
        val = int(hex_value, 16)
        ms = val * 0.625  # Each unit is 0.625 ms
        return f"{hex_value} (0x{val:04X}) => {ms:.2f} ms"
    except Exception:
        return hex_value







def format_channels(hex_value: str) -> str:
    try:
        val = int(hex_value, 16)
        channels = []
        if val & 0x1:
            channels.append("Channel 37")
        if val & 0x2:
            channels.append("Channel 38")
        if val & 0x4:
            channels.append("Channel 39")
        if channels:
            return f"{hex_value} -> " + ", ".join(channels)
        else:
            return hex_value
    except Exception:
        return hex_value









def format_flags(hex_value: str) -> str:
    try:
        val = int(hex_value, 16)
        flags = []
        if val & 0x1:
            flags.append("Auto-start on boot/disconnection")
        if val & 0x2:
            flags.append("Use custom adv/scan response data")
        if flags:
            return f"{hex_value} -> " + ", ".join(flags)
        else:
            return f"{hex_value} (No flags set, factory default)"
    except Exception:
        return hex_value






def format_mac(hex_value: str) -> str:
    if len(hex_value) == 12:
        return ":".join(hex_value[i:i+2] for i in range(0, 12, 2))
    return hex_value









def get_gacp_display_text() -> str:
    """
    Retrieves the extended advertising parameters using get_gacp_details()
    and returns a formatted multi-line string with descriptive text for each parameter.

    Expected parameters (keys) include:
      P: Advertisement mode
         • 0 = Legacy (factory default)
         • 1 = Extended
         • 2 = Periodic
      M: Discovery mode
         • 0 = Non-discoverable/broadcast-only
         • 1 = General discovery (factory default)
      T: Advertisement type
         • 0x00 = Legacy: Connectable, undirected (factory default)
         • 0x01 = Legacy: Connectable, directed
         • 0x02 = Legacy: Scannable, undirected
         • 0x03 = Legacy: Non-connectable, undirected
         • 0x04 = Periodic: Undirected
         • 0x05 = Periodic: Directed
         • 0x06 = Extended: Undirected connectable
         • 0x07 = Extended: Directed connectable
         • 0x08 = Extended: Non-connectable, non-scannable
         • 0x09 = Extended: Non-connectable, scannable
         • 0x0A = Extended: Non-connectable anonymous directed
      H: Primary PHY
         • 0 = 1M (factory default)
         • 1 = 2M
         • 2 = Coded
      I: Advertisement interval (625 μs units)
      C: Advertisement channels bitmask
      L: Filter policy
         • 0 = Scan and connect from any (factory default)
         • 1 = Scan whitelist-only, connect any
         • 2 = Scan any, connect whitelist-only
         • 3 = Scan and connect whitelist-only
      O: Advertisement timeout (seconds)
      F: Advertisement behavior flags bitmask
         • Bit 0 = Auto-start on boot/disconnection
         • Bit 1 = Use custom adv/scan response data
      A: Directed advertisement address (MAC)
      Y: Directed address type:
         • 0 = BLE_ADDR_PUBLIC
         • 1 = BLE_ADDR_RANDOM
      E: Secondary PHY (same mapping as H)
      S: Secondary max skip (integer)
      D: Secondary SID (0x00–0x0F)
      N: Periodic interval (1.25 ms units)

    Returns:
        A formatted string listing each parameter with descriptive values.
    """
    success, error_code, fields, raw_response = get_gacp_details()
    if not success:
        return "Failed to fetch GACP details: " + str(error_code)
    if not fields:
        return "No extended advertising parameters found."

    lines = ["Extended Advertising Parameters:"]
    for key, value in fields:
        try:
            int_val = int(value, 16)
        except Exception:
            int_val = None

        if key == "P":
            adv_mode = {0: "Legacy (factory default)", 1: "Extended", 2: "Periodic"}.get(int_val, value) if int_val is not None else value
            lines.append(f"P (Adv_mode) = {value} -> {adv_mode}")
        elif key == "M":
            disc_mode = {0: "Non-discoverable/broadcast-only", 1: "General discovery (factory default)"}.get(int_val, value) if int_val is not None else value
            lines.append(f"M (Disc_mode) = {value} -> {disc_mode}")
        elif key == "T":
            adv_type = {
                0x00: "Legacy: Connectable, undirected (factory default)",
                0x01: "Legacy: Connectable, directed",
                0x02: "Legacy: Scannable, undirected",
                0x03: "Legacy: Non-connectable, undirected",
                0x04: "Periodic: Undirected",
                0x05: "Periodic: Directed",
                0x06: "Extended: Undirected connectable",
                0x07: "Extended: Directed connectable",
                0x08: "Extended: Non-connectable, non-scannable",
                0x09: "Extended: Non-connectable, scannable",
                0x0A: "Extended: Non-connectable anonymous directed"
            }.get(int_val, value) if int_val is not None else value
            lines.append(f"T (Type) = {value} -> {adv_type}")
        elif key == "H":
            primary_phy = {0: "1M (factory default)", 1: "2M", 2: "Coded"}.get(int_val, value) if int_val is not None else value
            lines.append(f"H (Primary_phy) = {value} -> {primary_phy}")
        elif key == "I":
            try:
                interval_units = int(value, 16)
                interval_ms = interval_units * 0.625
                lines.append(f"I (Interval) = {value} -> {interval_ms:.2f} ms = {interval_ms/1000:.2f} s")
            except Exception:
                lines.append(f"I (Interval) = {value}")
        elif key == "C":
            lines.append(f"C (Channels) = {format_channels(value)}")
        elif key == "L":
            filter_policy = {0: "Scan and connect from any (factory default)", 1: "Scan whitelist-only, connect any",
                             2: "Scan any, connect whitelist-only", 3: "Scan and connect whitelist-only"}.get(int_val, value) if int_val is not None else value
            lines.append(f"L (Filter) = {value} -> {filter_policy}")
        elif key == "O":
            try:
                timeout_sec = int(value, 16)
                lines.append(f"O (Timeout) = {value} -> {timeout_sec} seconds")
            except Exception:
                lines.append(f"O (Timeout) = {value}")
        elif key == "F":
            lines.append(f"F (Flags) = {format_flags(value)}")
        elif key == "A":
            lines.append(f"A (Directed Adv Address) = {value} -> {format_mac(value)}")
        elif key == "Y":
            direct_type = {0: "BLE_ADDR_PUBLIC", 1: "BLE_ADDR_RANDOM"}.get(int_val, value) if int_val is not None else value
            lines.append(f"Y (Directed Addr Type) = {value} -> {direct_type}")
        elif key == "E":
            secondary_phy = {0: "1M (factory default)", 1: "2M", 2: "Coded"}.get(int_val, value) if int_val is not None else value
            lines.append(f"E (Secondary_phy) = {value} -> {secondary_phy}")
        elif key == "S":
            try:
                max_skip = int(value, 16)
                lines.append(f"S (Secondary_max_skip) = {value} -> {max_skip}")
            except Exception:
                lines.append(f"S (Secondary_max_skip) = {value}")
        elif key == "D":
            try:
                sid = int(value, 16)
                lines.append(f"D (Secondary_SID) = {value} -> {sid}")
            except Exception:
                lines.append(f"D (Secondary_SID) = {value}")
        elif key == "N":
            try:
                periodic_units = int(value, 16)
                periodic_ms = periodic_units * 1.25
                lines.append(f"N (Periodic_interval) = {value} -> {periodic_ms:.2f} ms")
            except Exception:
                lines.append(f"N (Periodic_interval) = {value}")
        else:
            lines.append(f"{key} = {value}")

    return "\n".join(lines)










def get_display_text() -> str:
    """
    Retrieves and formats the current advertising payload details
    (if in 'payload' mode) or the extended advertising parameters (if in 'gacp' mode)
    into a multi-line string.
    """
    global display_mode


    if display_mode == "payload":

        raw_payload, fields = get_adv_payload_details()
        lines = []
        if raw_payload:
            payload_size = len(raw_payload) // 2
            lines.append("Raw Payload: " + raw_payload)
            lines.append(f"Total Raw Payload Size: {payload_size} bytes\n")
            for idx, (length, ad_type, data) in enumerate(fields, start=1):
                try:
                    ad_enum = ADType(ad_type)
                    desc = ad_enum.name.replace("_", " ").title()
                except ValueError:
                    desc = "Unknown"
                if ad_type == ADType.MANUFACTURER_SPECIFIC_DATA.value:
                    company_id = data[:4]
                    additional_data = data[4:]
                    try:
                        data_bytes = bytes.fromhex(additional_data)
                        unicode_repr = data_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        unicode_repr = "N/A"
                    lines.append(f"Field {idx}: Length = {length}, AD Type = 0x{ad_type:02X} ({desc}), Data = {data}")
                    lines.append(f"         Company ID       = {company_id}")
                    lines.append(f"         Additional Data  = {additional_data}")
                    lines.append(f"         Unicode          = {unicode_repr}")
                else:
                    try:
                        data_bytes = bytes.fromhex(data)
                        unicode_repr = data_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        unicode_repr = "N/A"
                    lines.append(f"Field {idx}: Length = {length}, AD Type = 0x{ad_type:02X} ({desc}), Data = {data}")
                    lines.append(f"         Unicode          = {unicode_repr}")
        else:
            lines.append("No advertisement payload found.")
        return "\n".join(lines)




    elif display_mode == "gacp":

        return get_gacp_display_text()



    else:
        return "Unknown display mode."












def display_update_thread():
    """
    Thread function: continuously clear the screen and print the cached display text.
    This thread reads from the global cache (updated by the main loop or keyboard thread).
    """
    global cached_display_text
    while not stop_event.is_set():
        clear_screen()
        with display_lock:
            text = cached_display_text
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        time.sleep(1 / display_refresh_rate)


















def keyboard_input_thread():
    """
    Thread function to listen for keyboard input.
    - 'p': switch to payload display
    - 'g': switch to GACP display
    - '+': increase advertising interval (thus lowering the transmission rate)
    - '-': decrease advertising interval (thus increasing the transmission rate)
    Uses msvcrt (for Windows) for non-blocking input.
    """
    global display_mode, adv_interval_ms
    try:
        import msvcrt
        while not stop_event.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8').lower()
                if ch == 'p':
                    display_mode = "payload"
                elif ch == 'g':
                    display_mode = "gacp"
                elif ch == 's':
                    # Increase the advertising interval (lower transmission frequency)
                    adv_interval_ms += adv_interval_jump_amount  # adjust increment as needed
                    if adv_interval_ms > 10240:
                        adv_interval_ms = 10240  # enforce maximum limit
                    set_adv_interval(adv_interval_ms)
                    print(f"Increased advertising interval to {adv_interval_ms} ms")
                elif ch == 'f':
                    # Decrease the advertising interval (increase transmission frequency)
                    # Ensure that the interval does not go below the minimum allowed (20 ms)
                    adv_interval_ms = max(20, adv_interval_ms - adv_interval_jump_amount)
                    set_adv_interval(adv_interval_ms)
                    print(f"Decreased advertising interval to {adv_interval_ms} ms")
            time.sleep(0.1)
    except ImportError:
        # For Unix-like systems, you might implement using sys.stdin and select
        pass




















def main():
    global cached_display_text, display_mode, adv_interval_ms
    # CLI input: ask for COM port number and device name (use defaults if blank)
    com_port_number = input("Enter COM port number: ").strip()
    device_name = input("Enter device name (default Hamed_Experiment): ").strip() or "Hamed_Experiment"

    if not com_port_number:
        print("Invalid COM port number. Exiting.")
        return

    com_port = "COM{}".format(com_port_number)

    # Initialize the device
    success, ev_device = init_device(com_port, device_name)
    if not success:
        print("Device initialization failed. Exiting.")
        return

    print("Device initialized. Starting experiment... (Press Ctrl+C to quit)")
    print("Press 'p' to display payload details; press 'g' to display extended parameters (GACP).")

    # Update payload initially.
    new_payload_size = random.randint(50, 200)
    set_smart_manufacturer_payload(new_payload_size)
    set_adv_interval(adv_interval_ms)




    # Update the display cache initially.
    with display_lock:
        cached_display_text = get_display_text()

    # Start the display update thread.
    disp_thread = threading.Thread(target=display_update_thread, daemon=True)
    disp_thread.start()




    # Start the keyboard input thread.
    kb_thread = threading.Thread(target=keyboard_input_thread, daemon=True)
    kb_thread.start()



    # # Update device configuration immediately (for example, update payload every payload_update_interval seconds).
    # new_payload_size = random.randint(32, 75)
    # set_smart_manufacturer_payload(new_payload_size)


    try:











        while True:

            # Update the cached display text after making changes.
            with display_lock:
                cached_display_text = get_display_text()
            time.sleep(payload_update_interval)



    except KeyboardInterrupt:
        print("\nExperiment interrupted by user. Shutting down...")
        stop_event.set()
        disp_thread.join()
        kb_thread.join()
        close_device(ev_device)
        print("Connection closed. End of experiment.")
    finally:
        pass

if __name__ == "__main__":
    main()
