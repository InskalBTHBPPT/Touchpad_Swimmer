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
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.AccessTimeFilled
import androidx.compose.material.icons.filled.BatteryStd
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.BluetoothConnected
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DataUsage
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.EnergySavingsLeaf
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Smartphone
import androidx.compose.material.icons.filled.StopCircle
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Usb
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ble.BleConstants
import com.example.model.BleConnectionState
import com.example.model.DiscoveredDevice
import com.example.model.PalmLogStatus
import com.example.model.SetTimeAck
import com.example.model.SetTimeResult
import com.example.ui.theme.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

@Composable
fun StatusTabContent(
    connectionState: BleConnectionState,
    discoveredDevices: List<DiscoveredDevice>,
    boardStatus: PalmLogStatus?,
    lastRawRx: ByteArray?,
    isRawHexExpanded: Boolean,
    isRefreshing: Boolean,
    isSyncingTime: Boolean,
    lastSetTimeAck: SetTimeAck?,
    lastSyncedPhoneEpoch: Long?,
    syncStatusText: String?,
    onStartScan: () -> Unit,
    onStopScan: () -> Unit,
    onOpenDevicePicker: () -> Unit,
    onConnectDevice: (String) -> Unit,
    onDisconnect: () -> Unit,
    onRefreshStatus: () -> Unit,
    onSyncTime: () -> Unit,
    onToggleRawHex: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. Connection & Scanner Card
        ConnectionCard(
            connectionState = connectionState,
            discoveredDevices = discoveredDevices,
            onStartScan = onStartScan,
            onStopScan = onStopScan,
            onOpenDevicePicker = onOpenDevicePicker,
            onConnectDevice = onConnectDevice,
            onDisconnect = onDisconnect
        )

        // 2. Phase B: Time Sync Card (Phone -> Board RTC via 0x11)
        TimeSyncCard(
            isBleConnected = connectionState is BleConnectionState.Connected,
            isSyncing = isSyncingTime,
            lastAck = lastSetTimeAck,
            lastSyncedPhoneEpoch = lastSyncedPhoneEpoch,
            syncStatusText = syncStatusText,
            boardStatus = boardStatus,
            onSyncTime = onSyncTime
        )

        // 3. Refresh Status Action Bar
        RefreshStatusBar(
            isBleConnected = connectionState is BleConnectionState.Connected,
            isRefreshing = isRefreshing,
            lastReceivedMillis = boardStatus?.receivedAtMillis,
            onRefreshStatus = onRefreshStatus
        )

        // 4. Board Status Data Grid
        BoardStatusCard(
            isBleConnected = connectionState is BleConnectionState.Connected,
            boardStatus = boardStatus
        )

        // 5. Raw Last RX Hex (Debug - Collapsible)
        RawRxDebugCard(
            lastRawRx = lastRawRx,
            isExpanded = isRawHexExpanded,
            onToggle = onToggleRawHex
        )
    }
}

