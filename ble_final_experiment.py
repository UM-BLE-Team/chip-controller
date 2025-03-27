
"""
Title: Extended Advertising Payload Experiment Script

Description:
    This script demonstrates how to incrementally update the extended advertising payload
    on a BLE module using a custom payload defined by a hard-coded message (Cyrus text).

    The experiment works as follows:
      - The initial payload is set with the first 5 bytes of the default message.
      - In each subsequent update (up to a maximum of 7 rounds), 24 bytes of text are appended.
        This 24-byte addition, along with the AD header overhead, results in an overall 32-byte
        increase in the payload.
      - The payload is updated every 5000 advertising packets (~100 seconds per update at 50 Hz).
      - The script prints detailed status information including elapsed time, packet count,
        current payload size, and the most recently appended text.

Usage:
    - Ensure the evkit_lib module is in the Python path.
    - Run the script and input the COM port number when prompted.
    - The script will initialize the BLE device, set the advertising interval, and then
      perform payload updates for up to 7 rounds or until a payload size limit is reached.

Author: Hamed Esmaeilzadeh
Date: 2025-03-27
"""

import time
import sys
from evkit_lib import (
    init_device,
    set_adv_interval,
    get_adv_payload_details,
    close_device,
    send_custom_command_text
)

# Hard-coded default message (Cyrus text, used for payload data)
DEFAULT_MESSAGE = (
    "Divine Mandate for Justice: Cyrus portrays his conquest as being guided by the gods—particularly Marduk—suggesting "
    "that his rule is divinely sanctioned to bring order and relief. Restoration and Liberation: He emphasizes that "
    "he has liberated people from the hardships and oppressions imposed by previous regimes. Respect for Cultural "
    "and Religious Diversity: Cyrus underscores the importance of allowing conquered peoples to honor their own traditions "
    "and religious practices. A New Era of Tolerance: By implementing policies that fostered freedom of worship and the "
    "right to return home, Cyrus laid the groundwork for a more just and tolerant society. In essence, the message is that "
    "legitimate rule comes with the responsibility to ensure the welfare and dignity of all people."
)

# Hard-coded device name for initialization (not used in payload)
DEVICE_NAME = "scout_technologies"

# For the initial payload, use exactly 5 bytes from DEFAULT_MESSAGE.
INITIAL_PAYLOAD_CUSTOM = DEFAULT_MESSAGE[:5]  # e.g. "Divin"
INITIAL_OFFSET = len(INITIAL_PAYLOAD_CUSTOM)  # 5 bytes

# For subsequent updates, we now append 24 bytes at a time.
APPEND_INCREMENT = 24

# Global variable to track where we are in the default message.
current_text_offset = INITIAL_OFFSET

# We'll also track the complete custom payload locally.
local_custom_payload = INITIAL_PAYLOAD_CUSTOM

# Number of rounds to perform (7 rounds)
MAX_ROUNDS = 7

# Constants for experiment configuration
ADV_INTERVAL_MS = 20  # Advertising interval in milliseconds
ADV_FREQUENCY_HZ = 1000 / ADV_INTERVAL_MS  # Advertising frequency in Hz (50 Hz)
PAYLOAD_LIMIT = 160  # Stop experiment when payload reaches ~160 bytes
UPDATE_PACKET_THRESHOLD = 5000  # Update payload every 5000 advertising packets





def send_initial_payload(custom_data_str: str) -> tuple:
    """
    Build and send the initial advertising payload.

    The payload is constructed as a manufacturer-specific AD structure:
        [Length][AD Type=FF][Company ID=0900][custom_data]
    where:
        - Length: Number of bytes of custom_data plus 3 (1 byte for AD Type and 2 bytes for Company ID).
        - AD Type: 'FF' indicates Manufacturer Specific Data.
        - Company ID: '0900' (fixed value).

    Args:
        custom_data_str (str): The custom data to include in the payload.

    Returns:
        tuple: The result tuple returned by send_custom_command_text.
    """
    data = custom_data_str.encode('utf-8')
    length_val = len(data) + 3  # 1 byte for AD Type + 2 bytes for Company ID
    length_hex = f"{length_val:02X}"
    full_payload = length_hex + "FF" + "0900" + data.hex().upper()
    cmd = f"SEAD,T=01,D={full_payload}"
    return send_custom_command_text(cmd)






