# UI Spec — Bagi Layar

Acuan: screenshot pengguna 29 September 2026 (1672×941). Angka di bawah mengikuti pengukuran Astra pada plan audit dan dipakai sebagai contract implementasi, bukan sebagai alasan untuk mengganti UI dengan screenshot statis.

## Komposisi

- Ukuran acuan aplikasi sekitar 1566×914.
- Header: 72 px.
- Sidebar: target 285 px, boleh menyusut sampai 235 px pada layar kecil.
- Panel utama: preview di tengah + pengaturan kanan; jarak panel 10–15 px.
- Pengaturan kanan: target sekitar 335 px, minimum 285 px dan scroll vertikal bila tinggi terbatas.
- Aksi cepat: satu baris empat tombol, tinggi sekitar 90–106 px.
- Status bar: sekitar 34–40 px.

## Responsif

- Target: 1566×914 dan 1600×920 mengikuti komposisi acuan.
- 1366×768 dan 1280×720 tidak boleh memiliki overlap; monitor strip dan preset layout memakai horizontal scroll.
- Daftar jendela tetap scrollable.
- Preview monitor boleh mengecil proporsional dan mempertahankan rasio monitor aktif.
- Ukuran awal dibatasi work area monitor primer; minimum aplikasi 1080×650 agar laptop tetap dapat mengakses semua fungsi.

## Warna dan tipografi

- Font utama Windows: Segoe UI Variable Text / Segoe UI.
- Aksen utama: `#0B73FF`.
- Selected background: biru muda (`#EAF3FF` / `#DCEAFF`).
- Surface: putih hingga putih kebiruan.
- Border: abu-biru tipis.
- Radius panel: 12–16 px.
- Judul aplikasi: sekitar 20 px; section 15–18 px; label 12–14 px; subtitle 10–13 px.

## Header

- Logo vektor biru-putih di kiri.
- Judul `Bagi Layar` + subjudul `Atur jendela, maksimalkan produktivitas.`.
- Tombol gear berada di kanan dan memfokuskan panel pengaturan.
- Native window chrome tetap dipertahankan agar resize, snap, system menu, dan perilaku Windows tidak hilang.

## Sidebar

- Tiga nav item eksklusif: Workspace, Daftar Jendela, Aksi Cepat.
- Klik nav tidak membuat halaman baru; masing-masing memindahkan keyboard focus ke area terkait.
- Workspace menyediakan `+` dan menu `…`.
- Daftar jendela mendukung multi-select, drag, double-click, dan scroll.
- Aksi tambahan `Lepas slot` dan `Reset monitor` diletakkan ringkas di bawah daftar.

## Monitor preview

- Bezel gelap realistis + kaki monitor.
- Wallpaper vektor lipatan biru bergaya Windows 11.
- Badge nomor slot besar.
- Hover/drop/click menggunakan geometri cell yang sama.
- Rasio preview mengikuti monitor aktif.

## Monitor tabs

- Tab dinamis sesuai jumlah monitor nyata.
- Ikon monitor berasal dari `QStyle`, bukan glyph hardcode Chrome.
- Baris 1: `Monitor N`; baris 2: resolusi dan penanda `Utama` bila relevan.
- Tombol `Tambah / Monitor Lain` memakai border dashed dan membuka Display Settings Windows.

## Pengaturan kanan

- Resolusi: read-only/deteksi.
- Margin luar: slider + nilai px.
- Jarak antar jendela: slider + nilai px.
- Area taskbar: otomatis atau seluruh layar.
- Kunci layout: ToggleSwitch dengan thumb putih; keyboard Space bekerja.
- Background enforcement tidak boleh membatalkan minimize/maximize pengguna.

## Preset layout

- Preset: 2, 3, 4, 6, 8, 9, Kustom.
- Default: 6.
- Kustom bersifat transactional: pembatalan input baris/kolom mengembalikan highlight lama.
- Pada lebar kecil, preset diakses melalui horizontal scroll.

## Aksi cepat

Empat tombol semantik/focusable:

1. Susun Jendela — primary biru.
2. Pulihkan Layout.
3. Simpan Workspace.
4. Pindahkan ke Slot.

Semua mendukung mouse, Enter, dan Space. Feedback menampilkan jumlah berhasil/gagal bila operasi batch.

## Status bar

- Kiri: jumlah monitor + ringkasan `Monitor N WxH` dengan monitor aktif diberi marker penuh.
- Kanan: `Siap digunakan ⓘ`.
- Detail tray/hotkey/zona/auto-start/auto-restore/watcher dipindahkan ke tooltip agar status bar tidak memanjang seperti versi audit.

## Contract perilaku yang terkait UI

- Satu HWND hanya boleh memiliki satu live assignment global.
- `locked_rects` selalu diturunkan dari assignment + profile monitor tersambung yang lock-nya aktif.
- Saved slot intent tidak hilang hanya karena jendela atau monitor sedang offline.
- Release/reset yang disengaja disuppress dari watcher sampai user save/restore/workspace switch.
- Identitas monitor tidak memakai resolusi/koordinat sebagai primary key.
- Engine placement Windows memakai native monitor rectangles; overlay dikonversi per monitor ke ruang Qt.
