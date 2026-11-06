#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <SPI.h>

// SPI bus default nicenano (pinout-v2): SCK=D14/P1.11, MOSI=D15/P1.13, MISO=D18/P1.15
// CS: P1.12 tidak ada di header. Pakai D16 / P0.10 (silk 010), sebelah SCK.
// Pinout SOIC-8 sama dengan W25Q32; yang beda hanya kapasitas dan JEDEC.
static const uint8_t PIN_FLASH_CS = PIN_010;  // D16, P0.10, Arduino 10

static const uint32_t FLASH_SIZE = 16UL * 1024UL * 1024UL;  // W25Q128 = 16 MB
static const uint32_t TEST_ADDR = 0xFF0000UL;               // 64 KB sebelum akhir chip

static const uint8_t CMD_JEDEC = 0x9F;
static const uint8_t CMD_WREN = 0x06;
static const uint8_t CMD_RDSR = 0x05;
static const uint8_t CMD_READ = 0x03;
static const uint8_t CMD_PP = 0x02;
static const uint8_t CMD_SE = 0x20;  // 4 KB sector erase

static char lineBuf[96];
static uint8_t lineLen = 0;

static void csLow() { digitalWrite(PIN_FLASH_CS, LOW); }
static void csHigh() { digitalWrite(PIN_FLASH_CS, HIGH); }

static void printHelp() {
  Serial.println();
  Serial.println(F("Flash W25Q128JV SOIC-8  16MB  SPI Mode0"));
  Serial.println(F("  IC6 CLK  <- D14 P1.11 silk111 (#43)"));
  Serial.println(F("  IC5 DI   <- D15 P1.13 silk113 (#45)"));
  Serial.println(F("  IC2 DO   -> D18 P1.15 silk115 (#47)"));
  Serial.println(F("  IC1 /CS  <- D16 P0.10 silk010 (#10)"));
  Serial.println(F("  IC8 VCC 3V3  IC4 GND  IC3/7 10k->3V3"));
  Serial.println(F("Perintah (115200, Enter):"));
  Serial.println(F("  ID              JEDEC 9Fh (harus EF 40 18)"));
  Serial.println(F("  TEST            erase+write+read di 0xFF0000"));
  Serial.println(F("  READ addr len   baca hex (addr hex, len desimal)"));
  Serial.println(F("  HELP"));
  Serial.println();
}

static uint8_t readStatus() {
  csLow();
  SPI.transfer(CMD_RDSR);
  const uint8_t s = SPI.transfer(0xFF);
  csHigh();
  return s;
}

static void waitBusy() {
  while (readStatus() & 0x01) {
    delay(1);
  }
}

static void writeEnable() {
  csLow();
  SPI.transfer(CMD_WREN);
  csHigh();
}

static void jedecId(uint8_t out[3]) {
  csLow();
  SPI.transfer(CMD_JEDEC);
  out[0] = SPI.transfer(0xFF);
  out[1] = SPI.transfer(0xFF);
  out[2] = SPI.transfer(0xFF);
  csHigh();
}

static void cmdId() {
  uint8_t id[3];
  jedecId(id);
  Serial.print(F("JEDEC "));
  for (int i = 0; i < 3; i++) {
    if (id[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(id[i], HEX);
    if (i < 2) {
      Serial.print(' ');
    }
  }
  if (id[0] == 0xEF && id[1] == 0x40 && id[2] == 0x18) {
    Serial.println(F("  OK W25Q128"));
  } else if (id[0] == 0xEF && id[1] == 0x40 && id[2] == 0x16) {
    Serial.println(F("  WARN ini W25Q32 (4MB), bukan W25Q128"));
  } else {
    Serial.println(F("  ERR tidak dikenali / wiring salah"));
  }
}

static void readBytes(uint32_t addr, uint8_t *buf, size_t len) {
  csLow();
  SPI.transfer(CMD_READ);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  for (size_t i = 0; i < len; i++) {
    buf[i] = SPI.transfer(0xFF);
  }
  csHigh();
}

static void pageProgram(uint32_t addr, const uint8_t *buf, size_t len) {
  writeEnable();
  csLow();
  SPI.transfer(CMD_PP);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  for (size_t i = 0; i < len; i++) {
    SPI.transfer(buf[i]);
  }
  csHigh();
  waitBusy();
}

static void sectorErase4k(uint32_t addr) {
  writeEnable();
  csLow();
  SPI.transfer(CMD_SE);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);
  csHigh();
  waitBusy();
}

static void cmdTest() {
  uint8_t id[3];
  jedecId(id);
  if (!(id[0] == 0xEF && id[1] == 0x40 && id[2] == 0x18)) {
    Serial.println(F("ERR JEDEC bukan W25Q128 (EF 40 18) — abort TEST"));
    return;
  }
  if (TEST_ADDR + 256 > FLASH_SIZE) {
    Serial.println(F("ERR alamat di luar 16MB"));
    return;
  }

  Serial.print(F("Erase 4K @ 0x"));
  Serial.println(TEST_ADDR, HEX);
  sectorErase4k(TEST_ADDR);

  uint8_t wr[16];
  uint8_t rd[16];
  for (uint8_t i = 0; i < 16; i++) {
    wr[i] = (uint8_t)(0xA0 + i);
  }
  Serial.println(F("Page program 16 byte..."));
  pageProgram(TEST_ADDR, wr, sizeof(wr));
  readBytes(TEST_ADDR, rd, sizeof(rd));

  bool ok = true;
  Serial.print(F("READ "));
  for (uint8_t i = 0; i < 16; i++) {
    if (rd[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(rd[i], HEX);
    Serial.print(' ');
    if (rd[i] != wr[i]) {
      ok = false;
    }
  }
  Serial.println();
  Serial.println(ok ? F("TEST OK") : F("TEST FAIL (data tidak cocok)"));
}

static bool parseHexU32(const char *s, uint32_t *out) {
  char *end = nullptr;
  const unsigned long v = strtoul(s, &end, 16);
  if (end == s) {
    return false;
  }
  *out = (uint32_t)v;
  return true;
}

static void cmdRead(char *args) {
  while (*args == ' ') {
    args++;
  }
  char *sp = strchr(args, ' ');
  if (!sp) {
    Serial.println(F("ERR READ addr len"));
    return;
  }
  *sp = '\0';
  uint32_t addr = 0;
  if (!parseHexU32(args, &addr)) {
    Serial.println(F("ERR addr"));
    return;
  }
  int len = atoi(sp + 1);
  if (len < 1 || len > 64) {
    Serial.println(F("ERR len 1..64"));
    return;
  }
  if ((uint64_t)addr + (uint32_t)len > FLASH_SIZE) {
    Serial.println(F("ERR alamat di luar 16MB"));
    return;
  }
  uint8_t buf[64];
  readBytes(addr, buf, (size_t)len);
  Serial.print(F("READ 0x"));
  Serial.print(addr, HEX);
  Serial.print(F(": "));
  for (int i = 0; i < len; i++) {
    if (buf[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(buf[i], HEX);
    Serial.print(' ');
  }
  Serial.println();
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
  if (strcmp(line, "ID") == 0) {
    cmdId();
    return;
  }
  if (strcmp(line, "TEST") == 0) {
    cmdTest();
    return;
  }
  if (strncmp(line, "READ ", 5) == 0) {
    cmdRead(line + 5);
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

  pinMode(PIN_FLASH_CS, OUTPUT);
  csHigh();

  SPI.begin();
  SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

  printHelp();
  cmdId();
}

void loop() {
  pollSerial();
}