def append_payload(append_size: int) -> tuple:
    """
    Append additional filler bytes to the existing advertising payload.

    This function performs the following steps:
      1. Uses a global offset (current_text_offset) to determine the next substring from DEFAULT_MESSAGE.
      2. Retrieves the current payload (custom data) from the device.
      3. Appends the new filler bytes to the current payload.
      4. Rebuilds the complete AD structure with the updated custom data.
      5. Sends the new payload using the SEAD command.

    Args:
        append_size (int): The number of bytes to append from DEFAULT_MESSAGE.

    Returns:
        tuple: The result tuple returned by send_custom_command_text.
    """
    global current_text_offset
    # Get new filler bytes from DEFAULT_MESSAGE starting at current_text_offset.
    filler = DEFAULT_MESSAGE.encode('utf-8')[current_text_offset: current_text_offset + append_size]
    if len(filler) < append_size:
        filler += b' ' * (append_size - len(filler))
    # Update the offset for subsequent rounds.
    current_text_offset += append_size

    # Retrieve current custom data from the device.
    payload_details = get_adv_payload_details()
    current_custom = parse_payload_unicode(payload_details)

    # Combine the current custom data with the new filler bytes.
    new_custom_bytes = current_custom.encode('utf-8') + filler

    # Build new AD structure: total length = len(new_custom_bytes) + 3.
    total_length = len(new_custom_bytes) + 3
    length_hex = f"{total_length:02X}"
    # Construct payload with AD Type (FF) and fixed Company ID (0900).
    payload = length_hex + "FF" + "0900" + new_custom_bytes.hex().upper()

    cmd = f"SEAD,T=01,D={payload}"
    return send_custom_command_text(cmd)




def parse_payload_unicode(payload_details) -> str:
    """
    Extract and decode the custom data from the advertising payload details.

    The payload details contain a tuple with a raw hex string and a list of AD fields.
    This function finds the field with AD Type 0xFF that starts with the Company ID "0900" and returns
    the decoded custom data (with the Company ID removed).

    Args:
        payload_details: A tuple containing the raw hex payload and a list of field tuples.

    Returns:
        str: The decoded custom data, or an empty string if not found.
    """
    if not payload_details or len(payload_details) < 2:
        return ""
    fields = payload_details[1]
    for field in fields:
        if field[1] == 0xFF and field[2].startswith("0900"):
            # Remove the Company ID ("0900") and decode the remainder.
            custom_hex = field[2][4:]
            try:
                return bytes.fromhex(custom_hex).decode('utf-8', errors="replace")
            except Exception:
                return "<decode error>"
    return ""





def print_experiment_constants():
    """
    Print experiment configuration and constant values in a formatted manner.
    """
    print("Experiment Constants:")
    print(f"  Advertising Interval: {ADV_INTERVAL_MS} ms ({ADV_FREQUENCY_HZ:.1f} Hz)")
    print(f"  Initial Payload (Custom Data): {INITIAL_PAYLOAD_CUSTOM}  (Length: {len(INITIAL_PAYLOAD_CUSTOM)} bytes)")
    print(f"  Append Increment: {APPEND_INCREMENT} bytes (results in a 32-byte increase per round with overhead)")
    print(f"  Payload Limit: {PAYLOAD_LIMIT} bytes")
    print(f"  Update Threshold: {UPDATE_PACKET_THRESHOLD} packets")
    print(f"  Device Name (for init): {DEVICE_NAME}")
    print(f"  Maximum Rounds: {MAX_ROUNDS}")
    print("-" * 70)








