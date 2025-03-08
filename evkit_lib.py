from time import sleep
import time
import serial
import re
from enum import Enum

# Global constant for the RX buffer size when reading responses.
read_buffer_size = 512
serial_port = ''
ev_kit = None


# Note: You normally "Use SAD" for legacy advertisements (≤31 bytes).
#       "Use SEAD" for extended advertising when you need more than 31 bytes
#       or want the advanced BLE 5 features.

# This code references extended-adv commands (SACP, SEAD, etc.). If your module's
# EZ-Serial firmware does not support extended adv (API protocol < 1.3),
# those commands will fail.

"""
Key Features:
- Uses tuples `(success: bool, error_code: int, response: str)` for function returns:
    - `success`: Indicates whether the command executed successfully (`True`) or failed (`False`).
    - `error_code`: The response error code from the BLE module.
    - `response`: The raw text response received from the module.
    - Supports legacy and extended BLE advertising configurations.
    - Implements API commands for device management, including setting names, rebooting,
    and querying firmware details.

"""







def send_custom_command_text(command: str)->tuple:
    """
    Sends an ASCII/text-mode command to the BLE module, followed by \r\n,
    then reads and prints the response.

    Args:
        command (str): The text command (without '\r\n') to send.
    """

    command_packet = command + '\r\n'
    ev_kit.write(command_packet.encode('utf-8'))

    # Read back up to 'read_buffer_size' bytes from the module
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response








def get_firmware_version()->tuple:
    """
    Queries the module's firmware (EZ-Serial) version in text mode
    by sending "/QFV" and printing the raw text response.

    The result typically includes:
        E=<app_version>, S=<stack_version>, P=<protocol_version>, H=<hw_id>, ...
    Where 'P=01xx' indicates the API protocol. For extended adv,
    we need at least 'P=0103' (1.3 or newer).
    """
    # print("Querying firmware version in text mode...")
    command = "/QFV\r\n"
    ev_kit.write(command.encode())
    # print("Response (Firmware Version - Text):", response.decode('utf-8', errors='ignore'))
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response









def set_device_name_extended(device_name: str) -> tuple:
    """
    Sets the BLE device name in extended advertising mode using the SEAD command.
    The payload format is:
      - Length (hex): total bytes for type + device name (length = len(name_bytes) + 1)
      - Type (08): AD type for Shortened Local Name
      - Device Name: the UTF-8 encoded name in hex

    For example, for "HAMED_BLE_5":
      - If the name is 11 bytes, total length = 12 (0x0C)
      - The payload becomes "0C08" followed by the hex representation of "HAMED_BLE_5"

    The command is then sent using SEAD with T=1.
    """
    # Convert the device name to bytes and then to a hex string.
    name_bytes = device_name.encode('utf-8')
    # Total length includes the 1-byte type (0x08)
    total_length = len(name_bytes) + 1
    # Format length as a 2-digit uppercase hex string
    length_hex = f"{total_length:02X}"
    # The AD type for Shortened Local Name is 0x08
    ad_type = "08"
    # Convert the device name bytes to an uppercase hex string
    name_hex = name_bytes.hex().upper()
    # Build the full payload: length + AD type + name
    payload = length_hex + ad_type + name_hex
    # Build and send the SEAD command using T=1
    sead_command = f"SEAD,T=1,D={payload}"
    success, error_code, response = send_custom_command_text(sead_command)
    return success, error_code, response













def get_ping()->tuple:
    """
    Sends a "/PING" command in text mode to verify module communication.
    The response typically includes up-time counters in seconds/fractions.
    """
    # print("Querying ping in text mode...")
    command = "/PING\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response












def reboot_device()->tuple:
    """
    Reboots the BLE module via the "/RBT" text command.
    All current settings revert unless stored in flash.
    """
    # print("Rebooting device in text mode...")
    command = "/RBT\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response












def reset_factory()->tuple:
    """
    Resets the module to factory defaults using the "/RFAC" text command.
    This undoes any persistent (flash-stored) changes,
    then reboots automatically.
    """
    # print("Resetting to factory defaults in text mode...")
    command = "/RFAC\r\n"
    ev_kit.write(command.encode())
    # print("Factory Reset Response (Text):", response.decode('utf-8', errors='ignore'))
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response













def extended_adv_config(P="01", M="00", T="08", H="00", I="00A0", C="07",
                        L="00", O="0000", F="02", A="000000000000",
                        Y="00", E="00", S="00", D="00", N="0018")->tuple:
    """
    Configure EZ-Serial extended advertising parameters in text mode with SACP,
    then start adv using "/CA".

    Args:
        P (str): Advertising mode
                 '0' = Legacy
                 '1' = Extended
                 '2' = Periodic
        M (str): Discovery mode
                 '0' = Non-discoverable/broadcast
                 '1' = General discoverable
        T (str): Advertising type (in hex):
                 - '06' = Extended connectable, undirected
                 - '07' = Extended connectable, directed
                 - '08' = Extended non-connectable, non-scannable
                 - '09' = Extended non-connectable, scannable
        H (str): Primary PHY
                 '00' = 1M, '01' = 2M, '02' = Coded
        I (str): Advertising interval (hex string for 0.625 ms units),
                 e.g. '00A0' => 160 => 100 ms
        C (str): Channel bitmask, e.g. '07' = 37,38,39
        L (str): Address filter policy (0..3)
        O (str): Advertising timeout in seconds, e.g. '0000' = disable
        F (str): Behavior flags bitmask (hex)
                 Bit 0 (0x1) = auto-start on reboot
                 Bit 1 (0x2) = use custom adv data
        A (str): Directed adv address (6 bytes LE). '000000000000' if undirected
        Y (str): Directed address type: '00'=public, '01'=random
        E (str): Secondary PHY: '00'=1M, '01'=2M, '02'=Coded
        S (str): Secondary max skip
        D (str): Advertising SID (0..0x0F)
        N (str): Periodic interval (only valid if P='2'). Usually '0000' for normal extended adv.

    Note:
      - This function first stops adv with "/CAX".
      - Then it sends the "SACP" command with your chosen params.
      - Finally, it calls "/CA" to start advertising again.

      If your firmware is <1.3 (P=0001 in /QFV), extended adv won't work,
      and you'll get errors like 0x020C.
    """
    # Stop any extended adv
    send_custom_command_text("/CAX")

    # Apply the new adv parameters
    sacp_cmd = (
        f"SACP,P={P},M={M},T={T},H={H},I={I},C={C},L={L},"
        f"O={O},F={F},A={A},Y={Y},E={E},S={S},D={D},N={N}"
    )
    success, error_code, response = send_custom_command_text(sacp_cmd)
    # Re-enable advertising with new config
    send_custom_command_text("/CA")

    return success, error_code, response














