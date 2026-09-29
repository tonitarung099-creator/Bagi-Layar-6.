# Bagi Layar 6

Aplikasi Windows untuk membagi dan menyusun jendela ke beberapa slot pada satu atau banyak monitor. UI mengikuti mockup Bagi Layar yang sudah disetujui; spesifikasinya disimpan di `docs/UI_SPEC.md`.

## Fitur saat ini

- Deteksi monitor Windows otomatis: Monitor 1, 2, 3, dan seterusnya.
- Setiap monitor memiliki profile layout independen.
- Contoh: Monitor 1 = 6 slot, Monitor 2 = 4 slot, Monitor 3 = 2 slot.
- Layout, margin, gap, area taskbar, dan Kunci Layout disimpan terpisah untuk masing-masing monitor.
- Tab monitor menampilkan jumlah slot aktif agar konfigurasi mudah dibedakan.
- Preset layout 2, 3, 4, 6, 8, dan 9 jendela.
- Layout kustom baris × kolom.
- Identitas monitor disimpan menggunakan informasi layar, sehingga profile tidak hanya bergantung pada urutan tab.
- Workspace lama tetap kompatibel dan otomatis diperlakukan sebagai konfigurasi monitor aktif saat disimpan ulang.
- Workspace baru menyimpan konfigurasi dan assignment jendela untuk semua monitor sekaligus.
- Margin luar dan jarak antar jendela.
- Pilihan menghormati area taskbar atau memakai seluruh layar.
- Deteksi jendela aktif menggunakan Win32 API.
- Susun beberapa jendela sekaligus ke monitor aktif.
- Drag-and-drop jendela dari daftar langsung ke slot monitor.
- Overlay zona otomatis seperti FancyZones saat jendela benar-benar sedang digeser.
- Lepaskan jendela di atas zona untuk snap langsung ke slot terkait.
- Overlay membaca layout monitor yang sedang berada di bawah pointer, bukan sekadar layout monitor aktif di UI.
- Overlay mengikuti Monitor 1, 2, 3, dan seterusnya berdasarkan posisi pointer.
- Overlay bersifat click-through dan tidak mengambil fokus dari jendela yang sedang digeser.
- Double-click jendela untuk memasukkannya ke slot kosong pertama.
- Multi-select lalu klik slot untuk mengisi beberapa slot secara berurutan.
- Klik slot terisi untuk memilih jendela yang menempatinya.
- Lepas assignment slot tanpa menutup jendela.
- Hotkey global `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif langsung ke slot pada monitor yang sedang dipilih di Bagi Layar.
- Hotkey global dapat dimatikan/diaktifkan saat runtime dari system tray.
- **Target Monitor Hotkey** dapat dipilih langsung dari menu tray tanpa membuka UI utama.
- Kunci layout bekerja lintas monitor; monitor yang Kunci Layout-nya nonaktif tidak dipaksa kembali.
- Saat drag manual berlangsung, kunci layout dijeda sementara agar tidak melawan gerakan pengguna.
- Mode system tray: minimize atau klik X menyembunyikan UI, tetapi engine zona/hotkey tetap aktif.
- Menu tray menyediakan **Buka Bagi Layar**, **Workspace Cepat**, **Target Monitor Hotkey**, toggle **Zona Drag**, toggle **Hotkey Ctrl+Alt+1…9**, **Mulai bersama Windows**, dan **Keluar Bagi Layar**.
- **Workspace Cepat** dapat memulihkan workspace tersimpan langsung dari tray.
- Opsi **Mulai bersama Windows** memakai startup per-user, tidak membutuhkan administrator atau installer.
- Saat auto-start, Bagi Layar langsung masuk tray menggunakan argumen `--tray` sehingga jendela utama tidak mengganggu saat login Windows.
- Single-instance: Bagi Layar mencegah dua engine/tray/hotkey berjalan bersamaan.
- Jika EXE dibuka lagi saat aplikasi sudah aktif, instance lama dibawa ke depan; auto-start `--tray` kedua keluar diam-diam.
- Preferensi toggle zona/hotkey diingat menggunakan pengaturan aplikasi.
- Simpan dan pulihkan banyak workspace.
- UI Bahasa Indonesia.
- Workflow GitHub Actions: validasi source/UI/overlay/multi-monitor/system-tray/auto-start/single-instance, tes engine layout, lalu build portable Windows.

## Cara pakai multi-monitor

Contoh konfigurasi:

- **Monitor 1** → pilih `6 Jendela`, margin 16 px, gap 12 px.
- **Monitor 2** → klik tab Monitor 2 lalu pilih `4 Jendela`, margin 10 px, gap 8 px.
- **Monitor 3** → klik tab Monitor 3 lalu pilih `2 Jendela`.

Saat berpindah tab monitor, pengaturan monitor sebelumnya tetap tersimpan di memori workspace. Tekan **Simpan Workspace** untuk menyimpan seluruh konfigurasi monitor dan assignment jendela secara permanen.

Saat **Pulihkan Workspace** ditekan, Bagi Layar mencoba mengembalikan jendela ke monitor dan slot masing-masing. Workspace format lama tetap dibaca dan dimigrasikan sebagai konfigurasi monitor aktif.

## Mode system tray

Pada Windows yang memiliki system tray:

1. Klik tombol **X** atau minimize jendela utama.
2. Bagi Layar disembunyikan ke tray, bukan dimatikan.
3. Zona drag, Kunci Layout, dan hotkey tetap dapat bekerja di background.
4. Klik/double-click ikon **Bagi Layar** di tray untuk membuka UI lagi.
5. Klik kanan ikon tray untuk:
   - membuka Bagi Layar;
   - memilih dan memulihkan **Workspace Cepat**;
   - memilih **Target Monitor Hotkey**;
   - mengaktifkan/nonaktifkan **Zona Drag**;
   - mengaktifkan/nonaktifkan **Hotkey Ctrl+Alt+1…9**;
   - mengaktifkan/nonaktifkan **Mulai bersama Windows**;
   - benar-benar keluar melalui **Keluar Bagi Layar**.

Jika system tray tidak tersedia, perilaku close kembali normal dan aplikasi tidak memaksa berjalan di background.

## Single-instance

Bagi Layar hanya menjalankan satu engine per akun pengguna. Hal ini mencegah dua ikon tray, dua overlay, dua Kunci Layout, atau benturan registrasi hotkey.

Jika `Bagi-Layar.exe` dijalankan lagi secara manual saat aplikasi sudah aktif, proses baru mengirim perintah ke instance lama untuk membuka jendela utama lalu langsung keluar. Jika pemanggilan kedua berasal dari auto-start `--tray`, proses kedua cukup keluar tanpa memunculkan UI.

## Mulai bersama Windows

Aktifkan **Mulai bersama Windows** dari menu klik kanan ikon tray. Bagi Layar menambahkan entri startup hanya untuk akun Windows saat ini (`HKCU`), sehingga tidak membutuhkan hak administrator.

Karena aplikasi bersifat portable, auto-start menunjuk ke lokasi `Bagi-Layar.exe` saat opsi tersebut diaktifkan. Jika folder portable dipindahkan, nonaktifkan lalu aktifkan lagi **Mulai bersama Windows** agar lokasi startup diperbarui.

Saat Windows login, aplikasi dipanggil dengan `--tray`: UI utama tidak langsung dibuka, tetapi engine multi-monitor, zona drag, hotkey, dan Kunci Layout dapat tetap berjalan di background.

## Cara pakai cepat

1. Buka aplikasi yang ingin disusun, lalu buka **Bagi Layar**.
2. Pilih monitor dan preset yang diinginkan.
3. Untuk cara paling cepat, seret jendela biasa melalui title bar. Ketika jendela mulai berpindah, zona layout akan muncul otomatis pada monitor di bawah pointer.
4. Arahkan jendela ke zona yang diinginkan lalu lepaskan mouse. Jendela langsung masuk ke slot tersebut.
5. Alternatif lain:
   - tekan **Susun Jendela** untuk menyusun beberapa jendela terpilih sekaligus;
   - tarik jendela dari daftar kiri langsung ke slot pada preview;
   - double-click jendela untuk memasukkannya ke slot kosong pertama;
   - tekan `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif langsung ke slot terkait pada monitor aktif;
   - saat UI berada di tray, pilih **Target Monitor Hotkey** untuk mengganti monitor tujuan;
   - pilih **Workspace Cepat** untuk memulihkan susunan tanpa membuka UI utama.
6. Tekan **Simpan Workspace** jika seluruh susunan multi-monitor ingin digunakan lagi.

Hotkey yang slotnya tidak tersedia pada layout monitor aktif akan diabaikan dan statusnya ditampilkan di bagian bawah aplikasi.

## Menjalankan dari source

Windows 10/11 + Python 3.11 atau lebih baru:

```bat
run.bat
```

## Build portable folder

```bat
build_portable.bat
```

Hasil build berada di `dist\Bagi-Layar\`. Folder tersebut dapat dipindah dan dijalankan tanpa installer.

## Catatan

UI dapat dibuka di OS lain untuk pengembangan, tetapi fungsi memindahkan/resize jendela, overlay zona otomatis, hotkey global, system tray, auto-start, dan integrasi Windows ditujukan untuk Windows.
