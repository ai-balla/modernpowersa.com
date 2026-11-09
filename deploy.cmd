@echo off
REM ============================================================
REM  Deploy the new modernpowersa.com
REM  1) publishes the reviewed branch to GitHub "main"  -> Hostinger auto-deploys the website
REM  2) uploads the private bundle (form settings) by FTP to ~/_mpms_private (outside the web root)
REM  Rollback: see _docs\DEPLOYMENT.md  (previous version = commit 2c880aa)
REM ============================================================
cd /d "%~dp0"
echo.
echo [1/3] Checking content...
python _src\build.py --check || goto :fail
echo.
echo [2/3] Publishing to GitHub (main) - Hostinger deploys automatically...
git push origin dev/bilingual-rebuild || goto :fail
git push origin main || goto :fail
echo.
echo [3/3] Uploading private form settings (FTP, outside the web root)...
powershell -ExecutionPolicy Bypass -File "_private\ftp-upload.ps1" -Phase 2 || goto :fail
echo.
echo DONE. Wait 2-3 minutes, then open https://modernpowersa.com/ and tell Claude "deployed".
pause
goto :eof
:fail
echo.
echo *** Something failed. Nothing further was done. Copy the messages above to Claude. ***
pause
