@echo off
REM Internal preview on this PC (includes DRAFT records, marked). Requires Python 3.
cd /d "%~dp0"
python _src\build.py --preview || goto :eof
echo.
echo Preview: http://localhost:8000/   (Ctrl+C to stop)
start "" http://localhost:8000/
python -m http.server 8000 --directory _preview
