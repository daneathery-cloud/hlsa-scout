@echo off
cd /d "%~dp0"
call venv\Scripts\activate
pyinstaller --noconfirm --windowed --onefile --name HLSAScout ^
  --add-data "assets\hlsa_logo.png;assets" ^
  --add-data "README.html;." ^
  main.py
copy /y dist\HLSAScout.exe HLSAScout.exe >nul
echo.
echo Build complete: HLSAScout.exe
