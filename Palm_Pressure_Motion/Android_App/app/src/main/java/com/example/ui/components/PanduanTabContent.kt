package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Upcoming
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.*

@Composable
fun PanduanTabContent(
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .testTag("panduan_tab_content"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. Ringkasan App Phase D
        PanduanCard(
            icon = Icons.Default.Info,
            iconTint = Emerald400,
            title = "APLIKASI PALMLOG",
            subtitle = "Koneksi BLE, Status, Sync Waktu, Unduh Log & Manajemen File (Hapus & Format)"
        ) {
            Text(
                text = "App Phase D: connect + telemetri status + sync waktu RTC (u64 unix_ms) + daftar berkas flash & unduh raw .bin + manajemen berkas (hapus lokal HP, hapus board, & format chip flash).",
                style = MaterialTheme.typography.bodyMedium,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = Emerald300,
                lineHeight = 19.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Aplikasi berkomunikasi dengan board PalmLog via Nordic UART Service (NUS) dengan ATT MTU 247. Berkas raw .bin disimpan ke penyimpanan perangkat dan dapat di-plot langsung.",
                style = MaterialTheme.typography.bodySmall,
                fontSize = 12.sp,
                color = Slate400,
                lineHeight = 17.sp
            )
        }

        // 2. Tiga Aksi Manajemen Berkas (Phase D)
        PanduanCard(
            icon = Icons.Default.DeleteSweep,
            iconTint = Amber400,
            title = "TIGA AKSI MANAJEMEN BERKAS (PHASE D)",
            subtitle = "Perbedaan antara Hapus di HP, Hapus di Board, dan Format Flash"
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                InstructionItem(
                    badge = "Hapus HP",
                    badgeColor = Amber400,
                    title = "1) Hapus di HP Saja (Tanpa BLE)",
                    desc = "Menghapus berkas .bin lokal di penyimpanan HP saja. Berkas di memori flash board tidak berubah sama sekali. Status berkas akan kembali menjadi 'BELUM SYNC'."
                )

                InstructionItem(
                    badge = "0x23 Board",
                    badgeColor = Red400,
                    title = "2) Hapus di Flash Board (BLE 0x23)",
                    desc = "Mengirim perintah 0x23 ke board untuk menghapus entri berkas di tabel direktori flash board. Berkas berstatus 'sedang measure (OPEN)' tidak dapat dihapus. Perhatikan: Spasi fisik flash baru benar-benar dibebaskan saat FORMAT chip flash dilakukan. Salinan di HP tidak ikut terhapus."
                )

                InstructionItem(
                    badge = "0x24 Chip",
                    badgeColor = Red500,
                    title = "3) Format Flash Board (BLE 0x24 + 0xA5)",
                    desc = "Menjalankan chip erase SPI flash di board. PalmLog20 = 4 MB (timeout 65 s). PalmLog1 = 16 MB (timeout 120 s). Menghapus seluruh berkas di board sekaligus. Sensor tidak boleh sedang merekam (measure harus FALSE/berhenti)."
                )
            }
        }

        // 3. Panduan Operasional Board (Tombol & Sync)
        PanduanCard(
            icon = Icons.Default.PowerSettingsNew,
            iconTint = Sky400,
            title = "PANDUAN OPERASIONAL BOARD",
            subtitle = "Tombol fisik, sinkronisasi waktu & pengunduhan log"
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                InstructionItem(
                    badge = "≥ 10 dtk",
                    badgeColor = Amber400,
                    title = "Board ON / OFF",
                    desc = "Tahan tombol P0.17 ≥ 10 detik (baterai; USB = selalu ON)."
                )

                InstructionItem(
                    badge = "Multi-Board",
                    badgeColor = Emerald400,
                    title = "Koneksi Cerdas & Pemilih Board (Device Picker)",
                    desc = "Jika hanya 1 board aktif di sekitar, aplikasi langsung auto-connect (2 detik). Jika terdeteksi beberapa board PalmLog (MAC berbeda), muncul dialog Pemilih Board menampilkan daftar MAC Address dan RSSI (dBm). Koneksi BLE bekerja point-to-point (1 board aktif) dan dapat berganti board kapan saja."
                )

                InstructionItem(
                    badge = "3–10 dtk",
                    badgeColor = Emerald400,
                    title = "Start / Stop Measure",
                    desc = "Lepas tombol setelah tahan 3–10 detik untuk memulai atau menghentikan pengukuran."
                )

                InstructionItem(
                    badge = "Sync ms",
                    badgeColor = Sky400,
                    title = "Sync Waktu Presisi (unix ms)",
                    desc = "Tombol di app mengirim waktu lokal HP hingga milidetik (u64 LE unix ms, 9 B) ke board. Board menyetel RTC detik + anchor millis(). Berkas log baru menyimpan start_unix_ms (PLG1 v2, offset 22) agar sample tidak diasumsikan mulai di .000."
                )

                InstructionItem(
                    badge = "Unduh .bin",
                    badgeColor = Emerald300,
                    title = "Daftar & Unduh Berkas",
                    desc = "Tab File: Refresh daftar (0x20) membaca berkas flash. Tap Unduh pada berkas OK/CLOSED untuk menarik chunk (0x21/0xB1). Berkas OPEN tidak dapat diunduh (sedang merekam)."
                )

                InstructionItem(
                    badge = "Plot Multi-Ch",
                    badgeColor = Sky400,
                    title = "Plot Multi-Channel Overlay",
                    desc = "Tap Plot pada berkas terunduh PLG1 v4 (26 B, 11 kanal). Pilih grup Umum / Accel / Gyro / Mag; Y = nilai fisik (g, °/s, µT), X = t_rel_ms. Statistik Min/Max/Avg per kanal terpilih."
                )
            }
        }

        // 4. Indikator LED Merah P0.15
        PanduanCard(
            icon = Icons.Default.Lightbulb,
            iconTint = Red400,
            title = "INDIKATOR LED MERAH P0.15",
            subtitle = "Pola kedipan visual status sistem"
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                LedPatternItem(
                    label = "Mode Siap (Idle)",
                    pattern = "Triple blink / 10 s",
                    desc = "Kedip 3 kali setiap 10 detik. Board siap menerima koneksi BLE atau perintah.",
                    color = Amber400
                )
                LedPatternItem(
                    label = "Mode Pengukuran (Measure)",
                    pattern = "Double blink / 5 s",
                    desc = "Kedip 2 kali setiap 5 detik. Sensor aktif merekam data logger.",
                    color = Emerald400
                )
            }
        }

        // 5. Spesifikasi Protokol BLE NUS (Phase A, B, C, & D)
        PanduanCard(
            icon = Icons.Default.Code,
            iconTint = Sky400,
            title = "PROTOKOL BLE NUS (PHASE A, B, C, & D)",
            subtitle = "Daftar Opcode Lengkap"
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                ProtocolCommandRow(
                    title = "GET_STATUS (Phone → Board)",
                    detail = "Opcode 0x10 (1 byte total pada NUS RX)",
                    badge = "0x10",
                    badgeColor = Emerald400
                )
                ProtocolCommandRow(
                    title = "ACK GET_STATUS (Board → Phone)",
                    detail = "Opcode 0x90 (16 byte: status + vbat_mV u16 LE; usb tetap flag 0/1)",
                    badge = "0x90",
                    badgeColor = Emerald300
                )
                ProtocolCommandRow(
                    title = "SET_TIME (Phone → Board)",
                    detail = "Opcode 0x11 (Total 9 byte: 0x11 + uint64 LE unix ms local wall-clock)",
                    badge = "0x11",
                    badgeColor = Sky400
                )
                ProtocolCommandRow(
                    title = "ACK SET_TIME (Board → Phone)",
                    detail = "Opcode 0x91 (Total 10 byte: result u8 + uint64 LE adjust ms)",
                    badge = "0x91",
                    badgeColor = Sky400
                )
                ProtocolCommandRow(
                    title = "LIST (Phone → Board)",
                    detail = "Opcode 0x20 (Minta daftar berkas flash)",
                    badge = "0x20",
                    badgeColor = Emerald400
                )
                ProtocolCommandRow(
                    title = "LIST_BEGIN / ITEM / END",
                    detail = "0xA0 (BEGIN: total), 0xA1 (ITEM: 26 B), 0xA2 (END: sent)",
                    badge = "0xA0..A2",
                    badgeColor = Sky400
                )
                ProtocolCommandRow(
                    title = "GET_FILE (Phone → Board)",
                    detail = "Opcode 0x21 (19 B: name[12] + offset u32 + max_chunk 180)",
                    badge = "0x21",
                    badgeColor = Emerald400
                )
                ProtocolCommandRow(
                    title = "CHUNK (Board → Phone)",
                    detail = "Opcode 0xB1 (Header 12 B: result, offset, file_size, len + data)",
                    badge = "0xB1",
                    badgeColor = Sky400
                )
                ProtocolCommandRow(
                    title = "DELETE_FILE (Phone → Board)",
                    detail = "Opcode 0x23 (13 B: 0x23 + name[12] ASCII tanpa .bin)",
                    badge = "0x23",
                    badgeColor = Red400
                )
                ProtocolCommandRow(
                    title = "ACK_DELETE (Board → Phone)",
                    detail = "Opcode 0xA3 (2 B: result 0=OK, 1=not found, 2=busy OPEN)",
                    badge = "0xA3",
                    badgeColor = Red400
                )
                ProtocolCommandRow(
                    title = "FORMAT_FLASH (Phone → Board)",
                    detail = "Opcode 0x24 (2 B: [0x24, 0xA5] magic confirm wajib)",
                    badge = "0x24",
                    badgeColor = Red500
                )
                ProtocolCommandRow(
                    title = "ACK_FORMAT (Board → Phone)",
                    detail = "Opcode 0xA4 (2 B: result 0=OK, 1=stop measure, 2=rejected)",
                    badge = "0xA4",
                    badgeColor = Red500
                )
            }
        }

        // 6. Fitur Mendatang (Coming Soon / Phase E)
        PanduanCard(
            icon = Icons.Default.Upcoming,
            iconTint = Slate400,
            title = "STREAM LIVE",
            subtitle = "Opcode 0x30 / 0xB2 — PLG1 v4, 29 B"
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                FutureFeatureItem(
                    name = "STREAM OSILOSKOP",
                    desc = "Start/Stop saat measure ON. Paket 0xB2 = seq + t_rel_ms + d1..d11. Grup Umum/Accel/Gyro/Mag, Y fisik (g, °/s, µT)."
                )
            }
        }
    }
}

