@echo off
chcp 65001 >nul
cd /d F:\rvc\EQSwitcher
F:\ANACONDA\python.exe -m PyInstaller --onefile --noconsole --uac-admin --name "EQ???" --icon "F:\rvc\EQSwitcher\eq.ico" --add-data "F:\rvc\EQSwitcher\eq.ico;." --distpath "dist" --workpath "build" --specpath "build" "eq-switcher.py"
copy /y "dist\EQ???.exe" "F:\rvc\EQSwitcher\EQ???.exe"
echo ????
pause