def print_extended_parameters():
    """
    Issues "GACP" to display the current extended-adv parameters as
    recognized by the module. The response typically shows:

      P=xx, M=xx, T=xx, H=xx, I=xx, ...

    Letting you confirm if your adv config is set or if it fell back to legacy.
    """
    success, error_code, response = send_custom_command_text("GACP")
    if success:
        print(response)
    else:
        print("Command failed: ", get_error_description(error_code))










# def set_extended_adv_data(
#         payload_hex: str,
#         erase_or_append: int = 1,
#         adv_type: str = "08",
#         interval: str = "00A0",
#         discovery_mode: str = "00"
# )->tuple:
#     """
#     Configure extended advertising for custom data, then set the data using SEAD.
#
#     Steps in text mode:
#       1. Stop any extended advertising (/CAX).
#       2. Set SACP with P=1 (extended), T=adv_type, F=02 (use custom data),
#          plus interval, discovery, etc.
#       3. Use SEAD,T=<erase_or_append>,D=<payload_hex> to update the ext adv data.
#       4. Start advertising (/CA).
#
#     Args:
#         payload_hex (str): The hexadecimal string of your adv payload, e.g. '020106FF10FA021122334455'
#         erase_or_append (int):
#             - 0 => Erase existing extended data, then apply
#             - 1 => Append to existing buffer
#         adv_type (str):
#             - '08' => Non-connectable, non-scannable
#             - '09' => Non-connectable, scannable
#             - '06' => Connectable, undirected extended
#             etc.
#         interval (str):
#             BLE adv interval (in 0.625 ms units) in hex, e.g. '00A0' => 100 ms
#         discovery_mode (str):
#             '00' => Non-discoverable/broadcast
#             '01' => General discoverable
#     """
#     # 1) Stop any extended advertising
#     send_custom_command_text("/CAX")
#
#     # 2) SACP with:
#     #    - P=1 => Extended adv
#     #    - M=discovery_mode => '00' or '01'
#     #    - T=adv_type => '08', '09', ...
#     #    - I=interval => e.g. '00A0'
#     #    - F=02 => bit1 => "use custom data"
#     #
#     #    Other parameters kept minimal or zeroed out for simplicity.
#     sacp_cmd = (
#         f"SACP,P=01,"
#         f"M={discovery_mode},"
#         f"T={adv_type},"
#         f"H=00,"
#         f"I={interval},"
#         f"C=07,"
#         f"L=00,"
#         f"O=0000,"
#         f"F=02,"    # ** key bit: use custom data
#         f"A=000000000000,"
#         f"Y=00,"
#         f"E=00,"
#         f"S=00,"
#         f"D=00,"
#         f"N=0000"
#     )
#     send_custom_command_text(sacp_cmd)
#
#     # 3) Apply extended adv data with SEAD.
#     #    erase_or_append => 0 => T=00 => erase+overwrite,
#     #                      1 => T=01 => append
#     sead_cmd = f"SEAD,T=0{erase_or_append},D={payload_hex}"
#     success, error_code, response = send_custom_command_text(sead_cmd)
#
#    # 4) Start advertising
#     send_custom_command_text("/CA")
#
#
#     return success, error_code, response
#
#










def print_extended_adv_data():
    """
    Queries the module's extended advertisement data using the GEAD command in text mode.
    The response typically looks like:
        @R,00xx,GEAD,0000,D=020106... (hex data)
    If there's no data set, 'D=' may be empty.
    """
    success, error_code, response = send_custom_command_text("GEAD")
    # The send_custom_command_text function should read and print
    # whatever the module responds, e.g. "@R,000D,GEAD,0000,D=020106..."

    if success:
        print(response)
    else:
        print("Command failed: ", get_error_description(error_code))











def start_legacy_advertising()->tuple:
    """
    Start legacy advertising using the "/A" text command.

    The "/A" command instructs the BLE module to begin broadcasting advertising
    packets using the current legacy advertisement parameters.

    Note:
      - Ensure that your advertisement parameters have been properly configured
        before invoking this command.
      - This command does not change any advertisement data—it merely starts the
        advertising process.
    """
    # print("Starting legacy advertising (/A) in text mode...")
    command = "/A\r\n"
    ev_kit.write(command.encode('utf-8'))
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response











