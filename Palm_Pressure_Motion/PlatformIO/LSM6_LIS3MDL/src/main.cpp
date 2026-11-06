#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <math.h>

// Carrier skema 1.1: SDA P1.04, SCL P1.06, pull-up 10 kΩ di board.
//   U4 LSM6DSOX  SA0 = GND → 0x6A   WHO_AM_I 0x0F = 0x6C
//   U3 LIS3MDL   SA1 = GND → 0x1C   WHO_AM_I 0x0F = 0x3D
// INT1 (P0.11) dan DRDY (P0.12) tidak dipakai. Data diambil dengan polling.

static const uint8_t ADDR_LSM6 = 0x6A;
static const uint8_t ADDR_LIS3 = 0x1C;
static const uint8_t REG_WHO_AM_I = 0x0F;
static const uint8_t WHO_LSM6DSOX = 0x6C;
static const uint8_t WHO_LIS3MDL = 0x3D;

// LSM6DSOX, datasheet DS12814.
static const uint8_t LSM6_CTRL1_XL = 0x10;
static const uint8_t LSM6_CTRL2_G = 0x11;
static const uint8_t LSM6_CTRL3_C = 0x12;
static const uint8_t LSM6_STATUS = 0x1E;
static const uint8_t LSM6_OUTX_L_G = 0x22;
static const uint8_t LSM6_CTRL3_BDU_IFINC = 0x44;
static const uint8_t LSM6_ODR_104_FS_2G = 0x40;
static const uint8_t LSM6_ODR_104_FS_250 = 0x40;
static const float LSM6_ACCEL_G_PER_LSB = 0.000061f;
static const float LSM6_GYRO_DPS_PER_LSB = 0.00875f;

// LIS3MDL, datasheet DocID024204. Bit 7 alamat = auto-increment.
static const uint8_t LIS3_CTRL1 = 0x20;
static const uint8_t LIS3_CTRL2 = 0x21;
static const uint8_t LIS3_CTRL3 = 0x22;
static const uint8_t LIS3_CTRL4 = 0x23;
static const uint8_t LIS3_CTRL5 = 0x24;
static const uint8_t LIS3_STATUS = 0x27;
static const uint8_t LIS3_OUT_X_L = 0x28;
// FAST_ODR + ultra-high performance = 155 Hz. Tidak ada ODR tepat 100 Hz.
static const uint8_t LIS3_CTRL1_155HZ_UHP = 0x72;
static const uint8_t LIS3_CTRL2_SOFT_RST = 0x04;
static const uint8_t LIS3_CTRL3_CONTINUOUS = 0x00;
static const uint8_t LIS3_CTRL4_Z_UHP = 0x0C;
static const uint8_t LIS3_CTRL5_BDU = 0x40;
static const float LIS3_GAUSS_PER_LSB = 1.0f / 6842.0f;

static const int kSamples = 8;
static const unsigned long kLiveMs = 10;
static const float kAccelMinG = 0.70f;
static const float kAccelMaxG = 1.30f;
static const float kGyroMaxDps = 20.0f;
static const float kMagMinG = 0.05f;
static const float kMagMaxG = 3.80f;

struct Sample {
  int16_t ax, ay, az;
  int16_t gx, gy, gz;
  int16_t mx, my, mz;
  bool ok;
};

static bool writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
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

static bool readBurst(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom(addr, len) != len) {
    return false;
  }
  for (uint8_t i = 0; i < len; i++) {
    buf[i] = Wire.read();
  }
  return true;
}

