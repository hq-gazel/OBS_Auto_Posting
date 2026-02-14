@echo off
setlocal
cd /d "%~dp0"

echo [1/4] pip/uv を準備しています...
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install --upgrade uv
if errorlevel 1 goto :error

echo [2/4] 仮想環境を準備しています...
if not exist ".venv\Scripts\python.exe" (
    uv venv .venv
    if errorlevel 1 goto :error
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [3/4] 依存関係をインストールしています...
uv pip install --upgrade pip
if errorlevel 1 goto :error
uv pip install --native-tls -r requirements.txt
if errorlevel 1 goto :error

echo [4/4] 完了しました。
echo 以降は ".venv\Scripts\activate.bat" で有効化してから実行してください。
pause
exit /b 0

:error
echo [ERROR] インストールに失敗しました。上のログを確認してください。
pause
exit /b 1
