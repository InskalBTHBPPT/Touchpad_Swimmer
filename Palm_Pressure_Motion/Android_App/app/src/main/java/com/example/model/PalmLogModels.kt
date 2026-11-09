package com.example.model

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Parsed GET_STATUS board response.
 * Byte 0:     0x90 (ACK opcode)
 * Byte 1:     measure (u8: 0=F, 1=T)
 * Byte 2:     rtc_ok (u8: 0 or 1)
 * Byte 3..6:  unix_time (u32 LE, 0 if rtc_ok=0)
 * Byte 7..10: next_free (u32 LE flash address)
 * Byte 11:    file_count (u8: 0..48)
 * Byte 12:    usb (u8: 0=Baterai, 1=USB) — flag sumber, bukan tegangan
 * Byte 13:    pwr_save (u8: 0=Off, 1=On)
 * Byte 14..15: vbat_mV (u16 LE), hanya jika paket 16 byte
 */
data class PalmLogStatus(
    val measure: Boolean,
    val rtcOk: Boolean,
    val unixTime: Long,
    val nextFreeAddress: Long,
    val fileCount: Int,
    val usbConnected: Boolean,
    val powerSave: Boolean,
    val batteryMv: Int? = null,
    val rawBytes: ByteArray,
    val receivedAtMillis: Long = System.currentTimeMillis()
) {
    /**
     * Formats flash address in standard hex notation: e.g. 0x0001A000
     */
    val formattedNextFree: String
        get() = String.format(Locale.US, "0x%08X", nextFreeAddress)

    /**
     * Formats RTC datetime from unix timestamp (wall-clock encoded with UTC offset zero)
     */
    val formattedRtcTime: String
        get() {
            if (!rtcOk || unixTime <= 0L) {
                return "Belum Diatur (rtc_ok = 0)"
            }
            return try {
                val sdfUtc = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).apply {
                    timeZone = TimeZone.getTimeZone("UTC")
                }
                val date = Date(unixTime * 1000L)
                sdfUtc.format(date)
            } catch (e: Exception) {
                "Unix: $unixTime"
            }
        }

    /**
     * Formats raw bytes to uppercase hex string with spacing.
     */
    val rawHex: String
        get() = rawBytes.joinToString(" ") { "%02X".format(it) }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as PalmLogStatus

        if (measure != other.measure) return false
        if (rtcOk != other.rtcOk) return false
        if (unixTime != other.unixTime) return false
        if (nextFreeAddress != other.nextFreeAddress) return false
        if (fileCount != other.fileCount) return false
        if (usbConnected != other.usbConnected) return false
        if (powerSave != other.powerSave) return false
        if (batteryMv != other.batteryMv) return false
        if (!rawBytes.contentEquals(other.rawBytes)) return false

        return true
    }

    override fun hashCode(): Int {
        var result = measure.hashCode()
        result = 31 * result + rtcOk.hashCode()
        result = 31 * result + unixTime.hashCode()
        result = 31 * result + nextFreeAddress.hashCode()
        result = 31 * result + fileCount
        result = 31 * result + usbConnected.hashCode()
        result = 31 * result + powerSave.hashCode()
        result = 31 * result + (batteryMv ?: 0)
        result = 31 * result + rawBytes.contentHashCode()
        return result
    }
}

/**
 * BLE Connection states for PalmLog
 */
sealed interface BleConnectionState {
    data object Disconnected : BleConnectionState
    data object Scanning : BleConnectionState
    data class Connecting(val deviceName: String, val address: String) : BleConnectionState
    data class Connected(
        val deviceName: String,
        val address: String,
        val mtu: Int = 23,
        val isNotifyEnabled: Boolean = false
    ) : BleConnectionState
    data class Error(val message: String) : BleConnectionState
}

/**
 * Scanned BLE device
 */
data class DiscoveredDevice(
    val name: String,
    val address: String,
    val rssi: Int,
    val isTarget: Boolean
) {
    val signalStrengthLevel: String
        get() = when {
            rssi >= -60 -> "Sangat Kuat"
            rssi >= -75 -> "Kuat"
            rssi >= -85 -> "Sedang"
            else -> "Lemah"
        }
}

/**
 * Result codes for Phase B SET_TIME response:
 * 0 = OK, 1 = no RTC, 2 = bad range
 */
enum class SetTimeResult(val code: Int, val label: String) {
    OK(0, "RTC disetel"),
    NO_RTC(1, "RTC tidak ada / error"),
    BAD_RANGE(2, "Sync gagal"),
    UNKNOWN(-1, "Sync gagal");

    companion object {
        fun fromCode(code: Int): SetTimeResult = when (code) {
            0 -> OK
            1 -> NO_RTC
            2 -> BAD_RANGE
            else -> UNKNOWN
        }
    }
}

