package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material.icons.filled.DeleteForever
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.BleConnectionState
import com.example.model.FileDownloadState
import com.example.model.LogFileInfo
import com.example.model.PalmLogStatus
import com.example.model.PlgParsedData
import java.util.Locale
import com.example.storage.KnownBoard
import com.example.storage.shareBinFiles
import java.io.File
import com.example.ui.theme.*

@Composable
fun FileTabContent(
    connectionState: BleConnectionState,
    fileList: List<LogFileInfo>,
    knownBoards: List<KnownBoard>,
    selectedBoardMac: String?,
    connectedMacNormalized: String?,
    isViewingConnectedBoard: Boolean,
    pendingDownloadCount: Int,
    isRefreshingList: Boolean,
    downloadState: FileDownloadState?,
    plotData: PlgParsedData?,
    isMeasureActive: Boolean,
    boardStatus: PalmLogStatus?,
    isDeletingBoard: Boolean,
    deletingBoardFileName: String?,
    isFormattingFlash: Boolean,
    formatProgressText: String?,
    onSelectBoardMac: (String) -> Unit,
    onRefreshList: () -> Unit,
    onDownloadFile: (LogFileInfo) -> Unit,
    onSyncAllNew: () -> Unit,
    onPlotFile: (LogFileInfo) -> Unit,
    onDeleteLocalFile: (LogFileInfo) -> Unit,
    onDeleteBoardFile: (LogFileInfo) -> Unit,
    onFormatFlashBoard: () -> Unit,
    onDismissPlot: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val isConnected = connectionState is BleConnectionState.Connected
    val isDownloading = downloadState?.isDownloading == true
    val canUseBoardBle = isViewingConnectedBoard
    val localFiles = fileList.mapNotNull { info ->
        info.localFilePath?.let { path -> File(path) }?.takeIf { it.exists() && it.length() > 0L }
    }

    // Confirmation dialog states
    var fileToDeleteLocal by remember { mutableStateOf<LogFileInfo?>(null) }
    var fileToDeleteBoard by remember { mutableStateOf<LogFileInfo?>(null) }
    var showFormatDialog by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .testTag("file_tab_content"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        BoardSelectorRow(
            knownBoards = knownBoards,
            selectedBoardMac = selectedBoardMac,
            connectedMacNormalized = connectedMacNormalized,
            canRefresh = canUseBoardBle && !isDownloading && !isFormattingFlash,
            isRefreshing = isRefreshingList,
            showArchiveHint = isConnected && !canUseBoardBle,
            onSelectBoardMac = onSelectBoardMac,
            onRefreshList = onRefreshList
        )

        if (canUseBoardBle) {
            BoardCapacityCard(
                boardStatus = boardStatus,
                canFormat = !isMeasureActive && !isRefreshingList && !isDownloading && !isFormattingFlash,
                isMeasureActive = isMeasureActive,
                onOpenFormatDialog = { showFormatDialog = true }
            )
        }

        // 2. Active Format Flash Progress Card
        if (isFormattingFlash) {
            FormatProgressCard(progressText = formatProgressText)
        }

        // 3. Batch Sync Option Banner (If there are pending closed files not yet on phone)
        if (canUseBoardBle && pendingDownloadCount > 0 && !isDownloading && !isFormattingFlash) {
            BatchSyncCard(
                pendingCount = pendingDownloadCount,
                onSyncAllNew = onSyncAllNew
            )
        }

        // 4. Active Download Progress Bar Card
        if (downloadState != null && (downloadState.isDownloading || downloadState.errorMessage != null)) {
            DownloadProgressCard(downloadState = downloadState)
        }

        // 5. File List or Empty State
        if (fileList.isEmpty()) {
            EmptyFileCard(
                isConnected = isConnected,
                canUseBoardBle = canUseBoardBle,
                hasKnownBoards = knownBoards.isNotEmpty(),
                isRefreshing = isRefreshingList,
                isDownloading = isDownloading,
                isFormatting = isFormattingFlash,
                onRefreshList = onRefreshList
            )
        } else {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (localFiles.isNotEmpty()) {
                    OutlinedButton(
                        onClick = { shareBinFiles(context, localFiles) },
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(40.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Share,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Bagikan semua di HP (${localFiles.size})",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                    }
                }
                fileList.forEach { fileInfo ->
                    FileItemCard(
                        fileInfo = fileInfo,
                        canUseBoardBle = canUseBoardBle,
                        isDownloadingCurrent = downloadState?.fileName?.startsWith(fileInfo.fileName) == true && downloadState.isDownloading,
                        isDeletingCurrent = isDeletingBoard && deletingBoardFileName == fileInfo.fileName,
                        onDownload = { onDownloadFile(fileInfo) },
                        onPlot = { onPlotFile(fileInfo) },
                        onDeleteLocal = { fileToDeleteLocal = fileInfo },
                        onDeleteBoard = { fileToDeleteBoard = fileInfo },
                        onShare = {
                            val path = fileInfo.localFilePath ?: return@FileItemCard
                            shareBinFiles(context, listOf(File(path)))
                        }
                    )
                }
            }
        }
    }

    // Modal: Multi-Channel Plot Dialog
    if (plotData != null) {
        MultiChannelPlotDialog(
            plotData = plotData,
            onDismiss = onDismissPlot
        )
    }

    // Dialog 1: Confirm Hapus di HP saja (no BLE)
    fileToDeleteLocal?.let { file ->
        AlertDialog(
            onDismissRequest = { fileToDeleteLocal = null },
            icon = {
                Icon(
                    imageVector = Icons.Default.DeleteOutline,
                    contentDescription = null,
                    tint = Amber400
                )
            },
            title = {
                Text(
                    text = "Hapus di HP Saja",
                    fontWeight = FontWeight.Bold,
                    color = Slate100
                )
            },
            text = {
                Text(
                    text = "Hapus salinan ${file.fileName} di penyimpanan HP? Berkas di flash board tidak berubah.",
                    fontSize = 13.sp,
                    color = Slate300
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        onDeleteLocalFile(file)
                        fileToDeleteLocal = null
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Amber400,
                        contentColor = Slate950
                    )
                ) {
                    Text("Hapus di HP", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { fileToDeleteLocal = null }) {
                    Text("Batal", color = Slate400)
                }
            },
            containerColor = Slate850,
            tonalElevation = 6.dp
        )
    }

    // Dialog 2: Confirm Hapus di Board (BLE 0x23)
    fileToDeleteBoard?.let { file ->
        AlertDialog(
            onDismissRequest = { fileToDeleteBoard = null },
            icon = {
                Icon(
                    imageVector = Icons.Default.DeleteForever,
                    contentDescription = null,
                    tint = Red400
                )
            },
            title = {
                Text(
                    text = "Hapus di Flash Board",
                    fontWeight = FontWeight.Bold,
                    color = Slate100
                )
            },
            text = {
                Text(
                    text = "Hapus ${file.name} di flash board? Salinan di HP (jika ada) tidak ikut terhapus.\n\nKapasitas flash tidak kembali, kecuali berkas ini tepat di ujung alokasi. Ruang penuh kembali hanya setelah Format Flash Board.",
                    fontSize = 13.sp,
                    color = Slate300
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        onDeleteBoardFile(file)
                        fileToDeleteBoard = null
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Red500,
                        contentColor = Slate100
                    )
                ) {
                    Text("Hapus di Board", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { fileToDeleteBoard = null }) {
                    Text("Batal", color = Slate400)
                }
            },
            containerColor = Slate850,
            tonalElevation = 6.dp
        )
    }

    // Dialog 3: Strong Confirm Format Flash 4 MB (BLE 0x24 + 0xA5)
    if (showFormatDialog) {
        AlertDialog(
            onDismissRequest = { showFormatDialog = false },
            icon = {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = Red400
                )
            },
            title = {
                Text(
                    text = "Format Flash Board (4 MB)",
                    fontWeight = FontWeight.Bold,
                    color = Red400
                )
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "Menghapus SEMUA file di board (chip erase ~4 MB). Lanjut?",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Slate100
                    )
                    Text(
                        text = "• Seluruh data di memori flash board akan dihapus permanen.\n• Proses chip erase membutuhkan waktu sekitar 10–40 detik.\n• Salinan berkas yang sudah diunduh di HP TIDAK ikut terhapus.",
                        fontSize = 12.sp,
                        color = Slate300,
                        lineHeight = 18.sp
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        showFormatDialog = false
                        onFormatFlashBoard()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Red500,
                        contentColor = Slate100
                    )
                ) {
                    Text("Format Flash (4 MB)", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showFormatDialog = false }) {
                    Text("Batal", color = Slate400)
                }
            },
            containerColor = Slate850,
            tonalElevation = 6.dp
        )
    }
}

