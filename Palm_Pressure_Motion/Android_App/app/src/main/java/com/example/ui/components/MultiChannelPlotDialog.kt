package com.example.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.example.model.ChannelStats
import com.example.model.PlgParsedData
import com.example.model.PlgRecord
import com.example.model.PlotSensorGroup
import com.example.ui.theme.*
import java.util.Locale

/**
 * Plot berkas PLG1 v4: 4 grup sensor, sumbu X = t_rel_ms, Y = nilai fisik (float).
 */
@Composable
fun MultiChannelPlotDialog(
    plotData: PlgParsedData,
    onDismiss: () -> Unit
) {
    var selectedGroup by rememberSaveable { mutableStateOf(PlotSensorGroup.GENERAL.name) }
    val group = PlotSensorGroup.valueOf(selectedGroup)
    var selectedChannels by rememberSaveable {
        mutableStateOf(group.channelNums.toSet())
    }
    var isNormalizedScale by rememberSaveable { mutableStateOf(false) }
    var showAbsoluteTimeAxis by rememberSaveable { mutableStateOf(plotData.hasPreciseStartMs) }

    fun selectGroup(g: PlotSensorGroup) {
        selectedGroup = g.name
        selectedChannels = g.channelNums.toSet()
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth(0.96f)
                .heightIn(max = 720.dp)
                .clip(RoundedCornerShape(20.dp)),
            color = Slate900,
            tonalElevation = 6.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .wrapContentHeight()
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
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
                                .size(36.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(Emerald950)
                                .border(1.dp, Emerald400.copy(alpha = 0.5f), RoundedCornerShape(10.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.ShowChart,
                                contentDescription = null,
                                tint = Emerald400,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Column {
                            Text(
                                text = "Plot Sensor PLG1 v4",
                                style = MaterialTheme.typography.titleMedium,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Slate100
                            )
                            Text(
                                text = "${plotData.fileName} • ${plotData.durationText}",
                                style = MaterialTheme.typography.bodySmall,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate400
                            )
                        }
                    }

                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .size(34.dp)
                            .testTag("close_plot_dialog_button"),
                        shape = CircleShape,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Slate300),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Tutup Plot",
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(if (plotData.hasPreciseStartMs) Emerald950 else Slate850)
                        .border(
                            1.dp,
                            if (plotData.hasPreciseStartMs) Emerald400.copy(alpha = 0.4f) else Slate700,
                            RoundedCornerShape(10.dp)
                        )
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
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
                                Text(
                                    text = "Waktu Awal:",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (plotData.hasPreciseStartMs) Emerald400 else Slate400
                                )
                                Text(
                                    text = if (plotData.hasPreciseStartMs) {
                                        plotData.formattedStartMsText
                                    } else {
                                        val fn = plotData.fileName.removeSuffix(".bin")
                                        if (fn.length >= 12) {
                                            "20${fn.substring(0, 2)}-${fn.substring(2, 4)}-${fn.substring(4, 6)} " +
                                                "${fn.substring(6, 8)}:${fn.substring(8, 10)}:${fn.substring(10, 12)}.000"
                                        } else {
                                            "-"
                                        }
                                    },
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.SemiBold,
                                    color = if (plotData.hasPreciseStartMs) Emerald300 else Slate300
                                )
                            }
                            Text(
                                text = "PLG1 v${plotData.version} • ${plotData.recordSize} B",
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate400
                            )
                        }
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Text(
                                text = "Epoch:",
                                style = MaterialTheme.typography.labelSmall,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (plotData.hasPreciseStartMs) Emerald400.copy(alpha = 0.8f) else Slate500
                            )
                            Text(
                                text = if (plotData.hasPreciseStartMs) {
                                    "${plotData.startUnixMs} ms"
                                } else {
                                    "start_unix_ms = 0"
                                },
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = if (plotData.hasPreciseStartMs) Emerald300 else Slate400
                            )
                        }
                    }
                }

                // Grup sensor
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
                        style = MaterialTheme.typography.labelMedium,
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
                                    .border(
                                        1.dp,
                                        if (active) Sky400 else Slate700,
                                        RoundedCornerShape(8.dp)
                                    )
                                    .clickable { selectGroup(g) }
                                    .padding(vertical = 8.dp)
                                    .testTag("plot_group_${g.name.lowercase()}"),
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
                        Text(
                            text = "Kanal overlay",
                            style = MaterialTheme.typography.labelMedium,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Slate200
                        )
                        val allInGroup = group.channelNums.toSet()
                        val isAllSelected = selectedChannels.containsAll(allInGroup.toList()) &&
                            selectedChannels.size == allInGroup.size
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isAllSelected) Sky950 else Slate800)
                                .border(
                                    1.dp,
                                    if (isAllSelected) Sky400 else Slate700,
                                    RoundedCornerShape(8.dp)
                                )
                                .clickable {
                                    selectedChannels = if (isAllSelected) {
                                        setOf(group.channelNums.first())
                                    } else {
                                        allInGroup
                                    }
                                }
                                .padding(horizontal = 10.dp, vertical = 5.dp)
                                .testTag("select_all_channels_button")
                        ) {
                            Text(
                                text = if (isAllSelected) "Semua ✓" else "Semua",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if (isAllSelected) Sky400 else Slate300
                            )
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        for (ch in group.channelNums) {
                            val isSelected = selectedChannels.contains(ch)
                            val color = getChannelColor(ch)
                            SimpleChannelButton(
                                channelNum = ch,
                                isSelected = isSelected,
                                channelColor = color,
                                onClick = {
                                    selectedChannels = if (isSelected) {
                                        if (selectedChannels.size > 1) selectedChannels - ch else selectedChannels
                                    } else {
                                        selectedChannels + ch
                                    }
                                },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (showAbsoluteTimeAxis) Emerald950 else Slate800)
                            .border(
                                1.dp,
                                if (showAbsoluteTimeAxis) Emerald400 else Slate700,
                                RoundedCornerShape(8.dp)
                            )
                            .clickable {
                                if (plotData.hasPreciseStartMs) {
                                    showAbsoluteTimeAxis = !showAbsoluteTimeAxis
                                }
                            }
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                            .testTag("toggle_time_axis_button")
                    ) {
                        Text(
                            text = if (showAbsoluteTimeAxis) "Sumbu X: Absolut" else "Sumbu X: t_rel (s)",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = if (showAbsoluteTimeAxis) Emerald300 else Slate300
                        )
                    }

                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Slate800)
                            .border(1.dp, Slate700, RoundedCornerShape(8.dp))
                            .clickable { isNormalizedScale = !isNormalizedScale }
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                            .testTag("toggle_scale_mode_button")
                    ) {
                        Text(
                            text = if (isNormalizedScale) "Y: Normalisasi" else "Y: Fisik",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = Sky400
                        )
                    }
                }

                Text(
                    text = if (isNormalizedScale) {
                        "Mode Y: Normalisasi 0..100% per kanal"
                    } else {
                        val u = group.unitLabel.ifEmpty { "nilai mentah" }
                        "Mode Y: Fisik ($u) — skala bersama kanal terpilih"
                    },
                    fontSize = 11.sp,
                    color = Slate400,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { isNormalizedScale = !isNormalizedScale }
                )

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(Slate950)
                        .border(1.dp, Slate800, RoundedCornerShape(14.dp))
                        .padding(8.dp)
                ) {
                    PhysicalWaveformCanvas(
                        records = plotData.records,
                        selectedChannels = selectedChannels,
                        isNormalizedScale = isNormalizedScale,
                        modifier = Modifier.fillMaxSize()
                    )
                }

                if (plotData.records.isNotEmpty()) {
                    val first = plotData.records.first()
                    val last = plotData.records.last()
                    if (plotData.hasPreciseStartMs && showAbsoluteTimeAxis) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 4.dp),
                            verticalArrangement = Arrangement.spacedBy(2.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = plotData.formatTimestampCompact(first.absoluteUnixMs),
                                    fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Emerald300
                                )
                                Text(
                                    text = "+${plotData.totalDurationMs} ms",
                                    fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate400
                                )
                                Text(
                                    text = plotData.formatTimestampCompact(last.absoluteUnixMs),
                                    fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Emerald300
                                )
                            }
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "t_rel ${first.tRelMs} ms",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate500
                                )
                                Text(
                                    text = "periode ${plotData.periodMs} ms",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate500
                                )
                                Text(
                                    text = "t_rel ${last.tRelMs} ms",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Slate500
                                )
                            }
                        }
                    } else {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = String.format(Locale.US, "%.3f s", first.tRelMs / 1000.0),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate500
                            )
                            Text(
                                text = "X = t_rel_ms",
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate500
                            )
                            Text(
                                text = String.format(Locale.US, "%.3f s", last.tRelMs / 1000.0),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Slate500
                            )
                        }
                    }
                }

                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = "STATISTIK (${selectedChannels.size} KANAL, FISIK):",
                        style = MaterialTheme.typography.labelSmall,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        color = Slate400
                    )
                    selectedChannels.sorted().forEach { ch ->
                        val stats = plotData.getStatsForChannel(ch)
                        ChannelStatsRow(stats = stats, color = getChannelColor(ch))
                    }
                }

                Button(
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(42.dp)
                        .testTag("close_plot_bottom_button"),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Slate800,
                        contentColor = Slate100
                    )
                ) {
                    Text(text = "Tutup Plot", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                }
            }
        }
    }
}