@Composable
private fun ConnectionCard(
    connectionState: BleConnectionState,
    discoveredDevices: List<DiscoveredDevice>,
    onStartScan: () -> Unit,
    onStopScan: () -> Unit,
    onOpenDevicePicker: () -> Unit,
    onConnectDevice: (String) -> Unit,
    onDisconnect: () -> Unit,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "scan_pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(700, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha"
    )

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(20.dp))
            .padding(18.dp)
            .testTag("connection_card")
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Header Row: Status Indicator
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    val statusDotColor = when (connectionState) {
                        is BleConnectionState.Connected -> Emerald400
                        is BleConnectionState.Connecting -> Sky400
                        is BleConnectionState.Scanning -> Amber400
                        is BleConnectionState.Error -> Red400
                        BleConnectionState.Disconnected -> Slate500
                    }

                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(
                                if (connectionState is BleConnectionState.Scanning || connectionState is BleConnectionState.Connecting)
                                    statusDotColor.copy(alpha = pulseAlpha)
                                else statusDotColor
                            )
                    )

                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        val stateTitle = when (connectionState) {
                            is BleConnectionState.Connected -> "Terhubung ke ${connectionState.deviceName}"
                            is BleConnectionState.Connecting -> "Menghubungkan..."
                            is BleConnectionState.Scanning -> "Memindai PalmLog..."
                            is BleConnectionState.Error -> "Koneksi Bermasalah"
                            BleConnectionState.Disconnected -> "Perangkat Terputus"
                        }
                        Text(
                            text = stateTitle,
                            style = MaterialTheme.typography.titleMedium,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Slate100
                        )

                        when (val state = connectionState) {
                            is BleConnectionState.Connected -> {
                                Text(
                                    text = state.address,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate400
                                )
                                Text(
                                    text = "NUS MTU: ${state.mtu} • Notifikasi Aktif",
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate400
                                )
                            }
                            is BleConnectionState.Connecting -> {
                                Text(
                                    text = state.address,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate400
                                )
                            }
                            is BleConnectionState.Scanning -> {
                                Text(
                                    text = "Mencari board berawalan ${BleConstants.TARGET_DEVICE_NAME}",
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    color = Slate400
                                )
                            }
                            is BleConnectionState.Error -> {
                                Text(
                                    text = state.message,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    color = Red400
                                )
                            }
                            BleConnectionState.Disconnected -> {
                                Text(
                                    text = "Siap memindai BLE",
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    color = Slate400
                                )
                            }
                        }
                    }
                }

                if (connectionState is BleConnectionState.Scanning || connectionState is BleConnectionState.Connecting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = Sky400
                    )
                }
            }

            // Action Buttons
            when (connectionState) {
                is BleConnectionState.Disconnected, is BleConnectionState.Error -> {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = onStartScan,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(46.dp)
                                .testTag("scan_button"),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Emerald400,
                                contentColor = Slate950
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.BluetoothSearching,
                                contentDescription = null,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Pindai & Sambung ${BleConstants.TARGET_DEVICE_NAME}",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        }

                        OutlinedButton(
                            onClick = onOpenDevicePicker,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(38.dp)
                                .testTag("open_device_picker_button"),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Sky300)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Devices,
                                contentDescription = null,
                                modifier = Modifier.size(15.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Pilih Board dari Daftar MAC Address",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
                is BleConnectionState.Scanning -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = onStopScan,
                            modifier = Modifier
                                .weight(1f)
                                .height(44.dp)
                                .testTag("stop_scan_button"),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Slate200)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(text = "Hentikan Scan", fontSize = 12.sp)
                        }

                        Button(
                            onClick = onOpenDevicePicker,
                            modifier = Modifier
                                .weight(1f)
                                .height(44.dp)
                                .testTag("show_picker_during_scan_button"),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Sky400,
                                contentColor = Slate950
                            )
                        ) {
                            Icon(
                                imageVector = Icons.Default.Devices,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(text = "Pilih Board", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
                is BleConnectionState.Connecting, is BleConnectionState.Connected -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = onDisconnect,
                            modifier = Modifier
                                .weight(1.2f)
                                .height(44.dp)
                                .testTag("disconnect_button"),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Red400)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp),
                                tint = Red400
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Putuskan",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = Red400
                            )
                        }

                        OutlinedButton(
                            onClick = onOpenDevicePicker,
                            modifier = Modifier
                                .weight(1f)
                                .height(44.dp)
                                .testTag("switch_device_button"),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Sky300)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Devices,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(text = "Ganti Board", fontSize = 12.sp)
                        }
                    }
                }
            }

            // Discovered Devices list during Scan
            AnimatedVisibility(
                visible = connectionState is BleConnectionState.Scanning && discoveredDevices.isNotEmpty()
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "PERANGKAT DITEMUKAN",
                        style = MaterialTheme.typography.labelSmall,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Slate400,
                        letterSpacing = 1.sp
                    )
                    discoveredDevices.take(6).forEach { device ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (device.isTarget) Slate800 else Slate900)
                                .border(
                                    width = 1.dp,
                                    color = if (device.isTarget) Emerald400.copy(alpha = 0.6f) else Slate700,
                                    shape = RoundedCornerShape(12.dp)
                                )
                                .clickable { onConnectDevice(device.address) }
                                .padding(horizontal = 14.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(
                                modifier = Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(2.dp)
                            ) {
                                Text(
                                    text = device.name,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = if (device.isTarget) FontWeight.Bold else FontWeight.Normal,
                                    color = if (device.isTarget) Emerald300 else Slate100
                                )
                                Text(
                                    text = device.address,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate400
                                )
                                Text(
                                    text = "RSSI: ${device.rssi} dBm",
                                    style = MaterialTheme.typography.bodySmall,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate500
                                )
                            }
                            Button(
                                onClick = { onConnectDevice(device.address) },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (device.isTarget) Emerald400 else Slate700,
                                    contentColor = if (device.isTarget) Slate950 else Slate200
                                ),
                                modifier = Modifier
                                    .height(36.dp)
                                    .wrapContentWidth()
                            ) {
                                Text(
                                    text = "Hubungkan",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 1,
                                    softWrap = false
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

/**
 * Phase B: Dedicated Time Sync Card
 */
@Composable
private fun TimeSyncCard(
    isBleConnected: Boolean,
    isSyncing: Boolean,
    lastAck: SetTimeAck?,
    lastSyncedPhoneEpoch: Long?,
    syncStatusText: String?,
    boardStatus: PalmLogStatus?,
    onSyncTime: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(20.dp))
            .padding(18.dp)
            .testTag("time_sync_card")
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Header: judul + deskripsi rapat; badge tidak menekan lebar teks
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.Top
            ) {
                Box(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .background(Sky400.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.AccessTimeFilled,
                        contentDescription = null,
                        tint = Sky400,
                        modifier = Modifier.size(18.dp)
                    )
                }
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "SINKRONISASI WAKTU",
                            style = MaterialTheme.typography.labelSmall,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp,
                            color = Sky400
                        )
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(Slate800)
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "9 Byte LE",
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate400
                            )
                        }
                    }
                    Text(
                        text = "Kirim waktu UTC unix HP ke modul RTC board",
                        style = MaterialTheme.typography.bodySmall,
                        fontSize = 11.sp,
                        color = Slate400
                    )
                    Text(
                        text = "SET_TIME 0x11",
                        style = MaterialTheme.typography.bodySmall,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Slate500
                    )
                }
            }

            // Side-by-side Time Display (Phone Time vs Board Time)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Phone Time
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Slate800)
                        .padding(10.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Smartphone,
                                contentDescription = null,
                                tint = Sky400,
                                modifier = Modifier.size(13.dp)
                            )
                            Text(
                                text = "Waktu HP (Sekarang)",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Medium,
                                color = Slate400
                            )
                        }
                        val ldt = java.time.LocalDateTime.now()
                        val nowWallMs = ldt.toInstant(java.time.ZoneOffset.UTC).toEpochMilli()
                        val phoneTimeText = String.format(Locale.US, "%02d:%02d:%02d.%03d", ldt.hour, ldt.minute, ldt.second, ldt.nano / 1_000_000)
                        Text(
                            text = phoneTimeText,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = Slate100
                        )
                        Text(
                            text = "Wall: $nowWallMs ms",
                            fontSize = 9.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Slate500
                        )
                    }
                }

                // Board RTC Time
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Slate800)
                        .padding(10.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.AccessTime,
                                contentDescription = null,
                                tint = if (boardStatus?.rtcOk == true) Emerald400 else Amber400,
                                modifier = Modifier.size(13.dp)
                            )
                            Text(
                                text = "Waktu RTC Board",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Medium,
                                color = Slate400
                            )
                        }

                        val boardTimeText = if (boardStatus != null && boardStatus.rtcOk && boardStatus.unixTime > 0L) {
                            val sdfUtc = SimpleDateFormat("HH:mm:ss", Locale.US).apply {
                                timeZone = TimeZone.getTimeZone("UTC")
                            }
                            sdfUtc.format(Date(boardStatus.unixTime * 1000L))
                        } else {
                            "Belum Diatur"
                        }

                        Text(
                            text = boardTimeText,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = if (boardStatus?.rtcOk == true) Emerald300 else Amber400
                        )
                        Text(
                            text = if (boardStatus != null && boardStatus.unixTime > 0L) "Unix: ${boardStatus.unixTime} s" else "rtc_ok = 0",
                            fontSize = 9.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Slate500
                        )
                    }
                }
            }

            // Sync Button: "Sync waktu"
            Button(
                onClick = onSyncTime,
                enabled = isBleConnected && !isSyncing,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(46.dp)
                    .testTag("sync_time_button"),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Sky400,
                    contentColor = Slate950,
                    disabledContainerColor = Slate800,
                    disabledContentColor = Slate600
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isSyncing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                        color = Slate950
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Menyinkronkan...",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.Sync,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Sync waktu",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                }
            }

            // Result / Status Banner
            if (lastAck != null || syncStatusText != null) {
                val result = lastAck?.result
                val isSuccess = result == SetTimeResult.OK
                val isNoRtc = result == SetTimeResult.NO_RTC
                val isError = !isSuccess && (lastAck != null || syncStatusText?.contains("gagal", ignoreCase = true) == true)

                val bannerBg = when {
                    isSuccess -> Emerald950
                    isNoRtc -> Amber950
                    else -> Red950
                }
                val bannerBorder = when {
                    isSuccess -> Emerald400
                    isNoRtc -> Amber400
                    else -> Red400
                }
                val bannerContentColor = when {
                    isSuccess -> Emerald300
                    isNoRtc -> Amber400
                    else -> Red400
                }

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(bannerBg)
                        .border(1.dp, bannerBorder.copy(alpha = 0.6f), RoundedCornerShape(10.dp))
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = when {
                                isSuccess -> Icons.Default.CheckCircle
                                isNoRtc -> Icons.Default.Warning
                                else -> Icons.Default.Error
                            },
                            contentDescription = null,
                            tint = bannerContentColor,
                            modifier = Modifier.size(16.dp)
                        )
                        Column {
                            val mainText = when {
                                isSuccess -> "RTC disetel"
                                isNoRtc -> "RTC tidak ada / error"
                                else -> "Sync gagal"
                            }
                            Text(
                                text = mainText,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = bannerContentColor
                            )
                            if (isSuccess && lastAck != null) {
                                Text(
                                    text = "Waktu disetel: ${lastAck.formattedAdjustedTime}",
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate200
                                )
                            } else if (syncStatusText != null && syncStatusText != mainText) {
                                Text(
                                    text = syncStatusText,
                                    fontSize = 10.sp,
                                    color = Slate400
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RefreshStatusBar(
    isBleConnected: Boolean,
    isRefreshing: Boolean,
    lastReceivedMillis: Long?,
    onRefreshStatus: () -> Unit,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "refresh_spin")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "spin_rotation"
    )

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = "DATA BOARD",
                style = MaterialTheme.typography.labelSmall,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.2.sp,
                color = Slate400
            )
            Text(
                text = if (lastReceivedMillis != null) {
                    val agoSec = ((System.currentTimeMillis() - lastReceivedMillis) / 1000).coerceAtLeast(0)
                    "Diperbarui $agoSec detik lalu (GET_STATUS 0x10)"
                } else if (isBleConnected) {
                    "Tekan segarkan untuk meminta status"
                } else {
                    "Menunggu koneksi board"
                },
                style = MaterialTheme.typography.bodySmall,
                fontSize = 11.sp,
                color = Slate500
            )
        }

        Button(
            onClick = onRefreshStatus,
            enabled = isBleConnected && !isRefreshing,
            shape = RoundedCornerShape(12.dp),
            contentPadding = PaddingValues(0.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Slate800,
                contentColor = Emerald300,
                disabledContainerColor = Slate850,
                disabledContentColor = Slate600
            ),
            modifier = Modifier
                .size(40.dp)
                .testTag("refresh_status_button")
        ) {
            Icon(
                imageVector = Icons.Default.Refresh,
                contentDescription = "Segarkan Status",
                modifier = Modifier
                    .size(18.dp)
                    .rotate(if (isRefreshing) rotation else 0f)
            )
        }
    }
}

