/**
 * @file main.cpp
 * @brief PalmLog1 firmware — Log_Session_Bin **2.2.0**
 *
 * Logger carrier skema 1.1: rekam 100 Hz ke flash W25Q128 (PLG1 v4, 26 B/rekaman),
 * BLE NUS untuk status / sync waktu / LIST-GET / DELETE-FORMAT / stream uji.
 * Accel/gyro LSM6DSOX + mag LIS3MDL (sama LSM6_LIS3MDL 2.0.0). d1..d2 masih 0.
 *
 * ### Solusi A — timer + ring
 * SoftwareTimer 10 ms hanya capture -> ring (64); loop()/sampleTick() tulis flash.
 *
 * ### Solusi B — bypass erase setelah FORMAT
 * Chip erase penuh 16 MB -> erasedUntil = FLASH_SIZE. Append tanpa sector erase
 * sampai rewind/FORMAT.
 *
 * ### Stream
 * 0xB2 29 B untuk uji sensor. Jangan aktifkan saat perekaman lapangan.
 *
 * Spek: GoogleAIStudio/PROTOCOL.md, TIMING.md, README.md.
 *
 * ### Pin (SuperMini / carrier 1.1)
 * - Button: P0.24 -> GND (INPUT_PULLUP)
 * - LED: P0.15
 * - EXT_VCC: P0.13
 * - Flash W25Q128: SCK P1.11, MOSI P1.13, MISO P1.15, CS P0.10
 * - RTC RV-3032: SDA P1.04, SCL P1.06, addr 0x51 (bb_rtc lokal)
 * - Bat(+): R5 1 MΩ — P0.31 — R6 1 MΩ — AGND. Vbat = Vpin × 2 × 0,9726
 * - IMU U4 LSM6DSOX 0x6A + mag U3 LIS3MDL 0x1C (SDA P1.04, SCL P1.06)
 */
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <bluefruit.h>
#include <SPI.h>
#include <Wire.h>
#include <time.h>
#include <math.h>
#include <bb_rtc.h>
#include "utility/SoftwareTimer.h"
#include <string.h>
#include <stdlib.h>

// ---------------------------------------------------------------------------
static const char DEVICE_NAME[] = "PalmLog1";
static const uint8_t PIN_BTN = PIN_024;
static const uint8_t PIN_FLASH_CS = PIN_010;
static const uint8_t PIN_EXT_VCC = PIN_013;
static const uint8_t PIN_VBAT = PIN_031;

// Sama dengan VBAT_ADC 1.1.1: SAADC 12 bit, penuh skala pin 3,6 V, pembagi 1:2.
static const int VBAT_ADC_BITS = 12;
static const int VBAT_ADC_MAX = (1 << VBAT_ADC_BITS) - 1;
static const float VBAT_PIN_FULL_SCALE_V = 3.6f;
static const float VBAT_DIVIDER = 2.0f;
static const float VBAT_CAL = 0.9726f;
static const int VBAT_AVG_COUNT = 16;
static const uint32_t VBAT_REFRESH_MS = 1000;

static const uint32_t HOLD_MEASURE_MS = 3000;   // lepas dengan 3..10 s → measure
static const uint32_t HOLD_POWER_MS = 10000;    // hold ≥ 10 s → System OFF / ON
static const uint32_t ADV_IDLE_TIMEOUT_MS = 180000;  // 3 menit tanpa peer → System OFF
static const uint32_t DEBOUNCE_MS = 20;

// BLE opcodes — Fase A–D
static const uint8_t BLE_CMD_GET_STATUS = 0x10;
static const uint8_t BLE_ACK_STATUS = 0x90;
static const uint8_t BLE_CMD_SET_TIME = 0x11;
static const uint8_t BLE_ACK_SET_TIME = 0x91;
static const uint8_t BLE_CMD_LIST = 0x20;
static const uint8_t BLE_ACK_LIST_BEGIN = 0xA0;
static const uint8_t BLE_ACK_LIST_ITEM = 0xA1;
static const uint8_t BLE_ACK_LIST_END = 0xA2;
static const uint8_t BLE_CMD_GET_FILE = 0x21;
static const uint8_t BLE_ACK_FILE_CHUNK = 0xB1;
static const uint8_t BLE_CMD_DELETE = 0x23;
static const uint8_t BLE_ACK_DELETE = 0xA3;
static const uint8_t BLE_CMD_FORMAT = 0x24;
static const uint8_t BLE_ACK_FORMAT = 0xA4;
static const uint8_t BLE_FORMAT_CONFIRM = 0xA5;  // wajib di byte1 FORMAT
static const uint8_t BLE_CMD_STREAM = 0x30;       // + u8 1=start 0=stop
static const uint8_t BLE_ACK_STREAM = 0xB0;       // result: 0=mulai, 1=measure mati, 2=stop
static const uint8_t BLE_STREAM_SAMPLE = 0xB2;    // seq u16 LE + SampleRec 26 B
static const uint16_t BLE_MAX_CHUNK = 180;  // data per 0xB1 (header 12 B + data)
static const uint32_t HB_BLINK_MS = 100;
static const uint32_t HB_IDLE_PERIOD_MS = 10000;    // ON + measure=F
static const uint32_t HB_MEASURE_PERIOD_MS = 5000;  // ON + measure=T
static const uint16_t SAMPLE_PERIOD_MS = 10;
static const uint16_t FORMAT_VERSION = 4;  // v4: + t_rel_ms u32, record 26 B
static const uint8_t CHANNELS = 11;
static const uint8_t RECORD_SIZE = 26;  // t_rel_ms u32 + 11×int16
static const uint16_t FILE_HEADER_SIZE = 256;  // 1 page: meta + pad
// Rentang unix ms (~2020-01-01 … ~2100-01-01)
static const uint64_t UNIX_MS_MIN = 1577836800000ULL;
static const uint64_t UNIX_MS_MAX = 4102444800000ULL;
static const uint16_t FLASH_PAGE = 256;
static const uint32_t FLASH_SECTOR = 4096;
static const uint32_t FLASH_SIZE = 16UL * 1024UL * 1024UL;
static const uint32_t DIR_ADDR = 0x000000UL;
static const uint32_t DATA_START = FLASH_SECTOR;  // setelah 1 sektor direktori
static const uint8_t MAX_FILES = 48;

static const uint8_t CMD_JEDEC = 0x9F;
static const uint8_t CMD_WREN = 0x06;
static const uint8_t CMD_RDSR = 0x05;
static const uint8_t CMD_READ = 0x03;
static const uint8_t CMD_PP = 0x02;
static const uint8_t CMD_SE = 0x20;
static const uint8_t CMD_CE = 0xC7;

static BBRTC rtc;
static bool rtcOk = false;

static BLEUart bleuart;
static volatile bool peerConnected = false;
static bool ble_started = false;
static uint32_t adv_idle_since_ms = 0;

enum : uint8_t { ENT_FREE = 0, ENT_CLOSED = 1, ENT_OPEN = 2 };

/** Satu entri direktori flash (26 B packed). flags: ENT_FREE / CLOSED / OPEN. */
struct __attribute__((packed)) DirEntry {
  char name[13];      // "YYMMDDHHMMSS" + NUL
  uint8_t flags;
  uint32_t start;     // alamat awal file di flash
  uint32_t byte_size; // header 256 + N×26
  uint32_t n_records;
};

/** Sektor 0: metadata FS + tabel hingga MAX_FILES entri. */
struct __attribute__((packed)) DirSector {
  char magic[4];  // "PLG1"
  uint16_t version;
  uint16_t entry_count_max;
  uint32_t next_free;
  uint32_t reserved0;
  DirEntry entries[MAX_FILES];
};

/** 32 B meta di awal tiap .bin; ditulis ke page 256 B (sisanya pad 0). */
struct __attribute__((packed)) FileHeader {
  char magic[4];  // "PLG1"
  uint16_t version;
  uint16_t period_ms;
  uint8_t channels;
  uint8_t record_size;
  char start_name[12];     // YYMMDDHHMMSS tanpa NUL
  uint64_t start_unix_ms;  // wall-clock ms saat Start (0 = tidak diketahui)
  uint8_t reserved[2];
};

/**
 * Satu sampel PLG1 v4 (26 B).
 * d1..d2 general (0); d3..d5 accel mg; d6..d8 gyro 0.1°/s; d9..d11 mag µT.
 */
struct __attribute__((packed)) SampleRec {
  uint32_t t_rel_ms;  ///< millis() - sampleEpochMs
  int16_t d1;
  int16_t d2;
  int16_t d3;
  int16_t d4;
  int16_t d5;
  int16_t d6;
  int16_t d7;
  int16_t d8;
  int16_t d9;
  int16_t d10;
  int16_t d11;
};

static_assert(sizeof(SampleRec) == 26, "SampleRec must be 26 bytes");
static_assert(4 + CHANNELS * 2 == RECORD_SIZE, "CHANNELS vs RECORD_SIZE mismatch");
static_assert(sizeof(DirEntry) == 26, "DirEntry size unexpected");
static_assert(sizeof(FileHeader) == 32, "FileHeader size unexpected");

// ---- runtime state ----
static bool measure = false;
static bool streamEnabled = false;
static bool power_save_enabled = false;
/** Log Serial tiap potongan GET_FILE. Default mati agar unduh .bin tidak tertahan UART. */
static bool logGetFile = false;
// Anchor timing (lihat GoogleAIStudio/TIMING.md): bukan "RTC ms"
static bool timeAnchorValid = false;
static uint64_t t_anchor_unix_ms = 0;
static uint32_t t_anchor_millis = 0;
// Setelah ON dari tombol, OFF baru diizinkan setelah sempat lepas.
static bool pwr_btn_released_since_on = true;

