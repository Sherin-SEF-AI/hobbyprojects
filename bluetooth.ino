#define BLYNK_TEMPLATE_ID "YOUR_TEMPLATE_ID"
#define BLYNK_TEMPLATE_NAME "YOUR_TEMPLATE_NAME"
#define BLYNK_AUTH_TOKEN "YOUR_AUTH_TOKEN"

#include <BlynkSimpleSerialBLE.h>
#include <SoftwareSerial.h>
#include <DHT.h>

// Define pins for DHT11 and HC-05
#define DHTPIN 2
#define DHTTYPE DHT11
#define BT_RX 10
#define BT_TX 11

// Initialize DHT sensor and Bluetooth serial communication
DHT dht(DHTPIN, DHTTYPE);
SoftwareSerial bluetoothSerial(BT_RX, BT_TX);

// Virtual pins for Blynk
#define VPIN_TEMPERATURE V5    // Virtual pin for temperature
#define VPIN_HUMIDITY V6       // Virtual pin for humidity

void setup() {
    // Initialize serial communication for debugging
    Serial.begin(9600);
    
    // Initialize Bluetooth communication
    bluetoothSerial.begin(9600);
    
    // Start the DHT sensor
    dht.begin();
    
    // Connect to Blynk
    Blynk.begin(bluetoothSerial, BLYNK_AUTH_TOKEN);
    
    Serial.println("Setup complete");
}

void loop() {
    Blynk.run();
    
    // Read and send sensor data every 2 seconds
    static unsigned long lastRead = 0;
    if (millis() - lastRead >= 2000) {
        // Read sensor values
        float humidity = dht.readHumidity();
        float temperature = dht.readTemperature();
        
        // Check if readings are valid
        if (!isnan(humidity) && !isnan(temperature)) {
            // Send data to Blynk
            Blynk.virtualWrite(VPIN_TEMPERATURE, temperature);
            Blynk.virtualWrite(VPIN_HUMIDITY, humidity);
            
            // Print values for debugging
            Serial.print("Temperature: ");
            Serial.print(temperature);
            Serial.print("°C, Humidity: ");
            Serial.println(humidity);
        } else {
            Serial.println("Failed to read from DHT sensor!");
        }
        
        lastRead = millis();
    }
}