@Composable
private fun BoardStatusCard(
    isBleConnected: Boolean,
    boardStatus: PalmLogStatus?,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(20.dp))
            .padding(18.dp)
            .testTag("board_status_card")
    ) {
        if (!isBleConnected) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Bluetooth,
                    contentDescription = null,
                    tint = Slate600,
                    modifier = Modifier.size(36.dp)
                )
                Text(
                    text = "Board Belum Terhubung",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    color = Slate400
                )
                Text(
                    text = "Pindai dan hubungkan ke PalmLog untuk melihat status papan",
                    style = MaterialTheme.typography.bodySmall,
                    fontSize = 11.sp,
                    color = Slate500
                )
            }
        } else if (boardStatus == null) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(28.dp),
                    strokeWidth = 2.dp,
                    color = Emerald400
                )
                Text(
                    text = "Mengambil data status (GET_STATUS 0x10)...",
                    style = MaterialTheme.typography.bodySmall,
                    color = Slate300
                )
            }
        } else {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Row 1: BLE Connected & Measure State
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    StatusFieldItem(
                        icon = Icons.Default.BluetoothConnected,
                        label = "BLE Terhubung",
                        value = "Ya (Aktif)",
                        highlightColor = Emerald400,
                        backgroundColor = Emerald950,
                        modifier = Modifier.weight(1f),
                        testTag = "field_ble_connected"
                    )

                    StatusFieldItem(
                        icon = if (boardStatus.measure) Icons.Default.PlayCircle else Icons.Default.StopCircle,
                        label = "Status Measure",
                        value = if (boardStatus.measure) "AKTIF (True)" else "BERHENTI (False)",
                        highlightColor = if (boardStatus.measure) Emerald400 else Amber400,
                        backgroundColor = if (boardStatus.measure) Emerald950 else Amber950,
                        modifier = Modifier.weight(1f),
                        testTag = "field_measure"
                    )
                }

                // USB / baterai + hemat daya
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    StatusFieldItem(
                        icon = if (boardStatus.usbConnected) Icons.Default.Usb else Icons.Default.BatteryStd,
                        label = "Sumber daya",
                        value = if (boardStatus.usbConnected) {
                            "USB (Selalu ON)"
                        } else {
                            val mv = boardStatus.batteryMv
                            if (mv != null) {
                                String.format(java.util.Locale.US, "Baterai · %.2f V", mv / 1000.0)
                            } else {
                                "Baterai"
                            }
                        },
                        highlightColor = if (boardStatus.usbConnected) Emerald400 else Sky400,
                        backgroundColor = Slate800,
                        modifier = Modifier.weight(1f),
                        testTag = "field_usb"
                    )

                    StatusFieldItem(
                        icon = Icons.Default.EnergySavingsLeaf,
                        label = "Hemat Daya (pwr_save)",
                        value = if (boardStatus.powerSave) "Aktif (1)" else "Nonaktif (0)",
                        highlightColor = if (boardStatus.powerSave) Emerald400 else Slate400,
                        backgroundColor = Slate800,
                        modifier = Modifier.weight(1f),
                        testTag = "field_pwr_save"
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusFieldItem(
    icon: ImageVector,
    label: String,
    value: String,
    highlightColor: Color,
    backgroundColor: Color,
    modifier: Modifier = Modifier,
    badgeText: String? = null,
    badgeColor: Color = Slate400,
    isMonospace: Boolean = false,
    testTag: String = ""
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(backgroundColor)
            .border(1.dp, Slate700.copy(alpha = 0.7f), RoundedCornerShape(14.dp))
            .padding(12.dp)
            .testTag(testTag)
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = highlightColor,
                        modifier = Modifier.size(15.dp)
                    )
                    Text(
                        text = label,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Slate400
                    )
                }
                if (badgeText != null) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(badgeColor.copy(alpha = 0.15f))
                            .border(1.dp, badgeColor.copy(alpha = 0.3f), RoundedCornerShape(6.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = badgeText,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = badgeColor
                        )
                    }
                }
            }
            Text(
                text = value,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                fontFamily = if (isMonospace) FontFamily.Monospace else FontFamily.Default,
                color = highlightColor
            )
        }
    }
}

