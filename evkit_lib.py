from time import sleep
import time
import serial


# Global constant for the RX buffer size when reading responses.
read_buffer_size = 256
serial_port = 'COM3'


# Note: You normally "Use SAD" for legacy advertisements (≤31 bytes).
#       "Use SEAD" for extended advertising when you need more than 31 bytes
#       or want the advanced BLE 5 features.

# This code references extended-adv commands (SACP, SEAD, etc.). If your module's
# EZ-Serial firmware does not support extended adv (API protocol < 1.3),
# those commands will fail.


# Open the UART port to the BLE module (adjust COM port + baud as needed).
ev_kit = serial.Serial(serial_port, baudrate=115200, timeout=1)


def send_custom_command_text(command: str):
    """
    Sends an ASCII/text-mode command to the BLE module, followed by \r\n,
    then reads and prints the response.

    Args:
        command (str): The text command (without '\r\n') to send.
    """
    # Append CR+LF as required in text mode
    command_packet = command + '\r\n'
    ev_kit.write(command_packet.encode('utf-8'))

    # Read back up to 'read_buffer_size' bytes from the module
    response = ev_kit.read(read_buffer_size)
    print(f"Response (Custom {command} - Text):", response.decode('utf-8', errors='ignore'))


def send_command(command: bytes, description=""):
    """
    Sends a raw binary command and reads the response (binary or text).
    Usually, we do text mode, so you might not use this often.

    Args:
        command (bytes): The exact byte sequence to send.
        description (str): A label for debugging prints.

    Returns:
        bytes: The response from the module as raw bytes.
    """
    ev_kit.write(command)
    response = ev_kit.read(read_buffer_size)
    print(f"{description} Command: {command.hex()}")
    print(f"{description} Response: {response.hex()}")
    return response


def get_firmware_version():
    """
    Queries the module's firmware (EZ-Serial) version in text mode
    by sending "/QFV" and printing the raw text response.

    The result typically includes:
        E=<app_version>, S=<stack_version>, P=<protocol_version>, H=<hw_id>, ...
    Where 'P=01xx' indicates the API protocol. For extended adv,
    we need at least 'P=0103' (1.3 or newer).
    """
    print("Querying firmware version in text mode...")
    command = "/QFV\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size)
    print("Response (Firmware Version - Text):", response.decode('utf-8', errors='ignore'))


def set_device_name(device_name: str):
    """
    Sets the BLE device name by:
      1) Stopping any current advertising (/AX).
      2) Sending 'SDN,N=<device_name>'.
      3) Optionally re-enabling advertisement (/CA).

    Args:
        device_name (str): The desired name (e.g. "MyDevice").
    """
    print(f"Setting device name to '{device_name}' in text mode...")

    # Stop all legacy advertisings
    send_custom_command_text("/AX")

    # Send the "Set Device Name" command in text mode
    command = f"SDN,N={device_name}"
    send_custom_command_text(command)

    # Re-enable advertising (if you want the new name to be shown
    # in the local GATT Device Name or scan response).
    send_custom_command_text("/CA")


def get_ping():
    """
    Sends a "/PING" command in text mode to verify module communication.
    The response typically includes up-time counters in seconds/fractions.
    """
    print("Querying ping in text mode...")
    command = "/PING\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size)
    print("Response (Ping - Text):", response.decode('utf-8', errors='ignore'))


def reboot_device():
    """
    Reboots the BLE module via the "/RBT" text command.
    All current settings revert unless stored in flash.
    """
    print("Rebooting device in text mode...")
    command = "/RBT\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size)
    print("Response (Reboot - Text):", response.decode('utf-8', errors='ignore'))


def reset_factory():
    """
    Resets the module to factory defaults using the "/RFAC" text command.
    This undoes any persistent (flash-stored) changes,
    then reboots automatically.
    """
    print("Resetting to factory defaults in text mode...")
    command = "/RFAC\r\n"
    ev_kit.write(command.encode())
    response = ev_kit.read(read_buffer_size)
    print("Factory Reset Response (Text):", response.decode('utf-8', errors='ignore'))


def extended_adv_config(P="01", M="01", T="09", H="00", I="00A0", C="07",
                        L="00", O="0000", F="00", A="000000000000",
                        Y="00", E="00", S="00", D="00", N="0018"):
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
    send_custom_command_text(sacp_cmd)

    # Re-enable advertising with new config
    send_custom_command_text("/CA")




def print_extended_parameters():
    """
    Issues "GACP" to display the current extended-adv parameters as
    recognized by the module. The response typically shows:

      P=xx, M=xx, T=xx, H=xx, I=xx, ...

    Letting you confirm if your adv config is set or if it fell back to legacy.
    """
    send_custom_command_text("GACP")









def set_extended_adv_data(
        payload_hex: str,
        erase_or_append: int = 1,
        adv_type: str = "08",
        interval: str = "00A0",
        discovery_mode: str = "00"
):
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
    send_custom_command_text(sead_cmd)

    # 4) Start advertising
    send_custom_command_text("/CA")




def print_extended_adv_data():
    """
    Queries the module's extended advertisement data using the GEAD command in text mode.
    The response typically looks like:
        @R,00xx,GEAD,0000,D=020106... (hex data)
    If there's no data set, 'D=' may be empty.
    """
    print("Querying extended-advertising data (GEAD) in text mode...")
    send_custom_command_text("GEAD")
    # The send_custom_command_text function should read and print
    # whatever the module responds, e.g. "@R,000D,GEAD,0000,D=020106..."









# Main usage example
try:
    # Factory reset the module so we start fresh
    reset_factory()

    # Show firmware version to see if P=01xx means old or new protocol
    get_firmware_version()

    # Try setting the device name (will stop advertising, set name, then /CA)
    set_device_name("HAMED_BLE")

    # Example: configure extended adv with default arguments
    extended_adv_config()



    #Doesn't work due to API protocol ver being 1.1 not higher
    set_extended_adv_data(
        payload_hex="020106FF10FA021122334455",  # your custom bytes
        erase_or_append=0,
        adv_type="08",        # non-scannable
        interval="00A0",      # 100 ms
        discovery_mode="00"   # broadcast-only
    )

    # Print out what the module thinks is set for adv parameters
    print_extended_parameters()


    send_custom_command_text("GEAD")
    # Potentially we could then do SEAD if the firmware truly is 1.3+,
    # but if P=0001 we know it's old so it'd fail with 0x020C.

finally:
    # Make sure we close the serial port on exit
    ev_kit.close()
    print("Connection closed.")
