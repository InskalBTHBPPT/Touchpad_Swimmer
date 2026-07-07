@echo off
REM Build onefile executable — Swimmer Force Motion Monitoring v2.3.0
setlocal
cd /d "%~dp0"

echo === Memeriksa dependensi build ===
python -c "import PyInstaller" 2>nul || (
    echo PyInstaller belum terpasang. Jalankan: pip install pyinstaller
    exit /b 1
)

if not exist "image\logo_brin.png" (
    echo ERROR: image\logo_brin.png tidak ditemukan.
    exit /b 1
)
if not exist "image\logo_unnes.png" (
    echo ERROR: image\logo_unnes.png tidak ditemukan.
    exit /b 1
)

if not exist "UserManual_Force_Motion_v2.3.0-e.pdf" (
    echo Manual PDF -e belum ada. Menyiapkan...
    if exist "UserManual_Force_Motion_v2.3.0.pdf" (
        copy /Y "UserManual_Force_Motion_v2.3.0.pdf" "UserManual_Force_Motion_v2.3.0-e.pdf" >nul
    ) else (
        python "..\md_to_pdf_Force_Motion.py" -i UserManual_Force_Motion_v2.3.0.md -o UserManual_Force_Motion_v2.3.0-e.pdf
        if errorlevel 1 exit /b 1
    )
)

echo === PyInstaller onefile ===
pyinstaller --noconfirm --clean Swimmer_Force_Motion_Monitoring_v2.3.0.spec

if errorlevel 1 (
    echo Build GAGAL.
    exit /b 1
)

echo.
echo OK: dist\Swimmer_Force_Motion_Monitoring_v2.3.0.exe
copy /Y UserManual_Force_Motion_v2.3.0-e.pdf dist\ >nul
echo Manual PDF disalin ke dist\ untuk distribusi ke end user.
endlocal