@Composable
private fun RawRxDebugCard(
    lastRawRx: ByteArray?,
    isExpanded: Boolean,
    onToggle: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(16.dp))
            .padding(14.dp)
            .testTag("raw_rx_debug_card")
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onToggle() },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.DataUsage,
                        contentDescription = null,
                        tint = Sky400,
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "Data Mentah RX Terakhir (Debug)",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Slate200
                    )
                    if (lastRawRx != null) {
                        Text(
                            text = "(${lastRawRx.size} byte)",
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Slate400
                        )
                    }
                }
                Icon(
                    imageVector = if (isExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = if (isExpanded) "Tutup" else "Buka",
                    tint = Slate400,
                    modifier = Modifier.size(20.dp)
                )
            }

            AnimatedVisibility(visible = isExpanded) {
                Column(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (lastRawRx == null) {
                        Text(
                            text = "Belum ada paket notifikasi RX yang diterima.",
                            style = MaterialTheme.typography.bodySmall,
                            fontSize = 11.sp,
                            color = Slate500
                        )
                    } else {
                        // Raw hex display
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(Slate950)
                                .border(1.dp, Slate800, RoundedCornerShape(8.dp))
                                .padding(10.dp)
                        ) {
                            Text(
                                text = lastRawRx.joinToString(" ") { "%02X".format(it) },
                                style = MaterialTheme.typography.bodySmall,
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Medium,
                                color = Emerald300
                            )
                        }

                        // Byte breakdown guide based on opcode
                        if (lastRawRx.isNotEmpty() && lastRawRx[0] == BleConstants.OPCODE_ACK_SET_TIME) {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(
                                    text = "Paket ACK_SET_TIME (Opcode 0x91, 10 Byte):",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Sky400
                                )
                                ByteGuideRow("B0 [0x91]", "Opcode ACK SET_TIME")
                                ByteGuideRow("B1 [result]", "0=OK, 1=no RTC, 2=bad range")
                                ByteGuideRow("B2..B9 [unix_ms]", "u64 LE waktu RTC ms setelah disetel")
                            }
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(
                                    text = "Paket ACK_STATUS (Opcode 0x90, 16 Byte):",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Slate400
                                )
                                ByteGuideRow("B0 [0x90]", "Opcode ACK GET_STATUS")
                                ByteGuideRow("B1 [measure]", "1 = Aktif, 0 = Berhenti")
                                ByteGuideRow("B2 [rtc_ok]", "1 = Jam RTC valid, 0 = Gagal/Kosong")
                                ByteGuideRow("B3..B6 [unix_time]", "u32 Little-Endian detik Unix")
                                ByteGuideRow("B7..B10 [next_free]", "u32 Little-Endian flash address")
                                ByteGuideRow("B11 [file_count]", "Jumlah berkas tersimpan (0..48)")
                                ByteGuideRow("B12 [usb]", "1 = Daya USB, 0 = Daya Baterai")
                                ByteGuideRow("B13 [pwr_save]", "1 = Mode Hemat Daya Aktif, 0 = Off")
                                ByteGuideRow("B14..B15 [vbat_mV]", "u16 LE milivolt (dummy 3500..4250)")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ByteGuideRow(field: String, desc: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = field,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.SemiBold,
            color = Sky400
        )
        Text(
            text = desc,
            fontSize = 10.sp,
            color = Slate400
        )
    }
}
