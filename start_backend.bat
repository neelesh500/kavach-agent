@echo off
title Kavach Backend Server
echo Starting Kavach Security Agent Backend...
echo ----------------------------------------------------
echo Server is running! PLEASE DO NOT CLOSE THIS WINDOW.
echo You can minimize this window while you use the Chrome Extension.
echo ----------------------------------------------------
call .\venv\Scripts\activate.bat
python api_server.py
pause