def clear_and_start_legacy_advertising()->tuple:
    """
    Clear and start legacy advertising using the "/CA" text command.

    The "/CA" command clears any previous legacy advertising configuration and
    then starts advertising with a fresh set of parameters.

    Note:
      - Use this command after updating advertisement parameters or data to ensure
        that the new settings take effect.
      - This operation stops any ongoing legacy advertising, resets the configuration,
        and then re-enables advertising.
    """
    # print("Clearing and starting legacy advertising (/CA) in text mode...")
    command = "/CA\r\n"
    ev_kit.write(command.encode('utf-8'))
    # print("Response (/CA - Clear and Start Legacy Advertising):", response.decode('utf-8', errors='ignore'))
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response


















def stop_legacy_advertising()->tuple:
    """
    Stop legacy advertising using the "/AX" text command.

    The "/AX" command halts any ongoing legacy advertising processes.

    Note:
      - This command is useful when you need to temporarily disable advertising
        (for example, before modifying advertisement parameters or data).
      - After stopping advertising, you can restart it with either "/A" or "/CA".
    """
    # print("Stopping legacy advertising (/AX) in text mode...")
    command = "/AX\r\n"
    ev_kit.write(command.encode('utf-8'))
    # print("Response (/AX - Stop Legacy Advertising):", response.decode('utf-8', errors='ignore'))

    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response











def stop_extended_advertising()->tuple:
    """
    Stop extended advertising using the "/CAX" text command.

    The "/CAX" command terminates any active extended advertising sessions on the BLE module.
    Extended advertising supports longer payloads and additional BLE 5 features, and this
    command is used to disable such advertising when needed.

    Note:
      - Use this command before reconfiguring extended advertisement parameters or data.
      - If your module is using legacy advertising, consider using "/AX" instead.
    """
    # print("Stopping extended advertising (/CAX) in text mode...")
    command = "/CAX\r\n"
    ev_kit.write(command.encode('utf-8'))
    # print("Response (/CAX - Stop Extended Advertising):", response.decode('utf-8', errors='ignore'))
    response = ev_kit.read(read_buffer_size).decode('utf-8', errors='ignore')
    success, error_code = extract_error_code(response)
    return success, error_code, response
















