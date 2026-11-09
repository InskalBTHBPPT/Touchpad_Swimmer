package com.example.storage

import android.content.Context
import android.os.Environment
import com.example.model.LogFileInfo
import java.io.File
import java.util.Locale

/**
 * Penyimpanan log per board:
 *   …/Download/PalmLog/<AA-BB-CC-DD-EE-FF>/YYMMDDHHMMSS.bin
 * File lama di root PalmLog/ dipindah ke folder [_legacy] sekali.
 */
object BoardStorage {
    const val LEGACY_FOLDER = "_legacy"

    fun normalizeMac(address: String): String =
        address.trim().uppercase(Locale.US).replace(':', '-')

    fun displayMac(normalizedOrRaw: String): String {
        val n = normalizeMac(normalizedOrRaw)
        if (n == LEGACY_FOLDER) return "Arsip lama (tanpa MAC)"
        return n.replace('-', ':')
    }

    fun rootDir(context: Context): File {
        val base = context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS) ?: context.filesDir
        return File(base, "PalmLog").apply { mkdirs() }
    }

    fun boardDir(root: File, macNormalized: String): File =
        File(root, macNormalized).apply { mkdirs() }

    fun fileInBoard(root: File, macNormalized: String, fileName: String): File =
        File(boardDir(root, macNormalized), fileName)

    /** Pindahkan *.bin di root PalmLog/ ke _legacy/ (sekali, non-destruktif). */
    fun migrateLegacyRootBins(root: File) {
        val bins = root.listFiles { f -> f.isFile && f.name.endsWith(".bin", ignoreCase = true) }
            ?: return
        if (bins.isEmpty()) return
        val legacy = boardDir(root, LEGACY_FOLDER)
        for (f in bins) {
            val dest = File(legacy, f.name)
            if (!dest.exists()) {
                f.renameTo(dest)
            }
        }
    }

    fun listLocalBinFiles(boardDir: File): List<LogFileInfo> {
        val files = boardDir.listFiles { f ->
            f.isFile && f.name.endsWith(".bin", ignoreCase = true)
        } ?: return emptyList()

        return files.sortedByDescending { it.name }.map { f ->
            val baseName = f.name.removeSuffix(".bin").removeSuffix(".BIN")
            val name12 = if (baseName.length >= 12) baseName.take(12) else baseName
            val size = f.length()
            val records = if (size > 256L) (size - 256L) / 26L else 0L
            LogFileInfo(
                name = name12,
                flags = 1, // treat local archive as CLOSED/OK
                recordsCount = records,
                byteSize = size,
                startAddress = 0L,
                isDownloaded = true,
                localFilePath = f.absolutePath,
                isLocalOnly = true
            )
        }
    }

    fun countLocalBins(boardDir: File): Int =
        boardDir.listFiles { f -> f.isFile && f.name.endsWith(".bin", ignoreCase = true) }?.size ?: 0
}

data class KnownBoard(
    val macNormalized: String,
    val lastSeenName: String = "PalmLog",
    val localFileCount: Int = 0
) {
    val displayAddress: String
        get() = BoardStorage.displayMac(macNormalized)

    val isLegacy: Boolean
        get() = macNormalized == BoardStorage.LEGACY_FOLDER
}

/**
 * Riwayat MAC yang pernah terhubung (SharedPreferences).
 */
class BoardHistoryStore(context: Context) {
    private val prefs = context.getSharedPreferences("palmlog_board_history", Context.MODE_PRIVATE)

    fun remember(address: String, deviceName: String? = null) {
        val mac = BoardStorage.normalizeMac(address)
        if (mac.isBlank() || mac == BoardStorage.LEGACY_FOLDER) return
        val set = prefs.getStringSet(KEY_MACS, emptySet())?.toMutableSet() ?: mutableSetOf()
        set.add(mac)
        prefs.edit()
            .putStringSet(KEY_MACS, set)
            .putString(KEY_NAME_PREFIX + mac, deviceName ?: "PalmLog")
            .putLong(KEY_LAST_PREFIX + mac, System.currentTimeMillis())
            .apply()
    }

    fun knownMacs(): List<String> {
        val set = prefs.getStringSet(KEY_MACS, emptySet()) ?: emptySet()
        return set.sortedByDescending { prefs.getLong(KEY_LAST_PREFIX + it, 0L) }
    }

    fun displayName(macNormalized: String): String =
        prefs.getString(KEY_NAME_PREFIX + macNormalized, "PalmLog") ?: "PalmLog"

    companion object {
        private const val KEY_MACS = "macs"
        private const val KEY_NAME_PREFIX = "name_"
        private const val KEY_LAST_PREFIX = "last_"
    }
}
