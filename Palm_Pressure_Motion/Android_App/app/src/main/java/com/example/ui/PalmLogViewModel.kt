package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.ble.BleConstants
import com.example.ble.PalmLogBleManager
import com.example.ble.StatusParser
import com.example.model.BleConnectionState
import com.example.model.BoardProfiles
import com.example.model.DiscoveredDevice
import com.example.model.FileDownloadState
import com.example.model.LogFileInfo
import com.example.model.PalmLogStatus
import com.example.model.PlgParsedData
import com.example.model.SetTimeAck
import com.example.model.SetTimeResult
import com.example.model.StreamSample
import com.example.storage.BoardHistoryStore
import com.example.storage.BoardStorage
import com.example.storage.KnownBoard
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream

enum class AppTab(val title: String) {
    STATUS("Status"),
    FILE("File"),
    STREAM("Stream"),
    PANDUAN("Panduan")
}

data class PalmLogUiState(
    val selectedTab: AppTab = AppTab.STATUS,
    val connectionState: BleConnectionState = BleConnectionState.Disconnected,
    val discoveredDevices: List<DiscoveredDevice> = emptyList(),
    val showDevicePickerDialog: Boolean = false,
    val boardStatus: PalmLogStatus? = null,
    val lastRawRx: ByteArray? = null,
    val isRawHexExpanded: Boolean = false,
    val isRefreshing: Boolean = false,
    val isSyncingTime: Boolean = false,
    val lastSetTimeAck: SetTimeAck? = null,
    val lastSyncedPhoneEpoch: Long? = null,
    val syncStatusText: String? = null,
    val knownBoards: List<KnownBoard> = emptyList(),
    val isStreaming: Boolean = false,
    val streamSamples: List<StreamSample> = emptyList(),
    val streamChannels: Set<Int> = setOf(1),
    /** MAC ternormalisasi (AA-BB-…) yang sedang dilihat di tab File. */
    val selectedBoardMac: String? = null,
    val fileList: List<LogFileInfo> = emptyList(),
    val isRefreshingFileList: Boolean = false,
    val downloadState: FileDownloadState? = null,
    val plotData: PlgParsedData? = null,
    val selectedFileForPlot: LogFileInfo? = null,
    val isDeletingBoardFile: Boolean = false,
    val deletingBoardFileName: String? = null,
    val isFormattingFlash: Boolean = false,
    val formatProgressText: String? = null,
    val snackbarMessage: String? = null
) {
    val isBleConnected: Boolean
        get() = connectionState is BleConnectionState.Connected

    val connectedMacNormalized: String?
        get() = (connectionState as? BleConnectionState.Connected)?.let {
            BoardStorage.normalizeMac(it.address)
        }

    val isViewingConnectedBoard: Boolean
        get() = isBleConnected && selectedBoardMac != null && selectedBoardMac == connectedMacNormalized

    val pendingDownloadCount: Int
        get() = fileList.count { !it.isDownloaded && it.isClosed && !it.isLocalOnly }
}

class PalmLogViewModel(application: Application) : AndroidViewModel(application) {

    private val bleManager = PalmLogBleManager(application.applicationContext, viewModelScope)

    private val _uiState = MutableStateFlow(PalmLogUiState())
    val uiState: StateFlow<PalmLogUiState> = _uiState.asStateFlow()

    private var syncTimeoutJob: Job? = null
    private var listTimeoutJob: Job? = null
    private var downloadJob: Job? = null
    private var autoConnectJob: Job? = null

    private val boardHistory = BoardHistoryStore(application.applicationContext)
    private val storageRoot: File by lazy {
        BoardStorage.rootDir(application.applicationContext).also { BoardStorage.migrateLegacyRootBins(it) }
    }

    private val currentListAccumulator = mutableListOf<LogFileInfo>()
    private val streamBuf = ArrayDeque<StreamSample>()

    private fun boardDir(macNormalized: String): File =
        BoardStorage.boardDir(storageRoot, macNormalized)

    private fun localFile(macNormalized: String, fileName: String): File =
        BoardStorage.fileInBoard(storageRoot, macNormalized, fileName)

    private fun refreshKnownBoardsList(): List<KnownBoard> {
        val boards = mutableListOf<KnownBoard>()
        for (mac in boardHistory.knownMacs()) {
            if (mac == BoardStorage.LEGACY_FOLDER) continue
            boards.add(
                KnownBoard(
                    macNormalized = mac,
                    lastSeenName = boardHistory.displayName(mac),
                    localFileCount = BoardStorage.countLocalBins(boardDir(mac))
                )
            )
        }
        return boards
    }

    /** Muat daftar .bin lokal untuk board terpilih (mode offline / dasar sebelum LIST). */
    private fun loadLocalFilesForMac(macNormalized: String): List<LogFileInfo> =
        BoardStorage.listLocalBinFiles(boardDir(macNormalized))

