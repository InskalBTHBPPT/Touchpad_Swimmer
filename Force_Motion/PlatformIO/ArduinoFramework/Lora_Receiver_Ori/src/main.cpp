#include <Arduino.h>

// Program Receiver LoRa untuk ESP32
// Input: paket biner 12 byte dari Lora_Sender_Ori
// Output format CSV: Waktu(s),Force,Roll(°),Pitch(°),Baterai(%)

#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include "esp_bt.h"

// -------------------- LoRa SX1278 Setup --------------------
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS   5
#define LORA_RST  14
#define LORA_DIO0 26
#define LORA_BAND 433E6  // Frekuensi LoRa

// -------------------- LED Indikator --------------------
#define LED_PIN 2  // LED built-in ESP32

// -------------------- Binary Payload (harus sama dengan sender) --------------------
// Offset  Size  Type      Field
// 0       4     uint32_t  time_ms since start
// 4       2     int16_t   force × 10
// 6       2     int16_t   roll × 10 (degrees)
// 8       2     int16_t   pitch × 10 (degrees, sign inverted as in CSV)
// 10      1     uint8_t   battery %
// 11      1     uint8_t   CRC-8 of bytes 0–10 (poly 0x07)
#define LORA_PAYLOAD_SIZE 12

uint8_t crc8(const uint8_t* data, size_t len) {
  uint8_t crc = 0;
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

bool decodeLoraPayload(const uint8_t* buf, float& time_s, float& force,
                       float& roll, float& pitch, uint8_t& battery) {
  if (crc8(buf, 11) != buf[11]) {
    return false;
  }

  uint32_t time_ms;
  int16_t force_x10;
  int16_t roll_x10;
  int16_t pitch_x10;

  memcpy(&time_ms, &buf[0], sizeof(time_ms));
  memcpy(&force_x10, &buf[4], sizeof(force_x10));
  memcpy(&roll_x10, &buf[6], sizeof(roll_x10));
  memcpy(&pitch_x10, &buf[8], sizeof(pitch_x10));

  time_s = time_ms / 1000.0f;
  force = force_x10 / 10.0f;
  roll = roll_x10 / 10.0f;
  pitch = pitch_x10 / 10.0f;
  battery = buf[10];
  return true;
}

// -------------------- Variabel untuk menyimpan data --------------------
unsigned long packetCount = 0;
unsigned long lastReceiveTime = 0;

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  delay(1000);

  // LED Indikator
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Matikan WiFi dan Bluetooth untuk mengurangi interferensi
  WiFi.mode(WIFI_OFF);
  btStop();
  Serial.println("WiFi & Bluetooth dimatikan.");

  // Inisialisasi LoRa
  Serial.println("Inisialisasi LoRa Receiver...");
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  
  if (!LoRa.begin(LORA_BAND)) {
    Serial.println("Gagal inisialisasi LoRa!");
    Serial.println("Periksa koneksi dan konfigurasi pin.");
    while (1) {
      digitalWrite(LED_PIN, HIGH);
      delay(500);
      digitalWrite(LED_PIN, LOW);
      delay(500);
    }
  }
  
  Serial.println("LoRa Receiver Siap!");
  Serial.println("Frekuensi: " + String(LORA_BAND/1000000) + " MHz");
  
  // Cetak header CSV
  Serial.println("Waktu(s),Force,Roll(deg),Pitch(deg),Baterai(%)");
  
  // LED berkedip cepat menandakan siap
  for(int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
}

// -------------------- Loop --------------------
void loop() {
  // Cek apakah ada paket LoRa yang masuk
  int packetSize = LoRa.parsePacket();
  
  if (packetSize) {
    if (packetSize != LORA_PAYLOAD_SIZE) {
      Serial.print("ERROR: ukuran paket ");
      Serial.print(packetSize);
      Serial.println(" byte (diharapkan 12)");
      while (LoRa.available()) {
        LoRa.read();
      }
    } else {
      uint8_t buf[LORA_PAYLOAD_SIZE];
      int bytesRead = LoRa.readBytes(buf, LORA_PAYLOAD_SIZE);
      if (bytesRead != LORA_PAYLOAD_SIZE) {
        Serial.println("ERROR: pembacaan paket tidak lengkap");
      } else {
        float time_s;
        float force;
        float roll;
        float pitch;
        uint8_t battery;

        if (decodeLoraPayload(buf, time_s, force, roll, pitch, battery)) {
          packetCount++;
          lastReceiveTime = millis();

          char line[48];
          snprintf(line, sizeof(line), "%.2f,%.1f,%.1f,%.1f,%u",
                   time_s, force, roll, pitch, battery);
          Serial.println(line);

          digitalWrite(LED_PIN, HIGH);
          delay(50);
          digitalWrite(LED_PIN, LOW);
        } else {
          Serial.println("ERROR: CRC tidak valid");
        }
      }
    }
  }
  
  // Cek timeout - jika tidak ada data dalam 5 detik
  if (millis() - lastReceiveTime > 5000 && packetCount > 0) {
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
      lastBlink = millis();
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }
  }
  
  // Tampilkan status setiap 10 detik jika tidak ada data
  static unsigned long lastStatusTime = 0;
  if (millis() - lastStatusTime > 10000) {
    lastStatusTime = millis();
    if (packetCount == 0) {
      Serial.println("Menunggu data dari transmitter...");
    }
  }
  
  delay(10);
}
