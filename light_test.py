import RPi.GPIO as GPIO
import time

# Use BCM GPIO references instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define the GPIO pin we'll use (GPIO18 - pin 12)
LED_PIN = 18

# Set up the GPIO pin as output
GPIO.setup(LED_PIN, GPIO.OUT)

def main():
    print("Starting LED test sequence...")
    try:
        while True:
            # Turn LED on
            print("LED ON")
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(1)
            
            # Turn LED off
            print("LED OFF")
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nCleaning up...")
    finally:
        GPIO.cleanup()  # Clean up GPIO on exit

if __name__ == "__main__":
    main() 
