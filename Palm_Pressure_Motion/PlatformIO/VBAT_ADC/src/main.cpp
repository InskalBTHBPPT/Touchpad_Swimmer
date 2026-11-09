#include <Arduino.h>
#include <Adafruit_TinyUSB.h>

// Carrier skema 1.1:
//   Bat(+) — R5 1 MΩ — P0.31 — R6 1 MΩ — AGND
//   C4 100 nF paralel R6.
// Pembagi 1:2 → V_bat = V_pin * 2.
// Adafruit nRF52 SAADC: referensi internal 0,6 V, gain 1/6 → penuh skala 3,6 V di pin.

static const uint8_t PIN_VBAT = PIN_031;
static const int kAdcBits = 12;
static const int kAdcMax = (1 << kAdcBits) - 1;
static const float kPinFullScaleV = 3.6f;
static const float kDivider = 2.0f;
// Kalibrasi vs DMM Siglent di B+ (USB terpasang), dua baterai:
//   4,154 V → firmware mentah 4,299 V;  4,102 V → firmware mentah 4,190 V.
// Faktor = rata-rata (Vmeter / Vfirmware) = 0,9726.
static const float kCal = 0.9726f;
static const int kAvgCount = 16;
static const unsigned long kPrintMs = 1000;
static const float kBatMinV = 2.50f;
static const float kBatMaxV = 4.50f;

struct Reading {
  uint32_t raw;
  float vPin;
  float vBat;
  float vVddh;
};

static uint32_t readRawOnce() {
  return (uint32_t)analogRead(PIN_VBAT);
}

static float pinVolts(uint32_t raw) {
  return (raw * kPinFullScaleV) / (float)kAdcMax;
}

static float readVddh() {
  // Input SAADC sudah VDDH/5.
  const uint32_t raw = analogReadVDDHDIV5();
  return pinVolts(raw) * 5.0f;
}

static Reading takeReading() {
  uint32_t sum = 0;
  for (int i = 0; i < kAvgCount; i++) {
    sum += readRawOnce();
    delay(2);
  }
  Reading r;
  r.raw = (sum + (kAvgCount / 2)) / (uint32_t)kAvgCount;
  r.vPin = pinVolts(r.raw);
  r.vBat = r.vPin * kDivider * kCal;
  r.vVddh = readVddh();
  return r;
}

static void printReading(const Reading &r) {
  Serial.print(F("RAW "));
  Serial.print(r.raw);
  Serial.print(F("  Vpin "));
  Serial.print(r.vPin, 3);
  Serial.print(F(" V  Vbat "));
  Serial.print(r.vBat, 3);
  Serial.print(F(" V  VDDH "));
  Serial.print(r.vVddh, 3);
  Serial.println(F(" V"));
}

static void printHelp() {
  Serial.println();
  Serial.println(F("VBAT ADC  P0.31  R5/R6=1M/1M  x2  cal=0.9726"));
  Serial.println(F("Perintah (Serial 115200, akhiri Enter):"));
  Serial.println(F("  NOW    cetak sekali"));
  Serial.println(F("  TEST   rata-rata 16 sampel dan vonis"));
  Serial.println(F("  HELP"));
  Serial.println();
}

static bool runTest() {
  Serial.println();
  Serial.println(F("VBAT SENSE  pin=P0.31  divider=x2  cal=0.9726  ADC=12bit/3.6V"));
  const Reading r = takeReading();
  printReading(r);

  const bool pass = (r.vBat >= kBatMinV) && (r.vBat <= kBatMaxV);
  if (pass) {
    Serial.println(F("TEST OK"));
  } else if (r.vBat < kBatMinV) {
    Serial.println(F("TEST GAGAL  Vbat terlalu rendah (baterai kosong / tidak terhubung?)"));
  } else {
    Serial.println(F("TEST GAGAL  Vbat di luar rentang 2.5..4.5 V"));
  }
  return pass;
}

static char lineBuf[16];
static uint8_t lineLen = 0;
static unsigned long lastPrintMs = 0;

static void handleLine(char *line) {
  for (char *p = line; *p; ++p) {
    if (*p >= 'a' && *p <= 'z') {
      *p = (char)(*p - 'a' + 'A');
    }
  }
  if (strcmp(line, "NOW") == 0) {
    printReading(takeReading());
    return;
  }
  if (strcmp(line, "TEST") == 0) {
    runTest();
    return;
  }
  if (strcmp(line, "HELP") == 0) {
    printHelp();
    return;
  }
  Serial.println(F("Ketik NOW / TEST / HELP"));
}

void setup() {
  Serial.begin(115200);
  const unsigned long start = millis();
  while (!Serial && (millis() - start < 4000)) {
    delay(10);
  }

  Serial.println(F("VBAT ADC boot 1.1.1"));
  analogReadResolution(kAdcBits);
  printHelp();
  runTest();
  lastPrintMs = millis();
}

void loop() {
  while (Serial.available() > 0) {
    const int c = Serial.read();
    if (c < 0) {
      break;
    }
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
      continue;
    }
    if (lineLen + 1U < sizeof(lineBuf)) {
      lineBuf[lineLen++] = (char)c;
    }
  }

  if ((millis() - lastPrintMs) < kPrintMs) {
    return;
  }
  lastPrintMs = millis();
  printReading(takeReading());
}
