@echo off
cd C:\Users\Client\Desktop\New_Version\gso_latest_gso
call C:\Users\Client\Desktop\New_Version\newenv\Scripts\activate.bat
python manage.py backup