    private fun mergeBoardListWithLocal(boardItems: List<LogFileInfo>, macNormalized: String): List<LogFileInfo> {
        val locals = loadLocalFilesForMac(macNormalized)
        val byName = linkedMapOf<String, LogFileInfo>()
        for (b in boardItems) {
            val local = locals.find { it.name == b.name }
            byName[b.name] = if (local != null) {
                b.copy(
                    isDownloaded = true,
                    localFilePath = local.localFilePath,
                    isLocalOnly = false
                )
            } else {
                b.copy(isLocalOnly = false)
            }
        }
        for (l in locals) {
            if (!byName.containsKey(l.name)) {
                byName[l.name] = l
            }
        }
        return byName.values.sortedByDescending { it.name }
    }

    init {
        _uiState.update {
            val boards = refreshKnownBoardsList()
            it.copy(
                knownBoards = boards,
                selectedBoardMac = boards.firstOrNull()?.macNormalized,
                fileList = boards.firstOrNull()?.let { b -> loadLocalFilesForMac(b.macNormalized) } ?: emptyList()
            )
        }

        // Collect BLE connection state
        viewModelScope.launch {
            bleManager.connectionState.collect { state ->
                if (state is BleConnectionState.Connected) {
                    autoConnectJob?.cancel()
                    autoConnectJob = null
                    boardHistory.remember(state.address, state.deviceName)
                    val mac = BoardStorage.normalizeMac(state.address)
                    val boards = refreshKnownBoardsList()
                    val local = loadLocalFilesForMac(mac)
                    _uiState.update { current ->
                        current.copy(
                            connectionState = state,
                            showDevicePickerDialog = false,
                            knownBoards = boards,
                            selectedBoardMac = mac,
                            fileList = local,
                            boardStatus = current.boardStatus,
                            isSyncingTime = current.isSyncingTime,
                            isRefreshingFileList = current.isRefreshingFileList
                        )
                    }
                    // Auto LIST setelah connect
                    if (_uiState.value.selectedTab == AppTab.FILE) {
                        refreshFileList()
                    }
                } else if (state is BleConnectionState.Disconnected) {
                    _uiState.update { current ->
                        val mac = current.selectedBoardMac
                        current.copy(
                            connectionState = state,
                            boardStatus = null,
                            isSyncingTime = false,
                            isRefreshingFileList = false,
                            knownBoards = refreshKnownBoardsList(),
                            fileList = if (mac != null) loadLocalFilesForMac(mac) else emptyList()
                        )
                    }
                } else {
                    _uiState.update { current ->
                        current.copy(connectionState = state)
                    }
                }
            }
        }

        // Collect discovered devices & intelligent single auto-connect vs multi-device picker
        viewModelScope.launch {
            bleManager.discoveredDevices.collect { devices ->
                _uiState.update { it.copy(discoveredDevices = devices) }

                val conn = _uiState.value.connectionState
                if (conn !is BleConnectionState.Scanning) {
                    autoConnectJob?.cancel()
                    autoConnectJob = null
                    return@collect
                }

                // Filter board targets matching PalmLog
                val targetBoards = devices.filter {
                    it.isTarget || BleConstants.isTargetName(it.name)
                }

                if (targetBoards.size > 1) {
                    // Kasus B: Lebih dari 1 board PalmLog terdeteksi -> batalkan auto connect dan buka picker
                    autoConnectJob?.cancel()
                    autoConnectJob = null
                    _uiState.update { it.copy(showDevicePickerDialog = true) }
                } else if (targetBoards.size == 1 && autoConnectJob == null && !_uiState.value.showDevicePickerDialog) {
                    // Kasus A: Tepat 1 board terdeteksi -> beri jeda pemindaian 2.0 s untuk memastikan tidak ada board lain
                    val singleDevice = targetBoards.first()
                    autoConnectJob = viewModelScope.launch {
                        delay(2000)
                        val latestConn = _uiState.value.connectionState
                        val latestTargets = _uiState.value.discoveredDevices.filter {
                            it.isTarget || BleConstants.isTargetName(it.name)
                        }
                        if (latestConn is BleConnectionState.Scanning && latestTargets.size == 1) {
                            _uiState.update {
                                it.copy(
                                    showDevicePickerDialog = false,
                                    snackbarMessage = "1 board terdeteksi (${singleDevice.address}), menghubungkan otomatis..."
                                )
                            }
                            connectDevice(singleDevice.address)
                        } else if (latestTargets.size > 1) {
                            _uiState.update { it.copy(showDevicePickerDialog = true) }
                        }
                    }
                }
            }
        }

        // Collect parsed board status (Opcode 0x90, 14 atau 16 byte)
        viewModelScope.launch {
            bleManager.boardStatus.collect { status ->
                _uiState.update {
                    val stillMeasuring = status?.measure == true
                    it.copy(
                        boardStatus = status,
                        isRefreshing = false,
                        isStreaming = if (stillMeasuring) it.isStreaming else false,
                        streamSamples = if (stillMeasuring) it.streamSamples else emptyList()
                    )
                }
            }
        }

        viewModelScope.launch {
            bleManager.streamSamples.collect { sample ->
                if (!_uiState.value.isStreaming) return@collect
                synchronized(streamBuf) {
                    streamBuf.addLast(sample)
                    while (streamBuf.size > 200) streamBuf.removeFirst()
                }
            }
        }
        viewModelScope.launch {
            while (isActive) {
                delay(80)
                if (!_uiState.value.isStreaming) continue
                val snap = synchronized(streamBuf) { streamBuf.toList() }
                _uiState.update { it.copy(streamSamples = snap) }
            }
        }

        // Timing Precision: Collect SET_TIME ACK response (Opcode 0x91, 10 bytes)
        viewModelScope.launch {
            bleManager.lastSetTimeAck.collect { ack ->
                syncTimeoutJob?.cancel()
                val statusText = when (ack.result) {
                    SetTimeResult.OK -> "RTC disetel (${ack.formattedAdjustedTime})"
                    SetTimeResult.NO_RTC -> "RTC tidak ada / error"
                    SetTimeResult.BAD_RANGE -> "Sync gagal (rentang waktu tidak valid)"
                    SetTimeResult.UNKNOWN -> "Sync gagal"
                }

                val snackbar = when (ack.result) {
                    SetTimeResult.OK -> "RTC disetel: ${ack.formattedAdjustedTime}"
                    SetTimeResult.NO_RTC -> "RTC tidak ada / error"
                    SetTimeResult.BAD_RANGE, SetTimeResult.UNKNOWN -> "Sync gagal"
                }

                _uiState.update { current ->
                    current.copy(
                        isSyncingTime = false,
                        lastSetTimeAck = ack,
                        syncStatusText = statusText,
                        snackbarMessage = snackbar
                    )
                }

                if (ack.result == SetTimeResult.OK) {
                    delay(300)
                    refreshStatus()
                }
            }
        }

        // Phase C: Collect LIST_BEGIN (0xA0)
        viewModelScope.launch {
            bleManager.listBeginFlow.collect { total ->
                // Guard: Do not interrupt or clear files if a download is active
                if (_uiState.value.downloadState?.isDownloading == true) return@collect

                currentListAccumulator.clear()
                _uiState.update { it.copy(isRefreshingFileList = true) }

                // Always ensure timeout job is running to prevent stuck refresh state
                listTimeoutJob?.cancel()
                listTimeoutJob = viewModelScope.launch {
                    delay(5000)
                    bleManager.setAwaitingFileList(false)
                    if (_uiState.value.isRefreshingFileList) {
                        _uiState.update {
                            it.copy(
                                fileList = if (currentListAccumulator.isNotEmpty()) currentListAccumulator.toList() else it.fileList,
                                isRefreshingFileList = false,
                                snackbarMessage = if (currentListAccumulator.isEmpty()) "Waktu habis membaca berkas" else "Daftar selesai (${currentListAccumulator.size} berkas)"
                            )
                        }
                    }
                }
            }
        }

        // Phase C: Collect LIST_ITEM (0xA1)
        viewModelScope.launch {
            bleManager.listItemFlow.collect { rawItem ->
                if (_uiState.value.downloadState?.isDownloading == true) return@collect

                val mac = _uiState.value.connectedMacNormalized
                    ?: _uiState.value.selectedBoardMac
                    ?: return@collect
                val onDisk = localFile(mac, rawItem.fileName)
                val itemWithLocal = rawItem.copy(
                    isDownloaded = onDisk.exists() && onDisk.length() > 0L,
                    localFilePath = if (onDisk.exists()) onDisk.absolutePath else null,
                    isLocalOnly = false
                )

                val existingIndex = currentListAccumulator.indexOfFirst { it.name == itemWithLocal.name }
                if (existingIndex >= 0) {
                    currentListAccumulator[existingIndex] = itemWithLocal
                } else {
                    currentListAccumulator.add(itemWithLocal)
                }

                _uiState.update {
                    it.copy(fileList = currentListAccumulator.toList())
                }
            }
        }

        // Phase C: Collect LIST_END (0xA2)
        viewModelScope.launch {
            bleManager.listEndFlow.collect { sentCount ->
                if (_uiState.value.downloadState?.isDownloading == true) return@collect

                listTimeoutJob?.cancel()
                bleManager.setAwaitingFileList(false)
                val mac = _uiState.value.connectedMacNormalized
                    ?: _uiState.value.selectedBoardMac
                val merged = if (mac != null) {
                    mergeBoardListWithLocal(currentListAccumulator.toList(), mac)
                } else {
                    currentListAccumulator.toList()
                }
                currentListAccumulator.clear()
                currentListAccumulator.addAll(merged)
                _uiState.update {
                    it.copy(
                        fileList = merged,
                        isRefreshingFileList = false,
                        knownBoards = refreshKnownBoardsList(),
                        snackbarMessage = "Daftar berkas diperbarui: ${merged.size} berkas"
                    )
                }
            }
        }

        // Collect raw RX bytes
        viewModelScope.launch {
            bleManager.lastRawRx.collect { bytes ->
                _uiState.update { it.copy(lastRawRx = bytes) }
            }
        }

        // Collect user messages/toasts
        viewModelScope.launch {
            bleManager.userMessage.collect { msg ->
                _uiState.update { it.copy(snackbarMessage = msg) }
            }
        }
    }

