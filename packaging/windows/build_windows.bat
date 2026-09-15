@echo off
echo Building Typist for Windows...

python -m pip install --upgrade pip
pip install -e ".[cross-platform]"
pip install pyinstaller

pyinstaller --clean packaging\windows\typist.spec

echo Build finished. Binary is in dist\typist\typist.exe
