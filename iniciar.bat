@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
set "APP_URL=http://127.0.0.1:5000/"

if not exist "%PYTHON_EXE%" (
  echo No se encontro Python en:
  echo %PYTHON_EXE%
  echo.
  echo Instala Python 3.12 o actualiza este archivo con la ruta correcta.
  pause
  exit /b 1
)

cd /d "%PROJECT_DIR%"

start "" "%APP_URL%"
"%PYTHON_EXE%" app.py

endlocal
