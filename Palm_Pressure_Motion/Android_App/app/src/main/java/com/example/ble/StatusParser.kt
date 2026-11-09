package com.example.ble

import com.example.model.FileChunkResponse
import com.example.model.LogFileInfo
import com.example.model.PalmLogStatus
import com.example.model.PlgParsedData
import com.example.model.PlgRecord
import com.example.model.SetTimeAck
import com.example.model.SetTimeResult

object StatusParser {

    /**
     * Parses ACK_STATUS (Opcode 0x90).
     * 14 byte = layout lama. 16 byte = + vbat_mV u16 LE.
     */
    fun parse(bytes: ByteArray?): PalmLogStatus? {
        if (bytes == null ||
            (bytes.size != BleConstants.STATUS_PACKET_LENGTH_V1 &&
                bytes.size != BleConstants.STATUS_PACKET_LENGTH)
        ) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_ACK_STATUS) {
            return null
        }

        val measure = (bytes[1].toInt() and 0xFF) != 0
        val rtcOk = (bytes[2].toInt() and 0xFF) != 0

        val unixTime = (bytes[3].toLong() and 0xFF) or
                ((bytes[4].toLong() and 0xFF) shl 8) or
                ((bytes[5].toLong() and 0xFF) shl 16) or
                ((bytes[6].toLong() and 0xFF) shl 24)

        val nextFree = (bytes[7].toLong() and 0xFF) or
                ((bytes[8].toLong() and 0xFF) shl 8) or
                ((bytes[9].toLong() and 0xFF) shl 16) or
                ((bytes[10].toLong() and 0xFF) shl 24)

        val fileCount = bytes[11].toInt() and 0xFF
        val usb = (bytes[12].toInt() and 0xFF) != 0
        val pwrSave = (bytes[13].toInt() and 0xFF) != 0
        val batteryMv = if (bytes.size >= BleConstants.STATUS_PACKET_LENGTH) {
            (bytes[14].toInt() and 0xFF) or ((bytes[15].toInt() and 0xFF) shl 8)
        } else {
            null
        }

