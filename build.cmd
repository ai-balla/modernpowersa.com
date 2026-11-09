@echo off
REM Rebuild the public site from _src\content. Commit the result to the working branch.
cd /d "%~dp0"
python _src\build.py
pause