static bool btnDown = false;
static bool btnStableLow = false;
static bool powerHoldFired = false;  // hold ≥10 s sudah ditangani di tekanan ini
static uint32_t btnLastChange = 0;
static uint32_t btnPressAt = 0;

// Heartbeat LED non-blocking
// measure=F (idle): triple blink tiap 10 s
// measure=T:        double blink tiap 5 s
enum : uint8_t { HB_WAIT = 0, HB_ON, HB_OFF };
static uint8_t hbPhase = HB_WAIT;
static uint8_t hbBlinkCount = 0;     // berapa kali sudah ON dalam burst ini
static uint8_t hbBlinksTarget = 3;   // 3 idle / 2 measure
static uint32_t hbPhaseSince = 0;
static uint32_t hbNextDue = 0;
static bool hbMeasureLatched = false;

static uint32_t sampleEpochMs = 0;  // millis() saat Start measure
static uint32_t sampleIndex = 0;    // jumlah rekaman yang sudah di-commit ke flash
static uint32_t sampleSeqProd = 0;  // jumlah sampel yang sudah di-capture timer
static uint32_t sampleOverruns = 0; // ring penuh (sampel dibuang di timer)

// Ring buffer: timer 10 ms push; loop() pop + tulis flash / stream.
static const uint16_t SAMPLE_Q_LEN = 64;  // ~640 ms @ 100 Hz
static SampleRec sampleQ[SAMPLE_Q_LEN];
static volatile uint16_t sampleQHead = 0;
static volatile uint16_t sampleQTail = 0;
static SoftwareTimer sampleTimer;
static bool sensorsReady = false;

static int8_t openSlot = -1;
static uint32_t writeAddr = 0;
static uint32_t fileStart = 0;
static char openName[13];
static uint8_t pageBuf[FLASH_PAGE];
static uint16_t pageUsed = 0;
static uint32_t pageBase = 0;  // flash addr of pageBuf[0]

static char lineBuf[64];
static uint8_t lineLen = 0;

// ===========================================================================
// Flash low-level
// ===========================================================================
static void csLow() { digitalWrite(PIN_FLASH_CS, LOW); }
static void csHigh() { digitalWrite(PIN_FLASH_CS, HIGH); }

static uint8_t flashReadStatus() {
  csLow();
  SPI.transfer(CMD_RDSR);
  const uint8_t s = SPI.transfer(0xFF);
  csHigh();
  return s;
}

static void flashWaitBusy() {
  while (flashReadStatus() & 0x01) {
    yield();
  }
}

static void flashWriteEnable() {
  csLow();
  SPI.transfer(CMD_WREN);
  csHigh();
}

static void flashRead(uint32_t addr, uint8_t *dst, uint32_t len) {
  csLow();
  SPI.transfer(CMD_READ);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  for (uint32_t i = 0; i < len; i++) {
    dst[i] = SPI.transfer(0xFF);
  }
  csHigh();
}

static void flashSectorErase(uint32_t addr) {
  addr &= ~(FLASH_SECTOR - 1U);
  flashWriteEnable();
  csLow();
  SPI.transfer(CMD_SE);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  csHigh();
  flashWaitBusy();
}

static void flashChipErase() {
  flashWriteEnable();
  csLow();
  SPI.transfer(CMD_CE);
  csHigh();
  flashWaitBusy();
}

// Program within one page; len must not cross page boundary.
static bool flashPageProgram(uint32_t addr, const uint8_t *src, uint16_t len) {
  if (len == 0) {
    return true;
  }
  const uint32_t pageOff = addr & (FLASH_PAGE - 1U);
  if (pageOff + len > FLASH_PAGE) {
    return false;
  }
  flashWriteEnable();
  csLow();
  SPI.transfer(CMD_PP);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  for (uint16_t i = 0; i < len; i++) {
    SPI.transfer(src[i]);
  }
  csHigh();
  flashWaitBusy();
  return true;
}

static bool flashJedecOk() {
  csLow();
  SPI.transfer(CMD_JEDEC);
  const uint8_t m = SPI.transfer(0xFF);
  const uint8_t t = SPI.transfer(0xFF);
  const uint8_t c = SPI.transfer(0xFF);
  csHigh();
  return (m == 0xEF && t == 0x40 && c == 0x18);
}

// Batas atas alamat yang sudah dijamin 0xFF (siap page-program).
/**
 * Batas atas wilayah flash yang sudah dijamin 0xFF.
 * Setelah FORMAT: FLASH_SIZE (Solusi B). Selain itu: maju per sektor saat tulis.
 */
static uint32_t erasedUntil = DATA_START;

/** Pastikan [addr, addr+len) ter-erase; no-op jika erasedUntil sudah mencakup end. */
static bool ensureErased(uint32_t addr, uint32_t len) {
  uint32_t end = addr + len;
  if (end > FLASH_SIZE) {
    return false;
  }
  // Jika erasedUntil == FLASH_SIZE (pasca chip erase), loop ini tidak jalan.
  while (erasedUntil < end) {
    flashSectorErase(erasedUntil);
    erasedUntil += FLASH_SECTOR;
  }
  return true;
}

// ===========================================================================
// Directory
// ===========================================================================
static DirSector gDir;
static bool dirDirty = false;

static void dirLoad() {
  flashRead(DIR_ADDR, reinterpret_cast<uint8_t *>(&gDir), sizeof(gDir));
  if (memcmp(gDir.magic, "PLG1", 4) != 0 || gDir.version != FORMAT_VERSION) {
    memset(&gDir, 0, sizeof(gDir));
    memcpy(gDir.magic, "PLG1", 4);
    gDir.version = FORMAT_VERSION;
    gDir.entry_count_max = MAX_FILES;
    gDir.next_free = DATA_START;
    for (uint8_t i = 0; i < MAX_FILES; i++) {
      gDir.entries[i].flags = ENT_FREE;
    }
    dirDirty = true;
  }
  if (gDir.next_free < DATA_START || gDir.next_free > FLASH_SIZE) {
    gDir.next_free = DATA_START;
    dirDirty = true;
  }
  // Sektor yang sedang diisi diasumsikan sudah di-erase; jangan erase ulang
  // (akan menghapus file lama). erasedUntil = batas atas sektor next_free.
  erasedUntil = (gDir.next_free + FLASH_SECTOR - 1U) & ~(FLASH_SECTOR - 1U);
  if (erasedUntil < DATA_START) {
    erasedUntil = DATA_START;
  }
}

static bool dirFlush() {
  if (!dirDirty) {
    return true;
  }
  flashSectorErase(DIR_ADDR);
  // tulis sizeof(DirSector) dalam potongan page
  const uint8_t *p = reinterpret_cast<const uint8_t *>(&gDir);
  uint32_t left = sizeof(gDir);
  uint32_t addr = DIR_ADDR;
  while (left > 0) {
    const uint16_t chunk = (left > FLASH_PAGE) ? FLASH_PAGE : (uint16_t)left;
    if (!flashPageProgram(addr, p, chunk)) {
      return false;
    }
    addr += chunk;
    p += chunk;
    left -= chunk;
  }
  dirDirty = false;
  return true;
}

static int8_t dirFind(const char *name) {
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    if (gDir.entries[i].flags != ENT_FREE &&
        strncmp(gDir.entries[i].name, name, 12) == 0) {
      return (int8_t)i;
    }
  }
  return -1;
}

// Hapus entri direktori. result: 0=OK, 1=not found, 2=busy OPEN.
// Data flash tidak di-wipe; ruang hanya dikembalikan jika file ini di ujung next_free.
static uint8_t dirDeleteFile(const char *name) {
  const int8_t idx = dirFind(name);
  if (idx < 0) {
    return 1;
  }
  if (measure && openSlot == idx) {
    return 2;
  }
  DirEntry &e = gDir.entries[idx];
  const uint32_t end = e.start + e.byte_size;
  if (end == gDir.next_free && end >= DATA_START) {
    gDir.next_free = e.start;
    // Sektor di alamat ini sudah pernah diprogram → wajib erase lagi sebelum tulis.
    erasedUntil = gDir.next_free & ~(uint32_t)(FLASH_SECTOR - 1U);
  }
  memset(&e, 0, sizeof(e));
  e.flags = ENT_FREE;
  dirDirty = true;
  dirFlush();
  return 0;
}

// Chip erase 4 MB + FS baru. Panggil hanya jika !measure.
// Setelah chip erase, seluruh flash 0xFF → bypass sector erase saat append
// (erasedUntil = FLASH_SIZE). Cocok alur: FORMAT → rekam… → sync → FORMAT.
static void doFormatChip() {
  flashChipErase();
  erasedUntil = FLASH_SIZE;
  memset(&gDir, 0, sizeof(gDir));
  memcpy(gDir.magic, "PLG1", 4);
  gDir.version = FORMAT_VERSION;
  gDir.entry_count_max = MAX_FILES;
  gDir.next_free = DATA_START;
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    gDir.entries[i].flags = ENT_FREE;
  }
  dirDirty = true;
  dirFlush();
}

static int8_t dirAllocSlot() {
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    if (gDir.entries[i].flags == ENT_FREE) {
      return (int8_t)i;
    }
  }
  return -1;
}

// ===========================================================================
// Logger write path
// ===========================================================================
static uint16_t pageFillFrom = 0;

static void pageResetAt(uint32_t absAddr) {
  pageBase = absAddr & ~(uint32_t)(FLASH_PAGE - 1U);
  pageFillFrom = (uint16_t)(absAddr - pageBase);
  pageUsed = pageFillFrom;
  memset(pageBuf, 0xFF, sizeof(pageBuf));
}

