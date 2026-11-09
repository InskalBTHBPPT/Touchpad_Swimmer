package com.example.ble

import java.util.UUID

object BleConstants {
    /**
     * Awalan nama advertising. Cocok untuk PalmLog, PalmLog1, PalmLog20, dan seterusnya.
     * Filter hardware Android hanya menerima nama persis, jadi pencocokan dilakukan di aplikasi.
     */
    const val TARGET_DEVICE_NAME = "PalmLog"

    fun isTargetName(name: String?): Boolean =
        name?.startsWith(TARGET_DEVICE_NAME, ignoreCase = true) == true

    /**
     * Nordic UART Service (NUS) UUID
     * 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
     */
    val NUS_SERVICE_UUID: UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")

    /**
     * NUS RX Characteristic (Phone -> Board, Write / Write Without Response):
     * 6E400002-B5A3-F393-E0A9-E50E24DCCA9E
     */
    val NUS_RX_CHAR_UUID: UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

    /**
     * NUS TX Characteristic (Board -> Phone, Notify):
     * 6E400003-B5A3-F393-E0A9-E50E24DCCA9E
     */
    val NUS_TX_CHAR_UUID: UUID = UUID.fromString("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

    /**
     * Client Characteristic Configuration Descriptor (CCCD):
     * 00002902-0000-1000-8000-00805f9b34fb
     */
    val CCCD_DESCRIPTOR_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    /**
     * Phase A Command Opcode: GET_STATUS (1 byte, 0x10)
     */
    const val OPCODE_GET_STATUS: Byte = 0x10.toByte()
    val CMD_GET_STATUS = byteArrayOf(OPCODE_GET_STATUS)

    /**
     * ACK GET_STATUS (0x90).
     * 14 B = layout lama (tanpa Vbat). 16 B = + vbat_mV u16 LE di byte 14..15.
     */
    const val OPCODE_ACK_STATUS: Byte = 0x90.toByte()
    const val STATUS_PACKET_LENGTH_V1 = 14
    const val STATUS_PACKET_LENGTH = 16

    /** 0x30 + enable u8. 1 = mulai stream, 0 = stop. */
    const val OPCODE_STREAM: Byte = 0x30.toByte()
    const val OPCODE_ACK_STREAM: Byte = 0xB0.toByte()
    const val OPCODE_STREAM_SAMPLE: Byte = 0xB2.toByte()
    /** FW 3.1.x: 0xB2 + seq u16 + SampleRec 26 B = 29 B. */
    const val STREAM_SAMPLE_PACKET_LENGTH = 29

    /** PLG1 v4 / FW 3.1.x: t_rel_ms u32 + 11×int16 */
    const val PLG1_RECORD_SIZE_V4 = 26
    const val PLG1_CHANNELS_V4 = 11
    const val PLG1_HEADER_SIZE = 256
    const val SAMPLE_PERIOD_MS = 10

    /**
     * Timing Precision Command Opcode: SET_TIME (9 bytes: 0x11 + uint64 LE unix_ms)
     */
    const val OPCODE_SET_TIME: Byte = 0x11.toByte()
    const val SET_TIME_COMMAND_LENGTH = 9

    /**
     * Timing Precision Response Opcode: ACK_SET_TIME (10 bytes: 0x91 + result u8 + uint64 LE unix_ms)
     */
    const val OPCODE_ACK_SET_TIME: Byte = 0x91.toByte()
    const val ACK_SET_TIME_PACKET_LENGTH = 10

    /**
     * Phase C Command Opcode: LIST (1 byte, 0x20)
     */
    const val OPCODE_LIST: Byte = 0x20.toByte()
    val CMD_LIST = byteArrayOf(OPCODE_LIST)

    /**
     * Phase C Response Opcodes for LIST:
     * 0xA0: LIST_BEGIN (2 bytes: [0xA0, total])
     * 0xA1: LIST_ITEM (26 bytes)
     * 0xA2: LIST_END (2 bytes: [0xA2, sent])
     */
    const val OPCODE_LIST_BEGIN: Byte = 0xA0.toByte()
    const val OPCODE_LIST_ITEM: Byte = 0xA1.toByte()
    const val OPCODE_LIST_END: Byte = 0xA2.toByte()
    const val LIST_ITEM_PACKET_LENGTH = 26

    /**
     * Phase C Command Opcode: GET_FILE (19 bytes: 0x21 + name[12] + offset LE u32 + max_chunk LE u16)
     */
    const val OPCODE_GET_FILE: Byte = 0x21.toByte()
    const val DEFAULT_MAX_CHUNK = 180

    /**
     * Phase C Response Opcode: CHUNK (0xB1, header 12 bytes + data[len])
     */
    const val OPCODE_CHUNK: Byte = 0xB1.toByte()
    const val CHUNK_HEADER_LENGTH = 12

    /**
     * Phase D Command Opcode: DELETE_FILE (13 bytes: 0x23 + name[12] ASCII)
     */
    const val OPCODE_DELETE: Byte = 0x23.toByte()
    const val DELETE_COMMAND_LENGTH = 13

    /**
     * Phase D Response Opcode: ACK_DELETE (2 bytes: [0xA3, result])
     * result: 0 = OK, 1 = File tidak ada, 2 = Sedang measure / OPEN
     */
    const val OPCODE_ACK_DELETE: Byte = 0xA3.toByte()
    const val ACK_DELETE_PACKET_LENGTH = 2

    /**
     * Phase D Command Opcode: FORMAT_FLASH (2 bytes: [0x24, 0xA5])
     */
    const val OPCODE_FORMAT: Byte = 0x24.toByte()
    const val FORMAT_CONFIRM_MAGIC: Byte = 0xA5.toByte()
    val CMD_FORMAT = byteArrayOf(OPCODE_FORMAT, FORMAT_CONFIRM_MAGIC)

    /**
     * Phase D Response Opcode: ACK_FORMAT (2 bytes: [0xA4, result])
     * result: 0 = OK, 1 = Stop measure dulu, 2 = Format ditolak (confirm)
     */
    const val OPCODE_ACK_FORMAT: Byte = 0xA4.toByte()
    const val ACK_FORMAT_PACKET_LENGTH = 2

    /**
     * Requested ATT MTU after connect
     */
    const val REQUESTED_MTU = 247

    /**
     * Builds the 13-byte DELETE_FILE command payload:
     * Byte 0: 0x23
     * Byte 1..12: name[12] (ASCII, no NUL, no .bin)
     */
    fun buildDeleteFileCommand(name12: String): ByteArray {
        val payload = ByteArray(DELETE_COMMAND_LENGTH)
        payload[0] = OPCODE_DELETE
        val nameClean = name12.removeSuffix(".bin").trim()
        val nameBytes = nameClean.toByteArray(Charsets.US_ASCII)
        val copyLen = minOf(nameBytes.size, 12)
        if (copyLen > 0) {
            System.arraycopy(nameBytes, 0, payload, 1, copyLen)
        }
        return payload
    }

    /**
     * Builds the 9-byte SET_TIME command payload:
     * Byte 0: 0x11
     * Byte 1..8: unix_ms u64 little-endian
     */
    fun buildSetTimeCommand(unixMs: Long): ByteArray {
        val payload = ByteArray(SET_TIME_COMMAND_LENGTH)
        payload[0] = OPCODE_SET_TIME
        for (i in 0 until 8) {
            payload[1 + i] = ((unixMs ushr (i * 8)) and 0xFF).toByte()
        }
        return payload
    }

    /**
     * Builds the 19-byte GET_FILE command payload:
     * Byte 0: 0x21
     * Byte 1..12: name[12] (ASCII, no NUL, no .bin)
     * Byte 13..16: offset u32 LE
     * Byte 17..18: max_chunk u16 LE (180)
     */
    fun buildGetFileCommand(name12: String, offset: Long, maxChunk: Int = DEFAULT_MAX_CHUNK): ByteArray {
        val payload = ByteArray(19)
        payload[0] = OPCODE_GET_FILE
        val nameClean = name12.removeSuffix(".bin").trim()
        val nameBytes = nameClean.toByteArray(Charsets.US_ASCII)
        val copyLen = minOf(nameBytes.size, 12)
        if (copyLen > 0) {
            System.arraycopy(nameBytes, 0, payload, 1, copyLen)
        }
        // offset u32 LE
        payload[13] = (offset and 0xFF).toByte()
        payload[14] = ((offset shr 8) and 0xFF).toByte()
        payload[15] = ((offset shr 16) and 0xFF).toByte()
        payload[16] = ((offset shr 24) and 0xFF).toByte()

        // max_chunk u16 LE
        payload[17] = (maxChunk and 0xFF).toByte()
        payload[18] = ((maxChunk shr 8) and 0xFF).toByte()

        return payload
    }
}