    fun selectTab(tab: AppTab) {
        _uiState.update {
            it.copy(
                selectedTab = tab,
                knownBoards = refreshKnownBoardsList()
            )
        }
        if (tab == AppTab.STREAM && _uiState.value.isBleConnected) {
            refreshStatus()
        }
        if (tab != AppTab.FILE) return

        val mac = _uiState.value.selectedBoardMac
        if (mac != null && !_uiState.value.isViewingConnectedBoard) {
            // Offline / board lain: tampilkan arsip lokal
            _uiState.update { it.copy(fileList = loadLocalFilesForMac(mac)) }
        } else if (_uiState.value.isViewingConnectedBoard &&
            _uiState.value.fileList.isEmpty() &&
            !_uiState.value.isRefreshingFileList &&
            _uiState.value.downloadState?.isDownloading != true
        ) {
            refreshFileList()
        } else if (mac != null && _uiState.value.fileList.isEmpty()) {
            _uiState.update { it.copy(fileList = loadLocalFilesForMac(mac)) }
        }
    }

    fun toggleStreamChannel(channel: Int) {
        _uiState.update { state ->
            val next = if (channel in state.streamChannels) {
                if (state.streamChannels.size > 1) state.streamChannels - channel else state.streamChannels
            } else {
                state.streamChannels + channel
            }
            state.copy(streamChannels = next)
        }
    }

