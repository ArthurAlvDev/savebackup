@echo off
rem ===========================================================================
rem  SaveBackup - build do executavel Windows (PyInstaller)
rem  Saida: dist\SaveBackup.exe  (arquivo unico, sem console)
rem ===========================================================================
setlocal

cd /d "%~dp0"

if not exist "logo.ico" (
    echo AVISO: logo.ico nao encontrado. O executavel sera gerado sem icone.
)

echo [1/3] Restaurando icone e instalando dependencias de build...
python tools\restore_icon.py
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :erro

echo [2/3] Executando testes...
python -m unittest discover -s tests
if errorlevel 1 goto :erro

echo [3/3] Compilando com PyInstaller...
python -m PyInstaller --noconfirm --clean SaveBackup.spec
if errorlevel 1 goto :erro

if exist "dist\SaveBackup.exe" (
    echo.
    echo ===========================================================================
    echo  SUCESSO: dist\SaveBackup.exe
    echo ===========================================================================
    exit /b 0
)

:erro
echo.
echo  FALHA na compilacao. Veja as mensagens acima.
exit /b 1
