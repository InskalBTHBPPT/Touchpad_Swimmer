#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <SparkFun_RV3032.h>

// Carrier skema 1.1. begin() hanya ACK 0x51.
// setTime menulis BCD ke 0x01..0x07. Weekday 0x04 = 0..6 (Minggu = 0).
// EEPROM PMU dan trickle charger tidak ditulis.
static RV3032 rtc;

static const unsigned long kPrintMs = 1000;
static unsigned long lastPrintMs = 0;
static bool rtcOk = false;
static char lineBuf[48];
static uint8_t lineLen = 0;

static int weekday(int year, int month, int day) {
  static const int t[] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
  if (month < 3) {
    year -= 1;
  }
  return (year + year / 4 - year / 100 + year / 400 + t[month - 1] + day) % 7;
}

static void printHelp() {
  Serial.println();
  Serial.println(F("Timer RV-3032 KineticLabs  addr=0x51  SDA=P1.04 SCL=P1.06"));
  Serial.println(F("Perintah (Serial 115200, akhiri Enter):"));
  Serial.println(F("  NOW"));
  Serial.println(F("  SET YYYY-MM-DD HH:MM:SS"));
  Serial.println(F("  HELP"));
  Serial.println();
}

static void printNow() {
  if (!rtc.updateTime()) {
    Serial.println(F("ERR baca RTC"));
    return;
  }
  char buf[32];
  snprintf(buf, sizeof(buf), "RTC %04u-%02u-%02u %02u:%02u:%02u",
           rtc.getYear(), rtc.getMonth(), rtc.getDate(), rtc.getHours(),
           rtc.getMinutes(), rtc.getSeconds());
  Serial.println(buf);
}

static bool parseSet(const char *s, unsigned *y, unsigned *mo, unsigned *d,
                     unsigned *h, unsigned *mi, unsigned *se) {
  if (sscanf(s, "SET %u-%u-%u %u:%u:%u", y, mo, d, h, mi, se) != 6) {
    return false;
  }
  return *y >= 2000 && *y <= 2099 && *mo >= 1 && *mo <= 12 && *d >= 1 &&
         *d <= 31 && *h <= 23 && *mi <= 59 && *se <= 59;
}

static void handleLine(char *line) {
  if (line[0] == '\0') {
    return;
  }
  for (char *p = line; *p; ++p) {
    if (*p >= 'a' && *p <= 'z') {
      *p = (char)(*p - 'a' + 'A');
    }
  }
  if (strcmp(line, "HELP") == 0) {
    printHelp();
    return;
  }
  if (strcmp(line, "NOW") == 0) {
    if (!rtcOk) {
      Serial.println(F("ERR RTC tidak ada"));
      return;
    }
    printNow();
    return;
  }
  unsigned y, mo, d, h, mi, se;
  if (parseSet(line, &y, &mo, &d, &h, &mi, &se)) {
    if (!rtcOk) {
      Serial.println(F("ERR RTC tidak ada"));
      return;
    }
    if (!rtc.setTime((uint8_t)se, (uint8_t)mi, (uint8_t)h,
                     (uint8_t)weekday((int)y, (int)mo, (int)d), (uint8_t)d,
                     (uint8_t)mo, (uint16_t)y)) {
      Serial.println(F("ERR tulis RTC"));
      return;
    }
    Serial.print(F("OK ditulis "));
    printNow();
    return;
  }
  Serial.println(F("ERR perintah. Ketik HELP"));
}

static void pollSerial() {
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

void setup() {
  Serial.begin(115200);
  const unsigned long start = millis();
  while (!Serial && (millis() - start < 4000)) {
    delay(10);
  }

  Serial.println(F("Timer RV-3032 KineticLabs boot"));
  Wire.begin();
  Wire.setClock(100000);
  rtcOk = rtc.begin(Wire);
  rtc.set24Hour();

  printHelp();
  if (!rtcOk) {
    Serial.println(F("ERR RV-3032 tidak terdeteksi di 0x51."));
  } else {
    Serial.print(F("Jam saat boot: "));
    printNow();
  }
}

void loop() {
  pollSerial();
  const unsigned long nowMs = millis();
  if (rtcOk && (nowMs - lastPrintMs >= kPrintMs)) {
    lastPrintMs = nowMs;
    printNow();
  }
}
