@echo off
setlocal
cd /d "%~dp0"
echo Publishing MPMS through the saved FTP pipeline...
python "_private\refresh-secrets.py"
if errorlevel 1 goto fail
python "_private\publish-github.py"
if errorlevel 1 goto fail
echo Deployment and file verification completed.
pause
exit /b 0
:fail
echo Deployment stopped. Read the message above. No Git push was performed.
pause
exit /b 1
