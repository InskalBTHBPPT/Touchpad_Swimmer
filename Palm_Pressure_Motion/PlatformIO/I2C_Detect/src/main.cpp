#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>

// Carrier SuperMini skema 1.1
// SDA P1.04 (silk 104), SCL P1.06 (silk 106), pull-up 10 kΩ di board.
//   U4 LSM6DSOX  SA0 = GND → 0x6A   WHO_AM_I 0x0F = 0x6C
//   U3 LIS3MDL   SA1 = GND → 0x1C   WHO_AM_I 0x0F = 0x3D
//   U2 RV-3032             → 0x51   (ACK saja; tidak ada WHO_AM_I)

static const uint8_t ADDR_LSM6 = 0x6A;
static const uint8_t ADDR_LIS3 = 0x1C;
static const uint8_t ADDR_RTC = 0x51;

static const uint8_t REG_WHO_AM_I = 0x0F;
static const uint8_t WHO_LSM6DSOX = 0x6C;
static const uint8_t WHO_LIS3MDL = 0x3D;

static bool i2cAck(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static bool readReg(uint8_t addr, uint8_t reg, uint8_t *value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom(addr, (uint8_t)1) != 1) {
    return false;
  }
  *value = Wire.read();
  return true;
}

static void printAddr(uint8_t addr) {
  Serial.print(F("0x"));
  if (addr < 0x10) {
    Serial.print('0');
  }
  Serial.print(addr, HEX);
}

static void reportWho(const __FlashStringHelper *name, uint8_t addr, uint8_t expect) {
  Serial.print(name);
  Serial.print(F(" "));
  printAddr(addr);
  Serial.print(F("  "));

  if (!i2cAck(addr)) {
    Serial.println(F("TIDAK ADA"));
    return;
  }

  uint8_t who = 0;
  if (!readReg(addr, REG_WHO_AM_I, &who)) {
    Serial.println(F("ACK, baca WHO_AM_I gagal"));
    return;
  }

  Serial.print(F("WHO=0x"));
  if (who < 0x10) {
    Serial.print('0');
  }
  Serial.print(who, HEX);
  if (who == expect) {
    Serial.println(F("  OK"));
  } else {
    Serial.println(F("  ACK tapi ID tidak cocok"));
  }
}

static void reportRtc() {
  Serial.print(F("U2 RV-3032   "));
  printAddr(ADDR_RTC);
  Serial.print(F("  "));
  if (i2cAck(ADDR_RTC)) {
    Serial.println(F("OK"));
  } else {
    Serial.println(F("TIDAK ADA"));
  }
}

static void scanBus() {
  Serial.println(F("Scan 0x08..0x77:"));
  uint8_t found = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    if (!i2cAck(addr)) {
      continue;
    }
    Serial.print(F("  "));
    printAddr(addr);
    Serial.println();
    found++;
  }
  if (found == 0) {
    Serial.println(F("  (kosong — cek 3V3, SDA/SCL, pull-up)"));
  }
}

static void checkAll() {
  Serial.println();
  Serial.println(F("I2C SDA P1.04  SCL P1.06"));
  reportWho(F("U4 LSM6DSOX"), ADDR_LSM6, WHO_LSM6DSOX);
  reportWho(F("U3 LIS3MDL "), ADDR_LIS3, WHO_LIS3MDL);
  reportRtc();
  scanBus();
  Serial.println(F("Ketik SCAN lalu Enter untuk ulang."));
}

static char lineBuf[32];
static uint8_t lineLen = 0;

static void handleLine(char *line) {
  for (char *p = line; *p; ++p) {
    if (*p >= 'a' && *p <= 'z') {
      *p = (char)(*p - 'a' + 'A');
    }
  }
  if (strcmp(line, "SCAN") == 0 || strcmp(line, "HELP") == 0) {
    checkAll();
    return;
  }
  Serial.println(F("Ketik SCAN"));
}

void setup() {
  Serial.begin(115200);
  const unsigned long start = millis();
  while (!Serial && (millis() - start < 4000)) {
    delay(10);
  }

  Wire.begin();
  Wire.setClock(100000);
  checkAll();
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
}
