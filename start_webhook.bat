@echo off
echo Starting VAPI Webhook Server...
echo.
echo Server will be available at: http://localhost:8080/webhook
echo Health check available at: http://localhost:8080/health
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "C:\Users\simon\New Era AI\Clients + Projects\OK Tire\VAPI Call Summary"
python src/main.py