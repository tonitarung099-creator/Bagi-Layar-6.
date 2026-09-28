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
  echo.
  echo Build selesai: dist\Bagi-Layar\Bagi-Layar.exe
)
