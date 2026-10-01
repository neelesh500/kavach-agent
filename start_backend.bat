@echo off
echo Starting Kavach Security Agent Backend...
echo The backend is now running. Keep this window open or minimize it.
call .\venv\Scripts\activate.bat
python api_server.py
pause
