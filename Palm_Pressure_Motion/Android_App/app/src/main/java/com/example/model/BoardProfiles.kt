package com.example.model

/**
 * Profil flash untuk board yang protokolnya sama (PLG1 v4 / NUS) tetapi ukuran chip berbeda.
 * Dipilih dari nama advertising lengkap, bukan dari awalan "PalmLog".
 */
data class BoardProfile(
    val advertisedName: String,
    val flashSizeBytes: Long,
    val sizeLabel: String,
    val formatTimeoutMs: Long,
    val formatDurationHint: String
)

object BoardProfiles {
    val PALM_LOG_20 = BoardProfile(
        advertisedName = "PalmLog20",
        flashSizeBytes = 4L * 1024L * 1024L,
        sizeLabel = "4 MB",
        formatTimeoutMs = 65_000L,
        formatDurationHint = "10–40 detik"
    )

    val PALM_LOG_1 = BoardProfile(
        advertisedName = "PalmLog1",
        flashSizeBytes = 16L * 1024L * 1024L,
        sizeLabel = "16 MB",
        formatTimeoutMs = 120_000L,
        formatDurationHint = "sekitar 40 detik, bisa lebih lama"
    )

    /** Dipakai bila nama tidak dikenali, supaya chip 16 MB tidak terputus di tengah erase. */
    const val UNKNOWN_FORMAT_TIMEOUT_MS = 120_000L

    fun fromAdvertisedName(name: String?): BoardProfile? {
        val trimmed = name?.trim().orEmpty()
        return when {
            trimmed.equals(PALM_LOG_1.advertisedName, ignoreCase = true) -> PALM_LOG_1
            trimmed.equals(PALM_LOG_20.advertisedName, ignoreCase = true) -> PALM_LOG_20
            else -> null
        }
    }
}
