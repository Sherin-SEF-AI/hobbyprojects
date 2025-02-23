#include <DHT.h>
#include <Wire.h>
#include <MPU6050.h>

// Pin definitions
#define DHT_PIN 2
#define TRIG_PIN 9
#define ECHO_PIN 10
#define MQ2_PIN A0
#define MQ135_PIN A1

// Initialize sensors
DHT dht(DHT_PIN, DHT11);
MPU6050 mpu;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  dht.begin();
  mpu.initialize();
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  // Read DHT11
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  // Read MQ2 and MQ135
  int mq2_value = analogRead(MQ2_PIN);
  int mq135_value = analogRead(MQ135_PIN);
  
  // Read HC-SR04
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  float distance = pulseIn(ECHO_PIN, HIGH) * 0.034 / 2;
  
  // Read MPU6050
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  
  // Send data as CSV
  Serial.print(temperature); Serial.print(",");
  Serial.print(humidity); Serial.print(",");
  Serial.print(mq2_value); Serial.print(",");
  Serial.print(mq135_value); Serial.print(",");
  Serial.print(distance); Serial.print(",");
  Serial.print(ax); Serial.print(",");
  Serial.print(ay); Serial.print(",");
  Serial.print(az); Serial.print(",");
  Serial.print(gx); Serial.print(",");
  Serial.print(gy); Serial.print(",");
  Serial.println(gz);
  
  delay(1000);
}