@Composable
private fun PanduanCard(
    icon: ImageVector,
    iconTint: Color,
    title: String,
    subtitle: String,
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Slate850)
            .border(1.dp, Slate700, RoundedCornerShape(20.dp))
            .padding(18.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(Slate800),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = iconTint,
                        modifier = Modifier.size(18.dp)
                    )
                }
                Column {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.labelSmall,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.2.sp,
                        color = iconTint
                    )
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        fontSize = 11.sp,
                        color = Slate400
                    )
                }
            }
            content()
        }
    }
}

@Composable
private fun InstructionItem(
    badge: String,
    badgeColor: Color,
    title: String,
    desc: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Slate800)
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(badgeColor.copy(alpha = 0.15f))
                .border(1.dp, badgeColor.copy(alpha = 0.4f), RoundedCornerShape(8.dp))
                .padding(horizontal = 8.dp, vertical = 6.dp)
        ) {
            Text(
                text = badge,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = badgeColor
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                fontSize = 13.sp,
                color = Slate100
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = desc,
                style = MaterialTheme.typography.bodySmall,
                fontSize = 12.sp,
                color = Slate300,
                lineHeight = 17.sp
            )
        }
    }
}

@Composable
private fun LedPatternItem(
    label: String,
    pattern: String,
    desc: String,
    color: Color
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Slate800)
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .padding(top = 4.dp)
                .size(10.dp)
                .clip(CircleShape)
                .background(color)
        )
        Column(modifier = Modifier.weight(1f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = label,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Slate100
                )
                Text(
                    text = pattern,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    color = color
                )
            }
            Spacer(modifier = Modifier.height(3.dp))
            Text(
                text = desc,
                style = MaterialTheme.typography.bodySmall,
                fontSize = 12.sp,
                color = Slate400,
                lineHeight = 16.sp
            )
        }
    }
}

@Composable
private fun ProtocolCommandRow(
    title: String,
    detail: String,
    badge: String,
    badgeColor: Color
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(Slate800)
            .padding(10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = title,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Slate100
            )
            Text(
                text = detail,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = Slate400
            )
        }
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(6.dp))
                .background(badgeColor.copy(alpha = 0.15f))
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(
                text = badge,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = badgeColor
            )
        }
    }
}

@Composable
private fun FutureFeatureItem(
    name: String,
    desc: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Slate900)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = name,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            color = Slate400
        )
        Text(
            text = desc,
            fontSize = 11.sp,
            color = Slate500
        )
    }
}
