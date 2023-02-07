Remove-Item -Force -Recurse ./dist
. ./venv/Scripts/activate
pyinstaller galaxymsbt.spec
deactivate
Copy-Item -Path ./icons/ -Destination ./dist/icons/ -Recurse