    fun setStreamChannels(channels: Set<Int>) {
        if (channels.isEmpty()) return
        _uiState.update { it.copy(streamChannels = channels) }
    }

    fun toggleStream() {
        val connected = _uiState.value.isBleConnected
        if (!connected) {
            _uiState.update { it.copy(snackbarMessage = "Hubungkan board terlebih dahulu.") }
            return
        }
        val start = !_uiState.value.isStreaming
        if (start && _uiState.value.boardStatus?.measure != true) {
            _uiState.update { it.copy(snackbarMessage = "Stream hanya saat measure aktif.") }
            return
        }
        viewModelScope.launch {
            val sent = bleManager.sendStreamCommand(start)
            if (!sent) {
                _uiState.update { it.copy(snackbarMessage = "Gagal mengirim perintah stream.") }
                return@launch
            }
            val ack = withTimeoutOrNull(2000) { bleManager.streamAck.first() }
            when {
                start && ack == 0 -> {
                    synchronized(streamBuf) { streamBuf.clear() }
                    _uiState.update { it.copy(isStreaming = true, streamSamples = emptyList()) }
                }
                start && ack == 1 -> {
                    _uiState.update { it.copy(isStreaming = false, snackbarMessage = "Measure mati. Stream ditolak.") }
                }
                start -> {
                    _uiState.update { it.copy(snackbarMessage = "Tidak ada jawaban stream dari board.") }
                }
                else -> {
                    synchronized(streamBuf) { streamBuf.clear() }
                    _uiState.update { it.copy(isStreaming = false, streamSamples = emptyList()) }
                }
            }
        }
    }

    /** Pilih board (MAC) di tab File — offline menampilkan unduhan lokal. */
    fun selectBoardMac(macNormalized: String) {
        val boards = refreshKnownBoardsList()
        val local = loadLocalFilesForMac(macNormalized)
        _uiState.update {
            it.copy(
                selectedBoardMac = macNormalized,
                knownBoards = boards,
                fileList = local
            )
        }
        if (_uiState.value.isBleConnected &&
            _uiState.value.connectedMacNormalized == macNormalized &&
            _uiState.value.downloadState?.isDownloading != true
        ) {
            refreshFileList()
        }
    }

    fun startScan(manualOpenPicker: Boolean = false) {
        autoConnectJob?.cancel()
        autoConnectJob = null
        if (manualOpenPicker) {
            _uiState.update { it.copy(showDevicePickerDialog = true) }
        }
        val success = bleManager.startScan()
        if (!success && !bleManager.isBluetoothEnabled()) {
            _uiState.update { it.copy(snackbarMessage = "Nyalakan Bluetooth untuk memindai PalmLog") }
        }
    }

    fun openDevicePicker() {
        startScan(manualOpenPicker = true)
    }

    fun dismissDevicePicker() {
        _uiState.update { it.copy(showDevicePickerDialog = false) }
    }

    fun stopScan() {
        autoConnectJob?.cancel()
        autoConnectJob = null
        bleManager.stopScan()
    }

