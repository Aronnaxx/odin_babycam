#include <Adafruit_CircuitPlayground.h>

void setup() {
  // Initialize Circuit Playground
  CircuitPlayground.begin();
  
  // Start serial communication
  Serial.begin(115200);
  
  // Set initial brightness (30%)
  CircuitPlayground.setBrightness(30);
  
  // Turn off all pixels initially
  for(int i=0; i<10; i++) {
    CircuitPlayground.setPixelColor(i, 0);
  }
}

void setAllPixels(uint32_t color) {
  for(int i=0; i<10; i++) {
    CircuitPlayground.setPixelColor(i, color);
  }
  CircuitPlayground.show();  // Update the pixels
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    switch(cmd) {
      case 'R':  // Red
        setAllPixels(0xFF0000);
        break;
      case 'W':  // White
        setAllPixels(0xFFFFFF);
        break;
      case 'G':  // Green
        setAllPixels(0x00FF00);
        break;
      case 'O':  // Off
        setAllPixels(0x000000);
        break;
    }
  }
} 