/**
 * Timing Precision Response: ACK_SET_TIME (Opcode 0x91, 10 bytes total):
 * Byte 0: 0x91
 * Byte 1: result u8: 0=OK, 1=no RTC, 2=bad range
 * Byte 2..9: unix_ms u64 LE after adjust (0 if failed)
 */
data class SetTimeAck(
    val result: SetTimeResult,
    val adjustedUnixMs: Long,
    val rawBytes: ByteArray,
    val receivedAtMillis: Long = System.currentTimeMillis()
) {
    val isSuccess: Boolean
        get() = result == SetTimeResult.OK

    val unixMs: Long
        get() = adjustedUnixMs

    val adjustedUnixTime: Long
        get() = adjustedUnixMs / 1000L

    val formattedAdjustedTime: String
        get() {
            if (adjustedUnixMs <= 0L) return "-"
            return try {
                val sdfUtc = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).apply {
                    timeZone = TimeZone.getTimeZone("UTC")
                }
                val date = Date(adjustedUnixMs)
                sdfUtc.format(date)
            } catch (e: Exception) {
                "Unix ms: $adjustedUnixMs"
            }
        }

    val rawHex: String
        get() = rawBytes.joinToString(" ") { "%02X".format(it) }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as SetTimeAck

        if (result != other.result) return false
        if (adjustedUnixMs != other.adjustedUnixMs) return false
        if (!rawBytes.contentEquals(other.rawBytes)) return false

        return true
    }

    override fun hashCode(): Int {
        var res = result.hashCode()
        res = 31 * res + adjustedUnixMs.hashCode()
        res = 31 * res + rawBytes.contentHashCode()
        return res
    }
}

/**
 * Phase C: Log file entry returned by LIST_ITEM (Opcode 0xA1, 26 bytes).
 * Byte 1..12: name[12] ASCII YYMMDDHHMMSS
 * Byte 13: flags u8 (1=CLOSED/OK, 2=OPEN)
 * Byte 14..17: n_records u32 LE
 * Byte 18..21: byte_size u32 LE
 * Byte 22..25: start flash address u32 LE
 */
data class LogFileInfo(
    val name: String,
    val flags: Int,
    val recordsCount: Long,
    val byteSize: Long,
    val startAddress: Long,
    val isDownloaded: Boolean = false,
    val localFilePath: String? = null,
    /** True jika entri hanya dari arsip HP (tidak ada di LIST board saat ini). */
    val isLocalOnly: Boolean = false
) {
    val fileName: String
        get() = if (name.endsWith(".bin")) name else "$name.bin"

    val isClosed: Boolean
        get() = flags == 1

    val isOpen: Boolean
        get() = flags == 2

    val statusText: String
        get() = when (flags) {
            1 -> "OK"
            2 -> "OPEN"
            else -> "STATUS $flags"
        }

    val formattedSize: String
        get() = if (byteSize >= 1024) {
            String.format(Locale.US, "%.1f KB", byteSize / 1024.0)
        } else {
            "$byteSize B"
        }

    val formattedDateTime: String
        get() = try {
            if (name.length >= 12) {
                val yy = name.substring(0, 2)
                val mm = name.substring(2, 4)
                val dd = name.substring(4, 6)
                val hh = name.substring(6, 8)
                val min = name.substring(8, 10)
                val ss = name.substring(10, 12)
                "20$yy-$mm-$dd $hh:$min:$ss"
            } else {
                name
            }
        } catch (e: Exception) {
            name
        }
}

/**
 * Sampel live 0xB2 (FW 3.1.x): seq u16 + SampleRec 26 B
 * (= t_rel_ms u32 + d1..d11 int16). Total paket 29 B.
 */
data class StreamSample(
    val seq: Int,
    val tRelMs: Long,
    val channels: IntArray
) {
    fun rawChannel(channelNum: Int): Int =
        channels.getOrElse(channelNum - 1) { 0 }

    fun physicalChannel(channelNum: Int): Float {
        val raw = rawChannel(channelNum).toFloat()
        return when (channelNum) {
            in 3..5 -> raw / 1000f
            in 6..8 -> raw / 10f
            else -> raw
        }
    }
}

/**
 * Phase C: CHUNK Response (Opcode 0xB1).
 * Byte 0: 0xB1
 * Byte 1: result: 0=OK, 1=not found, 2=busy OPEN, 3=bad offset
 * Byte 2..5: offset u32 LE
 * Byte 6..9: file_size u32 LE
 * Byte 10..11: len u16 LE
 * Byte 12..: data[len]
 */
data class FileChunkResponse(
    val result: Int,
    val offset: Long,
    val fileSize: Long,
    val len: Int,
    val data: ByteArray
) {
    val isSuccess: Boolean
        get() = result == 0

    val errorMessage: String?
        get() = when (result) {
            0 -> null
            1 -> "Berkas tidak ditemukan"
            2 -> "Sedang merekam (busy OPEN)"
            3 -> "Offset tidak valid"
            else -> "Error unduhan ($result)"
        }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as FileChunkResponse

        if (result != other.result) return false
        if (offset != other.offset) return false
        if (fileSize != other.fileSize) return false
        if (len != other.len) return false
        if (!data.contentEquals(other.data)) return false

        return true
    }

    override fun hashCode(): Int {
        var res = result
        res = 31 * res + offset.hashCode()
        res = 31 * res + fileSize.hashCode()
        res = 31 * res + len
        res = 31 * res + data.contentHashCode()
        return res
    }
}

