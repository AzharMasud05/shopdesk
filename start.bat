@echo off
cd /d ~dp0

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo.
echo ==========================================
echo ShopDesk starting...
echo PC:       http://127.0.0.1:5000
echo Mobile:   http://<YOUR-PC-IP-ADDRESS>:5000  (same WiFi)
echo Example:  http://192.168.1.5:5000
echo ==========================================
echo.

python app.py
pause