def get_error_description(response_code):
    error_codes = {
        # Success and Core Errors
        0x0000: "EZS_ERR_SUCCESS - Operation successful, no error",

        # SMP Errors
        0x0800: "EZS_ERR_SMP - SMP error category",
        0x0801: "EZS_ERR_SMP_OOB_NOT_AVAILABLE - Out-of-band pairing data is not available",
        0x0802: "EZS_ERR_SMP_SECURITY_OPERATION_FAILED - Security operation failed",
        0x0803: "EZS_ERR_SMP_MIC_AUTH_FAILED - Message integrity check authentication failed",

        # Bluetooth Core Specification (SPEC) Errors
        0x0900: "EZS_ERR_SPEC - Bluetooth® Core Specification error category",
        0x0901: "EZS_ERR_SPEC_UNKNOWN_HCI_COMMAND - Unknown HCI Command",
        0x0902: "EZS_ERR_SPEC_UNKNOWN_CONNECTION_IDENTIFIER - Unknown Connection Identifier",
        0x0903: "EZS_ERR_SPEC_HARDWARE_FAILURE - Hardware Failure",
        0x0904: "EZS_ERR_SPEC_PAGE_TIMEOUT - Page Timeout",
        0x0905: "EZS_ERR_SPEC_AUTHENTICATION_FAILURE - Authentication Failure",
        0x0906: "EZS_ERR_SPEC_PIN_OR_KEY_MISSING - PIN or Key Missing",
        0x0907: "EZS_ERR_SPEC_MEMORY_CAPACITY_EXCEEDED - Memory Capacity Exceeded",
        0x0908: "EZS_ERR_SPEC_CONNECTION_TIMEOUT - Connection Timeout",
        0x0909: "EZS_ERR_SPEC_CONNECTION_LIMIT_EXCEEDED - Connection Limit Exceeded",
        0x0919: "EZS_ERR_SPEC_UNKNOWN_LMP_PDU - Unknown LMP PDU",
        0x091A: "EZS_ERR_SPEC_UNSUPPORTED_REMOTE_LMP_FEATURE - Unsupported Remote Feature / Unsupported LMP Feature",
        0x091B: "EZS_ERR_SPEC_SCO_OFFSET_REJECTED - SCO Offset Rejected",
        0x091C: "EZS_ERR_SPEC_SCO_INTERVAL_REJECTED - SCO Interval Rejected",
        0x091D: "EZS_ERR_SPEC_SCO_AIR_MODE_REJECTED - SCO Air Mode Rejected",
        0x091E: "EZS_ERR_SPEC_INVALID_LMP_LL_PARAMETERS - Invalid LMP Parameters / Invalid LL Parameters",
        0x091F: "EZS_ERR_SPEC_UNSPECIFIED_ERROR - Unspecified Error",
        0x0920: "EZS_ERR_SPEC_UNSUPPORTED_LMP_LL_PARAMETER_VALUE - Unsupported LMP Parameter Value / Unsupported LL Parameter Value",
        0x0921: "EZS_ERR_SPEC_ROLE_CHANGE_NOT_ALLOWED - Role Change Not Allowed",
        0x0922: "EZS_ERR_SPEC_LMP_LL_RESPONSE_TIMEOUT - LMP Response Timeout / LL Response Timeout",
        0x0923: "EZS_ERR_SPEC_LMP_ERROR_TRANSACTION_COLLISION - LMP Error Transaction Collision",
        0x0924: "EZS_ERR_SPEC_LMP_PDU_NOT_ALLOWED - LMP PDU Not Allowed",
        0x0925: "EZS_ERR_SPEC_ENCRYPTION_MODE_NOT_ACCEPTABLE - Encryption Mode Not Acceptable",
        0x0926: "EZS_ERR_SPEC_LINK_KEY_CANNOT_BE_CHANGED - The link Key cannot be Changed",
        0x0927: "EZS_ERR_SPEC_REQUESTED_QOS_NOT_SUPPORTED - Requested QoS Not Supported",
        0x0928: "EZS_ERR_SPEC_INSTANT_PASSED - Instant Passed",
        0x0929: "EZS_ERR_SPEC_PAIRING_WITH_UNIT_KEY_NOT_SUPPORTED - Pairing with Unit Key Not Supported",
        0x092A: "EZS_ERR_SPEC_DIFFERENT_TRANSACTION_COLLISION - Different Transaction Collision",
        0x092C: "EZS_ERR_SPEC_QOS_UNACCEPTABLE_PARAMETER - QoS Unacceptable Parameter",
        0x092D: "EZS_ERR_SPEC_QOS_REJECTED - QoS Rejected",
        0x092E: "EZS_ERR_SPEC_CHANNEL_CLASSIFICATION_NOT_SUPPORTED - Channel Classification Not Supported",
        0x092F: "EZS_ERR_SPEC_INSUFFICIENT_SECURITY - Insufficient Security",
        0x0930: "EZS_ERR_SPEC_PARAMETER_OUT_OF_MANDATORY_RANGE - Parameter Out Of Mandatory Range",
        0x0932: "EZS_ERR_SPEC_ROLE_SWITCH_PENDING - Role Switch Pending",
        0x0934: "EZS_ERR_SPEC_RESERVED_SLOT_VIOLATION - Reserved Slot Violation",
        0x0935: "EZS_ERR_SPEC_ROLE_SWITCH_FAILED - Role Switch Failed",
        0x0936: "EZS_ERR_SPEC_EXTENDED_INQUIRY_RSP_TOO_LARGE - Extended Inquiry Response Too Large",
        0x0937: "EZS_ERR_SPEC_SSP_NOT_SUPPORTED_BY_HOST - Secure Simple Pairing Not Supported By Host",
        0x0938: "EZS_ERR_SPEC_HOST_BUSY_PAIRING - Host Busy - Pairing",
        0x0939: "EZS_ERR_SPEC_CONNECTION_REJECTED_NO_SUITABLE_CHANNEL - Connection Rejected due to No Suitable Channel Found",
        0x093A: "EZS_ERR_SPEC_CONTROLLER_BUSY - Controller Busy",
        0x093B: "EZS_ERR_SPEC_UNACCEPTABLE_CONNECTION_PARAMETERS - Unacceptable Connection Parameters",
        0x093C: "EZS_ERR_SPEC_DIRECTED_ADVERTISING_TIMEOUT - Directed Advertising Timeout",
        0x093D: "EZS_ERR_SPEC_CONNECTION_TERMINATED_MIC_FAILURE - Connection Terminated due to MIC Failure",
        0x093E: "EZS_ERR_SPEC_CONNECTION_FAILED_TO_BE_ESTABLISHED - Connection Failed to be Established",
        0x093F: "EZS_ERR_SPEC_MAC_CONNECTION_FAILED - MAC Connection Failed",
        0x0940: "EZS_ERR_SPEC_COARSE_CLOCK_ADJ_REJECTED - Coarse Clock Adjustment Rejected but Will Try to Adjust Using Clock Dragging",

        # Generic Unknown Error
        0xEEEE: "EZS_ERR_UNKNOWN - Unknown problem (internal error)"
    }

    return error_codes.get(response_code, f"Unknown Error Code: {hex(response_code)}")













def extract_error_code(response):
    """
    Extracts the success/error code from a response string.

    - @R = Response message, contains an error code.
    - @E = Event message, does not necessarily contain an error code.
    - Handles cases where no error code is present.
    """

    # Match @R response pattern to extract the error code
    match = re.search(r"@R,[0-9A-Fa-f]+,[^,]+,([0-9A-Fa-f]{4})", response)

    if match:
        error_code = int(match.group(1), 16)  # Convert to hex integer
    else:
        # If no error code is found, assume it's a non-error event like firmware version or reboot
        error_code = 0x0000  # Default to success if no error code is present

    success = (error_code == 0x0000)  # Check if success (0000 means no error)

    return success, error_code













