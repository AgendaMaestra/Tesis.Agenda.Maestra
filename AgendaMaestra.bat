@echo off
setlocal enabledelayedexpansion
title Agenda Maestra - Sistema Global
mode con: cols=90 lines=30
color 0B

:inicio
cls
echo =====================================================================
echo          AGENDA MAESTRA - SERVIDOR INTEGRADO CON NGROK
echo =====================================================================
echo.

:: 1. VERIFICACION DE PYTHON
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python no detectado. Por favor, instalalo.
    pause
    exit
)

:: 2. GESTION DE DEPENDENCIAS
if exist requirements.txt (
    echo [+] Sincronizando librerias...
    pip install -q -r requirements.txt
    echo [OK] Entorno verificado.
)

:: 3. LIMPIEZA DE CACHE
del /s /q *.pyc >nul 2>&1
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1

:: 4. LANZAMIENTO DEL TUNEL NGROK (En ventana nueva)
echo [+] Abriendo tunel publico con ngrok...
:: Lanzamos ngrok en una ventana mínima para que no moleste
start "Tunel ngrok" /min ngrok http 5000

:: Esperamos 2 segundos para asegurar que el puerto esté listo
timeout /t 2 >nul

:: 5. LANZAMIENTO DEL SERVIDOR (En esta ventana)
echo.
echo [+] Iniciando servidor de alto rendimiento (Waitress)...
echo [INFO] Local: http://localhost:5000
echo [INFO] Publico: Revisa la ventana de ngrok para obtener la URL.
echo ---------------------------------------------------------------------
echo.

:: Ejecutamos el servidor principal
python run.py

:: 6. MODO DE EMERGENCIA
if %errorlevel% neq 0 (
    color 0E
    echo [!] Servidor principal interrumpido.
    echo [!] Probando modo de emergencia (Flask Debug)...
    timeout /t 2 >nul
    python app.py
)

if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No se pudo iniciar la Agenda. Revisa el puerto 5000.
)

:: 7. CIERRE DE NGROK AL TERMINAR
:: Cerramos ngrok automáticamente cuando detengas el servidor de Python
taskkill /f /im ngrok.exe >nul 2>&1

echo.
echo =====================================================================
echo       SESION FINALIZADA. NGROK Y SERVIDOR CERRADOS.
echo =====================================================================
pause >nul