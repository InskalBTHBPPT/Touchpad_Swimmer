package com.example.ui.theme

import androidx.compose.ui.graphics.Color

// PalmLog Brand Palette - Professional Slate & Emerald
val Slate950 = Color(0xFF090D16)
val Slate900 = Color(0xFF0F172A)
val Slate850 = Color(0xFF162032)
val Slate800 = Color(0xFF1E293B)
val Slate700 = Color(0xFF334155)
val Slate600 = Color(0xFF475569)
val Slate500 = Color(0xFF64748B)
val Slate400 = Color(0xFF94A3B8)
val Slate300 = Color(0xFFCBD5E1)
val Slate200 = Color(0xFFE2E8F0)
val Slate100 = Color(0xFFF1F5F9)

// Emerald & Mint (Primary / Active / Measurement)
val Emerald500 = Color(0xFF10B981)
val Emerald400 = Color(0xFF34D399)
val Emerald300 = Color(0xFF6EE7B7)
val Emerald900 = Color(0xFF064E3B)
val Emerald950 = Color(0xFF022C22)

// Cyan & Blue (BLE & Status)
val Sky200 = Color(0xFFBAE6FD)
val Sky300 = Color(0xFF7DD3FC)
val Sky400 = Color(0xFF38BDF8)
val Sky500 = Color(0xFF0EA5E9)
val Sky950 = Color(0xFF082F49)
val Blue600 = Color(0xFF2563EB)

// Alert colors
val Amber400 = Color(0xFFFBBF24)
val Amber500 = Color(0xFFF59E0B)
val Amber950 = Color(0xFF451A03)
val Red400 = Color(0xFFF87171)
val Red500 = Color(0xFFEF4444)
val Red950 = Color(0xFF450A0A)

// Multi-channel Waveform Plot Colors (d1..d8)
val ChannelD1Color = Color(0xFF10B981) // Emerald (Green)
val ChannelD2Color = Color(0xFF38BDF8) // Sky (Blue)
val ChannelD3Color = Color(0xFFF59E0B) // Amber (Yellow)
val ChannelD4Color = Color(0xFFF43F5E) // Rose (Red)
val ChannelD5Color = Color(0xFF8B5CF6) // Violet (Purple)
val ChannelD6Color = Color(0xFF06B6D4) // Cyan (Teal)
val ChannelD7Color = Color(0xFFFB923C) // Orange (Coral)
val ChannelD8Color = Color(0xFFEC4899) // Pink (Magenta)
val ChannelD9Color = Color(0xFFA78BFA) // Light violet
val ChannelD10Color = Color(0xFF2DD4BF) // Teal
val ChannelD11Color = Color(0xFFF472B6) // Light pink

fun getChannelColor(channelNum: Int): Color = when (channelNum) {
    1 -> ChannelD1Color
    2 -> ChannelD2Color
    3 -> ChannelD3Color
    4 -> ChannelD4Color
    5 -> ChannelD5Color
    6 -> ChannelD6Color
    7 -> ChannelD7Color
    8 -> ChannelD8Color
    9 -> ChannelD9Color
    10 -> ChannelD10Color
    11 -> ChannelD11Color
    else -> Slate400
}
