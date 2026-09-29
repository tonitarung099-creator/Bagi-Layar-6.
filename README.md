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
- Double-click jendela untuk memasukkannya ke slot kosong pertama.
- Multi-select lalu klik slot untuk mengisi beberapa slot secara berurutan.
- Klik slot terisi untuk memilih jendela yang menempatinya.
- Lepas assignment slot dan reset slot tanpa menutup jendela.
- Hotkey global `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif langsung ke slot.
- Kunci layout agar posisi jendela otomatis dipulihkan ketika berubah.
- Simpan dan pulihkan banyak workspace.
- UI Bahasa Indonesia.
- Workflow GitHub Actions: validasi source/UI, tes engine layout, lalu build portable Windows.

## Cara pakai cepat

1. Buka aplikasi yang ingin disusun, lalu buka **Bagi Layar**.
2. Pilih monitor dan preset, misalnya **6 Jendela**.
3. Pilih jendela di daftar kiri lalu:
   - tekan **Susun Jendela** untuk menyusun semuanya; atau
   - tarik satu jendela langsung ke Slot 1–6 pada preview; atau
   - double-click jendela untuk memasukkannya ke slot kosong pertama.
4. Saat sedang bekerja di aplikasi lain, tekan `Ctrl+Alt+1` sampai `Ctrl+Alt+9` untuk memindahkan jendela aktif ke slot terkait.
5. Tekan **Simpan Workspace** jika susunan ingin digunakan lagi.

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

UI dapat dibuka di OS lain untuk pengembangan, tetapi fungsi memindahkan/resize jendela dan hotkey global memakai Win32 API dan hanya aktif di Windows.
