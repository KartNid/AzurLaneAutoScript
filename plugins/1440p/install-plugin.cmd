@echo off
setlocal
set "ALAS_PLUGIN_ROOT=%~1"
if defined ALAS_PLUGIN_ROOT goto verify
set /p "ALAS_PLUGIN_ROOT=Enter the official Alas installation folder: "
:verify
if not exist "%ALAS_PLUGIN_ROOT%\toolkit\python.exe" goto missing
"%ALAS_PLUGIN_ROOT%\toolkit\python.exe" "%~dp0install.py" --alas "%ALAS_PLUGIN_ROOT%"
if errorlevel 1 goto failed
echo Installation complete. Start the original Alas.exe.
pause
exit /b 0
:missing
echo Could not find toolkit\python.exe in that folder.
:failed
pause
exit /b 1
