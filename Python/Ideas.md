# Ide Pengembangan GUI - Simple_GUI.py

Daftar ide tambahan untuk dikerjakan ke depan.

---

## 1. Label nilai saat ini (Live Value)
Di samping atau di bawah tiap plot, tampilkan nilai terbaru AI0 dan AI1 sebagai angka float real-time.
- Bisa menggunakan `QLabel` yang di-update setiap `_refresh_plot()`

## 2. Y-axis range: Auto / Manual
- Tambah checkbox "Auto Range" agar sumbu Y menyesuaikan data secara otomatis
- Atau input `Y Min` / `Y Max` untuk mengunci rentang manual
- Saat running, user bisa switch tanpa stop

## 3. Plot Window Size (detik tampil)
- Input field "Tampilkan N detik terakhir" yang bisa diubah bahkan saat running
- Saat diubah, `maxlen` rolling buffer menyesuaikan

## 4. Log Panel
- Tambah `QTextEdit` (read-only) kecil di bawah parameter sebagai log internal
- Menampilkan pesan error, peringatan fallback mode B, dan info status
- Pengganti `stderr` terminal agar informasi tampil di GUI

## 5. Warna Channel Configurable
- Beri tombol color-picker kecil di sebelah label "AI 0" dan "AI 1"
- Default: AI0 = biru (30,144,255), AI1 = oranye (220,80,0)

## 6. Export CSV
- Tombol "Save CSV" untuk menyimpan isi rolling buffer (atau semua data sejak Start) ke file `.csv`
- Format: `timestamp, ai0, ai1`
- Gunakan `QFileDialog` untuk memilih lokasi simpan

## 7. Status Bar: Sample Rate Aktual
- Hitung sample rate aktual dari waktu antar chunk yang diterima
- Tampilkan di status bar untuk memverifikasi perangkat berjalan sesuai setting

## 8. Pause Plot (tanpa Stop DAQ)
- Tombol "Pause Plot" yang menghentikan refresh chart tanpa menghentikan akuisisi
- Buffer tetap terisi; saat "Resume" langsung update ke data terbaru

## 9. Multiple Device Support
- Opsi menambah/mengurangi channel secara dinamis (bukan hanya 2 channel hardcoded)
- Setiap channel otomatis membuat plot baru

## 10. Trigger / Threshold Marker
- Tambah garis horizontal di plot sebagai batas threshold
- Ketika nilai melampaui threshold, berikan highlight atau notifikasi sederhana
