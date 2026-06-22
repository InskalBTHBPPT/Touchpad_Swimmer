// Program Receiver LoRa untuk ESP32
// Output format CSV: Waktu(s),Berat(kg),Roll(°),Pitch(°),Baterai(%)

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
  Serial.println("Waktu(s),Berat(kg),Roll(deg),Pitch(deg),Baterai(%)");
  
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
    // Baca data
    String receivedData = "";
    while (LoRa.available()) {
      receivedData += (char)LoRa.read();
    }
    
    // Validasi data sederhana (harus ada 4 koma)
    int commaCount = 0;
    for (int i = 0; i < receivedData.length(); i++) {
      if (receivedData.charAt(i) == ',') commaCount++;
    }
    
    if (commaCount == 4) {
      packetCount++;
      lastReceiveTime = millis();
      
      // Output data langsung dalam format CSV
      Serial.println(receivedData);
      
      // LED berkedip menunjukkan penerimaan data
      digitalWrite(LED_PIN, HIGH);
      delay(50);
      digitalWrite(LED_PIN, LOW);
      
    } else {
      // Jika format salah, tampilkan error
      Serial.print("ERROR: ");
      Serial.println(receivedData);
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
