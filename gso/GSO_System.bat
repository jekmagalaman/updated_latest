@echo off
title GSO Local System Starter
echo ==============================================
echo   Starting Palawan State University GSO System
echo ==============================================

:: Go to project folder
cd /d "C:\Users\Client\Desktop\New_Version"

:: Activate virtual environment
echo Activating virtual environment...
call newenv\Scripts\activate.bat

:: Start FastAPI (AI/NLG service) in new window
echo Starting AI Service (Uvicorn)...
start cmd /k "cd /d C:\Users\Client\Desktop\New_Version\gso_latest_gso && uvicorn apps.ai_service.inference_server:app --reload --port 8001"

:: Start Django main system in another window
echo Starting Main Django Server...
start cmd /k "cd /d C:\Users\Client\Desktop\New_Version\gso_latest_gso && python manage.py runserver"

echo ==============================================
echo   Both servers are now running!
echo   - FastAPI (AI Service): http://127.0.0.1:8001
echo   - Django (Main System): http://127.0.0.1:8000
echo ==============================================

timeout /t 5 /nobreak >nul
start http://127.0.0.1:8000

pause
