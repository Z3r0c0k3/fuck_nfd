@echo off
REM Windows .exe build script
REM 사용법: 이 파일을 Windows에서 더블클릭하거나 cmd에서 실행하세요.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --onefile --windowed ^
    --name "FuckNFD" ^
    --collect-all tkinterdnd2 ^
    fuck_nfd.py

echo.
echo 빌드 완료. dist\FuckNFD.exe 를 확인하세요.
pause