    fun connectDevice(address: String) {
        autoConnectJob?.cancel()
        autoConnectJob = null
        _uiState.update { it.copy(showDevicePickerDialog = false) }
        bleManager.connectAddress(address)
    }

    fun disconnect() {
        autoConnectJob?.cancel()
        autoConnectJob = null
        bleManager.disconnect()
    }

    fun refreshStatus() {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }
        _uiState.update { it.copy(isRefreshing = true) }
        val sent = bleManager.sendGetStatus()
        if (!sent) {
            _uiState.update {
                it.copy(
                    isRefreshing = false,
                    snackbarMessage = "Gagal mengirim perintah GET_STATUS (0x10)"
                )
            }
        } else {
            viewModelScope.launch {
                delay(1500)
                if (_uiState.value.isRefreshing) {
                    _uiState.update { it.copy(isRefreshing = false) }
                }
            }
        }
    }

    /**
     * Timing Precision: Sync waktu (phone -> board via SET_TIME 0x11, 9 bytes).
     * Sends local wall-clock encoded as epoch milliseconds with UTC offset zero.
     */
    fun syncTime() {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }
        if (_uiState.value.isSyncingTime) return

        val ldt = java.time.LocalDateTime.now()
        val unixMsLocalWall = ldt.toInstant(java.time.ZoneOffset.UTC).toEpochMilli()

        _uiState.update {
            it.copy(
                isSyncingTime = true,
                lastSyncedPhoneEpoch = unixMsLocalWall,
                syncStatusText = "Mengirim waktu lokal (ms) ke board..."
            )
        }

        val sent = bleManager.sendSetTime(unixMsLocalWall)
        if (!sent) {
            _uiState.update {
                it.copy(
                    isSyncingTime = false,
                    syncStatusText = "Gagal mengirim SET_TIME (0x11)",
                    snackbarMessage = "Sync gagal"
                )
            }
            return
        }

        syncTimeoutJob?.cancel()
        syncTimeoutJob = viewModelScope.launch {
            delay(3000)
            if (_uiState.value.isSyncingTime) {
                _uiState.update {
                    it.copy(
                        isSyncingTime = false,
                        syncStatusText = "Sync gagal (waktu habis 3 detik)",
                        snackbarMessage = "Sync gagal"
                    )
                }
            }
        }
    }

    /**
     * Phase C: Refresh daftar file via opcode 0x20 LIST.
     */
    fun refreshFileList() {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }

        if (!_uiState.value.isViewingConnectedBoard) {
            _uiState.update {
                it.copy(snackbarMessage = "Pilih board yang sedang terhubung untuk refresh daftar flash.")
            }
            return
        }

        if (_uiState.value.downloadState?.isDownloading == true) {
            _uiState.update { it.copy(snackbarMessage = "Sedang proses mengunduh berkas. Harap tunggu hingga selesai.") }
            return
        }

        currentListAccumulator.clear()
        _uiState.update { it.copy(isRefreshingFileList = true) }

        val sent = bleManager.sendListCommand()
        if (!sent) {
            _uiState.update {
                it.copy(
                    isRefreshingFileList = false,
                    snackbarMessage = "Gagal mengirim perintah LIST (0x20)"
                )
            }
            return
        }

        listTimeoutJob?.cancel()
        listTimeoutJob = viewModelScope.launch {
            delay(5000)
            bleManager.setAwaitingFileList(false)
            if (_uiState.value.isRefreshingFileList) {
                val mac = _uiState.value.connectedMacNormalized
                    ?: _uiState.value.selectedBoardMac
                val list = if (currentListAccumulator.isNotEmpty() && mac != null) {
                    mergeBoardListWithLocal(currentListAccumulator.toList(), mac)
                } else if (currentListAccumulator.isNotEmpty()) {
                    currentListAccumulator.toList()
                } else {
                    _uiState.value.fileList
                }
                _uiState.update {
                    it.copy(
                        fileList = list,
                        isRefreshingFileList = false,
                        knownBoards = refreshKnownBoardsList(),
                        snackbarMessage = if (currentListAccumulator.isEmpty()) {
                            "Tidak ada respon daftar dari board"
                        } else {
                            "Daftar selesai (${list.size} berkas)"
                        }
                    )
                }
            }
        }
    }

    /**
     * Executes safe chunk-by-chunk download for a single file.
     * Prevents any IndexOutOfBoundsException with safe bounds and try-catch.
     */
    private suspend fun executeDownloadSingleFile(fileInfo: LogFileInfo): Boolean {
        var offset = 0L
        val targetSize = fileInfo.byteSize
        val buffer = ByteArrayOutputStream()
        var failureMessage: String? = null
        val maxChunk = 180

        try {
            while (offset < targetSize || targetSize == 0L) {
                val sent = bleManager.sendGetFileChunk(fileInfo.name, offset, maxChunk)
                if (!sent) {
                    failureMessage = "Gagal mengirim permintaan chunk offset $offset"
                    break
                }

                val chunk = withTimeoutOrNull(3000) {
                    bleManager.chunkFlow.first { it.offset == offset }
                }

                if (chunk == null) {
                    failureMessage = "Waktu habis (timeout 3 detik) menunggu chunk offset $offset"
                    break
                }

                if (!chunk.isSuccess) {
                    failureMessage = chunk.errorMessage ?: "Unduhan gagal (kode ${chunk.result})"
                    break
                }

                val toWrite = chunk.data
                if (toWrite.isEmpty()) {
                    break
                }

                buffer.write(toWrite, 0, toWrite.size)
                offset += toWrite.size

                _uiState.update {
                    it.copy(
                        downloadState = it.downloadState?.copy(
                            currentBytes = offset,
                            totalBytes = if (chunk.fileSize > 0) chunk.fileSize else targetSize
                        )
                    )
                }

                if (chunk.fileSize > 0 && offset >= chunk.fileSize) {
                    break
                }
            }
        } catch (e: Exception) {
            failureMessage = "Error saat mengunduh: ${e.message}"
        }

        if (failureMessage != null) {
            _uiState.update {
                it.copy(
                    isRefreshingFileList = false,
                    downloadState = it.downloadState?.copy(
                        isDownloading = false,
                        errorMessage = failureMessage
                    ),
                    snackbarMessage = failureMessage
                )
            }
            return false
        } else {
            val mac = _uiState.value.connectedMacNormalized
                ?: _uiState.value.selectedBoardMac
            if (mac == null) {
                _uiState.update {
                    it.copy(
                        isRefreshingFileList = false,
                        downloadState = it.downloadState?.copy(
                            isDownloading = false,
                            errorMessage = "MAC board tidak diketahui; tidak bisa menyimpan berkas"
                        ),
                        snackbarMessage = "MAC board tidak diketahui; tidak bisa menyimpan berkas"
                    )
                }
                return false
            }
            val targetFile = localFile(mac, fileInfo.fileName)
            try {
                FileOutputStream(targetFile).use { fos ->
                    fos.write(buffer.toByteArray())
                }

                val updatedList = _uiState.value.fileList.map { item ->
                    if (item.name == fileInfo.name) {
                        item.copy(
                            isDownloaded = true,
                            localFilePath = targetFile.absolutePath,
                            isLocalOnly = false
                        )
                    } else item
                }

                val accIndex = currentListAccumulator.indexOfFirst { it.name == fileInfo.name }
                if (accIndex >= 0) {
                    currentListAccumulator[accIndex] = currentListAccumulator[accIndex].copy(
                        isDownloaded = true,
                        localFilePath = targetFile.absolutePath,
                        isLocalOnly = false
                    )
                }

                _uiState.update {
                    it.copy(
                        fileList = updatedList,
                        isRefreshingFileList = false,
                        knownBoards = refreshKnownBoardsList(),
                        downloadState = it.downloadState?.copy(
                            isDownloading = false,
                            currentBytes = targetFile.length(),
                            totalBytes = targetFile.length(),
                            completedFilePath = targetFile.absolutePath
                        ),
                        snackbarMessage = "Berhasil mengunduh ${fileInfo.fileName} (${targetFile.length()} B)"
                    )
                }
                return true
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isRefreshingFileList = false,
                        downloadState = it.downloadState?.copy(
                            isDownloading = false,
                            errorMessage = "Gagal menyimpan berkas: ${e.message}"
                        ),
                        snackbarMessage = "Gagal menyimpan berkas: ${e.message}"
                    )
                }
                return false
            }
        }
    }

    /**
     * Phase C: Unduh berkas tunggal secara manual.
     */
    fun downloadFile(fileInfo: LogFileInfo) {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }

        if (fileInfo.isOpen) {
            _uiState.update { it.copy(snackbarMessage = "Berkas sedang merekam (busy OPEN). Tidak dapat diunduh.") }
            return
        }

        if (_uiState.value.downloadState?.isDownloading == true) {
            _uiState.update { it.copy(snackbarMessage = "Sedang proses mengunduh...") }
            return
        }

        if (_uiState.value.isRefreshingFileList) {
            _uiState.update { it.copy(snackbarMessage = "Sedang memuat daftar berkas. Harap tunggu sebentar.") }
            return
        }

        downloadJob?.cancel()
        downloadJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    downloadState = FileDownloadState(
                        fileName = fileInfo.fileName,
                        currentBytes = 0L,
                        totalBytes = fileInfo.byteSize,
                        isDownloading = true
                    )
                )
            }
            executeDownloadSingleFile(fileInfo)
        }
    }

    /**
     * Batch Sync: Unduh semua berkas CLOSED yang belum ada di smartphone.
     */
    fun syncAllNewFiles() {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }

        val pendingFiles = _uiState.value.fileList.filter {
            !it.isDownloaded && it.isClosed && !it.isLocalOnly
        }
        if (pendingFiles.isEmpty()) {
            _uiState.update { it.copy(snackbarMessage = "Semua berkas CLOSED sudah ada di HP.") }
            return
        }

        if (_uiState.value.downloadState?.isDownloading == true) {
            _uiState.update { it.copy(snackbarMessage = "Sedang proses mengunduh berkas lain...") }
            return
        }

        if (_uiState.value.isRefreshingFileList) {
            _uiState.update { it.copy(snackbarMessage = "Sedang memuat daftar berkas. Harap tunggu sebentar.") }
            return
        }

        downloadJob?.cancel()
        downloadJob = viewModelScope.launch {
            var successCount = 0
            for ((index, fileInfo) in pendingFiles.withIndex()) {
                val fileNum = index + 1
                val totalNum = pendingFiles.size
                _uiState.update {
                    it.copy(
                        downloadState = FileDownloadState(
                            fileName = "${fileInfo.fileName} ($fileNum/$totalNum)",
                            currentBytes = 0L,
                            totalBytes = fileInfo.byteSize,
                            isDownloading = true
                        )
                    )
                }

                val ok = executeDownloadSingleFile(fileInfo)
                if (ok) {
                    successCount++
                } else {
                    break
                }
            }

            _uiState.update {
                it.copy(
                    isRefreshingFileList = false,
                    downloadState = it.downloadState?.copy(isDownloading = false),
                    snackbarMessage = "Sinkronisasi selesai: $successCount dari ${pendingFiles.size} berkas berhasil diunduh"
                )
            }
        }
    }

    /**
     * Phase C: Parse PLG1 header + records and open plot view.
     */
    fun plotFile(fileInfo: LogFileInfo) {
        val mac = _uiState.value.selectedBoardMac
        val targetFile = fileInfo.localFilePath?.let { File(it) }
            ?: mac?.let { localFile(it, fileInfo.fileName) }
        if (targetFile == null || !targetFile.exists() || targetFile.length() < 256) {
            _uiState.update { it.copy(snackbarMessage = "Berkas belum diunduh atau ukuran tidak valid.") }
            return
        }

        try {
            val bytes = targetFile.readBytes()
            val parsed = StatusParser.parsePlgFile(fileInfo.fileName, bytes)
            if (parsed == null || parsed.records.isEmpty()) {
                _uiState.update {
                    it.copy(
                        snackbarMessage = "Butuh PLG1 v4 (26 B, 11 kanal). Berkas lama atau kosong tidak didukung."
                    )
                }
                return
            }

            _uiState.update {
                it.copy(
                    plotData = parsed,
                    selectedFileForPlot = fileInfo
                )
            }
        } catch (e: Exception) {
            _uiState.update { it.copy(snackbarMessage = "Gagal membaca berkas: ${e.message}") }
        }
    }

    fun dismissPlot() {
        _uiState.update { it.copy(plotData = null, selectedFileForPlot = null) }
    }

    /**
     * Phase D: (1) Hapus di HP saja (no BLE).
     * Menghapus salinan lokal di folder board (per MAC).
     */
    fun deleteLocalFile(fileInfo: LogFileInfo) {
        val mac = _uiState.value.selectedBoardMac
        val targetFile = fileInfo.localFilePath?.let { File(it) }
            ?: mac?.let { localFile(it, fileInfo.fileName) }
        val fileExisted = targetFile?.exists() == true
        val deleted = if (fileExisted) targetFile!!.delete() else true

        val removeFromList = fileInfo.isLocalOnly || !_uiState.value.isViewingConnectedBoard
        val updatedList = if (removeFromList) {
            _uiState.value.fileList.filter { it.name != fileInfo.name }
        } else {
            _uiState.value.fileList.map { item ->
                if (item.name == fileInfo.name) {
                    item.copy(isDownloaded = false, localFilePath = null, isLocalOnly = false)
                } else item
            }
        }
        val accIndex = currentListAccumulator.indexOfFirst { it.name == fileInfo.name }
        if (accIndex >= 0) {
            if (removeFromList) {
                currentListAccumulator.removeAt(accIndex)
            } else {
                currentListAccumulator[accIndex] = currentListAccumulator[accIndex].copy(
                    isDownloaded = false,
                    localFilePath = null,
                    isLocalOnly = false
                )
            }
        }

        _uiState.update {
            it.copy(
                fileList = updatedList,
                knownBoards = refreshKnownBoardsList(),
                snackbarMessage = if (fileExisted && deleted) {
                    "Salinan ${fileInfo.fileName} di HP berhasil dihapus"
                } else {
                    "Salinan di HP tidak ditemukan"
                }
            )
        }
    }

    /**
     * Phase D: (2) Hapus di board (BLE 0x23).
     * Sends 0x23 + name[12] and awaits ACK 0xA3.
     */
    fun deleteBoardFile(fileInfo: LogFileInfo) {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }

        if (fileInfo.isOpen) {
            _uiState.update { it.copy(snackbarMessage = "Sedang measure / OPEN") }
            return
        }

        if (_uiState.value.isDeletingBoardFile || _uiState.value.isFormattingFlash) {
            _uiState.update { it.copy(snackbarMessage = "Operasi file sedang berjalan. Harap tunggu.") }
            return
        }

        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    isDeletingBoardFile = true,
                    deletingBoardFileName = fileInfo.fileName
                )
            }

            val sent = bleManager.sendDeleteFile(fileInfo.name)
            if (!sent) {
                _uiState.update {
                    it.copy(
                        isDeletingBoardFile = false,
                        deletingBoardFileName = null,
                        snackbarMessage = "Gagal mengirim perintah hapus ke board"
                    )
                }
                return@launch
            }

            val result = withTimeoutOrNull(5000) {
                bleManager.deleteAckFlow.first()
            }

            _uiState.update {
                it.copy(
                    isDeletingBoardFile = false,
                    deletingBoardFileName = null
                )
            }

            when (result) {
                0 -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "File ${fileInfo.fileName} berhasil dihapus dari flash board")
                    }
                    delay(300)
                    refreshFileList()
                    delay(500)
                    refreshStatus()
                }
                1 -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "File tidak ada di board")
                    }
                }
                2 -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Sedang measure / OPEN")
                    }
                }
                null -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Waktu habis (timeout 5s) menunggu respon hapus dari board")
                    }
                }
                else -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Hapus ditolak dengan kode: $result")
                    }
                }
            }
        }
    }

    /**
     * FORMAT (0x24 + 0xA5). Ukuran chip dan timeout mengikuti profil nama board.
     */
    fun formatFlashBoard() {
        val state = _uiState.value.connectionState
        if (state !is BleConnectionState.Connected) {
            _uiState.update { it.copy(snackbarMessage = "Perangkat belum terhubung. Hubungkan PalmLog terlebih dahulu.") }
            return
        }
        val profile = BoardProfiles.fromAdvertisedName(state.deviceName)
        val sizeLabel = profile?.sizeLabel ?: "flash"
        val durationHint = profile?.formatDurationHint ?: "waktu bervariasi"
        val timeoutMs = profile?.formatTimeoutMs ?: BoardProfiles.UNKNOWN_FORMAT_TIMEOUT_MS

        if (_uiState.value.boardStatus?.measure == true) {
            _uiState.update { it.copy(snackbarMessage = "Stop measure dulu") }
            return
        }

        if (_uiState.value.isFormattingFlash || _uiState.value.isDeletingBoardFile) {
            _uiState.update { it.copy(snackbarMessage = "Operasi sedang berjalan...") }
            return
        }

        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    isFormattingFlash = true,
                    formatProgressText = "Menghapus seluruh $sizeLabel (chip erase $durationHint)..."
                )
            }

            val sent = bleManager.sendFormatFlash()
            if (!sent) {
                _uiState.update {
                    it.copy(
                        isFormattingFlash = false,
                        formatProgressText = null,
                        snackbarMessage = "Gagal mengirim perintah format ke board"
                    )
                }
                return@launch
            }

            val result = withTimeoutOrNull(timeoutMs) {
                bleManager.formatAckFlow.first()
            }

            _uiState.update {
                it.copy(
                    isFormattingFlash = false,
                    formatProgressText = null
                )
            }

            when (result) {
                0 -> {
                    currentListAccumulator.clear()
                    val mac = _uiState.value.connectedMacNormalized
                        ?: _uiState.value.selectedBoardMac
                    _uiState.update {
                        it.copy(
                            // Flash kosong; arsip HP tetap tampil sebagai local-only
                            fileList = if (mac != null) loadLocalFilesForMac(mac) else emptyList(),
                            knownBoards = refreshKnownBoardsList(),
                            snackbarMessage = "Format berhasil: $sizeLabel telah dikosongkan"
                        )
                    }
                    delay(300)
                    refreshFileList()
                    delay(500)
                    refreshStatus()
                }
                1 -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Stop measure dulu")
                    }
                }
                2 -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Format ditolak (confirm)")
                    }
                }
                null -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Waktu habis (timeout ${timeoutMs / 1000} detik) menunggu proses format flash")
                    }
                }
                else -> {
                    _uiState.update {
                        it.copy(snackbarMessage = "Format gagal dengan kode: $result")
                    }
                }
            }
        }
    }

    fun toggleRawHexExpanded() {
        _uiState.update { it.copy(isRawHexExpanded = !it.isRawHexExpanded) }
    }

    fun dismissSnackbar() {
        _uiState.update { it.copy(snackbarMessage = null) }
    }

    fun isBluetoothEnabled(): Boolean = bleManager.isBluetoothEnabled()

    override fun onCleared() {
        super.onCleared()
        syncTimeoutJob?.cancel()
        listTimeoutJob?.cancel()
        downloadJob?.cancel()
        bleManager.disconnect()
    }
}
