/**
 * @file main.cpp
 * @brief Node pengirim LoRa untuk monitoring perenang (Swimmer Monitoring).
 *
 * Membaca load cell (HX711), IMU (WT61PC), dan level baterai, lalu mengirim
 * telemetri via LoRa SX1278 (433 MHz) dalam format paket biner 12 byte.
 *
 * Hardware:
 *   - HX711:    DOUT=32, SCK=33
 *   - WT61PC:   UART2 RX=16, TX=17 @ 115200 baud, 50 Hz
 *   - LoRa:     SPI SCK=18, MISO=19, MOSI=23, SS=5, RST=14, DIO0=26
 *   - Baterai:  ADC GPIO 12 (voltage divider)
 *
 * Sampling: ~50 Hz (50 ms) saat data IMU tersedia; baterai di-update 1 Hz.
 *
 * Debug Serial (115200): CSV `waktu,force,roll,pitch,baterai%`
 *
 * @see Lora_Receiver_Ori untuk format paket dan decode di sisi penerima.
 */

#include <Arduino.h>
#include "HX711.h"
#include <DFRobot_WT61PC.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include "esp_bt.h"

// -------------------- HX711 Setup --------------------
const int HX711_DOUT_PIN = 32;
const int HX711_SCK_PIN = 33;
#define CALIBRATION_A -434077
HX711 scale;

// -------------------- WT61PC Setup --------------------
#define SEN_RX 16
#define SEN_TX 17
HardwareSerial SENSerial(2);  // UART2 pada ESP32
DFRobot_WT61PC wt61pc(&SENSerial);

// -------------------- LoRa SX1278 Setup --------------------
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS   5
#define LORA_RST  14
#define LORA_DIO0 26
#define LORA_BAND 433E6  // Frekuensi LoRa

// -------------------- Battery Monitoring --------------------
const int analogPin = 12;
//const float R1 = 9860.0;
//const float R2 = 9860.0;
const float R1 = 100600.0;
const float R2 = 100600.0;
const float refVoltage = 3.3;
const int adcMax = 4095;
const int numPoints = 21;
float voltageTable[numPoints] = {
  4.20, 4.15, 4.11, 4.08, 4.02, 3.98, 3.95, 3.91, 3.87, 3.85,
  3.84, 3.82, 3.80, 3.78, 3.75, 3.73, 3.71, 3.69, 3.61, 3.50, 3.00
};
int percentTable[numPoints] = {
  100, 95, 90, 85, 80, 75, 70, 65, 60, 55,
   50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0
};

// -------------------- Waktu --------------------
unsigned long startTime;
unsigned long lastReadTime = 0;
const int sampleInterval = 50;  // 50Hz sampling

// -------------------- Fungsi Normalisasi --------------------

/**
 * @brief Normalisasi sudut ke rentang [-180°, 180°].
 * @param angle Sudut dalam derajat.
 * @return Sudut ternormalisasi.
 */
float normalizeAngle(float angle) {  while (angle > 180.0) angle -= 360.0;
  while (angle < -180.0) angle += 360.0;
  return angle;
}

// -------------------- Estimasi Persentase Baterai --------------------

/**
 * @brief Interpolasi linear persentase baterai LiPo dari tegangan.
 * @param voltage Tegangan baterai setelah voltage divider (V).
 * @return Persentase 0–100.
 */
float estimatePercentage(float voltage) {  if (voltage >= voltageTable[0]) return 100.0;
  if (voltage <= voltageTable[numPoints - 1]) return 0.0;

  for (int i = 0; i < numPoints - 1; i++) {
    if (voltage >= voltageTable[i + 1]) {
      float v1 = voltageTable[i];
      float v2 = voltageTable[i + 1];
      int p1 = percentTable[i];
      int p2 = percentTable[i + 1];
      float slope = (p2 - p1) / (v2 - v1);
      return p1 + slope * (voltage - v1);
    }
  }
  return 0.0;
}

#define BATTERY_AVG_SAMPLES 10
float batteryBuffer[BATTERY_AVG_SAMPLES];
int batteryIndex = 0;
bool bufferFilled = false;

/**
 * @brief Rata-rata bergerak tegangan baterai (10 sampel).
 * @param newSample Sampel tegangan terbaru (V).
 * @return Rata-rata tegangan.
 */
float getAverageBatteryVoltage(float newSample) {  batteryBuffer[batteryIndex] = newSample;
  batteryIndex = (batteryIndex + 1) % BATTERY_AVG_SAMPLES;
  if (batteryIndex == 0) bufferFilled = true;

  int samplesToAverage = bufferFilled ? BATTERY_AVG_SAMPLES : batteryIndex;
  float sum = 0.0;
  for (int i = 0; i < samplesToAverage; i++) {
    sum += batteryBuffer[i];
  }
  return sum / samplesToAverage;
}

// -------------------- LoRa Binary Payload (12 byte, little-endian) --------------------
// Offset  Size  Type      Field
// 0       4     uint32_t  time_ms since start
// 4       2     int16_t   force × 10
// 6       2     int16_t   roll × 10 (degrees)
// 8       2     int16_t   pitch × 10 (degrees, sign inverted as in CSV)
// 10      1     uint8_t   battery %
// 11      1     uint8_t   CRC-8 of bytes 0–10 (poly 0x07)
#define LORA_PAYLOAD_SIZE 12

