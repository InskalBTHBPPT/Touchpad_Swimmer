package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val PalmLogColorScheme = darkColorScheme(
    primary = Emerald400,
    onPrimary = Slate950,
    primaryContainer = Emerald950,
    onPrimaryContainer = Emerald300,
    secondary = Sky400,
    onSecondary = Slate950,
    secondaryContainer = Slate800,
    onSecondaryContainer = Sky400,
    tertiary = Amber400,
    onTertiary = Slate950,
    background = Slate900,
    onBackground = Slate100,
    surface = Slate850,
    onSurface = Slate100,
    surfaceVariant = Slate800,
    onSurfaceVariant = Slate400,
    outline = Slate700,
    outlineVariant = Slate800,
    error = Red400,
    onError = Slate950,
    errorContainer = Red950,
    onErrorContainer = Red400
)

@Composable
fun MyApplicationTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = PalmLogColorScheme,
        typography = Typography,
        content = content
    )
}
