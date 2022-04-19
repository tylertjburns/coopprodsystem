cd /D "%~dp0"
call %CD%\venv\scripts\activate.bat
pip freeze>requirements.txt
python setup.py sdist bdist_wheel
twine upload dist\* --skip-existing
pause