class ADType(Enum):
    FLAGS = 0x01  # Flags (Core Spec Supplement, Part A, Section 1.3)
    INCOMPLETE_LIST_16_BIT_SERVICE_CLASS_UUIDS = 0x02  # Incomplete List of 16-bit Service Class UUIDs (Part A, Section 1.1)
    COMPLETE_LIST_16_BIT_SERVICE_CLASS_UUIDS = 0x03    # Complete List of 16-bit Service Class UUIDs (Part A, Section 1.1)
    INCOMPLETE_LIST_32_BIT_SERVICE_CLASS_UUIDS = 0x04    # Incomplete List of 32-bit Service Class UUIDs (Part A, Section 1.1)
    COMPLETE_LIST_32_BIT_SERVICE_CLASS_UUIDS = 0x05      # Complete List of 32-bit Service Class UUIDs (Part A, Section 1.1)
    INCOMPLETE_LIST_128_BIT_SERVICE_CLASS_UUIDS = 0x06   # Incomplete List of 128-bit Service Class UUIDs (Part A, Section 1.1)
    COMPLETE_LIST_128_BIT_SERVICE_CLASS_UUIDS = 0x07     # Complete List of 128-bit Service Class UUIDs (Part A, Section 1.1)
    SHORTENED_LOCAL_NAME = 0x08                          # Shortened Local Name (Part A, Section 1.2)
    COMPLETE_LOCAL_NAME = 0x09                           # Complete Local Name (Part A, Section 1.2)
    TX_POWER_LEVEL = 0x0A                                # Tx Power Level (Part A, Section 1.5)
    CLASS_OF_DEVICE = 0x0D                               # Class of Device (Part A, Section 1.6)
    SIMPLE_PAIRING_HASH_C192 = 0x0E                      # Simple Pairing Hash C-192 (Part A, Section 1.6)
    SIMPLE_PAIRING_RANDOMIZER_R192 = 0x0F                # Simple Pairing Randomizer R-192 (Part A, Section 1.6)
    DEVICE_ID = 0x10                                     # Device ID (Device ID Profile)
    SM_TK_VALUE = 0x10                                   # Security Manager TK Value (Core Spec Supplement, Part A, Section 1.8) - alias for DEVICE_ID
    SECURITY_MANAGER_OOB_FLAGS = 0x11                    # Security Manager Out of Band Flags (Part A, Section 1.7)
    PERIPHERAL_CONNECTION_INTERVAL_RANGE = 0x12        # Peripheral Connection Interval Range (Part A, Section 1.9)
    LIST_16_BIT_SERVICE_SOLICITATION_UUIDS = 0x14        # List of 16-bit Service Solicitation UUIDs (Part A, Section 1.10)
    LIST_128_BIT_SERVICE_SOLICITATION_UUIDS = 0x15       # List of 128-bit Service Solicitation UUIDs (Part A, Section 1.10)
    SERVICE_DATA_16_BIT_UUID = 0x16                      # Service Data – 16-bit UUID (Part A, Section 1.11)
    PUBLIC_TARGET_ADDRESS = 0x17                         # Public Target Address (Part A, Section 1.13)
    RANDOM_TARGET_ADDRESS = 0x18                         # Random Target Address (Part A, Section 1.14)
    APPEARANCE = 0x19                                    # Appearance (Part A, Section 1.12)
    ADVERTISING_INTERVAL = 0x1A                          # Advertising Interval (Part A, Section 1.15)
    LE_BLUETOOTH_DEVICE_ADDRESS = 0x1B                   # LE Bluetooth Device Address (Part A, Section 1.16)
    LE_ROLE = 0x1C                                     # LE Role (Part A, Section 1.17)
    SIMPLE_PAIRING_HASH_C256 = 0x1D                      # Simple Pairing Hash C-256 (Part A, Section 1.6)
    SIMPLE_PAIRING_RANDOMIZER_R256 = 0x1E                # Simple Pairing Randomizer R-256 (Part A, Section 1.6)
    LIST_32_BIT_SERVICE_SOLICITATION_UUIDS = 0x1F        # List of 32-bit Service Solicitation UUIDs (Part A, Section 1.10)
    SERVICE_DATA_32_BIT_UUID = 0x20                      # Service Data – 32-bit UUID (Part A, Section 1.11)
    SERVICE_DATA_128_BIT_UUID = 0x21                     # Service Data – 128-bit UUID (Part A, Section 1.11)
    LE_SECURE_CONNECTIONS_CONFIRMATION_VALUE = 0x22      # LE Secure Connections Confirmation Value (Part A, Section 1.6)
    LE_SECURE_CONNECTIONS_RANDOM_VALUE = 0x23            # LE Secure Connections Random Value (Part A, Section 1.6)
    URI = 0x24                                         # URI (Part A, Section 1.18)
    INDOOR_POSITIONING = 0x25                            # Indoor Positioning (Indoor Positioning Service)
    TRANSPORT_DISCOVERY_DATA = 0x26                      # Transport Discovery Data (Transport Discovery Service)
    LE_SUPPORTED_FEATURES = 0x27                         # LE Supported Features (Part A, Section 1.19)
    CHANNEL_MAP_UPDATE_INDICATION = 0x28                 # Channel Map Update Indication (Part A, Section 1.20)
    PB_ADV = 0x29                                      # PB-ADV (Mesh Profile Specification, Section 5.2.1)
    MESH_MESSAGE = 0x2A                                  # Mesh Message (Mesh Profile Specification, Section 3.3.1)
    MESH_BEACON = 0x2B                                   # Mesh Beacon (Mesh Profile Specification, Section 3.9)
    BIGINFO = 0x2C                                     # BIGInfo (Part A, Section 1.21)
    BROADCAST_CODE = 0x2D                              # Broadcast_Code (Part A, Section 1.22)
    RESOLVABLE_SET_IDENTIFIER = 0x2E                     # Resolvable Set Identifier (Coordinated Set Identification Profile v1.0 or later)
    ADVERTISING_INTERVAL_LONG = 0x2F                     # Advertising Interval – long (Part A, Section 1.15)
    BROADCAST_NAME = 0x30                                # Broadcast_Name (Public Broadcast Profile v1.0 or later)
    ENCRYPTED_ADVERTISING_DATA = 0x31                    # Encrypted Advertising Data (Part A, Section 1.23)
    PERIODIC_ADVERTISING_RESPONSE_TIMING_INFORMATION = 0x32  # Periodic Advertising Response Timing Information (Part A, Section 1.24)
    ELECTRONIC_SHELF_LABEL = 0x34                        # Electronic Shelf Label (ESL Profile)
    INFORMATION_3D = 0x3D                                # 3D Information Data (3D Synchronization Profile)
    MANUFACTURER_SPECIFIC_DATA = 0xFF                    # Manufacturer Specific Data (Part A, Section 1.4)