def main():
    """
    Main execution function.

    This function:
      - Initializes the BLE device.
      - Sets the advertising interval.
      - Sends the initial advertising payload.
      - Enters a loop that updates the payload every UPDATE_PACKET_THRESHOLD packets.
      - Updates are performed for a maximum of MAX_ROUNDS rounds.
      - Displays detailed status information including elapsed time, packets sent,
        current custom payload size, and the text that was most recently appended.
      - Terminates when either MAX_ROUNDS is reached or an update fails.
    """
    global local_custom_payload
    print_experiment_constants()

    com_port_number = input("Enter COM port number: ").strip()
    if not com_port_number:
        print("Invalid COM port number. Exiting.")
        sys.exit(1)
    com_port = "COM" + com_port_number

    # Initialize device using the hard-coded device name.
    success, ev_device = init_device(com_port, DEVICE_NAME)
    if not success:
        print("Device initialization failed. Exiting.")
        sys.exit(1)

    success, error_code, response = set_adv_interval(ADV_INTERVAL_MS)
    if not success:
        print("Failed to set advertising interval:", response)
        close_device(ev_device)
        sys.exit(1)
    print(f"Advertising interval set to {ADV_INTERVAL_MS} ms ({ADV_FREQUENCY_HZ:.1f} Hz).")

    # Send the initial payload (5 bytes from DEFAULT_MESSAGE)
    print("Setting initial payload...")
    result = send_initial_payload(INITIAL_PAYLOAD_CUSTOM)
    if not result[0]:
        print("Error setting initial payload:", result[2])
        close_device(ev_device)
        sys.exit(1)

    time.sleep(1)
    payload_details = get_adv_payload_details()
    decoded_payload = parse_payload_unicode(payload_details)
    print("Initial payload set. Payload details:")
    print(payload_details)
    print("Decoded Payload:", decoded_payload)

    # Set the local custom payload from the initial value.
    local_custom_payload = decoded_payload

    print(
        "\nStarting experiment. Payload will increase by 32 bytes every 5000 packets (~100 seconds) for up to 8 rounds.")
    print("Experiment ends when 8 rounds are reached or if an update fails.")

    start_time = time.time()
    next_update_threshold = UPDATE_PACKET_THRESHOLD  # 5000 packets
    packets_per_second = ADV_FREQUENCY_HZ  # 50 packets per second
    round_count = 0  # Count the update rounds

    # Current custom data size (initially 5 bytes)
    current_custom_data_size = len(INITIAL_PAYLOAD_CUSTOM.encode('utf-8'))

    try:
        while True:
            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed:0.3f} s"
            packets_sent = int(elapsed * packets_per_second)
            # Retrieve the payload details from the device.
            payload_details = get_adv_payload_details()
            decoded_payload = parse_payload_unicode(payload_details)
            status = (
                f"Elapsed: {elapsed_str} | Packets Sent: {packets_sent:6d} | "
                f"Custom Data Size: {current_custom_data_size:3d} bytes | Next update: {next_update_threshold:6d} packets | "
                f"Adv Interval: {ADV_INTERVAL_MS} ms ({ADV_FREQUENCY_HZ:.1f} Hz) | Text Append Increment: {APPEND_INCREMENT} bytes | "
                f"Total Increment: 32 bytes | Payload Limit: {PAYLOAD_LIMIT} bytes | Decoded (Local): {local_custom_payload}"
            )
            sys.stdout.write("\r\033[K" + status)
            sys.stdout.flush()

            if packets_sent >= next_update_threshold:
                print("\n\n--- Updating payload ---")
                print(f"Packets: {packets_sent}. Appending {APPEND_INCREMENT} bytes "
                      f"(24 bytes of text = 32 bytes overall increase with overhead)...")
                result = append_payload(APPEND_INCREMENT)
                if not result[0]:
                    print("Error updating payload:", result[2])
                    break
                time.sleep(1)
                # Extract the new filler text that was appended.
                appended_filler = DEFAULT_MESSAGE.encode('utf-8')[
                                  len(local_custom_payload): len(local_custom_payload) + APPEND_INCREMENT]
                appended_text = appended_filler.decode('utf-8', errors="replace")
                # Update our local payload state.
                local_custom_payload += appended_text
                print("Updated payload details:")
                print(payload_details)
                print("Decoded (Local) Payload:", local_custom_payload)
                print("Latest payload added text:", appended_text)
                current_custom_data_size += APPEND_INCREMENT
                next_update_threshold += UPDATE_PACKET_THRESHOLD
                round_count += 1
                if round_count >= MAX_ROUNDS:
                    print("\nReached maximum of 8 rounds. Ending experiment.")
                    break
            time.sleep(1 / 300)  # update at about 300 Hz
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user. Shutting down...")
    finally:
        close_device(ev_device)
        print("Connection closed. End of experiment.")









if __name__ == "__main__":
    main()