/**
 * @brief Hitung CRC-8 (polynomial 0x07) untuk validasi paket LoRa.
 * @param data Buffer data.
 * @param len  Panjang byte yang di-CRC.
 * @return Nilai CRC-8.
 */
uint8_t crc8(const uint8_t* data, size_t len) {  uint8_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; bit++) {
      if (crc & 0x80) {
        crc = (uint8_t)((crc << 1) ^ 0x07);
      } else {
        crc <<= 1;
      }
    }
  }
  return crc;
}

/**
 * @brief Susun paket LoRa biner 12 byte (little-endian).
 *
 * Layout: time_ms(4) | force×10(2) | roll×10(2) | pitch×10(2) | bat%(1) | crc8(1)
 * Pitch disimpan dengan tanda dibalik (sama seperti output CSV).
 *
 * @param buf     Buffer keluaran, minimal 12 byte.
 * @param time_ms Waktu sejak start (ms).
 * @param force   Gaya hasil konversi load cell.
 * @param roll    Roll IMU (derajat).
 * @param pitch   Pitch IMU mentah (derajat, sebelum inversi tanda).
 * @param battery Persentase baterai 0–100.
 */
void buildLoraPayload(uint8_t* buf, uint32_t time_ms, float force, float roll,
                      float pitch, uint8_t battery) {  int16_t force_x10 = (int16_t)lroundf(force * 10.0f);
  int16_t roll_x10 = (int16_t)lroundf(roll * 10.0f);
  int16_t pitch_x10 = (int16_t)lroundf(pitch * -10.0f);

  memcpy(&buf[0], &time_ms, sizeof(time_ms));
  memcpy(&buf[4], &force_x10, sizeof(force_x10));
  memcpy(&buf[6], &roll_x10, sizeof(roll_x10));
  memcpy(&buf[8], &pitch_x10, sizeof(pitch_x10));
  buf[10] = battery;
  buf[11] = crc8(buf, 11);
}

// -------------------- Variabel Baru --------------------
unsigned long lastBatteryTime = 0;
int lastBatteryPercent = 100; // Inisialisasi awal

/** @brief Inisialisasi sensor, LoRa, dan timer sampling. */
void setup() {  Serial.begin(115200);
  delay(1000);

  // Matikan WiFi dan Bluetooth
  WiFi.mode(WIFI_OFF);
  btStop();
  Serial.println("WiFi & Bluetooth dimatikan.");

  // Sensor WT61PC
  SENSerial.begin(115200, SERIAL_8N1, SEN_RX, SEN_TX);
  wt61pc.modifyFrequency(FREQUENCY_50HZ);

  // HX711
  scale.begin(HX711_DOUT_PIN, HX711_SCK_PIN);
  scale.set_scale(CALIBRATION_A);
  //scale.set_scale(1);
  scale.tare();

  // Battery monitoring
  analogReadResolution(12);

  // LoRa
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  if (!LoRa.begin(LORA_BAND)) {
    Serial.println("Gagal inisialisasi LoRa");
    while (1);
  }
  Serial.println("LoRa Siap!");

  // Timer
  startTime = millis();
  //Serial.println("Waktu(s),Berat(g),Roll(°),Pitch(°),Baterai(%)");
}

/**
 * @brief Loop utama: update baterai 1 Hz, sampling sensor ~50 Hz, kirim LoRa.
 *
 * Pengiriman hanya saat wt61pc.available(). Force = 5.4315 × (berat × −1).
 */
void loop() {  unsigned long currentTime = millis();

  // 1. Logika Update Baterai (Setiap 1000ms / 1 detik)
  if (currentTime - lastBatteryTime >= 1000) {
    lastBatteryTime = currentTime;
    
    int rawADC = analogRead(analogPin);
    float voltageADC = ((rawADC * refVoltage) / adcMax) + 0.17;
    float rawVoltage = voltageADC * ((R1 + R2) / R2);
    float batteryVoltage = getAverageBatteryVoltage(rawVoltage);
    
    // Konversi ke int (bilangan bulat)
    lastBatteryPercent = (int)estimatePercentage(batteryVoltage);
  }

  // 2. Logika Utama (50Hz / 50ms)
  if (currentTime - lastReadTime >= sampleInterval) {
    lastReadTime = currentTime;

    if (wt61pc.available()) {
      float roll = normalizeAngle(wt61pc.Angle.X);
      float pitch = normalizeAngle(wt61pc.Angle.Y);
      //float yaw = normalizeAngle(wt61pc.Angle.Z);

      float berat = scale.get_units(1);
      float force = 5.4315 * (berat * -1);

      uint8_t payload[LORA_PAYLOAD_SIZE];
      uint32_t time_ms = (uint32_t)(currentTime - startTime);
      buildLoraPayload(payload, time_ms, force, roll, pitch,
                       (uint8_t)lastBatteryPercent);

      LoRa.beginPacket();
      LoRa.write(payload, LORA_PAYLOAD_SIZE);
      LoRa.endPacket();

      char debugLine[48];
      snprintf(debugLine, sizeof(debugLine), "%.2f,%.1f,%.1f,%.1f,%u",
               time_ms / 1000.0f, force, roll, pitch * (-1.0f),
               (unsigned)lastBatteryPercent);
      Serial.println(debugLine);
    }
  }
}
