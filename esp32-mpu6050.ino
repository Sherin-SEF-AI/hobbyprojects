#include <Wire.h>

// MPU6050 Registers and Address
#define MPU6050_ADDR    0x68
#define ACCEL_XOUT_H    0x3B
#define GYRO_XOUT_H     0x43
#define TEMP_OUT_H      0x41
#define PWR_MGMT_1      0x6B
#define CONFIG          0x1A
#define GYRO_CONFIG     0x1B
#define ACCEL_CONFIG    0x1C
#define FIFO_EN         0x23
#define INT_ENABLE      0x38
#define INT_STATUS      0x3A
#define USER_CTRL       0x6A
#define MOT_THR         0x1F  
#define MOT_DUR         0x20  
#define MOT_DETECT_CTRL 0x69  

// LED Pin
#define LED_PIN         2

// Sensor variables
float accelX, accelY, accelZ;
float gyroX, gyroY, gyroZ;
float temperature;
float roll, pitch, yaw;

// Calibration offsets
float accelXoffset = 0;
float accelYoffset = 0;
float accelZoffset = 0;
float gyroXoffset = 0;
float gyroYoffset = 0;
float gyroZoffset = 0;

// Timing variables
unsigned long lastReadTime = 0;
float deltaTime = 0;

// Filter coefficients
float alpha = 0.96;
float rollFilter = 0;
float pitchFilter = 0;

void setup() {
  Wire.begin(21, 22); // SDA = 21, SCL = 22
  Serial.begin(115200);
  
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  initMPU6050();
  delay(1000); // Wait for sensor to stabilize
  calibrateSensors();
  
  Serial.println("MPU6050 Ready!");
}

void initMPU6050() {
  // Wake up MPU6050
  writeMPU6050Register(PWR_MGMT_1, 0x00);
  delay(100);
  
  // Configure gyroscope (±250 deg/s)
  writeMPU6050Register(GYRO_CONFIG, 0x00);
  
  // Configure accelerometer (±2g)
  writeMPU6050Register(ACCEL_CONFIG, 0x00);
  
  // Set Digital Low Pass Filter
  writeMPU6050Register(CONFIG, 0x03);
  
  // Configure motion detection
  writeMPU6050Register(MOT_THR, 20);
  writeMPU6050Register(MOT_DUR, 20);
  writeMPU6050Register(MOT_DETECT_CTRL, 0x15);
  writeMPU6050Register(INT_ENABLE, 0x40);
}

void writeMPU6050Register(byte reg, byte data) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission(true);
}

byte readMPU6050Register(byte reg) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU6050_ADDR, 1, true);
  return Wire.read();
}

void calibrateSensors() {
  Serial.println("Calibrating sensors...");
  digitalWrite(LED_PIN, HIGH);
  
  float sumAccelX = 0, sumAccelY = 0, sumAccelZ = 0;
  float sumGyroX = 0, sumGyroY = 0, sumGyroZ = 0;
  
  // Take multiple readings for calibration
  for(int i = 0; i < 100; i++) {
    readRawData();
    sumAccelX += accelX;
    sumAccelY += accelY;
    sumAccelZ += accelZ;
    sumGyroX += gyroX;
    sumGyroY += gyroY;
    sumGyroZ += gyroZ;
    delay(10);
  }
  
  // Calculate offsets
  accelXoffset = sumAccelX / 100.0;
  accelYoffset = sumAccelY / 100.0;
  accelZoffset = (sumAccelZ / 100.0) - 1.0; // Account for gravity
  gyroXoffset = sumGyroX / 100.0;
  gyroYoffset = sumGyroY / 100.0;
  gyroZoffset = sumGyroZ / 100.0;
  
  digitalWrite(LED_PIN, LOW);
  Serial.println("Calibration complete!");
}

void readRawData() {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU6050_ADDR, 14, true);
  
  // Read accelerometer data
  int16_t accelXraw = Wire.read() << 8 | Wire.read();
  int16_t accelYraw = Wire.read() << 8 | Wire.read();
  int16_t accelZraw = Wire.read() << 8 | Wire.read();
  
  // Read temperature
  int16_t tempRaw = Wire.read() << 8 | Wire.read();
  
  // Read gyroscope data
  int16_t gyroXraw = Wire.read() << 8 | Wire.read();
  int16_t gyroYraw = Wire.read() << 8 | Wire.read();
  int16_t gyroZraw = Wire.read() << 8 | Wire.read();
  
  // Convert raw values to physical units
  accelX = accelXraw / 16384.0;
  accelY = accelYraw / 16384.0;
  accelZ = accelZraw / 16384.0;
  
  gyroX = gyroXraw / 131.0;
  gyroY = gyroYraw / 131.0;
  gyroZ = gyroZraw / 131.0;
  
  temperature = tempRaw / 340.0 + 36.53;
}

void calculateOrientation() {
  unsigned long currentTime = millis();
  deltaTime = (currentTime - lastReadTime) / 1000.0;
  lastReadTime = currentTime;
  
  // Calculate pitch and roll from accelerometer data
  float accelRoll = atan2(accelY, accelZ) * 180.0 / PI;
  float accelPitch = atan2(-accelX, sqrt(accelY * accelY + accelZ * accelZ)) * 180.0 / PI;
  
  // Complementary filter
  rollFilter = alpha * (rollFilter + gyroX * deltaTime) + (1 - alpha) * accelRoll;
  pitchFilter = alpha * (pitchFilter + gyroY * deltaTime) + (1 - alpha) * accelPitch;
  
  roll = rollFilter;
  pitch = pitchFilter;
  yaw += gyroZ * deltaTime;
}

bool checkMotion() {
  byte intStatus = readMPU6050Register(INT_STATUS);
  return (intStatus & 0x40) != 0;
}

void loop() {
  readRawData();
  calculateOrientation();
  bool motionDetected = checkMotion();
  
  digitalWrite(LED_PIN, motionDetected);

  // First print debug data to see raw values
  Serial.println("\nDebug Data:");
  Serial.printf("Accel Raw: X=%d Y=%d Z=%d\n", accelX, accelY, accelZ);
  Serial.printf("Gyro Raw: X=%d Y=%d Z=%d\n", gyroX, gyroY, gyroZ);
  
  // Then send formatted data for Python
  Serial.print("DATA:");
  Serial.print(accelX, 2); Serial.print(",");
  Serial.print(accelY, 2); Serial.print(",");
  Serial.print(accelZ, 2); Serial.print(",");
  Serial.print(gyroX, 2); Serial.print(",");
  Serial.print(gyroY, 2); Serial.print(",");
  Serial.print(gyroZ, 2); Serial.print(",");
  Serial.print(roll, 2); Serial.print(",");
  Serial.print(pitch, 2); Serial.print(",");
  Serial.print(temperature, 2); Serial.print(",");
  Serial.println(motionDetected ? "1" : "0");
  
  delay(100);
}