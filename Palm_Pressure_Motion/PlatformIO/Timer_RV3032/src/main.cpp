#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <time.h>
#include <bb_rtc.h>

// Carrier skema 1.1: SDA P1.04, SCL P1.06. U2 RV-3032 di 0x51.
// Salinan lib/bb_rtc hanya ACK 0x51. Tidak menulis 0x17, 0x03, atau EEPROM PMU C0h.
static BBRTC rtc;

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
  Serial.println(F("Timer RV-3032  addr=0x51  I2C SDA=P1.04 SCL=P1.06"));
  Serial.println(F("Perintah (Serial 115200, akhiri Enter):"));
  Serial.println(F("  NOW                     cetak waktu RTC"));
  Serial.println(F("  SET YYYY-MM-DD HH:MM:SS  tulis jam ke RV-3032"));
  Serial.println(F("  HELP"));
  Serial.println(F("Atau dari laptop: python tools/sync_time.py COM12"));
  Serial.println();
}

static void printDateTime(const struct tm &t) {
  char buf[32];
  snprintf(buf, sizeof(buf), "%04u-%02u-%02u %02u:%02u:%02u",
           (unsigned)(t.tm_year + 1900), (unsigned)(t.tm_mon + 1),
           (unsigned)t.tm_mday, (unsigned)t.tm_hour, (unsigned)t.tm_min,
           (unsigned)t.tm_sec);
  Serial.print(buf);
}

static void cmdNow() {
  if (!rtcOk) {
    Serial.println(F("ERR RTC tidak ada"));
    return;
  }
  struct tm t;
  rtc.getTime(&t);
  Serial.print(F("RTC "));
  printDateTime(t);
  Serial.println();
}

static bool parseSet(const char *s, struct tm *out) {
  unsigned y = 0, mo = 0, d = 0, h = 0, mi = 0, se = 0;
  if (sscanf(s, "SET %u-%u-%u %u:%u:%u", &y, &mo, &d, &h, &mi, &se) != 6) {
    return false;
  }
  if (y < 2000 || y > 2099 || mo < 1 || mo > 12 || d < 1 || d > 31 ||
      h > 23 || mi > 59 || se > 59) {
    return false;
  }
  memset(out, 0, sizeof(*out));
  out->tm_year = (int)y - 1900;
  out->tm_mon = (int)mo - 1;
  out->tm_mday = (int)d;
  out->tm_hour = (int)h;
  out->tm_min = (int)mi;
  out->tm_sec = (int)se;
  out->tm_wday = weekday((int)y, (int)mo, (int)d);
  return true;
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
    cmdNow();
    return;
  }

  struct tm t;
  if (parseSet(line, &t)) {
    if (!rtcOk) {
      Serial.println(F("ERR RTC tidak ada"));
      return;
    }
    rtc.setTime(&t);
    struct tm wrote;
    rtc.getTime(&wrote);
    Serial.print(F("OK ditulis "));
    printDateTime(wrote);
    Serial.println();
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

  Serial.println(F("Timer RV-3032 boot"));
  // init() memakai Wire default: SDA P1.04, SCL P1.06, 100 kHz.
  const int initRc = rtc.init();
  rtcOk = (initRc == RTC_SUCCESS) && (rtc.getType() == RTC_RV3032);

  printHelp();
  if (!rtcOk) {
    Serial.println(F("ERR RV-3032 tidak terdeteksi di 0x51. Cek 3V3, GND, SDA, SCL."));
  } else {
    struct tm t;
    rtc.getTime(&t);
    Serial.print(F("Jam saat boot: "));
    printDateTime(t);
    Serial.println();
  }
}

void loop() {
  pollSerial();

  const unsigned long nowMs = millis();
  if (rtcOk && (nowMs - lastPrintMs >= kPrintMs)) {
    lastPrintMs = nowMs;
    cmdNow();
  }
}