static int16_t le16(const uint8_t *p) {
  return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static bool waitBit(uint8_t addr, uint8_t reg, uint8_t mask, unsigned long timeoutMs) {
  const unsigned long start = millis();
  while ((millis() - start) < timeoutMs) {
    uint8_t value = 0;
    if (readReg(addr, reg, &value) && (value & mask) == mask) {
      return true;
    }
    delay(5);
  }
  return false;
}

static bool configureLsm6() {
  if (!writeReg(ADDR_LSM6, LSM6_CTRL3_C, 0x01)) {
    return false;
  }
  const unsigned long start = millis();
  bool resetDone = false;
  while ((millis() - start) < 50) {
    uint8_t value = 0x01;
    if (!readReg(ADDR_LSM6, LSM6_CTRL3_C, &value)) {
      return false;
    }
    if ((value & 0x01) == 0) {
      resetDone = true;
      break;
    }
    delay(2);
  }
  if (!resetDone) {
    return false;
  }
  if (!writeReg(ADDR_LSM6, LSM6_CTRL3_C, LSM6_CTRL3_BDU_IFINC)) {
    return false;
  }
  if (!writeReg(ADDR_LSM6, LSM6_CTRL1_XL, LSM6_ODR_104_FS_2G)) {
    return false;
  }
  if (!writeReg(ADDR_LSM6, LSM6_CTRL2_G, LSM6_ODR_104_FS_250)) {
    return false;
  }
  return waitBit(ADDR_LSM6, LSM6_STATUS, 0x03, 100);
}

static bool configureLis3() {
  if (!writeReg(ADDR_LIS3, LIS3_CTRL2, LIS3_CTRL2_SOFT_RST)) {
    return false;
  }
  delay(10);
  if (!writeReg(ADDR_LIS3, LIS3_CTRL2, 0x00)) {
    return false;
  }
  if (!writeReg(ADDR_LIS3, LIS3_CTRL1, LIS3_CTRL1_155HZ_UHP)) {
    return false;
  }
  if (!writeReg(ADDR_LIS3, LIS3_CTRL4, LIS3_CTRL4_Z_UHP)) {
    return false;
  }
  if (!writeReg(ADDR_LIS3, LIS3_CTRL5, LIS3_CTRL5_BDU)) {
    return false;
  }
  if (!writeReg(ADDR_LIS3, LIS3_CTRL3, LIS3_CTRL3_CONTINUOUS)) {
    return false;
  }
  return waitBit(ADDR_LIS3, LIS3_STATUS, 0x08, 200);
}

static bool readSample(Sample *s) {
  uint8_t imu[12];
  uint8_t mag[6];
  if (!readBurst(ADDR_LSM6, LSM6_OUTX_L_G, imu, sizeof(imu))) {
    return false;
  }
  if (!readBurst(ADDR_LIS3, (uint8_t)(0x80 | LIS3_OUT_X_L), mag, sizeof(mag))) {
    return false;
  }
  s->gx = le16(imu + 0);
  s->gy = le16(imu + 2);
  s->gz = le16(imu + 4);
  s->ax = le16(imu + 6);
  s->ay = le16(imu + 8);
  s->az = le16(imu + 10);
  s->mx = le16(mag + 0);
  s->my = le16(mag + 2);
  s->mz = le16(mag + 4);
  s->ok = true;
  return true;
}

static void printSigned(int16_t value) {
  Serial.print(value);
}

static void printSample(const Sample &s) {
  Serial.print(F("A "));
  printSigned(s.ax);
  Serial.print(' ');
  printSigned(s.ay);
  Serial.print(' ');
  printSigned(s.az);
  Serial.print(F("  G "));
  printSigned(s.gx);
  Serial.print(' ');
  printSigned(s.gy);
  Serial.print(' ');
  printSigned(s.gz);
  Serial.print(F("  M "));
  printSigned(s.mx);
  Serial.print(' ');
  printSigned(s.my);
  Serial.print(' ');
  printSigned(s.mz);
  Serial.println();

  Serial.print(F("  "));
  Serial.print(s.ax * LSM6_ACCEL_G_PER_LSB, 3);
  Serial.print(' ');
  Serial.print(s.ay * LSM6_ACCEL_G_PER_LSB, 3);
  Serial.print(' ');
  Serial.print(s.az * LSM6_ACCEL_G_PER_LSB, 3);
  Serial.print(F(" g | "));
  Serial.print(s.gx * LSM6_GYRO_DPS_PER_LSB, 2);
  Serial.print(' ');
  Serial.print(s.gy * LSM6_GYRO_DPS_PER_LSB, 2);
  Serial.print(' ');
  Serial.print(s.gz * LSM6_GYRO_DPS_PER_LSB, 2);
  Serial.print(F(" dps | "));
  Serial.print(s.mx * LIS3_GAUSS_PER_LSB, 3);
  Serial.print(' ');
  Serial.print(s.my * LIS3_GAUSS_PER_LSB, 3);
  Serial.print(' ');
  Serial.print(s.mz * LIS3_GAUSS_PER_LSB, 3);
  Serial.println(F(" G"));
}

static bool sensorsReady = false;
static unsigned long lastLiveMs = 0;

static bool runTest() {
  uint8_t whoLsm = 0;
  uint8_t whoLis = 0;
  bool whoOk = true;

  Serial.println();
  Serial.println(F("LSM6 + LIS3MDL  SDA P1.04  SCL P1.06"));

  if (!readReg(ADDR_LSM6, REG_WHO_AM_I, &whoLsm) || whoLsm != WHO_LSM6DSOX) {
    Serial.print(F("U4 LSM6DSOX 0x6A WHO gagal, dapat 0x"));
    Serial.println(whoLsm, HEX);
    whoOk = false;
  } else {
    Serial.println(F("U4 LSM6DSOX 0x6A WHO=0x6C OK"));
  }

  if (!readReg(ADDR_LIS3, REG_WHO_AM_I, &whoLis) || whoLis != WHO_LIS3MDL) {
    Serial.print(F("U3 LIS3MDL 0x1C WHO gagal, dapat 0x"));
    Serial.println(whoLis, HEX);
    whoOk = false;
  } else {
    Serial.println(F("U3 LIS3MDL  0x1C WHO=0x3D OK"));
  }

  if (!whoOk) {
    sensorsReady = false;
    Serial.println(F("TEST GAGAL"));
    return false;
  }

  if (!configureLsm6()) {
    Serial.println(F("LSM6 konfigurasi gagal"));
    sensorsReady = false;
    Serial.println(F("TEST GAGAL"));
    return false;
  }
  if (!configureLis3()) {
    Serial.println(F("LIS3 konfigurasi gagal"));
    sensorsReady = false;
    Serial.println(F("TEST GAGAL"));
    return false;
  }

  delay(80);  // gyro baru hidup masih puluhan dps selama ~40 ms

  Sample samples[kSamples];
  float accelSum = 0.0f;
  float gyroMax = 0.0f;
  float magSum = 0.0f;
  int good = 0;

  for (int i = 0; i < kSamples; i++) {
    delay(10);
    if (!readSample(&samples[i])) {
      Serial.println(F("baca sampel gagal"));
      sensorsReady = false;
      Serial.println(F("TEST GAGAL"));
      return false;
    }
    printSample(samples[i]);
    const float ax = samples[i].ax * LSM6_ACCEL_G_PER_LSB;
    const float ay = samples[i].ay * LSM6_ACCEL_G_PER_LSB;
    const float az = samples[i].az * LSM6_ACCEL_G_PER_LSB;
    const float gx = samples[i].gx * LSM6_GYRO_DPS_PER_LSB;
    const float gy = samples[i].gy * LSM6_GYRO_DPS_PER_LSB;
    const float gz = samples[i].gz * LSM6_GYRO_DPS_PER_LSB;
    const float mx = samples[i].mx * LIS3_GAUSS_PER_LSB;
    const float my = samples[i].my * LIS3_GAUSS_PER_LSB;
    const float mz = samples[i].mz * LIS3_GAUSS_PER_LSB;
    accelSum += sqrtf(ax * ax + ay * ay + az * az);
    gyroMax = max(gyroMax, fabsf(gx));
    gyroMax = max(gyroMax, fabsf(gy));
    gyroMax = max(gyroMax, fabsf(gz));
    magSum += sqrtf(mx * mx + my * my + mz * mz);
    good++;
  }

  const float accelMean = accelSum / good;
  const float magMean = magSum / good;
  bool pass = true;

  Serial.print(F("ACCEL |a|="));
  Serial.print(accelMean, 3);
  Serial.print(F(" g "));
  if (accelMean >= kAccelMinG && accelMean <= kAccelMaxG) {
    Serial.println(F("OK"));
  } else {
    Serial.println(F("GAGAL"));
    pass = false;
  }

  Serial.print(F("GYRO |w|max="));
  Serial.print(gyroMax, 2);
  Serial.print(F(" dps "));
  if (gyroMax <= kGyroMaxDps) {
    Serial.println(F("OK"));
  } else {
    Serial.println(F("GAGAL (board harus diam)"));
    pass = false;
  }

  Serial.print(F("MAG |m|="));
  Serial.print(magMean, 3);
  Serial.print(F(" G "));
  if (magMean >= kMagMinG && magMean <= kMagMaxG) {
    Serial.println(F("OK"));
  } else {
    Serial.println(F("GAGAL"));
    pass = false;
  }

  sensorsReady = true;
  lastLiveMs = millis();
  Serial.println(pass ? F("TEST OK") : F("TEST GAGAL"));
  return pass;
}

static char lineBuf[16];
static uint8_t lineLen = 0;

static void handleLine(char *line) {
  for (char *p = line; *p; ++p) {
    if (*p >= 'a' && *p <= 'z') {
      *p = (char)(*p - 'a' + 'A');
    }
  }
  if (strcmp(line, "TEST") == 0) {
    runTest();
    return;
  }
  if (strcmp(line, "HELP") == 0) {
    Serial.println(F("TEST  ulang 8 sampel dan vonis"));
    return;
  }
  Serial.println(F("Ketik TEST"));
}

void setup() {
  Serial.begin(115200);
  const unsigned long start = millis();
  while (!Serial && (millis() - start < 4000)) {
    delay(10);
  }

  Serial.println(F("LSM6 + LIS3MDL boot 1.1.0"));
  Serial.println(F("LSM6 104 Hz, LIS3MDL 155 Hz, cetak 100 Hz"));
  Wire.begin();
  Wire.setClock(100000);
  runTest();
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

  if (!sensorsReady) {
    return;
  }
  if ((millis() - lastLiveMs) < kLiveMs) {
    return;
  }
  lastLiveMs = millis();
  Sample s;
  if (readSample(&s)) {
    printSample(s);
  }
}