@Composable
private fun BoardSelectorRow(
    knownBoards: List<KnownBoard>,
    selectedBoardMac: String?,
    connectedMacNormalized: String?,
    canRefresh: Boolean,
    isRefreshing: Boolean,
    showArchiveHint: Boolean,
    onSelectBoardMac: (String) -> Unit,
    onRefreshList: () -> Unit,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "refresh_list_spin")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "spin"
    )

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Text(
            text = "Board (MAC)",
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = Slate400
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (knownBoards.isEmpty()) {
                Text(
                    text = "Belum ada board tersimpan.",
                    fontSize = 12.sp,
                    color = Slate500,
                    modifier = Modifier.weight(1f)
                )
            } else {
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    knownBoards.forEach { board ->
                        val selected = board.macNormalized == selectedBoardMac
                        val isLive = connectedMacNormalized != null &&
                            board.macNormalized == connectedMacNormalized
                        FilterChip(
                            selected = selected,
                            onClick = { onSelectBoardMac(board.macNormalized) },
                            label = {
                                Column {
                                    Text(
                                        text = board.lastSeenName,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1
                                    )
                                    Text(
                                        text = board.displayAddress,
                                        fontSize = 10.sp,
                                        fontFamily = FontFamily.Monospace,
                                        maxLines = 1
                                    )
                                }
                            },
                            leadingIcon = if (isLive) {
                                {
                                    Icon(
                                        imageVector = Icons.Default.Memory,
                                        contentDescription = null,
                                        modifier = Modifier.size(14.dp)
                                    )
                                }
                            } else null,
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Sky400.copy(alpha = 0.25f),
                                selectedLabelColor = Slate100,
                                selectedLeadingIconColor = Emerald300,
                                containerColor = Slate850,
                                labelColor = Slate300,
                                iconColor = Slate500
                            ),
                            modifier = Modifier.testTag("board_chip_${board.macNormalized}")
                        )
                    }
                }
            }
            Button(
                onClick = onRefreshList,
                enabled = canRefresh && !isRefreshing,
                shape = RoundedCornerShape(10.dp),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Slate800,
                    contentColor = Sky400,
                    disabledContainerColor = Slate850,
                    disabledContentColor = Slate600
                ),
                modifier = Modifier
                    .height(40.dp)
                    .testTag("refresh_file_list_button")
            ) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = "Refresh daftar",
                    modifier = Modifier
                        .size(16.dp)
                        .rotate(if (isRefreshing) rotation else 0f)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = if (isRefreshing) "..." else "Refresh",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp,
                    maxLines = 1
                )
            }
        }
        if (showArchiveHint) {
            Text(
                text = "Mode arsip HP. Pilih board yang sedang terhubung untuk refresh / unduh / hapus flash.",
                fontSize = 11.sp,
                color = Slate400
            )
        }
    }
}

