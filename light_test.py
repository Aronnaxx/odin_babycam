import time
from adafruit_circuitplayground import cp

def set_all_pixels(color):
    """Set all 10 NeoPixels to the specified color."""
    for i in range(10):
        cp.pixels[i] = color
    time.sleep(1)  # Keep the color visible for 1 second

def main():
    print("Starting LED test sequence...")
    try:
        while True:
            # Red
            print("Setting LEDs to RED")
            set_all_pixels((255, 0, 0))
            
            # White
            print("Setting LEDs to WHITE")
            set_all_pixels((255, 255, 255))
            
            # Green
            print("Setting LEDs to GREEN")
            set_all_pixels((0, 255, 0))
            
            print("Test sequence complete! Starting over...\n")
            
    except KeyboardInterrupt:
        # Turn off all LEDs when exiting
        print("\nTurning off LEDs...")
        for i in range(10):
            cp.pixels[i] = (0, 0, 0)

if __name__ == "__main__":
    main() 
