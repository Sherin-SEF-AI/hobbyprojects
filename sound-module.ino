const int digitalPin = 2;    // Digital pin connection
const int analogPin = A0;    // Analog pin connection
const int ledPin = 13;       // Built-in LED
const int sampleWindow = 50; // Sample window in ms (for better accuracy)
const int threshold = 500;   // Adjust this value based on your needs

// Variables for storing sound data
int maxSound = 0;
int minSound = 1024;
int soundLevel = 0;

void setup() {
  Serial.begin(9600);
  pinMode(digitalPin, INPUT);
  pinMode(ledPin, OUTPUT);
  
  Serial.println("Sound Level Monitor");
  Serial.println("------------------");
}

void loop() {
  // Get more accurate readings over a time window
  unsigned long startMillis = millis();
  maxSound = 0;
  minSound = 1024;
  
  // Collect samples over the window period
  while (millis() - startMillis < sampleWindow) {
    soundLevel = analogRead(analogPin);
    if (soundLevel > maxSound) {
      maxSound = soundLevel;
    }
    if (soundLevel < minSound) {
      minSound = soundLevel;
    }
  }

  // Calculate peak-to-peak amplitude
  int peakToPeak = maxSound - minSound;
  
  // Map to a percentage for easier understanding
  int soundPercentage = map(peakToPeak, 0, 1023, 0, 100);
  
  // Digital reading for sudden loud sounds
  int digitalReading = digitalRead(digitalPin);

  // Visual indication
  if (peakToPeak > threshold) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }

  // Print detailed readings
  Serial.print("Sound Level: ");
  Serial.print(soundPercentage);
  Serial.print("% | Raw: ");
  Serial.print(peakToPeak);
  Serial.print(" | Digital: ");
  Serial.println(digitalReading);

  // Add visual representation
  printGraph(soundPercentage);
  
  delay(100); // Small delay between readings
}

// Function to print a visual graph
void printGraph(int value) {
  Serial.print("[");
  for (int i = 0; i < 50; i++) {
    if (i < value/2) {
      Serial.print("|");
    } else {
      Serial.print(" ");
    }
  }
  Serial.println("]");
}