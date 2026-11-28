@echo off
chcp 65001 >nul
cd /d F:\rvc\EQSwitcher
F:\ANACONDA\python.exe -m PyInstaller --onefile --noconsole --uac-admin --name "EQ切换器" --icon "F:\rvc\EQSwitcher\eq.ico" --add-data "F:\rvc\EQSwitcher\eq.ico;." --distpath "dist" --workpath "build" --specpath "build" "eq-switcher.py"
copy /y "dist\EQ切换器.exe" "F:\rvc\EQSwitcher\EQ切换器.exe"
echo 构建完成
pause