@Composable
private fun BoardCapacityCard(
    boardStatus: PalmLogStatus?,
    canFormat: Boolean,
    isMeasureActive: Boolean,
    onOpenFormatDialog: () -> Unit,
    modifier: Modifier = Modifier
) {
    val flashSize = 4L * 1024L * 1024L
    val nextFree = boardStatus?.nextFreeAddress
    val freeBytes = if (nextFree != null && nextFree in 0x1000L..flashSize) {
        flashSize - nextFree
    } else {
        null
    }
    val remainText = freeBytes?.let { formatRemainTime(it) } ?: "—"
    val freeText = freeBytes?.let { formatByteSize(it) } ?: "—"
    val countText = boardStatus?.fileCount?.toString() ?: "—"

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(16.dp))
            .padding(14.dp)
            .testTag("board_capacity_card")
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            CapacityRow(label = "Berkas di board", value = countText)
            CapacityRow(label = "Sisa kapasitas", value = freeText)
            CapacityRow(label = "Sisa waktu ukur", value = remainText)
            Text(
                text = "Perkiraan dari next_free, 26 B/sample (PLG1 v4), periode 10 ms. Hapus di tengah tidak menambah sisa ini.",
                fontSize = 10.sp,
                color = Slate500
            )
            if (isMeasureActive) {
                Text(
                    text = "Pengukuran aktif. Format dinonaktifkan — stop measure dulu.",
                    fontSize = 11.sp,
                    color = Amber400
                )
            }
            OutlinedButton(
                onClick = onOpenFormatDialog,
                enabled = canFormat,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = Red400,
                    disabledContentColor = Slate600
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(38.dp)
                    .testTag("format_flash_button")
            ) {
                Icon(
                    imageVector = Icons.Default.DeleteSweep,
                    contentDescription = "Format flash board",
                    modifier = Modifier.size(15.dp),
                    tint = if (canFormat) Red400 else Slate600
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Format Flash Board",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun CapacityRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = label, fontSize = 12.sp, color = Slate400)
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = Slate100
        )
    }
}

