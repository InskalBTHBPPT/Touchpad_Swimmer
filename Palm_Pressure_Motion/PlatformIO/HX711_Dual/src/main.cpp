/**
 * Dua load cell selalu dibaca. Masing-masing punya SCK sendiri.
 *
 * HX711-1  SCK P0.06 (kuning)   DT P0.08 (hijau)
 * HX711-2  SCK P0.20 (hijau lumut)  DT P0.17 (orange)
 * RATE sudah ditarik ke VCC = 80 SPS. Serial lewat USB, bukan Serial1.
 *
 * Baris data: t_ms,kanal,raw
 * raw = hitungan 24-bit bertanda, kanal A gain 128, belum diubah ke gram.
 */
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>

static const uint8_t SCK_PIN[2] = {PIN_006, PIN_020};
static const uint8_t DT_PIN[2] = {PIN_008, PIN_017};

static const uint32_t SETTLE_MS = 400;

static uint32_t printAfter = 0;

static int32_t readRaw(uint8_t sck, uint8_t dt) {
  uint32_t value = 0;
  noInterrupts();
  for (uint8_t i = 0; i < 24; i++) {
    digitalWrite(sck, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | (uint32_t)digitalRead(dt);
    digitalWrite(sck, LOW);
    delayMicroseconds(1);
  }
  digitalWrite(sck, HIGH);
  delayMicroseconds(1);
  digitalWrite(sck, LOW);
  interrupts();
  delayMicroseconds(1);

  if (value & 0x800000u) {
    value |= 0xFF000000u;
  }
  return (int32_t)value;
}

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && (millis() - t0 < 4000)) {
    delay(10);
  }

  for (uint8_t i = 0; i < 2; i++) {
    pinMode(SCK_PIN[i], OUTPUT);
    pinMode(DT_PIN[i], INPUT_PULLUP);
    digitalWrite(SCK_PIN[i], LOW);
  }

  printAfter = millis() + SETTLE_MS;
  Serial.println(F("HX711 dua kanal, 80 SPS"));
  Serial.println(F("1 = SCK P0.06  DT P0.08"));
  Serial.println(F("2 = SCK P0.20  DT P0.17"));
}

void loop() {
  for (uint8_t i = 0; i < 2; i++) {
    if (digitalRead(DT_PIN[i]) != LOW) {
      continue;
    }
    const int32_t raw = readRaw(SCK_PIN[i], DT_PIN[i]);
    if ((int32_t)(millis() - printAfter) < 0) {
      continue;
    }
    Serial.print(millis());
    Serial.print(',');
    Serial.print(i + 1);
    Serial.print(',');
    Serial.println(raw);
  }
}
