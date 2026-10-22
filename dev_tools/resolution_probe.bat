@echo off
setlocal
cd /d "%~dp0.."
set "PROBE_ROOT=%CD%"
set "ALAS_PYTHON="
if not "%~1"=="" set "ALAS_PYTHON=%~1"
if defined ALAS_PYTHON if not exist "%ALAS_PYTHON%" set "ALAS_PYTHON="
if defined ALAS_PYTHON goto run
if exist "%PROBE_ROOT%\toolkit\python.exe" set "ALAS_PYTHON=%PROBE_ROOT%\toolkit\python.exe"
if defined ALAS_PYTHON goto run
echo This test uses an existing Alas Python environment without changing that installation.
set /p "ALAS_DIRECTORY=Enter your existing Alas installation folder: "
if exist "%ALAS_DIRECTORY%\toolkit\python.exe" set "ALAS_PYTHON=%ALAS_DIRECTORY%\toolkit\python.exe"
if defined ALAS_PYTHON goto run
echo Python was not found under toolkit\python.exe. Run the Python probe with your project environment instead.
pause
exit /b 1
:run
if not exist "%PROBE_ROOT%\tools\platform-tools\adb.exe" goto systemadb
"%ALAS_PYTHON%" -u "%PROBE_ROOT%\dev_tools\resolution_probe.py" --adb "%PROBE_ROOT%\tools\platform-tools\adb.exe" --serial 127.0.0.1:16448
goto done
:systemadb
"%ALAS_PYTHON%" -u "%PROBE_ROOT%\dev_tools\resolution_probe.py" --serial 127.0.0.1:16448
:done
set "PROBE_RESULT=%ERRORLEVEL%"
echo.
echo Exit code: %PROBE_RESULT%
echo Results are saved under log\resolution_probe in this extracted folder.
pause
exit /b %PROBE_RESULT%