@Composable
private fun SimpleChannelButton(
    channelNum: Int,
    isSelected: Boolean,
    channelColor: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .height(36.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(if (isSelected) channelColor.copy(alpha = 0.22f) else Slate800)
            .border(
                width = if (isSelected) 1.5.dp else 1.dp,
                color = if (isSelected) channelColor else Slate700,
                shape = RoundedCornerShape(8.dp)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 6.dp)
            .testTag("channel_btn_d$channelNum"),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(7.dp)
                    .clip(CircleShape)
                    .background(if (isSelected) channelColor else channelColor.copy(alpha = 0.4f))
            )
            Text(
                text = "d$channelNum",
                fontSize = 13.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                fontFamily = FontFamily.Monospace,
                color = if (isSelected) Slate100 else Slate400
            )
        }
    }
}

@Composable
private fun ChannelStatsRow(
    stats: ChannelStats,
    color: Color,
    modifier: Modifier = Modifier
) {
    fun fmt(v: Float): String =
        if (stats.unit.isEmpty()) {
            String.format(Locale.US, "%.0f", v)
        } else {
            String.format(Locale.US, "%.3f", v)
        }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Slate850)
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(8.dp))
            .padding(horizontal = 10.dp, vertical = 7.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(color)
            )
            Text(
                text = stats.name,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                color = color
            )
            if (stats.unit.isNotEmpty()) {
                Text(
                    text = stats.unit,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    color = Slate400
                )
            }
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Min: ${fmt(stats.min)}",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = Slate300
            )
            Text(
                text = "Max: ${fmt(stats.max)}",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = Slate300
            )
            Text(
                text = "Avg: ${fmt(stats.avg)}",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.SemiBold,
                color = color
            )
        }
    }
}

