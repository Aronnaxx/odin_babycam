import time
import usb.core
import usb.util
import serial
import serial.tools.list_ports

def find_circuit_playground():
    """Find the Circuit Playground Express device."""
    for port in serial.tools.list_ports.comports():
        if "Circuit Playground" in port.description:
            return serial.Serial(port.device, 115200, timeout=1)
    return None

def main():
    print("Looking for Circuit Playground Express...")
    ser = find_circuit_playground()
    if not ser:
        print("Could not find Circuit Playground Express! Is it connected via USB?")
        return

    print("Found Circuit Playground Express! Starting LED test sequence...")
    try:
        while True:
            # Red
            print("Setting LEDs to RED")
            ser.write(b'R')
            time.sleep(1)
            
            # White
            print("Setting LEDs to WHITE")
            ser.write(b'W')
            time.sleep(1)
            
            # Green
            print("Setting LEDs to GREEN")
            ser.write(b'G')
            time.sleep(1)
            
            print("Test sequence complete! Starting over...\n")
            
    except KeyboardInterrupt:
        # Turn off all LEDs when exiting
        print("\nTurning off LEDs...")
        ser.write(b'O')  # O for Off
        ser.close()

if __name__ == "__main__":
    main() 
