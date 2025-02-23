// Define pin constants for better code readability
const int BLINK_SENSOR_PIN = 2;  // Eye blink sensor connected to digital pin 2
const int LED_PIN = 13;          // Built-in LED on pin 13

// Variables to track blink state
bool previousBlinkState = false;
bool currentBlinkState = false;

void setup() {
  // Initialize serial communication for debugging
  Serial.begin(9600);
  
  // Configure pin modes
  pinMode(BLINK_SENSOR_PIN, INPUT);  // Set blink sensor pin as input
  pinMode(LED_PIN, OUTPUT);          // Set LED pin as output
  
  Serial.println("Eye Blink Detection System Ready!");
}

void loop() {
  // Read the current state of the blink sensor
  currentBlinkState = digitalRead(BLINK_SENSOR_PIN);
  
  // Check if a blink has occurred (transition from no blink to blink)
  if (currentBlinkState != previousBlinkState) {
    // If we detect a blink
    if (currentBlinkState == HIGH) {
      digitalWrite(LED_PIN, HIGH);  // Turn on LED
      Serial.println("Blink detected!");
      delay(100);  // Small delay to make LED visible
    } else {
      digitalWrite(LED_PIN, LOW);   // Turn off LED
    }
    
    // Update the previous state
    previousBlinkState = currentBlinkState;
  }
  
  // Small delay to prevent reading noise
  delay(50);
}