@Composable
private fun PhysicalWaveformCanvas(
    records: List<PlgRecord>,
    selectedChannels: Set<Int>,
    isNormalizedScale: Boolean,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        if (records.isEmpty() || selectedChannels.isEmpty()) return@Canvas

        val gridLines = 4
        for (i in 0..gridLines) {
            val y = (height / gridLines) * i
            drawLine(color = Slate800, start = Offset(0f, y), end = Offset(width, y), strokeWidth = 1f)
        }
        for (i in 1 until 4) {
            val x = (width / 4) * i
            drawLine(color = Slate850, start = Offset(x, 0f), end = Offset(x, height), strokeWidth = 1f)
        }

        val t0 = records.first().tRelMs.toFloat()
        val t1 = records.last().tRelMs.toFloat()
        val tSpan = (t1 - t0).coerceAtLeast(1f)

        var globalMin = Float.POSITIVE_INFINITY
        var globalMax = Float.NEGATIVE_INFINITY
        if (!isNormalizedScale) {
            for (rec in records) {
                for (ch in selectedChannels) {
                    val v = rec.physicalChannel(ch)
                    if (v < globalMin) globalMin = v
                    if (v > globalMax) globalMax = v
                }
            }
        }
        val globalRange = (globalMax - globalMin).coerceAtLeast(1e-6f)

        val step = (records.size / width.toInt().coerceAtLeast(1)).coerceAtLeast(1)

        for (ch in selectedChannels.sorted()) {
            val color = getChannelColor(ch)
            var chMin = Float.POSITIVE_INFINITY
            var chMax = Float.NEGATIVE_INFINITY
            if (isNormalizedScale) {
                for (rec in records) {
                    val v = rec.physicalChannel(ch)
                    if (v < chMin) chMin = v
                    if (v > chMax) chMax = v
                }
            }
            val chRange = (chMax - chMin).coerceAtLeast(1e-6f)

            val path = Path()
            var first = true
            for (i in records.indices step step) {
                val rec = records[i]
                val v = rec.physicalChannel(ch)
                val x = ((rec.tRelMs.toFloat() - t0) / tSpan) * width
                val normalized = if (isNormalizedScale) {
                    (v - chMin) / chRange
                } else {
                    (v - globalMin) / globalRange
                }
                val y = height - (normalized * (height - 24f)) - 12f
                if (first) {
                    path.moveTo(x, y)
                    first = false
                } else {
                    path.lineTo(x, y)
                }
            }
            drawPath(path = path, color = color, style = Stroke(width = 2.2f, cap = StrokeCap.Round))
        }
    }
}