/**
 * Phase C: Active file download status.
 */
data class FileDownloadState(
    val fileName: String,
    val currentBytes: Long = 0L,
    val totalBytes: Long = 0L,
    val isDownloading: Boolean = false,
    val errorMessage: String? = null,
    val completedFilePath: String? = null
) {
    val progress: Float
        get() = if (totalBytes > 0L) (currentBytes.toFloat() / totalBytes.toFloat()).coerceIn(0f, 1f) else 0f

    val progressPercent: Int
        get() = (progress * 100).toInt()
}

/**
 * PLG1 v4 record (FW 3.1.x): 26 B
 * t_rel_ms u32 + d1..d11 int16 (LE).
 * Fisik: d3..d5 mg→g (/1000), d6..d8 0.1°/s→°/s (/10), d9..d11 µT.
 */
data class PlgRecord(
    val index: Int,
    val tRelMs: Long,
    val channels: IntArray,
    val absoluteUnixMs: Long = 0L
) {
    /** Legacy alias: waktu relatif terukur (bukan index×period). */
    val timeMs: Long get() = tRelMs

    fun rawChannel(channelNum: Int): Int =
        channels.getOrElse(channelNum - 1) { 0 }

    fun physicalChannel(channelNum: Int): Float {
        val raw = rawChannel(channelNum).toFloat()
        return when (channelNum) {
            in 3..5 -> raw / 1000f
            in 6..8 -> raw / 10f
            else -> raw
        }
    }

    companion object {
        fun unitFor(channelNum: Int): String = when (channelNum) {
            in 3..5 -> "g"
            in 6..8 -> "°/s"
            in 9..11 -> "µT"
            else -> ""
        }
    }
}

enum class PlotSensorGroup(
    val label: String,
    val unitLabel: String,
    val channelNums: IntArray
) {
    GENERAL("Umum", "", intArrayOf(1, 2)),
    ACCEL("Accel", "g", intArrayOf(3, 4, 5)),
    GYRO("Gyro", "°/s", intArrayOf(6, 7, 8)),
    MAG("Mag", "µT", intArrayOf(9, 10, 11));
}

data class ChannelStats(
    val channelNum: Int,
    val name: String,
    val unit: String,
    val min: Float,
    val max: Float,
    val avg: Float
)

/**
 * Parsed PLG1 v4 header + records.
 */
data class PlgParsedData(
    val fileName: String,
    val version: Int,
    val periodMs: Int,
    val channels: Int,
    val recordSize: Int,
    val records: List<PlgRecord>,
    val startUnixMs: Long = 0L
) {
    val hasPreciseStartMs: Boolean
        get() = version >= 2 && startUnixMs != 0L

    val formattedStartMsText: String
        get() {
            if (startUnixMs <= 0L) return "-"
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
            return sdf.format(Date(startUnixMs))
        }

    val formattedStartCompact: String
        get() {
            if (startUnixMs <= 0L) return "-"
            val sdf = SimpleDateFormat("yyMMddHHmmss.SSS", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
            return sdf.format(Date(startUnixMs))
        }

    fun formatTimestampCompact(absUnixMs: Long): String {
        val sdf = SimpleDateFormat("yyMMddHHmmss.SSS", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        return sdf.format(Date(absUnixMs))
    }

    val totalDurationMs: Long
        get() {
            if (records.isEmpty()) return 0L
            val first = records.first().tRelMs
            val last = records.last().tRelMs
            return (last - first).coerceAtLeast(0L)
        }

    val durationText: String
        get() {
            val totalSec = totalDurationMs / 1000.0
            return String.format(Locale.US, "%.1f detik (%d rekaman)", totalSec, records.size)
        }

    fun getStatsForChannel(channelNum: Int): ChannelStats {
        val unit = PlgRecord.unitFor(channelNum)
        if (records.isEmpty()) {
            return ChannelStats(channelNum, "d$channelNum", unit, 0f, 0f, 0f)
        }
        var minVal = Float.POSITIVE_INFINITY
        var maxVal = Float.NEGATIVE_INFINITY
        var sumVal = 0.0
        for (rec in records) {
            val v = rec.physicalChannel(channelNum)
            if (v < minVal) minVal = v
            if (v > maxVal) maxVal = v
            sumVal += v
        }
        return ChannelStats(
            channelNum = channelNum,
            name = "d$channelNum",
            unit = unit,
            min = minVal,
            max = maxVal,
            avg = (sumVal / records.size).toFloat()
        )
    }
}