def set_custom_adv_payload(data: str, ad_type: ADType, append: bool = False) -> tuple:
    """
    Sets (or appends to) the extended advertisement payload using a SEAD command.

    For most AD types, the payload format is:
        [Length][AD Type][Data]
    For Manufacturer Specific Data (AD Type 0xFF), the payload format is:
        [Length][AD Type][Company ID][Data]
    where the Company ID is fixed as "0900".

    Args:
        data (str): The advertisement data as a string. It will be UTF-8 encoded.
        ad_type (ADType): The advertisement data type from the ADType enum.
        append (bool): If False, the payload is first cleared using SEAD with T=00.
                       If True, the new data is appended using SEAD with T=01.

    Returns:
        tuple: (success, error_code, response) from sending the SEAD command.
    """
    # If not appending, first clear the existing payload using SEAD with T=00.
    if not append:
        send_custom_command_text("SEAD,T=00,D=")

    # Encode the data into bytes.
    data_bytes = data.encode('utf-8')

    if ad_type == ADType.MANUFACTURER_SPECIFIC_DATA:
        # For Manufacturer Specific Data, insert the company ID.
        # Fixed Company ID is "0900".
        company_id = "0900"
        # Total length is: 1 byte for AD type + 2 bytes for Company ID + len(data_bytes)
        total_length = len(data_bytes) + 3
        length_hex = f"{total_length:02X}"
        ad_type_hex = f"{ad_type.value:02X}"
        data_hex = data_bytes.hex().upper()
        # Build payload: [Length][AD Type][Company ID][Data]
        payload = length_hex + ad_type_hex + company_id + data_hex
    else:
        # For other AD types, total length is 1 (AD type) + len(data_bytes)
        total_length = len(data_bytes) + 1
        length_hex = f"{total_length:02X}"
        ad_type_hex = f"{ad_type.value:02X}"
        data_hex = data_bytes.hex().upper()
        # Build payload: [Length][AD Type][Data]
        payload = length_hex + ad_type_hex + data_hex

    # Build and send the SEAD command to append the payload (T=01).
    sead_cmd = f"SEAD,T=01,D={payload}"
    return send_custom_command_text(sead_cmd)













#
#
# def get_gerd() -> tuple:
#     """
#     Sends the GERD command to retrieve the current advertising payload.
#
#     Returns:
#         tuple: (success, error_code, response) from the BLE module.
#                The response typically contains the raw hex payload in the form "D=<payload>".
#     """
#     return send_custom_command_text("GERD")
#






def get_gead() -> tuple:
    """
    Sends the GEAD command to retrieve the current extended advertising payload.

    Returns:
        tuple: (success, error_code, response) from the BLE module.
               The response typically contains the raw hex payload in the form "D=<payload>".
    """
    return send_custom_command_text("GEAD")








def get_gacp() -> tuple:
    """
    Sends the GACP command to retrieve the current extended advertising parameters.

    Returns:
        tuple: (success, error_code, response) from the BLE module.
               The response typically shows the extended advertising configuration.
    """
    return send_custom_command_text("GACP")




def set_adv_interval(interval_ms: int) -> tuple:
    """
    Sets the advertising interval by updating the 'I' parameter in the extended
    advertising configuration. The interval is specified in milliseconds and is
    converted to 0.625 ms units (as a 4-digit hex string).

    Valid range:
      - Minimum: 20 ms (0x0020)
      - Maximum: 10240 ms (0x4000)
      - Factory default: 30 ms (0x0030)

    Args:
        interval_ms (int): The desired advertising interval in milliseconds.

    Returns:
        tuple: (success, error_code, response) from the extended_adv_config command.
               If the interval is out of range, returns an error tuple.
    """
    # Check the limits (20 ms to 10240 ms)
    if interval_ms < 20 or interval_ms > 10240:
        return False, 0xEEEE, "Interval out of range. Must be between 20 ms and 10240 ms."

    # Convert ms to units (each unit = 0.625 ms)
    interval_units = int(round(interval_ms / 0.625))

    # Format as a 4-digit uppercase hex string.
    interval_hex = f"{interval_units:04X}"

    # Update the extended advertising configuration by setting the I parameter.
    return extended_adv_config(I=interval_hex)









def get_gacp_details() -> tuple:
    """
    Query the module for extended advertising parameters using the "GACP" command.
    Returns a tuple:
       (success: bool, error_code: int, fields: list of (key, value) tuples, raw_response: str)

    The returned 'fields' list contains parameter names and their corresponding values.
    For example:
       [("P", "01"), ("M", "01"), ("T", "09"), ("H", "00"), ("I", "00A0"), ...]
    """
    # Send the GACP command using the text mode interface.
    success, error_code, response = send_custom_command_text("GACP")
    if not success:
        return success, error_code, None, response

    try:
        # Look for the "GACP," marker in the response and extract the parameter string.
        start = response.find("GACP,")
        if start != -1:
            param_str = response[start + len("GACP,"):]
        else:
            # If not found, assume the entire response is the parameter string.
            param_str = response

        # Split the parameter string by commas.
        parts = param_str.split(',')
        fields = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '=' in part:
                key, value = part.split('=', 1)
                fields.append((key.strip(), value.strip()))
            else:
                fields.append((part, None))

        return True, 0, fields, response
    except Exception as e:
        # Return a parsing error.
        return False, -1, None, response