static bool pageFlushReal() {
  if (pageUsed <= pageFillFrom) {
    return true;
  }
  const uint16_t len = (uint16_t)(pageUsed - pageFillFrom);
  const uint32_t addr = pageBase + pageFillFrom;
  if (!ensureErased(addr, len)) {
    Serial.println(F("ERR flash penuh / erase"));
    return false;
  }
  if (!flashPageProgram(addr, pageBuf + pageFillFrom, len)) {
    Serial.println(F("ERR page program"));
    return false;
  }
  pageFillFrom = pageUsed;
  if (pageUsed >= FLASH_PAGE) {
    pageResetAt(pageBase + FLASH_PAGE);
  }
  return true;
}

static bool logWriteBytes(const uint8_t *data, uint16_t len) {
  uint16_t off = 0;
  while (off < len) {
    if (pageUsed >= FLASH_PAGE) {
      if (!pageFlushReal()) {
        return false;
      }
    }
    const uint16_t space = (uint16_t)(FLASH_PAGE - pageUsed);
    const uint16_t n = (len - off < space) ? (uint16_t)(len - off) : space;
    memcpy(pageBuf + pageUsed, data + off, n);
    pageUsed = (uint16_t)(pageUsed + n);
    writeAddr += n;
    off = (uint16_t)(off + n);
    if (pageUsed >= FLASH_PAGE) {
      if (!pageFlushReal()) {
        return false;
      }
    }
  }
  return true;
}


// ---------------------------------------------------------------------------
// RTC RV-3032 lewat bb_rtc (bukan RTClib / DS3231)
// ---------------------------------------------------------------------------
static int weekdayYmd(int year, int month, int day) {
  static const int tab[] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
  if (month < 3) {
    year -= 1;
  }
  return (year + year / 4 - year / 100 + year / 400 + tab[month - 1] + day) % 7;
}

static void forceUtcTz() {
  setenv("TZ", "GMT0", 1);
  tzset();
}

static uint32_t tmToUnix(struct tm *tmv) {
  forceUtcTz();
  return (uint32_t)mktime(tmv);
}

static uint32_t rtcUnixSeconds() {
  struct tm tmv;
  memset(&tmv, 0, sizeof(tmv));
  rtc.getTime(&tmv);
  return tmToUnix(&tmv);
}

static void rtcSetUnixSeconds(uint32_t unix_s) {
  forceUtcTz();
  time_t tt = (time_t)unix_s;
  struct tm *pt = gmtime(&tt);
  if (pt == nullptr) {
    return;
  }
  struct tm tmv = *pt;
  tmv.tm_wday = weekdayYmd(tmv.tm_year + 1900, tmv.tm_mon + 1, tmv.tm_mday);
  rtc.setTime(&tmv);
}

static void makeNameFromUnix(uint32_t unix_s, char out[13]) {
  forceUtcTz();
  time_t tt = (time_t)unix_s;
  struct tm *pt = gmtime(&tt);
  if (pt == nullptr) {
    memset(out, '0', 12);
    out[12] = '\0';
    return;
  }
  const unsigned yy = (unsigned)((pt->tm_year + 1900) % 100);
  const unsigned mo = (unsigned)(pt->tm_mon + 1);
  const unsigned dd = (unsigned)pt->tm_mday;
  const unsigned hh = (unsigned)pt->tm_hour;
  const unsigned mi = (unsigned)pt->tm_min;
  const unsigned ss = (unsigned)pt->tm_sec;
  out[0] = (char)('0' + (yy / 10) % 10);
  out[1] = (char)('0' + yy % 10);
  out[2] = (char)('0' + (mo / 10) % 10);
  out[3] = (char)('0' + mo % 10);
  out[4] = (char)('0' + (dd / 10) % 10);
  out[5] = (char)('0' + dd % 10);
  out[6] = (char)('0' + (hh / 10) % 10);
  out[7] = (char)('0' + hh % 10);
  out[8] = (char)('0' + (mi / 10) % 10);
  out[9] = (char)('0' + mi % 10);
  out[10] = (char)('0' + (ss / 10) % 10);
  out[11] = (char)('0' + ss % 10);
  out[12] = '\0';
}

static void printUnixCivil(uint32_t unix_s) {
  forceUtcTz();
  time_t tt = (time_t)unix_s;
  struct tm *pt = gmtime(&tt);
  if (pt == nullptr) {
    Serial.print(F("-- invalid time --"));
    return;
  }
  char buf[32];
  snprintf(buf, sizeof(buf), "%04u-%02u-%02u %02u:%02u:%02u",
           (unsigned)(pt->tm_year + 1900), (unsigned)(pt->tm_mon + 1),
           (unsigned)pt->tm_mday, (unsigned)pt->tm_hour, (unsigned)pt->tm_min,
           (unsigned)pt->tm_sec);
  Serial.print(buf);
}

// Anchor wall-clock ms + millis() MCU (bukan milidetik RTC). Lihat TIMING.md.
static void setTimeAnchorUnixMs(uint64_t unix_ms) {
  t_anchor_unix_ms = unix_ms;
  t_anchor_millis = millis();
  timeAnchorValid = true;
}

static uint64_t nowUnixMs() {
  if (timeAnchorValid) {
    const uint32_t elapsed = millis() - t_anchor_millis;  // wrap-safe
    return t_anchor_unix_ms + (uint64_t)elapsed;
  }
  if (rtcOk) {
    return (uint64_t)rtcUnixSeconds() * 1000ULL;
  }
  return 0;
}

static bool sampleQPop(SampleRec *out);
static void sampleQClear(void);

/**
 * Mulai sesi measure: alokasi DirEntry OPEN, tulis FileHeader, start timer 10 ms.
 * @return false jika sudah measure / RTC / flash / slot / ruang tidak siap.
 */
static bool sessionStart() {
  if (measure) {
    return false;
  }
  if (!rtcOk) {
    Serial.println(F("ERR RTC belum siap — SET dulu"));
    return false;
  }
  if (!flashJedecOk()) {
    Serial.println(F("ERR flash JEDEC"));
    return false;
  }

  const uint64_t startUnixMs = nowUnixMs();
  char name[13];
  makeNameFromUnix((uint32_t)(startUnixMs / 1000ULL), name);
  if (dirFind(name) >= 0) {
    Serial.println(F("ERR nama file sudah ada (tunggu 1s)"));
    return false;
  }
  const int8_t slot = dirAllocSlot();
  if (slot < 0) {
    Serial.println(F("ERR direktori penuh (max 48) — FORMAT atau hapus"));
    return false;
  }
  if (gDir.next_free + FILE_HEADER_SIZE + RECORD_SIZE > FLASH_SIZE) {
    Serial.println(F("ERR flash penuh"));
    return false;
  }

  fileStart = gDir.next_free;
  // align file start ke page agar header = 1 page penuh
  if (fileStart & (FLASH_PAGE - 1U)) {
    fileStart = (fileStart + FLASH_PAGE - 1U) & ~(uint32_t)(FLASH_PAGE - 1U);
    gDir.next_free = fileStart;
  }

  writeAddr = fileStart;
  pageResetAt(writeAddr);
  sampleIndex = 0;
  sampleSeqProd = 0;
  sampleOverruns = 0;
  sampleQClear();

  FileHeader hdr;
  memset(&hdr, 0, sizeof(hdr));
  memcpy(hdr.magic, "PLG1", 4);
  hdr.version = FORMAT_VERSION;
  hdr.period_ms = SAMPLE_PERIOD_MS;
  hdr.channels = CHANNELS;
  hdr.record_size = RECORD_SIZE;
  memcpy(hdr.start_name, name, 12);
  hdr.start_unix_ms = startUnixMs;
  memset(hdr.reserved, 0x00, sizeof(hdr.reserved));

  uint8_t hdrPage[FILE_HEADER_SIZE];
  memset(hdrPage, 0x00, sizeof(hdrPage));
  memcpy(hdrPage, &hdr, sizeof(hdr));

  if (!logWriteBytes(hdrPage, FILE_HEADER_SIZE)) {
    return false;
  }
  if (!pageFlushReal()) {
    return false;
  }

  DirEntry &e = gDir.entries[slot];
  memset(&e, 0, sizeof(e));
  memcpy(e.name, name, 13);
  e.flags = ENT_OPEN;
  e.start = fileStart;
  e.byte_size = FILE_HEADER_SIZE;
  e.n_records = 0;
  dirDirty = true;

  openSlot = slot;
  memcpy(openName, name, 13);
  measure = true;
  sampleEpochMs = millis();
  sampleTimer.start();

  Serial.print(F("START "));
  Serial.print(openName);
  Serial.print(F(".bin  measure=T  start_ms="));
  Serial.print((unsigned long)(startUnixMs / 1000ULL));
  Serial.print('.');
  const unsigned frac = (unsigned)(startUnixMs % 1000ULL);
  if (frac < 100) {
    Serial.print('0');
  }
  if (frac < 10) {
    Serial.print('0');
  }
  Serial.println(frac);
  return true;
}

/**
 * Stop measure: flush page, tutup entri CLOSED, stop timer, cetak prod/drop.
 * @return false jika tidak sedang measure.
 */
