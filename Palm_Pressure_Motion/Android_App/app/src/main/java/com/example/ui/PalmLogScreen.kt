package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.model.BleConnectionState
import com.example.ui.components.DevicePickerDialog
import com.example.ui.components.FileTabContent
import com.example.ui.components.PanduanTabContent
import com.example.ui.components.StatusTabContent
import com.example.ui.components.StreamTabContent
import com.example.ui.theme.*

@Composable
fun PalmLogScreen(
    viewModel: PalmLogViewModel,
    onRequestPermissions: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scrollState = rememberScrollState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.snackbarMessage) {
        val msg = uiState.snackbarMessage
        if (msg != null) {
            snackbarHostState.showSnackbar(msg)
            viewModel.dismissSnackbar()
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = Slate900,
        snackbarHost = {
            SnackbarHost(
                hostState = snackbarHostState,
                modifier = Modifier.padding(16.dp)
            ) { data ->
                Snackbar(
                    containerColor = Slate800,
                    contentColor = Slate100,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(text = data.visuals.message, fontSize = 13.sp)
                }
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(scrollState)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .widthIn(max = 640.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 1. Top Header
                HeaderBar(connectionState = uiState.connectionState)

                // 2. Navigation Tabs (Status | File | Panduan)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(Slate850)
                        .border(1.dp, Slate700, RoundedCornerShape(14.dp))
                        .padding(4.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    TabPill(
                        label = "Status",
                        icon = Icons.Default.Assessment,
                        isSelected = uiState.selectedTab == AppTab.STATUS,
                        onClick = { viewModel.selectTab(AppTab.STATUS) },
                        modifier = Modifier.weight(1f)
                    )
                    TabPill(
                        label = "File",
                        icon = Icons.Default.Folder,
                        isSelected = uiState.selectedTab == AppTab.FILE,
                        onClick = { viewModel.selectTab(AppTab.FILE) },
                        modifier = Modifier.weight(1f)
                    )
                    TabPill(
                        label = "Stream",
                        icon = Icons.Default.ShowChart,
                        isSelected = uiState.selectedTab == AppTab.STREAM,
                        onClick = { viewModel.selectTab(AppTab.STREAM) },
                        modifier = Modifier.weight(1f)
                    )
                    TabPill(
                        label = "Panduan",
                        icon = Icons.Default.MenuBook,
                        isSelected = uiState.selectedTab == AppTab.PANDUAN,
                        onClick = { viewModel.selectTab(AppTab.PANDUAN) },
                        modifier = Modifier.weight(1f)
                    )
                }

                // 3. Tab Contents
                when (uiState.selectedTab) {
                    AppTab.STATUS -> {
                        StatusTabContent(
                            connectionState = uiState.connectionState,
                            discoveredDevices = uiState.discoveredDevices,
                            boardStatus = uiState.boardStatus,
                            lastRawRx = uiState.lastRawRx,
                            isRawHexExpanded = uiState.isRawHexExpanded,
                            isRefreshing = uiState.isRefreshing,
                            isSyncingTime = uiState.isSyncingTime,
                            lastSetTimeAck = uiState.lastSetTimeAck,
                            lastSyncedPhoneEpoch = uiState.lastSyncedPhoneEpoch,
                            syncStatusText = uiState.syncStatusText,
                            onStartScan = {
                                onRequestPermissions()
                                viewModel.startScan()
                            },
                            onStopScan = { viewModel.stopScan() },
                            onOpenDevicePicker = {
                                onRequestPermissions()
                                viewModel.openDevicePicker()
                            },
                            onConnectDevice = { address -> viewModel.connectDevice(address) },
                            onDisconnect = { viewModel.disconnect() },
                            onRefreshStatus = { viewModel.refreshStatus() },
                            onSyncTime = { viewModel.syncTime() },
                            onToggleRawHex = { viewModel.toggleRawHexExpanded() }
                        )
                    }
                    AppTab.FILE -> {
                        FileTabContent(
                            connectionState = uiState.connectionState,
                            fileList = uiState.fileList,
                            knownBoards = uiState.knownBoards,
                            selectedBoardMac = uiState.selectedBoardMac,
                            connectedMacNormalized = uiState.connectedMacNormalized,
                            isViewingConnectedBoard = uiState.isViewingConnectedBoard,
                            pendingDownloadCount = uiState.pendingDownloadCount,
                            isRefreshingList = uiState.isRefreshingFileList,
                            downloadState = uiState.downloadState,
                            plotData = uiState.plotData,
                            isMeasureActive = uiState.boardStatus?.measure == true,
                            boardStatus = uiState.boardStatus,
                            isDeletingBoard = uiState.isDeletingBoardFile,
                            deletingBoardFileName = uiState.deletingBoardFileName,
                            isFormattingFlash = uiState.isFormattingFlash,
                            formatProgressText = uiState.formatProgressText,
                            onSelectBoardMac = { mac -> viewModel.selectBoardMac(mac) },
                            onRefreshList = { viewModel.refreshFileList() },
                            onDownloadFile = { fileInfo -> viewModel.downloadFile(fileInfo) },
                            onSyncAllNew = { viewModel.syncAllNewFiles() },
                            onPlotFile = { fileInfo -> viewModel.plotFile(fileInfo) },
                            onDeleteLocalFile = { fileInfo -> viewModel.deleteLocalFile(fileInfo) },
                            onDeleteBoardFile = { fileInfo -> viewModel.deleteBoardFile(fileInfo) },
                            onFormatFlashBoard = { viewModel.formatFlashBoard() },
                            onDismissPlot = { viewModel.dismissPlot() }
                        )
                    }
                    AppTab.STREAM -> {
                        StreamTabContent(
                            isConnected = uiState.isBleConnected,
                            measureActive = uiState.boardStatus?.measure == true,
                            isStreaming = uiState.isStreaming,
                            samples = uiState.streamSamples,
                            selectedChannels = uiState.streamChannels,
                            onToggleStream = { viewModel.toggleStream() },
                            onToggleChannel = { ch -> viewModel.toggleStreamChannel(ch) },
                            onSelectChannels = { chs -> viewModel.setStreamChannels(chs) }
                        )
                    }
                    AppTab.PANDUAN -> {
                        PanduanTabContent()
                    }
                }

                Spacer(modifier = Modifier.height(28.dp))
            }
        }
    }

    // Modal: Device Picker Dialog (Pemilih Perangkat PalmLog)
    if (uiState.showDevicePickerDialog) {
        DevicePickerDialog(
            discoveredDevices = uiState.discoveredDevices,
            isScanning = uiState.connectionState is BleConnectionState.Scanning,
            onSelectDevice = { address -> viewModel.connectDevice(address) },
            onRescan = {
                onRequestPermissions()
                viewModel.startScan()
            },
            onDismiss = { viewModel.dismissDevicePicker() }
        )
    }
}

@Composable
private fun HeaderBar(
    connectionState: BleConnectionState,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                text = "PalmLog",
                style = MaterialTheme.typography.titleLarge,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = (-0.5).sp,
                color = Slate100
            )
            Text(
                text = "Palm Logger Companion • 1.1.0",
                style = MaterialTheme.typography.bodySmall,
                fontSize = 12.sp,
                color = Slate400
            )
        }

        // Connection status pill
        val isConnected = connectionState is BleConnectionState.Connected
        val isConnecting = connectionState is BleConnectionState.Connecting || connectionState is BleConnectionState.Scanning

        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(100.dp))
                .background(
                    when {
                        isConnected -> Emerald950
                        isConnecting -> Slate800
                        else -> Slate850
                    }
                )
                .border(
                    width = 1.dp,
                    color = when {
                        isConnected -> Emerald400
                        isConnecting -> Sky400
                        else -> Slate700
                    },
                    shape = RoundedCornerShape(100.dp)
                )
                .padding(horizontal = 10.dp, vertical = 5.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(
                            when {
                                isConnected -> Emerald400
                                isConnecting -> Sky400
                                else -> Slate500
                            }
                        )
                )
                Text(
                    text = when {
                        isConnected -> "Online"
                        isConnecting -> "Proses..."
                        else -> "Offline"
                    },
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = when {
                        isConnected -> Emerald400
                        isConnecting -> Sky400
                        else -> Slate400
                    }
                )
            }
        }
    }
}

@Composable
private fun TabPill(
    label: String,
    icon: ImageVector,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (isSelected) Emerald400 else Color.Transparent)
            .clickable { onClick() }
            .padding(vertical = 10.dp)
            .testTag("tab_${label.lowercase()}"),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isSelected) Slate950 else Slate400,
                modifier = Modifier.size(16.dp)
            )
            Text(
                text = label,
                fontSize = 13.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) Slate950 else Slate300
            )
        }
    }
}
