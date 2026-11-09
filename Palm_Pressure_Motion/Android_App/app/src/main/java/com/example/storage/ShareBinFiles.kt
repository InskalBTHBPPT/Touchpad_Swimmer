package com.example.storage

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import java.io.File

fun shareBinFiles(context: Context, files: List<File>) {
    val existing = files.filter { it.isFile && it.exists() && it.length() > 0L }
    if (existing.isEmpty()) return

    val authority = "${context.packageName}.fileprovider"
    val uris = existing.map { file ->
        FileProvider.getUriForFile(context, authority, file)
    }
    val send = if (uris.size == 1) {
        Intent(Intent.ACTION_SEND).apply {
            type = "application/octet-stream"
            putExtra(Intent.EXTRA_STREAM, uris[0])
            putExtra(Intent.EXTRA_SUBJECT, existing[0].name)
        }
    } else {
        Intent(Intent.ACTION_SEND_MULTIPLE).apply {
            type = "application/octet-stream"
            putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
            putExtra(Intent.EXTRA_SUBJECT, "PalmLog ${existing.size} berkas")
        }
    }
    send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    context.startActivity(Intent.createChooser(send, "Bagikan berkas .bin"))
}
