// Arduino code with TinyML model
#include <DHT.h>
#include <Environment_Inferencing.h>  // This will be your exported Edge Impulse library

#define DHT_PIN 2
DHT dht(DHT_PIN, DHT11);

// Buffer for the features
float features[2];  // [temperature, humidity]

void setup() {
    Serial.begin(9600);
    dht.begin();
}

void loop() {
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    
    if (!isnan(humidity) && !isnan(temperature)) {
        // Prepare the feature array
        features[0] = temperature;
        features[1] = humidity;
        
        // Run inference
        ei_impulse_result_t result;
        ei_impulse_result_classification_t classification;
        
        // Make prediction
        run_classifier(features, 2, &result, &classification);
        
        // Send data to Python application
        Serial.print(temperature);
        Serial.print(",");
        Serial.print(humidity);
        Serial.print(",");
        Serial.println(result.anomaly);  // Add anomaly score to our output
    }
    delay(1000);
}