@echo off
:: =============================================================================
:: actualizar.bat — Ejecuta el ciclo completo de actualización ICT-A
:: Programar en el Programador de tareas de Windows cada 1 hora.
:: Ruta de la carpeta: ajustar la variable PROYECTO abajo.
:: =============================================================================

set PROYECTO=C:\Users\Joaquin Flores\Downloads\Agregar un subtítulo\ITT-A\iit_antartico

cd /d "%PROYECTO%"

echo ========================================
echo   ICT-A — Actualizacion automatica
echo   %DATE% %TIME%
echo ========================================

"%PROYECTO%\venv\Scripts\python.exe" scripts/actualizar.py

echo.
echo Actualizacion completada: %TIME%
echo ========================================