def get_adv_payload_details() -> tuple:
    """
    Retrieves the current extended advertisement payload using the GEAD command and
    parses it into its component fields.

    The expected format of the payload is a series of AD structures:
      [Length][AD Type][Data]

    For Manufacturer Specific Data (AD Type 0xFF), the Data field is:
      [Company ID (2 bytes)][Additional Data]

    Returns:
        tuple:
          - raw_payload (str): The entire payload as a hex string (e.g., "0201060C0948414D45445F424C455F35")
          - fields (list): A list of tuples, each representing one field.
            Each tuple is of the form:
              (field_length (int), ad_type (int), field_data (str))
            where field_data is a hex string representing the AD data.

    If no payload is found or an error occurs, returns ("", []).
    """
    # Issue the GEAD command to get the advertisement payload.
    success, error_code, response = send_custom_command_text("GEAD")
    if not success:
        # In case of failure, return empty values.
        return ("", [])

    # The response is expected to contain "D=<payload>".
    m = re.search(r"D=([0-9A-Fa-f]+)", response)
    if not m:
        # No payload data found.
        return ("", [])

    raw_payload = m.group(1)
    fields = []
    i = 0
    # Parse the raw hex payload.
    while i < len(raw_payload):
        # Ensure there are at least 2 hex characters for the length.
        if i + 2 > len(raw_payload):
            break
        # The first byte is the length (in hex).
        field_length = int(raw_payload[i:i+2], 16)
        i += 2

        # A length of 0 indicates no further fields.
        if field_length == 0:
            break

        # Next 2 hex digits represent the AD Type.
        if i + 2 > len(raw_payload):
            break
        ad_type = int(raw_payload[i:i+2], 16)
        i += 2

        # The remaining (field_length - 1) bytes are the data.
        data_byte_count = field_length - 1  # number of bytes
        data_hex_length = data_byte_count * 2  # each byte is 2 hex characters

        if i + data_hex_length > len(raw_payload):
            # If the payload is truncated, take whatever is left.
            field_data = raw_payload[i:]
            i = len(raw_payload)
        else:
            field_data = raw_payload[i:i + data_hex_length]
            i += data_hex_length

        fields.append((field_length, ad_type, field_data))

    return raw_payload, fields







def print_adv_payload_details():
    """
    Retrieves and prints the current extended advertisement payload using the GEAD command.

    The GEAD command returns a response that contains the payload as a hex string following ",D=".
    This function extracts the raw payload, calculates its size, parses its fields, and prints for each:
      - Field number, Length, AD Type (in hex and its enum name if available)
      - The raw data (in hex) with its Unicode representation.

    For Manufacturer Specific Data (AD Type 0xFF), the first 2 bytes (4 hex characters)
    are interpreted as the Company ID, and the remaining bytes as additional data.
    """
    # Send GEAD command and get response.
    success, error_code, response = send_custom_command_text("GEAD")
    if not success:
        print("Failed to retrieve advertisement payload:", get_error_description(error_code))
        return

    # Look for the payload data in the response (after ",D=")
    payload_marker = ",D="
    if payload_marker not in response:
        print("No advertisement payload found in response.")
        return

    # Extract raw payload (strip any trailing CR/LF)
    raw_payload = response.split(payload_marker, 1)[1].strip()
    if not raw_payload:
        print("No advertisement payload found.")
        return

    # Calculate total raw payload size in bytes.
    payload_size = len(raw_payload) // 2
    print("\nRaw Payload:", raw_payload)
    print(f"Total Raw Payload Size: {payload_size} bytes\n")

    # Parse the payload into fields.
    fields = []
    pos = 0
    field_index = 1
    while pos < len(raw_payload):
        # Each field starts with a length byte (2 hex digits)
        length_hex = raw_payload[pos:pos+2]
        try:
            field_length = int(length_hex, 16)
        except ValueError:
            print(f"Error parsing length at position {pos}")
            break
        pos += 2

        # A field length of 0 means no further fields.
        if field_length == 0:
            break

        # Next 2 hex digits are the AD Type.
        ad_type_hex = raw_payload[pos:pos+2]
        try:
            ad_type = int(ad_type_hex, 16)
        except ValueError:
            ad_type = 0
        pos += 2

        # The remainder of the field is (field_length - 1) bytes.
        data_length = (field_length - 1) * 2  # two hex digits per byte
        data_hex = raw_payload[pos:pos+data_length]
        pos += data_length

        fields.append((field_length, ad_type, data_hex))

    # Print details for each field.
    for idx, (length, ad_type, data) in enumerate(fields, start=1):
        try:
            ad_enum = ADType(ad_type)
            desc = ad_enum.name.replace("_", " ").title()
        except ValueError:
            desc = "Unknown"

        if ad_type == ADType.MANUFACTURER_SPECIFIC_DATA.value:
            # For Manufacturer Specific Data, the first 2 bytes (4 hex characters) are the Company ID.
            company_id = data[:4]
            additional_data = data[4:]
            try:
                data_bytes = bytes.fromhex(additional_data)
                unicode_repr = data_bytes.decode('utf-8', errors='replace')
            except Exception:
                unicode_repr = "N/A"
            print(f"Field {idx}: Length = {length}, AD Type = 0x{ad_type:02X} ({desc}), Data = {data}")
            print(f"         Company ID       = {company_id}")
            print(f"         Additional Data  = {additional_data}")
            print(f"         Unicode          = {unicode_repr}")
        else:
            try:
                data_bytes = bytes.fromhex(data)
                unicode_repr = data_bytes.decode('utf-8', errors='replace')
            except Exception:
                unicode_repr = "N/A"
            print(f"Field {idx}: Length = {length}, AD Type = 0x{ad_type:02X} ({desc}), Data = {data}")
            print(f"         Unicode          = {unicode_repr}")














