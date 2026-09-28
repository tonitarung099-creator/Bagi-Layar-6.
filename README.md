# Bagi Layar 6

Aplikasi Windows untuk membagi dan menyusun jendela ke beberapa slot pada satu atau banyak monitor. UI mengikuti mockup Bagi Layar yang sudah disetujui; spesifikasinya disimpan di `docs/UI_SPEC.md`.

## Fitur saat ini

- Deteksi monitor Windows otomatis: Monitor 1, 2, 3, dan seterusnya.
- Preset layout 2, 3, 4, 6, 8, dan 9 jendela.
- Layout kustom baris × kolom.
- Margin luar dan jarak antar jendela.
- Pilihan menghormati area taskbar atau memakai seluruh layar.
- Deteksi jendela aktif menggunakan Win32 API.
- Susun jendela otomatis ke monitor aktif.
- Pindahkan satu jendela ke slot tertentu.
- Simpan dan pulihkan workspace.
- UI Bahasa Indonesia.
- Workflow GitHub Actions untuk build portable Windows.

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

UI dapat dibuka di OS lain untuk pengembangan, tetapi fungsi memindahkan/resize jendela memakai Win32 API dan hanya aktif di Windows.
