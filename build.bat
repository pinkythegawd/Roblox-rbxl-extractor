@echo off
echo Building Roblox Extractor...

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Build with PyInstaller
pyinstaller --clean ^
    --onefile ^
    --noconsole ^
    --name "RobloxExtractor" ^
    --icon "resources\icon.ico" ^
    --add-data "resources;resources" ^
    "src\main.py"

echo Build complete! Check the dist folder for RobloxExtractor.exe