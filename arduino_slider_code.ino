// This code is specifically for Arduino Leonardo, Micro, or Due
// It uses the hardware serial port (Serial1) on pins 0 (RX) and 1 (TX).

// Analog pin for the slider
#define SLIDER_PIN A0

void setup() {
  // Initialize serial communication for the USB Serial Monitor
  Serial.begin(9600);
  
  // Wait for the serial monitor to open (important for Leonardo)
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }
  
  // Initialize Serial1 for Bluetooth communication (Pins 0 & 1)
  Serial1.begin(9600);
  
  Serial.println("Arduino Leonardo Slider with Bluetooth initialized");
  Serial.println("Using Hardware Serial1 for Bluetooth.");
}

void loop() {
  // Read the slider value (0-1023)
  int raw = analogRead(SLIDER_PIN);
  
  // Convert to percentage (0-100)
  int percentage = map(raw, 0, 1023, 0, 100);
  
  // Create the data string to send
  String dataString = "Raw: " + String(raw) + " => " + String(percentage) + "%";
  
  // Send to the USB Serial Monitor for debugging
  Serial.println(dataString);
  
  // Send to the Bluetooth module via the hardware serial port
  Serial1.println(dataString);
  
  // Small delay
  delay(100);
} 