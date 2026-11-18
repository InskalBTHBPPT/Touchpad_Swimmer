/**
 * Cek satu load cell. Perintah USB memilih chip, yang lain di-power-down.
 *
 * HX711-1  SCK P0.06 (kuning)   DT P0.08 (hijau)
 * HX711-2  SCK P0.20 (hijau lumut)  DT P0.17 (orange)
 * RATE sudah ditarik ke VCC = 80 SPS. Serial lewat USB, bukan Serial1.
 *
 * Baris data: t_ms,raw
 * raw = hitungan 24-bit bertanda, kanal A gain 128, belum diubah ke gram.
 */
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>

static const uint8_t SCK_PIN[2] = {PIN_006, PIN_020};
static const uint8_t DT_PIN[2] = {PIN_008, PIN_017};

static const uint32_t SETTLE_MS = 400;

static uint8_t active = 0;
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

static void powerDown(uint8_t sck) {
  digitalWrite(sck, HIGH);
  delayMicroseconds(80);
}

static void selectChannel(uint8_t index) {
  powerDown(SCK_PIN[0]);
  powerDown(SCK_PIN[1]);
  active = index;
  digitalWrite(SCK_PIN[active], LOW);
  printAfter = millis() + SETTLE_MS;
  Serial.print(F("ch,"));
  Serial.println(active + 1);
}

static void pollCommand() {
  while (Serial.available() > 0) {
    const int c = Serial.read();
    if (c == '1') {
      selectChannel(0);
    } else if (c == '2') {
      selectChannel(1);
    }
  }
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
    digitalWrite(SCK_PIN[i], HIGH);
  }
  delayMicroseconds(80);

  Serial.println(F("HX711 satu kanal, 80 SPS"));
  Serial.println(F("1 = HX711-1  SCK P0.06  DT P0.08"));
  Serial.println(F("2 = HX711-2  SCK P0.20  DT P0.17"));
  selectChannel(0);
}

void loop() {
  pollCommand();

  const uint8_t sck = SCK_PIN[active];
  const uint8_t dt = DT_PIN[active];
  if (digitalRead(dt) != LOW) {
    return;
  }

  const int32_t raw = readRaw(sck, dt);
  if ((int32_t)(millis() - printAfter) < 0) {
    return;
  }

  Serial.print(millis());
  Serial.print(',');
  Serial.println(raw);
}
