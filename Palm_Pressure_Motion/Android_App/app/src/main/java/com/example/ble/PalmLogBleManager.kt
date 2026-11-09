package com.example.ble

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import com.example.model.BleConnectionState
import com.example.model.DiscoveredDevice
import com.example.model.FileChunkResponse
import com.example.model.LogFileInfo
import com.example.model.PalmLogStatus
import com.example.model.SetTimeAck
import com.example.model.StreamSample
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@SuppressLint("MissingPermission")
class PalmLogBleManager(
    private val context: Context,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main)
) {
    private val bluetoothManager: BluetoothManager? =
        context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager

    private val bluetoothAdapter: BluetoothAdapter?
        get() = bluetoothManager?.adapter

    private val scanner: BluetoothLeScanner?
        get() = bluetoothAdapter?.bluetoothLeScanner

    private var activeGatt: BluetoothGatt? = null
    private var isScanningInternal = false
    private var currentMtu = 23
    private var isNotifyConfigured = false

    // Chunk packet assembly buffer for multi-packet / fragmented CHUNK (0xB1) responses
    private val chunkAssemblyBuffer = ByteArrayOutputStream()
    private var expectedChunkTotalLength = 0

    // Guard: Only parse LIST_BEGIN (0xA0), LIST_ITEM (0xA1), LIST_END (0xA2) when LIST command is active
    @Volatile
    private var isAwaitingFileList: Boolean = false

    private val _connectionState = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    val connectionState: StateFlow<BleConnectionState> = _connectionState.asStateFlow()

    private val _discoveredDevices = MutableStateFlow<List<DiscoveredDevice>>(emptyList())
    val discoveredDevices: StateFlow<List<DiscoveredDevice>> = _discoveredDevices.asStateFlow()

    private val _boardStatus = MutableStateFlow<PalmLogStatus?>(null)
    val boardStatus: StateFlow<PalmLogStatus?> = _boardStatus.asStateFlow()

    private val _lastRawRx = MutableStateFlow<ByteArray?>(null)
    val lastRawRx: StateFlow<ByteArray?> = _lastRawRx.asStateFlow()

    private val _lastSetTimeAck = MutableSharedFlow<SetTimeAck>(extraBufferCapacity = 1)
    val lastSetTimeAck: SharedFlow<SetTimeAck> = _lastSetTimeAck.asSharedFlow()

    private val _streamSamples = MutableSharedFlow<StreamSample>(
        extraBufferCapacity = 128,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val streamSamples: SharedFlow<StreamSample> = _streamSamples.asSharedFlow()

    private val _streamAck = MutableSharedFlow<Int>(extraBufferCapacity = 4)
    val streamAck: SharedFlow<Int> = _streamAck.asSharedFlow()

    private val _listBeginFlow = MutableSharedFlow<Int>(extraBufferCapacity = 16)
    val listBeginFlow: SharedFlow<Int> = _listBeginFlow.asSharedFlow()

    private val _listItemFlow = MutableSharedFlow<LogFileInfo>(extraBufferCapacity = 64)
    val listItemFlow: SharedFlow<LogFileInfo> = _listItemFlow.asSharedFlow()

    private val _listEndFlow = MutableSharedFlow<Int>(extraBufferCapacity = 16)
    val listEndFlow: SharedFlow<Int> = _listEndFlow.asSharedFlow()

    private val _chunkFlow = MutableSharedFlow<FileChunkResponse>(extraBufferCapacity = 64)
    val chunkFlow: SharedFlow<FileChunkResponse> = _chunkFlow.asSharedFlow()

    private val _deleteAckFlow = MutableSharedFlow<Int>(extraBufferCapacity = 8)
    val deleteAckFlow: SharedFlow<Int> = _deleteAckFlow.asSharedFlow()

    private val _formatAckFlow = MutableSharedFlow<Int>(extraBufferCapacity = 8)
    val formatAckFlow: SharedFlow<Int> = _formatAckFlow.asSharedFlow()

    private val _userMessage = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val userMessage: SharedFlow<String> = _userMessage.asSharedFlow()

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device ?: return
            val name = result.scanRecord?.deviceName ?: device.name ?: "BLE Device"
            val address = device.address ?: ""
            val rssi = result.rssi

            val isTarget = BleConstants.isTargetName(name)

            val current = _discoveredDevices.value.toMutableList()
            val existingIndex = current.indexOfFirst { it.address == address }
            val item = DiscoveredDevice(name = name, address = address, rssi = rssi, isTarget = isTarget)

            if (existingIndex >= 0) {
                current[existingIndex] = item
            } else {
                current.add(item)
            }

            // Sort PalmLog* target devices first, then by signal strength (RSSI)
            current.sortWith(compareByDescending<DiscoveredDevice> { it.isTarget }.thenByDescending { it.rssi })
            _discoveredDevices.value = current
        }

        override fun onScanFailed(errorCode: Int) {
            isScanningInternal = false
            _connectionState.value = BleConnectionState.Error("Pemindaian gagal: kode error $errorCode")
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            val deviceName = gatt.device?.name ?: BleConstants.TARGET_DEVICE_NAME
            val address = gatt.device?.address ?: ""

            if (status != BluetoothGatt.GATT_SUCCESS) {
                activeGatt?.close()
                activeGatt = null
                isNotifyConfigured = false
                isAwaitingFileList = false
                expectedChunkTotalLength = 0
                chunkAssemblyBuffer.reset()
                currentMtu = 23
                _connectionState.value = BleConnectionState.Disconnected
                _userMessage.tryEmit("Koneksi terputus (status $status)")
                return
            }

            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    _connectionState.value = BleConnectionState.Connecting(deviceName, address)
                    // Discover GATT services immediately after connect
                    gatt.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    activeGatt?.close()
                    activeGatt = null
                    isNotifyConfigured = false
                    isAwaitingFileList = false
                    expectedChunkTotalLength = 0
                    chunkAssemblyBuffer.reset()
                    currentMtu = 23
                    _connectionState.value = BleConnectionState.Disconnected
                    _userMessage.tryEmit("Perangkat terputus")
                }
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            val deviceName = gatt.device?.name ?: BleConstants.TARGET_DEVICE_NAME
            val address = gatt.device?.address ?: ""

            if (status != BluetoothGatt.GATT_SUCCESS) {
                _connectionState.value = BleConnectionState.Error("Gagal membaca layanan GATT: $status")
                return
            }

            // Step 1: Request MTU 247 sequentially.
            // On Android, calling requestMtu and writeDescriptor concurrently causes one to fail with mDeviceBusy.
            val mtuRequested = try {
                gatt.requestMtu(BleConstants.REQUESTED_MTU)
            } catch (e: Exception) {
                e.printStackTrace()
                false
            }

            // Fallback: If onMtuChanged does not fire within 600ms, proceed to enable notifications
            scope.launch {
                delay(600)
                if (!isNotifyConfigured) {
                    enableTxNotifications(gatt, deviceName, address)
                }
            }

            if (!mtuRequested) {
                enableTxNotifications(gatt, deviceName, address)
            }
        }

        override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
            val deviceName = gatt.device?.name ?: BleConstants.TARGET_DEVICE_NAME
            val address = gatt.device?.address ?: ""

            if (status == BluetoothGatt.GATT_SUCCESS) {
                currentMtu = mtu
                val current = _connectionState.value
                if (current is BleConnectionState.Connected) {
                    _connectionState.value = current.copy(mtu = mtu)
                }
            }

            // Step 2: Now that MTU is negotiated, request high connection priority and enable notifications
            try {
                gatt.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH)
            } catch (e: Exception) {
                e.printStackTrace()
            }

            enableTxNotifications(gatt, deviceName, address)
        }

        override fun onDescriptorWrite(
            gatt: BluetoothGatt,
            descriptor: BluetoothGattDescriptor,
            status: Int
        ) {
            if (descriptor.uuid == BleConstants.CCCD_DESCRIPTOR_UUID && status == BluetoothGatt.GATT_SUCCESS) {
                isNotifyConfigured = true
                val deviceName = gatt.device?.name ?: BleConstants.TARGET_DEVICE_NAME
                val address = gatt.device?.address ?: ""
                _connectionState.value = BleConnectionState.Connected(
                    deviceName = deviceName,
                    address = address,
                    mtu = currentMtu,
                    isNotifyEnabled = true
                )
                _userMessage.tryEmit("Terhubung ke $deviceName")

                // Automatically send GET_STATUS (0x10) to fetch initial board status
                scope.launch {
                    delay(300)
                    sendGetStatus()
                }
            }
        }

        // Android 13+ (API 33+) characteristic notify callback
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            value: ByteArray
        ) {
            if (characteristic.uuid == BleConstants.NUS_TX_CHAR_UUID) {
                handleIncomingBytes(value)
            }
        }

        // Legacy characteristic notify callback (API <= 32)
        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic
        ) {
            if (characteristic.uuid == BleConstants.NUS_TX_CHAR_UUID) {
                @Suppress("DEPRECATION")
                val value = characteristic.value ?: return
                handleIncomingBytes(value)
            }
        }
    }

    private fun handleIncomingBytes(value: ByteArray) {
        val copy = value.copyOf()
        _lastRawRx.value = copy
        if (copy.isEmpty()) return

        // 1. If currently assembling a multi-packet CHUNK (0xB1) response
        if (expectedChunkTotalLength > 0) {
            chunkAssemblyBuffer.write(copy)
            if (chunkAssemblyBuffer.size() >= expectedChunkTotalLength) {
                val fullPacket = chunkAssemblyBuffer.toByteArray()
                chunkAssemblyBuffer.reset()
                expectedChunkTotalLength = 0
                val chunk = StatusParser.parseChunk(fullPacket)
                if (chunk != null) {
                    _chunkFlow.tryEmit(chunk)
                }
            }
            return
        }

        // 2. Start of CHUNK (0xB1)
        if (copy[0] == BleConstants.OPCODE_CHUNK) {
            if (copy.size >= BleConstants.CHUNK_HEADER_LENGTH) {
                val len = (copy[10].toInt() and 0xFF) or ((copy[11].toInt() and 0xFF) shl 8)
                val expectedTotal = BleConstants.CHUNK_HEADER_LENGTH + len
                if (copy.size < expectedTotal) {
                    // Fragmented chunk across multiple BLE packets: begin accumulation
                    chunkAssemblyBuffer.reset()
                    chunkAssemblyBuffer.write(copy)
                    expectedChunkTotalLength = expectedTotal
                    return
                }
            }
            val chunk = StatusParser.parseChunk(copy)
            if (chunk != null) {
                _chunkFlow.tryEmit(chunk)
            }
            return
        }

        // 3. Strict packet size & state-gated opcodes
        when (copy[0]) {
            BleConstants.OPCODE_STREAM_SAMPLE -> {
                parseStreamSample(copy)?.let { _streamSamples.tryEmit(it) }
            }
            BleConstants.OPCODE_ACK_STREAM -> {
                if (copy.size >= 2) {
                    _streamAck.tryEmit(copy[1].toInt() and 0xFF)
                }
            }
            BleConstants.OPCODE_ACK_STATUS -> {
                if (copy.size == BleConstants.STATUS_PACKET_LENGTH ||
                    copy.size == BleConstants.STATUS_PACKET_LENGTH_V1
                ) {
                    val parsed = StatusParser.parse(copy)
                    if (parsed != null) {
                        _boardStatus.value = parsed
                    }
                }
            }
            BleConstants.OPCODE_ACK_SET_TIME -> {
                if (copy.size == BleConstants.ACK_SET_TIME_PACKET_LENGTH) {
                    val ack = StatusParser.parseSetTimeAck(copy)
                    if (ack != null) {
                        _lastSetTimeAck.tryEmit(ack)
                    }
                }
            }
            BleConstants.OPCODE_LIST_BEGIN -> {
                // LIST_BEGIN must be exactly 2 bytes [0xA0, total] AND only accepted when actively awaiting file list
                if (copy.size == 2 && isAwaitingFileList) {
                    val total = copy[1].toInt() and 0xFF
                    _listBeginFlow.tryEmit(total)
                }
            }
            BleConstants.OPCODE_LIST_ITEM -> {
                // LIST_ITEM must be exactly 26 bytes AND only accepted when actively awaiting file list
                if (copy.size == BleConstants.LIST_ITEM_PACKET_LENGTH && isAwaitingFileList) {
                    val item = StatusParser.parseListItem(copy)
                    if (item != null) {
                        _listItemFlow.tryEmit(item)
                    }
                }
            }
            BleConstants.OPCODE_LIST_END -> {
                // LIST_END must be exactly 2 bytes [0xA2, sent] AND only accepted when actively awaiting file list
                if (copy.size == 2 && isAwaitingFileList) {
                    isAwaitingFileList = false
                    val sent = copy[1].toInt() and 0xFF
                    _listEndFlow.tryEmit(sent)
                }
            }
            BleConstants.OPCODE_ACK_DELETE -> {
                if (copy.size == BleConstants.ACK_DELETE_PACKET_LENGTH) {
                    val result = StatusParser.parseDeleteAck(copy)
                    if (result != null) {
                        _deleteAckFlow.tryEmit(result)
                    }
                }
            }
            BleConstants.OPCODE_ACK_FORMAT -> {
                if (copy.size == BleConstants.ACK_FORMAT_PACKET_LENGTH) {
                    val result = StatusParser.parseFormatAck(copy)
                    if (result != null) {
                        _formatAckFlow.tryEmit(result)
                    }
                }
            }
            else -> {
                // Ignore unknown or unhandled bytes quietly
            }
        }
    }

    private fun enableTxNotifications(gatt: BluetoothGatt, deviceName: String, address: String) {
        if (isNotifyConfigured) return

        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID)
        if (nusService == null) {
            _connectionState.value = BleConnectionState.Error("Nordic UART Service (NUS) tidak ditemukan pada board")
            return
        }

        val txCharacteristic = nusService.getCharacteristic(BleConstants.NUS_TX_CHAR_UUID)
        if (txCharacteristic == null) {
            _connectionState.value = BleConnectionState.Error("Karakteristik NUS TX tidak ditemukan")
            return
        }

        // Enable local notifications in Android Bluetooth stack
        gatt.setCharacteristicNotification(txCharacteristic, true)

        // Write CCCD 0x0100 (ENABLE_NOTIFICATION_VALUE) to remote board
        val descriptor = txCharacteristic.getDescriptor(BleConstants.CCCD_DESCRIPTOR_UUID)
        if (descriptor != null) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                gatt.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
            } else {
                @Suppress("DEPRECATION")
                descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                @Suppress("DEPRECATION")
                gatt.writeDescriptor(descriptor)
            }
        } else {
            // If descriptor not found, update state directly
            isNotifyConfigured = true
            _connectionState.value = BleConnectionState.Connected(
                deviceName = deviceName,
                address = address,
                mtu = currentMtu,
                isNotifyEnabled = true
            )
            scope.launch {
                delay(300)
                sendGetStatus()
            }
        }
    }

    /**
     * Sends GET_STATUS (0x10, 1 byte total) to board on NUS RX characteristic.
     */
    fun sendStreamCommand(start: Boolean): Boolean {
        val payload = byteArrayOf(BleConstants.OPCODE_STREAM, if (start) 1 else 0)
        return writeNus(payload)
    }

    private fun writeNus(payload: ByteArray): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false
        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                gatt.writeCharacteristic(rxChar, payload, writeType) == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = payload
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    private fun parseStreamSample(bytes: ByteArray): StreamSample? {
        if (bytes.size < BleConstants.STREAM_SAMPLE_PACKET_LENGTH) return null
        if (bytes[0] != BleConstants.OPCODE_STREAM_SAMPLE) return null
        val seq = (bytes[1].toInt() and 0xFF) or ((bytes[2].toInt() and 0xFF) shl 8)
        fun u16(i: Int): Int =
            (bytes[i].toInt() and 0xFF) or ((bytes[i + 1].toInt() and 0xFF) shl 8)
        fun i16(i: Int): Int = u16(i).toShort().toInt()
        fun u32(i: Int): Long =
            (bytes[i].toLong() and 0xFF) or
                ((bytes[i + 1].toLong() and 0xFF) shl 8) or
                ((bytes[i + 2].toLong() and 0xFF) shl 16) or
                ((bytes[i + 3].toLong() and 0xFF) shl 24)
        // Byte 3..: SampleRec = t_rel_ms u32 + 11×int16
        val tRel = u32(3)
        val ch = IntArray(BleConstants.PLG1_CHANNELS_V4) { i -> i16(7 + i * 2) }
        return StreamSample(seq = seq, tRelMs = tRel, channels = ch)
    }

    fun sendGetStatus(): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false

        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, BleConstants.CMD_GET_STATUS, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = BleConstants.CMD_GET_STATUS
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Timing Precision: Sends SET_TIME (0x11, 9 bytes total: 0x11 + uint64 LE unix_ms) to board on NUS RX.
     */
    fun sendSetTime(unixMs: Long): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false
        val command = BleConstants.buildSetTimeCommand(unixMs)

        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, command, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = command
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Phase C: Sends LIST command (0x20, 1 byte) to board on NUS RX.
     */
    fun sendListCommand(): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false

        isAwaitingFileList = true
        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        val sent = try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, BleConstants.CMD_LIST, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = BleConstants.CMD_LIST
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }

        if (!sent) {
            isAwaitingFileList = false
        }
        return sent
    }

    /**
     * Phase C: Sends GET_FILE pull chunk command (0x21, 19 bytes) to board on NUS RX.
     */
    fun sendGetFileChunk(name12: String, offset: Long, maxChunk: Int = BleConstants.DEFAULT_MAX_CHUNK): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false

        // During file chunk pull, we are downloading data and NOT expecting LIST packets
        isAwaitingFileList = false
        expectedChunkTotalLength = 0
        chunkAssemblyBuffer.reset()

        val effectiveMaxChunk = minOf(maxChunk, maxOf(16, currentMtu - 15))
        val command = BleConstants.buildGetFileCommand(name12, offset, effectiveMaxChunk)

        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, command, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = command
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    fun setAwaitingFileList(awaiting: Boolean) {
        isAwaitingFileList = awaiting
    }

    /**
     * Phase D: Sends DELETE_FILE command (0x23, 13 bytes: 0x23 + name[12] ASCII) to board on NUS RX.
     */
    fun sendDeleteFile(name12: String): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false
        val command = BleConstants.buildDeleteFileCommand(name12)

        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, command, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = command
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Phase D: Sends FORMAT_FLASH command (0x24, 2 bytes: [0x24, 0xA5]) to board on NUS RX.
     */
    fun sendFormatFlash(): Boolean {
        val gatt = activeGatt ?: return false
        val nusService = gatt.getService(BleConstants.NUS_SERVICE_UUID) ?: return false
        val rxChar = nusService.getCharacteristic(BleConstants.NUS_RX_CHAR_UUID) ?: return false
        val command = BleConstants.CMD_FORMAT

        val writeType = if ((rxChar.properties and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE) != 0) {
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        } else {
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        }

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                val statusCode = gatt.writeCharacteristic(rxChar, command, writeType)
                statusCode == BluetoothGatt.GATT_SUCCESS
            } else {
                @Suppress("DEPRECATION")
                rxChar.value = command
                rxChar.writeType = writeType
                @Suppress("DEPRECATION")
                gatt.writeCharacteristic(rxChar)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Starts an unfiltered BLE scan. Android's name filter is exact, so PalmLog1
     * would be dropped by a filter of "PalmLog". Prefix matching happens in [scanCallback].
     */
    fun startScan(): Boolean {
        val adapter = bluetoothAdapter
        if (adapter == null || !adapter.isEnabled) {
            _connectionState.value = BleConnectionState.Error("Bluetooth mati atau tidak tersedia")
            return false
        }
        val leScanner = scanner
        if (leScanner == null) {
            _connectionState.value = BleConnectionState.Error("Pemindai BLE tidak tersedia")
            return false
        }

        if (isScanningInternal) return true

        _discoveredDevices.value = emptyList()
        _connectionState.value = BleConnectionState.Scanning
        isScanningInternal = true

        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .setReportDelay(0)
            .build()

        try {
            leScanner.startScan(emptyList(), settings, scanCallback)
        } catch (e: Exception) {
            isScanningInternal = false
            _connectionState.value = BleConnectionState.Error("Gagal memulai pemindaian: ${e.message}")
            return false
        }
        return true
    }

    /**
     * Stops active BLE scan.
     */
    fun stopScan() {
        if (!isScanningInternal) return
        isScanningInternal = false
        try {
            scanner?.stopScan(scanCallback)
        } catch (e: Exception) {
            e.printStackTrace()
        }
        if (_connectionState.value is BleConnectionState.Scanning) {
            _connectionState.value = BleConnectionState.Disconnected
        }
    }

    /**
     * Connects to a device by MAC address.
     */
    fun connectAddress(address: String) {
        stopScan()
        disconnect()

        val adapter = bluetoothAdapter ?: return
        val device = try {
            adapter.getRemoteDevice(address)
        } catch (e: Exception) {
            _connectionState.value = BleConnectionState.Error("Alamat BLE tidak valid: $address")
            return
        }

        val name = device.name ?: BleConstants.TARGET_DEVICE_NAME
        _connectionState.value = BleConnectionState.Connecting(name, address)
        activeGatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
    }

    /**
     * Disconnects and releases active GATT connection.
     */
    fun disconnect() {
        try {
            activeGatt?.disconnect()
            activeGatt?.close()
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            activeGatt = null
            isNotifyConfigured = false
            isAwaitingFileList = false
            expectedChunkTotalLength = 0
            chunkAssemblyBuffer.reset()
            currentMtu = 23
            _connectionState.value = BleConnectionState.Disconnected
        }
    }

    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true
}
