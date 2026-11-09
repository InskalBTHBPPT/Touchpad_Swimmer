#ifndef _VARIANT_NICENANO_
#define _VARIANT_NICENANO_

#define LED_STATE_ON  1
#define LED_STATE_OFF 0

#define VARIANT_MCK (64000000ul)

#define USE_LFXO
// #define USE_LFRC

#include "WVariant.h"

#ifdef __cplusplus
extern "C"
{
#endif

#define PINS_COUNT           (48)
#define NUM_DIGITAL_PINS     (48)
#define NUM_ANALOG_INPUTS    (6)
#define NUM_ANALOG_OUTPUTS   (0)

#define PIN_SERIAL1_TX 6
#define PIN_SERIAL1_RX 8

#define PIN_002 2
#define PIN_003 3
#define PIN_004 4
#define PIN_005 5
#define PIN_006 6
#define PIN_007 7
#define PIN_008 8
#define PIN_009 9
#define PIN_010 10
#define PIN_011 11
#define PIN_012 12
#define PIN_013 13
#define PIN_014 14
#define PIN_015 15
#define PIN_016 16
#define PIN_017 17
#define PIN_018 18
#define PIN_019 19
#define PIN_020 20
#define PIN_021 21
#define PIN_022 22
#define PIN_023 23
#define PIN_024 24
#define PIN_025 25
#define PIN_026 26
#define PIN_027 27
#define PIN_028 28
#define PIN_029 29
#define PIN_030 30
#define PIN_031 31
#define PIN_100 32
#define PIN_101 33
#define PIN_102 34
#define PIN_103 35
#define PIN_104 36
#define PIN_105 37
#define PIN_106 38
#define PIN_107 39
#define PIN_108 40
#define PIN_109 41
#define PIN_110 42
#define PIN_111 43
#define PIN_112 44
#define PIN_113 45
#define PIN_114 46
#define PIN_115 47

#ifndef LED_BUILTIN
#define LED_BUILTIN PIN_015
#endif

#define PIN_LED   LED_BUILTIN
#define LED_RED   LED_BUILTIN
#ifndef LED_BLUE
#define LED_BLUE  PIN_114
#endif

#define WIRE_INTERFACES_COUNT 1
#define PIN_WIRE_SDA 36
#define PIN_WIRE_SCL 38

#define SPI_INTERFACES_COUNT 1
#define PIN_SPI_MISO 47
#define PIN_SPI_MOSI 45
#define PIN_SPI_SCK  43

static const uint8_t MOSI = PIN_SPI_MOSI;
static const uint8_t MISO = PIN_SPI_MISO;
static const uint8_t SCK  = PIN_SPI_SCK;

#ifdef __cplusplus
}
#endif

#endif
