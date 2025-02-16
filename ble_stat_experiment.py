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
    ADType
)

# Experiment parameters
payload_update_interval = 5  # seconds between payload updates
display_refresh_rate = 60    # display refresh rate in Hz

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
        success, error_code, resp = get_gacp()
        if success:
            return "Extended Advertising Parameters:\n" + resp.strip()
        else:
            return "Failed to fetch GACP: " + str(error_code)
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
    Thread function to listen for keyboard input to switch display modes.
    Press 'p' for payload display, 'g' for GACP (extended advertising parameters).
    Uses msvcrt (for Windows) for non-blocking input.
    """
    global display_mode
    try:
        import msvcrt
        while not stop_event.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8').lower()
                if ch == 'p':
                    display_mode = "payload"
                elif ch == 'g':
                    display_mode = "gacp"
            time.sleep(0.1)
    except ImportError:
        # For Unix-like systems, you might implement using sys.stdin and select
        pass

def main():
    global cached_display_text, display_mode
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
