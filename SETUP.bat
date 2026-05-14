@echo off
echo ============================================
echo   Anime Screenshot Tool v4 - Setup
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Download from https://python.org
    echo Tick "Add Python to PATH" during install!
    pause
    exit /b
)

echo Installing libraries...
echo (torch + tensorflow are large - may take several minutes)
echo.
pip install opencv-python numpy Pillow imagehash torch torchvision tensorflow
echo.

if not exist "references"  mkdir references
if not exist "videos"      mkdir videos
if not exist "screenshots" mkdir screenshots

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo HOW TO USE:
echo.
echo   CHARACTER ON DANBOORU (recommended):
echo     1. Find tag at https://danbooru.donmai.us
echo     2. Open anime_screenshotter.py in Notepad
echo     3. Set CHARACTER_TAG = "the_tag"
echo.
echo   CHARACTER NOT ON DANBOORU:
echo     1. Take 5-10 clear face screenshots from the anime
echo     2. Put them in the "references" folder
echo     3. Leave CHARACTER_TAG = "" in the script
echo.
echo   FOR BEST ACCURACY - do BOTH above at once!
echo.
echo   Then put episodes in "videos" and run RUN.bat
echo.
pause
