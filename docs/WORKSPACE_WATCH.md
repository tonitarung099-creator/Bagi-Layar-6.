# Pantau Workspace Terus-menerus

Fitur **Pantau workspace terus-menerus** menjaga slot workspace tetap pulih walaupun aplikasi dibuka jauh setelah Windows selesai login.

## Bedanya dengan Auto-Restore saat mulai

- **Pulihkan workspace otomatis saat mulai** bekerja sebagai pemulihan awal. Ia mulai beberapa detik setelah Bagi Layar hidup dan melakukan retry terbatas sampai aplikasi lain selesai terbuka.
- **Pantau workspace terus-menerus** berjalan selama Bagi Layar aktif. Ia hanya memeriksa slot yang kosong atau assignment yang jendelanya sudah mati.

Keduanya boleh aktif bersamaan. Saat auto-restore startup sedang bekerja, watcher menunggu agar dua controller tidak menggeser desktop pada waktu yang sama.

## Perilaku aman

Watcher tidak menjalankan restore penuh berulang-ulang. Setiap siklus:

1. Membaca workspace aktif.
2. Menghapus assignment yang handle jendelanya sudah tidak valid.
3. Mengabaikan monitor yang sedang offline.
4. Membiarkan slot yang masih berisi jendela valid tetap seperti sekarang.
5. Mencari hanya jendela untuk slot yang kosong.
6. Memakai identitas process, class window, dan kemiripan judul untuk mencari jendela yang benar.
7. Memindahkan kandidat hanya jika pencocokannya cukup meyakinkan.

Jendela seperti **Runner 01**, **Runner 02**, dan seterusnya dilindungi agar nomor Runner yang berbeda tidak dianggap sebagai jendela yang sama.

## Cara mengaktifkan

Klik kanan ikon **Bagi Layar** di system tray, lalu centang:

**Pantau workspace terus-menerus**

Preferensi disimpan di `config/settings.ini`, sehingga ikut bersama folder portable.

## Contoh

Workspace menyimpan enam Chrome Runner pada Slot 1–6. Runner 04 ditutup pada pukul 10:00 dan baru dibuka lagi pada pukul 11:00.

Dengan watcher aktif, Bagi Layar tidak menggeser Runner 01, 02, 03, 05, atau 06. Ketika Runner 04 muncul kembali dan identitasnya cocok, hanya Runner 04 yang dikembalikan ke Slot 4.
