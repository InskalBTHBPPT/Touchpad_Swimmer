package com.example.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.PlotSensorGroup
import com.example.model.StreamSample
import com.example.ui.theme.Amber400
import com.example.ui.theme.Amber950
import com.example.ui.theme.Emerald300
import com.example.ui.theme.Emerald400
import com.example.ui.theme.Emerald950
import com.example.ui.theme.Red400
import com.example.ui.theme.Sky400
import com.example.ui.theme.Sky950
import com.example.ui.theme.Slate200
import com.example.ui.theme.Slate300
import com.example.ui.theme.Slate400
import com.example.ui.theme.Slate500
import com.example.ui.theme.Slate700
import com.example.ui.theme.Slate800
import com.example.ui.theme.Slate850
import com.example.ui.theme.Slate950
import com.example.ui.theme.getChannelColor

/** Stream live PLG1 v4: paket 0xB2 = 29 B, Y fisik, grup seperti plot berkas. */
@Composable
fun StreamTabContent(
    isConnected: Boolean,
    measureActive: Boolean,
    isStreaming: Boolean,
    samples: List<StreamSample>,
    selectedChannels: Set<Int>,
    onToggleStream: () -> Unit,
    onToggleChannel: (Int) -> Unit,
    onSelectChannels: (Set<Int>) -> Unit,
    modifier: Modifier = Modifier
) {
    var group by remember { mutableStateOf(PlotSensorGroup.GENERAL) }
    val canPress = isConnected && (measureActive || isStreaming)

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(14.dp))
                    .background(if (measureActive) Emerald950 else Slate850)
                    .border(
                        1.dp,
                        if (measureActive) Emerald400.copy(alpha = 0.6f) else Slate700,
                        RoundedCornerShape(14.dp)
                    )
                    .padding(horizontal = 12.dp, vertical = 10.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(text = "Measure", fontSize = 11.sp, color = Slate400)
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(if (measureActive) Emerald400 else Slate500)
                        )
                        Text(
                            text = if (measureActive) "AKTIF" else "BERHENTI",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = if (measureActive) Emerald300 else Slate300
                        )
                    }
                }
            }
            Button(
                onClick = onToggleStream,
                enabled = canPress,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isStreaming) Red400 else Sky400,
                    contentColor = Slate950,
                    disabledContainerColor = Slate800,
                    disabledContentColor = Slate500
                ),
                modifier = Modifier
                    .weight(1f)
                    .height(58.dp)
            ) {
                Icon(
                    imageVector = if (isStreaming) Icons.Default.Stop else Icons.Default.PlayArrow,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Text(
                    text = if (isStreaming) "Stop" else "Start",
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(start = 6.dp)
                )
            }
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Amber950)
                .border(1.dp, Amber400.copy(alpha = 0.55f), RoundedCornerShape(12.dp))
                .padding(horizontal = 12.dp, vertical = 10.dp)
        ) {
            Text(
                text = "Peringatan: Stream hanya untuk uji sensor. Jangan dipakai saat perekaman data " +
                    "sebenarnya — stream memperlambat tulis ke flash dan bisa membuat sampel hilang (drop).",
                fontSize = 12.sp,
                lineHeight = 16.sp,
                fontWeight = FontWeight.Medium,
                color = Amber400
            )
        }

        Text(
            text = when {
                !isConnected -> "Hubungkan board. Stream hanya saat measure aktif."
                !measureActive -> "Measure berhenti. Nyalakan measure di board, lalu Start."
                isStreaming -> "Live 0xB2 (29 B): t_rel + d1..d11. Sampel dibuang jika BLE penuh."
                else -> "Tekan Start — format sama PLG1 v4 (FW 3.1.x)."
            },
            fontSize = 12.sp,
            color = Slate400
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(Slate850)
                .border(1.dp, Slate700, RoundedCornerShape(14.dp))
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Grup sensor",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Slate200
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                PlotSensorGroup.entries.forEach { g ->
                    val active = g == group
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (active) Sky950 else Slate800)
                            .border(1.dp, if (active) Sky400 else Slate700, RoundedCornerShape(8.dp))
                            .clickable {
                                group = g
                                onSelectChannels(g.channelNums.toSet())
                            }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = if (g.unitLabel.isEmpty()) g.label else "${g.label}\n(${g.unitLabel})",
                            fontSize = 10.sp,
                            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                            color = if (active) Sky400 else Slate300,
                            lineHeight = 12.sp
                        )
                    }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Kanal overlay", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Slate300)
                val allInGroup = group.channelNums.toSet()
                val isAll = selectedChannels.containsAll(allInGroup) && selectedChannels.size == allInGroup.size
                Text(
                    text = if (isAll) "Semua ✓" else "Semua",
                    fontSize = 11.sp,
                    color = Sky400,
                    modifier = Modifier.clickable {
                        onSelectChannels(
                            if (isAll) setOf(group.channelNums.first()) else allInGroup
                        )
                    }
                )
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                for (ch in group.channelNums) {
                    val on = ch in selectedChannels
                    val color = getChannelColor(ch)
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (on) color.copy(alpha = 0.25f) else Slate800)
                            .border(1.dp, if (on) color else Slate700, RoundedCornerShape(8.dp))
                            .clickable { onToggleChannel(ch) }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "d$ch",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = if (on) color else Slate400
                        )
                    }
                }
            }
        }

        val unitHint = group.unitLabel.ifEmpty { "mentah" }
        Text(
            text = "Y = fisik ($unitHint) · X = urutan buffer live",
            fontSize = 11.sp,
            color = Slate500
        )

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Slate950)
                .border(1.dp, Slate700, RoundedCornerShape(16.dp))
        ) {
            if (samples.size < 2) {
                Text(
                    text = if (isStreaming) "Menunggu sampel..." else "Belum ada data stream",
                    color = Slate500,
                    fontSize = 12.sp,
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LivePlot(samples = samples, channels = selectedChannels)
            }
        }

        if (samples.isNotEmpty()) {
            val last = samples.last()
            Text(
                text = "seq=${last.seq}  t_rel=${last.tRelMs} ms  n=${samples.size}",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = Slate500
            )
        }
    }
}

@Composable
private fun LivePlot(samples: List<StreamSample>, channels: Set<Int>) {
    Canvas(modifier = Modifier.fillMaxWidth().height(220.dp).padding(8.dp)) {
        val chosen = channels.sorted()
        if (chosen.isEmpty() || samples.size < 2) return@Canvas

        var minV = Float.POSITIVE_INFINITY
        var maxV = Float.NEGATIVE_INFINITY
        for (s in samples) {
            for (ch in chosen) {
                val v = s.physicalChannel(ch)
                if (v < minV) minV = v
                if (v > maxV) maxV = v
            }
        }
        val range = (maxV - minV).coerceAtLeast(1e-6f)
        val n = samples.size
        for (ch in chosen) {
            val path = Path()
            samples.forEachIndexed { i, s ->
                val x = i.toFloat() / (n - 1).toFloat() * size.width
                val y = size.height - ((s.physicalChannel(ch) - minV) / range) * (size.height - 8f) - 4f
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(
                path,
                getChannelColor(ch),
                style = Stroke(width = 2.2f, cap = StrokeCap.Round)
            )
        }
        drawLine(Slate800, Offset(0f, size.height - 1f), Offset(size.width, size.height - 1f), 1f)
    }
}
