@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
rmdir /s /q dist 2>nul
pyinstaller --noconfirm --clean --windowed --name "Bagi-Layar" main.py
if exist "dist\Bagi-Layar" (
  if not exist "dist\Bagi-Layar\config" mkdir "dist\Bagi-Layar\config"
  >"dist\Bagi-Layar\config\README.txt" echo Folder konfigurasi portable Bagi Layar.
  >>"dist\Bagi-Layar\config\README.txt" echo workspace.json dan settings.ini akan dibuat otomatis di folder ini.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$zip='dist\Bagi-Layar-Windows-Portable.zip'; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path 'dist\Bagi-Layar\*' -DestinationPath $zip -CompressionLevel Optimal"
  echo.
  echo Build selesai: dist\Bagi-Layar\Bagi-Layar.exe
  echo Config portable: dist\Bagi-Layar\config\
  echo ZIP portable: dist\Bagi-Layar-Windows-Portable.zip
) else (
  echo Build gagal: folder dist\Bagi-Layar tidak ditemukan.
  exit /b 1
)