static bool sessionStop() {
  if (!measure || openSlot < 0) {
    sampleTimer.stop();
    measure = false;
    return false;
  }

  // Hentikan capture dulu, lalu kerjakan sisa antrian ke flash.
  sampleTimer.stop();
  SampleRec rec;
  while (sampleQPop(&rec)) {
    if (!logWriteBytes(reinterpret_cast<const uint8_t *>(&rec), RECORD_SIZE)) {
      Serial.println(F("ERR tulis sample saat STOP"));
      break;
    }
    sampleIndex++;
    if (openSlot >= 0) {
      gDir.entries[openSlot].n_records = sampleIndex;
      gDir.entries[openSlot].byte_size = writeAddr - fileStart;
    }
  }

  if (!pageFlushReal()) {
    Serial.println(F("ERR flush akhir"));
  }

  DirEntry &e = gDir.entries[openSlot];
  e.byte_size = writeAddr - fileStart;
  e.n_records = sampleIndex;
  e.flags = ENT_CLOSED;
  gDir.next_free = writeAddr;
  // align next_free ke page berikutnya agar file berikut bersih
  if (gDir.next_free & (FLASH_PAGE - 1U)) {
    gDir.next_free = (gDir.next_free + FLASH_PAGE - 1U) & ~(uint32_t)(FLASH_PAGE - 1U);
  }
  dirDirty = true;
  dirFlush();

  streamEnabled = false;
  Serial.print(F("STOP  "));
  Serial.print(openName);
  Serial.print(F(".bin  records="));
  Serial.print(e.n_records);
  Serial.print(F("  bytes="));
  Serial.print(e.byte_size);
  Serial.print(F("  prod="));
  Serial.print(sampleSeqProd);
  Serial.print(F("  drop="));
  Serial.println(sampleOverruns);

  openSlot = -1;
  measure = false;
  openName[0] = '\0';
  return true;
}

// ---------------------------------------------------------------------------
// LSM6DSOX + LIS3MDL (port dari PlatformIO/LSM6_LIS3MDL 2.0.0)
// ---------------------------------------------------------------------------
static const uint8_t ADDR_LSM6 = 0x6A;
static const uint8_t ADDR_LIS3 = 0x1C;
static const uint8_t REG_WHO_AM_I = 0x0F;
static const uint8_t WHO_LSM6DSOX = 0x6C;
static const uint8_t WHO_LIS3MDL = 0x3D;

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

static const uint8_t LIS3_CTRL1 = 0x20;
static const uint8_t LIS3_CTRL2 = 0x21;
static const uint8_t LIS3_CTRL3 = 0x22;
static const uint8_t LIS3_CTRL4 = 0x23;
static const uint8_t LIS3_CTRL5 = 0x24;
static const uint8_t LIS3_STATUS = 0x27;
static const uint8_t LIS3_OUT_X_L = 0x28;
static const uint8_t LIS3_CTRL1_155HZ_UHP = 0x72;
static const uint8_t LIS3_CTRL2_SOFT_RST = 0x04;
static const uint8_t LIS3_CTRL3_CONTINUOUS = 0x00;
static const uint8_t LIS3_CTRL4_Z_UHP = 0x0C;
static const uint8_t LIS3_CTRL5_BDU = 0x40;
static const float LIS3_GAUSS_PER_LSB = 1.0f / 6842.0f;

static bool imuWriteReg(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static bool imuReadReg(uint8_t addr, uint8_t reg, uint8_t *value) {
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

static bool imuReadBurst(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
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

static int16_t imuLe16(const uint8_t *p) {
  return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static bool imuWaitBit(uint8_t addr, uint8_t reg, uint8_t mask, unsigned long timeoutMs) {
  const unsigned long start = millis();
  while ((millis() - start) < timeoutMs) {
    uint8_t value = 0;
    if (imuReadReg(addr, reg, &value) && (value & mask) == mask) {
      return true;
    }
    delay(5);
  }
  return false;
}

static bool configureLsm6() {
  if (!imuWriteReg(ADDR_LSM6, LSM6_CTRL3_C, 0x01)) {
    return false;
  }
  const unsigned long start = millis();
  bool resetDone = false;
  while ((millis() - start) < 50) {
    uint8_t value = 0x01;
    if (!imuReadReg(ADDR_LSM6, LSM6_CTRL3_C, &value)) {
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
  if (!imuWriteReg(ADDR_LSM6, LSM6_CTRL3_C, LSM6_CTRL3_BDU_IFINC)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LSM6, LSM6_CTRL1_XL, LSM6_ODR_104_FS_2G)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LSM6, LSM6_CTRL2_G, LSM6_ODR_104_FS_250)) {
    return false;
  }
  return imuWaitBit(ADDR_LSM6, LSM6_STATUS, 0x03, 100);
}

static bool configureLis3() {
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL2, LIS3_CTRL2_SOFT_RST)) {
    return false;
  }
  delay(10);
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL2, 0x00)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL1, LIS3_CTRL1_155HZ_UHP)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL4, LIS3_CTRL4_Z_UHP)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL5, LIS3_CTRL5_BDU)) {
    return false;
  }
  if (!imuWriteReg(ADDR_LIS3, LIS3_CTRL3, LIS3_CTRL3_CONTINUOUS)) {
    return false;
  }
  return imuWaitBit(ADDR_LIS3, LIS3_STATUS, 0x08, 200);
}

static int16_t clampI16(long v) {
  if (v > 32767L) {
    return 32767;
  }
  if (v < -32768L) {
    return -32768;
  }
  return (int16_t)v;
}

/** Isi d3..d11 dari chip. d1..d2 = 0. Gagal baca → kanal IMU/mag = 0. */
static void fillSensorSample(SampleRec *r) {
  r->t_rel_ms = millis() - sampleEpochMs;
  r->d1 = 0;
  r->d2 = 0;
  r->d3 = 0;
  r->d4 = 0;
  r->d5 = 0;
  r->d6 = 0;
  r->d7 = 0;
  r->d8 = 0;
  r->d9 = 0;
  r->d10 = 0;
  r->d11 = 0;

  if (!sensorsReady) {
    return;
  }

  uint8_t imu[12];
  uint8_t mag[6];
  if (!imuReadBurst(ADDR_LSM6, LSM6_OUTX_L_G, imu, sizeof(imu))) {
    return;
  }
  if (!imuReadBurst(ADDR_LIS3, (uint8_t)(0x80 | LIS3_OUT_X_L), mag, sizeof(mag))) {
    return;
  }

  const int16_t gx = imuLe16(imu + 0);
  const int16_t gy = imuLe16(imu + 2);
  const int16_t gz = imuLe16(imu + 4);
  const int16_t ax = imuLe16(imu + 6);
  const int16_t ay = imuLe16(imu + 8);
  const int16_t az = imuLe16(imu + 10);
  const int16_t mx = imuLe16(mag + 0);
  const int16_t my = imuLe16(mag + 2);
  const int16_t mz = imuLe16(mag + 4);

  // PLG1 v4: accel mg, gyro 0.1°/s, mag µT (sama skala yang dipakai Android App).
  r->d3 = clampI16(lroundf(ax * LSM6_ACCEL_G_PER_LSB * 1000.0f));
  r->d4 = clampI16(lroundf(ay * LSM6_ACCEL_G_PER_LSB * 1000.0f));
  r->d5 = clampI16(lroundf(az * LSM6_ACCEL_G_PER_LSB * 1000.0f));
  r->d6 = clampI16(lroundf(gx * LSM6_GYRO_DPS_PER_LSB * 10.0f));
  r->d7 = clampI16(lroundf(gy * LSM6_GYRO_DPS_PER_LSB * 10.0f));
  r->d8 = clampI16(lroundf(gz * LSM6_GYRO_DPS_PER_LSB * 10.0f));
  r->d9 = clampI16(lroundf(mx * LIS3_GAUSS_PER_LSB * 100.0f));
  r->d10 = clampI16(lroundf(my * LIS3_GAUSS_PER_LSB * 100.0f));
  r->d11 = clampI16(lroundf(mz * LIS3_GAUSS_PER_LSB * 100.0f));
}

static bool initImuSensors() {
  uint8_t whoLsm = 0;
  uint8_t whoLis = 0;
  if (!imuReadReg(ADDR_LSM6, REG_WHO_AM_I, &whoLsm) || whoLsm != WHO_LSM6DSOX) {
    Serial.print(F("ERR LSM6DSOX WHO 0x"));
    Serial.println(whoLsm, HEX);
    return false;
  }
  if (!imuReadReg(ADDR_LIS3, REG_WHO_AM_I, &whoLis) || whoLis != WHO_LIS3MDL) {
    Serial.print(F("ERR LIS3MDL WHO 0x"));
    Serial.println(whoLis, HEX);
    return false;
  }
  if (!configureLsm6()) {
    Serial.println(F("ERR LSM6 konfigurasi"));
    return false;
  }
  if (!configureLis3()) {
    Serial.println(F("ERR LIS3 konfigurasi"));
    return false;
  }
  delay(80);
  return true;
}

static bool sampleQPush(const SampleRec &rec) {
  __disable_irq();
  const uint16_t head = sampleQHead;
  const uint16_t next = (uint16_t)((head + 1u) % SAMPLE_Q_LEN);
  if (next == sampleQTail) {
    sampleOverruns++;
    __enable_irq();
    return false;
  }
  sampleQ[head] = rec;
  sampleQHead = next;
  __enable_irq();
  return true;
}

static bool sampleQPop(SampleRec *out) {
  __disable_irq();
  const uint16_t tail = sampleQTail;
  if (tail == sampleQHead) {
    __enable_irq();
    return false;
  }
  *out = sampleQ[tail];
  sampleQTail = (uint16_t)((tail + 1u) % SAMPLE_Q_LEN);
  __enable_irq();
  return true;
}

static void sampleQClear() {
  __disable_irq();
  sampleQHead = 0;
  sampleQTail = 0;
  __enable_irq();
}

/**
 * Callback SoftwareTimer 10 ms (Solusi A). Baca I2C sensor + push ring; tanpa SPI flash.
 * Ring penuh → sampleOverruns++ (terlihat sebagai drop di STOP).
 */
static void sampleCaptureCb(TimerHandle_t) {
  if (!measure) {
    return;
  }
  SampleRec rec;
  fillSensorSample(&rec);
  sampleSeqProd++;
  sampleQPush(rec);
}

static bool bleNotify(const uint8_t *data, uint16_t len);

/**
 * Kirim satu 0xB2 (29 B) jika stream ON. Satu kali write, tanpa retry.
 * Hanya untuk uji; beban stream dapat menaikkan drop ring.
 */
