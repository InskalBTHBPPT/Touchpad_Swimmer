package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.ble.BleConstants
import com.example.ble.StatusParser
import com.example.model.SetTimeResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.nio.ByteBuffer
import java.nio.ByteOrder

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ExampleRobolectricTest {

    @Test
    fun `read string from context verifies PalmLog app name`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertEquals("PalmLog 1.0.0", appName)
    }

    @Test
    fun `test valid 14-byte GET_STATUS response decoding`() {
        val buffer = ByteBuffer.allocate(14).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0x90.toByte()) // B0: ACK opcode
        buffer.put(0x01.toByte()) // B1: measure = True
        buffer.put(0x01.toByte()) // B2: rtc_ok = 1
        buffer.putInt(1700000000) // B3..B6: unix_time
        buffer.putInt(0x0001A000) // B7..B10: next_free
        buffer.put(12.toByte())   // B11: file_count = 12
        buffer.put(0x01.toByte()) // B12: usb = 1
        buffer.put(0x01.toByte()) // B13: pwr_save = 1

        val bytes = buffer.array()
        assertEquals(14, bytes.size)

        val status = StatusParser.parse(bytes)
        assertNotNull(status)
        assertEquals(true, status!!.measure)
        assertEquals(true, status.rtcOk)
        assertEquals(1700000000L, status.unixTime)
        assertEquals(0x0001A000L, status.nextFreeAddress)
        assertEquals("0x0001A000", status.formattedNextFree)
        assertEquals(12, status.fileCount)
        assertEquals(true, status.usbConnected)
        assertEquals(true, status.powerSave)
        assertTrue(status.rawHex.startsWith("90 01 01"))
    }

    @Test
    fun `test GET_STATUS response when RTC is zero or invalid`() {
        val buffer = ByteBuffer.allocate(14).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0x90.toByte()) // B0: ACK opcode
        buffer.put(0x00.toByte()) // B1: measure = False
        buffer.put(0x00.toByte()) // B2: rtc_ok = 0
        buffer.putInt(0)          // B3..B6: unix_time = 0
        buffer.putInt(0x00004000) // B7..B10: next_free
        buffer.put(0.toByte())    // B11: file_count = 0
        buffer.put(0x00.toByte()) // B12: usb = 0 (Battery)
        buffer.put(0x00.toByte()) // B13: pwr_save = 0

        val status = StatusParser.parse(buffer.array())
        assertNotNull(status)
        assertFalse(status!!.measure)
        assertFalse(status.rtcOk)
        assertEquals(0L, status.unixTime)
        assertEquals("0x00004000", status.formattedNextFree)
        assertEquals(0, status.fileCount)
        assertFalse(status.usbConnected)
        assertFalse(status.powerSave)
        assertTrue(status.formattedRtcTime.contains("Belum Diatur"))
    }

    @Test
    fun `test unknown opcode or invalid packet size returns null quietly`() {
        // Unknown opcode (e.g. 0x83)
        val wrongOpcode = ByteArray(14) { 0 }
        wrongOpcode[0] = 0x83.toByte()
        assertNull(StatusParser.parse(wrongOpcode))

        // Too short
        val tooShort = byteArrayOf(0x90.toByte(), 0x01, 0x01)
        assertNull(StatusParser.parse(tooShort))

        // Too long (15 bytes)
        val tooLong = ByteArray(15) { 0 }
        tooLong[0] = 0x90.toByte()
        assertNull(StatusParser.parse(tooLong))

        // Null packet
        assertNull(StatusParser.parse(null))
    }

    @Test
    fun `test Timing Precision SET_TIME 9-byte command serialization with known unixMs`() {
        val testUnixMs = 1791290465123L
        val cmd = BleConstants.buildSetTimeCommand(testUnixMs)

        assertEquals(9, cmd.size)
        assertEquals(0x11.toByte(), cmd[0]) // Opcode 0x11

        val expectedLe = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putLong(testUnixMs).array()
        for (i in 0 until 8) {
            assertEquals(expectedLe[i], cmd[1 + i])
        }
    }

    @Test
    fun `test Timing Precision timezone fix encodes local wall-clock as epoch millis with UTC offset zero`() {
        val ldt = java.time.LocalDateTime.of(2026, 10, 5, 21, 8, 30, 123000000)
        val unixMsLocalWall = ldt.toInstant(java.time.ZoneOffset.UTC).toEpochMilli()
        val cmd = BleConstants.buildSetTimeCommand(unixMsLocalWall)

        assertEquals(9, cmd.size)
        assertEquals(0x11.toByte(), cmd[0])

        val unixSeconds = unixMsLocalWall / 1000L
        val statusBuffer = ByteBuffer.allocate(14).order(ByteOrder.LITTLE_ENDIAN)
        statusBuffer.put(0x90.toByte())
        statusBuffer.put(0x01.toByte()) // measure
        statusBuffer.put(0x01.toByte()) // rtc_ok
        statusBuffer.putInt(unixSeconds.toInt()) // unix_time
        statusBuffer.putInt(0x0001A000)
        statusBuffer.put(1.toByte())
        statusBuffer.put(1.toByte())
        statusBuffer.put(0.toByte())

        val status = StatusParser.parse(statusBuffer.array())
        assertNotNull(status)
        assertEquals("2026-10-05 21:08:30", status!!.formattedRtcTime)
    }

    @Test
    fun `test Timing Precision ACK_SET_TIME 10-byte response parsing result 0 OK with unixMs`() {
        val testUnixMs = 1791290465123L
        val buffer = ByteBuffer.allocate(10).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0x91.toByte()) // B0
        buffer.put(0x00.toByte()) // B1: result = 0
        buffer.putLong(testUnixMs) // B2..B9: adjusted unix_ms u64 LE

        val ack = StatusParser.parseSetTimeAck(buffer.array())
        assertNotNull(ack)
        assertEquals(SetTimeResult.OK, ack!!.result)
        assertTrue(ack.isSuccess)
        assertEquals(testUnixMs, ack.unixMs)
        assertEquals(testUnixMs, ack.adjustedUnixMs)
        assertEquals(testUnixMs / 1000L, ack.adjustedUnixTime)
        assertEquals("RTC disetel", ack.result.label)
        assertTrue(ack.rawHex.startsWith("91 00"))
    }

    @Test
    fun `test Timing Precision ACK_SET_TIME 10-byte response parsing error results 1 and 2`() {
        val buf1 = byteArrayOf(0x91.toByte(), 0x01, 0, 0, 0, 0, 0, 0, 0, 0)
        val ack1 = StatusParser.parseSetTimeAck(buf1)
        assertNotNull(ack1)
        assertEquals(SetTimeResult.NO_RTC, ack1!!.result)
        assertFalse(ack1.isSuccess)
        assertEquals("RTC tidak ada / error", ack1.result.label)

        val buf2 = byteArrayOf(0x91.toByte(), 0x02, 0, 0, 0, 0, 0, 0, 0, 0)
        val ack2 = StatusParser.parseSetTimeAck(buf2)
        assertNotNull(ack2)
        assertEquals(SetTimeResult.BAD_RANGE, ack2!!.result)
        assertFalse(ack2.isSuccess)
        assertEquals("Sync gagal", ack2.result.label)
    }

    @Test
    fun `test Phase C LIST_ITEM 26-byte notify parsing`() {
        // Construct 26 bytes:
        // Byte 0: 0xA1
        // Byte 1..12: "261005201500" ASCII (12 chars)
        // Byte 13: flags = 1 (CLOSED/OK)
        // Byte 14..17: n_records = 500 LE
        // Byte 18..21: byte_size = 8256 LE
        // Byte 22..25: start = 0x00010000 LE
        val buffer = ByteBuffer.allocate(26).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0xA1.toByte())
        buffer.put("261005201500".toByteArray(Charsets.US_ASCII))
        buffer.put(0x01.toByte()) // flags: 1 = CLOSED
        buffer.putInt(500)        // n_records
        buffer.putInt(8256)       // byte_size
        buffer.putInt(0x00010000) // start flash address

        val fileInfo = StatusParser.parseListItem(buffer.array())
        assertNotNull(fileInfo)
        assertEquals("261005201500", fileInfo!!.name)
        assertEquals("261005201500.bin", fileInfo.fileName)
        assertEquals(1, fileInfo.flags)
        assertTrue(fileInfo.isClosed)
        assertFalse(fileInfo.isOpen)
        assertEquals(500L, fileInfo.recordsCount)
        assertEquals(8256L, fileInfo.byteSize)
        assertEquals(0x00010000L, fileInfo.startAddress)
        assertEquals("OK", fileInfo.statusText)
        assertEquals("2026-10-05 20:15:00", fileInfo.formattedDateTime)
    }

    @Test
    fun `test Phase C LIST_ITEM with OPEN flag (sedang measure)`() {
        val buffer = ByteBuffer.allocate(26).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0xA1.toByte())
        buffer.put("261005210000".toByteArray(Charsets.US_ASCII))
        buffer.put(0x02.toByte()) // flags: 2 = OPEN
        buffer.putInt(120)        // n_records
        buffer.putInt(2176)       // byte_size
        buffer.putInt(0x00020000) // start

        val fileInfo = StatusParser.parseListItem(buffer.array())
        assertNotNull(fileInfo)
        assertEquals(2, fileInfo!!.flags)
        assertTrue(fileInfo.isOpen)
        assertFalse(fileInfo.isClosed)
        assertEquals("OPEN", fileInfo.statusText)
    }

    @Test
    fun `test Phase C GET_FILE 19-byte command builder`() {
        val cmd = BleConstants.buildGetFileCommand("261005201500.bin", 180L, 180)
        assertEquals(19, cmd.size)
        assertEquals(0x21.toByte(), cmd[0]) // Opcode 0x21
        val nameInCmd = String(cmd, 1, 12, Charsets.US_ASCII)
        assertEquals("261005201500", nameInCmd)
        val offsetInCmd = ByteBuffer.wrap(cmd, 13, 4).order(ByteOrder.LITTLE_ENDIAN).int
        assertEquals(180, offsetInCmd)
        val maxChunkInCmd = ByteBuffer.wrap(cmd, 17, 2).order(ByteOrder.LITTLE_ENDIAN).short.toInt() and 0xFFFF
        assertEquals(180, maxChunkInCmd)
    }

    @Test
    fun `test Phase C CHUNK 0xB1 response parsing`() {
        // Construct header (12 B) + 4 bytes payload
        val buffer = ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0xB1.toByte()) // B0
        buffer.put(0x00.toByte()) // B1: result = 0 (OK)
        buffer.putInt(0)          // B2..5: offset = 0
        buffer.putInt(8256)       // B6..9: file_size = 8256
        buffer.putShort(4.toShort()) // B10..11: len = 4
        buffer.put(byteArrayOf(0x50, 0x4C, 0x47, 0x31)) // "PLG1"

        val chunk = StatusParser.parseChunk(buffer.array())
        assertNotNull(chunk)
        assertEquals(0, chunk!!.result)
        assertTrue(chunk.isSuccess)
        assertEquals(0L, chunk.offset)
        assertEquals(8256L, chunk.fileSize)
        assertEquals(4, chunk.len)
        assertEquals(4, chunk.data.size)
        assertEquals("PLG1", String(chunk.data, Charsets.US_ASCII))
    }

    @Test
    fun `test Phase C CHUNK error response with short payload`() {
        val shortError = byteArrayOf(0xB1.toByte(), 0x02)
        val chunk = StatusParser.parseChunk(shortError)
        assertNotNull(chunk)
        assertEquals(2, chunk!!.result)
        assertFalse(chunk.isSuccess)
        assertEquals("Sedang merekam (busy OPEN)", chunk.errorMessage)
        assertEquals(0, chunk.data.size)
    }

    @Test
    fun `test Phase C PLG1 v4 file parser for plotting`() {
        // Header 256 B + 2 × 26 B records
        val buffer = ByteBuffer.allocate(256 + 52).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put("PLG1".toByteArray(Charsets.US_ASCII))
        buffer.putShort(4.toShort()) // version = 4
        buffer.putShort(10.toShort()) // period_ms
        buffer.put(11.toByte()) // channels
        buffer.put(26.toByte()) // record_size
        while (buffer.position() < 256) {
            buffer.put(0.toByte())
        }
        // Record 0: t_rel=0, d1=500, d3=1000 (→1.0 g), … d8=100
        buffer.putInt(0)
        buffer.putShort(500.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(1000.toShort())
        for (i in 4..7) buffer.putShort(0.toShort())
        buffer.putShort(100.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(0.toShort())

        // Record 1: t_rel=10, d1=1500
        buffer.putInt(10)
        buffer.putShort(1500.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(2000.toShort())
        for (i in 4..7) buffer.putShort(0.toShort())
        buffer.putShort(200.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(0.toShort())
        buffer.putShort(0.toShort())

        val parsed = StatusParser.parsePlgFile("test.bin", buffer.array())
        assertNotNull(parsed)
        assertEquals(2, parsed!!.records.size)
        assertEquals(4, parsed.version)
        assertEquals(26, parsed.recordSize)
        assertEquals(10, parsed.periodMs)
        assertEquals(0L, parsed.records[0].tRelMs)
        assertEquals(500, parsed.records[0].rawChannel(1))
        assertEquals(10L, parsed.records[1].tRelMs)
        assertEquals(1500, parsed.records[1].rawChannel(1))
        assertEquals(1.0f, parsed.records[0].physicalChannel(3), 0.001f)
        assertEquals(2.0f, parsed.records[1].physicalChannel(3), 0.001f)
    }

    @Test
    fun `test PLG1 v4 rejects legacy 16-byte records`() {
        val buffer = ByteBuffer.allocate(288).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put("PLG1".toByteArray(Charsets.US_ASCII))
        buffer.putShort(2.toShort())
        buffer.putShort(10.toShort())
        buffer.put(8.toByte())
        buffer.put(16.toByte())
        while (buffer.position() < 256) buffer.put(0.toByte())
        for (i in 0 until 32) buffer.put(0.toByte())
        assertNull(StatusParser.parsePlgFile("legacy.bin", buffer.array()))
    }

    @Test
    fun `test Multi-Channel PlgRecord and ChannelStats for PLG1 v4`() {
        val buffer = ByteBuffer.allocate(256 + 52).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put("PLG1".toByteArray(Charsets.US_ASCII))
        buffer.putShort(4.toShort())
        buffer.putShort(20.toShort())
        buffer.put(11.toByte())
        buffer.put(26.toByte())
        while (buffer.position() < 256) buffer.put(0.toByte())

        fun putRec(tRel: Int, d: IntArray) {
            buffer.putInt(tRel)
            for (v in d) buffer.putShort(v.toShort())
        }
        putRec(0, intArrayOf(1000, -50, 1000, -2000, 3000, -400, 500, 600, 100, 200, 300))
        putRec(20, intArrayOf(2000, -150, 2000, -1000, 4000, -300, 600, 650, 110, 210, 310))

        val parsed = StatusParser.parsePlgFile("multich.bin", buffer.array())
        assertNotNull(parsed)
        val rec0 = parsed!!.records[0]

        assertEquals(1000, rec0.rawChannel(1))
        assertEquals(-50, rec0.rawChannel(2))
        assertEquals(1.0f, rec0.physicalChannel(3), 0.001f)
        assertEquals(-2.0f, rec0.physicalChannel(4), 0.001f)
        assertEquals(-40.0f, rec0.physicalChannel(6), 0.001f)
        assertEquals(100f, rec0.physicalChannel(9), 0.001f)

        val statsD3 = parsed.getStatsForChannel(3)
        assertEquals("d3", statsD3.name)
        assertEquals("g", statsD3.unit)
        assertEquals(1.0f, statsD3.min, 0.001f)
        assertEquals(2.0f, statsD3.max, 0.001f)
        assertEquals(1.5f, statsD3.avg, 0.001f)

        val statsD6 = parsed.getStatsForChannel(6)
        assertEquals("°/s", statsD6.unit)
        assertEquals(-40.0f, statsD6.min, 0.001f)
        assertEquals(-30.0f, statsD6.max, 0.001f)
    }

    @Test
    fun `test Timing Precision PLG1 v4 with start_unix_ms and t_rel`() {
        val buffer = ByteBuffer.allocate(256 + 52).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put("PLG1".toByteArray(Charsets.US_ASCII))
        buffer.putShort(4.toShort())
        buffer.putShort(10.toShort())
        buffer.put(11.toByte())
        buffer.put(26.toByte())
        while (buffer.position() < 22) buffer.put(0.toByte())
        val testStartMs = 1791290465123L
        buffer.putLong(testStartMs)
        while (buffer.position() < 256) buffer.put(0.toByte())

        buffer.putInt(0)
        for (i in 1..11) buffer.putShort(if (i == 1) 500 else 0)
        buffer.putInt(10)
        for (i in 1..11) buffer.putShort(if (i == 1) 1500 else 0)

        val parsed = StatusParser.parsePlgFile("precision.bin", buffer.array())
        assertNotNull(parsed)
        assertEquals(4, parsed!!.version)
        assertEquals(testStartMs, parsed.startUnixMs)
        assertTrue(parsed.hasPreciseStartMs)
        assertEquals(testStartMs, parsed.records[0].absoluteUnixMs)
        assertEquals(testStartMs + 10L, parsed.records[1].absoluteUnixMs)
        assertEquals(0L, parsed.records[0].tRelMs)
        assertEquals(10L, parsed.records[1].tRelMs)
    }

    @Test
    fun `test BLE constants match PalmLog specifications`() {
        assertEquals("PalmLog", BleConstants.TARGET_DEVICE_NAME)
        assertTrue(BleConstants.isTargetName("PalmLog1"))
        assertTrue(BleConstants.isTargetName("PalmLog20"))
        assertTrue(BleConstants.isTargetName("palmlog1"))
        assertFalse(BleConstants.isTargetName("Palm"))
        assertFalse(BleConstants.isTargetName(null))
        assertEquals(0x10.toByte(), BleConstants.OPCODE_GET_STATUS)
        assertEquals(0x90.toByte(), BleConstants.OPCODE_ACK_STATUS)
        assertEquals(14, BleConstants.STATUS_PACKET_LENGTH_V1)
        assertEquals(16, BleConstants.STATUS_PACKET_LENGTH)
        assertEquals(0x11.toByte(), BleConstants.OPCODE_SET_TIME)
        assertEquals(9, BleConstants.SET_TIME_COMMAND_LENGTH)
        assertEquals(0x91.toByte(), BleConstants.OPCODE_ACK_SET_TIME)
        assertEquals(10, BleConstants.ACK_SET_TIME_PACKET_LENGTH)
        assertEquals(0x20.toByte(), BleConstants.OPCODE_LIST)
        assertEquals(0xA0.toByte(), BleConstants.OPCODE_LIST_BEGIN)
        assertEquals(0xA1.toByte(), BleConstants.OPCODE_LIST_ITEM)
        assertEquals(0xA2.toByte(), BleConstants.OPCODE_LIST_END)
        assertEquals(0x21.toByte(), BleConstants.OPCODE_GET_FILE)
        assertEquals(0xB1.toByte(), BleConstants.OPCODE_CHUNK)
        assertEquals(180, BleConstants.DEFAULT_MAX_CHUNK)
        assertEquals(247, BleConstants.REQUESTED_MTU)
        assertEquals(29, BleConstants.STREAM_SAMPLE_PACKET_LENGTH)
        assertEquals(26, BleConstants.PLG1_RECORD_SIZE_V4)
        assertEquals(11, BleConstants.PLG1_CHANNELS_V4)
    }

    @Test
    fun `test Phase C binary chunk fragments are not parsed as LIST_ITEM or LIST_END`() {
        // A stray 20-byte packet from binary data where byte 0 happens to be 0xA1 (LIST_ITEM)
        val strayBinaryPacket20 = ByteArray(20) { 0 }
        strayBinaryPacket20[0] = BleConstants.OPCODE_LIST_ITEM
        // LIST_ITEM requires exactly 26 bytes, so 20 bytes must return null
        assertNull(StatusParser.parseListItem(strayBinaryPacket20))

        // A stray packet from binary data where byte 0 happens to be 0x90 (GET_STATUS) but length != 14
        val strayBinaryPacket20Status = ByteArray(20) { 0 }
        strayBinaryPacket20Status[0] = BleConstants.OPCODE_ACK_STATUS
        assertNull(StatusParser.parse(strayBinaryPacket20Status))

        // A stray packet from binary data where byte 0 happens to be 0x91 (SET_TIME) but length != 10
        val strayBinaryPacket20SetTime = ByteArray(20) { 0 }
        strayBinaryPacket20SetTime[0] = BleConstants.OPCODE_ACK_SET_TIME
        assertNull(StatusParser.parseSetTimeAck(strayBinaryPacket20SetTime))
    }

    @Test
    fun `test Phase C CHUNK 0xB1 assembly with 180 byte data payload`() {
        val buffer = ByteBuffer.allocate(192).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put(0xB1.toByte()) // B0: opcode
        buffer.put(0x00.toByte()) // B1: result OK
        buffer.putInt(360)        // B2..B5: offset = 360
        buffer.putInt(5000)       // B6..B9: file_size = 5000
        buffer.putShort(180.toShort()) // B10..B11: len = 180
        val dummyData = ByteArray(180) { it.toByte() }
        buffer.put(dummyData)

        val fullBytes = buffer.array()
        assertEquals(192, fullBytes.size)

        val chunk = StatusParser.parseChunk(fullBytes)
        assertNotNull(chunk)
        assertTrue(chunk!!.isSuccess)
        assertEquals(360L, chunk.offset)
        assertEquals(5000L, chunk.fileSize)
        assertEquals(180, chunk.len)
        assertEquals(180, chunk.data.size)
        assertEquals(0.toByte(), chunk.data[0])
        assertEquals(179.toByte(), chunk.data[179])
    }

    @Test
    fun `test Phase D DELETE_FILE 13-byte command serialization`() {
        val testName = "261005201500"
        val cmd = BleConstants.buildDeleteFileCommand("$testName.bin")
        assertEquals(13, cmd.size)
        assertEquals(0x23.toByte(), cmd[0]) // Opcode 0x23
        val nameInCmd = String(cmd, 1, 12, Charsets.US_ASCII)
        assertEquals(testName, nameInCmd)

        // Test without .bin extension already
        val cmd2 = BleConstants.buildDeleteFileCommand(testName)
        assertEquals(13, cmd2.size)
        assertEquals(0x23.toByte(), cmd2[0])
        assertEquals(testName, String(cmd2, 1, 12, Charsets.US_ASCII))
    }

    @Test
    fun `test Phase D ACK_DELETE 2-byte response parsing for all result codes`() {
        // Result 0: OK
        val okPacket = byteArrayOf(0xA3.toByte(), 0x00)
        val okRes = StatusParser.parseDeleteAck(okPacket)
        assertNotNull(okRes)
        assertEquals(0, okRes)

        // Result 1: File tidak ada di board
        val notFoundPacket = byteArrayOf(0xA3.toByte(), 0x01)
        val notFoundRes = StatusParser.parseDeleteAck(notFoundPacket)
        assertNotNull(notFoundRes)
        assertEquals(1, notFoundRes)

        // Result 2: Sedang measure / OPEN
        val busyPacket = byteArrayOf(0xA3.toByte(), 0x02)
        val busyRes = StatusParser.parseDeleteAck(busyPacket)
        assertNotNull(busyRes)
        assertEquals(2, busyRes)

        // Invalid: Wrong opcode
        val wrongOpcode = byteArrayOf(0xA1.toByte(), 0x00)
        assertNull(StatusParser.parseDeleteAck(wrongOpcode))

        // Invalid: Wrong length (3 bytes or 1 byte)
        val wrongLen = byteArrayOf(0xA3.toByte(), 0x00, 0x00)
        assertNull(StatusParser.parseDeleteAck(wrongLen))
        val shortLen = byteArrayOf(0xA3.toByte())
        assertNull(StatusParser.parseDeleteAck(shortLen))
    }

    @Test
    fun `test Phase D FORMAT_FLASH 2-byte command contains 0x24 and 0xA5 confirm magic`() {
        val cmd = BleConstants.CMD_FORMAT
        assertEquals(2, cmd.size)
        assertEquals(0x24.toByte(), cmd[0]) // Opcode 0x24
        assertEquals(0xA5.toByte(), cmd[1]) // Confirm magic 0xA5
    }

    @Test
    fun `test Phase D ACK_FORMAT 2-byte response parsing for all result codes`() {
        // Result 0: OK
        val okPacket = byteArrayOf(0xA4.toByte(), 0x00)
        val okRes = StatusParser.parseFormatAck(okPacket)
        assertNotNull(okRes)
        assertEquals(0, okRes)

        // Result 1: Stop measure dulu
        val busyPacket = byteArrayOf(0xA4.toByte(), 0x01)
        val busyRes = StatusParser.parseFormatAck(busyPacket)
        assertNotNull(busyRes)
        assertEquals(1, busyRes)

        // Result 2: Format ditolak (confirm)
        val rejectPacket = byteArrayOf(0xA4.toByte(), 0x02)
        val rejectRes = StatusParser.parseFormatAck(rejectPacket)
        assertNotNull(rejectRes)
        assertEquals(2, rejectRes)

        // Invalid: Wrong opcode or length
        val wrongOpcode = byteArrayOf(0xA2.toByte(), 0x00)
        assertNull(StatusParser.parseFormatAck(wrongOpcode))
        val wrongLen = byteArrayOf(0xA4.toByte(), 0x00, 0x00)
        assertNull(StatusParser.parseFormatAck(wrongLen))
    }
}