private fun formatByteSize(bytes: Long): String {
    val kb = bytes / 1024.0
    val mb = bytes / (1024.0 * 1024.0)
    val pretty = when {
        mb >= 1.0 -> String.format(Locale.US, "%.2f MB", mb)
        kb >= 1.0 -> String.format(Locale.US, "%.1f KB", kb)
        else -> "$bytes B"
    }
    return "$pretty ($bytes B)"
}

private fun formatRemainTime(freeBytes: Long): String {
    val samples = freeBytes / 26L
    val totalSec = (samples * 10L) / 1000L
    val hours = totalSec / 3600L
    val minutes = (totalSec % 3600L) / 60L
    val seconds = totalSec % 60L
    return when {
        hours > 0L -> "$hours jam $minutes menit"
        minutes > 0L -> "$minutes menit $seconds detik"
        else -> "$seconds detik"
    }
}

@Composable
private fun FormatProgressCard(
    progressText: String?,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Red950)
            .border(1.dp, Red400, RoundedCornerShape(16.dp))
            .padding(16.dp)
            .testTag("format_progress_card")
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            CircularProgressIndicator(
                modifier = Modifier.size(24.dp),
                strokeWidth = 2.5.dp,
                color = Red400
            )
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = "Menghapus Flash Board...",
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    color = Red400
                )
                Text(
                    text = progressText ?: "Chip erase 4 MB sedang berjalan via BLE (0x24)... (~10–40 s)",
                    fontSize = 11.sp,
                    color = Slate300
                )
            }
        }
    }
}

@Composable
private fun BatchSyncCard(
    pendingCount: Int,
    onSyncAllNew: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Emerald950)
            .border(1.dp, Emerald400.copy(alpha = 0.6f), RoundedCornerShape(14.dp))
            .padding(14.dp)
            .testTag("batch_sync_card")
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Row 1: x berkas belum di-sync
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(Emerald900),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.CloudDownload,
                        contentDescription = null,
                        tint = Emerald300,
                        modifier = Modifier.size(16.dp)
                    )
                }
                Text(
                    text = "$pendingCount berkas belum di-sync",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = Emerald300
                )
            }

            // Row 2: button Sync semua
            Button(
                onClick = onSyncAllNew,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Emerald400,
                    contentColor = Slate950
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(38.dp)
                    .testTag("batch_sync_button")
            ) {
                Icon(
                    imageVector = Icons.Default.Sync,
                    contentDescription = null,
                    modifier = Modifier.size(15.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Sync Semua",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun DownloadProgressCard(
    downloadState: FileDownloadState,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Slate850)
            .border(1.dp, if (downloadState.errorMessage != null) Red400 else Sky400, RoundedCornerShape(16.dp))
            .padding(14.dp)
            .testTag("download_progress_card")
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = if (downloadState.errorMessage != null) Icons.Default.Error else Icons.Default.Download,
                        contentDescription = null,
                        tint = if (downloadState.errorMessage != null) Red400 else Sky400,
                        modifier = Modifier.size(18.dp)
                    )
                    Text(
                        text = if (downloadState.errorMessage != null) "Unduhan Gagal" else "Mengunduh ${downloadState.fileName}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Slate100
                    )
                }
                Text(
                    text = "${downloadState.progressPercent}%",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    color = if (downloadState.errorMessage != null) Red400 else Sky400
                )
            }

            if (downloadState.errorMessage != null) {
                Text(
                    text = downloadState.errorMessage,
                    fontSize = 11.sp,
                    color = Red400
                )
            } else {
                LinearProgressIndicator(
                    progress = { downloadState.progress },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp)),
                    color = Sky400,
                    trackColor = Slate800,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "${downloadState.currentBytes} / ${downloadState.totalBytes} bytes",
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Slate400
                    )
                    Text(
                        text = "Chunk 180 B (NUS 0x21/0xB1)",
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Slate500
                    )
                }
            }
        }
    }
}