static void bleTryStreamSample(const SampleRec &rec, uint32_t index) {
  if (!streamEnabled || !peerConnected) {
    return;
  }
  uint8_t pkt[1 + 2 + sizeof(SampleRec)];
  const uint16_t seq = (uint16_t)(index & 0xFFFF);
  pkt[0] = BLE_STREAM_SAMPLE;
  pkt[1] = (uint8_t)(seq & 0xFF);
  pkt[2] = (uint8_t)((seq >> 8) & 0xFF);
  memcpy(pkt + 3, &rec, sizeof(rec));
  bleuart.write(pkt, sizeof(pkt));
}

/** Handle 0x30: enable=1 start (butuh measure), 0=stop. ACK 0xB0. */
static void bleHandleStream(uint8_t enable) {
  uint8_t result;
  if (enable) {
    if (!measure) {
      streamEnabled = false;
      result = 1;
    } else {
      streamEnabled = true;
      result = 0;
    }
  } else {
    streamEnabled = false;
    result = 2;
  }
  uint8_t pkt[2] = {BLE_ACK_STREAM, result};
  bleNotify(pkt, sizeof(pkt));
}

/**
 * Dipanggil dari loop(): drain hingga 16 sampel dari ring → flash (+ stream opsional).
 * Timer tetap capture saat SPI sibuk.
 */
static void sampleTick() {
  if (!measure) {
    streamEnabled = false;
    return;
  }
  // Batasi per loop agar BLE/serial tetap dapat jatah CPU.
  uint8_t n = 0;
  SampleRec rec;
  while (n < 16 && sampleQPop(&rec)) {
    if (!logWriteBytes(reinterpret_cast<const uint8_t *>(&rec), RECORD_SIZE)) {
      Serial.println(F("ERR tulis sample — stop paksa"));
      sampleTimer.stop();
      sessionStop();
      return;
    }
    sampleIndex++;
    bleTryStreamSample(rec, sampleIndex);
    if (openSlot >= 0) {
      gDir.entries[openSlot].n_records = sampleIndex;
      gDir.entries[openSlot].byte_size = writeAddr - fileStart;
    }
    n++;
  }
}

// ===========================================================================
// Power (System OFF) — pola mirip Test_BLE_14Ch_Binary_Ctrl_PowerSave
// ===========================================================================
static bool btnRawDown() { return digitalRead(PIN_BTN) == LOW; }

static bool usbPresent() {
  if (ble_started) {
    uint32_t usb_reg = 0;
    if (sd_power_usbregstatus_get(&usb_reg) == NRF_SUCCESS) {
      return (usb_reg & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
    }
  }
  return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
}

static uint8_t countFiles() {
  uint8_t n = 0;
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    if (gDir.entries[i].flags != ENT_FREE) {
      n++;
    }
  }
  return n;
}

static bool wokeFromSystemOff() {
  return (readResetReason() & POWER_RESETREAS_OFF_Msk) != 0;
}

static bool heldFor(uint32_t ms) {
  const uint32_t t0 = millis();
  while ((millis() - t0) < ms) {
    if (!btnRawDown()) {
      return false;
    }
    delay(10);
  }
  return true;
}

static void enterSystemOff() {
  digitalWrite(LED_BUILTIN, LED_STATE_OFF);
  digitalWrite(PIN_EXT_VCC, LOW);

  if (ble_started) {
    Bluefruit.Advertising.restartOnDisconnect(false);
    Bluefruit.Advertising.stop();
    if (Bluefruit.connected()) {
      Bluefruit.disconnect(Bluefruit.connHandle());
    }
    delay(50);
  }

  pinMode(PIN_BTN, INPUT_PULLUP);

  // Wake aktif-LOW: jangan System OFF saat tombol masih ditekan.
  while (btnRawDown()) {
    delay(10);
  }
  delay(50);

  NRF_P0->LATCH = 0xFFFFFFFFu;
#ifdef NRF_P1
  NRF_P1->LATCH = 0xFFFFFFFFu;
#endif

  systemOff(PIN_BTN, 0);
  while (1) {
    __WFE();
  }
}

static void requestSystemOff() {
  if (measure) {
    Serial.println(F("POWER OFF — stop measure dulu"));
    sessionStop();
  }
  Serial.println(F("POWER OFF — System OFF"));
  Serial.flush();
  delay(30);
  enterSystemOff();
}

static void gatePowerOnFromButton() {
  // USB (termasuk setelah flash): tetap ON, PowerSave timer/OFF tombol nonaktif.
  if (usbPresent()) {
    power_save_enabled = false;
    pwr_btn_released_since_on = true;
    digitalWrite(PIN_EXT_VCC, HIGH);
    digitalWrite(LED_BUILTIN, LED_STATE_OFF);
    return;
  }

  power_save_enabled = true;
  digitalWrite(PIN_EXT_VCC, LOW);
  digitalWrite(LED_BUILTIN, LED_STATE_OFF);

  const bool from_system_off = wokeFromSystemOff();
  const bool btn_already_down = btnRawDown();

  // POR/RST tanpa tombol → tidur. Fallback: tombol sudah LOW (bit OFF hilang).
  if (!from_system_off && !btn_already_down) {
    enterSystemOff();
  }

  // Wake / tekan: wajib tahan ≥ 10 s.
  if (!heldFor(HOLD_POWER_MS)) {
    enterSystemOff();
  }

  pwr_btn_released_since_on = false;
  digitalWrite(PIN_EXT_VCC, HIGH);
}

// ===========================================================================
// LED heartbeat (non-blocking, paralel dengan sample)
// idle (measure=F): triple ON/OFF 100 ms, jeda 10 s
// measure=T:        double ON/OFF 100 ms, jeda 5 s
// ===========================================================================
static uint32_t hbPeriodMs() {
  return measure ? HB_MEASURE_PERIOD_MS : HB_IDLE_PERIOD_MS;
}

static uint8_t hbBlinksForMode() {
  return measure ? 2 : 3;
}

static void heartbeatStartBurst() {
  const uint32_t now = millis();
  hbBlinksTarget = hbBlinksForMode();
  hbBlinkCount = 1;
  hbPhase = HB_ON;
  hbPhaseSince = now;
  digitalWrite(LED_BUILTIN, LED_STATE_ON);
}

// blinkNow=true: langsung burst sesuai mode (feedback Start/Stop)
static void heartbeatOnMeasureChanged(bool blinkNow) {
  const uint32_t now = millis();
  hbMeasureLatched = measure;
  digitalWrite(LED_BUILTIN, LED_STATE_OFF);
  if (blinkNow) {
    heartbeatStartBurst();
  } else {
    hbPhase = HB_WAIT;
    hbNextDue = now + hbPeriodMs();
  }
}

static void heartbeatTick() {
  const uint32_t now = millis();

  if (hbMeasureLatched != measure) {
    heartbeatOnMeasureChanged(true);
    return;
  }

  if (hbPhase == HB_WAIT) {
    if ((int32_t)(now - hbNextDue) < 0) {
      return;
    }
    heartbeatStartBurst();
    return;
  }

  if ((now - hbPhaseSince) < HB_BLINK_MS) {
    return;
  }

  if (hbPhase == HB_ON) {
    digitalWrite(LED_BUILTIN, LED_STATE_OFF);
    if (hbBlinkCount >= hbBlinksTarget) {
      hbPhase = HB_WAIT;
      hbNextDue = now + hbPeriodMs();
    } else {
      hbPhase = HB_OFF;
      hbPhaseSince = now;
    }
    return;
  }

  // HB_OFF → nyala lagi untuk kedip berikutnya
  hbBlinkCount++;
  hbPhase = HB_ON;
  hbPhaseSince = now;
  digitalWrite(LED_BUILTIN, LED_STATE_ON);
}

// ===========================================================================
// Button (board ON):
//   hold ≥ 10 s → System OFF (suppress measure; flush jika measure=T)
//   lepas dengan 3 s ≤ hold < 10 s → Start/Stop measure
//   USB: PowerSave off → tidak System OFF via tombol; measure tetap jalan
// ===========================================================================
static void buttonTick() {
  const bool rawLow = btnRawDown();
  const uint32_t now = millis();

  if (rawLow != btnStableLow) {
    btnLastChange = now;
    btnStableLow = rawLow;
  }
  if ((now - btnLastChange) < DEBOUNCE_MS) {
    return;
  }

  if (btnStableLow && !btnDown) {
    btnDown = true;
    powerHoldFired = false;
    btnPressAt = now;
  } else if (!btnStableLow && btnDown) {
    const uint32_t held = now - btnPressAt;
    btnDown = false;

    if (!pwr_btn_released_since_on) {
      pwr_btn_released_since_on = true;
      powerHoldFired = false;
      return;
    }

    if (powerHoldFired) {
      powerHoldFired = false;
      return;
    }

    // Measure: fire-on-release di jendela 3..10 s
    if (held >= HOLD_MEASURE_MS && held < HOLD_POWER_MS) {
      if (!measure) {
        sessionStart();
      } else {
        sessionStop();
      }
      // Langsung double-blink + jadwal ulang (5 s measure / 10 s idle)
      heartbeatOnMeasureChanged(true);
    }
    return;
  }

  // Sedang ditekan
  if (!btnDown) {
    return;
  }

  // Belum pernah lepas setelah ON dari tombol → jangan OFF / measure
  if (!pwr_btn_released_since_on) {
    return;
  }

  // Power OFF hanya jika PowerSave aktif (bukan USB)
  if (power_save_enabled && !powerHoldFired &&
      (now - btnPressAt) >= HOLD_POWER_MS) {
    powerHoldFired = true;
    requestSystemOff();
  }
}

// ===========================================================================
// BLE NUS — Fase A–D (status, SET_TIME, LIST, GET_FILE, DELETE, FORMAT)
// ===========================================================================
static uint8_t bleRxBuf[32];
static uint8_t bleRxLen = 0;

