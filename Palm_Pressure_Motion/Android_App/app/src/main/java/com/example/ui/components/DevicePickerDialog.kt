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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SignalCellularAlt
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.example.ble.BleConstants
import com.example.model.DiscoveredDevice
import com.example.ui.theme.*

/**
 * Dialog Pemilih Perangkat (Device Picker / Selector):
 * Ditampilkan ketika terdeteksi beberapa board PalmLog dengan MAC address berbeda di sekitar,
 * atau ketika pengguna secara manual memilih untuk mencari dan memilih board tertentu.
 */
@Composable
fun DevicePickerDialog(
    discoveredDevices: List<DiscoveredDevice>,
    isScanning: Boolean,
    onSelectDevice: (String) -> Unit,
    onRescan: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val targetDevices = discoveredDevices.filter {
        it.isTarget || BleConstants.isTargetName(it.name)
    }
    val otherDevices = discoveredDevices.filter {
        !it.isTarget && !BleConstants.isTargetName(it.name)
    }

    var showOtherDevices by remember { mutableStateOf(false) }

    val infiniteTransition = rememberInfiniteTransition(label = "scan_spin")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "spin"
    )

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = modifier
                .fillMaxWidth(0.94f)
                .heightIn(max = 640.dp)
                .clip(RoundedCornerShape(20.dp)),
            color = Slate900,
            tonalElevation = 6.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // 1. Header Bar: Icon, Title, and Close Button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Emerald950)
                                .border(1.dp, Emerald400.copy(alpha = 0.5f), RoundedCornerShape(12.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Devices,
                                contentDescription = null,
                                tint = Emerald400,
                                modifier = Modifier.size(22.dp)
                            )
                        }

                        Column {
                            Text(
                                text = "Pilih Board PalmLog",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = Slate100
                            )
                            Text(
                                text = if (targetDevices.size > 1) {
                                    "${targetDevices.size} board aktif ditemukan"
                                } else if (targetDevices.size == 1) {
                                    "1 board aktif ditemukan"
                                } else {
                                    "Memindai board di sekitar..."
                                },
                                style = MaterialTheme.typography.bodySmall,
                                fontSize = 11.sp,
                                color = if (targetDevices.isNotEmpty()) Emerald300 else Slate400
                            )
                        }
                    }

                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .size(34.dp)
                            .testTag("close_device_picker_button"),
                        shape = CircleShape,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Slate300),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Tutup",
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                // 2. Info Banner jika terdeteksi banyak board
                if (targetDevices.size > 1) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(Sky950)
                            .border(1.dp, Sky400.copy(alpha = 0.4f), RoundedCornerShape(10.dp))
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text(
                            text = "Terdeteksi ${targetDevices.size} board ${BleConstants.TARGET_DEVICE_NAME} dengan MAC Address berbeda. Silakan pilih board yang ingin Anda hubungkan.",
                            fontSize = 11.sp,
                            color = Sky200,
                            lineHeight = 16.sp
                        )
                    }
                }

                // 3. Device List
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f, fill = false),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    if (targetDevices.isEmpty() && isScanning) {
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 24.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(28.dp),
                                        strokeWidth = 2.5.dp,
                                        color = Emerald400
                                    )
                                    Text(
                                        text = "Mencari board PalmLog...",
                                        fontSize = 12.sp,
                                        color = Slate400
                                    )
                                }
                            }
                        }
                    } else if (targetDevices.isEmpty() && !isScanning) {
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 24.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text(
                                        text = "Tidak ada board PalmLog yang ditemukan.",
                                        fontSize = 12.sp,
                                        color = Slate400
                                    )
                                    Text(
                                        text = "Pastikan board menyala dan dalam jangkauan BLE.",
                                        fontSize = 11.sp,
                                        color = Slate500
                                    )
                                }
                            }
                        }
                    } else {
                        items(targetDevices, key = { it.address }) { device ->
                            DeviceItemCard(
                                device = device,
                                isTarget = true,
                                onConnect = { onSelectDevice(device.address) }
                            )
                        }
                    }

                    // Optional section: Perangkat BLE lainnya
                    if (otherDevices.isNotEmpty()) {
                        item {
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { showOtherDevices = !showOtherDevices }
                                    .padding(vertical = 4.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Perangkat BLE Lainnya (${otherDevices.size})",
                                    fontSize = 11.sp,
                                    color = Slate500
                                )
                                Text(
                                    text = if (showOtherDevices) "Sembunyikan ▲" else "Tampilkan ▼",
                                    fontSize = 11.sp,
                                    color = Sky400
                                )
                            }
                        }

                        if (showOtherDevices) {
                            items(otherDevices, key = { it.address }) { device ->
                                DeviceItemCard(
                                    device = device,
                                    isTarget = false,
                                    onConnect = { onSelectDevice(device.address) }
                                )
                            }
                        }
                    }
                }

                // 4. Bottom Controls: Status Pemindaian & Tombol Pindai Ulang
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Status scanning indicator
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        if (isScanning) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(Emerald400)
                            )
                            Text(
                                text = "Memindai aktif...",
                                fontSize = 11.sp,
                                color = Emerald400
                            )
                        } else {
                            Text(
                                text = "Pemindaian selesai",
                                fontSize = 11.sp,
                                color = Slate500
                            )
                        }
                    }

                    // Pindai Ulang button
                    Button(
                        onClick = onRescan,
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Slate800,
                            contentColor = Sky400
                        ),
                        modifier = Modifier
                            .height(36.dp)
                            .testTag("rescan_picker_button")
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = null,
                            modifier = Modifier
                                .size(14.dp)
                                .rotate(if (isScanning) rotation else 0f)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isScanning) "Memindai..." else "Pindai Ulang",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DeviceItemCard(
    device: DiscoveredDevice,
    isTarget: Boolean,
    onConnect: () -> Unit,
    modifier: Modifier = Modifier
) {
    val rssiColor = when {
        device.rssi >= -65 -> Emerald400
        device.rssi >= -80 -> Amber400
        else -> Red400
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(if (isTarget) Slate850 else Slate900)
            .border(
                width = if (isTarget) 1.5.dp else 1.dp,
                color = if (isTarget) Emerald400.copy(alpha = 0.5f) else Slate800,
                shape = RoundedCornerShape(14.dp)
            )
            .clickable(onClick = onConnect)
            .padding(12.dp)
            .testTag("device_card_${device.address}")
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Left info: Name, MAC Address, RSSI
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = device.name,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (isTarget) Emerald300 else Slate200
                    )
                    if (isTarget) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(Emerald950)
                                .border(1.dp, Emerald400.copy(alpha = 0.6f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "BOARD",
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                color = Emerald400
                            )
                        }
                    }
                }

                // MAC Address (Monospace)
                Text(
                    text = device.address,
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.SemiBold,
                    color = Slate100
                )

                // RSSI & Signal Level
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.SignalCellularAlt,
                        contentDescription = null,
                        modifier = Modifier.size(12.dp),
                        tint = rssiColor
                    )
                    Text(
                        text = "${device.rssi} dBm • ${device.signalStrengthLevel}",
                        fontSize = 10.sp,
                        color = Slate400
                    )
                }
            }

            // Right: Hubungkan Button
            Button(
                onClick = onConnect,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isTarget) Emerald400 else Slate700,
                    contentColor = if (isTarget) Slate950 else Slate200
                ),
                modifier = Modifier
                    .height(34.dp)
                    .testTag("connect_btn_${device.address}")
            ) {
                Text(
                    text = "Hubungkan",
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
            }
        }
    }
}
