# Bagi Layar 6

Aplikasi Windows untuk membagi dan menyusun jendela ke beberapa slot pada satu atau banyak monitor. UI mengikuti mockup Bagi Layar yang sudah disetujui; spesifikasinya disimpan di `docs/UI_SPEC.md`.

## Fitur saat ini

- Deteksi monitor Windows otomatis: Monitor 1, 2, 3, dan seterusnya.
- Preset layout 2, 3, 4, 6, 8, dan 9 jendela.
- Layout kustom baris × kolom.
- Margin luar dan jarak antar jendela.
- Pilihan menghormati area taskbar atau memakai seluruh layar.
- Deteksi jendela aktif menggunakan Win32 API.
- Susun beberapa jendela sekaligus ke monitor aktif.
- Drag-and-drop jendela dari daftar langsung ke slot monitor.
- Overlay zona otomatis seperti FancyZones saat jendela benar-benar sedang digeser.
- Lepaskan jendela di atas zona untuk snap langsung ke slot terkait.
- Overlay mengikuti Monitor 1, 2, 3, dan seterusnya berdasarkan posisi pointer.
- Overlay bersifat click-through dan tidak mengambil fokus dari jendela yang sedang digeser.
- Double-click jendela untuk memasukkannya ke slot kosong pertama.
- Multi-select lalu klik slot untuk mengisi beberapa slot secara berurutan.
- Klik slot terisi untuk memilih jendela yang menempatinya.
- Lepas assignment slot dan reset slot tanpa menutup jendela.
- Hotkey global `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif langsung ke slot.
- Kunci layout agar posisi jendela otomatis dipulihkan ketika berubah.
- Saat drag manual berlangsung, kunci layout dijeda sementara agar tidak melawan gerakan pengguna.
- Simpan dan pulihkan banyak workspace.
- UI Bahasa Indonesia.
- Workflow GitHub Actions: validasi source/UI/overlay, tes engine layout, lalu build portable Windows.

## Cara pakai cepat

1. Buka aplikasi yang ingin disusun, lalu buka **Bagi Layar**.
2. Pilih preset, misalnya **6 Jendela**.
3. Untuk cara paling cepat, seret jendela biasa melalui title bar. Ketika jendela mulai berpindah, zona layout akan muncul otomatis pada monitor di bawah pointer.
4. Arahkan jendela ke zona yang diinginkan lalu lepaskan mouse. Jendela langsung masuk ke slot tersebut.
5. Alternatif lain:
   - tekan **Susun Jendela** untuk menyusun beberapa jendela terpilih sekaligus;
   - tarik jendela dari daftar kiri langsung ke slot pada preview;
   - double-click jendela untuk memasukkannya ke slot kosong pertama;
   - tekan `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif langsung ke slot terkait.
6. Tekan **Simpan Workspace** jika susunan ingin digunakan lagi.

Hotkey yang slotnya tidak tersedia pada layout aktif akan diabaikan dan statusnya ditampilkan di bagian bawah aplikasi.

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

UI dapat dibuka di OS lain untuk pengembangan, tetapi fungsi memindahkan/resize jendela, overlay zona otomatis, dan hotkey global memakai Win32 API dan hanya aktif di Windows.
