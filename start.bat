@echo off
title DataEraser
cd /d "%~dp0"

echo.
echo =====================================
echo    DataEraser  - Demarrage...
echo =====================================
echo.

:: Chercher Python
set PY=
for %%C in (python python3 py) do (
    %%C --version >nul 2>&1 && set PY=%%C && goto :found_py
)
goto :no_py

:found_py
echo [OK] Python trouve : 
%PY% --version
echo.

:: Verifier Flask
%PY% -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [..] Installation de Flask...
    %PY% -m pip install flask --quiet
    if errorlevel 1 (
        echo [..] Tentative alternative...
        %PY% -m pip install flask --quiet --user
    )
)

echo [OK] Flask pret
echo.
echo [>>] Lancement - le navigateur va s'ouvrir automatiquement
echo      Fermez cette fenetre pour arreter l'outil
echo.

%PY% app.py
goto :end

:no_py
echo.
echo [ERREUR] Python n'est pas installe.
echo.
echo Telechargez-le ici : https://www.python.org/downloads/
echo.
echo IMPORTANT : Cochez bien "Add Python to PATH" pendant l'installation.
echo.
pause
:end
