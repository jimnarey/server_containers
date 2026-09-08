#!/usr/bin/env python3

import serial
import time

# Constants
PORT_A = "/dev/ttyUSB0"
PORT_B = "/dev/ttyACM0"
BAUD_RATE = 115200
MESSAGE_TO_SEND = "F\r\n"
TIMEOUT = 1

def communicate_with_serial_port(port, baudrate, message, timeout):
    """
    Sends a message to a serial port and retrieves the response.

    Args:
        port (str): Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux).
        baudrate (int): Baud rate for the communication.
        message (str): Message to send.
        timeout (int): Timeout for reading the response in seconds.

    Returns:
        str: Response from the serial device.
    """
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            time.sleep(2)
            ser.write(message.encode())
            time.sleep(1)
            response = ser.read_all()
            print(f"Response length: {response}")
            response = response.decode()
            
        return response
    except serial.SerialException as e:
        return f"Error communicating with the serial port: {e}"

if __name__ == "__main__":
    response = communicate_with_serial_port(PORT_A, BAUD_RATE, MESSAGE_TO_SEND, TIMEOUT)
    print(f"Received response: {response}")
    response = communicate_with_serial_port(PORT_B, BAUD_RATE, MESSAGE_TO_SEND, TIMEOUT)
    print(f"Received response: {response}")