static void startAdvertising() {
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
  adv_idle_since_ms = millis();
}

static void putU16le(uint8_t *p, uint16_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
}

static void putU32le(uint8_t *p, uint32_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
  p[2] = (uint8_t)((v >> 16) & 0xFF);
  p[3] = (uint8_t)((v >> 24) & 0xFF);
}

static void putU64le(uint8_t *p, uint64_t v) {
  putU32le(p, (uint32_t)(v & 0xFFFFFFFFUL));
  putU32le(p + 4, (uint32_t)((v >> 32) & 0xFFFFFFFFUL));
}

static uint16_t getU16le(const uint8_t *p) {
  return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t getU32le(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

static uint64_t getU64le(const uint8_t *p) {
  return (uint64_t)getU32le(p) | ((uint64_t)getU32le(p + 4) << 32);
}

// Notify penuh; retry singkat jika buffer TX penuh.
static bool bleNotify(const uint8_t *data, uint16_t len) {
  for (uint8_t i = 0; i < 40; i++) {
    if (!peerConnected) {
      return false;
    }
    if (bleuart.write(data, len) == len) {
      return true;
    }
    delay(5);
    yield();
  }
  return false;
}

static uint16_t vbatCachedMv = 0;
static uint32_t vbatCachedAtMs = 0;
static bool vbatCacheValid = false;

// 16 sampel × 2 ms, sama seperti VBAT_ADC. Cache 1 s agar STATUS/BLE tidak
// menahan drain flash tiap permintaan.
static uint16_t readBatteryMv() {
  const uint32_t now = millis();
  if (vbatCacheValid && (uint32_t)(now - vbatCachedAtMs) < VBAT_REFRESH_MS) {
    return vbatCachedMv;
  }

  uint32_t sum = 0;
  for (int i = 0; i < VBAT_AVG_COUNT; i++) {
    sum += (uint32_t)analogRead(PIN_VBAT);
    delay(2);
  }
  const uint32_t raw = (sum + (uint32_t)(VBAT_AVG_COUNT / 2)) / (uint32_t)VBAT_AVG_COUNT;
  const float vPin = (raw * VBAT_PIN_FULL_SCALE_V) / (float)VBAT_ADC_MAX;
  const float vBat = vPin * VBAT_DIVIDER * VBAT_CAL;
  int mv = (int)(vBat * 1000.0f + 0.5f);
  if (mv < 0) {
    mv = 0;
  } else if (mv > 65535) {
    mv = 65535;
  }
  vbatCachedMv = (uint16_t)mv;
  vbatCachedAtMs = now;
  vbatCacheValid = true;
  return vbatCachedMv;
}

static void bleSendStatus() {
  uint8_t pkt[16];
  pkt[0] = BLE_ACK_STATUS;
  pkt[1] = measure ? 1 : 0;
  pkt[2] = rtcOk ? 1 : 0;
  uint32_t unix = 0;
  if (rtcOk) {
    unix = (uint32_t)(nowUnixMs() / 1000ULL);
  }
  putU32le(pkt + 3, unix);
  putU32le(pkt + 7, gDir.next_free);
  pkt[11] = countFiles();
  pkt[12] = usbPresent() ? 1 : 0;
  pkt[13] = power_save_enabled ? 1 : 0;
  const uint16_t vbatMv = readBatteryMv();
  pkt[14] = (uint8_t)(vbatMv & 0xFF);
  pkt[15] = (uint8_t)((vbatMv >> 8) & 0xFF);
  bleNotify(pkt, sizeof(pkt));
}

// ACK 0x91: result u8 + unix_ms u64 LE (total 10 B)
static void bleSendSetTimeAck(uint8_t result, uint64_t unix_ms) {
  uint8_t pkt[10];
  pkt[0] = BLE_ACK_SET_TIME;
  pkt[1] = result;
  putU64le(pkt + 2, unix_ms);
  bleNotify(pkt, sizeof(pkt));
}

// Payload: unix_ms u64 LE (dari HP, wall-clock lokal)
static void bleHandleSetTime(const uint8_t *payload8) {
  if (!rtcOk) {
    bleSendSetTimeAck(1, 0);
    Serial.println(F("BLE SET_TIME ERR no RTC"));
    return;
  }
  const uint64_t unix_ms = getU64le(payload8);
  if (unix_ms < UNIX_MS_MIN || unix_ms > UNIX_MS_MAX) {
    bleSendSetTimeAck(2, 0);
    Serial.println(F("BLE SET_TIME ERR range"));
    return;
  }
  const uint32_t tRTC_s = (uint32_t)(unix_ms / 1000ULL);
  rtcSetUnixSeconds(tRTC_s);
  setTimeAnchorUnixMs(unix_ms);
  const uint64_t ackMs = nowUnixMs();
  bleSendSetTimeAck(0, ackMs);
  Serial.print(F("BLE SET_TIME OK unix_ms="));
  Serial.print((unsigned long)(ackMs / 1000ULL));
  Serial.print('.');
  const unsigned frac = (unsigned)(ackMs % 1000ULL);
  if (frac < 100) {
    Serial.print('0');
  }
  if (frac < 10) {
    Serial.print('0');
  }
  Serial.println(frac);
}

// 0x20 → 0xA0 begin + N×0xA1 item + 0xA2 end
static void bleHandleList() {
  const uint8_t total = countFiles();
  uint8_t begin[2] = {BLE_ACK_LIST_BEGIN, total};
  if (!bleNotify(begin, sizeof(begin))) {
    Serial.println(F("BLE LIST ERR begin"));
    return;
  }

  uint8_t sent = 0;
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    const DirEntry &e = gDir.entries[i];
    if (e.flags == ENT_FREE) {
      continue;
    }
    uint8_t pkt[26];
    pkt[0] = BLE_ACK_LIST_ITEM;
    memcpy(pkt + 1, e.name, 12);
    pkt[13] = e.flags;
    putU32le(pkt + 14, e.n_records);
    putU32le(pkt + 18, e.byte_size);
    putU32le(pkt + 22, e.start);
    if (!bleNotify(pkt, sizeof(pkt))) {
      Serial.println(F("BLE LIST ERR item"));
      return;
    }
    sent++;
    delay(2);
    yield();
  }

  uint8_t end[2] = {BLE_ACK_LIST_END, sent};
  bleNotify(end, sizeof(end));
  Serial.print(F("BLE LIST OK n="));
  Serial.println(sent);
}

// 0x21 name[12] offset u32 max_chunk u16 → 0xB1 chunk (pull)
// result: 0=OK, 1=not found, 2=busy OPEN, 3=bad offset
static void bleHandleGetFile(const uint8_t *p) {
  char name[13];
  memcpy(name, p, 12);
  name[12] = '\0';
  const uint32_t offset = getU32le(p + 12);
  uint16_t want = getU16le(p + 16);
  if (want == 0 || want > BLE_MAX_CHUNK) {
    want = BLE_MAX_CHUNK;
  }

  uint8_t pkt[12 + BLE_MAX_CHUNK];
  pkt[0] = BLE_ACK_FILE_CHUNK;

  const int8_t idx = dirFind(name);
  if (idx < 0) {
    pkt[1] = 1;
    putU32le(pkt + 2, offset);
    putU32le(pkt + 6, 0);
    putU16le(pkt + 10, 0);
    bleNotify(pkt, 12);
    Serial.println(F("BLE GET_FILE ERR not found"));
    return;
  }

  if (measure && openSlot == idx) {
    pkt[1] = 2;
    putU32le(pkt + 2, offset);
    putU32le(pkt + 6, gDir.entries[idx].byte_size);
    putU16le(pkt + 10, 0);
    bleNotify(pkt, 12);
    Serial.println(F("BLE GET_FILE ERR busy"));
    return;
  }

  const DirEntry &e = gDir.entries[idx];
  if (offset > e.byte_size) {
    pkt[1] = 3;
    putU32le(pkt + 2, offset);
    putU32le(pkt + 6, e.byte_size);
    putU16le(pkt + 10, 0);
    bleNotify(pkt, 12);
    Serial.println(F("BLE GET_FILE ERR offset"));
    return;
  }

  uint16_t len = 0;
  if (offset < e.byte_size) {
    const uint32_t left = e.byte_size - offset;
    len = (left > want) ? want : (uint16_t)left;
    flashRead(e.start + offset, pkt + 12, len);
  }

  pkt[1] = 0;
  putU32le(pkt + 2, offset);
  putU32le(pkt + 6, e.byte_size);
  putU16le(pkt + 10, len);
  if (!bleNotify(pkt, (uint16_t)(12 + len))) {
    Serial.println(F("BLE GET_FILE ERR notify"));
    return;
  }

  const bool started = (offset == 0);
  const uint32_t next = offset + len;
  const bool finished = (e.byte_size == 0) || (next >= e.byte_size);
  if (logGetFile) {
    Serial.print(F("BLE GET_FILE "));
    Serial.print(name);
    Serial.print(F(" off="));
    Serial.print(offset);
    Serial.print(F(" len="));
    Serial.print(len);
    Serial.print(F(" / "));
    Serial.println(e.byte_size);
  } else {
    if (started) {
      Serial.print(F("BLE GET_FILE "));
      Serial.print(name);
      Serial.print(F(" start bytes="));
      Serial.println(e.byte_size);
    }
    if (finished) {
      Serial.print(F("BLE GET_FILE "));
      Serial.print(name);
      Serial.print(F(" done bytes="));
      Serial.println(e.byte_size);
    }
  }
}

// 0x23 + name[12] → 0xA3 result (0=OK, 1=not found, 2=busy)
static void bleHandleDelete(const uint8_t *name12) {
  char name[13];
  memcpy(name, name12, 12);
  name[12] = '\0';
  const uint8_t result = dirDeleteFile(name);
  uint8_t pkt[2] = {BLE_ACK_DELETE, result};
  bleNotify(pkt, sizeof(pkt));
  if (result == 0) {
    Serial.print(F("BLE DELETE OK "));
    Serial.println(name);
  } else if (result == 1) {
    Serial.println(F("BLE DELETE ERR not found"));
  } else {
    Serial.println(F("BLE DELETE ERR busy"));
  }
}

// 0x24 + confirm 0xA5 → 0xA4 result (0=OK, 1=measure, 2=bad confirm)
// Chip erase bisa 10–40 s — app perlu timeout panjang.
static void bleHandleFormat(uint8_t confirm) {
  if (confirm != BLE_FORMAT_CONFIRM) {
    uint8_t pkt[2] = {BLE_ACK_FORMAT, 2};
    bleNotify(pkt, sizeof(pkt));
    Serial.println(F("BLE FORMAT ERR confirm"));
    return;
  }
  if (measure) {
    uint8_t pkt[2] = {BLE_ACK_FORMAT, 1};
    bleNotify(pkt, sizeof(pkt));
    Serial.println(F("BLE FORMAT ERR measure"));
    return;
  }
  Serial.println(F("BLE FORMAT chip erase..."));
  doFormatChip();
  uint8_t pkt[2] = {BLE_ACK_FORMAT, 0};
  bleNotify(pkt, sizeof(pkt));
  Serial.println(F("BLE FORMAT OK"));
}

static void processBle() {
  while (bleuart.available() > 0) {
    const int b = bleuart.read();
    if (b < 0) {
      break;
    }
    if (bleRxLen >= sizeof(bleRxBuf)) {
      bleRxLen = 0;
    }
    bleRxBuf[bleRxLen++] = (uint8_t)b;

    const uint8_t op = bleRxBuf[0];
    if (op == BLE_CMD_GET_STATUS) {
      bleSendStatus();
      bleRxLen = 0;
    } else if (op == BLE_CMD_SET_TIME) {
      // 0x11 + unix_ms u64 LE = 9 byte
      if (bleRxLen >= 9) {
        bleHandleSetTime(bleRxBuf + 1);
        bleRxLen = 0;
      }
    } else if (op == BLE_CMD_LIST) {
      bleHandleList();
      bleRxLen = 0;
    } else if (op == BLE_CMD_GET_FILE) {
      if (bleRxLen >= 19) {
        bleHandleGetFile(bleRxBuf + 1);
        bleRxLen = 0;
      }
    } else if (op == BLE_CMD_DELETE) {
      if (bleRxLen >= 13) {
        bleHandleDelete(bleRxBuf + 1);
        bleRxLen = 0;
      }
    } else if (op == BLE_CMD_FORMAT) {
      if (bleRxLen >= 2) {
        bleHandleFormat(bleRxBuf[1]);
        bleRxLen = 0;
      }
    } else if (op == BLE_CMD_STREAM) {
      if (bleRxLen >= 2) {
        bleHandleStream(bleRxBuf[1]);
        bleRxLen = 0;
      }
    } else {
      // opcode tidak dikenal — buang
      bleRxLen = 0;
    }
  }
}

static void onConnect(uint16_t conn_handle) {
  peerConnected = true;
  BLEConnection *conn = Bluefruit.Connection(conn_handle);
  if (conn != nullptr) {
    conn->requestConnectionParameter(8);
    conn->requestMtuExchange(247);
  }
  Serial.println(F("BLE connected"));
}

static void onDisconnect(uint16_t conn_handle, uint8_t reason) {
  (void)conn_handle;
  (void)reason;
  peerConnected = false;
  streamEnabled = false;
  bleRxLen = 0;
  adv_idle_since_ms = millis();
  Serial.println(F("BLE disconnected"));
}

// ===========================================================================
// Serial CLI
// ===========================================================================
static void printHelp() {
  Serial.println();
  Serial.println(F("Log_Session_Bin 2.2.0  PalmLog1  PLG1 v4  W25Q128+RV3032  timer+ring + stream"));
  Serial.println(F("VBAT P0.31: R5/R6 1M/1M x2 cal=0.9726"));
  Serial.println(F("IMU: LSM6DSOX 0x6A + LIS3MDL 0x1C @ P1.04/P1.06"));
  Serial.println(F("PB P0.24:"));
  Serial.println(F("  lepas 3..10s  Start/Stop measure (hanya board ON)"));
  Serial.println(F("  hold >=10s    System OFF (USB cabut); ON dari tidur sama"));
  Serial.println(F("LED P0.15: idle triple/10s | measure double/5s"));
  Serial.println(F("BLE: 0x10 status | 0x11 time_ms | 0x20 LIST | 0x21 GET | 0x23 DEL | 0x24 FMT | 0x30 STREAM"));
  Serial.println(F("Sample: SoftwareTimer 10ms -> I2C sensor -> ring -> flash"));
  Serial.println(F("Rekaman: t_rel_ms | d1..d2=0 | accel mg d3..d5 | gyro 0.1dps d6..d8 | mag uT d9..d11"));
  Serial.println(F("Perintah Serial:"));
  Serial.println(F("  HELP | STATUS | NOW"));
  Serial.println(F("  LOG GET [ON|OFF]          log Serial tiap potongan unduh .bin (default OFF)"));
  Serial.println(F("  SET YYYY-MM-DD HH:MM:SS"));
  Serial.println(F("  LIST"));
  Serial.println(F("  INFO YYMMDDHHMMSS"));
  Serial.println(F("  DUMP YYMMDDHHMMSS [max]   cetak CSV index,t_rel_ms,d1..d11"));
  Serial.println(F("  DELETE YYMMDDHHMMSS       hapus entri file di board"));
  Serial.println(F("  FORMAT                    chip erase 16MB + FS baru (~40s tipikal)"));
  Serial.println();
}

static void cmdStatus() {
  Serial.print(F("board=ON"));
  Serial.print(F("  ble="));
  Serial.print(DEVICE_NAME);
  Serial.print(peerConnected ? F("/conn") : F("/adv"));
  Serial.print(F("  usb="));
  Serial.print(usbPresent() ? 'Y' : 'N');
  Serial.print(F("  vbat_mV="));
  Serial.print(readBatteryMv());
  Serial.print(F("  pwr_save="));
  Serial.print(power_save_enabled ? 'Y' : 'N');
  Serial.print(F("  measure="));
  Serial.print(measure ? 'T' : 'F');
  Serial.print(F("  rtc="));
  Serial.print(rtcOk ? F("OK") : F("NO"));
  Serial.print(F("  imu="));
  Serial.print(sensorsReady ? F("OK") : F("NO"));
  Serial.print(F("  files="));
  Serial.print(countFiles());
  if (measure) {
    Serial.print(F("  file="));
    Serial.print(openName);
    Serial.print(F(".bin  idx="));
    Serial.print(sampleIndex);
  }
  Serial.print(F("  next_free=0x"));
  Serial.println(gDir.next_free, HEX);
}

static void cmdNow() {
  if (!rtcOk) {
    Serial.println(F("ERR RTC"));
    return;
  }
  const uint64_t ms = nowUnixMs();
  Serial.print(F("RTC "));
  printUnixCivil((uint32_t)(ms / 1000ULL));
  Serial.print('.');
  const unsigned frac = (unsigned)(ms % 1000ULL);
  if (frac < 100) {
    Serial.print('0');
  }
  if (frac < 10) {
    Serial.print('0');
  }
  Serial.print(frac);
  Serial.print(timeAnchorValid ? F("  anchor=Y") : F("  anchor=N"));
  Serial.println();
}

static bool parseSet(const char *s, struct tm *out) {
  unsigned y = 0, mo = 0, d = 0, h = 0, mi = 0, se = 0;
  if (sscanf(s, "SET %u-%u-%u %u:%u:%u", &y, &mo, &d, &h, &mi, &se) != 6) {
    return false;
  }
  if (y < 2000 || y > 2099 || mo < 1 || mo > 12 || d < 1 || d > 31 || h > 23 ||
      mi > 59 || se > 59) {
    return false;
  }
  memset(out, 0, sizeof(*out));
  out->tm_year = (int)y - 1900;
  out->tm_mon = (int)mo - 1;
  out->tm_mday = (int)d;
  out->tm_hour = (int)h;
  out->tm_min = (int)mi;
  out->tm_sec = (int)se;
  out->tm_wday = weekdayYmd((int)y, (int)mo, (int)d);
  return true;
}

static void cmdList() {
  uint8_t n = 0;
  for (uint8_t i = 0; i < MAX_FILES; i++) {
    const DirEntry &e = gDir.entries[i];
    if (e.flags == ENT_FREE) {
      continue;
    }
    n++;
    Serial.print(e.name);
    Serial.print(F(".bin  "));
    Serial.print(e.flags == ENT_OPEN ? F("OPEN") : F("OK"));
    Serial.print(F("  rec="));
    Serial.print(e.n_records);
    Serial.print(F("  bytes="));
    Serial.print(e.byte_size);
    Serial.print(F("  @0x"));
    Serial.println(e.start, HEX);
  }
  if (n == 0) {
    Serial.println(F("(kosong)"));
  } else {
    Serial.print(F("total "));
    Serial.println(n);
  }
}

static void cmdInfo(const char *name) {
  const int8_t i = dirFind(name);
  if (i < 0) {
    Serial.println(F("ERR tidak ada"));
    return;
  }
  const DirEntry &e = gDir.entries[i];
  FileHeader hdr;
  flashRead(e.start, reinterpret_cast<uint8_t *>(&hdr), sizeof(hdr));
  Serial.print(F("file "));
  Serial.print(e.name);
  Serial.println(F(".bin"));
  Serial.print(F("  flags="));
  Serial.println(e.flags);
  Serial.print(F("  records="));
  Serial.println(e.n_records);
  Serial.print(F("  bytes="));
  Serial.println(e.byte_size);
  Serial.print(F("  period_ms="));
  Serial.println(hdr.period_ms);
  Serial.print(F("  record_size="));
  Serial.println(hdr.record_size);
  Serial.print(F("  version="));
  Serial.println(hdr.version);
  Serial.print(F("  start_unix_ms="));
  if (hdr.start_unix_ms == 0) {
    Serial.println(F("0 (unknown / file lama)"));
  } else {
    Serial.print((unsigned long)(hdr.start_unix_ms / 1000ULL));
    Serial.print('.');
    const unsigned frac = (unsigned)(hdr.start_unix_ms % 1000ULL);
    if (frac < 100) {
      Serial.print('0');
    }
    if (frac < 10) {
      Serial.print('0');
    }
    Serial.println(frac);
  }
  Serial.println(F("  t_nom_ms = index * period_ms  (jadwal)"));
  Serial.println(F("  t_rel_ms di tiap rekaman = millis sejak Start (terukur)"));
  Serial.println(F("  t_abs_ms ≈ start_unix_ms + t_rel_ms"));
}

static void cmdDump(const char *name, uint32_t maxRec) {
  const int8_t i = dirFind(name);
  if (i < 0) {
    Serial.println(F("ERR tidak ada"));
    return;
  }
  if (measure && openSlot == i) {
    Serial.println(F("ERR file sedang OPEN — STOP dulu"));
    return;
  }
  const DirEntry &e = gDir.entries[i];
  uint32_t n = e.n_records;
  if (maxRec > 0 && maxRec < n) {
    n = maxRec;
  }
  Serial.println(F("index,t_nom_ms,t_rel_ms,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11"));
  SampleRec rec;
  for (uint32_t idx = 0; idx < n; idx++) {
    const uint32_t addr = e.start + FILE_HEADER_SIZE + idx * RECORD_SIZE;
    flashRead(addr, reinterpret_cast<uint8_t *>(&rec), RECORD_SIZE);
    Serial.print(idx);
    Serial.print(',');
    Serial.print(idx * (uint32_t)SAMPLE_PERIOD_MS);
    Serial.print(',');
    Serial.print(rec.t_rel_ms);
    Serial.print(',');
    Serial.print(rec.d1);
    Serial.print(',');
    Serial.print(rec.d2);
    Serial.print(',');
    Serial.print(rec.d3);
    Serial.print(',');
    Serial.print(rec.d4);
    Serial.print(',');
    Serial.print(rec.d5);
    Serial.print(',');
    Serial.print(rec.d6);
    Serial.print(',');
    Serial.print(rec.d7);
    Serial.print(',');
    Serial.print(rec.d8);
    Serial.print(',');
    Serial.print(rec.d9);
    Serial.print(',');
    Serial.print(rec.d10);
    Serial.print(',');
    Serial.println(rec.d11);
    if ((idx & 0x1F) == 0x1F) {
      yield();
    }
  }
  Serial.println(F("OK DUMP"));
}

static void cmdDelete(const char *name) {
  const uint8_t result = dirDeleteFile(name);
  if (result == 0) {
    Serial.print(F("OK DELETE "));
    Serial.println(name);
  } else if (result == 1) {
    Serial.println(F("ERR tidak ada"));
  } else {
    Serial.println(F("ERR file sedang OPEN — STOP dulu"));
  }
}

static void cmdFormat() {
  if (measure) {
    Serial.println(F("ERR sedang measure — STOP dulu"));
    return;
  }
  Serial.println(F("FORMAT chip erase..."));
  doFormatChip();
  Serial.println(F("OK FORMAT"));
}

static void toUpperInPlace(char *s) {
  for (; *s; ++s) {
    if (*s >= 'a' && *s <= 'z') {
      *s = (char)(*s - 'a' + 'A');
    }
  }
}

static void handleLine(char *line) {
  if (line[0] == '\0') {
    return;
  }
  toUpperInPlace(line);

  if (strcmp(line, "HELP") == 0) {
    printHelp();
    return;
  }
  if (strcmp(line, "STATUS") == 0) {
    cmdStatus();
    return;
  }
  if (strcmp(line, "NOW") == 0) {
    cmdNow();
    return;
  }
  if (strcmp(line, "LIST") == 0) {
    cmdList();
    return;
  }
  if (strcmp(line, "FORMAT") == 0) {
    cmdFormat();
    return;
  }
  if (strcmp(line, "LOG GET") == 0) {
    Serial.println(logGetFile ? F("GET log ON") : F("GET log OFF"));
    return;
  }
  if (strcmp(line, "LOG GET ON") == 0) {
    logGetFile = true;
    Serial.println(F("GET log ON"));
    return;
  }
  if (strcmp(line, "LOG GET OFF") == 0) {
    logGetFile = false;
    Serial.println(F("GET log OFF"));
    return;
  }

  struct tm t;
  if (parseSet(line, &t)) {
    if (!rtcOk) {
      Serial.println(F("ERR RTC"));
      return;
    }
    rtc.setTime(&t);
    // Serial SET hanya detik -> ms = 0 dalam detik itu
    setTimeAnchorUnixMs((uint64_t)tmToUnix(&t) * 1000ULL);
    Serial.print(F("OK "));
    printUnixCivil(tmToUnix(&t));
    Serial.println(F(".000  anchor=Y"));
    return;
  }

  if (strncmp(line, "INFO ", 5) == 0) {
    char name[13];
    memset(name, 0, sizeof(name));
    strncpy(name, line + 5, 12);
    cmdInfo(name);
    return;
  }

  if (strncmp(line, "DELETE ", 7) == 0) {
    char name[13];
    memset(name, 0, sizeof(name));
    strncpy(name, line + 7, 12);
    if (name[0] == '\0') {
      Serial.println(F("ERR DELETE YYMMDDHHMMSS"));
      return;
    }
    cmdDelete(name);
    return;
  }

  if (strncmp(line, "DUMP ", 5) == 0) {
    char name[13];
    memset(name, 0, sizeof(name));
    unsigned maxRec = 0;
    if (sscanf(line + 5, "%12s %u", name, &maxRec) < 1) {
      Serial.println(F("ERR DUMP YYMMDDHHMMSS [max]"));
      return;
    }
    cmdDump(name, maxRec);
    return;
  }

  Serial.println(F("ERR perintah — HELP"));
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

// ===========================================================================
void setup() {
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_EXT_VCC, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_FLASH_CS, OUTPUT);
  digitalWrite(PIN_FLASH_CS, HIGH);
  digitalWrite(LED_BUILTIN, LED_STATE_OFF);
  digitalWrite(PIN_EXT_VCC, LOW);

  // Gate power SEBELUM Serial/SPI: baterai tanpa hold 10s → System OFF.
  // USB (setelah flash): langsung ON (pwr_save=N).
  gatePowerOnFromButton();

  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && (millis() - t0 < 4000)) {
    delay(10);
  }

  analogReadResolution(VBAT_ADC_BITS);

  SPI.begin();
  SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

  Wire.begin();
  Wire.setClock(100000);
  rtcOk = (rtc.init() == RTC_SUCCESS) && (rtc.getType() == RTC_RV3032);
  if (rtcOk) {
    struct tm nowT;
    rtc.getTime(&nowT);
    if ((nowT.tm_year + 1900) < 2020) {
      Serial.println(F("WARN RTC tahun < 2020 — ketik SET ..."));
    }
  } else {
    Serial.println(F("ERR RV-3032 tidak terdeteksi di 0x51"));
  }

  if (!flashJedecOk()) {
    Serial.println(F("ERR flash bukan W25Q128 (EF 40 18)"));
  }

  sensorsReady = initImuSensors();
  if (sensorsReady) {
    Serial.println(F("IMU OK LSM6DSOX+LIS3MDL"));
  }

  dirLoad();
  if (dirDirty) {
    ensureErased(DATA_START, FLASH_SECTOR);
    dirFlush();
    Serial.println(F("FS baru diinisialisasi"));
  }

  for (uint8_t i = 0; i < MAX_FILES; i++) {
    if (gDir.entries[i].flags == ENT_OPEN) {
      gDir.entries[i].flags = ENT_CLOSED;
      dirDirty = true;
    }
  }
  dirFlush();

  sampleTimer.begin(SAMPLE_PERIOD_MS, sampleCaptureCb);
  hbMeasureLatched = measure;
  hbPhase = HB_WAIT;
  hbNextDue = millis() + hbPeriodMs();

  Bluefruit.configPrphBandwidth(BANDWIDTH_HIGH);
  Bluefruit.begin();
  ble_started = true;
  sd_power_dcdc_mode_set(NRF_POWER_DCDC_ENABLE);
  Bluefruit.autoConnLed(false);
  Bluefruit.setTxPower(4);
  Bluefruit.setName(DEVICE_NAME);
  Bluefruit.Periph.setConnIntervalMS(7, 20);
  Bluefruit.Periph.setConnectCallback(onConnect);
  Bluefruit.Periph.setDisconnectCallback(onDisconnect);
  bleuart.begin();
  startAdvertising();

  printHelp();
  cmdStatus();
}

void loop() {
  // Setelah flash: cabut USB tanpa reset → aktifkan PowerSave (boleh OFF tombol).
  if (!power_save_enabled && !usbPresent()) {
    power_save_enabled = true;
    if (!peerConnected) {
      adv_idle_since_ms = millis();
    }
  }

  if (power_save_enabled && !peerConnected && !usbPresent()) {
    if ((millis() - adv_idle_since_ms) >= ADV_IDLE_TIMEOUT_MS) {
      requestSystemOff();
    }
  }

  buttonTick();
  sampleTick();
  heartbeatTick();
  pollSerial();

  if (peerConnected) {
    processBle();
  }
}