        return PalmLogStatus(
            measure = measure,
            rtcOk = rtcOk,
            unixTime = unixTime,
            nextFreeAddress = nextFree,
            fileCount = fileCount,
            usbConnected = usb,
            powerSave = pwrSave,
            batteryMv = batteryMv,
            rawBytes = bytes.copyOf()
        )
    }

    /**
     * Timing Precision: Parses the 10-byte ACK_SET_TIME response (Opcode 0x91):
     * Byte 0: 0x91
     * Byte 1: result u8: 0=OK, 1=no RTC, 2=bad range
     * Byte 2..9: unix_ms u64 LE after adjust (0 if failed)
     */
    fun parseSetTimeAck(bytes: ByteArray?): SetTimeAck? {
        if (bytes == null || bytes.size != BleConstants.ACK_SET_TIME_PACKET_LENGTH) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_ACK_SET_TIME) {
            return null
        }

        val resultCode = bytes[1].toInt() and 0xFF
        var adjustedUnixMs = 0L
        for (i in 0 until 8) {
            adjustedUnixMs = adjustedUnixMs or ((bytes[2 + i].toLong() and 0xFF) shl (i * 8))
        }

        return SetTimeAck(
            result = SetTimeResult.fromCode(resultCode),
            adjustedUnixMs = adjustedUnixMs,
            rawBytes = bytes.copyOf()
        )
    }

    /**
     * Phase C: Parses LIST_ITEM notify (Opcode 0xA1, 26 bytes).
     * Byte 0: 0xA1
     * Byte 1..12: name[12] ASCII YYMMDDHHMMSS (no NUL, no .bin)
     * Byte 13: flags u8 (1=CLOSED/OK, 2=OPEN)
     * Byte 14..17: n_records u32 LE
     * Byte 18..21: byte_size u32 LE
     * Byte 22..25: start u32 LE
     */
    fun parseListItem(bytes: ByteArray?): LogFileInfo? {
        if (bytes == null || bytes.size != BleConstants.LIST_ITEM_PACKET_LENGTH) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_LIST_ITEM) {
            return null
        }

        val name = String(bytes, 1, 12, Charsets.US_ASCII).trim('\u0000', ' ')
        val flags = bytes[13].toInt() and 0xFF
        val nRecords = (bytes[14].toLong() and 0xFF) or
                ((bytes[15].toLong() and 0xFF) shl 8) or
                ((bytes[16].toLong() and 0xFF) shl 16) or
                ((bytes[17].toLong() and 0xFF) shl 24)

        val byteSize = (bytes[18].toLong() and 0xFF) or
                ((bytes[19].toLong() and 0xFF) shl 8) or
                ((bytes[20].toLong() and 0xFF) shl 16) or
                ((bytes[21].toLong() and 0xFF) shl 24)

        val startAddr = (bytes[22].toLong() and 0xFF) or
                ((bytes[23].toLong() and 0xFF) shl 8) or
                ((bytes[24].toLong() and 0xFF) shl 16) or
                ((bytes[25].toLong() and 0xFF) shl 24)

        return LogFileInfo(
            name = name,
            flags = flags,
            recordsCount = nRecords,
            byteSize = byteSize,
            startAddress = startAddr
        )
    }

    /**
     * Phase C: Parses CHUNK notify (Opcode 0xB1).
     * Byte 0: 0xB1
     * Byte 1: result (0=OK, 1=not found, 2=busy OPEN, 3=bad offset)
     * Byte 2..5: offset u32 LE
     * Byte 6..9: file_size u32 LE
     * Byte 10..11: len u16 LE
     * Byte 12..: data[len]
     */
    fun parseChunk(bytes: ByteArray?): FileChunkResponse? {
        if (bytes == null || bytes.size < 2) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_CHUNK) {
            return null
        }

        val result = bytes[1].toInt() and 0xFF
        if (result != 0 && bytes.size < BleConstants.CHUNK_HEADER_LENGTH) {
            return FileChunkResponse(
                result = result,
                offset = 0L,
                fileSize = 0L,
                len = 0,
                data = ByteArray(0)
            )
        }

        if (bytes.size < BleConstants.CHUNK_HEADER_LENGTH) {
            return null
        }

        val offset = (bytes[2].toLong() and 0xFF) or
                ((bytes[3].toLong() and 0xFF) shl 8) or
                ((bytes[4].toLong() and 0xFF) shl 16) or
                ((bytes[5].toLong() and 0xFF) shl 24)

        val fileSize = (bytes[6].toLong() and 0xFF) or
                ((bytes[7].toLong() and 0xFF) shl 8) or
                ((bytes[8].toLong() and 0xFF) shl 16) or
                ((bytes[9].toLong() and 0xFF) shl 24)

        val len = (bytes[10].toInt() and 0xFF) or
                ((bytes[11].toInt() and 0xFF) shl 8)

        val availableData = (bytes.size - 12).coerceAtLeast(0)
        val copyCount = minOf(len, availableData)
        val chunkData = ByteArray(copyCount)
        if (copyCount > 0) {
            System.arraycopy(bytes, 12, chunkData, 0, copyCount)
        }

        return FileChunkResponse(
            result = result,
            offset = offset,
            fileSize = fileSize,
            len = copyCount,
            data = chunkData
        )
    }

    /**
     * Phase D: Parses 2-byte ACK_DELETE response (Opcode 0xA3).
     * Byte 0: 0xA3
     * Byte 1: result (0=OK, 1=file tidak ada di board, 2=sedang measure/OPEN)
     */
    fun parseDeleteAck(bytes: ByteArray?): Int? {
        if (bytes == null || bytes.size != BleConstants.ACK_DELETE_PACKET_LENGTH) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_ACK_DELETE) {
            return null
        }
        return bytes[1].toInt() and 0xFF
    }

    /**
     * Phase D: Parses 2-byte ACK_FORMAT response (Opcode 0xA4).
     * Byte 0: 0xA4
     * Byte 1: result (0=OK, 1=stop measure dulu, 2=format ditolak)
     */
    fun parseFormatAck(bytes: ByteArray?): Int? {
        if (bytes == null || bytes.size != BleConstants.ACK_FORMAT_PACKET_LENGTH) {
            return null
        }
        if (bytes[0] != BleConstants.OPCODE_ACK_FORMAT) {
            return null
        }
        return bytes[1].toInt() and 0xFF
    }

    /**
     * PLG1 v4 (FW 3.1.x): record 26 B = t_rel_ms u32 + 11×int16.
     * Berkas lama (16/22 B) ditolak.
     */
    fun parsePlgFile(fileName: String, fileBytes: ByteArray): PlgParsedData? {
        if (fileBytes.size < BleConstants.PLG1_HEADER_SIZE) return null
        if (fileBytes[0] != 'P'.code.toByte() ||
            fileBytes[1] != 'L'.code.toByte() ||
            fileBytes[2] != 'G'.code.toByte() ||
            fileBytes[3] != '1'.code.toByte()
        ) {
            return null
        }

        val version = (fileBytes[4].toInt() and 0xFF) or ((fileBytes[5].toInt() and 0xFF) shl 8)
        val periodMs = ((fileBytes[6].toInt() and 0xFF) or ((fileBytes[7].toInt() and 0xFF) shl 8)).coerceAtLeast(1)
        val channels = fileBytes[8].toInt() and 0xFF
        val recordSize = fileBytes[9].toInt() and 0xFF
        if (version < 4 ||
            recordSize != BleConstants.PLG1_RECORD_SIZE_V4 ||
            channels < BleConstants.PLG1_CHANNELS_V4
        ) {
            return null
        }

        var startUnixMs = 0L
        if (fileBytes.size >= 30) {
            for (i in 0 until 8) {
                startUnixMs = startUnixMs or ((fileBytes[22 + i].toLong() and 0xFF) shl (i * 8))
            }
        }

        fun i16At(base: Int): Int {
            val u = (fileBytes[base].toInt() and 0xFF) or ((fileBytes[base + 1].toInt() and 0xFF) shl 8)
            return u.toShort().toInt()
        }

        fun u32At(base: Int): Long =
            (fileBytes[base].toLong() and 0xFF) or
                ((fileBytes[base + 1].toLong() and 0xFF) shl 8) or
                ((fileBytes[base + 2].toLong() and 0xFF) shl 16) or
                ((fileBytes[base + 3].toLong() and 0xFF) shl 24)

        val records = mutableListOf<PlgRecord>()
        var offset = BleConstants.PLG1_HEADER_SIZE
        var index = 0
        while (offset + recordSize <= fileBytes.size) {
            val tRel = u32At(offset)
            val ch = IntArray(BleConstants.PLG1_CHANNELS_V4) { i ->
                i16At(offset + 4 + i * 2)
            }
            val absMs = if (startUnixMs != 0L) startUnixMs + tRel else 0L
            records.add(
                PlgRecord(
                    index = index,
                    tRelMs = tRel,
                    channels = ch,
                    absoluteUnixMs = absMs
                )
            )
            offset += recordSize
            index++
        }

        return PlgParsedData(
            fileName = fileName,
            version = version,
            periodMs = periodMs,
            channels = channels,
            recordSize = recordSize,
            records = records,
            startUnixMs = startUnixMs
        )
    }
}
