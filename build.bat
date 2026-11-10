@echo off
echo [1/3] Installing packages...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error
echo [2/3] Building app...
python make_icon.py
if errorlevel 1 goto error
python -m PyInstaller --noconfirm --windowed --onedir --icon assets\icon.ico --add-data "assets;assets" --name ImageRatioTool app.py
if errorlevel 1 goto error
echo [3/3] Building installer...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
  %ISCC% installer.iss
  if errorlevel 1 goto error
  echo Done! Installer: installer_output\ImageRatioTool-Setup.exe
) else (
  echo Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php and run this file again.
  echo The app itself is ready: dist\ImageRatioTool\ImageRatioTool.exe
)
pause
exit /b 0
:error
echo Build failed. Check that Python is installed and added to PATH.
pause
exit /b 1