@Composable
private fun EmptyFileCard(
    isConnected: Boolean,
    canUseBoardBle: Boolean,
    hasKnownBoards: Boolean,
    isRefreshing: Boolean,
    isDownloading: Boolean,
    isFormatting: Boolean,
    onRefreshList: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(20.dp))
            .padding(28.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(
                imageVector = Icons.Default.FolderOpen,
                contentDescription = null,
                tint = Slate600,
                modifier = Modifier.size(42.dp)
            )
            Text(
                text = when {
                    isFormatting -> "Sedang memformat flash..."
                    isRefreshing -> "Membaca daftar berkas (0x20)..."
                    isDownloading -> "Sedang mengunduh berkas..."
                    else -> "(kosong)"
                },
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = Slate400
            )
            Text(
                text = when {
                    canUseBoardBle ->
                        "Tekan tombol 'Refresh' di atas untuk memuat berkas dari flash board."
                    isConnected ->
                        "Board lain terpilih — menampilkan arsip HP. Pilih chip board yang live untuk sync flash."
                    hasKnownBoards ->
                        "Belum ada unduhan untuk board ini. Hubungkan board lalu unduh .bin agar bisa dibuka offline."
                    else ->
                        "Hubungkan PalmLog sekali, unduh log, lalu daftar tetap bisa dibuka tanpa BLE."
                },
                style = MaterialTheme.typography.bodySmall,
                fontSize = 12.sp,
                color = Slate500
            )

            if (canUseBoardBle && !isRefreshing && !isDownloading && !isFormatting) {
                OutlinedButton(
                    onClick = onRefreshList,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Sky400)
                ) {
                    Text(text = "Baca Berkas", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
private fun FileItemCard(
    fileInfo: LogFileInfo,
    canUseBoardBle: Boolean,
    isDownloadingCurrent: Boolean,
    isDeletingCurrent: Boolean,
    onDownload: () -> Unit,
    onPlot: () -> Unit,
    onDeleteLocal: () -> Unit,
    onDeleteBoard: () -> Unit,
    onShare: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isClosed = fileInfo.isClosed
    val isOpen = fileInfo.isOpen

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Slate850)
            .border(
                width = 1.dp,
                color = if (fileInfo.isDownloaded) Emerald400.copy(alpha = 0.5f) else Slate700,
                shape = RoundedCornerShape(16.dp)
            )
            .padding(14.dp)
            .testTag("file_item_${fileInfo.name}")
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            // Header: Name & Status Badges
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.InsertDriveFile,
                        contentDescription = null,
                        tint = if (fileInfo.isDownloaded) Emerald300 else Slate400,
                        modifier = Modifier.size(18.dp)
                    )
                    Column {
                        Text(
                            text = fileInfo.fileName,
                            style = MaterialTheme.typography.titleSmall,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = Slate100
                        )
                        Text(
                            text = fileInfo.formattedDateTime,
                            style = MaterialTheme.typography.bodySmall,
                            fontSize = 11.sp,
                            color = Slate400
                        )
                    }
                }

                // Status Badge
                when {
                    fileInfo.isLocalOnly -> {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(Slate800)
                                .border(1.dp, Sky400.copy(alpha = 0.45f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Text(
                                text = "ARSIP HP",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = Sky400
                            )
                        }
                    }
                    isOpen -> {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(Amber950)
                                .border(1.dp, Amber400.copy(alpha = 0.5f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(6.dp)
                                        .clip(CircleShape)
                                        .background(Amber400)
                                )
                                Text(
                                    text = "sedang measure",
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Amber400
                                )
                            }
                        }
                    }
                    else -> {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(if (fileInfo.isDownloaded) Emerald950 else Slate800)
                                .border(
                                    1.dp,
                                    if (fileInfo.isDownloaded) Emerald400.copy(alpha = 0.5f) else Slate700,
                                    RoundedCornerShape(6.dp)
                                )
                                .padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Text(
                                text = if (fileInfo.isDownloaded) "TERUNDUH" else "BELUM SYNC",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (fileInfo.isDownloaded) Emerald300 else Sky400
                            )
                        }
                    }
                }
            }

            // Metrics Row: Records & Byte Size
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Slate800)
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${fileInfo.recordsCount} records",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = Slate300
                )
                Text(
                    text = "${fileInfo.formattedSize} (${fileInfo.byteSize} B)",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = Sky400
                )
            }

            // Action Buttons Row 1: Unduh / Plot
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Button 1: Unduh
                Button(
                    onClick = onDownload,
                    enabled = canUseBoardBle && isClosed && !fileInfo.isLocalOnly && !isDownloadingCurrent,
                    modifier = Modifier
                        .weight(1f)
                        .height(38.dp)
                        .testTag("download_button_${fileInfo.name}"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (fileInfo.isDownloaded) Slate800 else Sky400,
                        contentColor = if (fileInfo.isDownloaded) Sky400 else Slate950,
                        disabledContainerColor = Slate800,
                        disabledContentColor = Slate600
                    )
                ) {
                    if (isDownloadingCurrent) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(14.dp),
                            strokeWidth = 2.dp,
                            color = Slate950
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(text = "Mengunduh...", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    } else {
                        Icon(
                            imageVector = Icons.Default.Download,
                            contentDescription = null,
                            modifier = Modifier.size(15.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (fileInfo.isDownloaded) "Unduh Ulang" else "Unduh (.bin)",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                // Button 2: Plot (active once downloaded)
                OutlinedButton(
                    onClick = onPlot,
                    enabled = fileInfo.isDownloaded,
                    modifier = Modifier
                        .weight(1f)
                        .height(38.dp)
                        .testTag("plot_button_${fileInfo.name}"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = Emerald300,
                        disabledContentColor = Slate600
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.ShowChart,
                        contentDescription = null,
                        modifier = Modifier.size(15.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = "Plot", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            if (fileInfo.isDownloaded) {
                OutlinedButton(
                    onClick = onShare,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(36.dp)
                        .testTag("share_button_${fileInfo.name}"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Sky400)
                ) {
                    Icon(
                        imageVector = Icons.Default.Share,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(text = "Bagikan", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            // Phase D Action Buttons Row 2: "Hapus di HP" vs "Hapus di board"
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Button 3: Hapus di HP saja (no BLE)
                OutlinedButton(
                    onClick = onDeleteLocal,
                    enabled = fileInfo.isDownloaded,
                    modifier = Modifier
                        .weight(1f)
                        .height(36.dp)
                        .testTag("delete_local_button_${fileInfo.name}"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = Amber400,
                        disabledContentColor = Slate600
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.DeleteOutline,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Hapus di HP",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

                // Button 4: Hapus di board (BLE 0x23)
                OutlinedButton(
                    onClick = onDeleteBoard,
                    enabled = canUseBoardBle && isClosed && !fileInfo.isLocalOnly && !isDeletingCurrent,
                    modifier = Modifier
                        .weight(1f)
                        .height(36.dp)
                        .testTag("delete_board_button_${fileInfo.name}"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = Red400,
                        disabledContentColor = Slate600
                    )
                ) {
                    if (isDeletingCurrent) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(13.dp),
                            strokeWidth = 2.dp,
                            color = Red400
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(text = "Menghapus...", fontSize = 11.sp)
                    } else {
                        Icon(
                            imageVector = Icons.Default.DeleteForever,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "Hapus di board",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }
    }
}
