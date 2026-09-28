# Bagi Layar 6

Aplikasi Windows untuk membagi dan menyusun jendela ke beberapa slot pada satu atau banyak monitor. UI dibuat mengikuti mockup `docs/reference/ui-bagi-layar.png`.

## Fitur saat ini

- Deteksi monitor Windows secara otomatis (Monitor 1, 2, 3, dan seterusnya).
- Preset layout 2, 3, 4, 6, 8, dan 9 jendela.
- Layout kustom baris × kolom.
- Margin luar dan jarak antar jendela.
- Otomatis menghormati area taskbar atau memakai seluruh layar.
- Deteksi jendela aktif.
- Susun jendela otomatis ke monitor aktif.
- Pindahkan satu jendela ke slot tertentu.
- Simpan dan pulihkan workspace.
- UI Bahasa Indonesia.

## Menjalankan dari source

Windows 10/11 + Python 3.11 atau lebih baru:

```bat
run.bat
```

Atau manual:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build portable folder

```bat
build_portable.bat
```

Hasilnya berada di `dist\Bagi-Layar\`. Folder tersebut dapat dipindah ke komputer Windows lain dan dijalankan tanpa instalasi Python.

## Catatan

Aplikasi dapat dibuka di OS lain untuk pengembangan UI, tetapi fungsi memindahkan/resize jendela memakai Win32 API dan hanya aktif di Windows.