def set_smart_manufacturer_payload(total_payload_bytes: int) -> tuple:
    """
    Creates and sends a manufacturer-specific advertising payload based on the desired total byte size.

    For Manufacturer Specific Data (AD Type 0xFF), the payload format is:
      [Length][AD Type][Company ID][Additional Data]

    This function uses a fixed Company ID of "0900". The Additional Data length is:
         total_payload_bytes - 3
    (1 byte for AD type + 2 bytes for Company ID).

    It uses an excerpt as the base message:
         "Divine Mandate for Justice: Cyrus portrays his conquest as being guided by the gods—particularly Marduk—suggesting
          that his rule is divinely sanctioned to bring order and relief. Restoration and Liberation: He emphasizes that
          he has liberated people from the hardships and oppressions imposed by previous regimes. Respect for Cultural
          and Religious Diversity: Cyrus underscores the importance of allowing conquered peoples to honor their own
          traditions and religious practices. A New Era of Tolerance: By implementing policies that fostered freedom of
          worship and the right to return home, Cyrus laid the groundwork for a more just and tolerant society. In essence,
          the message is that legitimate rule comes with the responsibility to ensure the welfare and dignity of all people."
    This text is then cut (or padded) so that its UTF-8 encoding exactly fits the available space.

    Args:
        total_payload_bytes (int): Total size (in bytes) for the manufacturer-specific data field.
                                   This includes 1 byte for AD type, 2 bytes for Company ID, and the remainder for additional data.

    Returns:
        tuple: (success, error_code, response) from sending the SEAD command.
    """
    if total_payload_bytes < 3:
        return (False, 0xEEEE, "Total payload size must be at least 3 bytes.")

    # Calculate available bytes for additional data.
    additional_data_length = total_payload_bytes - 3

    base_message = (
        "Divine Mandate for Justice: Cyrus portrays his conquest as being guided by the gods—particularly Marduk—suggesting "
        "that his rule is divinely sanctioned to bring order and relief. "
        "Restoration and Liberation: He emphasizes that he has liberated people from the hardships and oppressions imposed by "
        "previous regimes. Respect for Cultural and Religious Diversity: Cyrus underscores the importance of allowing conquered "
        "peoples to honor their own traditions and religious practices. A New Era of Tolerance: By implementing policies that fostered "
        "freedom of worship and the right to return home, Cyrus laid the groundwork for a more just and tolerant society. In essence, "
        "the message is that legitimate rule comes with the responsibility to ensure the welfare and dignity of all people."
    )

    # Adjust the message so that its UTF-8 encoded byte length exactly matches additional_data_length.
    # For simplicity, we assume each character is one byte (i.e. plain ASCII).
    if len(base_message) < additional_data_length:
        additional_data = base_message + " " * (additional_data_length - len(base_message))
    else:
        additional_data = base_message[:additional_data_length]

    # Encode the additional data to bytes.
    data_bytes = additional_data.encode('utf-8')

    # Total length is: 1 (for AD type) + 2 (for Company ID) + len(data_bytes)
    total_length = len(data_bytes) + 3
    length_hex = f"{total_length:02X}"
    # Use AD Type "FF" for Manufacturer Specific Data.
    ad_type_hex = "FF"
    # Fixed company ID "0900" for Infineon.
    company_id = "0900"
    data_hex = data_bytes.hex().upper()

    # Build the payload: [Length][AD Type][Company ID][Additional Data]
    payload = length_hex + ad_type_hex + company_id + data_hex

    # Build and send the SEAD command (T=01 means append the payload)
    sead_cmd = f"SEAD,T=01,D={payload}"
    return send_custom_command_text(sead_cmd)


































def init_device(serial_port_par: str, device_name: str) -> tuple:
    """
    Initializes the device by rebooting it, configuring the extended advertising parameters,
    and erasing any existing advertisement payload. This function does not close the COM port,
    leaving the device ready for a new payload.

    Returns:
        tuple: (True, ev_kit) if all steps succeeded, (False, ev_kit) otherwise.
    """
    global ev_kit
    # Open the UART port to the BLE module (adjust COM port + baud as needed).
    ev_kit = serial.Serial(serial_port_par, baudrate=115200, timeout=1)

    # Reboot the device.
    success, error_code, response = reboot_device()
    if success:
        print("Rebooted device successfully")
    else:
        print("Failed to reboot device:", get_error_description(error_code))
        return False, ev_kit

    # Wait a short period for the device to fully reboot.
    sleep(1)

    # Configure extended advertisement parameters.
    success, error_code, response = extended_adv_config()
    if success:
        print("Extended advertisement parameters configured successfully")
    else:
        print("Failed to configure extended advertisement parameters:", get_error_description(error_code))
        return False, ev_kit

    # Erase any existing advertisement payload using SEAD with T=00.
    success, error_code, response = send_custom_command_text("SEAD,T=00,D=")
    if success:
        print("Cleared existing advertisement payload")
    else:
        print("Failed to clear advertisement payload:", get_error_description(error_code))
        return False, ev_kit

    # Set the extended device name.
    success, error_code, response = set_device_name_extended(device_name)
    if success:
        print("Extended device name set successfully")
    else:
        print("Failed to set extended device name:", get_error_description(error_code))
        return False, ev_kit

    return True, ev_kit









def close_device(ev_kit:serial.Serial):
    # Make sure we close the serial port on exit
    ev_kit.close()
    print("Connection closed.")




























