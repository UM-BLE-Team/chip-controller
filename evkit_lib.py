from time import sleep
import time
import serial
import re

# Global constant for the RX buffer size when reading responses.
read_buffer_size = 256
serial_port = 'COM3'


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



# Open the UART port to the BLE module (adjust COM port + baud as needed).
ev_kit = serial.Serial(serial_port, baudrate=115200, timeout=1)




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









def set_device_name(device_name: str)->tuple:
    """
    Sets the BLE device name by:
      1) Stopping any current advertising (/AX).
      2) Sending 'SDN,N=<device_name>'.
      3) Optionally re-enabling advertisement (/CA).

    Args:
        device_name (str): The desired name (e.g. "MyDevice").
    """
    # print(f"Setting device name to '{device_name}' in text mode...")

    # Stop all legacy advertisings
    send_custom_command_text("/CAX")
    send_custom_command_text("/AX")

    # Send the "Set Device Name" command in text mode
    command = f"SDN,N={device_name}"
    success, error_code, response = send_custom_command_text(command)


    # Re-enable advertising (if you want the new name to be shown
    # in the local GATT Device Name or scan response).
    send_custom_command_text("/CA")
    send_custom_command_text("/A")


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













def extended_adv_config(P="01", M="01", T="09", H="00", I="00A0", C="07",
                        L="00", O="0000", F="01", A="000000000000",
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

      If your firmware is <1.3 (P=0001 in /QFV), extended adv won't work
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










def set_extended_adv_data(
        payload_hex: str,
        erase_or_append: int = 1,
        adv_type: str = "08",
        interval: str = "00A0",
        discovery_mode: str = "00"
)->tuple:
    """
    Configure extended advertising for custom data, then set the data using SEAD.

    Steps in text mode:
      1. Stop any extended advertising (/CAX).
      2. Set SACP with P=1 (extended), T=adv_type, F=02 (use custom data),
         plus interval, discovery, etc.
      3. Use SEAD,T=<erase_or_append>,D=<payload_hex> to update the ext adv data.
      4. Start advertising (/CA).

    Args:
        payload_hex (str): The hexadecimal string of your adv payload, e.g. '020106FF10FA021122334455'
        erase_or_append (int):
            - 0 => Erase existing extended data, then apply
            - 1 => Append to existing buffer
        adv_type (str):
            - '08' => Non-connectable, non-scannable
            - '09' => Non-connectable, scannable
            - '06' => Connectable, undirected extended
            etc.
        interval (str):
            BLE adv interval (in 0.625 ms units) in hex, e.g. '00A0' => 100 ms
        discovery_mode (str):
            '00' => Non-discoverable/broadcast
            '01' => General discoverable
    """
    # 1) Stop any extended advertising
    send_custom_command_text("/CAX")

    # 2) SACP with:
    #    - P=1 => Extended adv
    #    - M=discovery_mode => '00' or '01'
    #    - T=adv_type => '08', '09', ...
    #    - I=interval => e.g. '00A0'
    #    - F=02 => bit1 => "use custom data"
    #
    #    Other parameters kept minimal or zeroed out for simplicity.
    sacp_cmd = (
        f"SACP,P=01,"
        f"M={discovery_mode},"
        f"T={adv_type},"
        f"H=00,"
        f"I={interval},"
        f"C=07,"
        f"L=00,"
        f"O=0000,"
        f"F=02,"    # ** key bit: use custom data
        f"A=000000000000,"
        f"Y=00,"
        f"E=00,"
        f"S=00,"
        f"D=00,"
        f"N=0000"
    )
    send_custom_command_text(sacp_cmd)

    # 3) Apply extended adv data with SEAD.
    #    erase_or_append => 0 => T=00 => erase+overwrite,
    #                      1 => T=01 => append
    sead_cmd = f"SEAD,T=0{erase_or_append},D={payload_hex}"
    success, error_code, response = send_custom_command_text(sead_cmd)

   # 4) Start advertising
    send_custom_command_text("/CA")


    return success, error_code, response












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


























# Main usage example
try:
    # Factory reset the module so we start fresh
    # reset_factory()

    success, error_code, response = reboot_device()
    if success:
        print("Rebooted device successfully")
    else:
        print("Failed to reboot device")


    success, error_code, response = get_firmware_version()
    if success:
        print(">>> Firmware version:", response)
    else:
        print(">>> Failed to get firmware version:", get_error_description(error_code))



    success, error_code, response = set_device_name("HAMED_BLE")
    if success:
        print(">>> Device name set successfully")
    else:
        print(">>> Failed to set device name:", get_error_description(error_code))



    # Example: configure extended adv with default arguments

    success, error_code, response = extended_adv_config()
    if success:
        print(">>> Extended advertisement parameters configured successfully")
    else:
        print(">>> Failed to configure extended advertisement parameters:", get_error_description(error_code))





    #Doesn't work due to API protocol ver being 1.1 not higher
    # set_extended_adv_data(
    #     payload_hex="020106FF10FA021122334455",  # your custom bytes
    #     erase_or_append=0,
    #     adv_type="08",        # non-scannable
    #     interval="00A0",      # 100 ms
    #     discovery_mode="00"   # broadcast-only
    # )

    # Print out what the module thinks is set for adv parameters
    print_extended_parameters()


    # send_custom_command_text("GEAD")
    # Potentially we could then do SEAD if the firmware truly is 1.3+,
    # but if P=0001 we know it's old so it'd fail with 0x020C.

    
    # send_custom_command_text("SEAD,T=01,D=020106FF10FA021122334455")
    # send_custom_command_text("GEAD")




finally:
    # Make sure we close the serial port on exit
    ev_kit.close()
    print("Connection closed.")
